#!/usr/bin/env python3
"""全库爬虫切片污染与结构性缺陷深度普查引擎。

用于检测从爬虫抓取/切片入库的小说是否存在常见爬虫污染缺陷：
1. 正文误作标题率高（标题包含逗号、句号、冒号、省略号等标点或长度超标）。
2. 物理短章切片率高（切片内容长度不足 150 字）。
3. 章节标题异常高频重复（例如大量重复的"第一节"、"第一章"）。
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

CHAPTER_TITLE_PATTERN = re.compile(
    r"^(第[0-9零一二三四五六七八九十百千万]+[章节回卷]|Chapter [0-9]+)"
)
RAW_CHAPTER_SPLIT_PATTERN = re.compile(
    r"\n(?=第[0-9零一二三四五六七八九十百千万]+[章节回卷]|Chapter [0-9]+)"
)
SUSPICIOUS_PUNCTUATION = ("，", "。", "！", "？", "……", "“", "”", "：", "；")
COMMON_REPEATED_TITLES = {"第一节", "第二节", "第三节", "第四节", "第一章"}


def get_default_corpus_db() -> Path:
    """获取默认语料库数据库路径。"""
    env_db = os.environ.get("EXOSCRIBE_CORPUS_DB")
    if env_db:
        return Path(env_db).resolve()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "暮冬念春" / "index.db"
    return Path.home() / ".local" / "share" / "暮冬念春" / "index.db"


def extract_chapter_titles(content: str) -> list[str]:
    """从小说正文中提取所有章节标题行。"""
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    return [line for line in lines if CHAPTER_TITLE_PATTERN.match(line)]


def detect_sentence_like_titles(
    ch_titles: list[str], max_len: int = 30
) -> list[str]:
    """检测疑似正文误识别为标题的条目（含有常见标点或过长）。"""
    return [
        t
        for t in ch_titles
        if len(t) > max_len or any(punc in t for punc in SUSPICIOUS_PUNCTUATION)
    ]


def split_raw_chapters(content: str) -> list[str]:
    """按章节标题切分小说章节正文。"""
    return [c.strip() for c in RAW_CHAPTER_SPLIT_PATTERN.split(content) if c.strip()]


def detect_short_chapters(
    raw_chaps: list[str], min_chars: int = 150
) -> list[str]:
    """检测物理短小章节（字符数不足阈值）。"""
    return [c for c in raw_chaps if len(c) < min_chars]


def detect_max_duplicate_title(ch_titles: list[str]) -> tuple[str, int]:
    """计算出现次数最多的标题及其频次。"""
    if not ch_titles:
        return ("", 0)
    title_counts = Counter(ch_titles)
    most_common = title_counts.most_common(1)
    return most_common[0] if most_common else ("", 0)


def audit_book_text(
    content: str,
    *,
    short_ratio_thresh: float = 0.05,
    short_count_thresh: int = 10,
    sentence_ratio_thresh: float = 0.08,
    sentence_count_thresh: int = 10,
    dup_count_thresh: int = 15,
) -> dict[str, Any]:
    """对单本小说正文字符串执行爬虫切片缺陷核验。"""
    ch_titles = extract_chapter_titles(content)
    sentence_like = detect_sentence_like_titles(ch_titles)
    sentence_ratio = len(sentence_like) / max(len(ch_titles), 1)

    raw_chaps = split_raw_chapters(content)
    short_chaps = detect_short_chapters(raw_chaps)
    short_ratio = len(short_chaps) / max(len(raw_chaps), 1)

    max_dup_title, max_dup_count = detect_max_duplicate_title(ch_titles)

    is_defective = False
    reasons: list[str] = []

    if short_ratio > short_ratio_thresh and len(short_chaps) > short_count_thresh:
        is_defective = True
        reasons.append(
            f"短章率过高: {short_ratio:.1%} ({len(short_chaps)}/{len(raw_chaps)})"
        )

    if (
        sentence_ratio > sentence_ratio_thresh
        and len(sentence_like) > sentence_count_thresh
    ):
        is_defective = True
        reasons.append(
            f"正文误作标题率高: {sentence_ratio:.1%} ({len(sentence_like)}/{len(ch_titles)})"
        )

    if (
        max_dup_count > dup_count_thresh
        and max_dup_title in COMMON_REPEATED_TITLES
    ):
        is_defective = True
        reasons.append(f"重复标题过多: '{max_dup_title}' 出现 {max_dup_count} 次")

    return {
        "is_defective": is_defective,
        "reasons": reasons,
        "ch_titles_count": len(ch_titles),
        "sentence_like_count": len(sentence_like),
        "sentence_ratio": sentence_ratio,
        "raw_chaps_count": len(raw_chaps),
        "short_chaps_count": len(short_chaps),
        "short_ratio": short_ratio,
        "max_dup_title": max_dup_title,
        "max_dup_count": max_dup_count,
    }


def audit_corpus_db(
    db_source: str | Path | sqlite3.Connection,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """对语料库数据库中的全部书籍进行切片缺陷普查。"""
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
        if limit is not None and limit > 0:
            sql += f" LIMIT {limit}"

        rows = conn.execute(sql).fetchall()
        defects: list[dict[str, Any]] = []

        for r in rows:
            p = Path(r["source_path"])
            if not p.is_file():
                defects.append(
                    {
                        "id": r["id"],
                        "book_id": r["book_id"],
                        "title": r["title"],
                        "genre": r["genre"],
                        "total_chapters": r["total_chapters"],
                        "total_chars": r["total_chars"],
                        "reasons": [f"物理文件缺失或不可读: {p}"],
                        "metrics": None,
                    }
                )
                continue

            content = p.read_text(encoding="utf-8", errors="ignore")
            res = audit_book_text(content)
            if res["is_defective"]:
                defects.append(
                    {
                        "id": r["id"],
                        "book_id": r["book_id"],
                        "title": r["title"],
                        "genre": r["genre"],
                        "total_chapters": r["total_chapters"],
                        "total_chars": r["total_chars"],
                        "reasons": res["reasons"],
                        "metrics": res,
                    }
                )

        return defects
    finally:
        if should_close:
            conn.close()


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="全库爬虫切片污染全量深度普查工具"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="语料库数据库 index.db 路径（默认从环境变量或本地 AppData 获取）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制普查的最大书籍数量（便于快速巡检）",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静默模式，只通过退出码返回结果（存在缺陷返回 1，正常返回 0）",
    )
    args = parser.parse_args(argv)

    db_path = Path(args.db).resolve() if args.db else get_default_corpus_db()
    if not db_path.is_file():
        if not args.quiet:
            print(f"[ERROR] 语料库数据库文件不存在: {db_path}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"开始对全库数据库执行爬虫切片污染普查: {db_path}\n")

    defects = audit_corpus_db(db_path, limit=args.limit)

    if not args.quiet:
        print(f"【普查结论】发现 {len(defects)} 部存在结构性爬虫污染或物理缺失的作品：")
        for d in defects:
            reasons_str = "; ".join(d["reasons"])
            print(
                f"ID={d['id']:03d} | 《{d['title']}》 | "
                f"{d['total_chapters']}章 | {d['total_chars']:,}字 | 原因: {reasons_str}"
            )

    return 1 if defects else 0
