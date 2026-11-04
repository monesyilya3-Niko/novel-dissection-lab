"""写作任务取消能力（2026-11-03）。

背景：一次生成最多 N 轮改写，每轮都可能撞上 180s 的 LLM 超时——合计可达
数分钟，并且此前**没有任何中断手段**，用户只能等它跑完。

实现：cancel() 置 cancelled 标记，后台线程在下一轮开始前检查并退出。
正在进行的单次 LLM 调用不会被强行打断（读一半丢掉没意义，也浪费已花 token），
但结果不会被采用、不会落盘。
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


class TestWritingTaskCancel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    def _register(self, task_id: str, status: str = "running") -> None:
        from gui import writing_service
        with writing_service._WRITING_LOCK:
            writing_service._WRITING_TASKS[task_id] = {
                "task_id": task_id, "status": status, "cancelled": False,
                "attempts": [], "message": "",
            }

    def test_cancel_sets_flag_on_active_task(self):
        from gui import writing_service
        self._register("t-active")
        r = writing_service.cancel("t-active")
        self.assertTrue(r["cancelled"])
        with writing_service._WRITING_LOCK:
            self.assertTrue(writing_service._WRITING_TASKS["t-active"]["cancelled"])

    def test_cancel_unknown_task_raises_404(self):
        from gui import writing_service
        from gui.services import ServiceError
        with self.assertRaises(ServiceError) as ctx:
            writing_service.cancel("不存在的任务")
        self.assertEqual(ctx.exception.code, 404)

    def test_cancel_finished_task_is_noop(self):
        """已结束的任务调用取消不该报错，也不该把状态改回去。"""
        from gui import writing_service
        self._register("t-done", status="done")
        r = writing_service.cancel("t-done")
        self.assertEqual(r["status"], "done")
        self.assertFalse(r["cancelled"])

    def test_route_registered(self):
        from gui import router
        paths = [p.pattern for m, p, _f in router.ROUTES if m == "POST"]
        self.assertTrue(any("cancel" in p for p in paths),
                        "缺少写作任务取消端点")

    def test_route_validates_task_id(self):
        from gui import router
        from gui.services import ServiceError
        handler = next(f for m, p, f in router.ROUTES
                       if m == "POST" and p.pattern.endswith("/cancel$"))
        with self.assertRaises(ServiceError):
            handler({"task_id": ""}, {})


if __name__ == "__main__":
    unittest.main()
