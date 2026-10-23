#!/usr/bin/env python3
"""剔除劣质爬虫断章作品，并以超严苛六维标准补齐真正高质量主流长篇网络小说。

加固特性：
1. 彻底解耦硬编码路径，支持 --db 参数与 EXOSCRIBE_CORPUS_DB 环境变量；
2. 模块化 is_strictly_acceptable_webnovel 检测规则，支持阈值配置与异常数据防护；
3. purge_defective_books 支持自定义待清理书目、演练模式（--dry-run）与静默模式（-q）；
4. scan_and_supplement 支持自定义切片获取函数（fetch_chunk_func），支持重试上限与网络降级；
5. CLI 命令行入口支持 --db、--target-count、--purge-only、--dry-run、--start-mb、--max-mb、--chunk-size-mb、-q。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from gui import config
from scripts.batch_100_books import (
    FOREIGN_BLACKLIST,
    clean_title_and_author,
    get_opener,
    sanitize_book_id,
    sync_full_work_log,
)

DEFECTIVE_TITLES = ["孢子物语", "暴力前锋"]


def get_default_corpus_db(db_arg: str | None = None) -> Path:
    """获取默认语料库数据库路径。

    优先级：
    1. CLI 指定的 --db 参数
    2. EXOSCRIBE_CORPUS_DB 环境变量
    3. config.DB_PATH（若物理存在）
    4. %LOCALAPPDATA%/暮冬念春/index.db（若物理存在）
    5. config.DB_PATH（兜底）
    """
    if db_arg:
        return Path(db_arg)

    env_val = os.environ.get("EXOSCRIBE_CORPUS_DB")
    if env_val:
        return Path(env_val)

    if config.DB_PATH.exists():
        return config.DB_PATH

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        p = Path(local_app_data) / "暮冬念春" / "index.db"
        if p.exists():
            return p

    return config.DB_PATH


def init_db_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """初始化并配置 index.db 连接。"""
    p = get_default_corpus_db(str(db_path) if db_path else None)
    conn = sqlite3.connect(str(p), timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def is_strictly_acceptable_webnovel(
    raw_title: str,
    clean_title: str,
    chapters: list[dict[str, Any]],
    min_chapters: int = 60,
    min_total_chars: int = 250000,
    min_avg_chars: float = 1000.0,
    max_short_ratio: float = 0.03,
    max_short_count: int = 8,
    max_repeat_count: int = 10,
) -> tuple[bool, str]:
    """超严苛长篇网文门槛检测。

    返回 (是否合格, 原因说明)。
    """
    if not chapters:
        return False, "章节列表为空"

    for b in FOREIGN_BLACKLIST:
        if b in raw_title or b in clean_title:
            return False, f"命中黑名单: {b}"
    if re.search(r"[\(（](?:美|英|俄|日|法|德|意|加|瑞典|波兰|捷克|澳|前苏联)[\)）]", raw_title):
        return False, "包含外国作者标记"
    if any(k in raw_title for k in ("(美)", "(英)", "(俄)", "(日)", "·", "世界名著", "名著", "中短篇", "短篇", "选集", "全集")):
        return False, "包含名著/译作标识"

    ch_count = len(chapters)
    if ch_count < min_chapters:
        return False, f"章节数不足 {min_chapters} (实际 {ch_count})"

    total_chars = sum(len(c.get("text", "") or "") for c in chapters if isinstance(c, dict))
    if total_chars < min_total_chars:
        return False, f"总字数不足 {min_total_chars // 10000} 万字 (实际 {total_chars:,})"

    avg_chars = total_chars / max(ch_count, 1)
    if avg_chars < min_avg_chars:
        return False, f"单章平均字数不足 {int(min_avg_chars)} 字 (实际 {avg_chars:.1f})"

    # 首章校验
    first_ch = ""
    if chapters and isinstance(chapters[0], dict):
        first_ch = (chapters[0].get("chapter") or "").strip()
    is_clean_start = bool(
        re.search(
            r"(第[0-9零]*[1一]章|第[0-9零]*[1一]节|第[0-9零]*[1一]回|第[0-9零]*[1一]卷|Chapter 0?1\b|第0章|序|引子|楔子)",
            first_ch,
        )
    )
    if not is_clean_start:
        return False, f"首章非正常起始: '{first_ch}'"

    # 短章率严控：短于 150 字的章节比例不得超过阈值且绝对数量超标
    short_chaps = [
        c for c in chapters
        if isinstance(c, dict) and len((c.get("text") or "").strip()) < 150
    ]
    short_ratio = len(short_chaps) / ch_count
    if short_ratio > max_short_ratio and len(short_chaps) > max_short_count:
        return False, f"短章率超标: {short_ratio:.1%} ({len(short_chaps)}/{ch_count})"

    # 标题重复率严控：禁止大面积重复章节标题（如几十个第一节）
    ch_names = [
        (c.get("chapter") or "").strip()
        for c in chapters
        if isinstance(c, dict)
    ]
    cnts = Counter(ch_names)
    top_title, top_count = cnts.most_common(1)[0] if cnts else ("", 0)
    if top_count > max_repeat_count and top_title in ["第一节", "第二节", "第三节", "第四节", "第一章"]:
        return False, f"重复标题过多: '{top_title}' 出现 {top_count} 次"

    return True, "合格"


def purge_defective_books(
    conn: sqlite3.Connection,
    titles: list[str] | None = None,
    dry_run: bool = False,
    quiet: bool = False,
) -> list[str]:
    """干净、级联剔除有缺陷的作品，返回被剔除书籍的 book_id 列表。"""
    targets = titles if titles is not None else DEFECTIVE_TITLES
    if not quiet:
        print("【步骤 1】清理有缺陷的劣质爬虫作品...")
    purged_ids: list[str] = []

    for t in targets:
        row = conn.execute("SELECT book_id, source_path FROM essence_books WHERE title = ?", (t,)).fetchone()
        if not row:
            row = conn.execute("SELECT book_id, source_path FROM books WHERE title = ?", (t,)).fetchone()

        if row:
            b_id = row[0]
            p_str = row[1] if len(row) > 1 and row[1] else ""
            if not quiet:
                print(f"  正在级联删除《{t}》(book_id={b_id})...")
            if not dry_run:
                with conn:
                    conn.execute("DELETE FROM essence_assets WHERE book_id = ?", (b_id,))
                    conn.execute("DELETE FROM essence_chains WHERE book_id = ?", (b_id,))
                    conn.execute("DELETE FROM essence_books WHERE book_id = ?", (b_id,))
                    conn.execute("DELETE FROM books WHERE book_id = ?", (b_id,))
                if p_str:
                    p = Path(p_str)
                    if p.exists():
                        try:
                            p.unlink()
                            if not quiet:
                                print(f"  已删除物理语料文件: {p.name}")
                        except Exception as e:
                            if not quiet:
                                print(f"  删除物理语料失败: {e}")
            purged_ids.append(b_id)
        else:
            if not quiet:
                print(f"  《{t}》在库中不存在，无需清理。")

    if not dry_run:
        conn.commit()
    return purged_ids


def scan_and_supplement(
    conn: sqlite3.Connection,
    target_count: int = 100,
    opener: urllib.request.OpenerDirector | None = None,
    chunk_size: int = 16 * 1024 * 1024,
    start_offset: int = 920 * 1024 * 1024,
    max_offset: int = 3500 * 1024 * 1024,
    url: str = "https://huggingface.co/datasets/wdndev/webnovel-chinese/resolve/main/data/webnovel_0.jsonl",
    fetch_chunk_func: Callable[[str, int, int, Any], bytes] | None = None,
    dry_run: bool = False,
    quiet: bool = False,
    max_retries_per_chunk: int = 3,
    retry_delay: float = 2.0,
) -> int:
    """从指定 offset 开始扫描补足高质量长篇网络小说。返回成功入库本数。"""
    if not quiet:
        print(f"\n【步骤 2】从 HuggingFace 扫描高质量真长篇作品至目标 {target_count} 本...")

    if opener is None and fetch_chunk_func is None:
        opener = get_opener()

    current_count_row = conn.execute("SELECT count(*) FROM essence_books").fetchone()
    current_count = current_count_row[0] if current_count_row else 0
    if not quiet:
        print(f"当前剩余书籍数: {current_count}，需补足: {max(target_count - current_count, 0)} 本")

    current_offset = start_offset
    current_book_title = None
    current_book_chapters: list[dict[str, Any]] = []
    line_buffer = ""
    added_count = 0

    from scripts.batch_100_books import check_book_exists, ingest_book_atomic

    while current_count < target_count and current_offset < max_offset:
        start_byte = current_offset
        end_byte = current_offset + chunk_size - 1
        if not quiet:
            print(f">> 扫描区间: {start_byte // (1024*1024)}MB - {end_byte // (1024*1024)}MB (当前: {current_count}/{target_count})...")

        chunk_data: bytes | None = None
        retries = 0
        while retries < max_retries_per_chunk:
            try:
                if fetch_chunk_func is not None:
                    chunk_data = fetch_chunk_func(url, start_byte, end_byte, opener)
                else:
                    req = urllib.request.Request(
                        url,
                        headers={"User-Agent": "Mozilla/5.0", "Range": f"bytes={start_byte}-{end_byte}"},
                    )
                    with opener.open(req, timeout=45) as resp:  # type: ignore[union-attr]
                        chunk_data = resp.read()
                break
            except Exception as e:
                retries += 1
                if not quiet:
                    print(f"  扫描分块 [{start_byte // (1024*1024)}MB] 出错 (尝试 {retries}/{max_retries_per_chunk}): {e}")
                if retries < max_retries_per_chunk and retry_delay > 0:
                    time.sleep(retry_delay)

        if chunk_data is None:
            if not quiet:
                print(f"  跳过无法读取的分块: {start_byte // (1024*1024)}MB")
            current_offset += chunk_size
            continue

        chunk_text = line_buffer + chunk_data.decode("utf-8", errors="ignore")
        lines = chunk_text.split("\n")
        line_buffer = lines[-1]
        valid_lines = lines[:-1]

        for line in valid_lines:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue

            raw_t = item.get("title", "").strip() if isinstance(item, dict) else ""
            if not raw_t:
                continue

            if raw_t != current_book_title:
                if current_book_title and len(current_book_chapters) >= 60:
                    clean_t, author, genre = clean_title_and_author(current_book_title)
                    ok, _reason = is_strictly_acceptable_webnovel(current_book_title, clean_t, current_book_chapters)
                    if ok:
                        b_id = sanitize_book_id(clean_t)
                        if not check_book_exists(conn, b_id, clean_t):
                            t0 = time.time()
                            if not dry_run:
                                rec = ingest_book_atomic(conn, b_id, clean_t, author, genre, "general", current_book_chapters)
                                sync_full_work_log(conn)
                            else:
                                rec = {
                                    "chapters": len(current_book_chapters),
                                    "chars": sum(len(c.get("text", "")) for c in current_book_chapters if isinstance(c, dict)),
                                }
                            current_count += 1
                            added_count += 1
                            dt = round(time.time() - t0, 2)
                            if not quiet:
                                print(f"  ✅ 成功补齐入库 [{current_count:03d}/{target_count}]: 《{clean_t}》 ({author} | {rec['chapters']}章 | {rec['chars']:,}字 | 耗时 {dt}s)")
                            if current_count >= target_count:
                                break
                        else:
                            if not quiet:
                                print(f"  [已存在跳过]: 《{clean_t}》")
                current_book_title = raw_t
                current_book_chapters = [item]
            else:
                current_book_chapters.append(item)

        current_offset += chunk_size

    # 处理最后一本书
    if current_count < target_count and current_book_title and len(current_book_chapters) >= 60:
        clean_t, author, genre = clean_title_and_author(current_book_title)
        ok, _reason = is_strictly_acceptable_webnovel(current_book_title, clean_t, current_book_chapters)
        if ok:
            b_id = sanitize_book_id(clean_t)
            if not check_book_exists(conn, b_id, clean_t):
                t0 = time.time()
                if not dry_run:
                    rec = ingest_book_atomic(conn, b_id, clean_t, author, genre, "general", current_book_chapters)
                    sync_full_work_log(conn)
                else:
                    rec = {
                        "chapters": len(current_book_chapters),
                        "chars": sum(len(c.get("text", "")) for c in current_book_chapters if isinstance(c, dict)),
                    }
                current_count += 1
                added_count += 1
                dt = round(time.time() - t0, 2)
                if not quiet:
                    print(f"  ✅ 成功补齐入库 [{current_count:03d}/{target_count}]: 《{clean_t}》 ({author} | {rec['chapters']}章 | {rec['chars']:,}字 | 耗时 {dt}s)")

    if not dry_run and added_count > 0:
        sync_full_work_log(conn)

    if not quiet:
        final_row = conn.execute("SELECT count(*) FROM essence_books").fetchone()
        final_cnt = final_row[0] if final_row else current_count
        print("\n补齐工作完成！当前全库书籍总数:", final_cnt)

    return added_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="剔除劣质爬虫断章作品，并以超严苛标准补齐高质量长篇网络小说。")
    parser.add_argument("--db", default=None, help="SQLite 数据库文件路径（默认自动推断）")
    parser.add_argument("--target-count", type=int, default=100, help="目标全库合格作品数 (默认 100)")
    parser.add_argument("--purge-only", action="store_true", help="仅执行缺陷书籍级联清理，不启动在线补齐")
    parser.add_argument("--dry-run", action="store_true", help="演练模式，不实际修改数据库与物理语料")
    parser.add_argument("--start-mb", type=int, default=920, help="远程切片起始位置 (MB, 默认 920)")
    parser.add_argument("--max-mb", type=int, default=3500, help="远程切片最大位置 (MB, 默认 3500)")
    parser.add_argument("--chunk-size-mb", type=int, default=16, help="单次切片下载容量 (MB, 默认 16)")
    parser.add_argument("-q", "--quiet", action="store_true", help="静默模式，仅输出关键信息")
    args = parser.parse_args(argv)

    db_path = get_default_corpus_db(args.db)
    if not db_path.exists():
        print(f"错误: 数据库文件不存在: {db_path}", file=sys.stderr)
        return 1

    conn = init_db_connection(db_path)
    try:
        purge_defective_books(conn, dry_run=args.dry_run, quiet=args.quiet)
        if not args.purge_only:
            scan_and_supplement(
                conn,
                target_count=args.target_count,
                start_offset=args.start_mb * 1024 * 1024,
                max_offset=args.max_mb * 1024 * 1024,
                chunk_size=args.chunk_size_mb * 1024 * 1024,
                dry_run=args.dry_run,
                quiet=args.quiet,
            )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
