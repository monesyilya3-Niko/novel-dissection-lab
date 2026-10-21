#!/usr/bin/env python3
"""拆书流水线编排核心（pipeline.py）全维独立测试套件（纯标准库 unittest）。

覆盖范围：
1. load_prompt / extract_json / _sample_words / _pass_field_contract 核心辅助函数
2. build_user_input: pass1-5 消息与切片组装及未知 Pass 异常
3. run_pass: dry-run 分支、正常 LLM 调用、Pass2 角色门禁重试、JSON 损坏调试文件记录与超限重试失败
4. assemble_voice_card / assemble_voice_card_v2 / assemble_obs 资产组装与置信度计算
5. run_compliance / write_ai_takeover_guide / _run_distill_hook 辅助逻辑与容错
6. main CLI: 缺失文件拦截、章节过少拦截、无外部模型降级任务生成、dry-run 快速分支、
   Schema 校验失败拦截、合规扫描失败拦截与全流程成功入库
"""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pipeline as pipeline_mod


class TestPipelineHelpers(unittest.TestCase):
    """测试 pipeline 基础解析与提取工具。"""

    def test_extract_json_valid_code_fence(self):
        raw = "分析完成：\n```json\n{\"key\": \"value\", \"num\": 123}\n```\n祝写作顺利！"
        res = pipeline_mod.extract_json(raw)
        self.assertEqual(res, {"key": "value", "num": 123})

    def test_extract_json_plain(self):
        raw = "   {\"name\": \"test\"}   "
        res = pipeline_mod.extract_json(raw)
        self.assertEqual(res, {"name": "test"})

    def test_extract_json_with_surrounding_noise(self):
        raw = "这里是分析报告：{\"data\": [1, 2, 3]} 以上是全部内容。"
        res = pipeline_mod.extract_json(raw)
        self.assertEqual(res, {"data": [1, 2, 3]})

    def test_extract_json_missing_braces_raises(self):
        with self.assertRaises(ValueError) as cm:
            pipeline_mod.extract_json("抱歉，我无法输出 JSON 格式。")
        self.assertIn("输出中找不到 JSON", str(cm.exception))

    def test_load_prompt_all_kinds(self):
        for kind in ("pass1_structure", "pass2_character", "pass3_style", "pass4_commercial", "pass5_craft"):
            sys_t, usr_t = pipeline_mod.load_prompt(kind)
            self.assertIsInstance(sys_t, str)
            self.assertIsInstance(usr_t, str)
            self.assertTrue(len(sys_t) > 0)
            self.assertTrue(len(usr_t) > 0)

    def test_load_prompt_missing_header_raises(self):
        with tempfile.TemporaryDirectory() as td:
            bad_dir = Path(td)
            (bad_dir / "pass1_structure.md").write_text("无标题内容", encoding="utf-8")
            with mock.patch.object(pipeline_mod, "PROMPTS_DIR", bad_dir):
                with self.assertRaises(RuntimeError) as cm:
                    pipeline_mod.load_prompt("pass1_structure")
                self.assertIn("缺少 SYSTEM/USER 区块", str(cm.exception))

    def test_sample_words(self):
        # 1. 显式 sample_words 优先
        manifest = {"sample_words": 15000}
        metrics = {"total_chars": 50000}
        self.assertEqual(pipeline_mod._sample_words(manifest, metrics), 15000)

        # 2. 缺失时回退 metrics.total_chars
        manifest_old = {}
        self.assertEqual(pipeline_mod._sample_words(manifest_old, metrics), 50000)

        # 3. 非整数或 <= 0 时回退
        manifest_invalid = {"sample_words": -5}
        self.assertEqual(pipeline_mod._sample_words(manifest_invalid, metrics), 50000)

    def test_pass_field_contract(self):
        with tempfile.TemporaryDirectory() as td:
            raw_dir = Path(td)
            # 空目录回退
            empty_contract = pipeline_mod._pass_field_contract(raw_dir)
            self.assertIn("本目录暂无旧产出", empty_contract)

            # 有旧产出时提取顶层键
            (raw_dir / "pass1_structure.json").write_text(
                json.dumps({"arcs": [], "chapters": []}), encoding="utf-8"
            )
            (raw_dir / "pass2_character.json").write_text(
                json.dumps({"voices": []}), encoding="utf-8"
            )
            contract = pipeline_mod._pass_field_contract(raw_dir)
            self.assertIn("pass1_structure.json: arcs, chapters", contract)
            self.assertIn("pass2_character.json: voices", contract)


class TestPipelineUserInput(unittest.TestCase):
    """测试 build_user_input 切片与提示词拼装。"""

    def setUp(self):
        self.slices = {
            "pass1_structure": {
                "chapters": [{"index": 1, "title": "初见", "reason": "开篇", "text": "第1章正文", "tail500": "尾部500字"}]
            },
            "pass2_character": {
                "dialogues": [{"chapter": 1, "title": "初见", "before": "他问", "line": "你好", "after": "她答"}]
            },
            "pass3_style": {
                "chapters": [{"index": 2, "title": "试探", "text": "第2章正文"}]
            },
            "pass4_commercial": {
                "chapters": [{"index": 3, "title": "转折", "text": "第3章正文"}]
            },
        }
        self.metrics = {
            "avg_sentence_len": 18.5,
            "dialogue_ratio": 0.22,
            "char_ttr": 0.45,
            "top_bigrams": ["我们", "他们"],
            "sensory": {"visual": 10},
            "exclaim_ratio": 0.05,
        }

    def test_build_user_input_all_passes(self):
        # Pass 1
        p1 = pipeline_mod.build_user_input("pass1_structure", self.slices, self.metrics)
        self.assertIn("第1章 初见", p1)
        self.assertIn("【章末500字】", p1)

        # Pass 2
        p2 = pipeline_mod.build_user_input("pass2_character", self.slices, self.metrics)
        self.assertIn("对话:你好", p2)

        # Pass 3
        p3 = pipeline_mod.build_user_input("pass3_style", self.slices, self.metrics)
        self.assertIn("【量化指标】", p3)
        self.assertIn("avg_sentence_len", p3)
        self.assertIn("第2章 试探", p3)

        # Pass 4
        p4 = pipeline_mod.build_user_input("pass4_commercial", self.slices, self.metrics)
        self.assertIn("第3章 转折", p4)

        # Pass 5
        p5 = pipeline_mod.build_user_input("pass5_craft", self.slices, self.metrics)
        self.assertIn("第1章 初见（开篇）", p5)
        self.assertIn("第2章 试探", p5)

    def test_build_user_input_unknown_raises(self):
        with self.assertRaises(ValueError) as cm:
            pipeline_mod.build_user_input("unknown_pass", self.slices, self.metrics)
        self.assertIn("未知 Pass", str(cm.exception))


class TestPipelineRunPass(unittest.TestCase):
    """测试 run_pass 执行与重试机制。"""

    def setUp(self):
        self.slices = {
            "pass1_structure": {"chapters": []},
            "pass2_character": {"dialogues": []},
            "pass3_style": {"chapters": []},
            "pass4_commercial": {"chapters": []},
        }
        self.metrics = {"avg_sentence_len": 20, "dialogue_ratio": 0.2, "char_ttr": 0.5,
                        "top_bigrams": [], "sensory": {}, "exclaim_ratio": 0.05}

    def test_run_pass_dry_run(self):
        res = pipeline_mod.run_pass("pass1_structure", self.slices, self.metrics, dry_run=True, model_id=None)
        self.assertTrue(res.get("_dry_run"))
        self.assertIn("model", res)

    def test_run_pass_successful_chat(self):
        mock_res = {
            "text": json.dumps({"arcs": [{"title": "主线"}]}),
            "model_id": "test-model",
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "cost": 0.01,
            "elapsed": 0.8,
        }
        with mock.patch.object(pipeline_mod.llm_client, "chat", return_value=mock_res):
            res = pipeline_mod.run_pass("pass1_structure", self.slices, self.metrics, dry_run=False, model_id=None)
        self.assertIn("arcs", res)
        self.assertEqual(res["_meta"]["model"], "test-model")
        self.assertEqual(res["_meta"]["cost"], 0.01)

    def test_run_pass_pass2_character_retry(self):
        # 第一次返回 1 个角色，第二次返回 2 个角色
        mock_res_1 = {
            "text": json.dumps({"voices": [{"name": "主角", "speech_traits": ["短句"]}]}),
            "model_id": "test-model",
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "cost": 0.01,
            "elapsed": 0.8,
        }
        mock_res_2 = {
            "text": json.dumps({
                "voices": [
                    {"name": "主角", "speech_traits": ["短句"]},
                    {"name": "配角", "speech_traits": ["长句"]},
                ]
            }),
            "model_id": "test-model",
            "prompt_tokens": 120,
            "completion_tokens": 80,
            "cost": 0.02,
            "elapsed": 1.1,
        }
        with mock.patch.object(pipeline_mod.llm_client, "chat", side_effect=[mock_res_1, mock_res_2]):
            res = pipeline_mod.run_pass("pass2_character", self.slices, self.metrics, dry_run=False, model_id=None)
        self.assertIn("voices", res)
        self.assertEqual(len(res["voices"]), 2)

    def test_run_pass_json_failure_saves_debug_file_and_retries(self):
        mock_bad = {
            "text": "不是合法的 JSON 内容",
            "model_id": "test-model",
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "cost": 0.005,
            "elapsed": 0.4,
        }
        mock_good = {
            "text": json.dumps({"success": True}),
            "model_id": "test-model",
            "prompt_tokens": 60,
            "completion_tokens": 30,
            "cost": 0.006,
            "elapsed": 0.5,
        }
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(pipeline_mod, "ROOT", Path(td)), \
                 mock.patch.object(pipeline_mod.llm_client, "chat", side_effect=[mock_bad, mock_good]):
                res = pipeline_mod.run_pass("pass1_structure", self.slices, self.metrics, dry_run=False, model_id=None)
            self.assertTrue(res.get("success"))
            debug_file = Path(td) / "corpus" / "debug" / "pass1_structure_attempt0.txt"
            self.assertTrue(debug_file.is_file())
            self.assertIn("不是合法的", debug_file.read_text(encoding="utf-8"))

    def test_run_pass_fails_after_max_attempts(self):
        mock_bad = {
            "text": "持续损坏的响应",
            "model_id": "test-model",
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "cost": 0.005,
            "elapsed": 0.4,
        }
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(pipeline_mod, "ROOT", Path(td)), \
                 mock.patch.object(pipeline_mod.llm_client, "chat", return_value=mock_bad):
                with self.assertRaises(RuntimeError) as cm:
                    pipeline_mod.run_pass("pass1_structure", self.slices, self.metrics, dry_run=False, model_id=None)
                self.assertIn("多次调用未产出合格输出", str(cm.exception))


class TestPipelineAssetAssembly(unittest.TestCase):
    """测试 voice-card、structure-obs、commercial-obs 资产组装与置信度算法。"""

    def setUp(self):
        self.manifest_small = {
            "selected_count": 5,
            "selected_indices": [1, 2, 3, 4, 5],
            "sample_words": 10000,
        }
        self.manifest_large = {
            "selected_count": 20,
            "selected_indices": list(range(1, 21)),
            "sample_words": 50000,
        }
        self.metrics = {"dialogue_ratio": 0.25, "total_chars": 100000}

    def test_assemble_voice_card(self):
        pass2 = {"character_voices": [{"name": "主角", "archetype": "坚定"}]}
        pass3 = {
            "narration": {"pov": "第三人称"},
            "dialogue": {"tag_style": "轻动词", "subtext_level": "中等"},
            "emotion_handling": {"mode": "神态动作"},
            "imagery": {"domains": ["自然"]},
            "banned": {"never_used_words": ["突然"]},
        }
        # 小样本强制置信度 <= 0.6
        vc_small = pipeline_mod.assemble_voice_card("书A", "urban", self.manifest_small, pass2, pass3, self.metrics)
        self.assertEqual(vc_small["meta"]["confidence"], 0.6)
        self.assertEqual(vc_small["dialogue"]["dialogue_ratio"], 0.25)
        self.assertFalse(vc_small["provenance"]["contains_verbatim"])

        # 大样本置信度 > 0.6
        vc_large = pipeline_mod.assemble_voice_card("书A", "urban", self.manifest_large, pass2, pass3, self.metrics)
        self.assertGreater(vc_large["meta"]["confidence"], 0.6)

    def test_assemble_voice_card_v2(self):
        voices = [{"name": "主角", "role": "主角"}]
        narration = {"pov": "第一人称"}
        dialogue = {"tag_style": "极简"}
        emotion = {"mode": "微动作"}
        imagery = {}
        banned = {}
        vc_v2 = pipeline_mod.assemble_voice_card_v2(
            "书B", "xianxia", self.manifest_small,
            voices, narration, dialogue, emotion, imagery, banned, self.metrics
        )
        self.assertEqual(vc_v2["dialogue"]["character_voices"], voices)
        self.assertEqual(vc_v2["meta"]["source_title"], "书B")

    def test_assemble_obs(self):
        pass1_out = {"_meta": {"tokens": 100}, "chapter_word_range": {"typical": 2500}}
        obs = pipeline_mod.assemble_obs("structure", "书C", "sci-fi", pass1_out)
        self.assertTrue(obs["meta"]["awaiting_aggregation"])
        self.assertEqual(obs["meta"]["min_books_required"], 3)
        self.assertEqual(obs["chapter_word_range"]["typical"], 2500)
        self.assertNotIn("_meta", obs)


class TestPipelineComplianceAndDistill(unittest.TestCase):
    """测试合规扫描封装与蒸馏 Hook 逻辑。"""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.assets_dir = Path(self.td.name) / "assets"
        self.assets_dir.mkdir(parents=True)

    def tearDown(self):
        self.td.cleanup()

    def test_run_compliance_return_codes(self):
        asset_file = self.assets_dir / "test-voice-card.json"
        asset_file.write_text(json.dumps({"meta": {"name": "test"}}), encoding="utf-8")
        book_file = self.assets_dir / "test.txt"
        book_file.write_text("第一章 正文内容", encoding="utf-8")

        # 1. 无错误无警告 -> 0
        with mock.patch.object(pipeline_mod.compliance_mod, "scan_asset", return_value=([], [])):
            self.assertEqual(pipeline_mod.run_compliance(asset_file, book_file), 0)

        # 2. 有警告 -> 2
        with mock.patch.object(pipeline_mod.compliance_mod, "scan_asset", return_value=([], ["警告项"])):
            self.assertEqual(pipeline_mod.run_compliance(asset_file, book_file), 2)

        # 3. 有错误 -> 1
        with mock.patch.object(pipeline_mod.compliance_mod, "scan_asset", return_value=(["REJECT 抄袭"], [])):
            self.assertEqual(pipeline_mod.run_compliance(asset_file, book_file), 1)

    def test_run_distill_hook_under_threshold_skips(self):
        # 仅 1 本同题材书
        (self.assets_dir / "b1-voice-card.json").write_text(
            json.dumps({"meta": {"genre": "urban"}}), encoding="utf-8"
        )
        with mock.patch.object(pipeline_mod, "ASSETS_DIR", self.assets_dir), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as fake_out:
            pipeline_mod._run_distill_hook("urban")
            self.assertIn("暂不蒸馏", fake_out.getvalue())

    def test_run_distill_hook_success_when_enough_books(self):
        # 3 本同题材书
        for i in range(1, 4):
            (self.assets_dir / f"b{i}-voice-card.json").write_text(
                json.dumps({"meta": {"genre": "urban"}}), encoding="utf-8"
            )
        mock_distill = mock.MagicMock()
        with mock.patch.object(pipeline_mod, "ASSETS_DIR", self.assets_dir), \
             mock.patch.dict("sys.modules", {"distill": mock_distill}):
            pipeline_mod._run_distill_hook("urban")
            mock_distill.run_distill.assert_called_once_with("urban")

    def test_write_ai_takeover_guide(self):
        ai_dir = self.assets_dir / "raw" / "book_test"
        guide_path = pipeline_mod.write_ai_takeover_guide(
            "测试书", "urban", 5, 20, ai_dir, "无可用外部模型"
        )
        self.assertTrue(guide_path.is_file())
        text = guide_path.read_text(encoding="utf-8")
        self.assertIn("测试书", text)
        self.assertIn("无可用外部模型", text)
        self.assertIn("采样: 5/20 章", text)


class TestPipelineMainCLI(unittest.TestCase):
    """测试 pipeline.main 顶层 CLI 门禁。"""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def _make_book(self, filename: str, chapters: int = 6) -> Path:
        p = self.root_dir / filename
        parts = []
        for i in range(1, chapters + 1):
            parts.append(f"第{i}章 标题{i}\n" + ("正文内容测试。" * 150) + "\n")
        p.write_text("\n".join(parts), encoding="utf-8")
        return p

    def test_main_book_not_found_exits(self):
        with mock.patch("sys.argv", ["pipeline.py", str(self.root_dir / "not_found.txt")]):
            with self.assertRaises(SystemExit) as cm:
                pipeline_mod.main()
            self.assertIn("文件不存在", str(cm.exception))

    def test_main_too_few_chapters_exits(self):
        short_book = self._make_book("short.txt", chapters=3)
        with mock.patch("sys.argv", ["pipeline.py", str(short_book)]):
            with self.assertRaises(SystemExit) as cm:
                pipeline_mod.main()
            self.assertIn("章节过少", str(cm.exception))

    def test_main_no_external_model_generates_guide(self):
        book = self._make_book("valid.txt", chapters=6)
        with mock.patch("sys.argv", ["pipeline.py", str(book), "--genre", "urban"]), \
             mock.patch.object(pipeline_mod, "ROOT", self.root_dir), \
             mock.patch.object(pipeline_mod, "ASSETS_DIR", self.root_dir / "assets"), \
             mock.patch.object(pipeline_mod.llm_client, "any_model_configured", return_value=False):
            rc = pipeline_mod.main()
            self.assertEqual(rc, 0)
            guide = self.root_dir / "corpus" / "raw" / "valid" / "AI接管任务.md"
            self.assertTrue(guide.is_file())

    def test_main_dry_run_success(self):
        book = self._make_book("valid.txt", chapters=6)
        with mock.patch("sys.argv", ["pipeline.py", str(book), "--genre", "urban", "--dry-run"]), \
             mock.patch.object(pipeline_mod, "ROOT", self.root_dir), \
             mock.patch.object(pipeline_mod, "ASSETS_DIR", self.root_dir / "assets"), \
             mock.patch.object(pipeline_mod.llm_client, "any_model_configured", return_value=True):
            rc = pipeline_mod.main()
            self.assertEqual(rc, 0)
            manifest = self.root_dir / "corpus" / "sampled" / "valid" / "manifest.json"
            self.assertTrue(manifest.is_file())
            metrics = self.root_dir / "corpus" / "metrics" / "valid.json"
            self.assertTrue(metrics.is_file())


    def test_main_with_explicit_argv_and_dry_run(self):
        book = self._make_book("valid_argv.txt", chapters=6)
        argv = [str(book), "--genre", "urban", "--dry-run"]
        with mock.patch.object(pipeline_mod, "ROOT", self.root_dir), \
             mock.patch.object(pipeline_mod, "ASSETS_DIR", self.root_dir / "assets"), \
             mock.patch.object(pipeline_mod.llm_client, "any_model_configured", return_value=True):
            rc = pipeline_mod.main(argv)
            self.assertEqual(rc, 0)

    def test_main_llm_error_degradation_generates_guide_and_returns_1(self):
        book = self._make_book("valid_err.txt", chapters=6)
        argv = [str(book), "--genre", "urban"]
        with mock.patch.object(pipeline_mod, "ROOT", self.root_dir), \
             mock.patch.object(pipeline_mod, "ASSETS_DIR", self.root_dir / "assets"), \
             mock.patch.object(pipeline_mod.llm_client, "any_model_configured", return_value=True), \
             mock.patch.object(pipeline_mod, "run_pass", side_effect=pipeline_mod.llm_client.LLMError("模型 'test' 调用失败: 403 Forbidden")):
            rc = pipeline_mod.main(argv)
            self.assertEqual(rc, 1)
            raw_dir = self.root_dir / "corpus" / "raw" / "valid_err"
            guide = raw_dir / "AI接管任务.md"
            self.assertTrue(guide.is_file())
            self.assertIn("外部模型调用失败", guide.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
