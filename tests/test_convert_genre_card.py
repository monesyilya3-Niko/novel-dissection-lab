#!/usr/bin/env python3
"""体裁散文卡转换引擎（convert_genre_card.py）全维独立测试套件。

涵盖：
1. 辅助函数（_now_iso, _confidence_map, _extract_required_elements, _extract_banned_phrases,
   _extract_hook_types, _extract_payoff_types）；
2. Markdown 小节切分（parse_sections 标准13小节解析、一级标题忽略、额外小节容错、空正文兜底）；
3. 规则包数据结构组装（build_genre_pack 元数据规范、结构字段、商业爽点、语言规则与字段兜底）；
4. 转换流程与幂等保护（_load_existing 容错、输入文件缺失处理、正常转换写出、--force 同版本幂等跳过与异版本覆盖）；
5. 命令行接口（CLI main 弃用安全退出码 1 与 stderr 引导说明、缺失参数 argparse 拦截）。
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import convert_genre_card as cgc  # noqa: E402


class TestConvertGenreHelpers(unittest.TestCase):
    """测试底层辅助与映射函数。"""

    def test_now_iso_format(self):
        ts = cgc._now_iso()
        dt = datetime.fromisoformat(ts)
        self.assertIsNotNone(dt.tzinfo)

    def test_confidence_map(self):
        # 字符串映射
        self.assertEqual(cgc._confidence_map("high"), 0.85)
        self.assertEqual(cgc._confidence_map("HIGH"), 0.85)
        self.assertEqual(cgc._confidence_map("medium"), 0.65)
        self.assertEqual(cgc._confidence_map("low"), 0.4)
        # 数值型直通
        self.assertEqual(cgc._confidence_map(0.95), 0.95)
        self.assertEqual(cgc._confidence_map(1), 1.0)
        # 未知与兜底
        self.assertEqual(cgc._confidence_map("unknown"), 0.5)
        self.assertEqual(cgc._confidence_map(None), 0.5)

    def test_extract_required_elements(self):
        self.assertEqual(cgc._extract_required_elements(""), [])
        self.assertEqual(cgc._extract_required_elements("   \n  "), [])
        req = cgc._extract_required_elements("高中校园晨读，操场跑步")
        self.assertIn("校园/同学/家庭等青春场景", req)
        self.assertIn("关系每章有可见推进", req)

    def test_extract_banned_phrases(self):
        self.assertEqual(cgc._extract_banned_phrases(""), [])
        self.assertEqual(cgc._extract_banned_phrases("   "), [])

        sample = (
            "请注意本题材定位。不要狗血堕胎；禁止恶毒无脑女配；不得跨阶层商战。"
            "不要a；不得这是一段超级超级超级超级超级长的句子超过二十个字都不截断。"
        )
        banned = cgc._extract_banned_phrases(sample)
        self.assertIn("狗血堕胎", banned)
        self.assertIn("恶毒无脑女配", banned)
        self.assertIn("跨阶层商战", banned)
        # 长度小于 2 或大于 20 应被排除
        self.assertNotIn("a", banned)
        self.assertFalse(any(len(x) > 20 for x in banned))

    def test_extract_hook_types(self):
        # 空内容
        self.assertEqual(cgc._extract_hook_types({}), [])
        self.assertEqual(cgc._extract_hook_types({"章尾钩子": "", "正文落点": ""}), [])

        # 包含关键词与去重
        sections = {
            "章尾钩子": "两人在走廊产生误会升级，留下一条未发出的消息。",
            "正文落点": "甜蜜瞬间戛然而止，引来全校起哄围观。",
        }
        hooks = cgc._extract_hook_types(sections)
        types = [h["type"] for h in hooks]
        self.assertIn("误会升级", types)
        self.assertIn("信息断点", types)
        self.assertIn("甜蜜瞬间", types)
        self.assertIn("对手登场", types)
        # 结构验证
        for h in hooks:
            self.assertIsNone(h["frequency"])
            self.assertIsNone(h["strength"])
            self.assertEqual(h["skeleton"], "")

    def test_extract_payoff_types(self):
        # 空内容
        self.assertEqual(cgc._extract_payoff_types({}), [])
        self.assertEqual(cgc._extract_payoff_types({"爽点与情绪释放": "   "}), [])

        # 关键词提取与去重（维护与惩罚均映射为他人认可，补课映射为情感回应）
        sections = {
            "爽点与情绪释放": "男主在众人前霸气维护，私下主动帮女主补课，并在考试后给对手公开惩罚。"
        }
        payoffs = cgc._extract_payoff_types(sections)
        types = [p["type"] for p in payoffs]
        self.assertIn("他人认可", types)
        self.assertIn("情感回应", types)
        # 验证他人认可去重
        self.assertEqual(types.count("他人认可"), 1)
        for p in payoffs:
            self.assertIsNone(p["ratio"])
            self.assertIsNone(p["buildup_length"])
            self.assertEqual(p["skeleton"], "")


class TestParseSections(unittest.TestCase):
    """测试 Markdown 小节解析。"""

    def test_parse_sections_standard(self):
        md = """# 青春甜宠体裁提示卡

## 正文提示词
青春校园轻快对白。

## 开场抓手
从高二开学分班第一天切入。

## 禁止漂移
不要出现豪门恩怨。不得未成年同居。
"""
        sections = cgc.parse_sections(md)
        self.assertEqual(sections["正文提示词"], "青春校园轻快对白。")
        self.assertEqual(sections["开场抓手"], "从高二开学分班第一天切入。")
        self.assertEqual(sections["禁止漂移"], "不要出现豪门恩怨。不得未成年同居。")
        # 未出现的标准小节应保持为空字符串
        self.assertIn("章尾钩子", sections)
        self.assertEqual(sections["章尾钩子"], "")

    def test_parse_sections_unlisted_title(self):
        md = """
## 额外特别小节
这是自定义小节内容。
"""
        sections = cgc.parse_sections(md)
        self.assertIn("额外特别小节", sections)
        self.assertEqual(sections["额外特别小节"], "这是自定义小节内容。")

    def test_parse_sections_empty_body(self):
        sections = cgc.parse_sections("")
        for title in cgc._SECTION_TITLES:
            self.assertIn(title, sections)
            self.assertEqual(sections[title], "")


class TestBuildGenrePack(unittest.TestCase):
    """测试 genre-pack 数据结构组装。"""

    def test_build_genre_pack_full(self):
        frontmatter = {
            "genre": "青春甜宠",
            "aliases": ["校园恋爱", "纯爱"],
            "platform": "番茄",
            "confidence": "high",
            "source": "reference/oh-story/genre-prose-card_青春甜宠.md",
        }
        sections = {
            "正文提示词": "校园晨光与单车少年",
            "章尾钩子": "一条未发出的消息停在屏幕上。",
            "爽点与情绪释放": "男主公开放话维护女主。",
            "禁止漂移": "禁止出现绝症车祸；不要降智恶毒反派。",
        }
        pack = cgc.build_genre_pack(frontmatter, sections, "genre-youth-romance")

        meta = pack["meta"]
        self.assertEqual(meta["id"], "genre-youth-romance")
        self.assertEqual(meta["name"], "青春甜宠")
        self.assertEqual(meta["sub_tags"], ["校园恋爱", "纯爱"])
        self.assertEqual(meta["target_platform"], "番茄")
        self.assertEqual(meta["confidence"], 0.85)
        self.assertEqual(meta["schema_version"], 1)
        self.assertIn("converted_at", meta)
        self.assertEqual(meta["converted_from"], "reference/oh-story/genre-prose-card_青春甜宠.md")

        # 结构验证
        structure = pack["structure"]
        self.assertEqual(structure["chapter_word_range"], {})
        self.assertEqual(structure["chapter_roles"], [])
        self.assertTrue(len(structure["hook_system"]["hook_types"]) >= 1)

        # 商业爽点验证
        commercial = pack["commercial"]
        payoffs = commercial["payoff_density"]["payoff_types"]
        self.assertTrue(len(payoffs) >= 1)

        # 语言规则验证
        rules = pack["language_rules"]
        self.assertIn("出现绝症车祸", rules["banned_phrases"])
        self.assertIn("降智恶毒反派", rules["banned_phrases"])
        self.assertTrue(len(rules["required_elements"]) >= 1)

    def test_build_genre_pack_fallback(self):
        # 缺省字段与字符串别名容错
        frontmatter = {
            "genre": None,
            "aliases": "单标签",
            "platform": None,
            "confidence": "low",
            "source": None,
        }
        pack = cgc.build_genre_pack(frontmatter, {}, "genre-fallback")
        meta = pack["meta"]
        self.assertEqual(meta["name"], "genre-fallback")
        self.assertEqual(meta["sub_tags"], ["单标签"])
        self.assertEqual(meta["target_platform"], "")
        self.assertEqual(meta["confidence"], 0.4)
        self.assertEqual(meta["converted_from"], "")


class TestConvertFunction(unittest.TestCase):
    """测试 convert 转换主流程与幂等逻辑。"""

    def test_load_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "test.json"
            # 不存在
            self.assertIsNone(cgc._load_existing(p))

            # 损坏 JSON
            p.write_text("{bad-json", encoding="utf-8")
            self.assertIsNone(cgc._load_existing(p))

            # 正常 JSON
            p.write_text(json.dumps({"meta": {"schema_version": 1}}), encoding="utf-8")
            data = cgc._load_existing(p)
            self.assertIsNotNone(data)
            self.assertEqual(data["meta"]["schema_version"], 1)

    def test_convert_input_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            in_p = Path(tmpdir) / "nonexistent.md"
            out_p = Path(tmpdir) / "out.json"
            wrote, reason = cgc.convert(in_p, out_p, "genre-test")
            self.assertFalse(wrote)
            self.assertIn("输入文件不存在", reason)
            self.assertFalse(out_p.exists())

    def test_convert_success_writes_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            in_p = Path(tmpdir) / "input.md"
            out_p = Path(tmpdir) / "nested" / "out.json"
            in_p.write_text(
                """---
genre: 青春甜宠
platform: 番茄
confidence: high
---
## 正文提示词
操场微风

## 章尾钩子
发错的消息
""",
                encoding="utf-8",
            )
            wrote, reason = cgc.convert(in_p, out_p, "genre-youth")
            self.assertTrue(wrote)
            self.assertIn("已写出", reason)
            self.assertTrue(out_p.exists())

            with out_p.open("r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            self.assertEqual(loaded["meta"]["id"], "genre-youth")
            self.assertEqual(loaded["meta"]["name"], "青春甜宠")

    def test_convert_force_idempotent_skip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            in_p = Path(tmpdir) / "input.md"
            out_p = Path(tmpdir) / "out.json"
            in_p.write_text("---\ngenre: 青春甜宠\n---\n## 正文提示词\n测试", encoding="utf-8")

            # 首次转换写出
            wrote1, reason1 = cgc.convert(in_p, out_p, "genre-youth")
            self.assertTrue(wrote1)

            # 记录修改时间
            mtime1 = out_p.stat().st_mtime

            # force=True 且同版本（schema_version=1）触发跳过
            wrote2, reason2 = cgc.convert(in_p, out_p, "genre-youth", force=True)
            self.assertFalse(wrote2)
            self.assertIn("幂等跳过", reason2)
            self.assertEqual(out_p.stat().st_mtime, mtime1)

    def test_convert_force_overwrite_different_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            in_p = Path(tmpdir) / "input.md"
            out_p = Path(tmpdir) / "out.json"
            in_p.write_text("---\ngenre: 青春甜宠\n---\n## 正文提示词\n测试", encoding="utf-8")

            # 先写入旧版 schema_version=0
            out_p.write_text(json.dumps({"meta": {"schema_version": 0}}), encoding="utf-8")

            # force=True 时因版本不同，应重新写出覆盖
            wrote, reason = cgc.convert(in_p, out_p, "genre-youth", force=True)
            self.assertTrue(wrote)
            self.assertIn("已写出", reason)
            data = json.loads(out_p.read_text(encoding="utf-8"))
            self.assertEqual(data["meta"]["schema_version"], 1)


class TestConvertGenreCardCLI(unittest.TestCase):
    """测试命令行接口与弃用拦截机制。"""

    def test_main_deprecation_exit_code(self):
        stderr_buf = io.StringIO()
        with patch("sys.stderr", stderr_buf):
            ret = cgc.main(["--input", "in.md", "--output", "out.json", "--genre-id", "test"])
        self.assertEqual(ret, 1)
        err = stderr_buf.getvalue()
        self.assertIn("convert_genre_card.py 已弃用", err)
        self.assertIn("import_genre_prose_cards.py", err)

    def test_main_missing_args(self):
        with patch("sys.stderr", io.StringIO()):
            with self.assertRaises(SystemExit):
                cgc.main([])


if __name__ == "__main__":
    unittest.main()
