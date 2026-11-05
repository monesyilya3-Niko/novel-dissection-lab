#!/usr/bin/env python3
"""normalize.py / clean_verbatim.py 纯函数覆盖测试（出版级补强）。

目标：把 normalize（48%）、clean_verbatim（29%）的关键纯函数拉到高覆盖，
这些是拆书资产规范化的核心逻辑，不依赖 LLM，可完全离线测试。
"""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import normalize as norm
from clean_verbatim import clean_string


class TestFirst(unittest.TestCase):
    def test_first_hit(self):
        self.assertEqual(norm.first({"a": 1, "b": 2}, "b", "a"), 2)

    def test_first_skip_empty(self):
        self.assertEqual(norm.first({"a": "", "b": None, "c": "x"}, "a", "b", "c"), "x")

    def test_first_skip_empty_containers(self):
        self.assertEqual(norm.first({"a": [], "b": {}, "c": [1]}, "a", "b", "c"), [1])

    def test_first_nested_dict(self):
        self.assertEqual(norm.first({"a": {"x": "", "y": "deep"}}, "a"), "deep")

    def test_first_nested_all_empty(self):
        # 嵌套 dict 叶子全空时返回 dict 本身（first 只过滤顶层空值）
        self.assertEqual(norm.first({"a": {"x": ""}}, "a"), {"x": ""})

    def test_first_missing(self):
        self.assertIsNone(norm.first({}, "a", "b"))


class TestAsList(unittest.TestCase):
    def test_list_passthrough(self):
        self.assertEqual(norm.as_list(["a", "b"]), ["a", "b"])

    def test_str_split_cn(self):
        self.assertEqual(norm.as_list("红，蓝；绿/黄"), ["红", "蓝", "绿", "黄"])

    def test_str_split_en(self):
        self.assertEqual(norm.as_list("a, b;c"), ["a", "b", "c"])

    def test_str_strip_empty(self):
        self.assertEqual(norm.as_list("a,,b"), ["a", "b"])

    def test_non_str(self):
        self.assertEqual(norm.as_list(123), [])
        self.assertEqual(norm.as_list(None), [])


class TestAsStr(unittest.TestCase):
    def test_str(self):
        self.assertEqual(norm.as_str("  hi  "), "hi")

    def test_list_first(self):
        self.assertEqual(norm.as_str(["a", "b"]), "a")

    def test_list_nested(self):
        self.assertEqual(norm.as_str([["x"]]), "x")

    def test_dict_leaf(self):
        self.assertEqual(norm.as_str({"k": {"j": "v"}}), "v")

    def test_dict_skip_empty(self):
        self.assertEqual(norm.as_str({"k": "", "j": "v"}), "v")

    def test_empty(self):
        self.assertEqual(norm.as_str([]), "")
        self.assertEqual(norm.as_str({}), "")
        self.assertEqual(norm.as_str(None), "")


class TestExtractQuoted(unittest.TestCase):
    def test_cn_quotes(self):
        r = norm.extract_quoted("他常说「走着瞧」和「没问题」")
        self.assertIn("走着瞧", r)
        self.assertIn("没问题", r)

    def test_max_items(self):
        r = norm.extract_quoted("「一一」「二二」「三三」「四四」「五五」「六六」", max_items=3)
        self.assertEqual(len(r), 3)

    def test_too_short_ignored(self):
        # 单字引号内容（<2字）被忽略
        r = norm.extract_quoted("他说「好」")
        self.assertNotIn("好", r)

    def test_no_quotes(self):
        self.assertEqual(norm.extract_quoted("没有引号的文本"), [])


class TestExtractTics(unittest.TestCase):
    def test_inline_pattern(self):
        r = norm.extract_tics_from_text("常用的口头禅比如：呵呵")
        self.assertTrue(any("呵呵" in t for t in r))

    def test_empty(self):
        self.assertEqual(norm.extract_tics_from_text(""), [])


class TestCleanDomainLabel(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(norm.clean_domain_label("校园"), "校园")

    def test_truncate(self):
        r = norm.clean_domain_label("这是一个很长的领域标签超过十二字", max_len=12)
        self.assertLessEqual(len(r), 12)

    def test_strip(self):
        self.assertEqual(norm.clean_domain_label("  校园  "), "校园")


class TestSplitAnti(unittest.TestCase):
    def test_split(self):
        a, b = norm.split_anti("禁止：暴力")
        self.assertIsInstance(a, str)
        self.assertIsInstance(b, str)


class TestCleanString(unittest.TestCase):
    def test_no_ngram(self):
        s, n = clean_string("hello world", set(), "p")
        self.assertEqual(s, "hello world")

    def test_removes_long_quoted_verbatim(self):
        # 引号内 >12 字且命中原文 ngram 的片段被删除
        long_frag = "这是一段超过十二个字的原文片段内容"
        ngram = {long_frag[:12]}
        s, changed = clean_string(f"他说「{long_frag}」没错", ngram, "p")
        self.assertNotIn(long_frag, s)
        self.assertTrue(changed)

    def test_keeps_short_quotes(self):
        s, changed = clean_string("他说「走着瞧」", set(), "p")
        self.assertIn("走着瞧", s)
        self.assertFalse(changed)

    def test_returns_tuple(self):
        r = clean_string("x", set(), "p")
        self.assertIsInstance(r, tuple)
        self.assertEqual(len(r), 2)


class TestNormalizePass3SchemaFidelity(unittest.TestCase):
    """normalize_pass3 必须忠实读取 prompt/schema 规定的字段（2026-11-05）。

    实测缺陷：按 ``prompts/pass3_style.md`` 的规范输出，6 个字段里 4 个被丢弃，
    而且其中一个被**编造**成固定值。磁盘上 7 张 voice-card 中有 5 张的
    ``chapter_opening_patterns`` 完全相同（场景白描×3 + 内心独白×2），
    就是编造的产物——用户会以为那是每本书的真实规律。

    这几条把「规范输入 → 原样透传」「没有输入 → 留空而非编造」两个方向都钉死。
    """

    def test_body_reaction_vocabulary_from_schema_path(self):
        _, _, emotion, _, _ = norm.normalize_pass3({
            "emotion_handling": {
                "mode": "体感式",
                "body_reaction_vocabulary": ["手指捏白", "心跳如鼓"],
            }
        })
        self.assertEqual(emotion.get("body_reaction_vocabulary"),
                         ["手指捏白", "心跳如鼓"])

    def test_subtext_level_is_read_not_hardcoded(self):
        """原实现硬编码 "直白"，schema enum 的后两档永远不可能出现。"""
        _, dialogue, _, _, _ = norm.normalize_pass3({
            "dialogue": {"subtext_level": "大量潜台词", "tag_style": "靠动作代替标签"}
        })
        self.assertEqual(dialogue.get("subtext_level"), "大量潜台词")
        self.assertEqual(dialogue.get("tag_style"), "靠动作代替标签")

    def test_paragraph_is_read_not_empty(self):
        """原实现硬编码 {}，三项永远进不了 voice-card。"""
        narration, _, _, _, _ = norm.normalize_pass3({
            "narration": {"paragraph": {
                "avg_lines": 3,
                "single_line_para_ratio": 0.15,
                "usage_of_single_line": "转折前静默",
            }}
        })
        self.assertEqual(narration.get("paragraph"), {
            "avg_lines": 3,
            "single_line_para_ratio": 0.15,
            "usage_of_single_line": "转折前静默",
        })

    def test_opening_patterns_passed_through_verbatim(self):
        """规范结构必须原样透传（原实现只认 str，list 被丢弃后伪造默认值）。"""
        given = [
            {"pattern": "直入对话", "frequency": 4, "example_structure": "[对白]+[动作]"},
            {"pattern": "感官痛感", "frequency": 2, "example_structure": "[痛感]"},
        ]
        narration, _, _, _, _ = norm.normalize_pass3({
            "narration": {"chapter_opening_patterns": given}
        })
        self.assertEqual(narration.get("chapter_opening_patterns"), given)

    def test_opening_patterns_never_fabricated(self):
        """拿不到信息时必须留空——编造具体数字比缺字段更有害。"""
        narration, _, _, _, _ = norm.normalize_pass3({})
        self.assertEqual(narration.get("chapter_opening_patterns"), [],
                         "不得再编造「场景白描×3 + 内心独白×2」这类伪规律")


class TestNormalizeMainCLI(unittest.TestCase):
    def test_main_cli_execution_with_explicit_argv(self):
        with tempfile.TemporaryDirectory() as td:
            p2_file = Path(td) / "pass2.json"
            p3_file = Path(td) / "pass3.json"
            p2_file.write_text(json.dumps([{"角色": "李云", "台词特征": "冷静"}]), encoding="utf-8")
            p3_file.write_text(json.dumps({"叙述视角": "第三人称", "对话密度": "适中"}), encoding="utf-8")
            with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                code = norm.main([str(p2_file), str(p3_file)])
            self.assertEqual(code, 0)
            self.assertIn("character_voices", mock_out.getvalue())


if __name__ == "__main__":
    unittest.main()
