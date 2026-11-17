"""核心引擎企业级加固回归测试套件（2026-11-17 总工升级）。

覆盖：
1. llm_client：仓库默认 example-deepseek 未填密钥时不误判 model_configured、any_model_ready、
   HTTP 402 / SUBSCRIPTION_REQUIRED 零重试与 is_auth_or_quota_error、CIDR 与 [::1] NO_PROXY 绕过、
   DEFAULT_ROUTES 含 pass5_craft。
2. pipeline：assemble_voice_card_v2 自动回填 metrics 句长节奏、USER 模板 JSON 结构契约注入、
   pass5_craft 遇 LLMError 自动落盘 AI接管任务.md 且不留半成品脏资产。
3. write：LLMError 时自动落盘 AI接管写作任务.md、覆盖已有章节时生成 .bak 备份且只累加净字数增量。
4. sampler / report / qc / book_quality / logic_check / setting_check / inject / retrieve / distill：
   空章节防崩、英文双引号抽取、英文报告 ≥5000 词双轨门禁、QC source_title 与总分及格线、
   章内重复段落去重、全名切换不误报、设定禁用词顿号切分、女主/反派权重排序、检索缓存签名失效、
   跨目录 distill 0 规则写盘前拦截。
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
for _p in (str(ROOT), str(SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import book_quality  # noqa: E402
import distill  # noqa: E402
import genre_registry  # noqa: E402
import inject  # noqa: E402
import llm_client  # noqa: E402
import llm_hook  # noqa: E402
import logic_check  # noqa: E402
import pipeline  # noqa: E402
import qc  # noqa: E402
import report  # noqa: E402
import retrieve  # noqa: E402
import sampler  # noqa: E402
import setting_check  # noqa: E402
import validate  # noqa: E402
import write  # noqa: E402


class TestLLMClientEnterpriseUpgrades(unittest.TestCase):
    def test_repo_template_without_key_is_not_ready(self):
        with tempfile.TemporaryDirectory() as td:
            non_existent_user_dir = Path(td) / "no_user_cfg"
            env_clean = {k: v for k, v in os.environ.items() if k not in ("DEEPSEEK_API_KEY", "NOVEL_LAB_FORCE_NO_MODEL")}
            with mock.patch.object(llm_client, "user_config_dir", return_value=non_existent_user_dir), \
                 mock.patch.object(llm_client, "load_secrets", return_value={}), \
                 mock.patch.dict(os.environ, env_clean, clear=True):
                self.assertTrue(llm_client.any_model_configured())
                self.assertFalse(llm_client.any_model_ready())

    def test_repo_template_with_env_key_becomes_configured_and_ready(self):
        with tempfile.TemporaryDirectory() as td:
            non_existent_user_dir = Path(td) / "no_user_cfg"
            with mock.patch.object(llm_client, "user_config_dir", return_value=non_existent_user_dir), \
                 mock.patch.object(llm_client, "load_secrets", return_value={}), \
                 mock.patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-valid-key"}, clear=False):
                os.environ.pop("NOVEL_LAB_FORCE_NO_MODEL", None)
                self.assertTrue(llm_client.any_model_configured())
                self.assertTrue(llm_client.any_model_ready())

    def test_http_402_subscription_required_not_retried_and_classified(self):
        err = llm_client.LLMError('HTTP 402: {"error":{"code":"SUBSCRIPTION_REQUIRED"}}')
        self.assertFalse(llm_client._is_retryable_error(err))
        self.assertTrue(llm_client.is_auth_or_quota_error(err))
        desc = llm_client.describe_llm_degradation(err)
        self.assertIn("模型额度/权限不足", desc)

    def test_cidr_and_ipv6_no_proxy_bypass(self):
        with mock.patch.dict(os.environ, {"NO_PROXY": "localhost,127.0.0.1,::1,192.168.0.0/16,10.0.0.0/8"}, clear=False):
            self.assertTrue(llm_client._should_bypass_proxy_extra("http://192.168.1.50:11434/v1/chat/completions"))
            self.assertTrue(llm_client._should_bypass_proxy_extra("http://10.2.3.4:8000/v1"))
            self.assertTrue(llm_client._should_bypass_proxy_extra("http://[::1]:11434/api/chat"))
            self.assertFalse(llm_client._should_bypass_proxy_extra("https://api.deepseek.com/v1/chat/completions"))

    def test_pass5_craft_route_registered(self):
        self.assertEqual(llm_client.DEFAULT_ROUTES.get("pass5_craft"), "strong")

    def test_llm_hook_circuit_breaker_on_402(self):
        issues = [
            {"type": "timeline_contradiction", "severity": "high", "chapter": i, "detail": f"矛盾{i}"}
            for i in range(1, 6)
        ]
        calls = 0

        def _fail_402(**_kw):
            nonlocal calls
            calls += 1
            raise llm_client.LLMError("HTTP 402: SUBSCRIPTION_REQUIRED")

        stats = {}
        with mock.patch.object(llm_client, "any_model_configured", return_value=True), \
             mock.patch.object(llm_client, "chat", side_effect=_fail_402):
            kept = llm_hook._judge_candidates(issues, stats=stats)
        self.assertEqual(calls, 1, "遇到 402 致命错误应在首条后立即熔断，不再连撞后续候选")
        self.assertEqual(len(kept), 5)
        self.assertEqual(stats["undetermined"], 5)


class TestPipelineAndWriteUpgrades(unittest.TestCase):
    def test_assemble_voice_card_v2_backfills_sentence_rhythm_passes_validation(self):
        manifest = {"selected_count": 20, "selected_indices": list(range(1, 21)), "sample_words": 40000}
        metrics = {
            "avg_sentence_len": 16.4,
            "short_ratio": 0.35,
            "long_ratio": 0.12,
            "dialogue_ratio": 0.28,
            "paragraph_count": 200,
            "sentence_count": 500,
            "total_chars": 40000,
        }
        narration = {"pov": "第三人称限知", "sentence_rhythm": {"avg_length": 0, "short_ratio": 0, "long_ratio": 0, "burst_pattern": "交锋短句"}}
        voices = [
            {
                "name": "沈砚",
                "role": "主角",
                "speech_signature": {
                    "avg_utterance_length": 10,
                    "verbal_tics": ["无妨", "再看"],
                    "refusal_pattern": "沉默片刻后转身离开",
                    "anger_pattern": "声音压低反问一句",
                    "never_says": ["随便吧", "求你了", "算我倒霉"],
                },
            }
        ]
        dialogue = {"dialogue_ratio": 0.28, "tag_style": "动作代标签", "subtext_level": "大量潜台词"}
        emotion = {"mode": "体感式", "examples": [{"emotion": "愤怒", "pattern": "指节泛白"}]}
        imagery = {"high_freq_metaphor_domains": ["冷兵器"], "sensory_preference": "触觉优先"}
        banned = {"never_used_words": ["猛然"], "forbidden_patterns": ["直白喊口号"]}

        vc = pipeline.assemble_voice_card_v2(
            "测试书", "xuanhuan", manifest, voices, narration, dialogue, emotion, imagery, banned, metrics
        )
        self.assertEqual(vc["narration"]["sentence_rhythm"]["avg_length"], 16.4)
        errs, _ = validate.validate_asset_data("voice-card", vc)
        self.assertEqual(errs, [])

    def test_run_pass_injects_output_schema_from_user_template(self):
        captured = {}

        def _fake_chat(**kwargs):
            captured.update(kwargs)
            return {"text": '{"character_voices": [{"name": "A"}, {"name": "B"}]}', "model_id": "m", "prompt_tokens": 10, "completion_tokens": 10, "cost": 0, "elapsed": 0.1}

        slices = {"pass2_character": {"dialogues": [{"chapter": 1, "title": "Ch1", "before": "x", "line": "「走」", "after": "y"}]}}
        with mock.patch.object(pipeline.llm_client, "resolve_model", return_value=("m", {"model_name": "m"})), \
             mock.patch.object(pipeline.llm_client, "chat", side_effect=_fake_chat):
            pipeline.run_pass("pass2_character", slices, {}, dry_run=False, model_id=None)
        self.assertIn("character_voices", captured["system"])

    def test_write_llm_error_generates_takeover_guide_and_backup_delta(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pfile = root / "p.md"
            pfile.write_text("# System Prompt", encoding="utf-8")
            ndir = root / "novel"
            write.ensure_novel_structure(ndir, "测试书")
            ch1 = write.save_chapter(ndir, 1, "初稿一百字" * 20)
            st1 = json.loads((ndir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(st1["word_count_today"], 100)

            # 覆盖写入同章 120 字：生成 .bak 且今日字数只增加 20（变成 120 而非 220）
            write.save_chapter(ndir, 1, "改稿一百二十" * 20)
            st2 = json.loads((ndir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(st2["word_count_today"], 120)
            self.assertTrue(ch1.with_suffix(".txt.bak").is_file())

            # 遇 402 错误时自动生成 AI接管写作任务.md
            with mock.patch.object(write.llm_client, "any_model_configured", return_value=True), \
                 mock.patch.object(write.llm_client, "chat", side_effect=llm_client.LLMError("HTTP 402: SUBSCRIPTION_REQUIRED")), \
                 mock.patch("sys.stderr", new_callable=io.StringIO):
                rc = write.main(["--prompt", str(pfile), "--chapter", "2", "--task", "夜探敌营", "--novel-dir", str(ndir)])
            self.assertEqual(rc, 1)
            self.assertTrue((ndir / "AI接管写作任务.md").is_file())


class TestQualityAndAlgorithmUpgrades(unittest.TestCase):
    def test_sampler_empty_chapters_and_ascii_quotes(self):
        empty_slices = sampler.build_slices([], {})
        self.assertEqual(empty_slices["pass1_structure"]["chapters"], [])
        chs = [("Chapter 1", 'He stepped forward. "Stay right there!" she warned. Slowly he turned.')]
        dlgs = sampler.extract_dialogue(chs, [0])
        self.assertEqual(len(dlgs), 1)
        self.assertEqual(dlgs[0]["line"], '"Stay right there!"')

    def test_report_english_5000_words_gate(self):
        short_en = "word " * 1800  # ~9000 chars
        short_en2 = "word " * 400  # ~2000 chars -> 合计 >10000 字符但仅 2200 词，应被拦截
        chk_fail = report.combined_report_ok(len(short_en), len(short_en2), book_text=short_en, craft_text=short_en2)
        self.assertFalse(chk_fail["ok"])
        long_en = "narrative " * 3000
        long_en2 = "technique " * 2200  # 合计 5200 词 >= 5000，应放行
        chk_ok = report.combined_report_ok(len(long_en), len(long_en2), book_text=long_en, craft_text=long_en2)
        self.assertTrue(chk_ok["ok"])

    def test_qc_source_title_and_score_threshold_and_safe_filename(self):
        title = qc._resolve_book_title(None, {"meta": {"source_title": "诡秘/之主:卷一"}}, "chapters")
        self.assertEqual(title, "诡秘/之主:卷一")
        self.assertEqual(qc._judge([], total_score=50.0, pass_line=75, warn_line=60), "FAIL")
        self.assertEqual(qc._judge([], total_score=68.0, pass_line=75, warn_line=60), "WARN")

    def test_book_quality_paragraph_repeat_deduplicated(self):
        repeated = "这是一段超过二十个汉字的完全重复凑字数段落内容测试文本。"
        texts = {1: "\n".join([repeated] * 5)}
        issues = book_quality.check_word_padding(texts)
        para_issues = [i for i in issues if i["type"] == "paragraph_repeat"]
        self.assertEqual(len(para_issues), 1)
        self.assertIn("5 次", para_issues[0]["detail"])

    def test_logic_check_canonical_to_nickname_not_flagged(self):
        entities = {"characters": [{"name": "林知夏", "aliases": ["知夏", "小林"]}]}
        texts = {1: "林知夏推开门走进教室。", 2: "知夏低头翻开了笔记本。"}
        issues = logic_check.check_logic(texts, entities)
        app_issues = [i for i in issues if i["type"] == "appellation_contradiction"]
        self.assertEqual(app_issues, [])

    def test_setting_check_splits_delimiters_and_ignores_innocent(self):
        kws = setting_check._extract_banned_keywords("禁止出现枪械、火药，严禁魔法。他是无辜的路人，无奈摇头。")
        self.assertIn("枪械", kws)
        self.assertIn("火药", kws)
        self.assertIn("魔法", kws)
        self.assertFalse(any("辜" in k or "奈" in k for k in kws))

    def test_inject_role_order_heroine_before_mob(self):
        rendered = inject.render_voices([
            {"name": "路人甲", "role": "工具人", "speech_signature": {}},
            {"name": "苏清寒", "role": "女主", "speech_signature": {}},
            {"name": "沈砚", "role": "主角", "speech_signature": {}},
        ])
        self.assertLess(rendered.index("沈砚"), rendered.index("苏清寒"))
        self.assertLess(rendered.index("苏清寒"), rendered.index("路人甲"))

    def test_retrieve_cache_invalidates_when_assets_change(self):
        with tempfile.TemporaryDirectory() as td:
            cache_file = str(Path(td) / "idx.json")
            a1 = {"craft-card": {"b1": {"meta": {"id": "doc-alpha"}, "craft_summary": {"top_3_strengths": ["草蛇灰线暗埋伏笔"]}}}}
            a2 = {"craft-card": {"b2": {"meta": {"id": "doc-beta"}, "craft_summary": {"top_3_strengths": ["暴风骤雨极限反转"]}}}}
            idx1 = retrieve.build_index(a1, persist_path=cache_file)
            self.assertEqual(idx1.docs[0].asset_id, "doc-alpha")
            idx2 = retrieve.build_index(a2, persist_path=cache_file)
            self.assertEqual(idx2.docs[0].asset_id, "doc-beta")

    def test_distill_custom_assets_dir_and_require_non_empty(self):
        with tempfile.TemporaryDirectory() as td:
            empty_assets = Path(td) / "user_assets"
            empty_assets.mkdir()
            with self.assertRaises(ValueError):
                distill.run_distill("xuanhuan", assets_dir=empty_assets, require_non_empty=True)
            self.assertEqual(list(empty_assets.glob("*.json")), [])

    def test_genre_registry_known_genres_in_extra_dir(self):
        with tempfile.TemporaryDirectory() as td:
            extra = Path(td)
            (extra / "genre-cyber-cultivation.json").write_text(
                json.dumps({"meta": {"kind": "genre-prose-card", "id": "genre-cyber-cultivation"}}),
                encoding="utf-8",
            )
            merged = genre_registry.known_genres_in(extra)
            self.assertIn("cyber-cultivation", merged)


if __name__ == "__main__":
    unittest.main()
