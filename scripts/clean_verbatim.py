#!/usr/bin/env python3
"""
原文引用自动清洗器 — 从资产 JSON 中清除夹带的原文台词

Pass2/3 模型输出常把「例如」示例写成原文引用（如 '例如：'她把我衣服扒了，拍几张裸照散出去''），
这违反合规红线（连续12字匹配原文）。本脚本自动清洗：
- 删除「例如/比如/如」后紧跟的引号包裹片段（>8字视为疑似原文）
- 删除所有引号内 >12 字且与原文匹配的片段
- 保留抽象描述

用法:
  python clean_verbatim.py <asset.json> <book.txt> [--apply]
  （不带 --apply 只报告；带 --apply 原地修改）
"""
import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import chapter_loader
import compliance as comp

# 成对引号匹配器：严格要求首尾同型配对，英文单引号要求非字母边界以避开 don't / can't 等缩写
_PAIRED_QUOTES = (
    ("「", "」", re.compile(r"「([^」\n]+)」")),
    ("『", "』", re.compile(r"『([^』\n]+)』")),
    ("“", "”", re.compile(r"“([^”\n]+)”")),
    ("‘", "’", re.compile(r"‘([^’\n]+)’")),
    ('"', '"', re.compile(r'"([^"\n]+)"')),
    ("'", "'", re.compile(r"(?<![A-Za-z])'([^'\n]+)'(?![A-Za-z])")),
)

_EXAMPLE_QUOTE_PATTERNS = tuple(
    re.compile(
        r"(例如|比如|如)\s*[：:]\s*"
        + (
            r"(?<![A-Za-z])'([^'\n]{9,})'(?![A-Za-z])"
            if op == "'"
            else re.escape(op) + r"([^" + re.escape(cl) + r"\n]{9,})" + re.escape(cl)
        )
    )
    for op, cl, _ in _PAIRED_QUOTES
)

_EMPTY_QUOTE_PATTERNS = tuple(
    re.compile(
        r"(?<![A-Za-z])'\s*'(?![A-Za-z])"
        if op == "'"
        else re.escape(op) + r"\s*" + re.escape(cl)
    )
    for op, cl, _ in _PAIRED_QUOTES
)


def clean_string(s: str, ngram: set, path: str) -> tuple:
    """清洗单个字符串，返回 (清洗后, 是否改动)。"""
    orig = s
    # 1. 删除「例如/比如/如」后引号内 >8 字的片段（模型常把原文当示例）
    for pat in _EXAMPLE_QUOTE_PATTERNS:
        s = pat.sub(r"\1", s)

    # 2. 删除引号内 ≥12 字且滑窗命中原文的片段（无 40 字长度上限，O(N) 不回溯）
    def drop_quoted(m):
        frag = m.group(1)
        frag_c = re.sub(r"\s+", "", frag)
        w = comp.WINDOW
        if len(frag_c) >= w and ngram and any(
            frag_c[i:i + w] in ngram for i in range(len(frag_c) - w + 1)
        ):
            return ""
        return m.group(0)

    for _op, _cl, qpat in _PAIRED_QUOTES:
        s = qpat.sub(drop_quoted, s)

    # 3. 清理清洗后可能残留的空引号对
    for epat in _EMPTY_QUOTE_PATTERNS:
        s = re.sub(r"[、，,]\s*" + epat.pattern + r"\s*[、，,]", "、", s)
        s = re.sub(r"[、，,]\s*" + epat.pattern, "", s)

    # 4. 清理删除片段后产生的标点冗余（如"、。"、"、、"、"，，"）
    s = re.sub(r"[、，,]\s*[。；;]", "。", s)
    s = re.sub(r"[、，,]{2,}", "、", s)
    return s, s != orig


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="原文引用清洗器")
    ap.add_argument("asset", help="资产 JSON")
    ap.add_argument("book", help="原文 TXT")
    ap.add_argument("--apply", action="store_true", help="原地修改（缺省只报告）")
    args = ap.parse_args(argv)

    asset_path = Path(args.asset)
    asset = json.loads(asset_path.read_text(encoding="utf-8-sig"))
    book = chapter_loader.read_text_file(Path(args.book))
    ngram = comp.build_ngram_index(book)

    changes = []

    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif isinstance(node, str):
            cleaned, changed = clean_string(node, ngram, path)
            if changed:
                changes.append((path, node, cleaned))
                # 需要写回——用指针方式麻烦，这里收集后统一处理

    # 用引用方式收集写回点
    write_points = []

    def walk2(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, str):
                    cleaned, changed = clean_string(v, ngram, path)
                    if changed:
                        write_points.append((node, k, v, cleaned))
                else:
                    walk2(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                if isinstance(v, str):
                    cleaned, changed = clean_string(v, ngram, path)
                    if changed:
                        write_points.append((node, i, v, cleaned))
                else:
                    walk2(v, f"{path}[{i}]")

    walk2(asset)
    print(f"发现 {len(write_points)} 处原文引用待清洗：")
    for _parent, key, old, new in write_points[:10]:
        print(f"  {key}: …{old[:50]}…")
        print(f"    → …{new[:50]}…")

    if args.apply and write_points:
        for parent, key, _old, new in write_points:
            parent[key] = new
        payload = json.dumps(asset, ensure_ascii=False, indent=2)
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=str(asset_path.parent), suffix=".tmp", delete=False
        ) as fh:
            tmp_path = Path(fh.name)
            fh.write(payload)
        try:
            os.replace(tmp_path, asset_path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
        print(f"\n✓ 已清洗 {len(write_points)} 处并保存")

    # 复扫
    errs, warns = comp.scan_asset(asset, ngram)
    print(f"\n复扫: {len(errs)} 硬错误, {len(warns)} 警告")
    for e in errs[:5]:
        print(f"  ✗ {e}")

    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
