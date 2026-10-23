"""技法深度分析质量校验与组装器（scripts/deep_analyze.py）单元测试套件。

覆盖：
1. check_technique_depth 单条技法深度字段非空与完整性校验（齐全/部分缺失/缺失子对象/类型污染）
2. ensure_technique_depth 深度分析结构补齐（新建/增补/异常类型重置/就地修改）
3. analyze_craft_card 整张 craft-card 遍历、统计与缺段映射（多维度/空维度/非字典容错/命名回退）
4. main CLI 命令行入口（文件不存在/正常输出统计/--in-place 写回盘片）
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.deep_analyze as da  # noqa: E402


class TestDeepAnalyzeCore(unittest.TestCase):
    """测试 scripts/deep_analyze.py 核心函数与校验逻辑。"""

    def test_check_technique_depth_complete(self):
        """测试 7 个字段齐全且非空的情况。"""
        tech = {
            "name": "情绪压制逆转",
            "deep_analysis": {
                "reader_psychology": "利用期望落差制造心理压力",
                "execution_steps": "1. 铺垫困境；2. 强化绝望；3. 逆转翻盘",
                "applicable_scene": "高潮前夕与重大决战",
                "usage_boundary": "不可连续滥用导致读者疲劳",
                "intensity_control": "强档：绝境反杀；弱档：日常装逼",
                "combo_patterns": "与扮猪吃老虎搭配使用",
                "migration_checklist": "检查反派压制是否合乎逻辑",
            },
        }
        complete, missing = da.check_technique_depth(tech)
        self.assertTrue(complete)
        self.assertEqual(missing, [])

    def test_check_technique_depth_partial_missing(self):
        """测试部分字段缺失或空白字符串。"""
        tech = {
            "name": "残缺技法",
            "deep_analysis": {
                "reader_psychology": "读者期望",
                "execution_steps": "   ",  # 纯空白视作缺失
                # applicable_scene 缺失
                "usage_boundary": "使用边界",
                "intensity_control": "",
                "combo_patterns": "搭配套路",
                "migration_checklist": "清单",
            },
        }
        complete, missing = da.check_technique_depth(tech)
        self.assertFalse(complete)
        self.assertEqual(
            set(missing),
            {"execution_steps", "applicable_scene", "intensity_control"},
        )

    def test_check_technique_depth_no_or_invalid_deep_analysis(self):
        """测试没有 deep_analysis 或类型非字典的情况。"""
        # 没有 deep_analysis 键
        tech1 = {"name": "无分析技法"}
        complete1, missing1 = da.check_technique_depth(tech1)
        self.assertFalse(complete1)
        self.assertEqual(missing1, da.TECHNIQUE_DEEP_FIELDS)

        # deep_analysis 被污染为字符串
        tech2 = {"name": "污染技法", "deep_analysis": "invalid string"}
        complete2, missing2 = da.check_technique_depth(tech2)
        self.assertFalse(complete2)
        self.assertEqual(missing2, da.TECHNIQUE_DEEP_FIELDS)

    def test_ensure_technique_depth_new_and_preserve(self):
        """测试补齐字段逻辑：创建空键与保留已有内容。"""
        # 1. 完全没有 deep_analysis
        tech1 = {"name": "新技法"}
        res1 = da.ensure_technique_depth(tech1)
        self.assertIs(res1, tech1)
        self.assertIn("deep_analysis", tech1)
        for f in da.TECHNIQUE_DEEP_FIELDS:
            self.assertEqual(tech1["deep_analysis"][f], "")

        # 2. 已有部分字段，保留已有并增补
        tech2 = {
            "name": "半成品技法",
            "deep_analysis": {"reader_psychology": "既有心理"},
        }
        da.ensure_technique_depth(tech2)
        self.assertEqual(tech2["deep_analysis"]["reader_psychology"], "既有心理")
        self.assertEqual(tech2["deep_analysis"]["execution_steps"], "")

        # 3. deep_analysis 污染为非字典，重建并补齐
        tech3 = {"name": "异常字段技法", "deep_analysis": ["not", "a", "dict"]}
        da.ensure_technique_depth(tech3)
        self.assertIsInstance(tech3["deep_analysis"], dict)
        self.assertEqual(len(tech3["deep_analysis"]), len(da.TECHNIQUE_DEEP_FIELDS))

    def test_analyze_craft_card_empty_or_invalid(self):
        """测试空卡片或非字典 craft_analysis 的容错处理。"""
        stats1 = da.analyze_craft_card({})
        self.assertEqual(
            stats1, {"total": 0, "complete": 0, "incomplete": 0, "missing_map": {}}
        )

        stats2 = da.analyze_craft_card({"craft_analysis": "not-a-dict"})
        self.assertEqual(
            stats2, {"total": 0, "complete": 0, "incomplete": 0, "missing_map": {}}
        )

    def test_analyze_craft_card_full_walkthrough(self):
        """测试完整卡片多维度统计与缺段分析。"""
        craft = {
            "meta": {"id": "test-craft", "title": "测试技法卡"},
            "craft_analysis": {
                "structure_craft": {
                    "techniques": [
                        {
                            "name": "完备技法",
                            "deep_analysis": {
                                f: f"内容-{f}" for f in da.TECHNIQUE_DEEP_FIELDS
                            },
                        },
                        {
                            # 缺名字，回退为 <unnamed>
                            "deep_analysis": {
                                "reader_psychology": "读者心理",
                            },
                        },
                        "not-a-tech-dict",  # 脏元素跳过
                    ]
                },
                "emotional_craft": {
                    "techniques": [
                        {
                            "name": "空白技法",
                            # 无 deep_analysis，自动补齐后被判定为缺段
                        }
                    ]
                },
                "invalid_dim": "not-a-dict",  # 脏维度跳过
                "empty_techniques": {"techniques": "not-a-list"},  # 脏维度跳过
            },
        }

        stats = da.analyze_craft_card(craft)
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["complete"], 1)
        self.assertEqual(stats["incomplete"], 2)
        self.assertIn("<unnamed>", stats["missing_map"])
        self.assertIn("空白技法", stats["missing_map"])
        self.assertEqual(len(stats["missing_map"]["空白技法"]), 7)


class TestDeepAnalyzeCLI(unittest.TestCase):
    """测试 scripts/deep_analyze.py main 命令行。"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self):
        import gc

        gc.collect()
        self.tmp_dir.cleanup()

    def test_main_file_not_found(self):
        """测试指定不存在的文件时抛出 SystemExit(1)。"""
        missing_file = self.tmp_path / "not_exist.json"
        err = io.StringIO()
        with mock.patch("sys.stderr", err):
            with self.assertRaises(SystemExit) as cm:
                da.main([str(missing_file)])
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("文件不存在", err.getvalue())

    def test_main_readonly_inspection(self):
        """测试只读统计模式不改写文件。"""
        card_file = self.tmp_path / "craft_card.json"
        raw_card = {
            "meta": {"id": "sample"},
            "craft_analysis": {
                "dim1": {
                    "techniques": [
                        {"name": "技法A", "deep_analysis": {"reader_psychology": "ok"}}
                    ]
                }
            },
        }
        card_file.write_text(json.dumps(raw_card, ensure_ascii=False), encoding="utf-8")

        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            da.main([str(card_file)])

        output_str = out.getvalue()
        self.assertIn("技法总数: 1", output_str)
        self.assertIn("深度齐全: 0", output_str)
        self.assertIn("深度缺段: 1", output_str)
        self.assertIn("缺段明细:", output_str)
        self.assertIn("技法A", output_str)

        # 验证文件未被重写（因未加 --in-place）
        after_data = json.loads(card_file.read_text(encoding="utf-8"))
        self.assertEqual(after_data, raw_card)

    def test_main_in_place_writeback(self):
        """测试 --in-place 模式就地补齐并写回。"""
        card_file = self.tmp_path / "craft_card_inplace.json"
        raw_card = {
            "meta": {"id": "sample-inplace"},
            "craft_analysis": {
                "dim1": {
                    "techniques": [
                        {"name": "技法B"}
                    ]
                }
            },
        }
        card_file.write_text(json.dumps(raw_card, ensure_ascii=False), encoding="utf-8")

        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            da.main([str(card_file), "--in-place"])

        output_str = out.getvalue()
        self.assertIn("已就地补齐并写回", output_str)

        # 验证文件已成功写入补齐后的 7 个字段
        updated_data = json.loads(card_file.read_text(encoding="utf-8"))
        tech = updated_data["craft_analysis"]["dim1"]["techniques"][0]
        self.assertIn("deep_analysis", tech)
        for f in da.TECHNIQUE_DEEP_FIELDS:
            self.assertEqual(tech["deep_analysis"][f], "")


if __name__ == "__main__":
    unittest.main()
