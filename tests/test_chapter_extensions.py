"""章节文件的扩展名口径必须全链路一致（2026-11-04）。

三处对「什么算章节文件」的判断此前不一致：

- ``gui/text_access.TEXT_SUFFIXES`` = {.txt, .md}  → 导入、打分、投稿导出
- ``scripts.chapter_loader`` 只扫 ``*.txt``          → 质检、CLI 检查
- ``engine_adapter.chapter_scan_rules`` 返回 ``"*.txt"`` → 质检外部目录复制

后果：``.md`` 稿子能导入、能打分，一旦进质检就**整本静默消失**——
不是报错，而是"没有章节"，用户完全不知道发生了什么。

本测试守住三者一致：加载器认 .md、外部复制认 .md、无章号的 .md 仍被忽略。
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


class TestChapterExtensions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    def test_scan_rules_predicate_matches_loader(self):
        """gui 出口的判定必须与加载器一致：.txt/.md 且带章号。"""
        from gui import engine_adapter
        is_chapter, _excluded = engine_adapter.chapter_scan_rules()
        self.assertTrue(is_chapter("第1章.txt"))
        self.assertTrue(is_chapter("第1章.md"))
        self.assertTrue(is_chapter("chapter-001.md"))
        # 无章号的笔记不算章节
        self.assertFalse(is_chapter("设定笔记.md"))
        self.assertFalse(is_chapter("readme.md"))
        self.assertFalse(is_chapter("notes.txt"))

    def test_loader_reads_md_chapter(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import chapter_loader
        d = Path(self._tmp.name) / "md书"
        d.mkdir(exist_ok=True)
        (d / "第1章.md").write_text("第一章正文。", encoding="utf-8")
        (d / "第2章.txt").write_text("第二章正文。", encoding="utf-8")
        diag = chapter_loader.discover_chapter_files(d)
        self.assertEqual(sorted(diag["files"]), [1, 2],
                         f".md 章节未被加载：ignored={diag['ignored']}")

    def test_loader_ignores_md_without_number(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import chapter_loader
        d = Path(self._tmp.name) / "笔记书"
        d.mkdir(exist_ok=True)
        (d / "第1章.md").write_text("正文。", encoding="utf-8")
        (d / "notes.md").write_text("设定笔记", encoding="utf-8")
        diag = chapter_loader.discover_chapter_files(d)
        self.assertEqual(sorted(diag["files"]), [1])
        self.assertIn("notes.md", [p.name for p in diag["ignored"]])

    def test_external_copy_includes_md(self):
        from gui import quality_service
        d = Path(self._tmp.name) / "外部书"
        d.mkdir(exist_ok=True)
        (d / "第1章.md").write_text("正文一。", encoding="utf-8")
        (d / "第2章.txt").write_text("正文二。", encoding="utf-8")
        copy = quality_service.resolve_chapter_target(str(d))
        names = {p.name for p in Path(copy).rglob("*") if p.is_file()}
        self.assertIn("第1章.md", names, ".md 章节未进入质检隔离副本")
        self.assertIn("第2章.txt", names)


class TestExtensionSingleSource(unittest.TestCase):
    """正文扩展名的判断必须只有一处定义（text_access.TEXT_SUFFIXES）。

    2026-11-04 实测到的分歧：上传端点硬编码 .txt（.md 被拒，但路径导入能过）、
    corpus 扫描只扫 *.txt（上传的 .md 在资产库里消失）。两处都已改为复用同一定义。
    """

    def test_upload_accepts_md(self):
        from gui.server import _safe_upload_filename
        self.assertEqual(_safe_upload_filename("第1章.md"), "第1章.md")
        self.assertEqual(_safe_upload_filename("书稿.TXT"), "书稿.TXT")

    def test_upload_rejects_other_extensions(self):
        from gui.server import _safe_upload_filename
        from gui.services import ServiceError
        for name in ("a.pdf", "a.docx", "a.epub", "a"):
            with self.subTest(name=name):
                with self.assertRaises(ServiceError):
                    _safe_upload_filename(name)

    def test_corpus_scan_includes_md(self):
        from gui import config
        d = Path(self._tmp_path()) / "corpus扫描"
        d.mkdir(parents=True, exist_ok=True)
        (d / "书稿.txt").write_text("正文", encoding="utf-8")
        (d / "书稿2.md").write_text("正文", encoding="utf-8")
        (d / "笔记.pdf").write_text("x", encoding="utf-8")
        from gui import migrate
        orig = config.CORPUS_DIR
        config.CORPUS_DIR = d
        try:
            found = {p.name for p in migrate.scan_corpus()}
        finally:
            config.CORPUS_DIR = orig
        self.assertIn("书稿.txt", found)
        self.assertIn("书稿2.md", found)
        self.assertNotIn("笔记.pdf", found)

    @staticmethod
    def _tmp_path() -> str:
        return tempfile.mkdtemp()


if __name__ == "__main__":
    unittest.main()
