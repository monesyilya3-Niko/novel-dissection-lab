"""服务层业务编排：导入 / 切批 / 分析执行 / 暂停 / 续传 / 重试。

分层：路由层 → 服务层 → 引擎适配层。本模块不 import novel-lab 脚本，
只调用 engine_adapter 与 state_store。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gui import asset_index, config, db, engine_adapter, state_store
from gui.logging_setup import get_logger
from gui.sse import broker

_log = get_logger("services")

# 每个 pass 分析的 kind 名（串行顺序）。
# 2026-11-23：GUI 主链路补上 pass5_craft。此前只跑 4 pass，笔法卡/笔法分析报告
# 在 GUI 里永远不可能生成（结果页却始终展示「笔法卡」），属于明确的资产缺口。
PASS_ORDER = ("pass1_structure", "pass2_character", "pass3_style", "pass4_commercial",
              "pass5_craft")

# 离线 Web-AI 拆书接管支持的全部五遍扫描 Pass。
TAKEOVER_PASSES: tuple[tuple[str, str], ...] = (
    ("pass1_structure", "Pass 1 · 结构与钩子"),
    ("pass2_character", "Pass 2 · 角色声线与对话"),
    ("pass3_style", "Pass 3 · 叙述视角与文风"),
    ("pass4_commercial", "Pass 4 · 爽点与商业节奏"),
    ("pass5_craft", "Pass 5 · 十维笔法深度拆解"),
)
_TAKEOVER_PASS_MAP: dict[str, str] = dict(TAKEOVER_PASSES)

#: 主循环最多重扫几轮。retry_failed 把失败批改回 pending 后需要再走一遍，
#: 但有上限——否则「一直失败 → 一直 pending → 无限重扫」会把线程卡死。
_MAX_RESCAN_ROUNDS = 3

#: 合并批级 pass 文件时**不参与合并**的键（2026-11-05）。
#:
#: ``_meta``/``model``/``tokens`` 是元信息。``status``/``message``/``note``
#: 是模型**拒答**的措辞（见 pipeline._looks_like_refusal）：整批拒答的文件长这样
#:
#:     {"status": "no_input", "message": "未收到任何对话切片文本", "characters": []}
#:
#: 若把它们合并进来，``if pass2 or pass3`` 会因为 ``status`` 非空而判真，
#: 于是产出一张 ``character_voices: []`` 的空壳 voice-card——校验又恰好放行
#: （必填字段都在，只是全空）。用户拿到一张"有卡但没内容"的资产，
#: 比完全没有卡更难察觉。跳过这些键后，纯拒答批次合并结果为空 dict，
#: 上层 ``if pass2 or pass3`` 自然不成立，不会生成空壳。
_MERGE_SKIP_KEYS = frozenset({
    "_meta", "model", "tokens", "status", "message", "note", "error", "detail",
})


class ServiceError(Exception):
    """服务层业务错误，携带 HTTP 状态码。"""

    def __init__(self, message: str, code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def _require_positive_batch_size(batch_size: int | None) -> None:
    """纵深防御：服务层不信任调用方已做校验，非法 batch_size 直接 400。

    路由层已有 _safe_batch_size，但内部调用可绕过路由；负数 batch_size
    会透过 `batch_size or default`（负数 truthy）进入后台线程导致异常。
    """
    if batch_size is not None and batch_size <= 0:
        raise ServiceError("batch_size 必须为正整数", 400)


# ---------------------------------------------------------------------------
# 资产内容契约（不接触磁盘）
#
# 资产引用（``voice:<name>``）只给出**文件名**，文件名不保证与内容一致：
# 蒸馏卡历史上就落成 ``*-voice-card-distilled.json`` 这类基础卡后缀。因此服务层
# 在解析出 JSON 后必须按**内容**复核 kind，否则 distilled 会被当成单书 voice 卡
# 参与打分/注入，静默产出错误结果。
#
# 识别逻辑只此一份（单一来源）：服务层各函数一律调 ``assert_asset_kind``，不得复制。
# ---------------------------------------------------------------------------

# 跨书蒸馏卡的四维取值（与 scripts/validate.py、distill_core.DIMENSIONS 同源语义）。
_DISTILLED_DIMENSIONS = ("voice-card", "craft-card", "structure-obs", "commercial-obs")

# 自证 kind → 出现时的改用建议（错误消息用，明确提示应传哪个参数）。
_KIND_HINTS = {
    "distilled": "该文件是跨书题材蒸馏卡（distilled），不是单书基础卡；请通过 distilled 参数传入",
    "prose_card_index": "该文件是题材文风卡索引（prose_card_index，仅含题材→卡片文件的寻址表）；"
                        "请改用索引 cards 中指向的 genre-prose-card 卡片文件（prose_card 参数）",
    "prose_card": "该文件是题材文风卡；请通过 prose_card 参数传入",
}


def detect_asset_kind(data: Any) -> str | None:
    """按**内容**识别资产 kind（不接触磁盘）；无法自证的返回 None。

    Returns:
        ``"prose_card"`` / ``"prose_card_index"`` / ``"distilled"`` / ``None``。

    ``None`` 表示该资产不含自证字段（基础卡 voice/structure/commercial/craft、
    题材包等都属此类），调用方无从也无需反查其真实 kind。
    """
    if not isinstance(data, dict):
        return None
    meta = data.get("meta")
    meta = meta if isinstance(meta, dict) else {}
    # 题材文风卡：显式 meta.kind 标记（索引不含此标记）。
    if meta.get("kind") == "genre-prose-card":
        return "prose_card"
    # 题材文风卡索引：cards 寻址映射（_count/_description 为可选元信息）。
    if isinstance(data.get("cards"), (dict, list)):
        return "prose_card_index"
    # 跨书蒸馏卡：``meta.dimension ∈ 四维`` **或** ``rules/blindspots/stats 三元组齐备``。
    # OR 语义与 scripts/validate.py:auto_kind 严格同构——用 AND 会把「缺 meta.dimension、
    # 仅三元组」的蒸馏卡漏判，从而被放行当 voice 用（口径分叉）。
    if (meta.get("dimension") in _DISTILLED_DIMENSIONS
            or all(k in data for k in ("rules", "blindspots", "stats"))):
        return "distilled"
    return None


def assert_asset_kind(data: Any, expected: str, ref: str) -> None:
    """断言资产内容与期望 kind 一致；不一致抛 ``ServiceError(msg, 400)``。

    只对**能自证 kind** 的资产（distilled / prose_card_index / prose_card）做拒绝：
    例如 distilled 当作 voice 传入、index 当作 prose_card 传入。

    Args:
        data: 已解析的资产 JSON。
        expected: 该参数期望的 kind（voice/structure/commercial/craft/prose_card/distilled）。
        ref: 原始资产引用（仅用于错误消息定位）。
    """
    actual = detect_asset_kind(data)
    if actual is None or actual == expected:
        return
    hint = _KIND_HINTS.get(actual, "")
    raise ServiceError(
        f"资产 kind 不匹配：{ref} 的内容自证为 {actual}，不能作为 {expected} 使用。{hint}", 400)


# ---------------------------------------------------------------------------
# 运行时全局（进程内单例）
# ---------------------------------------------------------------------------

# 已导入书籍：book_id -> {title, source_path, chapters:[(title, body)], metrics}
# B9：LRU 缓存（最多 _BOOKS_MAX 本），超限时淘汰最久未用且未在分析中的书；
# 被淘汰的书可通过 _BOOK_INDEX 从源文件透明重载。
_BOOKS: OrderedDict[str, dict[str, Any]] = OrderedDict()
_BOOKS_MAX = 3
# 轻量索引：book_id -> source_path（淘汰后仍保留，用于透明重载）。
# 有界：防止长期导入导致无界增长；超限时淘汰最久未写入者。
_BOOK_INDEX: OrderedDict[str, str] = OrderedDict()
_BOOK_INDEX_MAX = 100
_books_lock = threading.Lock()


def _books_get(book_id: str) -> dict[str, Any] | None:
    """LRU 获取：命中时移到末尾（标记最近使用）；未命中时尝试从源文件重载。

    B9：淘汰后透明重载，保证用户无感。

    2026-11-04：内存与 _BOOK_INDEX 都未命中时，回退查 SQLite ``books`` 表。
    此前只有 `_BOOK_INDEX` 一个来源，而它是纯进程内字典——重启后为空，
    于是所有已导入的书一律 404「未导入（请先 import）」，断点续传彻底失效
    （实测：导入 → 清内存 → get_book 直接 404）。books 表里一直有正确的
    ``source_path``（``import_book`` 会 upsert 进去），只是从来没人读它。
    """
    with _books_lock:
        book = _BOOKS.get(book_id)
        if book is not None:
            _BOOKS.move_to_end(book_id)
            return book
        # 未命中：尝试从索引重载
        src_path = _BOOK_INDEX.get(book_id)
    if src_path is None:
        # 回退：从持久化的 books 表取源路径（重启后与 LRU 淘汰后的兜底）
        try:
            rows = db.get_books(book_id=book_id)
            if rows:
                src_path = rows[0].get("source_path") or None
        except Exception as exc:  # noqa: BLE001 - 库不可用时保持原行为
            _log.warning("从 books 表回退取 source_path 失败: %s", exc)
    if src_path is None:
        return None
    # 在锁外重载（IO 耗时），重载后重新加锁插入
    try:
        reloaded = _load_book_from_disk(book_id, src_path)
    except (OSError, ServiceError):
        return None
    with _books_lock:
        # 双重检查：重载期间可能已被其他线程插入
        if book_id in _BOOKS:
            _BOOKS.move_to_end(book_id)
            return _BOOKS[book_id]
        _books_put_locked(book_id, reloaded)
        return reloaded


def _books_put_locked(book_id: str, book: dict[str, Any]) -> None:
    """插入 LRU（调用方持有 _books_lock）；超限时淘汰最久未用者。

    正在分析中（_runtime 有条目）的书永不淘汰。
    """
    _BOOKS[book_id] = book
    _BOOKS.move_to_end(book_id)
    _BOOK_INDEX[book_id] = book["source_path"]
    _BOOK_INDEX.move_to_end(book_id)
    # 有界：索引超限时淘汰最久未写入者（仅影响极旧书的透明重载，可重新导入）。
    while len(_BOOK_INDEX) > _BOOK_INDEX_MAX:
        _BOOK_INDEX.popitem(last=False)
    # 淘汰：从最久未用开始，跳过正在分析的
    with _runtime_lock:
        analyzing = set(_runtime.keys())
    while len(_BOOKS) > _BOOKS_MAX:
        oldest_id = next(iter(_BOOKS))
        if oldest_id in analyzing:
            # 最久的是正在分析的，尝试淘汰次久的
            evicted = False
            for bid in list(_BOOKS.keys()):
                if bid not in analyzing:
                    del _BOOKS[bid]
                    evicted = True
                    break
            if not evicted:
                break  # 全在分析中，放弃淘汰
        else:
            del _BOOKS[oldest_id]


def _load_book_from_disk(book_id: str, src_path: str) -> dict[str, Any]:
    """从源文件重载书籍（B9 透明重载路径）。"""
    src = Path(src_path)
    if not src.is_absolute() or not src.exists():
        # migrate CLI 在 books 表里存的是相对 ROOT 的路径（corpus/xxx.txt）。
        # 直接 Path(rel) 会相对当前工作目录解析，重启/淘汰后书就打不开了。
        try:
            from gui import migrate as _migrate
            resolved = _migrate.resolve_rel_path(str(src_path))
            if resolved.exists():
                src = resolved
        except Exception:  # noqa: BLE001
            pass
    if not src.exists():
        raise ServiceError(f"源文件已丢失: {src_path}", 404)
    # 经 _secure_read_text：防符号链接、FIFO、超大文件（与 import 同一路防线）。
    text = _secure_read_text(str(src))
    chapters_raw = engine_adapter.split_chapters(text)
    if not chapters_raw:
        raise ServiceError("源文件无法解析", 400)
    metrics = engine_adapter.compute_metrics(text)
    del text
    return {
        "title": src.stem,
        "source_path": str(src),
        "chapters": chapters_raw,
        "metrics": metrics,
    }

# 分析运行时：book_id -> 分析上下文（线程 + 控制标志）
_runtime: dict[str, dict[str, Any]] = {}
_runtime_lock = threading.Lock()
# 报告生成互斥：两个 _watch 线程（前后两轮一键分析）可能同时观察到 done
# 并发写同一报告文件；write_text 非原子，会交错损坏。串行化生成。
_report_gen_lock = threading.Lock()


def _books_dir() -> Path:
    return config.STATE_ROOT


def unique_corpus_path(name: str) -> Path:
    """corpus/ 下防重名：已存在则追加 -1/-2…。

    P2-3 修复：用 O_CREAT|O_EXCL 原子占位，避免并发同名上传的 check-then-act
    竞态（旧实现双线程可返回同一路径，后写覆盖前写）。占位产生空文件，
    调用方随后覆盖写入（write_bytes/copy2 均可）；导入失败时由 P2-2 清理删掉。
    """
    config.CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    stem, suffix = Path(name).stem, Path(name).suffix
    i = 0
    while True:
        cand = config.CORPUS_DIR / (name if i == 0 else f"{stem}-{i}{suffix}")
        try:
            fd = os.open(cand, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return cand
        except FileExistsError:
            i += 1


# ---------------------------------------------------------------------------
# 导入
# ---------------------------------------------------------------------------

# 导入接受的正文后缀必须与其它入口一致（2026-11-05 修）。
#
# 原先这里是 {".txt"}，而上传入口（server._safe_upload_filename）已改用
# text_access.TEXT_SUFFIXES（{".txt", ".md"}），章节加载器也读 .md。
# 实测同一个 .md 稿子：上传导入成功，路径导入被拒「首版仅支持 .txt 导入」——
# 用户会看到"拖进去能行、选路径不行"这种自相矛盾的行为。
#
# 延迟到使用时取（text_access 反向 import 本模块的 ServiceError，模块级 import
# 会成环）；_import_suffixes() 是唯一入口，不要在别处再写一份后缀集合。
def _import_suffixes() -> frozenset[str]:
    from gui import text_access
    return text_access.TEXT_SUFFIXES
_IMPORT_MAX_BYTES = 100 * 1024 * 1024
# 拆书导入的对外措辞与状态码是既有契约（tests/test_deepwater_regressions.py 认它），
# 实现换成 text_access 后逐条显式覆盖，不让"重构"顺手改掉用户看到的错误信息。
_IMPORT_MESSAGES = {
    "suffix": ("仅支持 .txt / .md 导入", 400),
    "symlink": ("不允许导入符号链接", 403),
    "irregular": ("只能导入常规文件", 400),
    "oversize": ("文件超过 100MB 上限", 400),
    "missing": ("文件无法打开: {path}", 404),
    "unreadable": ("文件读取失败: {path}", 500),
    # 文案必须与实际解码链一致（2026-11-05）。原写「仅支持 UTF-8 / GBK」，
    # 而 text_access.read_text 实际依次尝试 UTF-16(BOM) / UTF-8(BOM) /
    # GB18030 / GBK——告诉用户"不支持你的编码"会让他去徒劳地转码，
    # 真实原因通常是文件损坏或不是文本。
    "decode": ("文件编码无法识别（已尝试 UTF-8 / GB18030 / GBK / UTF-16；"
               "若为其他编码请先另存为 UTF-8）", 400),
}


def _secure_read_text(path: str) -> str:
    """TOCTOU 安全读取文本文件（实现见 ``gui/text_access.py``，策略在此声明）。

    与打分 / 合规 / 投稿导出共用同一条读取通道：`os.open` 时带 O_NOFOLLOW，
    随后用 `fstat` 在同一 fd 上判常规文件与体积，全程不重解析路径；
    Windows 没有 O_NOFOLLOW，退化为打开后 `islink` 尽力检查。
    拆书只收 `.txt`、上限 100MB，与正文打分（`.txt`/`.md`、8MB）不同。
    """
    from gui import text_access

    return text_access.read_text(
        path,
        field="导入文件",
        suffixes=_import_suffixes(),
        max_bytes=_IMPORT_MAX_BYTES,
        messages=_IMPORT_MESSAGES,
    )


def import_book(path: str, batch_size: int | None = None) -> dict[str, Any]:
    """读 txt → 切章 → 切批 → 生成 book_id → 建状态文件 → 返回 Book。

    返回的 Book 章节列表只含批次元信息（不含正文），正文按需由 chapter 接口返回。
    读取与准入都由 :func:`_secure_read_text` 负责（后缀 / 符号链接 / 常规文件 /
    体积），路由层不再判目录（2026-10-08：用户要拆的书本来就在项目外）。
    导入是**就地引用** ``path``，不复制进 corpus/——原文件被移走后透明重载会 404。
    """
    src = Path(path)
    text = _secure_read_text(path)

    chapters_raw = engine_adapter.split_chapters(text)
    if not chapters_raw:
        raise ServiceError("未解析到任何章节（请确认文件为章节体 txt）", 400)
    # 空章会被 split_chapters 过滤（拆书无从分析空正文），但用户需要知道
    # 少了哪几章，否则「导入 50 章只见 48 章」看起来像丢内容。
    skipped_empty = engine_adapter.count_skipped_empty_chapters(text)

    _require_positive_batch_size(batch_size)
    bs = batch_size or config.batch_size_from_env()
    title = src.stem
    # 2026-11-04：book_id 生成规则已从「原始路径 md5」改为「规范化路径 md5」
    # （修正同一文件换写法就变成新书的问题）。为了让**规则变更前已导入**的书
    # 仍能被找回，这里做一次兼容：新 id 没有状态文件、但旧规则 id 有时，沿用旧 id。
    # 只在旧 id 确实存在时回退，新导入的书一律走新规则，不会长期依赖。
    new_id = state_store.book_id_from_title(title, str(src))
    legacy_id = state_store.legacy_book_id_from_title(title, str(src))
    if (new_id != legacy_id
            and state_store.resolve_state_path(new_id) is None
            and state_store.resolve_state_path(legacy_id) is not None):
        book_id = legacy_id
    else:
        book_id = new_id

    # 计算每章批次（只存元信息；正文不入响应，按需由 chapter 接口返回）。
    chapters_meta: list[dict[str, Any]] = []
    for i, (ctitle, cbody) in enumerate(chapters_raw, start=1):
        batches = engine_adapter.split_batches(cbody, bs)
        chapters_meta.append({
            "index": i,
            "title": ctitle,
            "batch_count": len(batches),
            "batches": [{
                "chapter_index": i,
                "batch_index": b["batch_index"],
                "char_start": b["char_start"],
                "char_end": b["char_end"],
                "status": "pending",
            } for b in batches],
        })

    # 整书量化指标（缓存复用，供单批分析）。
    metrics = engine_adapter.compute_metrics(text)
    # 内存：text（约 1x 文件大小的 str）只用于算 metrics，
    # 正文已在 chapters_raw 中保留，此处释放避免与后继流程叠加。
    del text

    with _books_lock:
        _books_put_locked(book_id, {
            "title": title,
            "source_path": str(src),
            "chapters": chapters_raw,
            "metrics": metrics,
        })

    # 2026-11-03：导入后立即登记到 books 表。
    # 此前 import_book 只写内存 LRU 与状态文件，books 表要等下一次
    # ``migrate`` 全量扫描才会出现这本书——用户刚导入完，首页「已拆书」
    # 与 /api/overview.total_books 都不变，看上去像导入没成功。
    # 失败只记日志：登记不上不该让导入本身失败（正文已在内存与状态文件里）。
    try:
        from gui import migrate as _migrate
        with db.tx() as conn:
            _migrate._upsert_book(
                conn, book_id, title, str(src), None, "idle")
    except Exception as exc:  # noqa: BLE001
        _log.warning("导入后登记 books 表失败（不影响本次导入）: %s", exc)

    # 建/复用状态文件。
    state = state_store.load_state(book_id)
    state["title"] = title
    state_store.save_state(state)

    return {
        "book_id": book_id,
        "title": title,
        "source_path": str(src),
        "total_chapters": len(chapters_raw),
        "skipped_empty_chapters": skipped_empty,
        "chapters": chapters_meta,
    }


def get_book(book_id: str) -> dict[str, Any]:
    """返回 Book 摘要（章节 + 批元信息，不含正文全文）。"""
    book = _get_book_or_raise(book_id)
    chapters_meta = _chapters_meta(book_id, book)
    return {
        "book_id": book_id,
        "title": book["title"],
        "source_path": book["source_path"],
        "total_chapters": len(book["chapters"]),
        "chapters": chapters_meta,
    }


def get_chapter(book_id: str, idx: int) -> dict[str, Any]:
    """返回单章（含全文 + 批切分结果）。"""
    book = _get_book_or_raise(book_id)
    chapters = book["chapters"]
    if idx < 1 or idx > len(chapters):
        raise ServiceError(f"章节 {idx} 不存在（共 {len(chapters)} 章）", 404)
    ctitle, cbody = chapters[idx - 1]
    batches = split_chapter_batches(book_id, idx)
    return {
        "index": idx,
        "title": ctitle,
        "text": cbody,
        "batch_count": len(batches),
        "batches": batches,
    }


def split_chapter_batches(book_id: str, idx: int, batch_size: int | None = None) -> list[dict[str, Any]]:
    """切批薄封装，可配置 batch_size。"""
    book = _get_book_or_raise(book_id)
    chapters = book["chapters"]
    if idx < 1 or idx > len(chapters):
        raise ServiceError(f"章节 {idx} 不存在", 404)
    _, cbody = chapters[idx - 1]
    _require_positive_batch_size(batch_size)
    bs = batch_size or config.batch_size_from_env()
    batches = engine_adapter.split_batches(cbody, bs)
    return [{
        "chapter_index": idx,
        "batch_index": b["batch_index"],
        "char_start": b["char_start"],
        "char_end": b["char_end"],
        "text": b["text"],
        "status": "pending",
    } for b in batches]


def _get_book_or_raise(book_id: str) -> dict[str, Any]:
    # 类型校验（2026-10-12 补）：book_id 在下面被用作 dict key，
    # 请求体传 {"book_id": ["a"]} 会以 "unhashable type: 'list'" 变 500。
    # 这里是 9 个调用点的共同入口，在此收口一处即可全覆盖。
    if not isinstance(book_id, str):
        raise ServiceError("book_id 必须为字符串", 400)
    book = _books_get(book_id)
    if book is None:
        raise ServiceError(f"书籍 {book_id} 未导入（请先 import）", 404)
    return book


def _chapters_meta(book_id: str, book: dict[str, Any]) -> list[dict[str, Any]]:
    """构造章节元信息（批数 + 状态，从状态文件同步状态）。"""
    state = state_store.load_state(book_id)
    chapter_states = state.get("chapter_states", {})
    metas = []
    for i, (ctitle, cbody) in enumerate(book["chapters"], start=1):
        batches = engine_adapter.split_batches(cbody, config.batch_size_from_env())
        batch_metas = []
        for b in batches:
            key = state_store.batch_id(i, b["batch_index"])
            record = chapter_states.get(key)
            st = record.get("status", "pending") if isinstance(record, dict) else "pending"
            batch_metas.append({
                "chapter_index": i,
                "batch_index": b["batch_index"],
                "char_start": b["char_start"],
                "char_end": b["char_end"],
                "text": "",
                "status": st,
            })
        metas.append({
            "index": i,
            "title": ctitle,
            "batch_count": len(batches),
            "batches": batch_metas,
        })
    return metas


# ---------------------------------------------------------------------------
# 分析执行（串行：章→批→pass）
# ---------------------------------------------------------------------------

# 每本书最多保留的归档轮次。归档是按时间戳新建目录、永不覆盖的，重跑多次
# 会无声堆积（一本书 4 张卡 + 2 份报告，重跑 100 次就是几百 MB）。
# 只保留最近 N 轮，够回滚也够追查，不会把用户磁盘吃满。
_MAX_ANALYSIS_ARCHIVES_PER_BOOK = 5


def _archive_analysis_outputs(book_id: str, reason: str) -> list[str]:
    """把旧整书卡与报告移入本地归档，避免新分析失败时仍展示旧产物。"""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    book_archive_root = config.STATE_ROOT / "analysis_archive" / book_id
    archive = book_archive_root / f"{stamp}-{reason}"
    sources = [
        (config.ASSETS_ROOT / f"{book_id}-voice-card.json", "assets"),
        (config.ASSETS_ROOT / f"{book_id}-structure-obs.json", "assets"),
        (config.ASSETS_ROOT / f"{book_id}-commercial-obs.json", "assets"),
        (config.ASSETS_ROOT / f"{book_id}-craft-card.json", "assets"),
        (config.REPORTS_DIR / f"{book_id}-拆书报告.md", "reports"),
        (config.REPORTS_DIR / f"{book_id}-笔法分析.md", "reports"),
    ]
    moved: list[str] = []
    for src, category in sources:
        if not src.is_file():
            continue
        dst_dir = archive / category
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / src.name
        shutil.move(str(src), str(dst))
        moved.append(str(dst))
    if moved:
        _prune_analysis_archives(book_archive_root)
    return moved


def _prune_analysis_archives(book_archive_root: Path) -> None:
    """只保留最近 N 轮归档，删除更旧的（按目录名的时间戳前缀排序）。

    失败一律吞掉：清理是尽力而为，绝不能因为删不掉旧归档就让分析失败。
    """
    try:
        dirs = sorted(
            (d for d in book_archive_root.iterdir() if d.is_dir()),
            key=lambda d: d.name,
        )
    except OSError:
        return
    for stale in dirs[:-_MAX_ANALYSIS_ARCHIVES_PER_BOOK]:
        try:
            shutil.rmtree(stale)
        except OSError:
            _log.warning("清理旧分析归档失败: %s", stale)


def start_analysis(
    book_id: str,
    genre: str,
    model_id: str | None = None,
    batch_size: int | None = None,
    *,
    generate_reports: bool | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    """开始新分析或续传。串行跑，后台线程执行，SSE 推送进度。"""
    _get_book_or_raise(book_id)
    if not engine_adapter.any_model_configured():
        raise ServiceError("未配置外部模型，请先运行 model_config.py 配置（PRD Q7：首版 GUI 仅支持已配置模型）", 400)

    # P0-4：题材必填且必须在注册表中（唯一来源：engine_adapter.is_known_genre）。
    if not engine_adapter.is_known_genre(genre):
        raise ServiceError(
            f"未知题材 {genre!r}，请从题材列表中选择（GET /api/genres）", 400)

    _require_positive_batch_size(batch_size)
    bs = batch_size or config.batch_size_from_env()

    # 【修复 M6】「检查 + 建 ctx + 建线程 + 登记 + 启动」必须在一个临界区内完成。
    # 原先分两段加锁且 thread 在锁外赋值，两个并发 start 可同时通过 is_alive 检查
    # （都看到无线程），各自起一个分析线程并发写同一状态与资产。
    with _runtime_lock:
        rt = _runtime.get(book_id)
        if rt and rt.get("thread") and rt["thread"].is_alive():
            raise ServiceError("分析已在运行中", 409)

        # 新分析先归档旧整书产物并清空批次；续传必须保留 success 批，避免重复扣费。
        if not resume:
            _archive_analysis_outputs(book_id, "restart")

        # 【修复 H3】必须把 status 重置为 running 并清掉上一次的 report_error。
        # 否则重跑一本已分析完（status="done"）的书时，报告监听线程 _watch 首次
        # 轮询就读到残留的 "done"，立刻用旧/半成品资产生成报告，并与新启动的
        # 分析线程并发读写同一批资产卡；返回体却仍声称 status:"running"。
        with state_store.update_state(book_id) as state:
            state["genre"] = genre
            state["model_id"] = model_id
            state["batch_size"] = bs
            state["status"] = "running"
            if not resume:
                state["chapter_states"] = {}
                state["asset_index"] = {}
                state["cursor"] = ""
                state["analysis_run_id"] = datetime.now(timezone.utc).isoformat()
            if generate_reports is not None:
                state["generate_reports"] = bool(generate_reports)
            state.pop("report_error", None)
            # 2026-11-23：重跑时旧错误必须清掉，否则进度页一边显示 running
            # 一边挂着上一次的红色失败原因，用户以为新任务又失败了。
            state.pop("last_error", None)

        # 启动后台线程（在锁内完成登记与启动，保证并发安全）
        stop_flag = threading.Event()
        ctx = {"stop_flag": stop_flag, "paused": threading.Event(), "thread": None}
        _runtime[book_id] = ctx
        thread = threading.Thread(
            target=_run_analysis,
            args=(book_id, genre, model_id, bs, ctx),
            daemon=True,
            name=f"analysis-{book_id}",
        )
        ctx["thread"] = thread
        thread.start()

    # 返回持久化的真实 cursor（断点），而非硬编码 c1-b0。
    state = state_store.load_state(book_id)
    cursor = state.get("cursor") or state_store.batch_id(1, 0)
    return {"task_id": book_id, "cursor": cursor, "status": "running"}


def _record_batch_failure(
    book_id: str,
    book: dict[str, Any],
    chapters: list[Any],
    genre: str,
    ci: int,
    bi: int,
    done: int,
    total_batches: int,
    ctx: dict[str, Any],
    exc: Exception,
    passes: dict[str, str] | None = None,
) -> bool:
    """记录单批失败；若命中鉴权/欠费熔断则生成离线接管指引并返回 True（主循环立即退出）。"""
    err_text = str(exc)[:500]
    if engine_adapter.is_auth_or_quota_error(exc):
        guide_rel = ""
        try:
            off = engine_adapter.run_offline_analysis(
                book_id,
                book.get("title") or book_id,
                chapters,
                genre,
                reason=f"外部模型不可用：{err_text[:160]}",
            )
            guide_rel = off.get("guide_path") or ""
        except Exception as off_exc:  # noqa: BLE001
            _log.warning("生成离线接管指引失败 %s: %s", book_id, off_exc)
        with state_store.update_state(book_id) as state:
            state_store.set_batch_state(state, ci, bi, "failed", passes=passes)
            state["status"] = "error"
            state["last_error"] = err_text
            if guide_rel:
                state["takeover_guide_path"] = guide_rel
        _sync_book_status(book_id, "error")
        broker.publish({
            "book_id": book_id,
            "status": "error",
            "chapter_index": ci,
            "batch_index": bi,
            "done": done,
            "total": total_batches,
            "message": err_text,
        })
        return True
    with state_store.update_state(book_id) as state:
        state_store.set_batch_state(state, ci, bi, "failed", passes=passes)
        state["last_error"] = err_text
    _publish(book_id, ci, bi, "failed", done + 1, total_batches, ctx)
    return False


def _pass_asset_valid(book_id: str, ci: int, bi: int, pass_name: str) -> bool:
    """批级产物存在且含有效载荷；损坏或纯拒答文件视为待补跑。"""
    try:
        data = json.loads(state_store.asset_path(book_id, ci, bi, pass_name).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return False
    if not isinstance(data, dict):
        return False
    return any(k not in _MERGE_SKIP_KEYS and v not in (None, "", [], {}) for k, v in data.items())


def _pending_passes(book_id: str, ci: int, bi: int, existing: object | None) -> tuple[str, ...]:
    """续传时只补跑缺失/失败的 pass；新批或失败批则执行全部 pass。"""
    if not isinstance(existing, dict) or existing.get("status") != "success":
        return PASS_ORDER
    recorded = existing.get("passes") if isinstance(existing.get("passes"), dict) else {}
    return tuple(
        name for name in PASS_ORDER
        if (name in recorded and recorded.get(name) != "success")
        or not _pass_asset_valid(book_id, ci, bi, name)
    )


def _run_analysis(book_id: str, genre: str, model_id: str | None, batch_size: int, ctx: dict[str, Any]) -> None:
    """后台串行分析主循环。"""
    try:
        book = _books_get(book_id)
        if book is None:
            # B7：书在线程启动后被 LRU 淘汰（_books_get 会尝试重载，仍为 None
            # 说明源文件也丢了），直接返回；finally 仍清理 _runtime 防泄漏。
            return
        chapters = book["chapters"]
        metrics = book["metrics"]
        total_batches = _count_total_batches(chapters, batch_size)
        done = 0

        # 2026-11-05：主循环支持**重扫**。
        # retry_failed 在线程存活时把失败批改回 pending 并承诺「将在当前循环内重扫」，
        # 但原来的单趟 for 循环已经走过那些位置，pending 再也不会被访问——
        # 接口 200、提示说会重扫、该批却永远停在 pending。
        # 现在整趟遍历结束后，只要还有 pending 批就再扫一轮（最多 MAX_RESCAN_ROUNDS 轮）。
        _rescan_rounds = 0
        outputs_archived = False
        while True:
            for ci, (ctitle, cbody) in enumerate(chapters, start=1):
                batches = engine_adapter.split_batches(cbody, batch_size)
                for b in batches:
                    bi = b["batch_index"]
                    key = state_store.batch_id(ci, bi)

                    existing = state_store.load_state(book_id).get("chapter_states", {}).get(key)
                    if not isinstance(existing, dict):
                        existing = None
                    passes_to_run = _pending_passes(book_id, ci, bi, existing)
                    if existing and existing.get("status") == "success" and not passes_to_run:
                        done += 1
                        continue

                    _wait_if_paused(ctx)
                    if ctx["stop_flag"].is_set():
                        _publish(book_id, ci, bi, "paused", done, total_batches, ctx)
                        return
                    # 2026-11-03：从暂停恢复后要把 state.status 改回 running。
                    # 此前 pause 会把状态写成 "paused"，resume 只 clear 了内存里的
                    # Event，主循环这里没回写状态——于是分析已经继续跑批，
                    # /api/status 却永远显示 paused，前端也就不再刷新进度。
                    _resume_status_if_paused(book_id)

                    if not outputs_archived:
                        _archive_analysis_outputs(book_id, "resume")
                        outputs_archived = True
                    pass_status = {
                        name: ("pending" if name in passes_to_run else "success")
                        for name in PASS_ORDER
                    }

                    _publish(book_id, ci, bi, "running", done, total_batches, ctx)
                    # 标记 running 落盘（原子读改写：HTTP 线程可能同时在 pause/retry）
                    with state_store.update_state(book_id) as state:
                        state_store.set_batch_state(state, ci, bi, "running", passes=pass_status)

                    last_asset = None
                    pass5_error = ""
                    try:
                        for pass_name in passes_to_run:
                            try:
                                out = engine_adapter.run_batch(
                                    pass_name, ci, ctitle, b["text"], metrics,
                                    dry_run=False, model_id=model_id,
                                )
                            except Exception as pass_exc:  # noqa: BLE001
                                pass_status[pass_name] = "failed"
                                # pass5 失败保留 pass1-4，但整本书必须显示部分完成，不能冒充全部成功。
                                if pass_name == "pass5_craft":
                                    pass5_error = str(pass_exc)[:500]
                                    _log.warning(
                                        "pass5 笔法拆解失败，保留 pass1-4 资产 book=%s c%d-b%d: %s",
                                        book_id, ci, bi, pass_exc,
                                    )
                                    continue
                                raise
                            # 每个 pass 原子落一个资产文件，避免中断留下半份 JSON。
                            ap = state_store.asset_path(book_id, ci, bi, pass_name)
                            ap.parent.mkdir(parents=True, exist_ok=True)
                            tmp = ap.with_name(f"{ap.name}.{os.getpid()}.{threading.get_ident()}.tmp")
                            try:
                                tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
                                os.replace(tmp, ap)
                            finally:
                                try:
                                    tmp.unlink(missing_ok=True)
                                except OSError:
                                    pass
                            pass_status[pass_name] = "success"
                            # 资产相对路径以 ASSETS_ROOT 为基准（不假设 ASSETS_ROOT 在 ROOT_DIR 下，
                            # 兼容测试/自定义目录隔离），供前端按 book_id/ch/batch/pass 定位。
                            try:
                                last_asset = str(ap.relative_to(config.ASSETS_ROOT))
                            except ValueError:
                                last_asset = str(ap)
                    except Exception as exc:  # noqa: BLE001
                        if _record_batch_failure(book_id, book, chapters, genre, ci, bi, done, total_batches, ctx, exc, pass_status):
                            return
                        done += 1
                        continue

                    # 基础拆书成功仍记 success；pass5 失败通过 passes 与整书 partial 状态暴露。
                    with state_store.update_state(book_id) as state:
                        state_store.set_batch_state(state, ci, bi, "success", asset=last_asset, passes=pass_status)
                        if pass5_error:
                            state["last_error"] = pass5_error
                    done += 1
                    _publish(book_id, ci, bi, "success", done, total_batches, ctx)

            # 一趟遍历结束：若仍有 pending（retry_failed 改回来的），再来一轮
            _st = state_store.load_state(book_id)
            _has_pending = any(
                isinstance(v, dict) and v.get("status") == "pending"
                for v in (_st.get("chapter_states") or {}).values())
            if not _has_pending or ctx["stop_flag"].is_set():
                break
            _rescan_rounds += 1
            if _rescan_rounds >= _MAX_RESCAN_ROUNDS:
                _log.warning("重扫已达上限 %d 轮，仍有 pending 批，停止", _MAX_RESCAN_ROUNDS)
                break

        # 统计最终成功/失败批数：若全部失败（0 批成功且存在 failed），绝不伪装成 done！
        final_state = state_store.load_state(book_id)
        ch_states = (final_state.get("chapter_states") or {}).values()
        success_total = sum(1 for v in ch_states if isinstance(v, dict) and v.get("status") == "success")
        failed_total = sum(1 for v in ch_states if isinstance(v, dict) and v.get("status") == "failed")
        degraded_total = sum(
            1 for v in ch_states
            if isinstance(v, dict)
            and isinstance(v.get("passes"), dict)
            and v["passes"].get("pass5_craft") == "failed"
        )
        if failed_total > 0 and success_total == 0:
            err_msg = final_state.get("last_error") or f"全部 {failed_total} 个批次均分析失败"
            with state_store.update_state(book_id) as state:
                state["status"] = "error"
                state["last_error"] = err_msg
            _sync_book_status(book_id, "error")
            broker.publish({
                "book_id": book_id,
                "status": "error",
                "chapter_index": 0,
                "batch_index": 0,
                "done": 0,
                "total": total_batches,
                "message": err_msg,
            })
            return

        # 全部完成（或部分批次成功）：先完成整书资产卡组装与可选报告生成，再置 status="done"，
        # 确保轮询 /api/status 或收到 SSE done 时磁盘与 SQLite 上的卡片及报告已 100% 就绪。
        pre_done_state = state_store.load_state(book_id)
        try:
            _assemble_after_analysis(book_id, genre, chapters, pre_done_state)
        except Exception as exc:  # noqa: BLE001 - 组装失败不改变"分析已完成"的事实
            _log.warning("分析后组装资产失败（批级产物仍完整）: %s", exc)
        if pre_done_state.get("generate_reports"):
            try:
                _generate_reports(
                    book_id,
                    {"title": pre_done_state.get("title") or book.get("title") or book_id},
                )
            except Exception as exc:  # noqa: BLE001
                with state_store.update_state(book_id) as st_err:
                    st_err["report_error"] = str(exc)[:500]

        # 2026-11-23 企业级修正：部分批次失败时不能伪装成 done。
        # 旧实现只要有一批成功就写 status="done"，UI 顶部显示「已完成」，
        # 但 done/total 只有 1/3 且 last_error 仍在——用户会以为拆完了。
        # 现在用独立的 partial 状态，报告/资产仍按成功批次生成。
        final_status = "partial" if failed_total > 0 or degraded_total > 0 else "done"
        with state_store.update_state(book_id) as state:
            state["status"] = final_status
            if failed_total == 0 and degraded_total == 0:
                state.pop("last_error", None)
            else:
                problems = []
                if failed_total:
                    problems.append(f"{failed_total} 个批次分析失败，成功 {success_total} 个")
                if degraded_total:
                    problems.append(f"{degraded_total} 个批次笔法分析失败，基础拆书结果已保留")
                detail = final_state.get("last_error")
                state["last_error"] = "；".join(problems) + (f"；{detail}" if detail else "")
        _sync_book_status(book_id, final_status)
        _publish(book_id, 0, 0, final_status, done, total_batches, ctx)
    except Exception as exc:  # noqa: BLE001
        _log.exception("拆书任务未捕获异常 book_id=%s", book_id)
        err_msg = str(exc)[:500]
        with state_store.update_state(book_id) as state:
            state["status"] = "error"
            state["last_error"] = err_msg
        _sync_book_status(book_id, "error")
        # 必须广播 error 事件（2026-11-05 修）。
        #
        # 原实现只写状态文件、不 publish，而前端（AppContext）只在收到 done
        # 时刷新——于是「未配置模型 / 读盘失败 / 组装异常」这类致命错误发生后，
        # 进度条永远停在「运行中」，用户必须手动刷新页面才能看到 error，
        # 且刷新后也看不到失败原因（/api/status 当时不回传 last_error）。
        #
        # 这里补发一条与 done 同形的事件，前端按既有 done 分支刷新即可收敛。
        broker.publish({
            "book_id": book_id,
            "status": "error",
            "chapter_index": 0,
            "batch_index": 0,
            "done": 0,
            "total": 0,
            "message": err_msg,
        })
    finally:
        # B7：任务结束清理 _runtime 条目，避免内存缓慢增长。
        with _runtime_lock:
            _runtime.pop(book_id, None)


def _sync_book_status(book_id: str, status: str) -> None:
    """把分析任务状态同步进 SQLite ``books`` 表（2026-11-05 新增）。

    ``/api/books`` 的 status 列取自 ``books.status``，而分析完成原先只改状态
    文件——于是拆完的书在书库里永远显示「待拆」。这里在 done / error 时回写。

    尽力而为：库不可用只记日志，不影响分析结果本身。
    """
    try:
        from gui import migrate as _migrate
        book = _books_get(book_id)
        title = (book or {}).get("title") or book_id
        src = (book or {}).get("source_path")
        genre = (book or {}).get("genre")
        with db.tx() as conn:
            _migrate._upsert_book(conn, book_id, title, src, genre, status)
    except Exception as exc:  # noqa: BLE001
        _log.warning("回写 books.status=%s 失败（不影响分析）: %s", status, exc)


def recover_stale_tasks() -> int:
    """启动时回收上次进程遗留的进行中状态（2026-11-05）。

    批次状态 ``running`` 只在当前进程的主循环里被推进成 success/failed。
    进程被杀或崩溃后，落盘的 ``running`` 没有任何代码会再改它：
    前端把该批画成「运行中」直到永远；``retry_failed`` 只收 ``failed``，
    也重试不到它。任务级 ``status=running/paused`` 同理——``resume`` 在内存
    ``_runtime`` 为空时会走 start_analysis，但状态里的 paused 会让前端看起来
    还在暂停中。

    处理：把 ``running`` 批退回 ``pending``（可重跑、断点续传会正常跳过已
    success 的批），任务状态退回 ``idle``。返回修动的任务数。

    只动 running/paused，绝不动 success/failed——failed 留给用户显式重试。
    """
    fixed = 0
    for fp in state_store._iter_state_files():
        # book_id 从文件名推（gui_state_<book_id>.json）——文件内容里的
        # book_id 字段历史数据可能缺失，文件名则一定是对的。
        book_id = _book_id_from_state_file(fp)
        if not book_id:
            continue
        try:
            state = state_store.load_state(book_id)
        except Exception:  # noqa: BLE001
            continue
        if not state:
            continue
        changed = False
        for rec in (state.get("chapter_states") or {}).values():
            if isinstance(rec, dict) and rec.get("status") == "running":
                rec["status"] = "pending"
                changed = True
        if state.get("status") in ("running", "paused"):
            state["status"] = "idle"
            changed = True
        if not changed:
            continue
        try:
            state["book_id"] = book_id
            state_store.save_state(state)
        except Exception as exc:  # noqa: BLE001
            _log.warning("回收任务状态失败 %s: %s", book_id, exc)
            continue
        fixed += 1
    return fixed


def _book_id_from_state_file(fp) -> str:
    """``gui_state_<book_id>.json`` → book_id；不匹配返回空串。"""
    name = fp.name
    prefix, suffix = "gui_state_", ".json"
    if name.startswith(prefix) and name.endswith(suffix):
        return name[len(prefix):-len(suffix)]
    return ""


def _wait_if_paused(ctx: dict[str, Any]) -> None:
    """暂停时阻塞，直到 resume 或 stop。"""
    while ctx["paused"].is_set() and not ctx["stop_flag"].is_set():
        time.sleep(0.2)


def _resume_status_if_paused(book_id: str) -> None:
    """暂停恢复后把落盘状态改回 running（幂等，非 paused 时不动）。

    只在确实处于 paused 时写盘，避免每个批都多一次 state 读写。
    """
    try:
        # 先无锁读判一次，绝大多数批不在 paused 状态，直接返回省掉一次写。
        if state_store.load_state(book_id).get("status") != "paused":
            return
        with state_store.update_state(book_id) as state:
            # 持锁后再判一次：无锁读到 paused 与真正写之间，分析线程可能已推进状态。
            if state.get("status") == "paused":
                state["status"] = "running"
    except Exception as exc:  # noqa: BLE001 - 状态回写失败不阻断分析
        _log.warning("恢复 paused→running 失败（不影响分析继续）: %s", exc)


def _publish(book_id: str, ci: int, bi: int, status: str, done: int, total: int, ctx: dict[str, Any]) -> None:
    broker.publish({
        "book_id": book_id,
        "cursor": state_store.batch_id(ci, bi),
        "chapter_index": ci,
        "batch_index": bi,
        "status": status,
        "done": done,
        "total": total,
    })


def _count_total_batches(chapters: list[Any], batch_size: int) -> int:
    total = 0
    for _, cbody in chapters:
        total += len(engine_adapter.split_batches(cbody, batch_size))
    return total


# ---------------------------------------------------------------------------
# 暂停 / 续传 / 重试
# ---------------------------------------------------------------------------

def pause(book_id: str) -> dict[str, Any]:
    """暂停（当前批完成后停）。"""
    # 与 _get_book_or_raise 同口径：本函数不走那个入口（直接查 _runtime），
    # 故单独校验，否则 {"book_id": ["a"]} 会以 unhashable 变 500。
    if not isinstance(book_id, str):
        raise ServiceError("book_id 必须为字符串", 400)
    ctx = _runtime.get(book_id)
    if ctx is None:
        raise ServiceError("没有运行中的分析任务", 404)
    ctx["paused"].set()
    # ⚠️ 必须走 update_state（原子读改写）：分析线程此时可能正在同一 book_id
    # 上把某批标 success。旧写法先 load 再 save，会用这份旧快照整份覆盖，
    # 把已完成的批抹回初始状态（实测复现见 state_store.update_state 文档）。
    with state_store.update_state(book_id) as state:
        state["status"] = "paused"
    return {"cursor": state.get("cursor", "")}


def resume(book_id: str, genre: str | None = None, model_id: str | None = None) -> dict[str, Any]:
    """从中断批续传（跳过已 success 批，幂等）。"""
    book = _get_book_or_raise(book_id)
    ctx = _runtime.get(book_id)
    if ctx and ctx.get("thread") and ctx["thread"].is_alive():
        # 若处于 paused，则解除暂停继续。
        if ctx["paused"].is_set():
            ctx["paused"].clear()
            # 2026-11-03：立即回写 running，不要等下一批才开始——否则用户点了
            # 「继续」，接口返回 200，但 /api/status 仍是 paused，看上去没反应。
            _resume_status_if_paused(book_id)
            return {"cursor": state_store.load_state(book_id).get("cursor", "")}
        raise ServiceError("分析已在运行中", 409)

    state = state_store.load_state(book_id)
    g = genre or state.get("genre", "unknown")
    mid = model_id or state.get("model_id")
    bs = state.get("batch_size") or config.batch_size_from_env()
    return start_analysis(book_id, g, mid, bs, resume=True)


def retry_failed(book_id: str) -> dict[str, Any]:
    """重试所有失败批（P1）。把失败批状态重置为 pending，再触发续传。"""
    # 先无锁探一次：绝大多数情况下没有失败批，直接返回省掉一次整份状态写。
    _probe = state_store.load_state(book_id).get("chapter_states", {})
    if not any(isinstance(v, dict) and v.get("status") == "failed"
               for v in _probe.values()):
        return {"retried": 0}

    # 线程存活时主循环会按 pending 重扫，不必（也不能）再 resume。
    rt = _runtime.get(book_id)
    alive = bool(rt and rt.get("thread") and rt["thread"].is_alive())

    # ⚠️ 线程已死时，必须在**改状态之前**确认能真的续传（2026-11-05 修）。
    #
    # 原实现先把 failed 改成 pending、再调 resume()。resume() 会做题材校验
    # （未知题材直接 400）、书可用性校验等——一旦它抛错，刚才写下去的 pending
    # 就永久留在状态里：主循环不在跑、没人会重扫，任务状态还是 error。
    # 实测：一批 failed 的书 retry_failed → ServiceError「未知题材 'unknown'」，
    # 批状态停在 pending，用户既看不到进度也无法推进。
    #
    # 现在先试跑续传的**前置校验**，通过后才改状态；改完再真正启动。
    if not alive:
        _precheck_resumable(book_id)

    # 原子改状态：分析线程可能正在同一 book_id 上推进批次，load→save 会覆盖。
    with state_store.update_state(book_id) as state:
        failed = [k for k, v in state.get("chapter_states", {}).items()
                  if isinstance(v, dict) and v.get("status") == "failed"]
        if not failed:
            return {"retried": 0}
        for key in failed:
            state["chapter_states"][key]["status"] = "pending"
    if alive:
        return {"retried": len(failed), "note": "线程运行中，将在当前循环内重扫"}
    try:
        resume(book_id)
    except Exception:
        # 兜底回滚：precheck 之后、真正启动之前仍可能失败（竞态/磁盘等）。
        # 把刚改成 pending 的批退回 failed，避免"卡在 pending 无人处理"。
        with state_store.update_state(book_id) as state:
            for key in failed:
                rec = state.get("chapter_states", {}).get(key)
                if isinstance(rec, dict) and rec.get("status") == "pending":
                    rec["status"] = "failed"
        raise
    return {"retried": len(failed)}


def _precheck_resumable(book_id: str) -> None:
    """续传前置校验：不通过就抛错，**不产生任何状态写入**。

    与 ``resume()`` 里真正启动前的那几项检查同口径（书可用 + 题材合法），
    但不启动线程。抽出来是为了让 ``retry_failed`` 能在改状态前判定。
    """
    _get_book_or_raise(book_id)
    state = state_store.load_state(book_id)
    genre = state.get("genre") or "unknown"
    if not engine_adapter.is_known_genre(genre):
        raise ServiceError(
            f"未知题材 {genre!r}，请从题材列表中选择（GET /api/genres）", 400)



# ---------------------------------------------------------------------------
# 状态查询
# ---------------------------------------------------------------------------

def get_asset(book_id: str, chapter_index: int, batch_index: int, pass_name: str) -> dict[str, Any]:
    """读取某批某个 pass 的资产 JSON 内容。

    pass_name 允许传入任意值，但会做白名单校验以防路径穿越；
    资产不存在时返回空 dict（前端显示「暂无结果」）。
    """
    _get_book_or_raise(book_id)
    if pass_name not in PASS_ORDER:
        raise ServiceError(f"未知 pass: {pass_name}", 400)
    ap = state_store.asset_path(book_id, chapter_index, batch_index, pass_name)
    if not ap.is_file():
        return {}
    try:
        return json.loads(ap.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError) as exc:
        _log.warning(f"pass 资产加载失败，按空结果返回 {ap.name}: {exc}")
        return {}


def get_status(book_id: str | None = None) -> dict[str, Any]:
    """返回 TaskState（含 cursor + chapter_states）。

    优先从 ``state_store.load_task``（SQLite 权威 + JSON 降级）读取，保证进程重启后
    仍可恢复 cursor/batch_state（W08 验收点）。
    """
    if not book_id:
        # 返回第一个已导入的书，或空状态。
        with _books_lock:
            if not _BOOKS:
                return {"book_id": None, "status": "idle", "cursor": "", "done": 0, "total": 0}
            book_id = next(reversed(_BOOKS))  # 最近使用的

    state = state_store.load_task(book_id)
    book = _books_get(book_id)
    total = 0
    if book:
        total = _count_total_batches(book["chapters"], state.get("batch_size") or config.batch_size_from_env())
    done = sum(
        1 for v in state.get("chapter_states", {}).values()
        if isinstance(v, dict) and v.get("status") == "success"
    )
    return {
        "book_id": book_id,
        "status": state.get("status", "idle"),
        "cursor": state.get("cursor", ""),
        "done": done,
        "total": total,
        "chapter_states": state.get("chapter_states", {}),
        "asset_index": state.get("asset_index", {}),
        # 失败原因（2026-11-05）：load_task 早就带了 last_error，但这里从没往外传，
        # 于是用户只能看到 status="error"，不知道错在哪。
        "last_error": state.get("last_error") or "",
        # 报告生成失败原因（2026-11-05）：铁律二未过 / 组装异常时写进状态文件的
        # report_error 从没有 API 出口——前端即使想显示也拿不到。
        "report_error": state.get("report_error") or "",
        "takeover_guide_path": state.get("takeover_guide_path") or "",
    }


def offline_analyze_book(book_id: str, genre: str = "unknown") -> dict[str, Any]:
    """无外部 LLM 时的纯离线量化拆解 + 采样切片 + AI 接管任务包生成。"""
    book = _get_book_or_raise(book_id)
    g = (genre or "").strip() or "unknown"
    if g != "unknown" and not engine_adapter.is_known_genre(g):
        raise ServiceError(f"未知题材: {g!r}", 400)
    res = engine_adapter.run_offline_analysis(
        book_id,
        book.get("title") or book_id,
        book.get("chapters") or [],
        g,
        reason="用户在 GUI 触发离线量化拆解与 AI 接管任务生成",
    )
    with state_store.update_state(book_id) as state:
        state["genre"] = g
        state["takeover_guide_path"] = res.get("guide_path") or ""
    return res


_TAKEOVER_HEADER = (
    "请严格按以下要求分析小说采样切片，最终仅输出一个合法的 JSON 对象"
    "（可使用 ```json 代码块包裹，切勿省略结构字段，严禁连续摘抄原文超过 11 字）。"
)


def _validate_safe_book_id(book_id: Any) -> str:
    """校验 book_id 安全性（拒绝非字符串、空值与任何路径穿越字符）。"""
    if not isinstance(book_id, str):
        raise ServiceError("book_id 必须为字符串", 400)
    bid = book_id.strip()
    if not bid or any(ch in bid for ch in ("/", "\\", "..", ":", "\x00", "\n", "\r")):
        raise ServiceError(f"非法 book_id: {book_id!r}", 400)
    probe = (config.CORPUS_DIR / "raw" / bid).resolve()
    if not probe.is_relative_to(config.CORPUS_DIR.resolve()):
        raise ServiceError(f"非法 book_id: {book_id!r}", 400)
    return bid


def _load_takeover_prompt_markdown(pass_name: str) -> str:
    """读取 prompts/<pass_name>.md 原文（优先 PROMPTS_DIR 定制覆盖，回退仓库 prompts/）。"""
    candidates = [
        config.PROMPTS_DIR / f"{pass_name}.md",
        config.PROMPTS_DIR.parent / f"{pass_name}.md",
        config.ROOT_DIR / "prompts" / f"{pass_name}.md",
    ]
    for fp in candidates:
        if fp.is_file():
            try:
                return fp.read_text(encoding="utf-8-sig").strip()
            except OSError as exc:
                _log.warning("读取 prompt 模板失败 %s: %s", fp, exc)
    sys_prompt, usr_prompt = engine_adapter.load_prompt(pass_name)
    return f"## SYSTEM\n{sys_prompt}\n\n## USER\n{usr_prompt}"


def _compact_metrics_json(metrics: dict[str, Any]) -> str:
    """提炼紧凑版全书量化指标 JSON，防止大体积统计明细撑爆 Web-AI 上下文。"""
    if not isinstance(metrics, dict) or not metrics:
        return "{}"
    keep_keys = (
        "total_chars",
        "total_words_est",
        "chapter_count",
        "sentence_count",
        "avg_sentence_len",
        "short_ratio",
        "long_ratio",
        "paragraph_count",
        "dialogue_ratio",
        "char_ttr",
        "exclaim_ratio",
        "sensory",
    )
    compact: dict[str, Any] = {k: metrics[k] for k in keep_keys if k in metrics}
    if isinstance(metrics.get("top_bigrams"), list):
        compact["top_bigrams"] = metrics["top_bigrams"][:10]
    return json.dumps(compact, ensure_ascii=False)


def get_takeover_bundle(book_id: str, pass_name: str | None = None) -> dict[str, Any]:
    """获取离线 Web-AI 拆书接管状态总览，或生成指定 Pass 的完整一键复制 Prompt 包。"""
    bid = _validate_safe_book_id(book_id)
    sampled_fp = config.CORPUS_DIR / "sampled" / bid / "slices.json"
    raw_dir = config.CORPUS_DIR / "raw" / bid

    if not pass_name:
        passes_info: list[dict[str, Any]] = []
        for p_key, p_label in TAKEOVER_PASSES:
            rfp = raw_dir / f"{p_key}.json"
            if rfp.is_file():
                st = rfp.stat()
                passes_info.append({
                    "pass_name": p_key,
                    "label": p_label,
                    "saved": True,
                    "size_bytes": st.st_size,
                    "updated_at": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                })
            else:
                passes_info.append({
                    "pass_name": p_key,
                    "label": p_label,
                    "saved": False,
                    "size_bytes": 0,
                    "updated_at": None,
                })
        assembled_cards = [
            fname
            for fname in (
                f"{bid}-voice-card.json",
                f"{bid}-structure-obs.json",
                f"{bid}-commercial-obs.json",
                f"{bid}-craft-card.json",
            )
            if (config.ASSETS_ROOT / fname).is_file()
        ]
        reports = [
            f"report:{rname}"
            for rname in (f"{bid}-拆书报告", f"{bid}-笔法分析")
            if (config.REPORTS_DIR / f"{rname}.md").is_file()
        ]
        return {
            "book_id": bid,
            "sampled_ready": sampled_fp.is_file(),
            "passes": passes_info,
            "assembled_cards": assembled_cards,
            "reports": reports,
        }

    if not isinstance(pass_name, str) or pass_name.strip() not in _TAKEOVER_PASS_MAP:
        raise ServiceError(
            f"未知 pass_name: {pass_name!r}，允许值为 {list(_TAKEOVER_PASS_MAP)}",
            400,
        )
    p = pass_name.strip()

    if not sampled_fp.is_file():
        offline_analyze_book(bid)

    try:
        slices = json.loads(sampled_fp.read_text(encoding="utf-8-sig")) if sampled_fp.is_file() else {}
    except (json.JSONDecodeError, OSError) as exc:
        raise ServiceError(f"采样切片读取失败: {exc}", 500) from exc

    metrics_fp = config.CORPUS_DIR / "metrics" / f"{bid}.json"
    metrics: dict[str, Any] = {}
    if metrics_fp.is_file():
        try:
            loaded_m = json.loads(metrics_fp.read_text(encoding="utf-8-sig"))
            if isinstance(loaded_m, dict):
                metrics = loaded_m
        except (json.JSONDecodeError, OSError) as exc:
            _log.warning("读取量化指标失败 %s: %s", metrics_fp.name, exc)

    prompt_md = _load_takeover_prompt_markdown(p)
    compact_metrics = _compact_metrics_json(metrics)
    book_mem = _books_get(bid)
    slice_text = engine_adapter.build_takeover_slice_text(
        p,
        slices if isinstance(slices, dict) else {},
        metrics,
        chapters=(book_mem or {}).get("chapters"),
        max_chars=40000,
    )
    bundle = (
        f"{_TAKEOVER_HEADER}\n\n"
        f"# 分析规范与输出 Schema（{p}）\n\n{prompt_md}\n\n"
        f"# 全书量化统计指标\n\n```json\n{compact_metrics}\n```\n\n"
        f"# 小说采样切片内容\n\n{slice_text}\n"
    )

    raw_fp = raw_dir / f"{p}.json"
    existing_text = ""
    if raw_fp.is_file():
        try:
            existing_text = raw_fp.read_text(encoding="utf-8-sig")
        except OSError as exc:
            _log.warning("读取已存 pass JSON 失败 %s: %s", raw_fp, exc)

    return {
        "book_id": bid,
        "pass_name": p,
        "prompt_bundle": bundle,
        "char_count": len(bundle),
        "saved": raw_fp.is_file(),
        "existing_json": existing_text,
    }


def save_takeover_pass(book_id: str, pass_name: Any, content: Any) -> dict[str, Any]:
    """校验并原子保存用户在 Web-AI 生成的 Pass JSON 回复至 corpus/raw/<book_id>/<pass_name>.json。"""
    bid = _validate_safe_book_id(book_id)
    if not isinstance(pass_name, str) or pass_name.strip() not in _TAKEOVER_PASS_MAP:
        raise ServiceError(
            f"未知 pass_name: {pass_name!r}，允许值为 {list(_TAKEOVER_PASS_MAP)}",
            400,
        )
    p = pass_name.strip()

    parsed: dict[str, Any] | None = None
    if isinstance(content, dict):
        parsed = content
    elif isinstance(content, str) and content.strip():
        try:
            extracted = engine_adapter.extract_json(content)
            if isinstance(extracted, dict):
                parsed = extracted
        except (ValueError, TypeError) as exc:
            raise ServiceError(
                "无法从内容中解析出合法 JSON 对象，请粘贴完整的 AI JSON 回复",
                400,
            ) from exc
    else:
        raise ServiceError("content 必须为非空字符串或 JSON 对象", 400)

    if not isinstance(parsed, dict) or not parsed:
        raise ServiceError(
            "无法从内容中解析出合法 JSON 对象，请粘贴完整的 AI JSON 回复（不允许空对象 {}）",
            400,
        )

    raw_dir = config.CORPUS_DIR / "raw" / bid
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_fp = raw_dir / f"{p}.json"
    tmp_fp = raw_fp.with_name(f"{raw_fp.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp_fp.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_fp, raw_fp)

    return {
        "book_id": bid,
        "pass_name": p,
        "saved_path": str(raw_fp),
        "keys": list(parsed.keys()),
        "size_bytes": raw_fp.stat().st_size,
    }


def generate_book_reports(
    book_id: str,
    genre: str | None = None,
    assemble: bool | None = None,
) -> dict[str, Any]:
    """纯离线组装四维资产并生成双份万字报告（无需配置任何外部 LLM 模型，不要求 _BOOKS 驻留内存）。"""
    bid = _validate_safe_book_id(book_id)
    if genre is not None and not isinstance(genre, str):
        raise ServiceError("genre 必须为字符串", 400)
    if assemble is not None and not isinstance(assemble, bool):
        raise ServiceError("assemble 必须为布尔值", 400)

    raw_dir = config.CORPUS_DIR / "raw" / bid
    has_raw = raw_dir.is_dir() and any(raw_dir.glob("pass*.json"))
    batch_dir = config.ASSETS_ROOT / bid
    has_batches = batch_dir.is_dir() and any(batch_dir.glob("c*-b*-pass*.json"))

    existing_voice = _load_assembled_card(bid, "voice")
    existing_struct = _load_assembled_card(bid, "structure")
    existing_comm = _load_assembled_card(bid, "commercial")
    existing_craft = _load_assembled_card(bid, "craft")
    has_cards = bool(existing_voice or existing_struct or existing_comm or existing_craft)

    db_rows: list[dict[str, Any]] = []
    try:
        if db._db_ready():
            db_rows = db.get_books(book_id=bid)
    except Exception as exc:  # noqa: BLE001
        _log.debug("generate_book_reports 查询 books 表跳过 %s: %s", bid, exc)

    st_loaded = state_store.load_state(bid)
    mem_book = _books_get(bid)
    if not (has_raw or has_batches or has_cards or db_rows or st_loaded.get("title") or mem_book):
        raise ServiceError(f"未找到书籍或拆书产物: {bid}", 404)

    body_genre = (genre or "").strip()
    if body_genre and len(body_genre) < 2:
        raise ServiceError(f"genre 长度过短: {body_genre!r}", 400)
    resolved_genre = (
        body_genre
        or (str(db_rows[0].get("genre") or "").strip() if db_rows else "")
        or str(st_loaded.get("genre") or "").strip()
        or str((existing_voice.get("meta") or {}).get("genre") or "").strip()
        or str((existing_craft.get("meta") or {}).get("genre") or "").strip()
        or str((existing_struct.get("meta") or {}).get("genre") or "").strip()
        or "unknown"
    )
    if len(resolved_genre) < 2:
        resolved_genre = "unknown"

    should_assemble = assemble if assemble is not None else bool(has_raw or has_batches)
    assembled_list: list[str] = []
    if should_assemble:
        if has_raw and (raw_dir / "pass1_structure.json").is_file():
            from gui import writing_service

            asm_res = writing_service.assemble(bid, resolved_genre)
            assembled_list = list(asm_res.get("written") or [])
        elif has_batches:
            assembled_list = _assemble_after_analysis(
                bid,
                resolved_genre,
                (mem_book or {}).get("chapters") or [],
                st_loaded,
            )

    voice_now = _load_assembled_card(bid, "voice")
    craft_now = _load_assembled_card(bid, "craft")
    resolved_title = (
        (voice_now.get("meta") or {}).get("source_title")
        or (craft_now.get("meta") or {}).get("source_title")
        or (db_rows[0].get("title") if db_rows else None)
        or st_loaded.get("title")
        or (mem_book or {}).get("title")
        or bid
    )

    with state_store.update_state(bid) as st_clear:
        st_clear.pop("report_error", None)

    _generate_reports(bid, {"title": resolved_title})

    st_after = state_store.load_state(bid)
    err_str = str(st_after.get("report_error") or "")
    generated_ids = [
        f"report:{rname}"
        for rname in (f"{bid}-拆书报告", f"{bid}-笔法分析")
        if (config.REPORTS_DIR / f"{rname}.md").is_file()
    ]
    total_chars = 0
    if generated_ids:
        chk = engine_adapter.check_report_min_length(config.REPORTS_DIR, bid)
        total_chars = int(chk.get("total", 0))
    report_ok = bool(generated_ids) and not err_str

    return {
        "book_id": bid,
        "assembled": assembled_list,
        "reports": generated_ids,
        "report_ok": report_ok,
        "report_error": err_str,
        "total_chars": total_chars,
    }


# ---------------------------------------------------------------------------
# 阶段一：概览 / 资产 / 报告 / 拆书结果 / 一键分析
# ---------------------------------------------------------------------------

def get_overview() -> dict[str, Any]:
    """首页概览聚合：SQL 聚合计数 + 已拆书本数 + 模型状态。"""
    ov = asset_index.index.get_overview()
    # 2026-11-23：`total_books` 在首页的标签是「已拆书」，必须只数真正分析完成的
    # 书（status=done），不能回退成「导入过但从未分析」的书——旧实现无 done 书时
    # 用 state_store 全量列表兜底，首页会显示「已拆书 2」而实际一本都没拆。
    done_books = db.get_books(status="done")
    ov["total_books"] = len(done_books)
    try:
        ov["total_imported_books"] = len(db.get_books())
    except Exception:  # noqa: BLE001
        ov["total_imported_books"] = 0
    # 2026-11-23：首页「使用旅程」第 3 步需要真实的写作/质检信号。
    # 旧判据只看资产数——内置资产 138 张，拆完一本书就让「写一章并质检」自动打勾。
    try:
        ov["total_writing_chapters"] = sum(
            1 for _ in config.NOVEL_DIR.rglob("chapter-*.txt")
        ) if config.NOVEL_DIR.is_dir() else 0
    except OSError:
        ov["total_writing_chapters"] = 0
    try:
        qc_dir = config.REPORTS_DIR / "qc"
        ov["total_qc_reports"] = sum(1 for _ in qc_dir.glob("*-qc.json")) if qc_dir.is_dir() else 0
    except OSError:
        ov["total_qc_reports"] = 0
    # 2026-11-23：首页「最近动态」此前后端恒返回 []，区块永远不出现。
    # 用 books 表的 updated_at 派生最近 5 条真实动态（不再需要独立活动日志表）。
    try:
        _status_cn = {
            "done": "已完成拆书", "error": "拆书失败", "running": "拆解中",
            "paused": "已暂停", "partial": "部分完成", "ready": "已导入", "idle": "待拆",
        }
        recent = []
        for b in sorted(db.get_books(), key=lambda r: r.get("updated_at") or "",
                        reverse=True)[:5]:
            title = b.get("title") or b.get("book_id")
            recent.append(f"《{title}》 · {_status_cn.get(b.get('status') or '', b.get('status') or '')}")
        ov["recent_activity"] = recent
    except Exception:  # noqa: BLE001
        ov["recent_activity"] = []
    ov["model_configured"] = engine_adapter.any_model_configured()
    ov["model_ready"] = engine_adapter.any_model_ready()
    return ov


def list_assets(kind: str | None = None, genre: str | None = None,
                book_id: str | None = None, offset: int = 0,
                limit: int | None = None) -> dict[str, Any]:
    """资产清单分页（kind/genre/book_id 可选组合筛选）。

    ``limit=None`` = 返回全部（asset_index 内部有 500 硬上限）。
    2026-10-29：默认值从 50 改为 None —— 分页是调用方的显式选择，
    默认截断会让不传 limit 的调用方静默丢数据（管理后台资产列表即如此）。
    """
    try:
        return asset_index.index.list_assets(kind, genre, book_id, offset, limit)
    except ValueError as exc:
        raise ServiceError(str(exc), 400) from exc


def get_asset_detail(kind: str, asset_id: str) -> dict[str, Any]:
    """资产详情（只读，白名单校验）。"""
    try:
        return asset_index.index.get_asset_detail(kind, asset_id)
    except ValueError as exc:
        raise ServiceError(str(exc), 400) from exc
    except KeyError as exc:
        raise ServiceError(str(exc), 404) from exc


def list_tropes() -> dict[str, Any]:
    """桥段库清单（只读）：直接读 ``config.ASSETS_ROOT/trope-library.json``。

    不走 ``/api/assets?kind=trope`` 通道：该文件在目录扫描中不被归类为
    trope kind（见 ``_SUFFIX_KIND``），且 SQLite 迁移状态因环境而异；
    桥段库是内置只读数据，直读文件最可靠。

    2026-10-12：改走 ``_load_library`` 的指纹缓存。该文件 411KB、解析 3.07ms，
    是其余内置库的 20 倍——每次请求重解析是 /api/tropes 的主要开销。
    """
    fp = config.ASSETS_ROOT / "trope-library.json"
    if not fp.is_file():
        raise ServiceError("桥段库文件不存在（assets/trope-library.json）", 404)
    data = _load_library("trope-library.json")
    tropes = data.get("tropes") if isinstance(data, dict) else None
    if not isinstance(tropes, list):
        raise ServiceError("桥段库格式错误：缺少 tropes 数组", 500)
    return {"total_count": len(tropes), "tropes": tropes}


def list_reports() -> list[dict[str, Any]]:
    """报告清单（拆书报告 + 笔法分析），合并 SQLite 记录与磁盘 reports/*.md，确保双端零漂移。"""
    rows = db.list_reports()
    out: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for r in rows:
        path = r.get("path", "")
        stem = Path(path).stem if path else r.get("title", "")
        if not stem:
            continue
        rid = f"report:{stem}"
        seen_ids.add(rid)
        disk_fp = config.REPORTS_DIR / f"{stem}.md"
        sz: int | None = None
        if disk_fp.is_file():
            try:
                sz = disk_fp.stat().st_size
            except OSError:
                sz = None
        out.append({
            "id": rid,
            "name": stem,
            "kind": r.get("type", "book"),
            "book_id": r.get("book_id", ""),
            "size": sz,
        })

    if config.REPORTS_DIR.is_dir():
        for fp in sorted(config.REPORTS_DIR.glob("*.md")):
            if not fp.is_file():
                continue
            rid = f"report:{fp.stem}"
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            rtype = "book"
            bid = fp.stem
            if fp.name.endswith("-笔法分析.md"):
                rtype = "craft"
                bid = fp.name[: -len("-笔法分析.md")]
            elif fp.name.endswith("-拆书报告.md"):
                rtype = "book"
                bid = fp.name[: -len("-拆书报告.md")]
            try:
                sz = fp.stat().st_size
            except OSError:
                sz = None
            out.append({
                "id": rid,
                "name": fp.stem,
                "kind": rtype,
                "book_id": bid,
                "size": sz,
            })

    if out:
        return out

    # 回退扫描（迁移前）。
    items = [it for it in asset_index.index.scan()["items"] if it["kind"] == "report"]
    for it in items:
        out.append({
            "id": it["id"],
            "name": it["name"],
            "kind": it.get("report_kind", "book"),
            "book_id": it.get("book_id", ""),
            "size": it["size"],
        })
    return out


def get_stats() -> dict[str, Any]:
    """关系统计（P1）：书→资产/报告计数、题材→卡片计数、kind 分布。

    返回结构：
    {
        "books": [{book_id, title, status, asset_count, report_count}, ...],
        "genres": [{genre, asset_count}, ...],
        "by_kind": {kind: count},
        "totals": {books, assets, reports},
    }
    """
    books = db.get_books()
    ready = db._db_ready()
    if not ready:
        # 库未就绪：回退目录扫描（兼容迁移前的旧测试/环境）。
        books = []
        totals = {"books": 0, "assets": 0, "reports": 0}
    else:
        conn = db.get_conn()
        totals = {
            "books": len(books),
            "assets": conn.execute("SELECT COUNT(*) AS n FROM assets").fetchone()["n"],
            "reports": conn.execute("SELECT COUNT(*) AS n FROM reports").fetchone()["n"],
        }

    book_stats = []
    if ready:
        conn = db.get_conn()
        for b in books:
            bid = b["book_id"]
            n_assets = conn.execute("SELECT COUNT(*) AS n FROM assets WHERE book_id = ?", (bid,)).fetchone()["n"]
            n_reports = conn.execute("SELECT COUNT(*) AS n FROM reports WHERE book_id = ?", (bid,)).fetchone()["n"]
            book_stats.append({
                "book_id": bid,
                "title": b.get("title", bid),
                "status": b.get("status", "idle"),
                "genre": b.get("genre"),
                "asset_count": n_assets,
                "report_count": n_reports,
            })
        genre_rows = conn.execute(
            "SELECT genre, COUNT(*) AS n FROM assets WHERE genre IS NOT NULL AND genre != '' "
            "GROUP BY genre ORDER BY n DESC"
        ).fetchall()
        genres = [{"genre": r["genre"], "asset_count": r["n"]} for r in genre_rows]
    else:
        genres = []

    # M7：by_kind 与 totals 共用同一就绪判据，避免空库中间态下数字打架。
    by_kind = asset_index.index.count_by_kind() if ready else {}
    return {"books": book_stats, "genres": genres, "by_kind": by_kind, "totals": totals}


def get_report(report_id: str) -> dict[str, Any]:
    """报告 Markdown 原文（前端 react-markdown 渲染）。"""
    # report_id 形如 ``report:<name>``。
    try:
        detail = asset_index.index.get_asset_detail("report", report_id)
    except (ValueError, KeyError) as exc:
        raise ServiceError(str(exc), 404) from exc
    return {"id": report_id, "name": detail["name"], "markdown": detail["markdown"]}


def _load_assembled_card(book_id: str, card_type: str) -> dict[str, Any]:
    """从 assets/{book_id}/ 或 assets/ 根目录定位**单书基础组装卡**。

    阶段一沿用旧 DESIGN A6：整书跑完统一组装，命名 ``{book_id}-{card_type}.json``，
    落在 assets/ 根目录下（当前资产落盘即 assets/ 根目录）；若缺失返回空 dict 降级。

    只认基础卡后缀：``*-distilled.json`` 是**跨书题材蒸馏产物**（无单书归属，
    kind=distilled），不得作为单书基础卡 fallback 返回；需要蒸馏结果时由
    writing inject 的显式 ``distilled`` 参数加载（见 writing_service）。
    """
    mapping = {
        "voice": "voice-card",
        "structure": "structure-obs",
        "commercial": "commercial-obs",
        "craft": "craft-card",
    }
    suffix = mapping.get(card_type)
    if suffix is None:
        return {}
    # 候选名：先按 GUI 的 book_id（`{书名}-{hash}`），再按 CLI 的裸书名。
    #
    # 2026-11-04：GUI 的 book_id 由 `book_id_from_title` 生成，形如
    # ``我的书-4519bf2c``；而 CLI 拆书（pipeline / assemble / batch）落盘用的是
    # 纯书名 ``我的书-voice-card.json``。两套命名空间并存，导致 GUI 导入一本
    # CLI 已经拆完的书后，结果页资产全空——不是没拆，是名字对不上。
    # 回退时用 book_id 去掉末尾 ``-{8位hex}`` 得到书名。
    names = [f"{book_id}-{suffix}.json"]
    m = re.match(r"^(?P<title>.+)-[0-9a-f]{8}$", book_id)
    if m:
        names.append(f"{m.group('title')}-{suffix}.json")
    # 优先 assets/{book_id}/ 子目录，其次 assets/ 根目录。
    for d in (config.ASSETS_ROOT / book_id, config.ASSETS_ROOT):
        for fname in names:
            fp = d / fname
            if fp.is_file():
                try:
                    return json.loads(fp.read_text(encoding="utf-8-sig"))
                except (json.JSONDecodeError, OSError) as exc:
                    _log.warning(f"资产卡加载失败 {fp.name}: {exc}")
                    continue
    return {}


def get_book_results(book_id: str) -> dict[str, Any]:
    """某书拆书结构化结果（组装卡 + 章节打分 + 报告关联）。

    阶段一：voice-card/structure/commercial 缺失时降级返回批级 pass 原始 JSON 聚合
    （见 DESIGN §8 D1）；章节打分为空列表（打分属阶段二 consistency，见 D2）。

    安全：book_id 直接拼文件路径，必须先校验存在性（防 ../ 路径穿越）。
    """
    _get_book_or_raise(book_id)
    voice = _load_assembled_card(book_id, "voice")
    structure = _load_assembled_card(book_id, "structure")
    commercial = _load_assembled_card(book_id, "commercial")
    craft = _load_assembled_card(book_id, "craft")

    title = (voice.get("meta") or {}).get("source_title", book_id)

    # 报告关联：reports 目录下 `<stem>-拆书报告.md` / `<stem>-笔法分析.md`。
    # 2026-11-23：CLI/迁移产出的报告以**书名**为 stem，GUI 以 book_id 为 stem；
    # 旧实现只认 book_id，迁移书的报告明明存在却显示「暂无报告」。
    report_ids = []
    stems = [book_id]
    if title and title != book_id:
        stems.append(str(title))
    for stem in stems:
        for suffix in ("拆书报告", "笔法分析"):
            name = f"{stem}-{suffix}"
            if (config.REPORTS_DIR / f"{name}.md").is_file():
                rid = f"report:{name}"
                if rid not in report_ids:
                    report_ids.append(rid)

    return {
        "book_id": book_id,
        "title": title,
        "voice_card": voice,
        "structure": structure,
        "commercial": commercial,
        "craft_card": craft,
        "chapter_scores": _collect_chapter_scores(book_id, voice),
        "report_ids": report_ids,
    }


def _collect_chapter_scores(book_id: str, voice: dict[str, Any]) -> list[dict[str, Any]]:
    """章节打分（阶段一尽力而为）。

    若组装卡含一致性相关分数则提取；否则扫描批级 pass 结果 JSON，尝试读取内嵌的
    一致性/质量分。阶段一通常返回空列表（打分属阶段二）。
    """
    scores: list[dict[str, Any]] = []
    assets_dir = config.ASSETS_ROOT / book_id
    if not assets_dir.is_dir():
        return scores
    # 扫描批级 pass JSON，按章节聚合（尽力而为提取 quality/consistency 字段）。
    seen: dict[int, dict[str, Any]] = {}
    for fp in sorted(assets_dir.glob("c*-b*-pass*.json")):
        # 文件名形如 c{ch}-b{bi}-{pass}.json。
        stem = fp.stem  # e.g. c3-b2-pass1_structure
        try:
            ch_str = stem.split("-b")[0][1:]  # 去掉前缀 'c'
            chapter_index = int(ch_str)
        except (ValueError, IndexError):
            continue
        try:
            data = json.loads(fp.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError) as exc:
            _log.warning(f"跳过无法解析的批状态 {fp.name}: {exc}")
            continue
        if not isinstance(data, dict):
            continue
        entry = seen.setdefault(chapter_index, {"chapter_index": chapter_index,
                                                "title": f"第{chapter_index}章",
                                                "consistency": 0.0, "quality": 0.0})
        # 尽力提取分数。
        for key in ("consistency", "consistency_score", "score"):
            if isinstance(data.get(key), (int, float)):
                entry["consistency"] = float(data[key])
        for key in ("quality", "quality_score"):
            if isinstance(data.get(key), (int, float)):
                entry["quality"] = float(data[key])
    if seen:
        scores = [seen[k] for k in sorted(seen)]
    return scores


def get_book_scores(book_id: str) -> list[dict[str, Any]]:
    """章节打分数据（供章节打分对比图）。"""
    return get_book_results(book_id)["chapter_scores"]


def run_full_analysis(book_id: str, genre: str, model_id: str | None = None) -> dict[str, Any]:
    """一键「分析」：拆书 + 拆书报告 + 笔法报告串联。

    在 ``state_store`` 中持久化 ``generate_reports=True``，由 ``_run_analysis`` 在
    ``_assemble_after_analysis`` 完成后直接同步生成报告（既不启动 24 小时轮询线程钉死
    百兆级 ``book`` 内存，也能在 ``pause/resume`` 或 ``retry_failed`` 后可靠续接报告生成）。
    """
    _get_book_or_raise(book_id)
    if not engine_adapter.any_model_configured():
        raise ServiceError("未配置外部模型，请先运行 model_config.py 配置", 400)

    return start_analysis(book_id, genre, model_id, generate_reports=True)


def _schedule_report_generation(book_id: str, book: dict[str, Any] | None = None) -> None:
    """兼容包装：标记 ``generate_reports=True``，若任务已处于 done 则立即触发报告生成。

    已废弃旧版 24 小时轮询守护线程，避免闭包长期持有完整 ``book`` 正文字典造成内存泄漏。
    """
    title_hint = str((book or {}).get("title") or book_id)
    with state_store.update_state(book_id) as st:
        st["generate_reports"] = True
        is_done = st.get("status") == "done"
    if is_done:
        try:
            _generate_reports(book_id, {"title": title_hint})
        except Exception as exc:  # noqa: BLE001
            with state_store.update_state(book_id) as st_err:
                st_err["report_error"] = str(exc)[:500]


def _generate_reports(book_id: str, book: dict[str, Any]) -> None:
    """组装拆书报告 + 笔法报告，**校验通过后**写 reports/{book_id}-*.md，并 invalidate 资产索引。

    报告生成串行化：前后两轮一键分析的 _watch 线程可能同时观察到 done，
    并发写同一报告文件（write_text 非原子，会交错损坏）；此处持锁串行。
    """
    with _report_gen_lock:
        _generate_reports_inner(book_id, book)


def _assemble_after_analysis(book_id: str, genre: str,
                             chapters: list, state: dict[str, Any]) -> list[str]:
    """分析完成后把批级 pass 文件组装成整书资产卡（2026-11-04 新增）。

    背景：GUI 分析只落批级 ``assets/{book_id}/cN-bM-passK.json``，
    而 ``get_book_results`` / ``_generate_reports_inner`` 读的是整书卡
    ``assets/{book_id}-voice-card.json`` 这类——此前**没有任何代码生成它们**，
    于是结果页资产全空、报告 0 字、铁律二必然判失败，且用户只看到「分析完成」。

    做法：按章节/批次顺序把批级 pass 结果合并成一份"整书 pass"，再走与 CLI
    相同的 normalize + assemble 路径，落盘并立即重索引。

    2026-11-23：GUI 已补齐 pass5_craft，与 CLI 一致生成 craft-card 与笔法报告。
    """
    import json as _json

    def _merge(pass_name: str) -> dict[str, Any]:
        """按 cN-bM 顺序把同 pass 的批级结果合并成一份整书 pass 输出。

        ⚠️ 同一个键在不同批次里可能是 **list 也可能是 dict**（2026-11-05 修）：
        模型有时写 ``{"characters": {"唐雨": {...}}}``，有时写
        ``{"characters": [{"name": "边炀"}]}``。原实现先收集 lists、再用
        ``merged.update(lists)`` 覆盖——实测前一批的唐雨整个消失，只剩边炀。

        现在按"统一折算成 list"处理：dict 形态先转成 ``[{name: key, **v}]``
        （与 normalize_pass2 对容器键的处理一致），再按 name 去重合并。
        """
        base = config.ASSETS_ROOT / book_id
        if not base.is_dir():
            return {}
        merged: dict[str, Any] = {}
        lists: dict[str, list] = {}
        dict_lists: dict[str, list] = {}

        def _as_items(key: str, val: Any) -> list | None:
            """把值折算成可合并的 list；不是列表语义时返回 None。

            ⚠️ 只有 **dict-of-dict / dict-of-str**（容器键形态，如
            ``{"唐雨": {...}}``）才折算成 ``[{name: 唐雨, ...}]``。
            普通 list 原样返回——``banned.words`` 是字符串列表，
            把它包装成 ``{"name": "不禁"}`` 会让校验器报"条目应为非空字符串"。
            """
            if isinstance(val, list):
                return list(val)
            if isinstance(val, dict):
                # 只有当**所有**值都是 dict/str 时才视为"以角色名/条目名为键的容器"
                if not val or not all(isinstance(b, (dict, str)) for b in val.values()):
                    return None
                out = []
                for name, body in val.items():
                    if isinstance(body, dict):
                        item = dict(body)
                        item.setdefault("name", name)
                        out.append(item)
                    elif isinstance(body, str):
                        out.append({"name": name, "value": body})
                    else:
                        out.append({"name": name})
                return out if out else None
            return None

        records = state.get("chapter_states")
        candidates: list[Path] = []
        if isinstance(records, dict):
            for key, rec in records.items():
                if not isinstance(rec, dict) or rec.get("status") != "success":
                    continue
                parsed = state_store.parse_cursor(key)
                if not parsed:
                    continue
                pass_states = rec.get("passes")
                if isinstance(pass_states, dict) and pass_states.get(pass_name) != "success":
                    continue
                fp = state_store.asset_path(book_id, parsed[0], parsed[1], pass_name)
                if fp.is_file():
                    candidates.append(fp)
        else:
            # 兼容直接调用组装的旧测试/迁移工具；生产状态始终带 chapter_states。
            candidates = list(base.glob(f"c*-b*-{pass_name}.json"))

        for fp in sorted(candidates, key=lambda p: _batch_sort_key(p.name)):
            try:
                part = _json.loads(fp.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError):
                continue
            if not isinstance(part, dict):
                continue
            for k, v in part.items():
                if k in _MERGE_SKIP_KEYS:
                    continue
                items = _as_items(k, v)
                if items is not None:
                    dict_lists.setdefault(k, []).extend(items)
                elif isinstance(v, dict):
                    merged.setdefault(k, {}).update(v)
                else:
                    merged.setdefault(k, v)

        # 列表型键：按 name 去重（同名保留先出现的，后续只补缺字段）
        for k, items in dict_lists.items():
            deduped: list[Any] = []
            index: dict[str, int] = {}
            for item in items:
                name = item.get("name") if isinstance(item, dict) else None
                if isinstance(name, str) and name in index:
                    existing = deduped[index[name]]
                    if isinstance(existing, dict):
                        for kk, vv in item.items():
                            existing.setdefault(kk, vv)
                    continue
                if isinstance(name, str):
                    index[name] = len(deduped)
                deduped.append(item)
            lists[k] = deduped
        merged.update(lists)
        # 丢掉空值：纯拒答批次合并后只剩 {"characters": []}，而这个 dict
        # 在布尔上是 True——上层 ``if pass2 or pass3`` 仍会成立并产出空壳卡。
        return {k: v for k, v in merged.items() if v not in (None, "", [], {})}

    written: list[str] = []
    title = state.get("title") or book_id
    # ⚠️ manifest 必须带 selected_indices / selected_count，否则
    # assemble_voice_card 会产出一张 ``sample_chapters: []`` 的卡——
    # validate_voice_card 对 sample_chapters 要求至少 3 项，校验必失败，
    # _write 静默跳过落盘。结果是「组装函数写了、卡永远出不来」：
    # 结果页资产全空、报告 0 字、铁律二必判失败，而日志只有一行 warning。
    #
    # GUI 分析是全章分析（不是 sampler 的抽样），故索引就是 1..N。
    chapter_count = len(chapters) if chapters else 0
    if not chapter_count:
        # chapters 参数未传时用状态文件里的批记录反推章节数（cN-bM → N）。
        idxs = set()
        for key in (state.get("chapter_states") or {}):
            parsed = state_store.parse_cursor(key)
            if parsed and parsed[0]:
                idxs.add(parsed[0])
        chapter_count = max(idxs) if idxs else 0
    selected_indices = list(range(1, chapter_count + 1))
    manifest = {
        "title": title,
        "selected_indices": selected_indices,
        "selected_count": len(selected_indices),
    }
    metrics = {}
    book = _books_get(book_id)
    if book and isinstance(book.get("metrics"), dict):
        metrics = book["metrics"]

    from gui import migrate as _migrate

    def _write(name: str, card: dict[str, Any]) -> None:
        fp = config.ASSETS_ROOT / f"{book_id}-{name}.json"
        fp.parent.mkdir(parents=True, exist_ok=True)
        # 先校验再落盘（与 assemble.py 2026-09-21 的口径一致）：
        # 校验失败时不覆盖旧卡，避免次品污染。
        errs, _warns = engine_adapter.validate_asset_card(card, fp.name)
        if errs:
            _log.warning("组装卡未通过校验，跳过落盘 %s: %s", fp.name, errs[:3])
            return
        tmp = fp.with_name(fp.name + ".tmp")
        tmp.write_text(_json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, fp)
        try:
            _migrate.sync_asset(fp)
        except Exception as exc:  # noqa: BLE001 - 索引失败不影响文件本身
            _log.warning("组装卡重索引失败 %s: %s", fp.name, exc)
        written.append(fp.name)

    # voice-card：pass2(角色) + pass3(叙述/对白/情绪/意象/禁用词)
    try:
        pass2 = _merge("pass2_character")
        pass3 = _merge("pass3_style")
        if pass2 or pass3:
            voices = engine_adapter.normalize_pass2(pass2)
            narration, dialogue, emotion, imagery, banned = engine_adapter.normalize_pass3(pass3)
            card = engine_adapter.assemble_asset_voice_card(
                title, genre, manifest, metrics, voices,
                narration, dialogue, emotion, imagery, banned)
            _write("voice-card", card)
    except Exception as exc:  # noqa: BLE001
        _log.warning("组装 voice-card 失败: %s", exc)

    # structure-obs / commercial-obs：各自由单 pass 组装
    for pass_name, kind, name in (("pass1_structure", "structure", "structure-obs"),
                                  ("pass4_commercial", "commercial", "commercial-obs")):
        try:
            out = _merge(pass_name)
            if out:
                card = engine_adapter.assemble_asset_obs(kind, title, genre, out)
                _write(name, card)
        except Exception as exc:  # noqa: BLE001
            _log.warning("组装 %s 失败: %s", name, exc)

    # craft-card：pass5 十维笔法深度拆解（2026-11-23 补齐 GUI 缺口）
    try:
        pass5 = _merge("pass5_craft")
        if pass5:
            card = engine_adapter.assemble_asset_craft_card(
                title, genre, manifest, metrics, pass5)
            _write("craft-card", card)
    except Exception as exc:  # noqa: BLE001
        _log.warning("组装 craft-card 失败: %s", exc)

    if written:
        _log.info("分析后已组装 %d 张整书资产卡: %s", len(written), written)
    return written


def _batch_sort_key(filename: str) -> tuple[int, int, str]:
    """``c3-b2-pass1_structure.json`` → (3, 2, ...)，用于按章批顺序合并。"""
    m = re.match(r"c(\d+)-b(\d+)-(.+)\.json$", filename)
    if not m:
        return (10**9, 10**9, filename)
    return (int(m.group(1)), int(m.group(2)), m.group(3))


def _is_sample_book(book_id: str, title: str = "", source_path: str | None = None) -> bool:
    """是否为内置示例语料（2026-11-23）。

    示例只有 3 章、约 1.5 万字，客观上无法产出 ≥10000 字的正式双报告。
    旧实现让它走同一套铁律二硬校验，新手第一次「一键分析」100% 得到
    「铁律二未通过」的红色失败提示，像软件坏了。这里识别示例书，改用
    明确的「示例不生成正式报告」说明，而不是假装成功或硬报错。
    """
    if str(book_id or "").startswith("示例-") or str(title or "").startswith("示例-"):
        return True
    src = str(source_path or "").replace("/", "\\")
    return "\\samples\\" in src


def _generate_reports_inner(book_id: str, book: dict[str, Any]) -> None:
    """_generate_reports 的实际实现（调用方已持 _report_gen_lock）。

    尽力而为（DESIGN §8 D3）：craft-card 缺失时笔法报告留空并在结果提示，不阻断。

    2026-09-23（总工排查）改为**先校验、后落盘**：原实现是「先写盘 → 再校验」，
    校验失败只抑制 report_ready 事件、**不删已落盘的文件**，于是低于门槛的报告会
    永久留在 reports/ 里冒充合格品（实测存量 6 本书里 4 本不达标）。现在两份 Markdown
    先在内存里生成并判定合计字符数，通过才落盘；不通过则一个字节都不写。
    """
    voice = _load_assembled_card(book_id, "voice")
    structure = _load_assembled_card(book_id, "structure")
    commercial = _load_assembled_card(book_id, "commercial")
    craft = _load_assembled_card(book_id, "craft")

    book_dict = book if isinstance(book, dict) else {}
    db_title = None
    db_src = None
    try:
        if db._db_ready():
            db_rows = db.get_books(book_id=book_id)
            if db_rows:
                db_title = db_rows[0].get("title")
                db_src = db_rows[0].get("source_path")
    except Exception as exc:  # noqa: BLE001
        _log.debug("读取报告书名回退跳过 %s: %s", book_id, exc)
    state_title = state_store.load_state(book_id).get("title")
    title = (
        (voice.get("meta") or {}).get("source_title")
        or (craft.get("meta") or {}).get("source_title")
        or book_dict.get("title")
        or db_title
        or state_title
        or book_id
    )
    reports_dir = config.REPORTS_DIR

    # 1. 全部在内存里生成（不落盘）。
    #    拆书报告（voice/structure/commercial 任一存在即尝试生成）。
    book_md = ""
    if voice or structure or commercial:
        book_md = engine_adapter.build_report(voice or {}, structure or {}, commercial or {},
                                              title_override=title)
    #    笔法报告（craft-card 缺失则留空提示，不阻断）。
    craft_md = engine_adapter.render_craft_report(craft) if craft else ""

    # 2. 铁律二：合计 ≥10000 字符（或英文 ≥5000 词）硬校验（写盘**之前**判定）。
    chk = engine_adapter.combined_report_ok(
        len(book_md), len(craft_md), book_text=book_md, craft_text=craft_md
    )
    if not chk.get("ok"):
        if _is_sample_book(book_id, title, db_src):
            msg = (f"这是内置示例语料（{chk['total']} 字），仅用于体验拆书流程，"
                   f"篇幅不足以生成正式万字报告（硬门槛 {chk['min_chars']} 字）。"
                   "资产卡已正常生成；导入你自己的书即可生成正式报告。")
        else:
            msg = (f"铁律二未通过：拆书报告 {chk['book_chars']} 字 + 笔法分析 "
                   f"{chk['craft_chars']} 字 = 合计 {chk['total']} 字 < 硬门槛 "
                   f"{chk['min_chars']} 字（已阻止写盘，未产出任何报告文件）")
        with state_store.update_state(book_id) as state:
            state["report_error"] = msg
        broker.publish({
            "book_id": book_id,
            "status": "report_error",
            "chapter_index": 0,
            "batch_index": 0,
            "done": 0,
            "total": 0,
            "message": msg,
        })
        return

    # 3. 校验通过才落盘（此时两份报告都已确定合格）。
    #    原子写（tmp + os.replace）：崩溃不留半份文件；与 _report_gen_lock
    #    配合，并发 _watch 也只会完整覆盖，不会交错。
    def _atomic_write_text(fp: Path, text: str) -> None:
        # tmp 名唯一：即使未来有锁外并发写，也不互相抢占 tmp。
        tmp = fp.with_name(f"{fp.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, fp)

    from gui import migrate as _migrate

    reports_dir.mkdir(parents=True, exist_ok=True)
    if book_md:
        book_fp = reports_dir / f"{book_id}-拆书报告.md"
        _atomic_write_text(book_fp, book_md)
        try:
            _migrate.sync_report(book_fp, book_id=book_id, report_type="book")
        except Exception as exc:  # noqa: BLE001
            _log.warning("同步拆书报告至 SQLite 失败 %s: %s", book_fp.name, exc)
    if craft_md:
        craft_fp = reports_dir / f"{book_id}-笔法分析.md"
        _atomic_write_text(craft_fp, craft_md)
        try:
            _migrate.sync_report(craft_fp, book_id=book_id, report_type="craft")
        except Exception as exc:  # noqa: BLE001
            _log.warning("同步笔法分析报告至 SQLite 失败 %s: %s", craft_fp.name, exc)

    with state_store.update_state(book_id) as state:
        state.pop("report_error", None)

    # 刷新资产索引。
    asset_index.index.invalidate()

    # 4. SSE 推送 report_ready 事件。
    #    2026-09-23：report_ids 只列**实际写出**的报告——此前恒列两份，
    #    craft-card 缺失时「笔法分析」并不存在，属虚报。
    report_ids = []
    if book_md:
        report_ids.append(f"report:{book_id}-拆书报告")
    if craft_md:
        report_ids.append(f"report:{book_id}-笔法分析")
    broker.publish({
        "book_id": book_id,
        "status": "report_ready",
        "chapter_index": 0,
        "batch_index": 0,
        "done": 0,
        "total": 0,
        "report_ids": report_ids,
        "report_chars": chk.get("total", 0),
    })


# ---------------------------------------------------------------------------
# 创作增值工具服务（起名 / 毒点扫描 / 实操资产库）
# ---------------------------------------------------------------------------

def generate_names(kind: str = "character", style: str = "xianxia",
                   gender: str = "all", count: int = 10) -> dict[str, Any]:
    from gui import name_generator
    return name_generator.generate(kind=kind, style=style, gender=gender, count=count)


def scan_poison(text: str) -> dict[str, Any]:
    from gui import poison_checker
    return poison_checker.check_poison(text)


# ---------------------------------------------------------------------------
# 内置库文件加载器（2026-10-12 性能优化）
#
# 背景：``get_goldfingers`` / ``get_hooks`` / ``get_taboos`` / ``get_shuangdians``
# / ``get_worlds`` / ``get_dialogues`` / ``get_characters`` / ``get_emotions``
# 与 ``list_tropes`` 共 9 个函数结构完全一致（定位文件 → 读盘 → JSON 解析），
# 每次调用都重新读盘解析。实测 trope-library.json 411KB、解析 3.07ms，
# 是其余库（5-21KB，0.1-0.2ms）的 20 倍——/api/tropes 因此达 24.5ms。
#
# 这些库是**内置只读数据**：全仓库 grep 确认没有任何写路径
# （无 write_text / json.dump / open(..., "w") 触碰这些文件名）。
#
# 缓存键 = (文件名, 大小, mtime_ns)：用户手工替换库文件时立即感知，
# 不引入 TTL 的滞后。相比 TTL 方案，这里的指纹只 stat 单个文件（~0.01ms），
# 成本可忽略，故不必用 TTL 换实时性。
#
# 铁律三：纯标准库。
# ---------------------------------------------------------------------------
_LIB_CACHE: dict[str, tuple[tuple, Any]] = {}   # filename -> (fingerprint, data)


def _load_library(filename: str) -> Any:
    """读内置库 JSON，带指纹缓存；文件不存在返回 None。

    解析失败抛 ServiceError(500)——与各 get_* 原行为一致（库文件损坏是
    部署问题，不是调用方错误）。
    """
    fp = config.ASSETS_ROOT / filename
    if not fp.is_file():
        fp = config.ROOT_DIR / "assets" / filename
    if not fp.is_file():
        return None

    try:
        st = fp.stat()
        fingerprint = (st.st_size, st.st_mtime_ns)
    except OSError:
        fingerprint = None

    if fingerprint is not None:
        cached = _LIB_CACHE.get(filename)
        if cached is not None and cached[0] == fingerprint:
            return cached[1]

    try:
        data = json.loads(fp.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001 —— 与原各 get_* 的宽泛捕获一致
        raise ServiceError(f"{filename} 损坏: {exc}", 500) from exc

    if fingerprint is not None:
        _LIB_CACHE[filename] = (fingerprint, data)
    return data


def invalidate_library_cache() -> None:
    """清空内置库缓存（测试隔离环境切换时调用）。"""
    _LIB_CACHE.clear()


def _library_payload(filename: str, items_key: str) -> dict[str, Any]:
    """统一工具库响应形状：``{total_count, <items_key>, meta?}``。

    2026-11-03 修复：正常路径直接返回库文件原样（``{meta, goldfingers}``，
    total_count 埋在 meta 里），文件缺失时却返回 ``{total_count: 0, ...}``
    ——两种形状不一致。前端类型声明的是 ``{totalCount, items}``（经
    deepToCamel），拿不到 totalCount，计数徽标永远是空。

    现在两条路径统一把 ``total_count`` 提到顶层（meta 原样保留）。
    """
    data = _load_library(filename)
    if not isinstance(data, dict):
        return {"total_count": 0, items_key: []}
    items = data.get(items_key)
    if not isinstance(items, list):
        items = []
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    total = meta.get("total_count", data.get("total_count", len(items)))
    if not isinstance(total, int) or isinstance(total, bool):
        total = len(items)
    out: dict[str, Any] = {"total_count": total, items_key: items}
    if meta:
        out["meta"] = meta
    return out


def get_goldfingers() -> dict[str, Any]:
    return _library_payload("goldfinger-library.json", "goldfingers")


def get_hooks() -> dict[str, Any]:
    return _library_payload("hook-library.json", "hooks")


def get_taboos() -> dict[str, Any]:
    return _library_payload("taboo-library.json", "taboos")


def get_shuangdians() -> dict[str, Any]:
    return _library_payload("shuangdian-library.json", "shuangdians")


def get_worlds() -> dict[str, Any]:
    return _library_payload("world-library.json", "worlds")


def get_dialogues() -> dict[str, Any]:
    return _library_payload("dialogue-library.json", "dialogues")


def get_characters() -> dict[str, Any]:
    return _library_payload("character-library.json", "characters")


def get_emotions() -> dict[str, Any]:
    return _library_payload("emotion-library.json", "emotions")


