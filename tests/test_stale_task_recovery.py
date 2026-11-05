"""崩溃后遗留的 running 状态必须能被回收（2026-11-05）。

批次状态 ``running`` 只在当前进程的主循环里被推进成 success/failed。
进程被杀或崩溃后，落盘的 running 没有任何代码会再改它：

- 前端把该批画成「运行中」直到永远；
- ``retry_failed`` 只收 ``failed``，也重试不到它；
- 任务级 ``running``/``paused`` 让界面看起来还在跑/还在暂停。

实测生产库 ``analysis_tasks`` 里就有 1 条 running、1 条 paused 卡着。
现在服务启动时调 ``recover_stale_tasks()`` 把它们退回可重跑状态。
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


class TestStaleTaskRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()
        from gui import db
        db.init_schema()
        from gui import config
        config.STATE_JSON_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    def _seed(self, book_id: str, task_status: str, batch_states: dict):
        from gui import state_store
        st = state_store.load_state(book_id)
        st["book_id"] = book_id
        st["status"] = task_status
        st["chapter_states"] = {k: {"status": v} for k, v in batch_states.items()}
        state_store.save_state(st)

    def test_running_batch_becomes_pending(self):
        from gui import services, state_store
        self._seed("回收书1", "running", {"c1-b0": "running"})
        services.recover_stale_tasks()
        st = state_store.load_state("回收书1")
        self.assertEqual(st["chapter_states"]["c1-b0"]["status"], "pending")

    def test_success_and_failed_untouched(self):
        """success 要保留（续传靠它跳过），failed 要留给用户显式重试。"""
        from gui import services, state_store
        self._seed("回收书2", "running",
                   {"c1-b0": "success", "c1-b1": "failed", "c1-b2": "running"})
        services.recover_stale_tasks()
        st = state_store.load_state("回收书2")
        cs = st["chapter_states"]
        self.assertEqual(cs["c1-b0"]["status"], "success")
        self.assertEqual(cs["c1-b1"]["status"], "failed")
        self.assertEqual(cs["c1-b2"]["status"], "pending")

    def test_task_status_running_and_paused_become_idle(self):
        from gui import services, state_store
        for bid, status in (("回收书3", "running"), ("回收书4", "paused")):
            self._seed(bid, status, {})
            services.recover_stale_tasks()
            self.assertEqual(state_store.load_state(bid)["status"], "idle",
                             f"{status} 未被回收")

    def test_done_task_not_touched(self):
        from gui import services, state_store
        self._seed("回收书5", "done", {"c1-b0": "success"})
        services.recover_stale_tasks()
        self.assertEqual(state_store.load_state("回收书5")["status"], "done")

    def test_idempotent(self):
        """重复回收不改变结果，也不报错。"""
        from gui import services, state_store
        self._seed("回收书6", "running", {"c1-b0": "running"})
        services.recover_stale_tasks()
        first = dict(state_store.load_state("回收书6")["chapter_states"])
        services.recover_stale_tasks()
        second = dict(state_store.load_state("回收书6")["chapter_states"])
        self.assertEqual(first, second)

    def test_storage_report_lists_stuck_tasks(self):
        """生产库那两条 stuck 任务在修复前确实存在——本测试守住回收能识别它们。"""
        from gui import services
        self._seed("回收书7", "running", {"c1-b0": "running"})
        self.assertGreaterEqual(services.recover_stale_tasks(), 1)


if __name__ == "__main__":
    unittest.main()
