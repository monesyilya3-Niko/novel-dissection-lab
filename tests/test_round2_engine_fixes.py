#!/usr/bin/env python3
"""Round-2 Engine Fixes 全维回归测试套件（纯 Python 标准库，零第三方依赖）。

覆盖 P0-1 ~ P2-3 全部引擎层修复：
1. chapter_loader & assemble：中文数词章号解析、辅助文件名排除、__all__ 导出、带卷名前缀章号提取
2. novel.py：cmd_status 动态模型配置解析与畸形 JSON 防御、分析 --from-assets 与失败降级提示
3. assemble / pipeline / normalize：craft-card 保留 deep_analysis 与非截断类型容错、角色枚举全映射
4. clean_verbatim / compliance / assemble：成对引号与英文缩写防误判、12字边界与长引用滑窗清洗、顶层合规字段
5. consistency / validate / state_tracker / chapter_check / report_craft / secret_store 健壮性加固
"""
from __future__ import annotations

import contextlib
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import assemble  # noqa: E402
import chapter_check  # noqa: E402
import chapter_loader  # noqa: E402
import clean_verbatim  # noqa: E402
import compliance  # noqa: E402
import consistency  # noqa: E402
import normalize  # noqa: E402
import pipeline  # noqa: E402
import report_craft  # noqa: E402
import secret_store  # noqa: E402
import state_tracker  # noqa: E402
import validate  # noqa: E402

import novel  # noqa: E402


class TestP01ChineseNumeralAndExclusions(unittest.TestCase):
    """[P0-1] 中文数词章号解析、裸数字前缀辅助稿件排除与 __all__ 导出。"""

    def test_parse_cn_int_arabic_and_chinese(self):
        cases = {
            "0": 0,
            "007": 7,
            "128": 128,
            "零": 0,
            "〇": 0,
            "一": 1,
            "两": 2,
            "十": 10,
            "十二": 12,
            "二十": 20,
            "一百零一": 101,
            "一百十四": 114,
            "两百五十六": 256,
            "一千零八": 1008,
            "一千零一十": 1010,
            "一零八": 108,
            "一万零八": 10008,
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(chapter_loader._parse_cn_int(raw), expected)

        for bad in ("", "   ", None, "十十", "百", "10一", "abc"):
            with self.subTest(bad=bad):
                self.assertIsNone(chapter_loader._parse_cn_int(bad))  # type: ignore[arg-type]

    def test_chinese_chapter_filenames_and_aux_stem_exclusions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "第1章 开端.txt").write_text("第一章正文", encoding="utf-8")
            (root / "第一百零一章 转折.md").write_text("第101章正文", encoding="utf-8")
            (root / "第两百五十六回 终局.txt").write_text("第256章正文", encoding="utf-8")
            # 裸数字前缀辅助文件不得与 第1章 撞号
            for aux in (
                "01_番外.txt",
                "01_设定.md",
                "01-楔子.txt",
                "01.序章.txt",
                "01 大纲.md",
                "01_前言.txt",
                "01_后记.txt",
            ):
                (root / aux).write_text("辅助内容", encoding="utf-8")

            loaded = chapter_loader.load_chapter_texts(root)
            self.assertEqual(sorted(loaded.keys()), [1, 101, 256])

            # 显式写了「第N章」的标题不受裸数字前缀排除影响
            self.assertEqual(chapter_loader._chapter_number(Path("第2章_序章回顾.txt")), 2)

    def test_chapter_loader_all_exports(self):
        self.assertIn("read_text_file", chapter_loader.__all__)
        self.assertIn("is_chapter_filename", chapter_loader.__all__)
        self.assertTrue(chapter_loader.is_chapter_filename("第一百零一章.md"))
        self.assertFalse(chapter_loader.is_chapter_filename("01_设定.md"))

    def test_assemble_parse_chapter_no_with_volume_prefix_and_cn_numerals(self):
        self.assertEqual(assemble._parse_chapter_no("卷一 第101章 风起"), 101)
        self.assertEqual(assemble._parse_chapter_no("第一百零一章 破阵"), 101)
        self.assertEqual(assemble._parse_chapter_no("第二卷 第两百五十六回 夜战"), 256)

        obs = assemble.assemble_obs(
            "structure",
            "demo",
            "xuanhuan",
            {
                "chapter_analyses": [
                    {"title": "卷一 第101章 风起", "role": "推进"},
                    {"title": "第一百零二章 破阵", "role": "爆发"},
                ]
            },
        )
        self.assertEqual(obs["chapter_analyses"][0]["chapter"], "101")
        self.assertEqual(obs["chapter_analyses"][1]["chapter"], "102")


class TestP02CliOfflineAndStatusResilience(unittest.TestCase):
    """[P0-2][P2-2][P2-3] novel.py 状态健壮性与 分析 --from-assets 离线交付。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="r2_novel_"))
        self._orig_root = novel.ROOT
        novel.ROOT = self.tmp
        for sub in ("assets", "reports", "novel", "config", "corpus"):
            (self.tmp / sub).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        novel.ROOT = self._orig_root
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cmd_status_malformed_json_and_null_fields_do_not_crash(self):
        # 1. JSON 顶层为 list
        (self.tmp / "assets" / "list_bad-voice-card.json").write_text("[]", encoding="utf-8")
        # 2. meta / dialogue 为 null
        (self.tmp / "assets" / "null_fields-voice-card.json").write_text(
            '{"meta": null, "dialogue": null}', encoding="utf-8"
        )
        # 3. UTF-8 BOM 正常卡
        (self.tmp / "assets" / "bom_ok-voice-card.json").write_text(
            '{"meta": {"genre": "xuanhuan", "confidence": 0.85}, "dialogue": {"character_voices": []}}',
            encoding="utf-8-sig",
        )
        # 4. state.json 顶层为 null
        proj = self.tmp / "novel" / "bad_proj"
        proj.mkdir()
        (proj / "state.json").write_text("null", encoding="utf-8")

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = novel.cmd_status()
        out = buf.getvalue()
        self.assertEqual(rc, 1)
        self.assertIn("list_bad-voice-card.json: （损坏，跳过）", out)
        self.assertIn("null_fields-voice-card.json: （损坏，跳过）", out)
        self.assertIn("bom_ok: xuanhuan | 置信 85%", out)
        self.assertIn("bad_proj: （损坏，跳过）", out)

    def test_cmd_status_uses_resolve_models_file_and_any_model_ready(self):
        custom_models = self.tmp / "user_models.json"
        custom_models.write_text(
            json.dumps({"models": {"my-ds": {"model_name": "deepseek-chat"}}}),
            encoding="utf-8-sig",
        )
        buf = io.StringIO()
        with mock.patch("llm_client.resolve_models_file", return_value=custom_models), \
             mock.patch("llm_client.any_model_ready", return_value=False), \
             contextlib.redirect_stdout(buf):
            rc = novel.cmd_status()
        self.assertEqual(rc, 0)
        self.assertIn("my-ds", buf.getvalue())
        self.assertIn("未就绪", buf.getvalue())

    def test_analyze_pipeline_failure_prints_from_assets_hint(self):
        book = self.tmp / "corpus" / "demo_book.txt"
        book.write_text("第一章 正文", encoding="utf-8")
        (self.tmp / "assets" / "demo_book-voice-card.json").write_text("{}", encoding="utf-8")

        buf = io.StringIO()
        with mock.patch.object(sys, "argv", ["novel", "分析", str(book), "--genre", "xuanhuan"]), \
             mock.patch.object(novel, "run_script", return_value=1), \
             contextlib.redirect_stdout(buf):
            rc = novel.main()
        self.assertEqual(rc, 1)
        self.assertIn("--from-assets", buf.getvalue())

    def test_analyze_from_assets_skips_pipeline_and_publishes_reports(self):
        vc = self.tmp / "assets" / "offline_book-voice-card.json"
        cc = self.tmp / "assets" / "offline_book-craft-card.json"
        vc.write_text('{"meta":{"source_title":"offline_book","genre":"xuanhuan"}}', encoding="utf-8")
        cc.write_text('{"meta":{"source_title":"offline_book","genre":"xuanhuan"}}', encoding="utf-8")

        def fake_run_script(script_name: str, script_args: list):
            if script_name == "pipeline.py":
                raise AssertionError("--from-assets 不得调用 pipeline.py")
            out_idx = script_args.index("--out") + 1
            Path(script_args[out_idx]).write_text("报" * 6000, encoding="utf-8")
            return 0

        buf = io.StringIO()
        with mock.patch.object(
            sys, "argv", ["novel", "分析", "offline_book", "--genre", "xuanhuan", "--from-assets"]
        ), mock.patch.object(novel, "run_script", side_effect=fake_run_script), \
             contextlib.redirect_stdout(buf):
            rc = novel.main()
        self.assertEqual(rc, 0)
        self.assertTrue((self.tmp / "reports" / "offline_book-拆书报告.md").is_file())
        self.assertTrue((self.tmp / "reports" / "offline_book-笔法分析.md").is_file())


class TestP03P04CraftDeepAnalysisAndRoleEnum(unittest.TestCase):
    """[P0-3][P0-4] craft-card 保留 deep_analysis 与非截断容错、normalize 角色枚举映射。"""

    def test_assemble_craft_card_preserves_deep_analysis_and_long_fields(self):
        manifest = {"selected_indices": [1, 2, 3], "selected_count": 3, "sample_words": 9000}
        metrics = {"total_chars": 30000}
        long_desc = "深" * 320
        da_payload = {"reader_psychology": "制造悬念闭合冲动", "execution_steps": "三步递进"}

        # 格式 A：维度直接为 list（此前会丢失 deep_analysis）
        p5_list_dim = {
            "craft_analysis": {
                "foreshadowing": [
                    {
                        "name": "草蛇灰线",
                        "description": long_desc,
                        "effect": ["层层递进", "后劲绵长"],
                        "skeleton": 12345,
                        "deep_analysis": da_payload,
                    }
                ]
            }
        }
        card_a = assemble.assemble_craft_card("b", "xuanhuan", manifest, metrics, p5_list_dim)
        tech_a = card_a["craft_analysis"]["foreshadowing"]["techniques"][0]
        self.assertEqual(tech_a["deep_analysis"], da_payload)
        self.assertEqual(len(tech_a["description"]), 320)
        self.assertEqual(tech_a["skeleton"], "12345")
        self.assertIn("层层递进", tech_a["effect"])

        # 格式 B：chapter_analysis（此前 [:200] 截断且丢 deep_analysis）
        p5_ch = {
            "chapter_analysis": [
                None,
                {
                    "techniques": [
                        None,
                        {
                            "name": "伏笔暗扣",
                            "example_in_text": long_desc,
                            "abstract_skeleton": long_desc,
                            "effect": long_desc,
                            "counter_example": long_desc,
                            "deep_analysis": da_payload,
                        },
                    ]
                },
            ]
        }
        card_b = pipeline.assemble_craft_card("b", "xuanhuan", manifest, metrics, p5_ch)
        tech_b = card_b["craft_analysis"]["foreshadowing"]["techniques"][0]
        self.assertEqual(tech_b["deep_analysis"], da_payload)
        self.assertEqual(len(tech_b["description"]), 320)
        self.assertEqual(len(tech_b["skeleton"]), 320)

        # 格式 C：craft_analysis 为 null 不崩溃
        card_null = assemble.assemble_craft_card(
            "b", "xuanhuan", manifest, metrics, {"craft_analysis": None, "craft_summary": None}
        )
        self.assertEqual(card_null["craft_analysis"], {})

    def test_normalize_role_for_maps_all_variants_into_role_enum(self):
        mapping = {
            "男主": "主角",
            "男主角": "主角",
            "主人公": "主角",
            "第一主角": "主角",
            "女主角": "女主",
            "女配": "配角",
            "男配": "配角",
            "女配角": "配角",
            "男配角": "配角",
            "次要角色": "配角",
            "大反派": "反派",
            "反派BOSS": "反派",
            "师父": "导师",
            "引路人": "导师",
            "路人甲乙": "配角",
        }
        for raw_role, expected in mapping.items():
            with self.subTest(raw_role=raw_role):
                got = normalize._role_for("某人", {}, position=2, explicit_role=raw_role)
                self.assertEqual(got, expected)
                self.assertIn(got, validate.ROLE_ENUM)

        # 显式 item["role"] = "男主" 在数组与 characters 列表中均不得绕过 _role_for
        voices = normalize.normalize_pass2(
            {
                "characters": [
                    {"name": "萧炎", "role": "男主"},
                    {"name": "薰儿", "身份": "女主角"},
                    {"name": "药老", "role": "师父"},
                    {"name": "魂天帝", "role": "反派BOSS"},
                ]
            }
        )
        by_name = {v["name"]: v["role"] for v in voices}
        self.assertEqual(by_name, {"萧炎": "主角", "薰儿": "女主", "药老": "导师", "魂天帝": "反派"})
        for v in voices:
            self.assertIn(v["role"], validate.ROLE_ENUM)


class TestP05VerbatimAndCompliance(unittest.TestCase):
    """[P0-5] 成对引号与英文缩写防误判、12字精确清洗、>40字长引文清洗、顶层合规检查。"""

    def test_english_contractions_not_paired_as_quotes(self):
        en = "He didn't know why she couldn't stay in the castle when they wouldn't listen."
        self.assertEqual(compliance.find_quoted_fragments(en), [])
        ngram = compliance.build_ngram_index(en)
        # 英文缩写不应被 clean_string 当成单引号片段误删周围文本（仅测引号剥离本身）
        non_matching_ngram = compliance.build_ngram_index("完全无关的另一段中文语料十二个字以上测试")
        cleaned, changed = clean_verbatim.clean_string(en, non_matching_ngram, "desc")
        self.assertFalse(changed)
        self.assertEqual(cleaned, en)
        _ = ngram

    def test_clean_verbatim_exact_12_chars_and_over_40_chars_and_mid_window(self):
        book = "苍穹之上雷霆万钧劈碎了整座古老石殿，少年握紧断剑一步步走出废墟直面漫天诸神与无尽狂风骤雨。"
        ngram = compliance.build_ngram_index(book)

        # 1. 恰好 12 字匹配原文（修复旧版 >12 off-by-one）
        exact_12 = "苍穹之上雷霆万钧劈碎了整"
        self.assertEqual(len(exact_12), 12)
        c1, ch1 = clean_verbatim.clean_string(f"此处台词“{exact_12}”极具冲击力。", ngram, "p")
        self.assertTrue(ch1)
        self.assertNotIn(exact_12, c1)

        # 2. >40 字长引号原文（修复旧版 {1,40} 上限漏洗）
        long_quote = book
        self.assertGreater(len(long_quote), 40)
        c2, ch2 = clean_verbatim.clean_string(f"长段引用：「{long_quote}」结束。", ngram, "p")
        self.assertTrue(ch2)
        self.assertNotIn("苍穹之上雷霆万钧", c2)

        # 3. 引号前部改写、中部命中 12-gram（滑窗检测）
        mid_quote = "前缀修饰词组：" + exact_12
        c3, ch3 = clean_verbatim.clean_string(f"描述『{mid_quote}』收尾。", ngram, "p")
        self.assertTrue(ch3)
        self.assertNotIn(exact_12, c3)

    def test_compliance_top_level_special_fields(self):
        ngram = compliance.build_ngram_index("这是一段用于测试顶层标题豁免的十二字原文内容")
        errs, _ = compliance.scan_asset(
            {
                "abstraction_level": "verbal",
                "contains_verbatim": True,
                "title": "这是一段用于测试顶层标题豁免的十二字原文内容",
            },
            ngram,
        )
        self.assertEqual(len(errs), 2)
        self.assertTrue(any("abstraction_level='verbal'" in e for e in errs))
        self.assertTrue(any("contains_verbatim=true" in e for e in errs))

    def test_assemble_cleans_craft_card_with_md_corpus(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            raw_dir = base / "corpus" / "raw" / "mdbook"
            sampled_dir = base / "corpus" / "sampled" / "mdbook"
            metrics_dir = base / "corpus" / "metrics"
            assets_dir = base / "assets"
            for d in (raw_dir, sampled_dir, metrics_dir, assets_dir):
                d.mkdir(parents=True, exist_ok=True)

            verbatim = "星河倒悬于九天孤峰之上映照万古长夜"
            (base / "corpus" / "mdbook.md").write_text(f"# 第1章\n{verbatim}。\n", encoding="utf-8")
            (sampled_dir / "manifest.json").write_text(
                '{"selected_indices":[1,2,3],"selected_count":3,"sample_words":3000}',
                encoding="utf-8",
            )
            (metrics_dir / "mdbook.json").write_text('{"total_chars":9000}', encoding="utf-8")
            (raw_dir / "pass1_structure.json").write_text("{}", encoding="utf-8")
            (raw_dir / "pass2_character.json").write_text("{}", encoding="utf-8")
            (raw_dir / "pass3_style.json").write_text("{}", encoding="utf-8")
            (raw_dir / "pass4_commercial.json").write_text("{}", encoding="utf-8")
            (raw_dir / "pass5_craft.json").write_text(
                json.dumps(
                    {
                        "craft_analysis": {
                            "foreshadowing": [
                                {"name": "星河伏笔", "description": f"开篇写「{verbatim}」埋下暗线"}
                            ]
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with mock.patch.object(assemble, "ROOT", base), \
                 mock.patch.object(assemble, "RAW_DIR", base / "corpus" / "raw"), \
                 mock.patch.object(assemble, "SAMPLED_DIR", base / "corpus" / "sampled"), \
                 mock.patch.object(assemble, "METRICS_DIR", metrics_dir), \
                 mock.patch.object(assemble, "ASSETS_DIR", assets_dir), \
                 mock.patch.object(assemble.validate_mod, "validate_asset_data", return_value=([], [])), \
                 contextlib.redirect_stdout(io.StringIO()):
                rc = assemble.main(["mdbook", "--genre", "xuanhuan"])
            self.assertEqual(rc, 0)
            saved_cc = json.loads((assets_dir / "mdbook-craft-card.json").read_text(encoding="utf-8"))
            desc = saved_cc["craft_analysis"]["foreshadowing"]["techniques"][0]["description"]
            self.assertNotIn(verbatim, desc)


class TestP1ValidatorsTrackersCheckersAndSecrets(unittest.TestCase):
    """[P1-1]..[P2-3] consistency / validate / state_tracker / chapter_check / report_craft / secret_store。"""

    def test_consistency_single_sentence_punct_cjk_prefix_dialogue_pov_and_null_guards(self):
        # 1. 带句末标点的单句成段计数（章节标题与多句同段不计）
        ch_text = "\n".join(
            [
                "第1章 夜雨",
                "风起了。",
                "雨落了！",
                "是谁在敲门？",
                "没有人回答……",
                "门缓缓关上了。",
                "第一句很短。第二句也很短。",
            ]
        )
        n_score, n_details = consistency.check_narration(ch_text, {"pov": "第三人称"})
        self.assertTrue(any("单句成段 5 段 ✓(+5)" in d for d in n_details), n_details)
        self.assertGreaterEqual(n_score, 5)

        # 2. 对白内的「我」不得让第三人称正文误通过第一人称 POV 检查
        third_with_quote = "他推开窗户，冷冷说道：“我是绝对不会答应你们的！”"
        pov_score, pov_details = consistency.check_narration(third_with_quote, {"pov": "第一人称"})
        self.assertTrue(any("视角第一人称 ✗(+0)" in d for d in pov_details), pov_details)
        self.assertEqual(pov_score, 0)

        # 3. 英文角色名不得按前 2 字母前缀误匹配英文单词
        v_score, _ = consistency.check_voices(
            "All soldiers stood in silence.", [{"name": "Alice", "speech_signature": {"verbal_tics": ["hi"]}}]
        )
        self.assertEqual(v_score, 0.0)

        # 4. voice_card 各子块为 null 时不崩溃
        total, _, _ = consistency.score_text(
            {"dialogue": None, "emotion_handling": None, "narration": None, "banned_words": None, "imagery": None},
            "他心跳加速。",
        )
        self.assertIsInstance(total, (int, float))

    def test_validate_non_dict_nan_techniques_and_10_dims(self):
        self.assertEqual(validate.auto_kind([]), "voice-card")  # type: ignore[arg-type]
        self.assertEqual(validate.auto_kind(None), "voice-card")  # type: ignore[arg-type]
        self.assertFalse(validate.is_num(float("nan")))
        self.assertFalse(validate.is_num(float("inf")))

        errs, warns = validate.validate_asset_data(
            "craft-card",
            {
                "meta": {
                    "source_title": "t",
                    "genre": "xuanhuan",
                    "extracted_at": "2026-11-18",
                    "sample_chapters": [1, 2, 3],
                    "confidence": 0.8,
                },
                "craft_analysis": {"foreshadowing": {"techniques": "not-a-list"}},
                "craft_summary": {
                    "top_3_strengths": ["a"],
                    "unique_techniques": ["b"],
                    "reusable_patterns": ["c"],
                },
            },
        )
        self.assertTrue(any("techniques 应为数组" in e for e in errs), errs)
        self.assertTrue(any("/10 维" in w for w in warns), warns)

    def test_state_tracker_partial_upsert_bool_rejection_and_init_snapshot_check(self):
        state = state_tracker._empty_state("测试")
        # init 模式活跃角色无快照必须报 ValueError
        with self.assertRaises(ValueError):
            state_tracker.apply_transaction(
                state,
                {"mode": "init", "context": {"active_character_names": ["无快照角色"]}},
            )

        # bool 伪装 int 必须拒绝
        with self.assertRaises(ValueError):
            state_tracker.apply_transaction(state, {"mode": "init", "chapter": True})

        # None 字段必须报 ValueError 而非 AttributeError/TypeError
        for bad_tx in (
            {"mode": "init", "character_snapshots": None},
            {"mode": "init", "context": None},
            {"mode": "init", "delta": None},
            {"mode": "init", "delta": {"retired_characters": None}},
        ):
            with self.subTest(bad_tx=bad_tx), self.assertRaises(ValueError):
                state_tracker.apply_transaction(state, bad_tx)

        # 正常 init + 部分字段 upsert 合并且剥离 action
        s1 = state_tracker.apply_transaction(
            state,
            {
                "mode": "init",
                "chapter": 1,
                "character_snapshots": {"林动": {"identity": "少年"}},
                "context": {"active_character_names": ["林动"]},
                "foreshadow": [{"id": "FS-1", "summary": "石符秘密", "status": "未触发"}],
            },
        )
        with self.assertRaises(ValueError):
            state_tracker.apply_transaction(
                s1,
                {"mode": "append", "expected_state_revision": True, "delta": {}},
            )
        with self.assertRaises(ValueError):
            state_tracker.apply_transaction(
                s1,
                {
                    "mode": "append",
                    "expected_state_revision": 1,
                    "delta": {"foreshadow_changes": [{"id": "", "status": "进行中"}]},
                },
            )
        s2 = state_tracker.apply_transaction(
            s1,
            {
                "mode": "append",
                "chapter": 2,
                "expected_state_revision": 1,
                "delta": {
                    "foreshadow_changes": [{"id": "FS-1", "action": "upsert", "status": "已回收"}],
                    "timeline_events": [{"id": "EV-1", "action": "upsert", "event": "青阳镇大比"}],
                },
            },
        )
        self.assertEqual(s2["foreshadow"][0]["summary"], "石符秘密")
        self.assertEqual(s2["foreshadow"][0]["status"], "已回收")
        self.assertNotIn("action", s2["foreshadow"][0])
        self.assertNotIn("action", s2["timeline_events"][0])

    def test_chapter_check_improvements(self):
        # 1. 纯对白含标点不得超 100%，纯英文不报「无文本」
        _, d_pure = chapter_check.check_dialogue_ratio("「你好？！」")
        self.assertIn("100.0%", d_pure)
        s_en, d_en = chapter_check.check_dialogue_ratio('He whispered, "Stay back!" and drew his sword in the dark.')
        self.assertNotEqual(d_en, "无文本")
        self.assertGreater(s_en, 0)

        # 2. 闭合引号章末钩子、英文单问号不重复计分、跨句「门…开了」不误判、trunc=1 含截断风险
        _, h_trunc = chapter_check.check_hook("忽然风停了，他转身望向走廊尽头还没说完的话")
        self.assertIn("截断风险", h_trunc)
        _, h_quote_close = chapter_check.check_hook("他压低嗓音提醒道：“小心身后！”")
        self.assertIn("closed=1", h_quote_close)
        self.assertIn("hits=1", h_quote_close)
        _, h_en_q = chapter_check.check_hook("Calm ordinary sentence ending with a question?")
        self.assertIn("hits=1", h_en_q)
        _, h_far_door = chapter_check.check_hook("门口停着一辆旧单车。傍晚时分她终于想开了。")
        self.assertIn("hits=1", h_far_door)

        # 3. 直角引号对话开场 + 男性代词对称 AI 味与情绪标签 + 低分维度进 issues
        op_score, op_detail = chapter_check.check_opening("「快走，别回头！」他在教室里抓起背包冲了出去。")
        self.assertIn("对话开场", op_detail)
        self.assertGreaterEqual(op_score, 6)

        ai_score, ai_detail = chapter_check.check_ai_tics(
            "他不知道，今天踏出的这一步将会彻底改写所有人的结局。他深吸一口气，望着远方完全不知道前路。"
        )
        self.assertEqual(ai_score, 2)
        self.assertIn("作者预告旁白", ai_detail)
        self.assertIn("深呼吸+不知道模板", ai_detail)

        et_score, _ = chapter_check.check_emotion_tags("他不禁感到一阵寒意，他内心无比挣扎。")
        self.assertLess(et_score, 7)

        res = chapter_check.chapter_check("平淡无奇的几句短叙述。")
        self.assertGreater(len(res["issues"]), 2)

    def test_report_craft_null_guards_and_float_formatting(self):
        md = report_craft.render_craft_report(
            {
                "meta": {
                    "source_title": "容错书",
                    "confidence": None,
                    "sample_chapters": None,
                    "total_sample_words": None,
                },
                "craft_summary": None,
                "craft_analysis": {
                    "foreshadowing": {
                        "techniques": [
                            "非字典条目忽略",
                            {"name": "伏笔一", "deep_analysis": "非字典深度字段忽略"},
                        ],
                        "buried_payoff_ratio": 0.75,
                        "note": 3.5,
                    },
                    "pov_control": "非字典维度忽略",
                },
            }
        )
        self.assertIn("## 8 维技法深度拆解", md)
        self.assertIn("- **伏笔回收率**：75%", md)
        self.assertIn("- **备注**：3.5", md)
        self.assertNotIn("350%", md)

    def test_secret_store_no_mkdir_on_load_and_corrupt_backup(self):
        with tempfile.TemporaryDirectory() as td:
            missing_dir = Path(td) / "nonexistent_cfg"
            self.assertEqual(secret_store.load_secrets(missing_dir), {})
            self.assertFalse(missing_dir.exists(), "load_secrets 不得创建不存在的目录")

            if secret_store._is_windows():
                cfg_dir = Path(td) / "win_cfg"
                cfg_dir.mkdir()
                bin_file = cfg_dir / ".secrets.bin"
                bin_file.write_bytes(b"corrupted-dpapi-bytes")

                err_buf = io.StringIO()
                with contextlib.redirect_stderr(err_buf):
                    self.assertEqual(secret_store.load_secrets(cfg_dir), {})
                self.assertIn("警告", err_buf.getvalue())

                err_buf2 = io.StringIO()
                with contextlib.redirect_stderr(err_buf2):
                    secret_store.save_secrets({"k": "v"}, cfg_dir)
                bak_file = cfg_dir / ".secrets.bin.corrupt.bak"
                self.assertTrue(bak_file.is_file())
                self.assertEqual(bak_file.read_bytes(), b"corrupted-dpapi-bytes")
                self.assertEqual(secret_store.load_secrets(cfg_dir), {"k": "v"})


if __name__ == "__main__":
    unittest.main()
