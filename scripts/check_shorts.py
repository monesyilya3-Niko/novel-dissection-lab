#!/usr/bin/env python3
"""检查特定小说切片中的短章分布。"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any


def get_default_corpus_db() -> Path:
    """获取默认语料库数据库路径。"""
    env_db = os.environ.get("EXOSCRIBE_CORPUS_DB")
    if env_db:
        return Path(env_db).resolve()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "暮冬念春" / "index.db"
    return Path.home() / ".local" / "share" / "暮冬念春" / "index.db"


def inspect_book_shorts(
    db_source: str | Path | sqlite3.Connection,
    titles: list[str] | tuple[str, ...],
    min_chars: int = 150,
) -> dict[str, dict[str, Any]]:
    """检查指定书籍集合中的短章分布情况。"""
    if isinstance(db_source, sqlite3.Connection):
        conn = db_source
        should_close = False
    else:
        conn = sqlite3.connect(str(db_source))
        conn.row_factory = sqlite3.Row
        should_close = True

    try:
        results: dict[str, dict[str, Any]] = {}
        for title in titles:
            r = conn.execute(
                "SELECT title, source_path FROM essence_books WHERE title = ?",
                (title,),
            ).fetchone()
            if not r:
                continue
            p = Path(r["source_path"])
            if not p.is_file():
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
            raw_chaps = re.split(
                r"\n(?=第[0-9零一二三四五六七八九十百千万]+[章节回卷]|Chapter [0-9]+)",
                text,
            )
            shorts = [c.strip() for c in raw_chaps if len(c.strip()) < min_chars]
            results[title] = {
                "total_chapters": len(raw_chaps),
                "short_chapters": shorts,
            }
        return results
    finally:
        if should_close:
            conn.close()


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(description="特定小说短章切片巡检工具")
    parser.add_argument("--db", type=str, default=None, help="数据库路径")
    parser.add_argument(
        "--titles",
        nargs="+",
        default=["暴力前锋", "孢子物语"],
        help="要检查的书名列表",
    )
    parser.add_argument("--min-chars", type=int, default=150, help="短章判定字数上限")
    parser.add_argument("--show", type=int, default=5, help="展示前 N 个短章样例")
    args = parser.parse_args(argv)

    db_path = Path(args.db).resolve() if args.db else get_default_corpus_db()
    if not db_path.is_file():
        print(f"[WARN] 语料库数据库不存在: {db_path}", file=sys.stderr)
        return 0

    results = inspect_book_shorts(db_path, args.titles, min_chars=args.min_chars)
    for title, data in results.items():
        total = data["total_chapters"]
        shorts = data["short_chapters"]
        print(f"=== {title} === (total {total}, short {len(shorts)})")
        for s in shorts[: args.show]:
            print("  Sample short:", repr(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())

