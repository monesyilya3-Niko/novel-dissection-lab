#!/usr/bin/env python3
"""调查语料库中的资产卡/伏笔链异常短小、短章切片与广告水印残留。"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

AD_PATTERNS = ("防盗章", "点击下一页继续阅读", "请到.*首发", "本章未完", "小说网.*免费阅读")


def get_default_corpus_db() -> Path:
    """获取默认语料库数据库路径。"""
    env_db = os.environ.get("EXOSCRIBE_CORPUS_DB")
    if env_db:
        return Path(env_db).resolve()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "暮冬念春" / "index.db"
    return Path.home() / ".local" / "share" / "暮冬念春" / "index.db"


def debug_short_assets(
    conn: sqlite3.Connection, min_len: int = 20
) -> list[dict[str, Any]]:
    """查询内容长度低于阈值的短小资产卡。"""
    sql = """
        SELECT ea.id, ea.book_id, eb.title, ea.category, ea.title as asset_title,
               length(ea.content) as c_len, ea.content
        FROM essence_assets ea
        JOIN essence_books eb ON ea.book_id = eb.book_id
        WHERE length(ea.content) < ?
        ORDER BY ea.id ASC
    """
    rows = conn.execute(sql, (min_len,)).fetchall()
    return [
        {
            "id": r["id"],
            "book_id": r["book_id"],
            "title": r["title"],
            "category": r["category"],
            "asset_title": r["asset_title"],
            "content_len": r["c_len"],
            "content": r["content"],
        }
        for r in rows
    ]


def debug_short_chains(
    conn: sqlite3.Connection, min_len: int = 10
) -> list[dict[str, Any]]:
    """查询钩子文本过短的伏笔链。"""
    sql = """
        SELECT ec.id, ec.book_id, eb.title, length(ec.hook_text) as h_len, ec.hook_text
        FROM essence_chains ec
        JOIN essence_books eb ON ec.book_id = eb.book_id
        WHERE length(ec.hook_text) < ?
        ORDER BY ec.id ASC
    """
    rows = conn.execute(sql, (min_len,)).fetchall()
    return [
        {
            "id": r["id"],
            "book_id": r["book_id"],
            "title": r["title"],
            "hook_len": r["h_len"],
            "hook_text": r["hook_text"],
        }
        for r in rows
    ]


def debug_short_chapters_and_ads(
    conn: sqlite3.Connection, min_chars: int = 150
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """检查短章率过高与广告模式命中作品。"""
    rows = conn.execute(
        "SELECT book_id, title, source_path FROM essence_books ORDER BY id ASC"
    ).fetchall()
    short_books: list[dict[str, Any]] = []
    ad_matches: list[dict[str, Any]] = []

    for eb in rows:
        p = Path(eb["source_path"])
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        raw_chaps = re.split(
            r"\n(?=第[0-9零一二三四五六七八九十百千万]+[章节回卷]|Chapter [0-9]+)",
            text,
        )
        short_cnt = sum(1 for c in raw_chaps if len(c.strip()) < min_chars)
        total_chaps = max(len(raw_chaps), 1)
        if short_cnt > total_chaps * 0.05 and short_cnt > 10:
            short_books.append(
                {
                    "book_id": eb["book_id"],
                    "title": eb["title"],
                    "short_count": short_cnt,
                    "total_count": total_chaps,
                    "ratio": short_cnt / total_chaps,
                }
            )

        for m in AD_PATTERNS:
            hit = re.search(m, text)
            if hit:
                ad_matches.append(
                    {
                        "book_id": eb["book_id"],
                        "title": eb["title"],
                        "pattern": m,
                        "snippet": text[max(0, hit.start() - 20) : hit.end() + 20],
                    }
                )

    return short_books, ad_matches


def debug_corpus_flaws(
    db_source: str | Path | sqlite3.Connection,
) -> dict[str, Any]:
    """对语料库多维度质量瑕疵执行综合深度诊断。"""
    if isinstance(db_source, sqlite3.Connection):
        conn = db_source
        should_close = False
    else:
        conn = sqlite3.connect(str(db_source))
        conn.row_factory = sqlite3.Row
        should_close = True

    try:
        short_assets = debug_short_assets(conn)
        short_chains = debug_short_chains(conn)
        short_books, ad_matches = debug_short_chapters_and_ads(conn)
        return {
            "short_assets": short_assets,
            "short_chains": short_chains,
            "short_books": short_books,
            "ad_matches": ad_matches,
        }
    finally:
        if should_close:
            conn.close()


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="语料库资产/伏笔链/切片及广告深度瑕疵排查工具"
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

    results = debug_corpus_flaws(db_path)

    if not args.quiet:
        print(f"=== 调查维度一：{len(results['short_assets'])} 张资产卡内容过短/为空 ===")
        for a in results["short_assets"]:
            print(
                f"Asset {a['id']}: 《{a['title']}》 category={a['category']} "
                f"len={a['content_len']} content={repr(a['content'])}"
            )

        print(f"\n=== 调查维度二：{len(results['short_chains'])} 条伏笔链钩子文本过短/为空 ===")
        for c in results["short_chains"]:
            print(
                f"Chain {c['id']}: 《{c['title']}》 "
                f"len={c['hook_len']} hook_text={repr(c['hook_text'])}"
            )

        print("\n=== 调查维度三：异常短章作品与广告命中 ===")
        for sb in results["short_books"]:
            print(
                f"短章多: 《{sb['title']}》 短章数={sb['short_count']}/{sb['total_count']} "
                f"({sb['ratio']:.1%})"
            )
        for ad in results["ad_matches"]:
            print(f"广告命中: 《{ad['title']}》 模式={ad['pattern']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

