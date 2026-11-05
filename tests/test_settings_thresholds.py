"""设置页质量阈值是否真的生效（2026-11-03）。

背景：用户在设置页调「质量及格线 / 质量警告线」，保存成功、读回来也对，
但**没有任何质检代码读这两个值**——改完再检查，结果纹丝不动。
根因是 scripts/ 不能 import gui/（分层铁律），而 gui 层也没人把它传下去。

修法：gui/engine_adapter._with_user_thresholds 在唯一出口处合并
（题材包显式配置 > 用户设置 > 默认 75/60），chapter_check 与
resolve_thresholds 两条路径都经过它。

本测试守护三点：
1. 用户设置能改变判定；
2. 题材包已显式配置时不被全局设置覆盖（题材专门标定优先）；
3. 非法设置（非 int / 越界 / warn>pass）静默回退，不影响质检。
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


class TestSettingsThresholdsTakeEffect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    def _write_settings(self, thresholds: dict) -> None:
        from gui import system_service
        path = system_service._settings_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"thresholds": thresholds}, ensure_ascii=False),
                        encoding="utf-8")
        # settings 可能有短 TTL 缓存，直接清掉以免串测
        cache = getattr(system_service, "_SETTINGS_CACHE", None)
        if isinstance(cache, dict):
            cache.clear()

    def setUp(self) -> None:
        from gui import system_service
        path = system_service._settings_file()
        if path.exists():
            path.unlink()

    def test_user_settings_change_resolved_thresholds(self):
        from gui import engine_adapter
        self.assertEqual(engine_adapter.resolve_thresholds(None), (75, 60))
        self._write_settings({"quality_pass_line": 88, "quality_warn_line": 70})
        self.assertEqual(engine_adapter.resolve_thresholds(None), (88, 70))

    def test_user_settings_change_verdict(self):
        """端到端：把及格线抬到 99，同一段正文应从 PASS 变 FAIL。"""
        from gui import engine_adapter
        sample = ROOT / "samples" / "示例-玄幻.txt"
        if not sample.is_file():
            self.skipTest("缺少示例语料")
        text = sample.read_text(encoding="utf-8")[:2500]
        base = engine_adapter.chapter_check(text, None)
        self.assertEqual(base.get("verdict"), "PASS", "基线应是高分文本（约 87 分）")
        self._write_settings({"quality_pass_line": 99, "quality_warn_line": 98})
        strict = engine_adapter.chapter_check(text, None)
        self.assertEqual(
            strict.get("verdict"), "FAIL",
            "抬高及格线后判定没变，说明设置页阈值仍未生效",
        )

    def test_genre_pack_explicit_config_wins(self):
        from gui import engine_adapter
        self._write_settings({"quality_pass_line": 88, "quality_warn_line": 70})
        pack = {"quality_thresholds": {"pass": 82, "warn": 66}}
        self.assertEqual(engine_adapter.resolve_thresholds(pack), (82, 66))

    def test_invalid_settings_fall_back_silently(self):
        from gui import engine_adapter
        for bad in (
            {"quality_pass_line": 50, "quality_warn_line": 80},   # warn > pass
            {"quality_pass_line": "88", "quality_warn_line": 70},  # 字符串
            {"quality_pass_line": 180, "quality_warn_line": 70},   # 越界
            {"quality_pass_line": True, "quality_warn_line": 70},  # bool
        ):
            with self.subTest(settings=bad):
                self._write_settings(bad)
                self.assertEqual(engine_adapter.resolve_thresholds(None), (75, 60))

    def test_missing_settings_file_uses_default(self):
        from gui import engine_adapter
        self.assertEqual(engine_adapter.resolve_thresholds(None), (75, 60))


class TestWritingDefaultsFromSettings(unittest.TestCase):
    """设置页的写作默认值（default_words / consistency_target）必须真的被用上。

    2026-11-03：这两项此前只存不读——生成章节时用的是函数签名里写死的
    2400 / 90，用户改了设置没有任何效果。
    """

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    def _write(self, payload: dict) -> None:
        from gui import system_service
        path = system_service._settings_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def setUp(self) -> None:
        from gui import system_service
        path = system_service._settings_file()
        if path.exists():
            path.unlink()

    def test_defaults_when_no_settings(self):
        from gui import writing_service
        self.assertEqual(writing_service._settings_defaults(),
                         {"words": 2400, "target_score": 90, "max_attempts": 3})

    def test_settings_override_defaults(self):
        from gui import writing_service
        self._write({"writing": {"default_words": 3500, "max_attempts": 5},
                     "thresholds": {"consistency_target": 95}})
        self.assertEqual(writing_service._settings_defaults(),
                         {"words": 3500, "target_score": 95, "max_attempts": 5})

    def test_out_of_range_settings_fall_back(self):
        from gui import writing_service
        self._write({"writing": {"default_words": 999999, "max_attempts": 99},
                     "thresholds": {"consistency_target": 150}})
        self.assertEqual(writing_service._settings_defaults(),
                         {"words": 2400, "target_score": 90, "max_attempts": 3})

    def test_router_passes_none_so_service_can_decide(self):
        """路由层不得再用写死的 2400/90 覆盖设置。"""
        from gui import router
        self.assertIsNone(router._safe_int_or_none(None, "words"))
        self.assertIsNone(router._safe_int_or_none(None, "target_score"))
        self.assertEqual(router._safe_int_or_none(3000, "words"), 3000)


if __name__ == "__main__":
    unittest.main()
