"""轻量 YAML frontmatter 解析器单元测试（纯标准库，零第三方依赖）。

覆盖 scripts/yaml_lite.py：
1. _strip_comment：行内注释去除与引号内 # 保护；
2. _unquote：单双引号剥离与转义字符（\\n, \\t, \\", \\'）还原；
3. _parse_scalar：布尔、空值、整数、浮点数、科学计数法与普通字符串解析；
4. _split_inline_list：内联列表逗号切分与引号内逗号保护；
5. _parse_value：标量、内联列表与内联映射（含布尔标旗）；
6. _split_key_value：冒号切分与引号内冒号（如 URL / 时间戳）保护；
7. parse_yaml：标量键值映射、块级列表、列表内多行字典项、顶层纯列表、注释与容错；
8. load_frontmatter：--- 与 +++ 分隔符解析、无 frontmatter 降级、未闭合分隔符降级与空输入。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import yaml_lite  # noqa: E402


class TestYamlLiteInternalHelpers(unittest.TestCase):
    """底层辅助函数回归测试。"""

    def test_strip_comment_basic_and_quoted(self):
        self.assertEqual(yaml_lite._strip_comment("title: test # 注释"), "title: test")
        self.assertEqual(yaml_lite._strip_comment("tag: '#not_a_comment'"), "tag: '#not_a_comment'")
        self.assertEqual(yaml_lite._strip_comment('tag: "#not_a_comment" # real comment'), 'tag: "#not_a_comment"')
        self.assertEqual(yaml_lite._strip_comment("# 整行注释"), "")

    def test_unquote_and_unescape(self):
        self.assertEqual(yaml_lite._unquote("'simple string'"), "simple string")
        self.assertEqual(yaml_lite._unquote('"double quoted"'), "double quoted")
        self.assertEqual(yaml_lite._unquote(r'"line1\nline2\ttab"'), "line1\nline2\ttab")
        self.assertEqual(yaml_lite._unquote(r'"quote: \"hello\""'), 'quote: "hello"')
        self.assertEqual(yaml_lite._unquote("raw unquoted"), "raw unquoted")

    def test_parse_scalar_types(self):
        # 空串
        self.assertEqual(yaml_lite._parse_scalar(""), "")
        # 布尔
        self.assertIs(yaml_lite._parse_scalar("true"), True)
        self.assertIs(yaml_lite._parse_scalar("True"), True)
        self.assertIs(yaml_lite._parse_scalar("false"), False)
        self.assertIs(yaml_lite._parse_scalar("FALSE"), False)
        # 空值
        self.assertIsNone(yaml_lite._parse_scalar("null"))
        self.assertIsNone(yaml_lite._parse_scalar("None"))
        self.assertIsNone(yaml_lite._parse_scalar("~"))
        # 整数与带符号整型
        self.assertEqual(yaml_lite._parse_scalar("42"), 42)
        self.assertEqual(yaml_lite._parse_scalar("-100"), -100)
        self.assertEqual(yaml_lite._parse_scalar("+7"), 7)
        # 浮点数与科学计数法
        self.assertEqual(yaml_lite._parse_scalar("3.1415"), 3.1415)
        self.assertEqual(yaml_lite._parse_scalar("-0.05"), -0.05)
        self.assertEqual(yaml_lite._parse_scalar(".5"), 0.5)
        self.assertEqual(yaml_lite._parse_scalar("1e-4"), 0.0001)
        # 文本
        self.assertEqual(yaml_lite._parse_scalar("青春校园"), "青春校园")

    def test_split_inline_list_respects_quotes(self):
        self.assertEqual(yaml_lite._split_inline_list("a, b, c"), ["a", "b", "c"])
        self.assertEqual(yaml_lite._split_inline_list('a, "b, c", d'), ["a", '"b, c"', "d"])
        self.assertEqual(yaml_lite._split_inline_list("item1, 'item2, sub', item3"), ["item1", "'item2, sub'", "item3"])
        self.assertEqual(yaml_lite._split_inline_list(""), [])

    def test_parse_value_inline_list_and_map(self):
        # 内联列表
        self.assertEqual(yaml_lite._parse_value("[a, b, c]"), ["a", "b", "c"])
        self.assertEqual(yaml_lite._parse_value("[1, 2.5, true, null, 'text']"), [1, 2.5, True, None, "text"])
        self.assertEqual(yaml_lite._parse_value("[]"), [])
        # 内联映射
        self.assertEqual(yaml_lite._parse_value("{a: 1, b: 2.5}"), {"a": 1, "b": 2.5})
        self.assertEqual(yaml_lite._parse_value("{flag, count: 10}"), {"flag": True, "count": 10})

    def test_split_key_value_handles_colons_in_quotes(self):
        self.assertEqual(yaml_lite._split_key_value("name: 张三"), ("name", "张三"))
        self.assertEqual(
            yaml_lite._split_key_value('url: "http://example.com/api"'),
            ("url", '"http://example.com/api"'),
        )
        self.assertEqual(
            yaml_lite._split_key_value("quote: 'a: b: c'"),
            ("quote", "'a: b: c'"),
        )
        self.assertEqual(yaml_lite._split_key_value("no_colon_here"), (None, None))


class TestParseYaml(unittest.TestCase):
    """parse_yaml 核心解析功能回归测试。"""

    def test_parse_yaml_scalar_mapping(self):
        text = """
        genre: 青春甜宠
        score: 95
        confidence: 0.98
        published: true
        summary: "这是被双引号包裹的摘要"
        """
        res = yaml_lite.parse_yaml(text)
        self.assertEqual(res["genre"], "青春甜宠")
        self.assertEqual(res["score"], 95)
        self.assertEqual(res["confidence"], 0.98)
        self.assertIs(res["published"], True)
        self.assertEqual(res["summary"], "这是被双引号包裹的摘要")

    def test_parse_yaml_block_list(self):
        text = """
        aliases:
          - 青春甜宠
          - 校园甜宠
          - 治愈恋爱
        """
        res = yaml_lite.parse_yaml(text)
        self.assertEqual(res["aliases"], ["青春甜宠", "校园甜宠", "治愈恋爱"])

    def test_parse_yaml_nested_maps_in_list(self):
        text = """
        characters:
          - name: 林舒
            role: 女主
          - name: 江迟
            role: 男主
        """
        res = yaml_lite.parse_yaml(text)
        self.assertEqual(len(res["characters"]), 2)
        self.assertEqual(res["characters"][0], {"name": "林舒", "role": "女主"})
        self.assertEqual(res["characters"][1], {"name": "江迟", "role": "男主"})

    def test_parse_yaml_multiline_map_items_in_list(self):
        text = """
        hooks:
          - hook_id: H01
            beat: 危机起手
            intensity: 85
          - hook_id: H02
            beat: 悬念断章
            intensity: 90
        """
        res = yaml_lite.parse_yaml(text)
        self.assertEqual(len(res["hooks"]), 2)
        self.assertEqual(res["hooks"][0]["hook_id"], "H01")
        self.assertEqual(res["hooks"][0]["intensity"], 85)
        self.assertEqual(res["hooks"][1]["hook_id"], "H02")

    def test_parse_yaml_top_level_list(self):
        text = """
        - 凡人流
        - 稳健流
        - 系统流
        """
        res = yaml_lite.parse_yaml(text)
        self.assertEqual(res, ["凡人流", "稳健流", "系统流"])

    def test_parse_yaml_comments_and_empty_lines(self):
        text = """
        # 头部注释
        genre: 都市脑洞 # 题材分类

        # 中部空行与注释
        word_count: 500000
        """
        res = yaml_lite.parse_yaml(text)
        self.assertEqual(res["genre"], "都市脑洞")
        self.assertEqual(res["word_count"], 500000)


class TestLoadFrontmatter(unittest.TestCase):
    """load_frontmatter 提取与解析测试。"""

    def test_load_frontmatter_standard_triple_dash(self):
        md = """---
title: 暮冬念春
author: 念春
genre: 青春甜宠
tags: [校园, 治愈]
---
# 第一章
这里是正文开始的内容。
第二行文本。"""
        meta, body = yaml_lite.load_frontmatter(md)
        self.assertEqual(meta["title"], "暮冬念春")
        self.assertEqual(meta["author"], "念春")
        self.assertEqual(meta["genre"], "青春甜宠")
        self.assertEqual(meta["tags"], ["校园", "治愈"])
        self.assertEqual(body.strip(), "# 第一章\n这里是正文开始的内容。\n第二行文本。")

    def test_load_frontmatter_plus_delimiter(self):
        md = """+++
title: TOML风格分隔符
format: markdown
+++
正文内容在此。"""
        meta, body = yaml_lite.load_frontmatter(md)
        self.assertEqual(meta["title"], "TOML风格分隔符")
        self.assertEqual(meta["format"], "markdown")
        self.assertEqual(body.strip(), "正文内容在此。")

    def test_load_frontmatter_no_frontmatter(self):
        md = "# 纯正文\n没有任何 frontmatter 头部。"
        meta, body = yaml_lite.load_frontmatter(md)
        self.assertEqual(meta, {})
        self.assertEqual(body, md)

    def test_load_frontmatter_unclosed_delimiter(self):
        md = """---
title: 未闭合的分隔符
没有闭合的三个破折号直接结束文本。"""
        meta, body = yaml_lite.load_frontmatter(md)
        self.assertEqual(meta, {})
        self.assertEqual(body, md)

    def test_load_frontmatter_empty_text(self):
        meta, body = yaml_lite.load_frontmatter("")
        self.assertEqual(meta, {})
        self.assertEqual(body, "")


if __name__ == "__main__":
    sys.exit(unittest.main())
