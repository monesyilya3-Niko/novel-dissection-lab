"""质检的「粘贴文本」模式必须可用（2026-11-04）。

背景：``_materialize_text`` 把文本写成 ``scratch/<task_id>/input.txt``，
而 ``chapter_loader._chapter_number`` 只认 ``chapter-N`` / ``第N章`` / 纯数字，
``input`` 取不到章号 → 归入 ignored → 目录里等于没有章节，
质检直接报「未找到章节文件」。也就是说：**粘贴文本走质检这条路径整体不可用**，
用户在前端贴一段正文点质检，只会拿到一个错误。

修复：文件名改为 ``chapter-001.txt``。
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


class TestQcTextMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    def test_materialized_file_is_loadable(self):
        """落到 scratch 的文件必须能被 chapter_loader 识别出章号。"""
        from gui import config, quality_service
        fp = quality_service._materialize_text("第一章\n\n正文。", "q-test")
        self.assertEqual(fp.parent, config.STATE_ROOT / "scratch" / "q-test")

        sys.path.insert(0, str(ROOT / "scripts"))
        import chapter_loader
        diag = chapter_loader.discover_chapter_files(fp.parent)
        self.assertEqual(len(diag["files"]), 1,
                         f"落盘的临时文件未被识别为章节：{diag['ignored']}")

    def test_text_mode_qc_reaches_done(self):
        """端到端：粘贴文本跑质检必须走到 done，而不是 error。"""
        import time

        from gui import quality_service
        r = quality_service.qc(text="第一章 测试\n\n" + "正文内容，用于质检测试。" * 120,
                               llm_hook=False)
        tid = r["task_id"]
        deadline = time.time() + 90
        while time.time() < deadline:
            st = quality_service.qc_task_state(tid)
            if st["status"] in ("done", "error"):
                self.assertEqual(st["status"], "done",
                                 f"粘贴文本质检失败：{st.get('error')}")
                self.assertIsNotNone(st.get("verdict"))
                return
            time.sleep(0.5)
        self.fail("质检任务在 90s 内未结束")


if __name__ == "__main__":
    unittest.main()
