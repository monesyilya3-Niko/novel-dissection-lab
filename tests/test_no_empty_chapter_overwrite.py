"""空正文绝不能覆盖已有章节（2026-11-04）。

两条独立的 P0 数据丢失路径，都由 Agent 审计发现、本测试逐条钉住：

1. CLI ``--max-attempts -5``：``or 3`` 兜得住 0 却兜不住负数，
   ``range(1, -4)`` 为空 → 一次 LLM 都不调 → ``content`` 保持 ``""``
   → ``save_chapter`` 用空串覆盖已有章节（实测 7500 字节变 0）。

2. GUI 生成：``llm_chat`` 把 ``content: null`` 归一成 ``""``（模型拒答 /
   内容过滤 / 空 choices 都走这里），空稿仍被当「最佳稿」落盘，
   任务状态还是 done（实测 3600 字节变 0）。

共同原则：**没有正文就不写盘**，并且要让用户看到原因。
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


class TestCliMaxAttemptsValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    def _setup(self):
        from gui import config
        proj = Path(config.NOVEL_DIR) / "校验项目"
        arc = proj / "chapters" / "arc-1"
        arc.mkdir(parents=True, exist_ok=True)
        target = arc / "chapter-001.txt"
        target.write_text("原有正文。" * 500, encoding="utf-8")
        prompt = Path(self._tmp.name) / "p.md"
        prompt.write_text("# prompt", encoding="utf-8")
        return proj, target, prompt

    def test_negative_max_attempts_rejected(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import write
        proj, target, prompt = self._setup()
        before = target.stat().st_size
        with self.assertRaises(SystemExit) as ctx:
            write.main(["--prompt", str(prompt), "--chapter", "1", "--task", "t",
                        "--novel-dir", str(proj.parent), "--novel-name", "校验项目",
                        "--max-attempts", "-5"])
        self.assertIn("1-10", str(ctx.exception), "拒绝理由应说明合法范围")
        self.assertEqual(target.stat().st_size, before,
                         "参数非法时章节文件被覆盖了")

    def test_zero_max_attempts_rejected(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import write
        proj, target, prompt = self._setup()
        before = target.stat().st_size
        with self.assertRaises(SystemExit):
            write.main(["--prompt", str(prompt), "--chapter", "1", "--task", "t",
                        "--novel-dir", str(proj.parent), "--novel-name", "校验项目",
                        "--max-attempts", "0"])
        self.assertEqual(target.stat().st_size, before)

    def test_too_large_max_attempts_rejected(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import write
        proj, target, prompt = self._setup()
        before = target.stat().st_size
        with self.assertRaises(SystemExit):
            write.main(["--prompt", str(prompt), "--chapter", "1", "--task", "t",
                        "--novel-dir", str(proj.parent), "--novel-name", "校验项目",
                        "--max-attempts", "99"])
        self.assertEqual(target.stat().st_size, before)


class TestCliEmptyContentNotSaved(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    def test_empty_llm_output_does_not_overwrite(self):
        """模型返回空串时不得覆盖已有章节。"""
        sys.path.insert(0, str(ROOT / "scripts"))
        import write

        from gui import config
        proj = Path(config.NOVEL_DIR) / "空稿项目"
        arc = proj / "chapters" / "arc-1"
        arc.mkdir(parents=True, exist_ok=True)
        target = arc / "chapter-001.txt"
        target.write_text("不能丢的正文。" * 200, encoding="utf-8")
        before = target.stat().st_size
        prompt = Path(self._tmp.name) / "p.md"
        prompt.write_text("# prompt", encoding="utf-8")

        orig = write.llm_client.chat
        write.llm_client.chat = lambda **kw: {
            "text": "", "elapsed": 0.1,
            "prompt_tokens": 0, "completion_tokens": 0}
        try:
            rc = write.main(["--prompt", str(prompt), "--chapter", "1", "--task", "t",
                             "--novel-dir", str(proj.parent), "--novel-name", "空稿项目"])
        finally:
            write.llm_client.chat = orig
        self.assertNotEqual(rc, 0, "空正文时应返回非零")
        self.assertEqual(target.stat().st_size, before,
                         "空正文覆盖了已有章节（P0 数据丢失）")


if __name__ == "__main__":
    unittest.main()
