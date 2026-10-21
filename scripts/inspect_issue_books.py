#!/usr/bin/env python3
"""检查单部书籍中不同章节正则切片下的短章模式分布。"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
for _p in (str(ROOT_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def get_default_corpus_db() -> Path:
    """获取默认语料库数据库路径。"""
    env_db = os.environ.get("EXOSCRIBE_CORPUS_DB")
    if env_db:
        return Path(env_db).resolve()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "暮冬念春" / "index.db"
    return Path.home() / ".local" / "share" / "暮冬念春" / "index.db"


def inspect_book_chapter_patterns(
    db_source: str | Path | sqlite3.Connection,
    title: str = "暴力前锋",
    min_chars: int = 150,
) -> dict[str, Any] | None:
    """对比包含[节]与排除[节]两种正则切片下的短章分布。"""
    if isinstance(db_source, sqlite3.Connection):
        conn = db_source
        should_close = False
    else:
        conn = sqlite3.connect(str(db_source))
        conn.row_factory = sqlite3.Row
        should_close = True

    try:
        row = conn.execute(
            "SELECT title, source_path FROM essence_books WHERE title = ?",
            (title,),
        ).fetchone()
        if not row:
            return None
        src_path = Path(row[1])
        if not src_path.is_file():
            return None

        content = src_path.read_text(encoding="utf-8", errors="ignore")

        # 1. 包含节
        chaps_with_jie = re.split(
            r"\n(?=第[0-9零一二三四五六七八九十百千万]+[章节回卷]|Chapter [0-9]+)",
            content,
        )
        short1 = [c.strip() for c in chaps_with_jie if len(c.strip()) < min_chars]

        # 2. 排除节（只保留 章/回/卷）
        chaps_no_jie = re.split(
            r"\n(?=第[0-9零一二三四五六七八九十百千万]+[章回卷]|Chapter [0-9]+)",
            content,
        )
        short2 = [c.strip() for c in chaps_no_jie if len(c.strip()) < min_chars]

        return {
            "title": title,
            "with_jie": {
                "total": len(chaps_with_jie),
                "short_count": len(short1),
                "short_ratio": len(short1) / max(len(chaps_with_jie), 1),
                "shorts": short1,
            },
            "no_jie": {
                "total": len(chaps_no_jie),
                "short_count": len(short2),
                "short_ratio": len(short2) / max(len(chaps_no_jie), 1),
                "shorts": short2,
            },
        }
    finally:
        if should_close:
            conn.close()


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="单书章节切片模式对照检查工具"
    )
    parser.add_argument("--db", type=str, default=None, help="数据库路径")
    parser.add_argument("--title", type=str, default="暴力前锋", help="书名")
    parser.add_argument("--min-chars", type=int, default=150, help="短章字数上限")
    parser.add_argument("--show", type=int, default=5, help="展示前 N 个短章样例")
    args = parser.parse_args(argv)

    db_path = Path(args.db).resolve() if args.db else get_default_corpus_db()
    if not db_path.is_file():
        print(f"[WARN] 语料库数据库不存在: {db_path}", file=sys.stderr)
        return 0

    res = inspect_book_chapter_patterns(
        db_path, title=args.title, min_chars=args.min_chars
    )
    if not res:
        print(f"[WARN] 未找到书籍或物理文件不可读: {args.title}", file=sys.stderr)
        return 0

    w = res["with_jie"]
    print(f"包含[节]: 总数={w['total']}, 短章={w['short_count']} ({w['short_ratio']:.1%})")

    nj = res["no_jie"]
    print(f"排除[节]: 总数={nj['total']}, 短章={nj['short_count']} ({nj['short_ratio']:.1%})")

    if nj["shorts"]:
        for s in nj["shorts"][: args.show]:
            print("剩余短章:", repr(s[:80]))

    return 0


if __name__ == "__main__":
    sys.exit(main())

