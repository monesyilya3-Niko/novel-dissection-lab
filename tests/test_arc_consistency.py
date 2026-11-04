"""GUI 与 CLI 必须把同一章写到同一个卷目录（2026-11-04）。

背景：CLI（``scripts/write.py``）按每 30 章一卷划分：
``arc = (chapter_no - 1) // 30 + 1``。
GUI 的正常入库走同一个函数，但**未配置模型时的降级路径**写死了 ``arc-1``。

于是没配模型的用户写第 31 章，指引让他存到 ``arc-1/chapter-031.txt``，
而 CLI 按公式找的是 ``arc-2/chapter-031.txt``——两个入口对不上，
用户表现为"CLI 看不到我在 GUI 写的章节"。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui.writing_service import CHAPTERS_PER_ARC, _arc_for_chapter  # noqa: E402


def _cli_arc(chapter_no: int) -> int:
    """复刻 scripts/write.py 的公式，作为对照基准。"""
    return (chapter_no - 1) // 30 + 1


class TestArcConsistency(unittest.TestCase):
    def test_matches_cli_formula(self):
        for ch in (1, 2, 29, 30, 31, 59, 60, 61, 100, 1000):
            with self.subTest(chapter=ch):
                self.assertEqual(_arc_for_chapter(ch), _cli_arc(ch),
                                 f"第 {ch} 章 GUI 与 CLI 卷号不一致")

    def test_constants_agree(self):
        import re
        src = (ROOT / "scripts" / "write.py").read_text(encoding="utf-8")
        m = re.search(r"arc = \(chapter_no - 1\) // (\d+) \+ 1", src)
        self.assertIsNotNone(m, "scripts/write.py 的卷号公式改变了，需同步本测试")
        self.assertEqual(int(m.group(1)), CHAPTERS_PER_ARC,
                         "GUI 的 CHAPTERS_PER_ARC 与 CLI 公式里的除数不一致")

    def test_boundary_values(self):
        self.assertEqual(_arc_for_chapter(1), 1)
        self.assertEqual(_arc_for_chapter(30), 1)
        self.assertEqual(_arc_for_chapter(31), 2)
        self.assertEqual(_arc_for_chapter(60), 2)
        self.assertEqual(_arc_for_chapter(61), 3)


if __name__ == "__main__":
    unittest.main()
