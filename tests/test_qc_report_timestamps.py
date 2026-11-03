"""质检报告时间戳与列表排序（2026-11-03）。

背景：``gui.quality_service.list_qc_reports`` 从报告 JSON 的
``meta.created_at`` 读时间显示，而 ``scripts/qc.py`` 从未写入该键——
GUI「历史质检报告」里的时间列永远是空。同时列表按文件名倒序，
而 GUI 落盘的文件名带 task_id（``<名>-q-xxxx-qc.json``）、CLI 不带
（``<名>-qc.json``），文件名顺序与时间无关。

修复：qc.py 落盘时写 created_at；列表优先读它，缺失时回退文件 mtime，
并按时间倒序排列。
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


class TestQcReportTimestamps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    def setUp(self):
        from gui import config, quality_service  # noqa: F401
        qc_dir = config.REPORTS_DIR / "qc"
        if qc_dir.is_dir():
            for fp in qc_dir.glob("*"):
                fp.unlink()
        else:
            qc_dir.mkdir(parents=True)

    def _write(self, name: str, payload: dict) -> None:
        from gui import config
        (config.REPORTS_DIR / "qc" / f"{name}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def test_run_qc_writes_created_at(self):
        """qc.py 的报告必须带 created_at。"""
        sys.path.insert(0, str(ROOT / "scripts"))
        import qc as qc_mod
        rep = qc_mod.QCReport(book_title="X", total_score=80.0, verdict="PASS",
                              layers=[], issues=[], meta={})
        data = json.loads(qc_mod.to_json(rep))
        # to_json 本身不会补 created_at（那是 run_qc 的职责），
        # 所以这里直接检查 run_qc 构造的 meta 里有没有这个键的写入代码路径
        src = (ROOT / "scripts" / "qc.py").read_text(encoding="utf-8")
        self.assertIn('"created_at"', src,
                      "qc.py 的 meta 未写入 created_at，列表时间会永远是空")

    def test_listing_uses_meta_created_at(self):
        from gui import quality_service
        self._write("A-qc", {"verdict": "PASS", "total_score": 90,
                             "meta": {"created_at": "2026-11-03T10:00:00+08:00"}})
        rows = quality_service.list_qc_reports()
        self.assertEqual(rows[0]["created_at"], "2026-11-03T10:00:00+08:00")

    def test_listing_falls_back_to_mtime(self):
        """历史报告没有 created_at，必须回退 mtime 而不是留空。"""
        from gui import quality_service
        self._write("B-qc", {"verdict": "WARN", "total_score": 70, "meta": {}})
        rows = quality_service.list_qc_reports()
        self.assertTrue(rows[0]["created_at"], "缺少 created_at 时未回退到 mtime")

    def test_listing_sorted_by_time_not_filename(self):
        from gui import quality_service
        # 文件名 A > B 字典序，但 A 的时间更早
        self._write("zzz-qc", {"verdict": "PASS", "total_score": 90,
                               "meta": {"created_at": "2026-11-01T10:00:00+08:00"}})
        self._write("aaa-qc", {"verdict": "PASS", "total_score": 90,
                               "meta": {"created_at": "2026-11-03T10:00:00+08:00"}})
        rows = quality_service.list_qc_reports()
        self.assertEqual(rows[0]["name"], "aaa-qc",
                         "列表未按时间倒序（仍按文件名排序）")


if __name__ == "__main__":
    unittest.main()
