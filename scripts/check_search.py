#!/usr/bin/env python3
"""检查数据库中资产的关键词检索结果。"""

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


def search_essence_assets(
    db_source: str | Path | sqlite3.Connection,
    keyword: str = "萧炎",
    limit: int | None = None,
) -> list[tuple[int, str, str]]:
    """在 essence_assets 表中全文检索指定关键词。"""
    if isinstance(db_source, sqlite3.Connection):
        conn = db_source
        should_close = False
    else:
        conn = sqlite3.connect(str(db_source))
        conn.row_factory = sqlite3.Row
        should_close = True

    try:
        sql = (
            "SELECT id, title, content FROM essence_assets "
            "WHERE content LIKE ? OR title LIKE ? ORDER BY id ASC"
        )
        if limit is not None and limit > 0:
            sql += f" LIMIT {limit}"
        term = f"%{keyword}%"
        rows = conn.execute(sql, (term, term)).fetchall()
        return [(r["id"], r["title"], r["content"]) for r in rows]
    finally:
        if should_close:
            conn.close()


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(description="资产库关键词直接检索巡检工具")
    parser.add_argument("--db", type=str, default=None, help="数据库路径")
    parser.add_argument("--keyword", type=str, default="萧炎", help="检索关键词")
    parser.add_argument("--limit", type=int, default=None, help="最多返回记录数")
    args = parser.parse_args(argv)

    db_path = Path(args.db).resolve() if args.db else get_default_corpus_db()
    if not db_path.is_file():
        print(f"[WARN] 语料库数据库不存在: {db_path}", file=sys.stderr)
        return 0

    rows = search_essence_assets(db_path, keyword=args.keyword, limit=args.limit)
    print(f"Direct SQL matching {args.keyword}:", len(rows))
    for r in rows:
        print(" ", r[0], r[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())

