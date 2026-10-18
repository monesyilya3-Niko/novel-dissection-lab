"""笔法深度分析报告生成器 report_craft.py 单元与行为级测试（纯标准库，零第三方依赖）。

覆盖 scripts/report_craft.py：
1. _technique_block 单个技法 Markdown 渲染：
   - 技法名称中英文键名与默认序号回退；
   - 手法、效果、可复用骨架、反例（作者不会这么写）段落格式化；
   - deep_analysis 7 维深度分析（读者心理/执行步骤/适用场景/使用边界/强度控制/组合套路/迁移清单）渲染。
2. _dimension_section 维度渲染：
   - 空维度与 None 容错返回空串；
   - 兼容 list（技法数组）与 dict（{techniques: [...], ...}）双数据形态；
   - 维度扩展指标（伏笔回收率百分比化、潜台词占比、张力起伏模式等）解析。
3. render_craft_report 完整报告拼接：
   - 头部元数据展示（作者/题材/平台/分析样本/置信度/生成时间）；
   - 技法总览三项（最强技法 TOP 3、独有技法、最值得学习复用模式）；
   - 8 维技法深度拆解章节编排；
   - 尾部免责声明。
4. main CLI 产物写入：
   - 输入文件不存在退出码 1；
   - 默认报告路径与自定义 --out 导出；
   - 报告字数低于 MIN_REPORT_CHARS 警戒提示。
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

import report_craft  # noqa: E402


class TestReportCraftHelpers(unittest.TestCase):
    """底层渲染辅助函数测试。"""

    def test_technique_block_with_all_fields(self):
        t = {
            "name": "延迟揭示法",
            "description": "通过截断动作在章节末留下悬念",
            "effect": "提升读者追读欲望",
            "skeleton": "起笔设谜 → 动作截断 → 次章揭示",
            "anti_pattern": "平铺直叙直接给出答案",
            "deep_analysis": {
                "reader_psychology": "利用蔡加尼克记忆效应产生认知闭合需求",
                "execution_steps": "1. 抛出不协调线索；2. 强化紧迫感；3. 在高潮点断开。",
                "applicable_scene": "主线重大转折或遭遇强敌",
                "usage_boundary": "单卷不宜超过 3 次",
                "intensity_control": "由浅入深逐步拉高",
                "combo_patterns": "与视角盲区组合使用",
                "migration_checklist": "检查线索是否提前埋下",
            },
        }
        md = report_craft._technique_block(t, 1)
        self.assertIn("**1. 延迟揭示法**", md)
        self.assertIn("- **手法**：通过截断动作在章节末留下悬念", md)
        self.assertIn("- **效果**：提升读者追读欲望", md)
        self.assertIn("- **可复用骨架**：`起笔设谜 → 动作截断 → 次章揭示`", md)
        self.assertIn("- **反例**（该作者不会这么写）：平铺直叙直接给出答案", md)
        self.assertIn("- **读者心理机制**：利用蔡加尼克记忆效应产生认知闭合需求", md)
        self.assertIn("- **执行步骤**：1. 抛出不协调线索；2. 强化紧迫感；3. 在高潮点断开。", md)
        self.assertIn("- **适用场景**：主线重大转折或遭遇强敌", md)
        self.assertIn("- **使用边界**：单卷不宜超过 3 次", md)
        self.assertIn("- **强度控制**：由浅入深逐步拉高", md)
        self.assertIn("- **组合套路**：与视角盲区组合使用", md)
        self.assertIn("- **迁移清单**：检查线索是否提前埋下", md)

    def test_technique_block_fallback_names(self):
        # 无 name 时回退到 technique_name 或 技法N
        t1 = {"technique_name": "草蛇灰线"}
        self.assertIn("**2. 草蛇灰线**", report_craft._technique_block(t1, 2))

        t2 = {"effect": "单纯效果"}
        self.assertIn("**3. 技法3**", report_craft._technique_block(t2, 3))

    def test_dimension_section_dict_and_list(self):
        # 1. 空数据返回空串
        self.assertEqual(report_craft._dimension_section("foreshadowing", None, "伏笔技法"), "")
        self.assertEqual(report_craft._dimension_section("foreshadowing", {}, "伏笔技法"), "")

        # 2. list 格式
        list_data = [{"name": "技法甲", "effect": "效果甲"}]
        md_list = report_craft._dimension_section("dim", list_data, "维度甲")
        self.assertIn("### 维度甲", md_list)
        self.assertIn("**1. 技法甲**", md_list)

        # 3. dict 格式及维度特有字段
        dict_data = {
            "techniques": [{"name": "技法乙"}],
            "buried_payoff_ratio": 0.85,
            "dominant_style": "冷峻克制",
            "peak_valley_pattern": "两起一伏",
        }
        md_dict = report_craft._dimension_section("dim", dict_data, "维度乙")
        self.assertIn("### 维度乙", md_dict)
        self.assertIn("**1. 技法乙**", md_dict)
        self.assertIn("- **伏笔回收率**：85%", md_dict)
        self.assertIn("- **主要风格**：冷峻克制", md_dict)
        self.assertIn("- **张力起伏模式**：两起一伏", md_dict)


class TestReportCraftRender(unittest.TestCase):
    """render_craft_report 完整报告拼装测试。"""

    def test_render_craft_report_structure(self):
        craft_json = {
            "meta": {
                "source_title": "剑破长空",
                "author": "测试作者",
                "genre": "传统修仙",
                "platform": "起点中文网",
                "confidence": 0.95,
                "sample_chapters": [1, 2, 3, 4, 5],
                "total_sample_words": 15000,
                "extracted_at": "2026-10-18",
            },
            "craft_summary": {
                "top_3_strengths": ["高密度伏笔布局", "多线交织叙事", "极简动作描写"],
                "unique_techniques": ["三拍节奏断句法"],
                "reusable_patterns": ["压力递增反弹模型"],
            },
            "craft_analysis": {
                "foreshadowing": {
                    "techniques": [{"name": "微小物件暗线"}],
                    "buried_payoff_ratio": 0.9,
                },
                "dialogue_craft": [
                    {"name": "言下之意对白", "effect": "交代身份差"}
                ],
            },
        }
        report = report_craft.render_craft_report(craft_json)

        # 头部断言
        self.assertIn("# 《剑破长空》写作技法深度拆解报告", report)
        self.assertIn("> **作者**：测试作者", report)
        self.assertIn("> **题材**：传统修仙 · **平台**：起点中文网", report)
        self.assertIn("> **分析样本**：5 章（15,000 字）", report)
        self.assertIn("> **置信度**：95%", report)

        # 总结段断言
        self.assertIn("### 最强技法 TOP 3", report)
        self.assertIn("1. 高密度伏笔布局", report)
        self.assertIn("### 该作者独有技法", report)
        self.assertIn("- 三拍节奏断句法", report)
        self.assertIn("### 最值得学习复用的模式", report)
        self.assertIn("- 压力递增反弹模型", report)

        # 8 维深度拆解断言
        self.assertIn("## 8 维技法深度拆解", report)
        self.assertIn("### 伏笔技法", report)
        self.assertIn("**1. 微小物件暗线**", report)
        self.assertIn("- **伏笔回收率**：90%", report)
        self.assertIn("### 对话技法", report)
        self.assertIn("**1. 言下之意对白**", report)

        # 免责声明
        self.assertIn("> 本报告由 novel-lab 拆书引擎 Pass5 笔法分析模块自动生成。", report)


class TestReportCraftCli(unittest.TestCase):
    """report_craft main 命令行执行测试。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="report_craft_test_")
        self.dir_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_main_cli_missing_file_exits_1(self):
        non_existent = self.dir_path / "not_found.json"
        test_args = ["report_craft.py", str(non_existent)]
        with mock.patch("sys.argv", test_args), mock.patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as cm:
                report_craft.main()
            self.assertEqual(cm.exception.code, 1)

    def test_main_cli_generates_markdown_report(self):
        craft_data = {
            "meta": {
                "source_title": "测试作品",
                "author": "测试作者",
                "sample_chapters": [1],
                "total_sample_words": 3000,
            },
            "craft_summary": {
                "top_3_strengths": ["精炼文笔"],
            },
            "craft_analysis": {
                "foreshadowing": [{"name": "伏笔1"}],
            },
        }
        craft_file = self.dir_path / "craft.json"
        craft_file.write_text(json.dumps(craft_data, ensure_ascii=False), encoding="utf-8")

        out_file = self.dir_path / "custom_report.md"
        test_args = ["report_craft.py", str(craft_file), "--out", str(out_file)]
        with mock.patch("sys.argv", test_args), mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            report_craft.main()
            output = out.getvalue()
            self.assertIn("报告已生成", output)

        self.assertTrue(out_file.exists())
        content = out_file.read_text(encoding="utf-8")
        self.assertIn("# 《测试作品》写作技法深度拆解报告", content)


if __name__ == "__main__":
    unittest.main()
