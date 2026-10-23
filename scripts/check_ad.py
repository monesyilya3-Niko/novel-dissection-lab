#!/usr/bin/env python3
"""检查小说正文中的首发广告信息残留。"""

from __future__ import annotations

import argparse
import os
import re
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


def check_book_ad(
    db_source: str | Path | sqlite3.Connection,
    title: str = "暴力前锋",
    pattern: str = r"请到.*首发",
) -> str | None:
    """检查指定书籍正文是否命中广告模式。"""
    if isinstance(db_source, sqlite3.Connection):
        conn = db_source
        should_close = False
    else:
        conn = sqlite3.connect(str(db_source))
        conn.row_factory = sqlite3.Row
        should_close = True

    try:
        r = conn.execute(
            "SELECT title, source_path FROM essence_books WHERE title = ?", (title,)
        ).fetchone()
        if not r:
            return None
        p = Path(r["source_path"])
        if not p.is_file():
            return None
        text = p.read_text(encoding="utf-8", errors="ignore")
        hit = re.search(pattern, text)
        if hit:
            start = max(0, hit.start() - 30)
            end = min(len(text), hit.end() + 30)
            return text[start:end]
        return None
    finally:
        if should_close:
            conn.close()


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(description="检查小说正文中的广告水印残留")
    parser.add_argument("--db", type=str, default=None, help="数据库路径")
    parser.add_argument("--title", type=str, default="暴力前锋", help="书名")
    parser.add_argument("--pattern", type=str, default=r"请到.*首发", help="广告正则")
    args = parser.parse_args(argv)

    db_path = Path(args.db).resolve() if args.db else get_default_corpus_db()
    if not db_path.is_file():
        print(f"[WARN] 语料库数据库不存在: {db_path}", file=sys.stderr)
        return 0

    match_snippet = check_book_ad(db_path, args.title, args.pattern)
    if match_snippet:
        print(f"Match in {args.title}:", repr(match_snippet))
    else:
        print(f"No ad pattern match in {args.title}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

