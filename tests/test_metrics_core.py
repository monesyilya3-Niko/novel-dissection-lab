#!/usr/bin/env python3
"""
Unit tests for scripts/metrics.py (Quantitative Metrics Engine)
100% pure Python standard library unittest, zero external dependencies.
"""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from scripts import metrics


class TestSentencesAndParagraphs(unittest.TestCase):
    """测试句子与段落切分辅助函数。"""

    def test_sentences_non_string(self):
        self.assertEqual(metrics.sentences(None), [])
        self.assertEqual(metrics.sentences(123), [])
        self.assertEqual(metrics.sentences([]), [])

    def test_sentences_split_and_strip(self):
        text = "第一句。第二句！第三句？第四句…第五句;第六句；第七句\n第八句"
        res = metrics.sentences(text)
        expected = [
            "第一句", "第二句", "第三句", "第四句", "第五句", "第六句", "第七句", "第八句"
        ]
        self.assertEqual(res, expected)

    def test_sentences_empty_or_whitespace(self):
        self.assertEqual(metrics.sentences(""), [])
        self.assertEqual(metrics.sentences("   \n\n  。！？  "), [])

    def test_paragraphs_non_string(self):
        self.assertEqual(metrics.paragraphs(None), [])
        self.assertEqual(metrics.paragraphs(123), [])

    def test_paragraphs_split(self):
        text = "第一段第一行\n第一段第二行\n\n第二段内容\n  \n第三段内容"
        res = metrics.paragraphs(text)
        self.assertEqual(len(res), 3)
        self.assertIn("第一段第一行\n第一段第二行", res[0])
        self.assertEqual(res[1], "第二段内容")
        self.assertEqual(res[2], "第三段内容")

    def test_paragraph_count_helper(self):
        self.assertEqual(metrics._paragraph_count(None), 0)
        self.assertEqual(metrics._paragraph_count(""), 0)
        text = "段落一\n\n段落二\n\n段落三"
        self.assertEqual(metrics._paragraph_count(text), 3)


class TestCjkRunsAndTtr(unittest.TestCase):
    """测试 CJK 连续串提取与字符级 TTR 计算。"""

    def test_cjk_runs_non_string(self):
        self.assertEqual(metrics.cjk_runs(None), [])
        self.assertEqual(metrics.cjk_runs(456), [])

    def test_cjk_runs_extraction(self):
        text = "Hello 世界！123 这是 Python 和 中文 的 混合 测试。"
        runs = metrics.cjk_runs(text)
        self.assertEqual(runs, ["世界", "这是", "和", "中文", "的", "混合", "测试"])

    def test_char_ttr_edge_cases(self):
        self.assertEqual(metrics.char_ttr(None), 0.0)
        self.assertEqual(metrics.char_ttr(""), 0.0)
        self.assertEqual(metrics.char_ttr("English Only! 12345"), 0.0)

    def test_char_ttr_values(self):
        # 4 个独一无二汉字 / 4 个总汉字 = 1.0
        self.assertEqual(metrics.char_ttr("春华秋实"), 1.0)
        # 1 个汉字重复 4 次 = 0.25
        self.assertEqual(metrics.char_ttr("人人人人"), 0.25)


class TestBigramFreq(unittest.TestCase):
    """测试 2-gram 词频统计。"""

    def test_bigram_freq_non_string(self):
        self.assertEqual(metrics.bigram_freq(None), [])
        self.assertEqual(metrics.bigram_freq(123), [])

    def test_bigram_freq_single_char_or_no_cjk(self):
        self.assertEqual(metrics.bigram_freq("好"), [])
        self.assertEqual(metrics.bigram_freq("abc def"), [])

    def test_bigram_freq_accurate_counts(self):
        # "风云" 出现 3 次，"云涌" 出现 2 次
        text = "风云变色，风云再起，风云涌动，四海云涌。"
        top_grams = metrics.bigram_freq(text, top=2)
        self.assertEqual(len(top_grams), 2)
        d = {item["gram"]: item["count"] for item in top_grams}
        self.assertEqual(d["风云"], 3)
        self.assertEqual(d["云涌"], 2)


class TestDialogueExtraction(unittest.TestCase):
    """测试四类引号对白字符统计与对白占比。"""

    def test_dialogue_char_count_non_string(self):
        self.assertEqual(metrics.dialogue_char_count(None), 0)
        self.assertEqual(metrics.dialogue_char_count(999), 0)

    def test_dialogue_char_count_various_quotes(self):
        # ASCII quotes: "hello" -> 5 chars
        self.assertEqual(metrics.dialogue_char_count('他说："你好啊"'), 3)
        # Chinese curved quotes: “你好” -> 2 chars
        self.assertEqual(metrics.dialogue_char_count('他说：“你好”'), 2)
        # Corner quotes: 「很好」 -> 2 chars
        self.assertEqual(metrics.dialogue_char_count('他说：「很好」'), 2)
        # Double corner quotes: 『确实』 -> 2 chars
        self.assertEqual(metrics.dialogue_char_count('他说：『确实』'), 2)
        # Single curved quotes: ‘明白了’ -> 3 chars
        self.assertEqual(metrics.dialogue_char_count('他说：‘明白了’'), 3)

    def test_unclosed_quotes_at_eof(self):
        # 未闭合引号计到文末（容错）
        self.assertEqual(metrics.dialogue_char_count('他说：「还未结束'), 4)
        self.assertEqual(metrics.dialogue_char_count('她说："未闭合'), 3)

    def test_nested_quotes_handling(self):
        # 嵌套开引号忽略，内部闭引号按正文计入
        text = '他说：「他大喊“救命”然后跑了」'
        self.assertEqual(metrics.dialogue_char_count(text), 10)

    def test_dialogue_ratio_calculation(self):
        self.assertEqual(metrics.dialogue_ratio(None), 0.0)
        self.assertEqual(metrics.dialogue_ratio(""), 0.0)
        # 纯叙述文本无引号
        self.assertEqual(metrics.dialogue_ratio("大漠孤烟直，长河落日圆。"), 0.0)
        # 文本: '我说：“好”' -> 去空白共 6 字符，引号内 1 字符 -> 1/6 ≈ 0.1667
        self.assertEqual(metrics.dialogue_ratio('我说：“好”'), 0.1667)


class TestSensoryCounts(unittest.TestCase):
    """测试五感词频统计。"""

    def test_sensory_counts_non_string(self):
        res = metrics.sensory_counts(None)
        self.assertEqual(res, {"视觉": 0, "听觉": 0, "嗅觉": 0, "味觉": 0, "触觉": 0})

    def test_sensory_counts_detection(self):
        text = "他凝视着白光（视觉），听到雷声呼啸（听觉），闻到了芳香（嗅觉），尝到了甘甜（味觉），手心感到冰冷刺疼（触觉）。"
        res = metrics.sensory_counts(text)
        self.assertGreater(res["视觉"], 0)
        self.assertGreater(res["听觉"], 0)
        self.assertGreater(res["嗅觉"], 0)
        self.assertGreater(res["味觉"], 0)
        self.assertGreater(res["触觉"], 0)


class TestSentenceRhythmAndStats(unittest.TestCase):
    """测试句长分布、节奏特征与统计器。"""

    def test_sentence_length_profile_empty_or_invalid(self):
        self.assertEqual(metrics.sentence_length_profile(None), {"short_ratio": 0.0, "long_ratio": 0.0})
        self.assertEqual(metrics.sentence_length_profile([]), {"short_ratio": 0.0, "long_ratio": 0.0})
        self.assertEqual(metrics.sentence_length_profile("not a list"), {"short_ratio": 0.0, "long_ratio": 0.0})

    def test_sentence_length_profile_proportions(self):
        # 10 (short <=15), 20 (mid), 45 (long >=40)
        lens = [10, 20, 45]
        prof = metrics.sentence_length_profile(lens)
        self.assertEqual(prof["short_ratio"], 0.3333)
        self.assertEqual(prof["long_ratio"], 0.3333)

    def test_sentence_len_stats_non_string(self):
        res = metrics._sentence_len_stats(None)
        self.assertEqual(res, (0, 0, 0, 0, 0, 0))

    def test_sentence_len_stats_calculation(self):
        text = "短句。这是一句比较长的正常叙述文字！"
        n, total, max_len, min_len, short_n, long_n = metrics._sentence_len_stats(text)
        self.assertEqual(n, 2)
        self.assertEqual(min_len, 2)  # "短句" 2 字
        self.assertEqual(max_len, 14)  # "这是一句比较长的正常叙述文字" 14 字
        self.assertEqual(short_n, 2)  # 2 <= 15, 14 <= 15
        self.assertEqual(long_n, 0)


class TestComputeIntegration(unittest.TestCase):
    """测试 compute 综合量化指标计算。"""

    def test_compute_non_string(self):
        r = metrics.compute(None)
        self.assertEqual(r["total_chars"], 0)
        self.assertEqual(r["sentence_count"], 0)
        self.assertEqual(r["avg_sentence_len"], 0)

    def test_compute_comprehensive_fields(self):
        text = (
            "第一章 初见\n\n"
            "少年拔剑四顾心茫然！他大喊道：“绝不认输！”\n\n"
            "寒风呼啸，雪花纷飞。冷，太冷了。"
        )
        r = metrics.compute(text)
        expected_keys = {
            "total_chars", "sentence_count", "avg_sentence_len", "max_sentence_len",
            "min_sentence_len", "short_ratio", "long_ratio", "paragraph_count",
            "dialogue_ratio", "char_ttr", "top_bigrams", "sensory", "exclaim_ratio"
        }
        self.assertEqual(set(r.keys()), expected_keys)
        self.assertGreater(r["total_chars"], 0)
        self.assertGreater(r["sentence_count"], 0)
        self.assertEqual(r["paragraph_count"], 3)
        self.assertGreater(r["dialogue_ratio"], 0.0)
        self.assertGreater(r["exclaim_ratio"], 0.0)


class TestMetricsCLI(unittest.TestCase):
    """测试 main 命令行入口。"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmppath = Path(self.tmpdir.name)
        self.book1 = self.tmppath / "chapter01.txt"
        self.book1.write_text("第一章。主角走在雪地里，听着呼啸的风声。“冷！”他低声说。", encoding="utf-8")
        self.book2 = self.tmppath / "chapter02.txt"
        self.book2.write_text("第二章。远处的阳光照耀在金色的山峦上，美不胜收！", encoding="utf-8")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_cli_non_existent_path(self):
        bad_path = self.tmppath / "non_existent.txt"
        code = metrics.main([str(bad_path), "-q"])
        self.assertEqual(code, 1)

    def test_cli_single_file_default_out(self):
        f = io.StringIO()
        with mock.patch("sys.stdout", f):
            code = metrics.main([str(self.book1)])
        self.assertEqual(code, 0)
        out_json = self.tmppath / "chapter01_metrics.json"
        self.assertTrue(out_json.is_file())
        data = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertIn("chapter01", data)
        self.assertIn("total_chars", data["chapter01"])
        self.assertIn("指标已写入", f.getvalue())

    def test_cli_directory_and_custom_out_and_quiet(self):
        custom_out = self.tmppath / "custom_summary.json"
        f = io.StringIO()
        with mock.patch("sys.stdout", f):
            code = metrics.main([str(self.tmppath), "--out", str(custom_out), "-q"])
        self.assertEqual(code, 0)
        # quiet 模式下不向 stdout 打印
        self.assertEqual(f.getvalue(), "")
        self.assertTrue(custom_out.is_file())
        data = json.loads(custom_out.read_text(encoding="utf-8"))
        self.assertIn("chapter01", data)
        self.assertIn("chapter02", data)


if __name__ == "__main__":
    unittest.main()
