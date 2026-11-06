"""空章跳过必须对用户可见（2026-11-04）。

背景：``split_chapters`` 会过滤正文为空的章——这对拆书分析是正确的
（空章无从分析），但导入结果只报 ``total_chapters``，用户「导入 50 章
只见 48 章」时没有任何解释，看起来像丢内容。
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

TEXT_WITH_EMPTY = (
    "第1章 有内容\n\n" + "正文。" * 200 + "\n\n"
    "第2章 空章\n\n"
    "第3章 有内容\n\n" + "内容。" * 200 + "\n\n"
    "第4章 也空\n\n"
    "第5章 有内容\n\n" + "文字。" * 200
)


class TestSplitChaptersAll(unittest.TestCase):
    def _sampler(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import sampler
        return sampler

    def test_all_keeps_empty(self):
        s = self._sampler()
        all_ch = s.split_chapters_all(TEXT_WITH_EMPTY)
        kept = s.split_chapters(TEXT_WITH_EMPTY)
        self.assertEqual(len(all_ch), 5, "split_chapters_all 应保留全部 5 章")
        self.assertEqual(len(kept), 3, "split_chapters 应过滤掉 2 个空章")

    def test_filtered_result_unchanged(self):
        """split_chapters 的行为不能因为拆出 _all 而改变。"""
        s = self._sampler()
        kept = s.split_chapters(TEXT_WITH_EMPTY)
        self.assertEqual([t for t, _ in kept],
                         ["第1章 有内容", "第3章 有内容", "第5章 有内容"])

    def test_no_empty_chapters_reports_zero(self):
        from gui import engine_adapter
        text = "第1章\n\n" + "正文。" * 100 + "\n\n第2章\n\n" + "内容。" * 100
        self.assertEqual(engine_adapter.count_skipped_empty_chapters(text), 0)

    def test_untitled_leading_block_not_counted_as_empty_chapter(self):
        """开头的空白前导段不算「跳过的空章」（2026-11-05）。

        稿子开头有空白行时，切章器会产出一个正文为空、标题为
        「（无标题开头）」的前导段。它被 filter 掉后被原实现算成"跳过 1 章"，
        用户看到提示却找不到哪一章少了。
        """
        from gui import engine_adapter
        text = "\n\n第1章 开端\n正文一。\n\n第2章 再会\n正文二。"
        self.assertEqual(engine_adapter.count_skipped_empty_chapters(text), 0)

    def test_real_empty_chapter_still_counted(self):
        """反向守卫：真正有标题的空章仍要如实上报。"""
        from gui import engine_adapter
        text = "第1章 开端\n正文一。\n\n第2章 空章\n\n第3章 再会\n正文三。"
        self.assertEqual(engine_adapter.count_skipped_empty_chapters(text), 1)


class TestImportReportsSkipped(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    def test_import_result_contains_skipped_count(self):
        from gui import services
        src = Path(self._tmp.name) / "含空章.txt"
        src.write_text(TEXT_WITH_EMPTY, encoding="utf-8")
        r = services.import_book(str(src))
        self.assertEqual(r["total_chapters"], 3)
        self.assertEqual(r["skipped_empty_chapters"], 2)

    def test_import_without_empty_chapters(self):
        from gui import services
        src = Path(self._tmp.name) / "无空章.txt"
        src.write_text("第1章\n\n" + "正文。" * 200 + "\n\n第2章\n\n" + "内容。" * 200,
                       encoding="utf-8")
        r = services.import_book(str(src))
        self.assertEqual(r["skipped_empty_chapters"], 0)


if __name__ == "__main__":
    unittest.main()
