#!/usr/bin/env python3
"""用题材文风卡的实测证据标定 genre-pack 的对话占比区间。

背景（2026-11-03）：45 个题材包的 ``quality_thresholds.dialogue_optimal``
是同一组通用默认值 ``(0.15, 0.35)``，而实际上题材之间的对话密度差异不小
（实测 19%~33%）。通用默认值把「武侠/历史」与「都市日常」按同一标准量，
前者被误判为对话不足、后者被误判为对话过量。

数据来源纪律：**只搬运已存在的实测证据，不编造。**
``genre-prose-card-genre-*.json`` 的 ``meta.provenance.evidence`` 里记录了
抽样实测的「对话约占 N%」（样本说明：本地同题材长篇样本，抽样 24 本，
前/中/后各 24 个章节段，共 72 个）。本脚本以该值为中心，取 ±8 个百分点
作为满分区：

    满分区 = [N/100 - 0.08, N/100 + 0.08]，夹在 [0.05, 0.85]

±8 的理由：实测值是「同题材样本的平均」，单章有波动；章节级质检不该因为
一章对话偏多就判不及格。这个带宽是**经验容忍带**，不是实测值本身——
写进 meta.calibration 说明来源，避免后来者把它当成实测结论。

无实测证据的题材（agent 原创卡 16 张）**不动**，保留通用默认值，
并在 meta 里保持现状（它们本来就没有标定依据）。

用法:
    python -m scripts.calibrate_genre_thresholds --dry-run   # 只看会改什么
    python -m scripts.calibrate_genre_thresholds             # 写盘
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

#: 实测值两侧的容忍带宽（对话占比的绝对差值）
BAND_HALF_WIDTH = 0.08
#: 满分区允许的下/上界（避免极端值把区间推到 0 或 1）
BAND_FLOOR = 0.05
BAND_CEIL = 0.85
#: 实测证据的正则：文风卡里写作「对话约占 27%」
EVIDENCE_RE = re.compile(r"对话约占\s*(\d+)%")


def measured_ratio(card: dict) -> int | None:
    """从文风卡 provenance.evidence 里取出实测对话占比（百分数）；无则 None。"""
    prov = (card.get("meta") or {}).get("provenance") or {}
    if "agent-authored" in str(prov.get("source", "")):
        # agent 原创卡未经拆书实测，evidence 里即便有数字也不是实测
        return None
    m = EVIDENCE_RE.search(str(prov.get("evidence", "")))
    return int(m.group(1)) if m else None


def compute_band(pct: int) -> tuple[float, float]:
    """由实测百分比算满分区。"""
    center = pct / 100.0
    lo = max(BAND_FLOOR, round(center - BAND_HALF_WIDTH, 2))
    hi = min(BAND_CEIL, round(center + BAND_HALF_WIDTH, 2))
    return lo, hi


def calibrate_one(pack_path: Path, card_path: Path, dry_run: bool) -> dict | None:
    """标定单个题材包；返回变更记录，未变动返回 None。"""
    card = json.loads(card_path.read_text(encoding="utf-8"))
    pct = measured_ratio(card)
    if pct is None:
        return None

    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    th = pack.setdefault("quality_thresholds", {})
    if not isinstance(th, dict):
        return None
    lo, hi = compute_band(pct)
    before = th.get("dialogue_optimal")
    if isinstance(before, dict) and before.get("min") == lo and before.get("max") == hi:
        return None

    th["dialogue_optimal"] = {"min": lo, "max": hi}
    pack.setdefault("meta", {})["calibration"] = {
        "dialogue_optimal": {
            "method": f"实测对话占比 {pct}% ± {int(BAND_HALF_WIDTH * 100)} 个百分点",
            "measured_pct": pct,
            "source": card_path.name,
            "evidence": "文风卡 provenance.evidence 记录的抽样实测（24 本 × 前中后各 24 段）",
        }
    }
    if not dry_run:
        pack_path.write_text(
            json.dumps(pack, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    return {
        "slug": pack_path.name.replace("-genre-pack.json", ""),
        "measured_pct": pct,
        "before": before,
        "after": {"min": lo, "max": hi},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="用实测证据标定题材包对话占比区间")
    ap.add_argument("--dry-run", action="store_true", help="只打印变更，不写盘")
    args = ap.parse_args(argv)

    changed, skipped = [], 0
    for pack_path in sorted(ASSETS.glob("*-genre-pack.json")):
        slug = pack_path.name.replace("-genre-pack.json", "")
        card_path = ASSETS / f"genre-prose-card-genre-{slug}.json"
        if not card_path.exists():
            skipped += 1
            continue
        rec = calibrate_one(pack_path, card_path, args.dry_run)
        if rec:
            changed.append(rec)

    for r in changed:
        print(f"  {r['slug']:26} 实测{r['measured_pct']:>3}%  "
              f"{r['before']} -> {r['after']}")
    verb = "将调整" if args.dry_run else "已调整"
    print(f"\n{verb} {len(changed)} 个；无源卡跳过 {skipped} 个")
    return 0


if __name__ == "__main__":
    sys.exit(main())
