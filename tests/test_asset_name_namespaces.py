"""GUI 与 CLI 的资产命名空间必须互通（2026-11-04）。

两套命名并存：

- GUI：``book_id = {书名}-{8位hash}``（``state_store.book_id_from_title``）
  → 期望 ``我的书-4519bf2c-voice-card.json``
- CLI：pipeline / assemble / batch 落盘用**纯书名**
  → 实际 ``我的书-voice-card.json``

导致 GUI 导入一本 CLI 已经拆完的书后，结果页资产全空——不是没拆，
是名字对不上。``_load_assembled_card`` 现在先找带 hash 的，找不到再按
裸书名回退。
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

import _isolation  # noqa: E402


class TestAssetNameNamespaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()
        from gui import config
        config.ASSETS_ROOT.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    def _write_card(self, name: str, pov: str) -> None:
        from gui import config
        (config.ASSETS_ROOT / name).write_text(
            json.dumps({"meta": {"source_title": "书"}, "narration": {"pov": pov}},
                       ensure_ascii=False),
            encoding="utf-8")

    def test_falls_back_to_bare_title(self):
        """只有 CLI 的裸书名资产时，GUI 也要能读到。"""
        from gui import services
        self._write_card("命名测试书-voice-card.json", "CLI 写的")
        got = services._load_assembled_card("命名测试书-abcdef12", "voice")
        self.assertEqual((got.get("narration") or {}).get("pov"), "CLI 写的")

    def test_prefers_hashed_name_when_both_exist(self):
        """两者都存在时优先 GUI 自己的（带 hash）。"""
        from gui import services
        self._write_card("双份书-voice-card.json", "CLI")
        self._write_card("双份书-deadbeef-voice-card.json", "GUI")
        got = services._load_assembled_card("双份书-deadbeef", "voice")
        self.assertEqual((got.get("narration") or {}).get("pov"), "GUI")

    def test_hashed_name_only(self):
        from gui import services
        self._write_card("仅GUI书-11112222-voice-card.json", "只有 GUI")
        got = services._load_assembled_card("仅GUI书-11112222", "voice")
        self.assertEqual((got.get("narration") or {}).get("pov"), "只有 GUI")

    def test_missing_returns_empty(self):
        from gui import services
        self.assertEqual(services._load_assembled_card("根本不存在的书-00000000", "voice"), {})

    def test_non_hash_suffix_not_stripped(self):
        """book_id 不以 8 位 hex 结尾时，不做剥离（避免误伤真实书名）。"""
        from gui import services
        self._write_card("普通名-voice-card.json", "裸名")
        # book_id 本身没有 hash 后缀 → 直接按原样找，命中
        got = services._load_assembled_card("普通名", "voice")
        self.assertEqual((got.get("narration") or {}).get("pov"), "裸名")


if __name__ == "__main__":
    unittest.main()
