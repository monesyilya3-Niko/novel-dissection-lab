"""爆款书名生成的重复词守卫（2026-11-03）。

背景：书名由 identity + 连接符 + twist + hook 拼成。各题材的 identities
有 1~2 条、twists 有 0~1 条以「开局」开头，而连接符里也有「：开局」——
三种来源撞在一起会出「开局开局继承诛仙剑阵」这类重复词。
实测 300 轮产生了 54 个重复书名。

修复后两条路径都去重：identity 与 twist 同时以「开局」起头、以及连接符
自带「开局」而 twist 也以它起头。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui import name_generator  # noqa: E402


class TestTitleNoDuplicatedPrefix(unittest.TestCase):
    def test_no_doubled_prefix_across_styles(self):
        """多种题材大量生成，不得出现重复的「开局开局」。"""
        offenders = []
        for style in ("xianxia", "dushi", "kehuan", "xuanyi", "duanpian"):
            for _ in range(60):
                for title in name_generator.generate_title_names(style=style, count=5):
                    if "开局开局" in title:
                        offenders.append(title)
        self.assertEqual(offenders, [], f"出现重复词的书名：{offenders[:5]}")

    def test_titles_are_wrapped(self):
        for title in name_generator.generate_title_names(style="xianxia", count=5):
            self.assertTrue(title.startswith("《") and title.endswith("》"))

    def test_no_doubled_punctuation(self):
        for _ in range(40):
            for title in name_generator.generate_title_names(style="xianxia", count=5):
                self.assertNotIn("，，", title)
                self.assertNotIn("：：", title)


class TestAllNameKindsProduceOutput(unittest.TestCase):
    """起名工坊 9 种 kind 都必须能出名字（UI 下拉全给了这些选项）。"""

    KINDS = ("character", "title", "sect", "corp", "team",
             "shelter", "org", "skill", "artifact")

    def test_every_kind_returns_names(self):
        for kind in self.KINDS:
            with self.subTest(kind=kind):
                r = name_generator.generate(kind=kind, count=3)
                self.assertEqual(r["count"], 3)
                self.assertEqual(len(r["names"]), 3)
                self.assertTrue(all(isinstance(n, str) and n.strip() for n in r["names"]))

    def test_count_is_clamped(self):
        """count 越界要被夹住，不能返回空列表。"""
        self.assertEqual(len(name_generator.generate(kind="sect", count=0)["names"]), 1)
        self.assertEqual(len(name_generator.generate(kind="sect", count=999)["names"]), 50)

    def test_unknown_kind_falls_back_to_character(self):
        r = name_generator.generate(kind="不存在的类型", count=2)
        self.assertEqual(len(r["names"]), 2)


if __name__ == "__main__":
    unittest.main()
