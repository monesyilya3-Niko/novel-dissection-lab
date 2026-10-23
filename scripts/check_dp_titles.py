#!/usr/bin/env python3
"""检查特定书籍中的疑似异常章节标题。"""

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


def inspect_book_titles(
    db_source: str | Path | sqlite3.Connection,
    title: str = "斗破苍穹",
    max_len: int = 30,
) -> tuple[int, list[str]]:
    """提取指定书籍的所有章节标题及异常标题列表。"""
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
            return (0, [])
        p = Path(r[0])
        if not p.is_file():
            return (0, [])
        lines = [
            l.strip()
            for l in p.read_text(encoding="utf-8", errors="ignore").split("\n")
            if l.strip()
        ]
        ch_titles = [
            l for l in lines if l.startswith("第") or l.startswith("Chapter")
        ]
        suspicious_punctuation = ("，", "。", "！", "？", "……", "“", "”")
        bad = [
            t
            for t in ch_titles
            if len(t) > max_len or any(punc in t for punc in suspicious_punctuation)
        ]
        return (len(ch_titles), bad)
    finally:
        if should_close:
            conn.close()


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(description="单书异常章节标题检测工具")
    parser.add_argument("--db", type=str, default=None, help="数据库路径")
    parser.add_argument("--title", type=str, default="斗破苍穹", help="书名")
    parser.add_argument("--max-len", type=int, default=30, help="标题最大安全长度")
    parser.add_argument("--show", type=int, default=10, help="展示前 N 条异常标题")
    args = parser.parse_args(argv)

    db_path = Path(args.db).resolve() if args.db else get_default_corpus_db()
    if not db_path.is_file():
        print(f"[WARN] 语料库数据库不存在: {db_path}", file=sys.stderr)
        return 0

    total_count, bad_titles = inspect_book_titles(
        db_path, args.title, max_len=args.max_len
    )
    print(f"{args.title}总章数: {total_count}, 异常命中数: {len(bad_titles)}")
    for b in bad_titles[: args.show]:
        print(" ", repr(b))
    return 0


if __name__ == "__main__":
    sys.exit(main())

