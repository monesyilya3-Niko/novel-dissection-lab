"""正文编码兼容性（2026-11-03 扩展）。

背景：此前只支持 UTF-8 / GBK 两种。实测国内稿件里还常见：
- GB18030：GBK 的超集（多覆盖生僻字与 4 字节区），老稿子会用到
- UTF-16：Windows 记事本「另存为 → Unicode」的默认产物，带 BOM

不支持时用户会看到「编码无法识别」，措辞像路径问题，实际是编码。
更糟的是同一个稿子在「导入」与「质检」两条路径上表现不同——
所以两个解码点（gui/text_access 与 scripts/chapter_loader）必须同口径。

本测试同时校验两者，并守住「纯 GBK 文件结果不变」这一回归底线。
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

SAMPLE = "第一章 开端\n\n他说：“你好。”\n\n生僻字：𠮷 鿍 龘\n"


class TestTextEncodingCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    def _write(self, name: str, content: str, enc: str, prefix: bytes = b"") -> Path:
        fp = Path(self._tmp.name) / name
        fp.write_bytes(prefix + content.encode(enc))
        return fp

    def _read_both(self, fp: Path):
        from gui import text_access
        from scripts import chapter_loader
        return (text_access.read_text(fp, field="import"),
                chapter_loader.read_text_file(fp))

    def test_utf8_and_gbk_unchanged(self):
        """回归底线：原有两种编码行为不得改变。"""
        for enc in ("utf-8", "gbk"):
            fp = self._write(f"a_{enc}.txt", "你好世界", enc)
            gui_text, loader_text = self._read_both(fp)
            self.assertEqual(gui_text, "你好世界")
            self.assertEqual(loader_text, "你好世界")

    def test_utf8_bom_stripped(self):
        fp = self._write("bom.txt", "第一章", "utf-8-sig")
        gui_text, loader_text = self._read_both(fp)
        self.assertFalse(gui_text.startswith("﻿"))
        self.assertFalse(loader_text.startswith("﻿"))
        self.assertEqual(gui_text, "第一章")

    def test_gb18030_supported(self):
        fp = self._write("gb18030.txt", SAMPLE, "gb18030")
        gui_text, loader_text = self._read_both(fp)
        self.assertIn("𠮷", gui_text)
        self.assertIn("𠮷", loader_text)

    def test_utf16_with_bom_supported(self):
        fp = self._write("u16.txt", SAMPLE, "utf-16")
        gui_text, loader_text = self._read_both(fp)
        self.assertIn("你好", gui_text)
        self.assertIn("你好", loader_text)

    def test_utf16be_with_bom_supported(self):
        fp = self._write("u16be.txt", SAMPLE, "utf-16-be", prefix=b"\xfe\xff")
        gui_text, loader_text = self._read_both(fp)
        self.assertIn("你好", gui_text)
        self.assertIn("你好", loader_text)

    def test_both_decoders_agree(self):
        """同一文件在两个解码点必须得到同一结果。

        注意样本要能编进目标编码：GBK 编不了「𠮷」（4 字节区），
        所以 GBK 那组用不含生僻字的样本。
        """
        cases = (
            ("utf-8", b"", SAMPLE),
            ("gbk", b"", "第一章\n\n他说：“你好。”"),
            ("utf-8-sig", b"", SAMPLE),
            ("gb18030", b"", SAMPLE),
            ("utf-16", b"", SAMPLE),
            ("utf-16-be", b"\xfe\xff", SAMPLE),
        )
        for enc, prefix, sample in cases:
            fp = self._write(f"agree_{enc}.txt", sample, enc, prefix)
            gui_text, loader_text = self._read_both(fp)
            with self.subTest(enc=enc):
                self.assertEqual(gui_text, loader_text,
                                 f"{enc} 在两个解码点结果不同")

    def test_undecodable_raises_clear_error(self):
        """真解不开的字节要报明确错误，且提示已支持的编码列表。"""
        fp = Path(self._tmp.name) / "bad.txt"
        fp.write_bytes(b"\xff\xff\xff\xff\xff")
        from gui import text_access
        from gui.services import ServiceError
        with self.assertRaises(ServiceError) as ctx:
            text_access.read_text(fp, field="import")
        self.assertIn("编码", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
