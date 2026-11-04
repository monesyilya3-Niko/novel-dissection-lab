"""分析任务的暂停/恢复状态一致性（2026-11-03）。

背景：pause 把 state.status 写成 "paused"，但 resume 只 clear 了内存里的
Event，没有回写状态。结果分析已经继续跑批，/api/status 却永远显示 paused，
前端据此不再刷新进度——用户点了「继续」却看不到任何变化。
"""
from __future__ import annotations

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


class TestResumeRestoresStatus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    def test_resume_status_helper_flips_paused_to_running(self):
        from gui import services, state_store
        bid = "状态测试书"
        state = state_store.load_state(bid)
        state["status"] = "paused"
        state_store.save_state(state)

        services._resume_status_if_paused(bid)
        self.assertEqual(state_store.load_state(bid)["status"], "running")

    def test_helper_is_idempotent_when_not_paused(self):
        from gui import services, state_store
        bid = "状态测试书2"
        state = state_store.load_state(bid)
        state["status"] = "running"
        state_store.save_state(state)

        services._resume_status_if_paused(bid)
        self.assertEqual(state_store.load_state(bid)["status"], "running")

    def test_helper_survives_corrupt_state(self):
        """状态文件读不出来时不能抛，分析要继续跑。"""
        from gui import services
        services._resume_status_if_paused("根本不存在的书")  # 不应抛异常


if __name__ == "__main__":
    unittest.main()
