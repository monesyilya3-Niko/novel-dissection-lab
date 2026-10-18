#!/usr/bin/env python3
"""检查特定书籍行序列切片。"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path


def get_default_corpus_db() -> Path:
    """获取默认语料库数据库路径。"""
    env_db = os.environ.get("EXOSCRIBE_CORPUS_DB")
    if env_db:
        return Path(env_db).resolve()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "暮冬念春" / "index.db"
    return Path.home() / ".local" / "share" / "暮冬念春" / "index.db"


def inspect_book_lines(
    db_source: str | Path | sqlite3.Connection,
    title: str = "奥术神座",
    start_line: int = 9210,
    end_line: int = 9245,
) -> list[tuple[int, str]]:
    """读取指定书籍指定行号区间的文本行。"""
    if isinstance(db_source, sqlite3.Connection):
        conn = db_source
        should_close = False
    else:
        conn = sqlite3.connect(str(db_source))
        conn.row_factory = sqlite3.Row
        should_close = True

    try:
        r = conn.execute(
            "SELECT source_path FROM essence_books WHERE title = ?", (title,)
        ).fetchone()
        if not r:
            return []
        p = Path(r[0])
        if not p.is_file():
            return []
        lines = p.read_text(encoding="utf-8", errors="ignore").split("\n")
        total = len(lines)
        s = max(0, min(start_line, total))
        e = max(s, min(end_line, total))
        return [(idx, lines[idx]) for idx in range(s, e)]
    finally:
        if should_close:
            conn.close()


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(description="行区间切片巡检工具")
    parser.add_argument("--db", type=str, default=None, help="数据库路径")
    parser.add_argument("--title", type=str, default="奥术神座", help="书名")
    parser.add_argument("--start", type=int, default=9210, help="起始行号")
    parser.add_argument("--end", type=int, default=9245, help="结束行号")
    args = parser.parse_args(argv)

    db_path = Path(args.db).resolve() if args.db else get_default_corpus_db()
    if not db_path.is_file():
        print(f"[WARN] 语料库数据库不存在: {db_path}", file=sys.stderr)
        return 0

    results = inspect_book_lines(db_path, args.title, args.start, args.end)
    for line_no, content in results:
        print(f"{line_no}: {repr(content)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

