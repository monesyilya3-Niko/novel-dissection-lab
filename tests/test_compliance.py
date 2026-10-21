"""版权合规扫描脚本 compliance.py 单元与行为级测试（纯标准库，零第三方依赖）。

覆盖 scripts/compliance.py：
1. load_json：
   - 合法 JSON 正常读取；
   - 畸形 JSON 打印失败并以状态码 1 退出。
2. build_ngram_index：
   - 长度小于 WINDOW (12) 返回空集合；
   - 自动清除换行、制表符与空格，生成连续 12-gram 窗口；
   - 中文与特殊符号滑窗索引构造。
3. walk_strings 与 walk_all_values：
   - 字典与列表深层嵌套寻址（形如 a.b[0].c）；
   - 叶子节点全类型（布尔值/数字/字符串）准确提取。
4. find_quoted_fragments：
   - 中文四类引号对（「」、『』、“”、‘’）提取；
   - 英文单双引号对（""、''）提取；
   - 无引号与空串处理。
5. scan_asset 核心合规规则引擎：
   - 嵌套层 abstraction_level == 'verbal' 触发版权红线 REJECT；
   - 嵌套层 contains_verbatim == true 触发版权红线 REJECT（contains_verbatim == false 不误报）；
   - 连续 12 字命中原文 12-gram 触发 REJECT；
   - 章节标题 .title 豁免版权比对；
   - 引号内片段超过 20 字触发 WARN（需人工复核）；
   - 引号内片段不超过 20 字正常放行；
   - 干净资产零错误零警告。
6. main CLI 退出码：
   - PASS 退出码 0；
   - REJECT 退出码 1；
   - WARN 退出码 2。
"""
from __future__ import annotations

import io
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

import compliance  # noqa: E402


class TestComplianceHelpers(unittest.TestCase):
    """合规底层辅助函数测试。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="compliance_test_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_json_valid_and_invalid(self):
        json_file = Path(self.temp_dir) / "test.json"
        json_file.write_text('{"name": "test_asset", "level": 1}', encoding="utf-8")
        data = compliance.load_json(json_file)
        self.assertEqual(data["name"], "test_asset")
        self.assertEqual(data["level"], 1)

        # 畸形 JSON 导致 sys.exit(1)
        bad_json = Path(self.temp_dir) / "bad.json"
        bad_json.write_text("{unclosed json", encoding="utf-8")
        with self.assertRaises(SystemExit) as cm, mock.patch("sys.stdout", new_callable=io.StringIO):
            compliance.load_json(bad_json)
        self.assertEqual(cm.exception.code, 1)

    def test_build_ngram_index_short_and_whitespace(self):
        # 长度小于 12 字
        self.assertEqual(compliance.build_ngram_index("一二三四五六七八九十"), set())

        # 换行与空白清除后正好 12 字
        raw = "一二三  \n四五六\t七八九十壹贰"
        ngrams = compliance.build_ngram_index(raw)
        self.assertEqual(len(ngrams), 1)
        self.assertIn("一二三四五六七八九十壹贰", ngrams)

        # 滑窗测试：14 字产生 3 个 12-gram
        text = "零一二三四五六七八九十百千万"
        ngrams14 = compliance.build_ngram_index(text)
        self.assertEqual(len(ngrams14), 3)
        self.assertIn("零一二三四五六七八九十百", ngrams14)
        self.assertIn("一二三四五六七八九十百千", ngrams14)
        self.assertIn("二三四五六七八九十百千万", ngrams14)

    def test_walk_strings_and_walk_all_values(self):
        doc = {
            "title": "测试小说",
            "meta": {
                "author": "张三",
                "counts": 100,
                "is_active": True,
            },
            "tags": ["玄幻", "热血"],
            "nested_list": [{"note": "第一条"}, {"note": "第二条"}],
        }

        # walk_strings 只收集字典键值中的字符串
        s_list = compliance.walk_strings(doc)
        s_dict = dict(s_list)
        self.assertEqual(s_dict["title"], "测试小说")
        self.assertEqual(s_dict["meta.author"], "张三")
        self.assertEqual(s_dict["nested_list[0].note"], "第一条")
        self.assertEqual(s_dict["nested_list[1].note"], "第二条")
        self.assertNotIn("meta.counts", s_dict)
        self.assertNotIn("meta.is_active", s_dict)

        # walk_all_values 收集字典键值全部叶子节点（含数字/布尔）
        v_list = compliance.walk_all_values(doc)
        v_dict = dict(v_list)
        self.assertEqual(v_dict["meta.counts"], 100)
        self.assertIs(v_dict["meta.is_active"], True)
        self.assertEqual(v_dict["title"], "测试小说")
        self.assertEqual(v_dict["nested_list[0].note"], "第一条")

    def test_find_quoted_fragments(self):
        text = (
            "他说：「第一段对白」然后冷笑：『第二段对白』。"
            "“第三段对白”与‘第四段对白’，以及\"第五段对白\"和'第六段对白'。"
        )
        frags = compliance.find_quoted_fragments(text)
        self.assertEqual(
            frags,
            [
                "第一段对白",
                "第二段对白",
                "第三段对白",
                "第四段对白",
                "第五段对白",
                "第六段对白",
            ],
        )

        # 无引号文本
        self.assertEqual(compliance.find_quoted_fragments("纯叙述文字没有引号"), [])


class TestComplianceScanner(unittest.TestCase):
    """版权合规红线与警告规则扫描测试。"""

    def setUp(self):
        self.corpus_text = "少年负剑行天下风云激荡英雄辈出气壮山河万里长征不畏艰难险阻"
        self.ngram = compliance.build_ngram_index(self.corpus_text)

    def test_clean_asset_passes(self):
        asset = {
            "meta": {
                "name": "原创风格卡",
                "abstraction_level": "analytical",
                "contains_verbatim": False,
            },
            "analysis": "本作注重意象留白，行文节奏明快，对话风格平实而富于哲思。",
            "quotes": ["「短对白」", "『短对白二』"],
        }
        errors, warns = compliance.scan_asset(asset, self.ngram)
        self.assertEqual(errors, [])
        self.assertEqual(warns, [])

    def test_abstraction_level_verbal_rejected(self):
        asset = {
            "meta": {
                "name": "违规卡片",
                "abstraction_level": "verbal",
            }
        }
        errors, warns = compliance.scan_asset(asset, self.ngram)
        self.assertEqual(len(errors), 1)
        self.assertIn("abstraction_level='verbal' → REJECT", errors[0])

    def test_contains_verbatim_true_rejected(self):
        asset = {
            "meta": {
                "name": "违规卡片",
                "contains_verbatim": True,
            }
        }
        errors, warns = compliance.scan_asset(asset, self.ngram)
        self.assertEqual(len(errors), 1)
        self.assertIn("contains_verbatim=true → REJECT", errors[0])

    def test_twelve_gram_verbatim_match_rejected(self):
        # 包含完全匹配原文的连续 12 字片段
        asset = {
            "summary": "在这一章中，少年负剑行天下风云激荡英雄，展现了非凡的胆魄。",
        }
        errors, warns = compliance.scan_asset(asset, self.ngram)
        self.assertEqual(len(errors), 1)
        self.assertIn("连续 12 字匹配原文 → REJECT", errors[0])
        self.assertIn("summary", errors[0])

    def test_title_exempted_from_twelve_gram_match(self):
        # 章节标题是元数据，即便连续 12 字一致也豁免
        asset = {
            "chapter": {
                "title": "少年负剑行天下风云激荡英雄",
            }
        }
        errors, warns = compliance.scan_asset(asset, self.ngram)
        self.assertEqual(errors, [])

    def test_quoted_fragment_warning(self):
        # 引号内片段 > 20 字触发人工复核警告
        long_quote = "「这是一段超过二十个字的长篇摘录，用于检验合规引擎是否能够敏锐触发人工复核警告提示」"
        asset = {
            "note": long_quote,
        }
        errors, warns = compliance.scan_asset(asset, self.ngram)
        self.assertEqual(errors, [])
        self.assertEqual(len(warns), 1)
        self.assertIn("字 > 20 → WARN 人工复核", warns[0])

    def test_multiple_violations_aggregated(self):
        asset = {
            "meta": {
                "abstraction_level": "verbal",
                "contains_verbatim": True,
            },
            "excerpt": "此处写道少年负剑行天下风云激荡英雄辈出！",
            "quote": "“这是一段超过二十个字的长篇摘录，用于检验合规引擎是否能够敏锐触发人工复核警告提示”",
        }
        errors, warns = compliance.scan_asset(asset, self.ngram)
        self.assertEqual(len(errors), 3)  # verbal + verbatim=true + 12-gram
        self.assertEqual(len(warns), 1)   # >20 字引号


class TestComplianceMainCli(unittest.TestCase):
    """compliance.py main 命令行运行测试。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="compliance_cli_")
        self.book_file = Path(self.temp_dir) / "book.txt"
        self.book_file.write_text("少年负剑行天下风云激荡英雄辈出气壮山河万里长征不畏艰难险阻", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_main_cli_pass_exit_0(self):
        asset_file = Path(self.temp_dir) / "clean.json"
        asset_file.write_text(json.dumps({"analysis": "原创行文解析"}), encoding="utf-8")

        test_args = ["compliance.py", str(asset_file), str(self.book_file)]
        with mock.patch("sys.argv", test_args), mock.patch("sys.stdout", new_callable=io.StringIO):
            exit_code = compliance.main()
            self.assertEqual(exit_code, 0)

    def test_main_cli_reject_exit_1(self):
        asset_file = Path(self.temp_dir) / "bad.json"
        asset_file.write_text(json.dumps({"meta": {"abstraction_level": "verbal"}}), encoding="utf-8")

        test_args = ["compliance.py", str(asset_file), str(self.book_file)]
        with mock.patch("sys.argv", test_args), mock.patch("sys.stdout", new_callable=io.StringIO):
            exit_code = compliance.main()
            self.assertEqual(exit_code, 1)

    def test_main_cli_warn_exit_2(self):
        long_q = "「这是一段超过二十个字的长篇摘录，用于检验合规引擎是否能够敏锐触发人工复核警告提示」"
        asset_file = Path(self.temp_dir) / "warn.json"
        asset_file.write_text(json.dumps({"quote": long_q}), encoding="utf-8")

        test_args = ["compliance.py", str(asset_file), str(self.book_file)]
        with mock.patch("sys.argv", test_args), mock.patch("sys.stdout", new_callable=io.StringIO):
            exit_code = compliance.main()
            self.assertEqual(exit_code, 2)

    def test_main_cli_with_explicit_argv(self):
        asset_file = Path(self.temp_dir) / "clean_explicit.json"
        asset_file.write_text(json.dumps({"analysis": "显式传参解析"}), encoding="utf-8")
        with mock.patch("sys.stdout", new_callable=io.StringIO):
            exit_code = compliance.main([str(asset_file), str(self.book_file)])
            self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
