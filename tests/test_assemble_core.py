"""资产组装引擎核心（assemble.py）全维独立测试套件。

覆盖维度：
1. 文件读取与编码容错（load_json：标准 UTF-8 / 带 BOM utf-8-sig 回退）
2. 置信度测算与样本字数兜底（_confidence 门槛与递增 / _sample_words 优先 manifest 与回退 metrics）
3. 原文引用合规清洗（_clean_verbatim 树形遍历 / 命中清理 / 未命中保留）
4. voice-card 组装规范（assemble_voice_card 结构 / character_voices 回填 / 元数据与溯源）
5. 观测资产组装与容错补齐（assemble_obs：structure-obs 提取章号 / commercial-obs common_mistakes 双路兜底 / 待聚合标注）
6. craft-card 组装与 4 类格式兼容（assemble_craft_card：已整理格式 / 多维直填 / chapter_analysis 拆解归类 / techniques 列表匹配 / 技法名称截断与补齐）
7. 来源指纹生成与版本追溯（source_fingerprint / SOURCE_PASSES 16位哈希 / 缺失文件容错）
8. CLI 主控流程与内存校验防线（main：缺失前置清单退出 / 内存校验失败阻止落盘 / 全量通过原子写入）
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

import assemble


class TestAssembleFileAndMathHelpers(unittest.TestCase):
    """测试文件读取、置信度算法与采样字数字段处理。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_assemble_helpers_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_json_utf8_and_bom(self):
        # 1. 标准 utf-8
        f_utf8 = Path(self.temp_dir) / "normal.json"
        f_utf8.write_text('{"name": "正常JSON"}', encoding="utf-8")
        self.assertEqual(assemble.load_json(f_utf8), {"name": "正常JSON"})

        # 2. 带 BOM 的 utf-8-sig
        f_bom = Path(self.temp_dir) / "bom.json"
        f_bom.write_text('{"name": "BOM_JSON"}', encoding="utf-8-sig")
        self.assertEqual(assemble.load_json(f_bom), {"name": "BOM_JSON"})

    def test_confidence_calculation(self):
        # 样本 < 10 章强制 0.6
        self.assertEqual(assemble._confidence(0), 0.6)
        self.assertEqual(assemble._confidence(5), 0.6)
        self.assertEqual(assemble._confidence(9), 0.6)

        # 样本 >= 10 章线性增加，但最高不超过 0.9
        conf_10 = assemble._confidence(10)
        self.assertAlmostEqual(conf_10, 0.65 + 10 / 80)
        self.assertGreater(conf_10, 0.6)

        conf_80 = assemble._confidence(80)
        self.assertAlmostEqual(conf_80, 0.9)

        conf_200 = assemble._confidence(200)
        self.assertEqual(conf_200, 0.9)

    def test_sample_words_precedence(self):
        # 1. 优先使用 manifest.sample_words
        m1 = {"sample_words": 15000}
        met1 = {"total_chars": 200000}
        self.assertEqual(assemble._sample_words(m1, met1), 15000)

        # 2. 缺失或非正整数时回退到 metrics.total_chars
        m2 = {}
        met2 = {"total_chars": 88888}
        self.assertEqual(assemble._sample_words(m2, met2), 88888)

        m3 = {"sample_words": 0}
        self.assertEqual(assemble._sample_words(m3, met2), 88888)

        # 3. 两处皆无
        self.assertEqual(assemble._sample_words({}, {}), 0)


class TestCleanVerbatim(unittest.TestCase):
    """测试资产合规清洗逻辑 _clean_verbatim。"""

    def test_clean_verbatim_integration(self):
        book_text = "这是一段来自小说的长篇完整原文，包含了非常特别的台词与独白段落。"
        asset = {
            "meta": {"title": "测试资产"},
            "refusal_pattern": "例如「这是一段来自小说的长篇完整原文」的口吻",
            "normal_rule": "正常的概括规则叙述，不含原文",
            "character_list": [
                {"quote": "包含特别台词：这是一段来自小说的长篇完整原文。"}
            ],
        }
        cleaned_asset, changed = assemble._clean_verbatim(asset, book_text)
        self.assertGreater(changed, 0)
        self.assertNotIn("这是一段来自小说的长篇完整原文", cleaned_asset["refusal_pattern"])
        self.assertEqual(cleaned_asset["normal_rule"], "正常的概括规则叙述，不含原文")


class TestAssembleVoiceCard(unittest.TestCase):
    """测试 voice-card 资产组装 assemble_voice_card。"""

    def test_assemble_voice_card_structure(self):
        name = "demo_book"
        genre = "urban"
        manifest = {"selected_indices": [1, 2, 3], "selected_count": 3, "sample_words": 9000}
        metrics = {"total_chars": 50000}
        voices = [{"name": "主角A", "role": "主角"}]
        narration = {"pov": "第三人称"}
        dialogue = {}
        emotion = {"mode": "体感白描"}
        imagery = {"high_freq": ["雨水"]}
        banned = {"words": ["现代词"]}

        card = assemble.assemble_voice_card(
            name, genre, manifest, metrics,
            voices, narration, dialogue, emotion, imagery, banned
        )

        self.assertEqual(card["meta"]["source_title"], "demo_book")
        self.assertEqual(card["meta"]["genre"], "urban")
        self.assertEqual(card["meta"]["total_sample_words"], 9000)
        self.assertEqual(card["meta"]["confidence"], 0.6)
        self.assertFalse(card["meta"]["human_reviewed"])
        self.assertEqual(card["dialogue"]["character_voices"], voices)
        self.assertFalse(card["provenance"]["contains_verbatim"])


class TestAssembleObservations(unittest.TestCase):
    """测试 structure-obs 与 commercial-obs 组装及特殊修复。"""

    def test_assemble_structure_obs_fixes_chapter_from_title(self):
        pass1 = {
            "_internal_debug": "ignore me",
            "chapter_analyses": [
                {"title": "第1章 晨光与侧影", "role": "开篇引入"},
                {"title": "第十二回 狂风骤雨", "role": "冲突升级"},  # 非数字章号不崩
                {"chapter": "3", "title": "第3章 既有章号", "role": "转折"},
            ]
        }
        obs = assemble.assemble_obs("structure", "my_book", "xianxia", pass1)
        self.assertNotIn("_internal_debug", obs)
        self.assertEqual(obs["meta"]["source_title"], "my_book")
        self.assertEqual(obs["meta"]["scope"], "single-book-observation")
        self.assertTrue(obs["meta"]["awaiting_aggregation"])

        analyses = obs["chapter_analyses"]
        self.assertEqual(analyses[0]["chapter"], "1")
        self.assertEqual(analyses[2]["chapter"], "3")

    def test_assemble_commercial_obs_common_mistakes_fallbacks(self):
        # 1. 优先从 opening_analysis.common_mistakes 获取
        pass4_with_oa = {
            "opening_analysis": {
                "common_mistakes": ["开篇对话过多", "主角动机不明"]
            }
        }
        obs1 = assemble.assemble_obs("commercial", "b1", "genre1", pass4_with_oa)
        self.assertEqual(obs1["common_mistakes"], ["开篇对话过多", "主角动机不明"])

        # 2. 从 retention_risk_points 汇总兜底
        pass4_with_risk = {
            "retention_risk_points": [
                {"position": "前3章", "reason": "慢热无爽点"},
                {"chapter": "第10章", "risk": "战力突变"},
                "字符串形式的流失风险说明",
            ]
        }
        obs2 = assemble.assemble_obs("commercial", "b2", "genre2", pass4_with_risk)
        self.assertIn("前3章：慢热无爽点", obs2["common_mistakes"])
        self.assertIn("第10章：战力突变", obs2["common_mistakes"])
        self.assertIn("字符串形式的流失风险说明", obs2["common_mistakes"])


class TestAssembleCraftCard(unittest.TestCase):
    """测试 craft-card 四类格式输入兼容与规范化。"""

    def setUp(self):
        self.manifest = {"selected_indices": [1, 2], "selected_count": 2, "sample_words": 5000}
        self.metrics = {"total_chars": 30000}

    def test_format_1_craft_analysis_direct(self):
        pass5 = {
            "craft_analysis": {
                "foreshadowing": {
                    "techniques": [{"name": "草蛇灰线", "skeleton": "骨架描述"}]
                }
            },
            "craft_summary": {"top_3_strengths": ["草蛇灰线"]}
        }
        card = assemble.assemble_craft_card("b1", "g1", self.manifest, self.metrics, pass5)
        self.assertEqual(card["craft_summary"]["top_3_strengths"], ["草蛇灰线"])
        self.assertIn("foreshadowing", card["craft_analysis"])

    def test_format_2_dimension_keys_direct(self):
        pass5 = {
            "dialogue_craft": [{"name": "潜台词留白", "skeleton": "点到即止"}],
            "tension_building": {"techniques": [{"name": "倒计时压迫"}]},
        }
        card = assemble.assemble_craft_card("b2", "g2", self.manifest, self.metrics, pass5)
        self.assertIn("dialogue_craft", card["craft_analysis"])
        self.assertIn("tension_building", card["craft_analysis"])
        self.assertEqual(card["craft_analysis"]["dialogue_craft"]["techniques"][0]["name"], "潜台词留白")

    def test_format_3_chapter_analysis_decomposition(self):
        pass5 = {
            "chapter_analysis": [
                {
                    "techniques": [
                        {
                            "technique_name": "多重伏笔布局",
                            "abstract_skeleton": "线索暗示",
                            "effect": "引发好奇",
                        },
                        {
                            "name": "陌生未命中技法",
                            "abstract_skeleton": "通用压迫",
                            "effect": "震撼",
                        }
                    ]
                }
            ]
        }
        card = assemble.assemble_craft_card("b3", "g3", self.manifest, self.metrics, pass5)
        # "伏笔" 关键词应命中 foreshadowing 维度
        self.assertTrue(len(card["craft_analysis"]["foreshadowing"]["techniques"]) > 0)
        # 未命中维度应兜底归入 tension_building
        self.assertTrue(len(card["craft_analysis"]["tension_building"]["techniques"]) > 0)
        self.assertIn("多重伏笔布局", card["craft_summary"]["top_3_strengths"])

    def test_format_4_techniques_list(self):
        pass5 = {
            "techniques": [
                {
                    "name": "感官细节通感",
                    "abstract_skeleton": "视觉与听觉交织",
                    "effect": "代入感倍增",
                }
            ]
        }
        card = assemble.assemble_craft_card("b4", "g4", self.manifest, self.metrics, pass5)
        # "感官" 关键词命中 sensory_craft
        self.assertTrue(len(card["craft_analysis"]["sensory_craft"]["techniques"]) > 0)

    def test_technique_name_fallback_from_skeleton(self):
        # 技法缺少 name 时从 abstract_pattern / skeleton 生成
        pass5 = {
            "craft_analysis": {
                "rhythm_control": [
                    {"abstract_pattern": "短句爆发式推进，营造紧迫感。"}
                ]
            }
        }
        card = assemble.assemble_craft_card("b5", "g5", self.manifest, self.metrics, pass5)
        tech = card["craft_analysis"]["rhythm_control"]["techniques"][0]
        self.assertEqual(tech["name"], "短句爆发式推进，营造紧迫感")


class TestSourceFingerprint(unittest.TestCase):
    """测试来源文件内容指纹计算 source_fingerprint。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_assemble_fp_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_source_fingerprint_generation(self):
        p_dir = Path(self.temp_dir)
        (p_dir / "pass2_character.json").write_text('{"p2": 1}', encoding="utf-8")
        (p_dir / "pass3_style.json").write_text('{"p3": 2}', encoding="utf-8")

        fp = assemble.source_fingerprint(p_dir, "voice-card")
        self.assertIn("pass2_character.json", fp)
        self.assertIn("pass3_style.json", fp)
        self.assertEqual(len(fp["pass2_character.json"]), 16)
        self.assertEqual(len(fp["pass3_style.json"]), 16)

        # 缺失文件时不产生该键
        fp_struct = assemble.source_fingerprint(p_dir, "structure-obs")
        self.assertEqual(fp_struct, {})


class TestAssembleCLIWorkflow(unittest.TestCase):
    """测试 assemble.main CLI 的参数校验与内存质检安全防线。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_assemble_cli_")
        self.raw_dir = Path(self.temp_dir) / "corpus" / "raw" / "testbook"
        self.sampled_dir = Path(self.temp_dir) / "corpus" / "sampled" / "testbook"
        self.metrics_dir = Path(self.temp_dir) / "corpus" / "metrics"
        self.assets_dir = Path(self.temp_dir) / "assets"

        self.raw_dir.mkdir(parents=True)
        self.sampled_dir.mkdir(parents=True)
        self.metrics_dir.mkdir(parents=True)
        self.assets_dir.mkdir(parents=True)

        # 写入前置必要文件
        (self.sampled_dir / "manifest.json").write_text('{"sample_words": 1000}', encoding="utf-8")
        (self.metrics_dir / "testbook.json").write_text('{"total_chars": 5000}', encoding="utf-8")
        (self.raw_dir / "pass1_structure.json").write_text('{"structure": {}}', encoding="utf-8")
        (self.raw_dir / "pass2_character.json").write_text('{"characters": []}', encoding="utf-8")
        (self.raw_dir / "pass3_style.json").write_text('{"style": {}}', encoding="utf-8")
        (self.raw_dir / "pass4_commercial.json").write_text('{"commercial": {}}', encoding="utf-8")
        (self.raw_dir / "pass5_craft.json").write_text('{"craft": {}}', encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_missing_manifest_exits(self):
        # 模拟不存在的书名
        with mock.patch("sys.argv", ["assemble.py", "non_existent_book"]), \
             self.assertRaises(SystemExit) as cm:
            assemble.main()
        self.assertIn("缺少采样清单", str(cm.exception))

    def test_validation_failure_prevents_disk_write(self):
        # 预设磁盘上已有旧资产
        old_asset_file = self.assets_dir / "testbook-voice-card.json"
        old_asset_file.write_text('{"old_data": "must_preserve"}', encoding="utf-8")

        # 模拟内存校验失败（返回硬错误）
        with mock.patch("assemble.ROOT", Path(self.temp_dir)), \
             mock.patch("assemble.RAW_DIR", Path(self.temp_dir) / "corpus" / "raw"), \
             mock.patch("assemble.SAMPLED_DIR", Path(self.temp_dir) / "corpus" / "sampled"), \
             mock.patch("assemble.METRICS_DIR", Path(self.temp_dir) / "corpus" / "metrics"), \
             mock.patch("assemble.ASSETS_DIR", self.assets_dir), \
             mock.patch("assemble.validate_mod.validate_asset_data", return_value=(["重大Schema校验错误"], [])), \
             mock.patch("sys.argv", ["assemble.py", "testbook"]), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:

            exit_code = assemble.main()
            self.assertEqual(exit_code, 1)
            self.assertIn("已阻止写盘", mock_out.getvalue())

            # 验证旧资产绝不被覆盖
            self.assertEqual(old_asset_file.read_text(encoding="utf-8"), '{"old_data": "must_preserve"}')

    def test_successful_assembly_and_disk_write(self):
        with mock.patch("assemble.ROOT", Path(self.temp_dir)), \
             mock.patch("assemble.RAW_DIR", Path(self.temp_dir) / "corpus" / "raw"), \
             mock.patch("assemble.SAMPLED_DIR", Path(self.temp_dir) / "corpus" / "sampled"), \
             mock.patch("assemble.METRICS_DIR", Path(self.temp_dir) / "corpus" / "metrics"), \
             mock.patch("assemble.ASSETS_DIR", self.assets_dir), \
             mock.patch("assemble.validate_mod.validate_asset_data", return_value=([], [])), \
             mock.patch("sys.argv", ["assemble.py", "testbook", "--genre", "fantasy"]), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:

            exit_code = assemble.main()
            self.assertEqual(exit_code, 0)  # 成功落盘走完显式返回 0
            self.assertIn("组装完成：四类资产全部通过 schema 校验并已落盘", mock_out.getvalue())

            # 检查4类资产是否真实落盘
            self.assertTrue((self.assets_dir / "testbook-voice-card.json").exists())
            self.assertTrue((self.assets_dir / "testbook-structure-obs.json").exists())
            self.assertTrue((self.assets_dir / "testbook-commercial-obs.json").exists())
            self.assertTrue((self.assets_dir / "testbook-craft-card.json").exists())

            # 检查来源指纹是否注入
            data = json.loads((self.assets_dir / "testbook-voice-card.json").read_text(encoding="utf-8"))
            self.assertIn("source_fingerprint", data["meta"])

    def test_main_with_explicit_argv_and_skip_craft(self):
        with mock.patch("assemble.ROOT", Path(self.temp_dir)), \
             mock.patch("assemble.RAW_DIR", Path(self.temp_dir) / "corpus" / "raw"), \
             mock.patch("assemble.SAMPLED_DIR", Path(self.temp_dir) / "corpus" / "sampled"), \
             mock.patch("assemble.METRICS_DIR", Path(self.temp_dir) / "corpus" / "metrics"), \
             mock.patch("assemble.ASSETS_DIR", self.assets_dir), \
             mock.patch("assemble.validate_mod.validate_asset_data", return_value=([], [])), \
             mock.patch("sys.stdout", new_callable=io.StringIO):

            # 删除已有的 craft-card
            craft_file = self.assets_dir / "testbook-craft-card.json"
            if craft_file.exists():
                craft_file.unlink()

            exit_code = assemble.main(["testbook", "--genre", "fantasy", "--skip-craft"])
            self.assertEqual(exit_code, 0)
            self.assertTrue((self.assets_dir / "testbook-voice-card.json").exists())
            self.assertFalse(craft_file.exists())


class TestBackfillRhythm(unittest.TestCase):
    """narration 数值字段以实测指标为准（2026-10-29 数据断流修复）。

    旧实现把 LLM 输出的 narration 原样透传，pass3 只给定性描述时
    sentence_rhythm 三项恒为 0、paragraph 恒为 {}，8 张内置声线卡全是空壳。
    这些数值 metrics.compute() 本来就算得出来，不该交给 LLM 猜。
    """

    def test_backfills_from_metrics(self):
        narr = {
            "sentence_rhythm": {"avg_length": 0, "short_ratio": 0, "long_ratio": 0,
                                "burst_pattern": "保留我"},
            "paragraph": {},
        }
        metrics = {
            "avg_sentence_len": 22.5, "short_ratio": 0.31, "long_ratio": 0.12,
            "sentence_count": 500, "paragraph_count": 100, "total_chars": 20000,
        }
        out = assemble._backfill_rhythm(narr, metrics)
        sr = out["sentence_rhythm"]
        self.assertEqual(sr["avg_length"], 22.5)
        self.assertEqual(sr["short_ratio"], 0.31)
        self.assertEqual(sr["long_ratio"], 0.12)
        self.assertEqual(sr["burst_pattern"], "保留我", "定性描述不得被覆盖")
        self.assertEqual(out["paragraph"]["avg_lines"], 5.0)

    def test_keeps_original_when_metrics_missing(self):
        """metrics 没算出有效值时不得把原值改成 0（避免"没测"被写成"测出来是 0"）。"""
        narr = {"sentence_rhythm": {"avg_length": 18.0, "burst_pattern": "x"}, "paragraph": {}}
        out = assemble._backfill_rhythm(narr, {})
        self.assertEqual(out["sentence_rhythm"]["avg_length"], 18.0)
        self.assertNotIn("short_ratio", out["sentence_rhythm"])

    def test_tolerates_non_dict_input(self):
        # 空 narration + 有指标 → 应该被填上（有实测值就该用），不是原样返回空
        out = assemble._backfill_rhythm({}, {"avg_sentence_len": 20})
        self.assertEqual(out["sentence_rhythm"]["avg_length"], 20.0)
        # metrics 非 dict 时原样返回，不得抛异常
        self.assertEqual(assemble._backfill_rhythm({"a": 1}, "not-a-dict"), {"a": 1})


if __name__ == "__main__":
    unittest.main()
