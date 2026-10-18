#!/usr/bin/env python3
"""全库小说深度扫描爬虫残留伪标题与短章异常。"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

SUSPICIOUS_TITLE_PATTERNS = (
    "第一天",
    "第二天",
    "第三天",
    "第四天",
    "第一次",
    "第二次",
    "第一轮",
    "第二轮",
    "第一小队",
    "第一节",
    "第二节",
    "第三节",
    "第四节",
    "第一球",
    "第二球",
    "第三球",
    "第四球",
    "第五球",
)


def get_default_corpus_db() -> Path:
    """获取默认语料库数据库路径。"""
    env_db = os.environ.get("EXOSCRIBE_CORPUS_DB")
    if env_db:
        return Path(env_db).resolve()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "暮冬念春" / "index.db"
    return Path.home() / ".local" / "share" / "暮冬念春" / "index.db"


def scan_crawler_artifacts(
    db_source: str | Path | sqlite3.Connection,
    *,
    short_ratio_thresh: float = 0.03,
    bad_title_ratio_thresh: float = 0.02,
    min_chars: int = 150,
) -> list[dict[str, Any]]:
    """扫描全部书籍中疑似爬虫伪标题与短章异常。"""
    if isinstance(db_source, sqlite3.Connection):
        conn = db_source
        should_close = False
    else:
        conn = sqlite3.connect(str(db_source))
        conn.row_factory = sqlite3.Row
        should_close = True

    try:
        sql = (
            "SELECT id, book_id, title, genre, total_chapters, total_chars, source_path "
            "FROM essence_books ORDER BY id ASC"
        )
        rows = conn.execute(sql).fetchall()
        suspicious_books: list[dict[str, Any]] = []

        for r in rows:
            p = Path(r["source_path"])
            if not p.is_file():
                suspicious_books.append(
                    {
                        "id": r["id"],
                        "book_id": r["book_id"],
                        "title": r["title"],
                        "reason": "文件不存在",
                        "short_ratio": 0.0,
                        "bad_title_ratio": 0.0,
                    }
                )
                continue

            content = p.read_text(encoding="utf-8", errors="ignore")
            raw_chaps = re.split(
                r"\n(?=第[0-9零一二三四五六七八九十百千万]+[章节回卷]|Chapter [0-9]+)",
                content,
            )
            short_chaps = [c.strip() for c in raw_chaps if len(c.strip()) < min_chars]
            short_ratio = len(short_chaps) / max(len(raw_chaps), 1)

            lines = [l.strip() for l in content.split("\n") if l.strip()]
            ch_titles = [
                l
                for l in lines
                if re.match(
                    r"^(第[0-9零一二三四五六七八九十百千万]+[章节回卷]|Chapter [0-9]+)",
                    l,
                )
            ]

            bad_title_count = 0
            for ct in ch_titles:
                if any(w in ct for w in SUSPICIOUS_TITLE_PATTERNS):
                    bad_title_count += 1

            bad_title_ratio = bad_title_count / max(len(ch_titles), 1)

            if short_ratio > short_ratio_thresh or bad_title_ratio > bad_title_ratio_thresh:
                reason = (
                    f"短章率={short_ratio:.1%}({len(short_chaps)}/{len(raw_chaps)}), "
                    f"假标题率={bad_title_ratio:.1%}({bad_title_count})"
                )
                suspicious_books.append(
                    {
                        "id": r["id"],
                        "book_id": r["book_id"],
                        "title": r["title"],
                        "reason": reason,
                        "short_ratio": short_ratio,
                        "bad_title_ratio": bad_title_ratio,
                    }
                )

        return suspicious_books
    finally:
        if should_close:
            conn.close()


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="全库小说爬虫伪标题与切片污染深度扫描工具"
    )
    parser.add_argument("--db", type=str, default=None, help="数据库路径")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静默模式，仅通过退出码返回结果",
    )
    args = parser.parse_args(argv)

    db_path = Path(args.db).resolve() if args.db else get_default_corpus_db()
    if not db_path.is_file():
        if not args.quiet:
            print(f"[WARN] 语料库数据库不存在: {db_path}", file=sys.stderr)
        return 0

    results = scan_crawler_artifacts(db_path)

    if not args.quiet:
        print(f"全库扫描完成，发现可疑书籍数: {len(results)}")
        for sb in results:
            print(f"  - 《{sb['title']}》: {sb['reason']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

