"""全书导出五种格式的产出有效性（2026-11-03）。

实测发现的问题：
1. Shunn 投稿格式的 author_name / contact_info 写死为占位符，而
   export_project 调用时从不传参——用户导出的投稿稿永远带
   "Author Name / author@example.com"，直接投出去会被退稿。
2. 书名用 .upper()，对中文书名无意义（原样返回，但语义上是错的）。

修复后：作者信息优先从项目元数据 meta.author / meta.contact 读取，
缺省时仍给占位符但返回 author_missing=True 供 UI 提示。
"""
from __future__ import annotations

import base64
import io
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

import _isolation  # noqa: E402


class TestExportFormats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()
        from gui import config
        proj = Path(config.NOVEL_DIR) / "测试书"
        ch = proj / "chapters" / "arc-1"
        ch.mkdir(parents=True, exist_ok=True)
        (ch / "chapter-001.txt").write_text(
            "第一章 开端\n\n第一段正文。\n\n第二段正文。", encoding="utf-8")
        (ch / "chapter-002.txt").write_text(
            "第二章 转折\n\n第三段正文。", encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    def _export(self, fmt: str) -> dict:
        from gui import writing_extra
        return writing_extra.export_project("测试书", fmt)

    # --- 五种格式都能产出 ---
    def test_all_five_formats_produce_output(self):
        for fmt in ("txt", "md", "docx", "epub", "shunn"):
            with self.subTest(fmt=fmt):
                r = self._export(fmt)
                self.assertTrue(r.get("filename"))
                has_text = bool(r.get("content"))
                has_b64 = bool(r.get("content_base64"))
                self.assertTrue(has_text or has_b64, f"{fmt} 没有任何内容")

    # --- docx ---
    def test_docx_is_valid_openxml_zip(self):
        from gui import writing_extra
        r = writing_extra.export_project_docx("测试书")
        raw = base64.b64decode(r["content_base64"])
        z = zipfile.ZipFile(io.BytesIO(raw))
        self.assertIsNone(z.testzip(), "docx 压缩包损坏")
        names = z.namelist()
        for required in ("[Content_Types].xml", "_rels/.rels", "word/document.xml"):
            self.assertIn(required, names)
        ET.fromstring(z.read("word/document.xml"))  # XML 合法性
        doc = z.read("word/document.xml").decode("utf-8")
        self.assertIn("第一段正文", doc)

    # --- epub ---
    def test_epub_is_valid_container(self):
        from gui import writing_extra
        r = writing_extra.export_project_epub("测试书")
        raw = base64.b64decode(r["content_base64"])
        z = zipfile.ZipFile(io.BytesIO(raw))
        self.assertIsNone(z.testzip())
        first = z.infolist()[0]
        self.assertEqual(first.filename, "mimetype", "mimetype 必须是第一条")
        self.assertEqual(first.compress_type, zipfile.ZIP_STORED,
                         "mimetype 必须不压缩（EPUB 规范要求）")
        self.assertEqual(z.read("mimetype").decode(), "application/epub+zip")
        self.assertIn("META-INF/container.xml", z.namelist())

    def test_epub_opf_references_exist(self):
        import re

        from gui import writing_extra
        r = writing_extra.export_project_epub("测试书")
        z = zipfile.ZipFile(io.BytesIO(base64.b64decode(r["content_base64"])))
        opf = z.read("OEBPS/content.opf").decode("utf-8")
        names = set(z.namelist())
        for href in re.findall(r'href="([^"]+)"', opf):
            with self.subTest(href=href):
                self.assertTrue(
                    any(n.endswith(href) for n in names),
                    f"OPF 引用了不存在的文件: {href}")

    # --- Shunn ---
    def test_shunn_flags_missing_author(self):
        """未填作者时必须带 author_missing 标记，不能静默给占位符。"""
        from gui import writing_extra
        orig = writing_extra.get_project_meta
        writing_extra.get_project_meta = lambda p: {"meta": {}}
        try:
            r = writing_extra.export_project_shunn("测试书")
            self.assertTrue(r.get("author_missing"))
            self.assertIn("Author Name", r["content"])
        finally:
            writing_extra.get_project_meta = orig

    def test_shunn_uses_metadata_author(self):
        from gui import writing_extra
        orig = writing_extra.get_project_meta
        writing_extra.get_project_meta = lambda p: {
            "meta": {"author": "张三", "contact": "zs@example.com"}}
        try:
            r = writing_extra.export_project_shunn("测试书")
            self.assertFalse(r.get("author_missing"))
            self.assertIn("张三", r["content"])
            self.assertIn("zs@example.com", r["content"])
            self.assertNotIn("Author Name", r["content"])
        finally:
            writing_extra.get_project_meta = orig

    def test_shunn_chinese_title_not_converted(self):
        from gui import writing_extra
        orig = writing_extra.get_project_meta
        writing_extra.get_project_meta = lambda p: {"meta": {"author": "A"}}
        try:
            r = writing_extra.export_project_shunn("测试书")
            self.assertIn("测试书", r["content"])
        finally:
            writing_extra.get_project_meta = orig



class TestChapterFilenameCompat(unittest.TestCase):
    """章节文件命名兼容（2026-11-03）。

    背景：此前只认 ``chapter-001.txt`` 一种命名，实测 9 种常见写法里
    只有 1 种被识别，其余全部静默忽略——导出会凭空少章，用户不知道原因。
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

    def _proj(self, names: list[str]) -> str:
        from gui import config
        proj = "命名测试"
        base = Path(config.NOVEL_DIR) / proj / "chapters" / "arc-1"
        if base.exists():
            for fp in base.iterdir():
                fp.unlink()
        base.mkdir(parents=True, exist_ok=True)
        for n in names:
            (base / n).write_text("正文内容。", encoding="utf-8")
        return proj

    def test_common_naming_written_by_users(self):
        """用户常见的 8 种命名都应被识别。"""
        # 章号各不相同，避免去重干扰（同章号并存另有专门用例）
        cases = {
            "chapter-001.txt": 1,
            "002.txt": 2,
            "第3章.txt": 3,
            "第004章.txt": 4,
            "chapter_005.txt": 5,
            "Chapter 6.txt": 6,
            "ch7.md": 7,
            "8.txt": 8,
        }
        proj = self._proj(list(cases))
        from gui import writing_extra
        got = {fp.name: no for no, fp in writing_extra._iter_chapter_files(proj)}
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(got.get(name), expected,
                                 f"{name} 未被识别或章号错误")

    def test_non_chapter_files_ignored(self):
        proj = self._proj(["第1章.txt", "前言.txt", "大纲.md", "notes.txt"])
        from gui import writing_extra
        got = [fp.name for _, fp in writing_extra._iter_chapter_files(proj)]
        self.assertEqual(got, ["第1章.txt"])

    def test_duplicate_chapter_keeps_most_explicit(self):
        """同章号多文件时优先保留带 chapter 前缀的那份。"""
        proj = self._proj(["001.txt", "第1章.txt", "chapter-001.txt"])
        from gui import writing_extra
        files = writing_extra._iter_chapter_files(proj)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0][1].name, "chapter-001.txt")

    def test_sorted_by_chapter_number(self):
        proj = self._proj(["第10章.txt", "第2章.txt", "第1章.txt"])
        from gui import writing_extra
        nos = [no for no, _ in writing_extra._iter_chapter_files(proj)]
        self.assertEqual(nos, [1, 2, 10], "章节未按数字序排列")


class TestChapterTitleSplitting(unittest.TestCase):
    """导入时的章节切分兼容（2026-11-03 补「第1章开端」无空格写法）。

    实测这类稿子此前整本被切成「（无标题开头）」，第一章标题丢失。
    """

    def _split(self, text: str):
        sys.path.insert(0, str(ROOT / "scripts"))
        import sampler
        return sampler.split_chapters(text)

    def test_no_space_title_recognised(self):
        chs = self._split("第1章开端\n\n正文一。\n\n第2章转折\n\n正文二。")
        self.assertEqual([t for t, _ in chs], ["第1章开端", "第2章转折"])

    def test_spaced_title_still_works(self):
        chs = self._split("第1章 开端\n\n正文\n\n第2章 转折\n\n正文")
        self.assertEqual(len(chs), 2)

    def test_narrative_mentioning_chapter_not_split(self):
        """正文里提到「第3章」不能被当成标题。"""
        chs = self._split("第1章 开端\n\n他翻开第3章的内容，继续读下去。\n\n第2章 转折\n\n正文")
        self.assertEqual([t for t, _ in chs], ["第1章 开端", "第2章 转折"])

    def test_long_paragraph_not_split(self):
        chs = self._split("第1章 开端\n\n" + "这是一段很长的正文内容" * 12 + "。")
        self.assertEqual(len(chs), 1)

    def test_sentence_with_period_not_split(self):
        """标题行含句末标点时视为叙述，不切章。"""
        chs = self._split("第1章 开端\n\n第2章开始了。主角走进门。\n\n正文")
        self.assertEqual(len(chs), 1)

if __name__ == "__main__":
    unittest.main()
