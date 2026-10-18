#!/usr/bin/env python3
"""世界观约束与角色属性别名一致性检测引擎（scripts/setting_check.py）全维独立测试套件。

遵循纯 Python 标准库，零第三方依赖（铁律三）。
全面覆盖：
1. 世界观规则禁用词提取与违规拦截（_extract_banned_keywords / _check_world_rules）；
2. 角色数值属性一致性与冲突检测（_check_attributes 别名穿透与年龄等数值校验）；
3. 别名一致性与称呼混用排查（_check_alias_consistency 全名与别称跨章检测）；
4. 检测覆盖率分析与跳过提示（setting_coverage / _format_coverage_warning）；
5. 综合设定质检入口与命令行接口（check_setting / main 纯文本与 --json 分流及退出码）。
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_TESTS_DIR = Path(__file__).resolve().parent
ROOT = _TESTS_DIR.parent
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(_TESTS_DIR))

import setting_check as sc  # noqa: E402


class TestWorldRuleChecks(unittest.TestCase):
    """测试世界观规则禁用词提取与正文冲突拦截。"""

    def test_extract_banned_keywords_prohibition(self):
        # 常见禁止句式
        rule1 = "校园日常题材。禁止出现枪械。不得使用魔法"
        kws1 = sc._extract_banned_keywords(rule1)
        self.assertIn("枪械", kws1)
        self.assertIn("魔法", kws1)

        rule2 = "严禁提及超能力。避免出现修仙"
        kws2 = sc._extract_banned_keywords(rule2)
        self.assertIn("超能力", kws2)
        self.assertIn("修仙", kws2)

    def test_extract_banned_keywords_negation(self):
        # 无 / 没有 句式
        rule = "纯都市职场，无系统，没有重生"
        kws = sc._extract_banned_keywords(rule)
        self.assertIn("系统", kws)
        self.assertIn("重生", kws)

    def test_extract_banned_keywords_stopwords_and_dedup(self):
        # 停用词被排除（出现/提及/描写等）
        rule = "禁止出现任何枪支，不得提及所有暗杀"
        kws = sc._extract_banned_keywords(rule)
        for stop in ("出现", "提及", "任何", "所有"):
            self.assertNotIn(stop, kws)

    def test_check_world_rules_violation(self):
        texts = {
            1: "今天天气晴朗，两人一同走在校园的小径上。",
            2: "突然，黑衣人拔出一把枪械指向前方！",
        }
        rules = ["禁止出现枪械"]
        issues = sc._check_world_rules(texts, rules)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["type"], "world_rule_violation")
        self.assertEqual(issues[0]["severity"], "high")
        self.assertEqual(issues[0]["chapter"], 2)
        self.assertIn("枪械", issues[0]["detail"])

    def test_check_world_rules_clean_and_edge_cases(self):
        texts = {1: "少年认真复习功课。"}
        # 干净正文零 issue
        self.assertEqual(sc._check_world_rules(texts, ["禁止出现枪械"]), [])
        # 非法规则类型安全跳过
        self.assertEqual(sc._check_world_rules(texts, None), [])
        self.assertEqual(sc._check_world_rules(texts, [123, None]), [])


class TestAttributeChecks(unittest.TestCase):
    """测试角色数值属性冲突检测。"""

    def test_attribute_contradiction_canonical_name(self):
        texts = {
            1: "唐雨今年 18 岁，刚上大学一年级。",
            2: "时隔不久，唐雨 20 岁的时候再次回到故乡。",
        }
        characters = [
            {"name": "唐雨", "aliases": ["小雨"], "attributes": {"年龄": 18}}
        ]
        issues = sc._check_attributes(texts, characters)
        # 第 2 章写成 20 岁与设定 18 岁冲突
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["type"], "attribute_contradiction")
        self.assertEqual(issues[0]["severity"], "high")
        self.assertEqual(issues[0]["chapter"], 2)
        self.assertIn("唐雨", issues[0]["detail"])
        self.assertIn("应为 18", issues[0]["detail"])
        self.assertIn("写为 20", issues[0]["detail"])

    def test_attribute_contradiction_alias_penetration(self):
        # 通过别名定位到实体并发现属性冲突
        texts = {
            1: "小雨 19 岁那天，天空飘起了细雨。",
        }
        characters = [
            {"name": "唐雨", "aliases": ["小雨"], "attributes": {"年龄": 18}}
        ]
        issues = sc._check_attributes(texts, characters)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["chapter"], 1)
        self.assertIn("角色「唐雨」", issues[0]["detail"])
        self.assertIn("写为 19", issues[0]["detail"])

    def test_attribute_matching_and_clean(self):
        # 数值完全一致
        texts = {
            1: "唐雨 18 岁，风华正茂。",
        }
        characters = [
            {"name": "唐雨", "aliases": [], "attributes": {"年龄": 18}}
        ]
        self.assertEqual(sc._check_attributes(texts, characters), [])

        # 非法结构安全容错
        self.assertEqual(sc._check_attributes(texts, None), [])
        self.assertEqual(sc._check_attributes(texts, [{}]), [])
        self.assertEqual(sc._check_attributes(texts, [{"name": "路人", "attributes": {"年龄": "未知"}}]), [])


class TestAliasConsistencyChecks(unittest.TestCase):
    """测试别名一致性与称呼混用排查。"""

    def test_alias_only_without_canonical_name(self):
        texts = {
            1: "小雨低着头走过操场，心情十分沮丧。",
            2: "唐雨微笑着向大家挥手致意，小雨显得格外开心。",
        }
        characters = [
            {"name": "唐雨", "aliases": ["小雨"]}
        ]
        issues = sc._check_alias_consistency(texts, characters)
        # 第 1 章仅出现别名「小雨」而未出现全名「唐雨」
        # 第 2 章全名与别名均出现，合规
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["type"], "alias_consistency")
        self.assertEqual(issues[0]["severity"], "medium")
        self.assertEqual(issues[0]["chapter"], 1)
        self.assertIn("仅以别称「小雨」出现", issues[0]["detail"])

    def test_alias_clean_and_absent(self):
        texts = {
            1: "陌生人在街角驻足观望。",
            2: "唐雨独自在教室内看书。",
        }
        characters = [
            {"name": "唐雨", "aliases": ["小雨"]}
        ]
        # 第 1 章未提及，第 2 章全名提及，均无 issue
        self.assertEqual(sc._check_alias_consistency(texts, characters), [])

        # 空结构安全容错
        self.assertEqual(sc._check_alias_consistency(texts, None), [])
        self.assertEqual(sc._check_alias_consistency(texts, [{"name": "无别名角色"}]), [])


class TestSettingCoverage(unittest.TestCase):
    """测试设定一致性检测项覆盖率分析。"""

    def test_coverage_no_chapters(self):
        cov = sc.setting_coverage({})
        self.assertFalse(cov["entities_loaded"])
        self.assertEqual(cov["chapters"], 0)
        self.assertEqual(cov["evaluable"], [])
        self.assertEqual(cov["skipped"], ["world_rules", "attributes", "alias"])
        self.assertEqual(cov["skipped_reason"], "无章节文本")
        self.assertIn("无章节文本", sc._format_coverage_warning(cov))

    def test_coverage_full_entities(self):
        texts = {1: "正文内容"}
        entities = {
            "characters": [
                {"name": "唐雨", "aliases": ["小雨"], "attributes": {"年龄": 18}}
            ],
            "world_rules": ["禁止枪械"]
        }
        cov = sc.setting_coverage(texts, entities)
        self.assertTrue(cov["entities_loaded"])
        self.assertEqual(cov["chapters"], 1)
        self.assertTrue(cov["checks"]["world_rules"])
        self.assertTrue(cov["checks"]["attributes"])
        self.assertTrue(cov["checks"]["alias"])
        self.assertEqual(set(cov["evaluable"]), {"world_rules", "attributes", "alias"})
        self.assertEqual(cov["skipped"], [])
        self.assertEqual(sc._format_coverage_warning(cov), "")

    def test_coverage_partial_entities(self):
        texts = {1: "正文内容"}
        entities = {
            "characters": [
                {"name": "林羽"}  # 缺 aliases 和 attributes
            ]
            # 缺 world_rules
        }
        cov = sc.setting_coverage(texts, entities)
        self.assertTrue(cov["entities_loaded"])
        self.assertEqual(len(cov["skipped"]), 3)
        self.assertIn("world_rules", cov["skipped"])
        self.assertIn("attributes", cov["skipped"])
        self.assertIn("alias", cov["skipped"])
        warning = sc._format_coverage_warning(cov)
        self.assertIn("⚠ 未评估:", warning)
        self.assertIn("缺少 entities.json 的 world_rules", warning)


class TestCheckSettingAndCLI(unittest.TestCase):
    """测试综合检测入口 check_setting 与 CLI main()。"""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="setting_check_test_"))
        self._chapters_dir = self._tmp / "chapters"
        self._chapters_dir.mkdir(parents=True)
        self._settings_dir = self._tmp / "settings"
        self._settings_dir.mkdir(parents=True)

    def test_check_setting_combination(self):
        texts = {
            1: "小雨 19 岁，私藏了一把枪械。",
        }
        entities = {
            "characters": [
                {"name": "唐雨", "aliases": ["小雨"], "attributes": {"年龄": 18}}
            ],
            "world_rules": ["禁止枪械"]
        }
        issues = sc.check_setting(texts, entities)
        # 一章同时命中：世界观违规 + 属性冲突 + 别名无全名
        self.assertEqual(len(issues), 3)
        types = {it["type"] for it in issues}
        self.assertEqual(types, {"world_rule_violation", "attribute_contradiction", "alias_consistency"})

    def test_check_setting_empty_texts(self):
        self.assertEqual(sc.check_setting({}), [])
        self.assertEqual(sc.check_setting(None), [])

    def test_cli_missing_source(self):
        f = io.StringIO()
        with patch("sys.stderr", f):
            with patch("sys.argv", ["setting_check.py", str(self._tmp / "empty_dir")]):
                with self.assertRaises(SystemExit) as cm:
                    sc.main()
                self.assertEqual(cm.exception.code, 1)
        self.assertIn("未找到章节文件", f.getvalue())

    def test_cli_execution_with_issues_and_json(self):
        # 写入真实测试章节文件与 settings
        ch1 = self._chapters_dir / "chapter-001.txt"
        ch1.write_text("小雨拿出一把枪械。", encoding="utf-8")

        entities_file = self._settings_dir / "entities.json"
        entities_data = {
            "characters": [{"name": "唐雨", "aliases": ["小雨"]}],
            "world_rules": ["禁止枪械"]
        }
        entities_file.write_text(json.dumps(entities_data, ensure_ascii=False), encoding="utf-8")

        # 1. 文本输出模式（有 issues 退出码为 1）
        f_txt = io.StringIO()
        with patch("sys.stdout", f_txt):
            with patch("sys.argv", ["setting_check.py", str(self._chapters_dir)]):
                with self.assertRaises(SystemExit) as cm:
                    sc.main()
                self.assertEqual(cm.exception.code, 1)
        out_txt = f_txt.getvalue()
        self.assertIn("设定一致性检测:", out_txt)
        self.assertIn("Ch1:", out_txt)

        # 2. JSON 模式
        f_json = io.StringIO()
        with patch("sys.stdout", f_json):
            with patch("sys.argv", ["setting_check.py", str(self._chapters_dir), "--json"]):
                with self.assertRaises(SystemExit) as cm:
                    sc.main()
                self.assertEqual(cm.exception.code, 1)
        parsed = json.loads(f_json.getvalue())
        self.assertEqual(parsed["total_chapters"], 1)
        self.assertGreaterEqual(parsed["total_issues"], 1)
        self.assertIn("coverage", parsed)


if __name__ == "__main__":
    unittest.main()
