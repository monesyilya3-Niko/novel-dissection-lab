"""题材包对话区间标定守卫（2026-11-03）。

背景：45 个题材包共用同一组通用默认值 ``dialogue_optimal = (0.15, 0.35)``，
但实测对话密度差异不小（19%~33%）。通用默认把「武侠/历史」与「都市日常」
按同一尺度量，前者被判对话不足、后者被判对话过量。

标定规则（scripts/calibrate_genre_thresholds.py）：
以文风卡 provenance.evidence 里记录的实测「对话约占 N%」为中心，
取 ±8 个百分点作满分区。±8 是**容忍带**，不是实测值本身。

本测试守住三条：
1. 有实测证据的题材，区间必须落在实测值 ±8 内（不能退回通用默认）；
2. agent 原创卡（无实测依据）必须仍用默认值，不得被凭空标定；
3. 标定结果要在 meta.calibration 里留下可追溯的来源。
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ASSETS = ROOT / "assets"
DEFAULT_BAND = (0.15, 0.35)
HALF_WIDTH = 0.08


def _load_calibrator():
    spec = importlib.util.spec_from_file_location(
        "calibrate_under_test", ROOT / "scripts" / "calibrate_genre_thresholds.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _measured(card: dict) -> int | None:
    prov = (card.get("meta") or {}).get("provenance") or {}
    if "agent-authored" in str(prov.get("source", "")):
        return None
    m = re.search(r"对话约占\s*(\d+)%", str(prov.get("evidence", "")))
    return int(m.group(1)) if m else None


class TestGenreDialogueCalibration(unittest.TestCase):
    def test_compute_band_is_centred_on_measurement(self):
        cal = _load_calibrator()
        lo, hi = cal.compute_band(27)
        self.assertAlmostEqual(lo, 0.19, places=2)
        self.assertAlmostEqual(hi, 0.35, places=2)
        # 极端值被夹住，不会推出 0 或 1
        lo2, hi2 = cal.compute_band(3)
        self.assertGreaterEqual(lo2, cal.BAND_FLOOR)
        lo3, hi3 = cal.compute_band(95)
        self.assertLessEqual(hi3, cal.BAND_CEIL)

    def test_measured_genres_are_calibrated(self):
        """有实测证据的题材，区间必须围绕实测值，而不是通用默认。"""
        checked = 0
        for card_path in sorted(ASSETS.glob("genre-prose-card-genre-*.json")):
            if "index" in card_path.name:
                continue
            card = json.loads(card_path.read_text(encoding="utf-8"))
            pct = _measured(card)
            if pct is None:
                continue
            slug = card_path.name[len("genre-prose-card-genre-"):-len(".json")]
            pack_path = ASSETS / f"{slug}-genre-pack.json"
            if not pack_path.exists():
                continue
            pack = json.loads(pack_path.read_text(encoding="utf-8"))
            band = ((pack.get("quality_thresholds") or {}).get("dialogue_optimal") or {})
            lo, hi = band.get("min"), band.get("max")
            with self.subTest(genre=slug, measured=pct):
                self.assertIsNotNone(lo, f"{slug} 缺少 dialogue_optimal")
                center = pct / 100.0
                self.assertAlmostEqual(center, (lo + hi) / 2, delta=0.011,
                                       msg=f"{slug} 满分区 {lo}~{hi} 未以实测 {pct}% 为中心")
                self.assertAlmostEqual(hi - lo, 2 * HALF_WIDTH, delta=0.011,
                                       msg=f"{slug} 带宽偏离 ±{HALF_WIDTH}")
                checked += 1
        self.assertGreater(checked, 20, "带实测证据的题材应远多于 20 个")

    def test_calibration_provenance_recorded(self):
        """标定过的包必须在 meta.calibration 里写明来源，便于追溯。"""
        for pack_path in sorted(ASSETS.glob("*-genre-pack.json")):
            pack = json.loads(pack_path.read_text(encoding="utf-8"))
            cal = (pack.get("meta") or {}).get("calibration") or {}
            do = cal.get("dialogue_optimal")
            if not do:
                continue
            self.assertIn("measured_pct", do)
            self.assertIn("source", do)
            self.assertTrue(str(do.get("source", "")).startswith("genre-prose-card-"))

    def test_unmeasured_genres_keep_default(self):
        """agent 原创卡没有实测依据，必须保留默认区间，不得被凭空标定。"""
        for card_path in sorted(ASSETS.glob("genre-prose-card-genre-*.json")):
            card = json.loads(card_path.read_text(encoding="utf-8"))
            if _measured(card) is not None:
                continue
            slug = card_path.name[len("genre-prose-card-genre-"):-len(".json")]
            pack_path = ASSETS / f"{slug}-genre-pack.json"
            if not pack_path.exists():
                continue
            pack = json.loads(pack_path.read_text(encoding="utf-8"))
            cal = (pack.get("meta") or {}).get("calibration") or {}
            with self.subTest(genre=slug):
                self.assertNotIn(
                    "dialogue_optimal", cal,
                    f"{slug} 无实测证据却被标定，等于凭空造数",
                )


if __name__ == "__main__":
    unittest.main()
