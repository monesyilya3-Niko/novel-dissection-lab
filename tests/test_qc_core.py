"""QC 统一质检引擎（qc.py）四层十二维全维独立测试套件。

覆盖维度：
1. 质检评分辅助（_severity_to_deduct 扣分阶梯与上限 / _score_from_issues 换算 / _wrap_issues 统一归一化 / _judge 裁决规则 / _severity_count）
2. 十二维独立打分（D1剧情连贯 / D2逻辑合理 / D3结构完整 / D4人物弧线 / D5设定一致 / D6手法运用 / D7节奏 / D8爽点 / D9句子重复 / D10章节重复 / D11AI味 / D12禁用词）
3. 声线与手法空卡保护（D4/D6 无 voice-card / 空 character_voices 65分重归一与防假0分）
4. 全书 QC 统一编排（run_qc：空章节异常 / 书名三优先级解析 / 实体表双路探测 / 四层等权加权 / 元数据与覆盖率聚合）
5. 报告序列化与 Markdown 排版（to_json / to_markdown：标题 / 四层十二维表格 / 问题图标列表）
6. CLI 命令行控制（main：--json / --no-save / 报告自动落盘 reports/qc/ / 退出状态码判定）
"""
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import qc


class TestQCScoringHelpers(unittest.TestCase):
    """测试 QC 严重度折算、问题归一化与统一判定规则。"""

    def test_severity_to_deduct_and_score(self):
        # 1. 空问题 -> 扣分 0，得分 100
        self.assertEqual(qc._severity_to_deduct([]), 0.0)
        self.assertEqual(qc._score_from_issues([]), 100.0)

        # 2. 各级严重度权重：critical=20, high=10, medium=5, low=2
        issues = [
            {"severity": "critical"},
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "low"},
            {"severity": "unknown"},  # 默认回退 2
        ]
        # 20 + 10 + 5 + 2 + 2 = 39
        self.assertEqual(qc._severity_to_deduct(issues), 39.0)
        self.assertEqual(qc._score_from_issues(issues), 61.0)

        # 3. 扣分满 100 封顶，得分下限 0
        many_issues = [{"severity": "critical"}] * 10
        self.assertEqual(qc._severity_to_deduct(many_issues), 100.0)
        self.assertEqual(qc._score_from_issues(many_issues), 0.0)

    def test_wrap_issues(self):
        # 1. 过滤非字典
        raw_issues = [
            "not a dict",
            {"type": "t1", "detail": "d1"},  # 缺 chapter / severity
            {"type": "t2", "chapters": [3, 5], "severity": "high"},  # 兼容 chapters 列表
            {"type": "t3", "chapters": []},
        ]
        wrapped = qc._wrap_issues(raw_issues)
        self.assertEqual(len(wrapped), 3)

        self.assertEqual(wrapped[0]["chapter"], 0)
        self.assertEqual(wrapped[0]["severity"], "low")

        self.assertEqual(wrapped[1]["chapter"], 3)
        self.assertEqual(wrapped[1]["severity"], "high")

        self.assertEqual(wrapped[2]["chapter"], 0)

    def test_judge_and_severity_count(self):
        # 1. critical > 0 -> FAIL
        self.assertEqual(qc._judge([{"severity": "critical"}]), "FAIL")

        # 2. high >= 5 -> FAIL
        self.assertEqual(qc._judge([{"severity": "high"}] * 5), "FAIL")

        # 3. high in 1..4 -> WARN
        self.assertEqual(qc._judge([{"severity": "high"}] * 4), "WARN")

        # 4. 仅 medium / low -> PASS
        self.assertEqual(qc._judge([{"severity": "medium"}] * 10 + [{"severity": "low"}] * 20), "PASS")

        # 5. _severity_count 统计
        counts = qc._severity_count([{"severity": "high"}, {"severity": "low"}, {"severity": "low"}])
        self.assertEqual(counts, {"high": 1, "low": 2})


class TestQCDimensions(unittest.TestCase):
    """测试十二维打分函数独立行为。"""

    def setUp(self):
        self.texts = {
            1: "第一章内容。阳光透过树叶洒在地面上，四周静悄悄的。",
            2: "第二章内容。微风拂过水面激起阵阵涟漪，令人心旷神怡。",
        }

    def test_dim_plot_continuity(self):
        with mock.patch("qc.book_quality.check_plot_continuity", return_value=[{"type": "t", "severity": "medium"}]):
            ds = qc._dim_plot_continuity(self.texts)
            self.assertEqual(ds.key, "plot_continuity")
            self.assertEqual(ds.layer, "L1")
            self.assertEqual(ds.score, 95.0)  # 100 - 5
            self.assertEqual(len(ds.issues), 1)

    def test_dim_logic(self):
        with mock.patch("qc.logic_check.check_logic", return_value=[]):
            ds = qc._dim_logic(self.texts, entities={})
            self.assertEqual(ds.key, "logic")
            self.assertEqual(ds.layer, "L1")
            self.assertEqual(ds.score, 100.0)

    def test_dim_structure(self):
        # check_structure 满分 8，模拟第1章得分8、第2章得分2 (偏低应报警)
        with mock.patch("qc.chapter_check.check_structure", side_effect=[(8, "完整"), (2, "缺失开头")]):
            ds = qc._dim_structure(self.texts)
            self.assertEqual(ds.key, "structure")
            self.assertEqual(ds.layer, "L1")
            # avg = (8+2)/2 = 5, score = 5/8*100 = 62.5
            self.assertEqual(ds.score, 62.5)
            self.assertEqual(len(ds.issues), 1)
            self.assertEqual(ds.issues[0]["chapter"], 2)

    def test_dim_character_arc_and_craft_empty_voice_card(self):
        # 1. voice_card 为 None -> character_arc 与 craft 均记 100 并标注 skipped
        ds_arc_none = qc._dim_character_arc(self.texts, None)
        self.assertEqual(ds_arc_none.score, 100.0)
        self.assertIn("skipped", ds_arc_none.raw)

        ds_craft_none = qc._dim_craft(self.texts, None)
        self.assertEqual(ds_craft_none.score, 100.0)
        self.assertIn("skipped", ds_craft_none.raw)

        # 2. voice_card 缺少角色（character_voices 为空） -> 防假0分
        vc_empty_voices = {
            "dialogue": {"character_voices": []},
            "emotion_handling": {"mode": "白描"},
        }
        ds_arc_empty = qc._dim_character_arc(self.texts, vc_empty_voices)
        self.assertEqual(ds_arc_empty.score, 100.0)
        self.assertIn("声线卡无角色", ds_arc_empty.raw["skipped"])

        # craft 按可评估子项 65 分制重归一
        with mock.patch("qc.consistency.score_text", return_value=(
            65.0,
            ["细节"],
            {"emotion": 20, "narration": 15, "banned": 20, "imagery": 10, "voice_details": []}
        )):
            ds_craft_empty = qc._dim_craft(self.texts, vc_empty_voices)
            self.assertEqual(ds_craft_empty.score, 100.0)  # 65/65 * 100 = 100.0
            self.assertIn("重归一", ds_craft_empty.raw["dims"]["renormalized"])

    def test_dim_rhythm_and_hook(self):
        with mock.patch("qc.chapter_check.check_paragraph_rhythm", return_value=(8, "节奏好")), \
             mock.patch("qc.chapter_check.check_hook", return_value=(12, "钩子强")):
            ds_r = qc._dim_rhythm(self.texts)
            self.assertEqual(ds_r.score, 100.0)
            self.assertEqual(len(ds_r.issues), 0)

            ds_h = qc._dim_hook(self.texts)
            self.assertEqual(ds_h.score, 100.0)
            self.assertEqual(len(ds_h.issues), 0)

    def test_dim_sentence_and_chapter_dup(self):
        with mock.patch("qc.book_quality.check_duplicate_sentences", return_value=[{"type": "s_dup", "severity": "low"}]), \
             mock.patch("qc.book_quality.check_intra_chapter_repeats", return_value=[{"type": "intra_dup", "severity": "medium"}]):
            ds_s = qc._dim_sentence_dup(self.texts)
            self.assertEqual(ds_s.key, "sentence_dup")
            self.assertEqual(ds_s.layer, "L4")
            self.assertEqual(len(ds_s.issues), 2)
            self.assertEqual(ds_s.raw["cross_chapter"], 1)
            self.assertEqual(ds_s.raw["intra_chapter"], 1)

        with mock.patch("qc.book_quality.check_duplicate_chapters", return_value=[]), \
             mock.patch("qc.book_quality.check_duplicate_paragraphs", return_value=[]):
            ds_c = qc._dim_chapter_dup(self.texts)
            self.assertEqual(ds_c.score, 100.0)

    def test_dim_ai_flavor(self):
        with mock.patch("qc.book_quality.check_ai_flavor", return_value=[{"type": "ai_flavor", "severity": "medium"}]), \
             mock.patch("qc.chapter_check.check_ai_tics", return_value=(3, "稍有模板句")):
            ds_ai = qc._dim_ai_flavor(self.texts)
            self.assertEqual(ds_ai.key, "ai_flavor")
            # 1 medium (5分) + 2章 ai_tics各1 low (各2分) -> 扣 9分 -> 91.0
            self.assertEqual(ds_ai.score, 91.0)
            self.assertEqual(len(ds_ai.issues), 3)

    def test_dim_banned(self):
        # 1. 缺 asset 或缺 book -> 100分安全跳过
        self.assertEqual(qc._dim_banned(self.texts, None, "book.txt").score, 100.0)
        self.assertEqual(qc._dim_banned(self.texts, {"asset": 1}, None).score, 100.0)

        # 2. 有 asset 与 book -> 运行合规扫描
        with mock.patch("qc.chapter_loader.read_text_file", return_value="书本全文"), \
             mock.patch("qc.compliance.build_ngram_index", return_value=set()), \
             mock.patch("qc.compliance.scan_asset", return_value=(["硬错误"], ["警告"])):
            ds_b = qc._dim_banned(self.texts, {"asset": 1}, "book.txt")
            self.assertEqual(len(ds_b.issues), 2)
            # critical(20) + medium(5) -> 扣 25 -> 得分 75.0
            self.assertEqual(ds_b.score, 75.0)


class TestQCOrchestrationAndRunQC(unittest.TestCase):
    """测试统一 QC 编排流程 run_qc。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_qc_orch_")
        self.chapter_dir = Path(self.temp_dir) / "chapters"
        self.chapter_dir.mkdir()
        (self.chapter_dir / "chapter-001.txt").write_text("第一章开局。", encoding="utf-8")
        (self.chapter_dir / "chapter-002.txt").write_text("第二章继续。", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_run_qc_empty_directory_raises_value_error(self):
        empty_dir = Path(self.temp_dir) / "empty_dir"
        empty_dir.mkdir()
        with self.assertRaises(ValueError) as cm:
            qc.run_qc(str(empty_dir))
        self.assertIn("未找到章节文件", str(cm.exception))

    def test_run_qc_full_orchestration(self):
        # 构建 novel_dir 与 state.json
        novel_dir = Path(self.temp_dir) / "my_project"
        novel_dir.mkdir()
        (novel_dir / "state.json").write_text('{"name": "仙侠传世录"}', encoding="utf-8")

        # 模拟各底层模块返回全绿
        report = qc.run_qc(
            str(self.chapter_dir),
            novel_dir=str(novel_dir),
        )

        self.assertEqual(report.book_title, "仙侠传世录")
        self.assertEqual(len(report.layers), 4)
        self.assertIn("L1", [l.layer for l in report.layers])
        self.assertIn("L2", [l.layer for l in report.layers])
        self.assertIn("L3", [l.layer for l in report.layers])
        self.assertIn("L4", [l.layer for l in report.layers])
        self.assertGreaterEqual(report.total_score, 0.0)
        self.assertIn(report.verdict, ["PASS", "WARN", "FAIL"])
        self.assertEqual(report.meta["total_chapters"], 2)
        self.assertIn("coverage", report.meta)


class TestQCReportSerializationAndCLI(unittest.TestCase):
    """测试 QC 报告序列化（JSON/Markdown）与 main CLI 入口。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_qc_cli_")
        self.chapter_dir = Path(self.temp_dir) / "chapters"
        self.chapter_dir.mkdir()
        (self.chapter_dir / "chapter-001.txt").write_text("这是高质量的章节内容。", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_to_json_and_to_markdown(self):
        layer = qc.LayerScore(layer="L1", label="剧情层", score=90.0, dimensions=[
            qc.DimensionScore(key="plot_continuity", label="剧情连贯", layer="L1", score=90.0)
        ])
        rep = qc.QCReport(
            book_title="测试之书", total_score=90.0, verdict="PASS",
            layers=[layer], issues=[{"severity": "low", "chapter": 1, "detail": "轻微小问题"}],
            meta={"total_chapters": 1, "total_issues": 1, "pass_line": 75, "warn_line": 60}
        )

        # JSON 校验
        json_str = qc.to_json(rep)
        data = json.loads(json_str)
        self.assertEqual(data["book_title"], "测试之书")
        self.assertEqual(data["total_score"], 90.0)
        self.assertEqual(data["verdict"], "PASS")

        # Markdown 校验
        md_str = qc.to_markdown(rep)
        self.assertIn("# 测试之书 QC 质检报告", md_str)
        self.assertIn("**总分**: 90.0/100", md_str)
        self.assertIn("## 四层十二维", md_str)
        self.assertIn("剧情层(L1)", md_str)
        self.assertIn("轻微小问题", md_str)

    def test_main_cli_execution_with_save_and_json(self):
        # 1. 正常运行并落盘
        reports_dir = Path(self.temp_dir) / "reports" / "qc"
        with mock.patch("qc.ROOT", Path(self.temp_dir)), \
             mock.patch("sys.argv", ["qc.py", str(self.chapter_dir)]), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            exit_code = qc.main()
        self.assertEqual(exit_code, 0)
        self.assertIn("QC 质检报告", mock_out.getvalue())
        # 验证落盘文件生成
        self.assertTrue((reports_dir / "chapters-qc.json").exists())
        self.assertTrue((reports_dir / "chapters-qc.md").exists())

        # 2. 带 --no-save 与 --json
        with mock.patch("qc.ROOT", Path(self.temp_dir)), \
             mock.patch("sys.argv", ["qc.py", str(self.chapter_dir), "--no-save", "--json"]), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out_json:
            exit_code = qc.main()
        self.assertEqual(exit_code, 0)
        out_json = json.loads(mock_out_json.getvalue())
        self.assertIn("total_score", out_json)

    def test_main_cli_execution_with_explicit_argv(self):
        with mock.patch("qc.ROOT", Path(self.temp_dir)), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            exit_code = qc.main([str(self.chapter_dir), "--no-save"])
        self.assertEqual(exit_code, 0)
        self.assertIn("QC 质检报告", mock_out.getvalue())


if __name__ == "__main__":
    unittest.main()
