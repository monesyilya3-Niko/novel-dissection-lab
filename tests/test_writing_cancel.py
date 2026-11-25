"""写作任务取消能力（2026-11-03）。

背景：一次生成最多 N 轮改写，每轮都可能撞上 180s 的 LLM 超时——合计可达
数分钟，并且此前**没有任何中断手段**，用户只能等它跑完。

实现：cancel() 置 cancelled 标记，后台线程在当前 LLM 响应返回后丢弃结果。
正在进行的单次 LLM 调用不会被强行打断（读一半丢掉没意义，也浪费已花 token），
但结果不会被采用、不会落盘。
"""
from __future__ import annotations

import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

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

    def test_cancel_during_llm_discards_passing_draft(self):
        from gui import config, writing_service

        entered = threading.Event()
        release = threading.Event()
        task_id = "t-cancel-inflight"
        req = {
            "project": "cancel-project", "chapter_no": 1,
            "task": "写一段开场", "words": 1000,
            "target_score": 80, "pass_line": 60,
            "quality_target": 60, "max_attempts": 1,
        }
        with writing_service._WRITING_LOCK:
            writing_service._WRITING_TASKS[task_id] = {
                "task_id": task_id, "status": "running", "cancelled": False,
                "attempt": 1, "attempts": [], "message": "生成中",
            }

        def blocked_chat(**_kwargs):
            entered.set()
            if not release.wait(5):
                raise TimeoutError("test did not release mock LLM")
            return {"text": "这是一份已经达标、但用户已取消的生成稿。"}

        chapter_path = config.NOVEL_DIR / req["project"] / "chapter-001.txt"
        try:
            with mock.patch.object(writing_service.engine_adapter, "llm_chat", side_effect=blocked_chat), \
                 mock.patch.object(writing_service.engine_adapter, "score_text", return_value={"score": 100, "details": []}), \
                 mock.patch.object(writing_service.engine_adapter, "chapter_check", return_value={"score": 100, "issues": []}), \
                 mock.patch.object(writing_service.engine_adapter, "save_chapter", return_value=chapter_path) as save_chapter, \
                 mock.patch("gui.writing_extra.get_chapter_words", return_value=None), \
                 mock.patch("gui.writing_extra.count_words", return_value=20), \
                 mock.patch("gui.writing_extra.record_words"):
                worker = threading.Thread(
                    target=writing_service._run_generate,
                    args=(task_id, {}, "system", req),
                    daemon=True,
                )
                worker.start()
                self.assertTrue(entered.wait(5), "mock LLM was not entered")
                writing_service.cancel(task_id)
                release.set()
                worker.join(5)

            self.assertFalse(worker.is_alive(), "cancelled worker did not stop")
            save_chapter.assert_not_called()
            with writing_service._WRITING_LOCK:
                state = dict(writing_service._WRITING_TASKS[task_id])
            self.assertEqual(state["status"], "cancelled")
            self.assertIsNone(state.get("chapter_path"))
        finally:
            release.set()
            with writing_service._WRITING_LOCK:
                writing_service._WRITING_TASKS.pop(task_id, None)

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
