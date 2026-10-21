"""分层采样脚本 sampler.py 单元与行为级测试（纯标准库，零第三方依赖）。

覆盖 scripts/sampler.py：
1. split_chapters：
   - 各种章节正则（第N章/回/节/卷、Chapter N、CHAPTER N）；
   - 首章前的无标题开头处理；
   - 空章节过滤与空白符清理。
2. detect_volumes：
   - 多卷小说卷边界识别；
   - 无分卷小说的全局单一区间退化。
3. select：
   - 短篇（≤10章）开篇全取；
   - 长篇（如100章）开篇段、25%/50%/75% 三处各连续5章、卷末2章与全书末章联合采样。
4. last_n_chars：
   - 超过与未超过阈值的尾部截取。
5. split_sentences 与 _sentence_at：
   - 各类中文/英文句边界（。！？!?…;；\\n）；
   - 句子索引合法提取与越界安全回退空串。
6. extract_dialogue：
   - 中文四类引号对（「」、『』、“”、‘’）提取；
   - 包含前句、对话句与后句的上下文包裹。
7. build_slices：
   - pass1_structure、pass2_character、pass3_style 与 pass4_commercial 四层数据切片生成。
8. main CLI 产物写入：
   - 物理生成 manifest.json、slices.json 与 pass1-4 文本切片文件。
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import sampler  # noqa: E402


class TestSamplerChapterSplitting(unittest.TestCase):
    """章节与分卷切分测试。"""

    def test_split_chapters_varied_headers(self):
        text = """
前言说明文字。
第1章 初入江湖
少年背着木剑走出了村庄。
第2回 狭路相逢
古道上尘土飞扬。
Chapter 3 The Journey
The night was cold and silent.
CHAPTER 4 Epilogue
All ends well.
"""
        chaps = sampler.split_chapters(text)
        self.assertEqual(len(chaps), 5)
        self.assertEqual(chaps[0][0], "（无标题开头）")
        self.assertIn("前言说明文字", chaps[0][1])
        self.assertEqual(chaps[1][0], "第1章 初入江湖")
        self.assertEqual(chaps[2][0], "第2回 狭路相逢")
        self.assertEqual(chaps[3][0], "Chapter 3 The Journey")
        self.assertEqual(chaps[4][0], "CHAPTER 4 Epilogue")

    def test_split_chapters_filters_empty(self):
        text = """
第1章 有内容
正文不为空。
第2章 紧接着空章
第3章 终章
只有第一章和第三章有正文。
"""
        chaps = sampler.split_chapters(text)
        self.assertEqual(len(chaps), 2)
        self.assertEqual(chaps[0][0], "第1章 有内容")
        self.assertEqual(chaps[1][0], "第3章 终章")

    def test_detect_volumes_multi_and_single(self):
        # 1. 多卷
        chaps_multi = [
            ("第1卷 起源 第1章", "a"),
            ("第2章 启程", "b"),
            ("第2卷 风云 第3章", "c"),
            ("第4章 归途", "d"),
        ]
        bounds = sampler.detect_volumes(chaps_multi)
        self.assertEqual(bounds, [(0, 1), (2, 3)])

        # 2. 单卷/无卷标记
        chaps_single = [("第1章", "a"), ("第2章", "b"), ("第3章", "c")]
        self.assertEqual(sampler.detect_volumes(chaps_single), [(0, 2)])


class TestSamplerSelectionStrategy(unittest.TestCase):
    """分层采样策略测试。"""

    def test_select_short_book(self):
        # 小于等于 10 章的小说全部选中
        chaps = [(f"第{i}章", f"正文{i}") for i in range(1, 9)]
        sel = sampler.select(chaps)
        self.assertEqual(len(sel), 8)
        for i in range(8):
            self.assertIn(i, sel)
            self.assertIn("开篇段", sel[i])

    def test_select_long_book_coverage(self):
        # 100 章长篇小说
        chaps = [(f"第{i}章", f"正文{i}") for i in range(1, 101)]
        sel = sampler.select(chaps)
        indices = sorted(sel.keys())
        # 开篇前 10 章全取
        for i in range(10):
            self.assertIn(i, sel)
        # 中段 25% (25-2=23 到 25+2=27)
        for i in range(23, 28):
            self.assertIn(i, sel)
        # 中段 50% (50-2=48 到 50+2=52)
        for i in range(48, 53):
            self.assertIn(i, sel)
        # 中段 75% (75-2=73 到 75+2=77)
        for i in range(73, 78):
            self.assertIn(i, sel)
        # 全书末尾两章
        self.assertIn(98, sel)
        self.assertIn(99, sel)
        # 采样比例合理（25-35 章区间）
        self.assertGreaterEqual(len(indices), 25)
        self.assertLessEqual(len(indices), 40)


class TestSamplerDialogueAndTextHelpers(unittest.TestCase):
    """文本截取、句子边界与对话行定位测试。"""

    def test_last_n_chars(self):
        self.assertEqual(sampler.last_n_chars("abcdef", n=3), "def")
        self.assertEqual(sampler.last_n_chars("abc", n=10), "abc")

    def test_split_sentences_and_sentence_at(self):
        body = "第一句。第二句！第三句？第四句"
        sents = sampler.split_sentences(body)
        self.assertEqual(sents, ["第一句", "第二句", "第三句", "第四句"])

        # 测试 _sentence_at
        boundaries = [0, 4, 8, 12, len(body)]
        self.assertEqual(sampler._sentence_at(body, boundaries, 0), "第一句。")
        self.assertEqual(sampler._sentence_at(body, boundaries, 1), "第二句！")
        # 越界回退
        self.assertEqual(sampler._sentence_at(body, boundaries, -1), "")
        self.assertEqual(sampler._sentence_at(body, boundaries, 10), "")

    def test_extract_dialogue_chinese_quotes(self):
        chaps = [
            (
                "第1章 遇仙",
                "清风徐来。老道抚须道：「少年骨骼清奇」天边雷声轰鸣。\n"
                "少女冷笑：『区区妖道何足挂齿』长剑出鞘！\n"
                "师尊叹道：“天命难违”\n"
                "旁人低语：‘小声些’四周安静下来。",
            )
        ]
        dlg = sampler.extract_dialogue(chaps, [0])
        self.assertGreaterEqual(len(dlg), 4)
        quotes = [d["line"] for d in dlg]
        self.assertTrue(any("「少年骨骼清奇」" in q for q in quotes))
        self.assertTrue(any("『区区妖道何足挂齿』" in q for q in quotes))
        self.assertTrue(any("“天命难违”" in q for q in quotes))
        self.assertTrue(any("‘小声些’" in q for q in quotes))
        # 验证前后句存在
        first = dlg[0]
        self.assertEqual(first["chapter"], 1)
        self.assertEqual(first["title"], "第1章 遇仙")
        self.assertTrue(first["before"] != "" or first["after"] != "")


class TestSamplerBuildSlicesAndCli(unittest.TestCase):
    """build_slices 数据封装与 main CLI 导出回归测试。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sampler_test_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_build_slices_structure(self):
        chaps = [(f"第{i}章", f"正文第{i}章。主角说道：「冲锋！」敌人溃散。") for i in range(1, 16)]
        sel = sampler.select(chaps)
        slices = sampler.build_slices(chaps, sel)
        self.assertIn("pass1_structure", slices)
        self.assertIn("pass2_character", slices)
        self.assertIn("pass3_style", slices)
        self.assertIn("pass4_commercial", slices)

        # pass1 包含 tail500
        p1 = slices["pass1_structure"]["chapters"]
        self.assertGreater(len(p1), 0)
        self.assertIn("tail500", p1[0])
        self.assertIn("reason", p1[0])

        # pass2 包含提取的对话
        p2 = slices["pass2_character"]["dialogues"]
        self.assertGreater(len(p2), 0)

        # pass3 风格层中段与高潮
        p3 = slices["pass3_style"]["chapters"]
        self.assertGreater(len(p3), 0)

        # pass4 商业层开篇与末章
        p4 = slices["pass4_commercial"]["chapters"]
        self.assertGreater(len(p4), 0)

    def test_main_cli_execution_generates_all_artifacts(self):
        book_txt = self.tmp / "test_novel.txt"
        book_content = []
        for i in range(1, 15):
            book_content.append(f"第{i}章 章节标题{i}\n这是第{i}章的正文内容。「你好，世界！」\n")
        book_txt.write_text("\n".join(book_content), encoding="utf-8")

        out_dir = self.tmp / "output_sampled"
        with mock.patch.object(sys, "argv", ["sampler.py", str(book_txt), "--out", str(out_dir)]):
            try:
                sampler.main()
            except SystemExit as exc:
                self.assertEqual(exc.code, 0)

        # 验证输出产物
        self.assertTrue((out_dir / "manifest.json").is_file())
        self.assertTrue((out_dir / "slices.json").is_file())
        self.assertTrue((out_dir / "pass1_structure.txt").is_file())
        self.assertTrue((out_dir / "pass2_dialogue.txt").is_file())
        self.assertTrue((out_dir / "pass3_style.txt").is_file())
        self.assertTrue((out_dir / "pass4_commercial.txt").is_file())
        self.assertTrue((out_dir / "chapters").is_dir())

        manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["book"], "test_novel")
        self.assertEqual(manifest["total_chapters"], 14)
        self.assertGreater(manifest["selected_count"], 0)

    def test_main_cli_with_explicit_argv(self):
        book_txt = self.tmp / "test_novel_explicit.txt"
        book_content = [f"第{i}章 章节标题{i}\n正文内容\n" for i in range(1, 15)]
        book_txt.write_text("\n".join(book_content), encoding="utf-8")
        out_dir = self.tmp / "output_sampled_explicit"
        code = sampler.main([str(book_txt), "--out", str(out_dir)])
        self.assertEqual(code, 0)
        self.assertTrue((out_dir / "manifest.json").is_file())


if __name__ == "__main__":
    sys.exit(unittest.main())
