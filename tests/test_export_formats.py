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


if __name__ == "__main__":
    unittest.main()
