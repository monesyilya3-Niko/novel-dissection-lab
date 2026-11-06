"""服务层业务编排：导入 / 切批 / 分析执行 / 暂停 / 续传 / 重试。

分层：路由层 → 服务层 → 引擎适配层。本模块不 import novel-lab 脚本，
只调用 engine_adapter 与 state_store。
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

from gui import asset_index, config, db, engine_adapter, state_store
from gui.logging_setup import get_logger
from gui.sse import broker

_log = get_logger("services")

# 每个 pass 分析的 kind 名（串行顺序）。
PASS_ORDER = ("pass1_structure", "pass2_character", "pass3_style", "pass4_commercial")

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
            st = chapter_states.get(key, {}).get("status", "pending")
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

def start_analysis(book_id: str, genre: str, model_id: str | None = None,
                   batch_size: int | None = None) -> dict[str, Any]:
    """开始/重启分析。串行跑，后台线程执行，SSE 推送进度。"""
    book = _get_book_or_raise(book_id)
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

        # 【修复 H3】必须把 status 重置为 running 并清掉上一次的 report_error。
        # 否则重跑一本已分析完（status="done"）的书时，报告监听线程 _watch 首次
        # 轮询就读到残留的 "done"，立刻用旧/半成品资产生成报告，并与新启动的
        # 分析线程并发读写同一批资产卡；返回体却仍声称 status:"running"。
        with state_store.update_state(book_id) as state:
            state["genre"] = genre
            state["model_id"] = model_id
            state["batch_size"] = bs
            state["status"] = "running"
            state.pop("report_error", None)

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
        while True:
            for ci, (ctitle, cbody) in enumerate(chapters, start=1):
                batches = engine_adapter.split_batches(cbody, batch_size)
                for b in batches:
                    bi = b["batch_index"]
                    key = state_store.batch_id(ci, bi)

                    # 断点续传：已 success 的批直接跳过，不重复分析（设计 §3.3/§5）。
                    existing = state_store.load_state(book_id).get("chapter_states", {}).get(key)
                    if existing and existing.get("status") == "success":
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

                    _publish(book_id, ci, bi, "running", done, total_batches, ctx)
                    # 标记 running 落盘（原子读改写：HTTP 线程可能同时在 pause/retry）
                    with state_store.update_state(book_id) as state:
                        state_store.set_batch_state(state, ci, bi, "running")

                    # 串行跑四个 pass
                    batch_results = {}
                    last_asset = None
                    try:
                        for pass_name in PASS_ORDER:
                            out = engine_adapter.run_batch(
                                pass_name, ci, ctitle, b["text"], metrics,
                                dry_run=False, model_id=model_id,
                            )
                            batch_results[pass_name] = out
                            # 每个 pass 落一个资产文件
                            ap = state_store.asset_path(book_id, ci, bi, pass_name)
                            ap.parent.mkdir(parents=True, exist_ok=True)
                            ap.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
                            # 资产相对路径以 ASSETS_ROOT 为基准（不假设 ASSETS_ROOT 在 ROOT_DIR 下，
                            # 兼容测试/自定义目录隔离），供前端按 book_id/ch/batch/pass 定位。
                            try:
                                last_asset = str(ap.relative_to(config.ASSETS_ROOT))
                            except ValueError:
                                last_asset = str(ap)
                    except Exception as exc:  # noqa: BLE001
                        with state_store.update_state(book_id) as state:
                            state_store.set_batch_state(state, ci, bi, "failed")
                            state["last_error"] = str(exc)[:500]
                        done += 1
                        _publish(book_id, ci, bi, "failed", done, total_batches, ctx)
                        continue

                    # 记录成功（资产取 pass1 作为代表，asset_index 只记批）
                    with state_store.update_state(book_id) as state:
                        state_store.set_batch_state(state, ci, bi, "success", asset=last_asset)
                    done += 1
                    _publish(book_id, ci, bi, "success", done, total_batches, ctx)

            # 一趟遍历结束：若仍有 pending（retry_failed 改回来的），再来一轮
            _st = state_store.load_state(book_id)
            _has_pending = any(
                (v or {}).get("status") == "pending"
                for v in (_st.get("chapter_states") or {}).values())
            if not _has_pending or ctx["stop_flag"].is_set():
                break
            _rescan_rounds += 1
            if _rescan_rounds >= _MAX_RESCAN_ROUNDS:
                _log.warning("重扫已达上限 %d 轮，仍有 pending 批，停止", _MAX_RESCAN_ROUNDS)
                break

        # 全部完成
        with state_store.update_state(book_id) as state:
            state["status"] = "done"
            state.pop("last_error", None)
        # 同步 books 表状态（2026-11-05 修）。
        #
        # /api/books 的 status 取自 SQLite books.status，而分析完成原先只改
        # 状态文件——全库没有任何代码把 books.status 推进到 done（唯一写入点
        # 是导入时的 "idle"）。实测：db.get_books(status='done') 恒为 0 条，
        # 而状态文件里有 7 本 done。用户看到拆完的书仍标「待拆」。
        _sync_book_status(book_id, "done")
        # 2026-11-04：分析结束后组装整书资产卡。
        # 此前只落了批级 pass 文件就置 done，而 get_book_results /
        # _generate_reports_inner 读的是 {book_id}-voice-card.json 这类整书卡——
        # 没有任何代码生成它们，于是结果页资产全空、报告 0 字、铁律二必然判失败。
        try:
            _assemble_after_analysis(book_id, genre, chapters, state)
        except Exception as exc:  # noqa: BLE001 - 组装失败不改变"分析已完成"的事实
            _log.warning("分析后组装资产失败（批级产物仍完整）: %s", exc)
        _publish(book_id, 0, 0, "done", done, total_batches, ctx)
    except Exception as exc:  # noqa: BLE001
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
    return start_analysis(book_id, g, mid, bs)


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
    done = sum(1 for v in state.get("chapter_states", {}).values() if v.get("status") == "success")
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
    }


# ---------------------------------------------------------------------------
# 阶段一：概览 / 资产 / 报告 / 拆书结果 / 一键分析
# ---------------------------------------------------------------------------

def get_overview() -> dict[str, Any]:
    """首页概览聚合：SQL 聚合计数 + 已拆书本数 + 模型状态。"""
    ov = asset_index.index.get_overview()
    # 「已拆 N 本」来自 SQLite books 表（status='done'）优先，回退 gui_state 目录。
    done_books = db.get_books(status="done")
    if done_books:
        ov["total_books"] = len(done_books)
    else:
        books = state_store.list_books_summary()
        ov["total_books"] = len(books)
    ov["model_configured"] = engine_adapter.any_model_configured() or ov.get("model_configured", False)
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
    """报告清单（拆书报告 + 笔法分析），优先 SQLite，空则回退扫描。"""
    rows = db.list_reports()
    if rows:
        out = []
        for r in rows:
            path = r.get("path", "")
            stem = Path(path).stem if path else r.get("title", "")
            out.append({
                "id": f"report:{stem}",
                "name": stem,
                "kind": r.get("type", "book"),
                "book_id": r.get("book_id", ""),
                "size": None,
            })
        return out
    # 回退扫描（迁移前）。
    items = [it for it in asset_index.index.scan()["items"] if it["kind"] == "report"]
    out = []
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

    # 报告关联：reports 目录下 {book_id}-拆书报告.md / {book_id}-笔法分析.md。
    report_ids = []
    for name in (f"{book_id}-拆书报告", f"{book_id}-笔法分析"):
        if (config.REPORTS_DIR / f"{name}.md").is_file():
            report_ids.append(f"report:{name}")

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

    拆书阶段复用现有 ``start_analysis``（后台线程 + SSE）；报告阶段在拆书线程
    done 后由 ``_generate_reports`` 回调生成。返回 ``{task_id, cursor, status}``，
    与 ``/api/analyze/start`` 一致，前端沿用既有 SSE 进度订阅。
    """
    book = _get_book_or_raise(book_id)
    if not engine_adapter.any_model_configured():
        raise ServiceError("未配置外部模型，请先运行 model_config.py 配置", 400)

    # 复用现有 start_analysis（内部起后台线程）。
    result = start_analysis(book_id, genre, model_id)

    # 报告生成采用「拆书 done 后回调」：轮询状态，done 后触发报告生成。
    _schedule_report_generation(book_id, book)
    return result


def _schedule_report_generation(book_id: str, book: dict[str, Any]) -> None:
    """拆书线程完成后回调生成两份报告（拆书报告 + 笔法分析，尽力而为）。

    用独立守护线程轮询拆书状态，done 后调用 ``_generate_reports``。不阻塞
    ``run_full_analysis`` 返回（前端已拿到 task_id 继续走 SSE）。
    """
    def _watch() -> None:
        deadline = time.time() + 24 * 3600  # 上限 24h，避免永久占用。
        while time.time() < deadline:
            st = state_store.load_state(book_id)
            if st.get("status") in ("done", "error"):
                if st.get("status") == "done":
                    try:
                        _generate_reports(book_id, book)
                    except Exception as exc:  # noqa: BLE001
                        with state_store.update_state(book_id) as st:
                            st["report_error"] = str(exc)[:500]
                return
            time.sleep(1.0)
        # 24h 未收敛（极少见：拆书线程僵死 / 一直被暂停）（2026-11-05）。
        # 原来直接 return，既不写状态也不告知——这个后台线程就此消失，
        # 用户永远等不到报告，也不知道为什么。
        try:
            with state_store.update_state(book_id) as st:
                st["report_error"] = (
                    "报告生成等待超时（拆书在 24 小时内未完成，可能因长期暂停或线程僵死）。"
                    "请检查任务状态后重试分析。")
        except Exception as exc:  # noqa: BLE001
            _log.warning("写入报告超时标记失败 %s: %s", book_id, exc)

    threading.Thread(target=_watch, daemon=True, name=f"report-{book_id}").start()


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

    GUI 只跑 4 个 pass（PASS_ORDER 不含 pass5），所以 craft-card 无法生成——
    这是 GUI 与 CLI 的能力差异，不是本次遗漏；笔法报告在缺卡时留空提示。
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

        for fp in sorted(base.glob(f"c*-b*-{pass_name}.json"),
                         key=lambda p: _batch_sort_key(p.name)):
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

    if written:
        _log.info("分析后已组装 %d 张整书资产卡: %s", len(written), written)
    return written


def _batch_sort_key(filename: str) -> tuple[int, int, str]:
    """``c3-b2-pass1_structure.json`` → (3, 2, ...)，用于按章批顺序合并。"""
    m = re.match(r"c(\d+)-b(\d+)-(.+)\.json$", filename)
    if not m:
        return (10**9, 10**9, filename)
    return (int(m.group(1)), int(m.group(2)), m.group(3))


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

    title = (voice.get("meta") or {}).get("source_title", book.get("title", book_id))
    reports_dir = config.REPORTS_DIR

    # 1. 全部在内存里生成（不落盘）。
    #    拆书报告（voice/structure/commercial 任一存在即尝试生成）。
    book_md = ""
    if voice or structure or commercial:
        book_md = engine_adapter.build_report(voice or {}, structure or {}, commercial or {},
                                              title_override=title)
    #    笔法报告（craft-card 缺失则留空提示，不阻断）。
    craft_md = engine_adapter.render_craft_report(craft) if craft else ""

    # 2. 铁律二：合计 ≥10000 字符硬校验（与 CLI 共用同一实现，写盘**之前**判定）。
    chk = engine_adapter.combined_report_ok(len(book_md), len(craft_md))
    if not chk.get("ok"):
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

    reports_dir.mkdir(parents=True, exist_ok=True)
    if book_md:
        _atomic_write_text(reports_dir / f"{book_id}-拆书报告.md", book_md)
    if craft_md:
        _atomic_write_text(reports_dir / f"{book_id}-笔法分析.md", craft_md)

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


