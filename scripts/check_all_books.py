#!/usr/bin/env python3
"""全量入库小说深度自检与质量核验引擎。

核验维度：
1. 检查物理文件存在性与大小（非空）
2. 检查书籍资产卡（assets_cnt=4）与伏笔链（chains_cnt=1）数量一致性
3. 检查正文首末章节完整性与首章开篇特征（第1章/引子/序/楔子）
4. 检查全库重名作品
5. 检查书名是否包含冗余爬虫标签（正文全/全集/选集/未完/番外/校对版）
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

CLEAN_START_PATTERN = re.compile(
    r"(第0*[01一][章节回卷]|Chapter 0?1\b|序|引子|楔子)"
)
CHAPTER_HEADER_PATTERN = re.compile(
    r"^(第[0-9零一二三四五六七八九十百千万]+[章节回卷]|Chapter [0-9]+)"
)
SUSPICIOUS_TITLE_TAGS = (
    "（正文全）",
    "【含",
    "正文",
    "全集",
    "选集",
    "未完",
    "番外",
    "校对版",
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


def is_clean_start_chapter(first_ch: str) -> bool:
    """判断首章标题是否符合规范的开篇特征。"""
    return bool(CLEAN_START_PATTERN.search(first_ch))


def has_title_tags(title: str) -> bool:
    """检查书名是否含有未清洗的爬虫附带标记。"""
    return any(bad in title for bad in SUSPICIOUS_TITLE_TAGS)


def check_corpus_books(
    db_source: str | Path | sqlite3.Connection,
    *,
    expected_assets_cnt: int = 4,
    expected_chains_cnt: int = 1,
) -> dict[str, Any]:
    """对语料库中的所有书籍执行深度质量核验。"""
    if isinstance(db_source, sqlite3.Connection):
        conn = db_source
        should_close = False
    else:
        conn = sqlite3.connect(str(db_source))
        conn.row_factory = sqlite3.Row
        should_close = True

    try:
        sql = """
            SELECT eb.id, eb.book_id, eb.title, eb.genre, eb.total_chapters, eb.total_chars, eb.source_path,
                   (SELECT count(*) FROM essence_assets ea WHERE ea.book_id = eb.book_id) as assets_cnt,
                   (SELECT count(*) FROM essence_chains ec WHERE ec.book_id = eb.book_id) as chains_cnt
            FROM essence_books eb
            ORDER BY eb.id ASC
        """
        rows = conn.execute(sql).fetchall()

        flaws: list[str] = []
        suspicious_starts: list[dict[str, Any]] = []
        duplicate_titles: dict[str, list[int]] = {}
        flagged_titles: list[dict[str, Any]] = []
        book_details: list[dict[str, Any]] = []

        for idx, r in enumerate(rows, start=1):
            t = r["title"]
            p = Path(r["source_path"])
            ch = r["total_chapters"]
            w = r["total_chars"]
            g = r["genre"]

            if has_title_tags(t):
                flagged_titles.append({"index": idx, "title": t, "genre": g})

            if t in duplicate_titles:
                duplicate_titles[t].append(idx)
            else:
                duplicate_titles[t] = [idx]

            book_info: dict[str, Any] = {
                "index": idx,
                "id": r["id"],
                "book_id": r["book_id"],
                "title": t,
                "genre": g,
                "total_chapters": ch,
                "total_chars": w,
                "source_path": str(p),
                "assets_cnt": r["assets_cnt"],
                "chains_cnt": r["chains_cnt"],
                "first_chapter": None,
                "last_chapter": None,
            }
            book_details.append(book_info)

            # 1. 物理文件存在
            if not p.is_file() or p.stat().st_size == 0:
                flaws.append(f"[{idx:03d}] 《{t}》 物理文件缺失或为空: {p}")
                continue

            # 2. 资产卡与链
            if r["assets_cnt"] != expected_assets_cnt:
                flaws.append(
                    f"[{idx:03d}] 《{t}》 资产卡数量异常: {r['assets_cnt']} != {expected_assets_cnt}"
                )
            if r["chains_cnt"] != expected_chains_cnt:
                flaws.append(
                    f"[{idx:03d}] 《{t}》 伏笔链数量异常: {r['chains_cnt']} != {expected_chains_cnt}"
                )

            # 3. 读文件检查章节
            text = p.read_text(encoding="utf-8", errors="ignore")
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            ch_headers = [l for l in lines if CHAPTER_HEADER_PATTERN.match(l)]

            if not ch_headers:
                flaws.append(f"[{idx:03d}] 《{t}》 未提取到章节标题")
                continue

            first_ch = ch_headers[0]
            last_ch = ch_headers[-1]
            book_info["first_chapter"] = first_ch
            book_info["last_chapter"] = last_ch

            if not is_clean_start_chapter(first_ch):
                suspicious_starts.append(
                    {
                        "index": idx,
                        "title": t,
                        "first_chapter": first_ch,
                        "last_chapter": last_ch,
                        "total_chapters": ch,
                        "total_chars": w,
                    }
                )

        dups = {k: v for k, v in duplicate_titles.items() if len(v) > 1}

        return {
            "total_records": len(rows),
            "flaws": flaws,
            "suspicious_starts": suspicious_starts,
            "duplicate_titles": dups,
            "flagged_titles": flagged_titles,
            "books": book_details,
        }
    finally:
        if should_close:
            conn.close()


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="全量入库小说深度自检与质量核验工具"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="语料库数据库 index.db 路径（默认从环境变量或本地 AppData 获取）",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="严格模式：存在任何瑕疵或异常首章均返回非零退出码",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静默模式，只通过退出码返回结果",
    )
    args = parser.parse_args(argv)

    db_path = Path(args.db).resolve() if args.db else get_default_corpus_db()
    if not db_path.is_file():
        if not args.quiet:
            print(f"[ERROR] 语料库数据库文件不存在: {db_path}", file=sys.stderr)
        return 1

    report = check_corpus_books(db_path)

    if not args.quiet:
        print("=== 深度核验入库小说质量 ===")
        print(f"数据库记录数: {report['total_records']}")

        flaws = report["flaws"]
        print(f"\n【1. 物理与结构瑕疵】发现缺陷数: {len(flaws)}")
        for f in flaws:
            print("  -", f)

        suspicious = report["suspicious_starts"]
        print(f"\n【2. 首章疑似残缺/非从第一章开始】数量: {len(suspicious)}")
        for s in suspicious:
            print(
                f"  - 序号 {s['index']:03d} 《{s['title']}》: "
                f"首章='{s['first_chapter']}' | 末章='{s['last_chapter']}' | "
                f"章节数={s['total_chapters']} | 字数={s['total_chars']:,}"
            )

        dups = report["duplicate_titles"]
        print(f"\n【3. 重复书名】数量: {len(dups)}")
        for k, v in dups.items():
            print(f"  - 书名《{k}》出现在序号: {v}")

        flagged = {item["index"] for item in report["flagged_titles"]}
        print(f"\n【4. 全量 {report['total_records']} 本书名与特征清单】")
        for b in report["books"]:
            flag = " [⚠️ 包含附带标记需清洗]" if b["index"] in flagged else ""
            print(
                f"  {b['index']:03d}. 《{b['title']}》 [{b['genre']}] - "
                f"{b['total_chapters']}章 / {b['total_chars']:,}字{flag}"
            )

    has_issues = bool(
        report["flaws"] or report["suspicious_starts"] or report["duplicate_titles"]
    )
    if args.strict and has_issues:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
