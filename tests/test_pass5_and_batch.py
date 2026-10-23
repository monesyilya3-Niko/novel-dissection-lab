#!/usr/bin/env python3
"""Pass5 题材包聚合与全流程批量拆书引擎全维独立测试覆盖（纯标准库 unittest）。

覆盖范围：
1. scripts/pass5_aggregate.py:
   - collect_books: 合成文件过滤、题材匹配与 mismatch 收集、book_names 筛选、obs 结构加载。
   - extract_features: POV、爆发节奏核心词、情绪模式、高频比喻领域、禁忌词抽取与频率测算。
   - summarize_thresholds: 铁律 (>=80%)、建议项 (40-80%)、个人特色 (<40%) 阈值切分与排序。
   - build_prompt: 多书核心特征、跨书一致特征候选与 schema 规则 prompt 组装。
   - main CLI: 题材名正则防御、无书退出、显式指定书目题材不匹配阻断、--dry-run 快速分支、
     verbatim 标记拦截、schema 校验失败拦截、完整聚合写盘与自定义 --out 导出。

2. scripts/batch.py:
   - run_book: 章节过少跳过、dry-run 分支、合规扫描失败拦截、完整拆书入库。
   - generate_reports: 报告渲染写盘与 None 容错。
   - main CLI: 目录不存在拦截、无 TXT 拦截、批量执行与 --report 报告生成。
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

import batch as batch_mod
import pass5_aggregate as p5_mod


class TestPass5AggregateCollectBooks(unittest.TestCase):
    """测试 pass5_aggregate.collect_books 资产发现与过滤机制。"""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.assets_dir = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def test_collect_books_filters_synthetic(self):
        # 合成 voice-card 应该被跳过
        (self.assets_dir / "synthetic_test-voice-card.json").write_text(
            json.dumps({"meta": {"genre": "urban"}}, ensure_ascii=False),
            encoding="utf-8",
        )
        with mock.patch.object(p5_mod, "ASSETS", self.assets_dir):
            books, mismatches = p5_mod.collect_books("urban", None)
        self.assertEqual(books, [])
        self.assertEqual(mismatches, [])

    def test_collect_books_mismatches_and_match(self):
        (self.assets_dir / "book1-voice-card.json").write_text(
            json.dumps({"meta": {"genre": "urban"}}, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.assets_dir / "book2-voice-card.json").write_text(
            json.dumps({"meta": {"genre": "xianxia"}}, ensure_ascii=False),
            encoding="utf-8",
        )
        with mock.patch.object(p5_mod, "ASSETS", self.assets_dir):
            books, mismatches = p5_mod.collect_books("urban", None)

        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]["name"], "book1")
        self.assertEqual(mismatches, [("book2", "xianxia")])

    def test_collect_books_with_book_names_filter(self):
        (self.assets_dir / "book1-voice-card.json").write_text(
            json.dumps({"meta": {"genre": "urban"}}, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.assets_dir / "book2-voice-card.json").write_text(
            json.dumps({"meta": {"genre": "urban"}}, ensure_ascii=False),
            encoding="utf-8",
        )
        with mock.patch.object(p5_mod, "ASSETS", self.assets_dir):
            books, mismatches = p5_mod.collect_books("urban", ["book1"])

        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]["name"], "book1")
        self.assertEqual(mismatches, [])

    def test_collect_books_loads_structure_and_commercial_obs(self):
        (self.assets_dir / "book1-voice-card.json").write_text(
            json.dumps({"meta": {"genre": "urban"}}, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.assets_dir / "book1-structure-obs.json").write_text(
            json.dumps({"chapter_word_range": {"min": 1000, "typical": 2000, "max": 3000}}, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.assets_dir / "book1-commercial-obs.json").write_text(
            json.dumps({"payoff_density": {"per_thousand_words": 1.5}}, ensure_ascii=False),
            encoding="utf-8",
        )
        with mock.patch.object(p5_mod, "ASSETS", self.assets_dir):
            books, mismatches = p5_mod.collect_books("urban", None)

        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]["struct"].get("chapter_word_range", {}).get("typical"), 2000)
        self.assertEqual(books[0]["comm"].get("payoff_density", {}).get("per_thousand_words"), 1.5)


class TestPass5AggregateFeatureExtraction(unittest.TestCase):
    """测试 pass5_aggregate.extract_features 与 summarize_thresholds 算法。"""

    def test_extract_features_and_rates(self):
        b1 = {
            "name": "b1",
            "voice": {
                "narration": {
                    "pov": "第一人称",
                    "sentence_rhythm": {"burst_pattern": "对话 / 交锋 / 短句"},
                },
                "emotion_handling": {"mode": "动作外化"},
                "imagery": {"high_freq_metaphor_domains": ["钢铁（冰冷机械）", "寒冬冷冽"]},
                "banned": {"never_used_words": ["蓦然", "仿佛", "宛如", "多余的词"]},
            },
        }
        b2 = {
            "name": "b2",
            "voice": {
                "narration": {
                    "pov": "第一人称",
                    "sentence_rhythm": {"burst_pattern": "内心 / 交锋 / 震动"},
                },
                "emotion_handling": {"mode": "微表情"},
                "imagery": {"high_freq_metaphor_domains": ["钢铁"]},
                "banned": {"never_used_words": ["蓦然", "绝不"]},
            },
        }
        rates = p5_mod.extract_features([b1, b2])

        # pov:第一人称 两本书都有 -> 1.0
        self.assertEqual(rates.get("pov:第一人称"), 1.0)
        # burst:对话 只有 b1 -> 0.5; burst:交锋 两本都有 -> 1.0
        self.assertEqual(rates.get("burst:对话"), 0.5)
        self.assertEqual(rates.get("burst:交锋"), 1.0)
        # emotion_mode:动作外化 -> 0.5; emotion_mode:微表情 -> 0.5
        self.assertEqual(rates.get("emotion_mode:动作外化"), 0.5)
        self.assertEqual(rates.get("emotion_mode:微表情"), 0.5)
        # metaphor:钢铁 经正则清洗后两本都有 -> 1.0
        self.assertEqual(rates.get("metaphor:钢铁"), 1.0)
        # avoid:蓦然 两本都有 -> 1.0
        self.assertEqual(rates.get("avoid:蓦然"), 1.0)
        # 禁忌词只取前 3 个: "多余的词" 不应存在
        self.assertNotIn("avoid:多余的词", rates)

    def test_summarize_thresholds(self):
        feature_rates = {
            "feat_iron_1": 1.0,
            "feat_iron_2": 0.8,
            "feat_suggest_1": 0.79,
            "feat_suggest_2": 0.4,
            "feat_personal_1": 0.39,
            "feat_personal_2": 0.1,
        }
        thresholds = p5_mod.summarize_thresholds(feature_rates)
        self.assertEqual(thresholds["iron"], ["feat_iron_1", "feat_iron_2"])
        self.assertEqual(thresholds["suggest"], ["feat_suggest_1", "feat_suggest_2"])
        self.assertEqual(thresholds["personal"], ["feat_personal_1", "feat_personal_2"])


class TestPass5AggregatePrompt(unittest.TestCase):
    """测试 build_prompt 提示词组装。"""

    def test_build_prompt_content(self):
        books = [
            {
                "name": "测试作品",
                "voice": {
                    "meta": {"genre": "test-genre"},
                    "narration": {"pov": "第三人称", "sentence_rhythm": {"burst_pattern": "对决交锋"}},
                    "emotion_handling": {"mode": "神态动作", "examples": [{"pattern": "紧握双拳"}]},
                    "banned": {"never_used_words": ["突然", "立刻"]},
                },
                "comm": {"payoff_density": {"per_thousand_words": 1.2}},
            }
        ]
        thresholds = {
            "iron": ["pov:第三人称"],
            "suggest": ["metaphor:雷霆"],
            "personal": ["burst:对决"],
        }
        prompt = p5_mod.build_prompt(books, thresholds)
        self.assertIn("测试作品", prompt)
        self.assertIn("test-genre", prompt)
        self.assertIn("pov:第三人称", prompt)
        self.assertIn("metaphor:雷霆", prompt)
        self.assertIn("burst:对决", prompt)
        self.assertIn("【硬性约束】", prompt)


class TestPass5AggregateMainCLI(unittest.TestCase):
    """测试 pass5_aggregate.main CLI 命令行分支与防线。"""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.assets_dir = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def test_main_invalid_genre_name_fails(self):
        test_argv = ["pass5_aggregate.py", "--genre", "bad genre!@#"]
        with mock.patch("sys.argv", test_argv), \
             mock.patch.object(p5_mod, "ASSETS", self.assets_dir):
            with self.assertRaises(SystemExit) as cm:
                p5_mod.main()
            self.assertIn("未找到", str(cm.exception))

    def test_main_no_books_found_exits(self):
        test_argv = ["pass5_aggregate.py", "--genre", "campus-redemption"]
        with mock.patch("sys.argv", test_argv), \
             mock.patch.object(p5_mod, "ASSETS", self.assets_dir):
            with self.assertRaises(SystemExit) as cm:
                p5_mod.main()
            self.assertIn("未找到 campus-redemption 题材的 voice-card", str(cm.exception))

    def test_main_specified_books_mismatch_exits(self):
        (self.assets_dir / "book1-voice-card.json").write_text(
            json.dumps({"meta": {"genre": "xianxia"}}, ensure_ascii=False),
            encoding="utf-8",
        )
        test_argv = ["pass5_aggregate.py", "--genre", "urban", "--books", "book1"]
        with mock.patch("sys.argv", test_argv), \
             mock.patch.object(p5_mod, "ASSETS", self.assets_dir):
            with self.assertRaises(SystemExit) as cm:
                p5_mod.main()
            self.assertIn("题材隔离违规", str(cm.exception))

    def test_main_dry_run_success(self):
        (self.assets_dir / "book1-voice-card.json").write_text(
            json.dumps({"meta": {"genre": "urban"}, "narration": {"pov": "第三人称"}}, ensure_ascii=False),
            encoding="utf-8",
        )
        test_argv = ["pass5_aggregate.py", "--genre", "urban", "--dry-run"]
        with mock.patch("sys.argv", test_argv), \
             mock.patch.object(p5_mod, "ASSETS", self.assets_dir), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as fake_out:
            code = p5_mod.main()
            self.assertEqual(code, 0)
            output = fake_out.getvalue()
            self.assertIn("[dry-run] 跳过 LLM 聚合", output)
            self.assertIn("聚合样本: 1 本", output)

    def test_main_with_explicit_argv(self):
        (self.assets_dir / "explicit_book-voice-card.json").write_text(
            json.dumps({"meta": {"genre": "urban"}}, ensure_ascii=False),
            encoding="utf-8",
        )
        with mock.patch.object(p5_mod, "ASSETS", self.assets_dir), \
             mock.patch("sys.stdout", new_callable=io.StringIO):
            code = p5_mod.main(["--genre", "urban", "--dry-run"])
            self.assertEqual(code, 0)

    def test_main_verbatim_rejection(self):
        (self.assets_dir / "book1-voice-card.json").write_text(
            json.dumps({"meta": {"genre": "urban"}}, ensure_ascii=False),
            encoding="utf-8",
        )
        test_argv = ["pass5_aggregate.py", "--genre", "urban"]
        mock_llm_res = {
            "text": json.dumps({"contains_verbatim": True, "meta": {"genre": "urban"}}),
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "elapsed": 1.2,
        }
        with mock.patch("sys.argv", test_argv), \
             mock.patch.object(p5_mod, "ASSETS", self.assets_dir), \
             mock.patch("pass5_aggregate.llm_client.chat", return_value=mock_llm_res):
            with self.assertRaises(SystemExit) as cm:
                p5_mod.main()
            self.assertIn("未入库", str(cm.exception))

    def test_main_schema_validation_failure_exits(self):
        (self.assets_dir / "book1-voice-card.json").write_text(
            json.dumps({"meta": {"genre": "urban"}}, ensure_ascii=False),
            encoding="utf-8",
        )
        test_argv = ["pass5_aggregate.py", "--genre", "urban"]
        mock_llm_res = {
            "text": json.dumps({"incomplete": "schema"}),
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "elapsed": 0.5,
        }
        with mock.patch("sys.argv", test_argv), \
             mock.patch.object(p5_mod, "ASSETS", self.assets_dir), \
             mock.patch("pass5_aggregate.llm_client.chat", return_value=mock_llm_res):
            with self.assertRaises(SystemExit) as cm:
                p5_mod.main()
            self.assertIn("题材包不符合 schema，未入库", str(cm.exception))

    def test_main_full_success_writes_pack(self):
        (self.assets_dir / "book1-voice-card.json").write_text(
            json.dumps({"meta": {"genre": "urban"}}, ensure_ascii=False),
            encoding="utf-8",
        )
        valid_pack = {
            "meta": {
                "id": "genre-urban",
                "name": "都市都市",
                "source_books": [
                    {"title": "书1", "platform": "番茄", "voice_card_ref": "b1"},
                    {"title": "书2", "platform": "番茄", "voice_card_ref": "b2"},
                    {"title": "书3", "platform": "番茄", "voice_card_ref": "b3"},
                ],
                "confidence": 0.85,
            },
            "structure": {
                "chapter_roles": [{"role": "铺垫"}],
                "hook_system": {"hook_types": [{"type": "悬念揭示"}]},
            },
            "commercial": {
                "payoff_density": {
                    "per_thousand_words": 1.2,
                    "payoff_types": [{"type": "打脸", "buildup_length": 500, "skeleton": "测试骨架"}],
                },
                "opening_analysis": {
                    "chapter_1": {"hook_position": 100, "first_300_words_task": "立住悬念"}
                },
            },
            "language_rules": {
                "iron_rules": [{"rule": "短句递进", "bad_example": "长难句堆砌", "good_example": "短句推进"}]
            },
        }
        out_file = self.assets_dir / "custom-genre-pack.json"
        test_argv = ["pass5_aggregate.py", "--genre", "urban", "--out", str(out_file)]
        mock_llm_res = {
            "text": json.dumps(valid_pack, ensure_ascii=False),
            "prompt_tokens": 150,
            "completion_tokens": 80,
            "elapsed": 1.1,
        }
        with mock.patch("sys.argv", test_argv), \
             mock.patch.object(p5_mod, "ASSETS", self.assets_dir), \
             mock.patch("pass5_aggregate.llm_client.chat", return_value=mock_llm_res):
            p5_mod.main()

        self.assertTrue(out_file.is_file())
        saved = json.loads(out_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["meta"]["id"], "genre-urban")
        self.assertEqual(len(saved["language_rules"]["iron_rules"]), 1)


class TestBatchEngine(unittest.TestCase):
    """测试 batch.py 批量拆书引擎全流程。"""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def _make_book(self, filename: str, chapters: int = 6) -> Path:
        book_path = self.root_dir / filename
        parts = []
        for i in range(1, chapters + 1):
            parts.append(f"第{i}章 标题{i}\n" + ("正文内容。" * 200) + "\n")
        book_path.write_text("\n".join(parts), encoding="utf-8")
        return book_path

    def test_run_book_too_few_chapters_skipped(self):
        src = self._make_book("short.txt", chapters=3)
        with mock.patch.object(batch_mod, "ROOT", self.root_dir):
            res = batch_mod.run_book(src, "urban", None, dry_run=False)
        self.assertIsNone(res)

    def test_run_book_dry_run_success(self):
        src = self._make_book("novel1.txt", chapters=6)
        with mock.patch.object(batch_mod, "ROOT", self.root_dir):
            res = batch_mod.run_book(src, "urban", None, dry_run=True)
        self.assertIsNone(res)
        # 验证 manifest 和 metrics 写入
        manifest_file = self.root_dir / "corpus" / "sampled" / "novel1" / "manifest.json"
        self.assertTrue(manifest_file.is_file())
        metrics_file = self.root_dir / "corpus" / "metrics" / "novel1.json"
        self.assertTrue(metrics_file.is_file())

    def test_run_book_compliance_failure_returns_none(self):
        src = self._make_book("novel2.txt", chapters=6)
        mock_pass1 = {"chapter_word_range": {"min": 1000, "typical": 2000, "max": 3000}}
        mock_pass2 = {"voices": [{"name": "主角", "archetype": "坚定", "speech_traits": ["短句"]}]}
        mock_pass3 = {
            "narration": {"pov": "第三人称", "sentence_rhythm": {"avg_len": 15}},
            "dialogue": {"avg_len": 10},
            "emotion_handling": {"mode": "神态动作"},
            "imagery": {},
            "banned": {"never_used_words": []},
        }
        mock_pass4 = {"payoff_density": {"per_thousand_words": 1.0}}

        def fake_run_pass(kind, *args, **kwargs):
            mapping = {
                "pass1_structure": mock_pass1,
                "pass2_character": mock_pass2,
                "pass3_style": mock_pass3,
                "pass4_commercial": mock_pass4,
            }
            return mapping[kind]

        with mock.patch.object(batch_mod, "ROOT", self.root_dir), \
             mock.patch("batch.pipeline.run_pass", side_effect=fake_run_pass), \
             mock.patch("batch.compliance_mod.scan_asset", return_value=(["REJECT: 原文抄袭"], [])):
            res = batch_mod.run_book(src, "urban", None, dry_run=False)

        self.assertIsNone(res)

    def test_run_book_full_success(self):
        src = self._make_book("novel3.txt", chapters=6)
        mock_pass1 = {"chapter_word_range": {"min": 1000, "typical": 2000, "max": 3000}}
        mock_pass2 = {"voices": [{"name": "主角", "archetype": "坚定", "speech_traits": ["短句"]}]}
        mock_pass3 = {
            "narration": {"pov": "第三人称", "sentence_rhythm": {"avg_len": 15}},
            "dialogue": {"avg_len": 10},
            "emotion_handling": {"mode": "神态动作"},
            "imagery": {},
            "banned": {"never_used_words": []},
        }
        mock_pass4 = {"payoff_density": {"per_thousand_words": 1.0}}

        def fake_run_pass(kind, *args, **kwargs):
            mapping = {
                "pass1_structure": mock_pass1,
                "pass2_character": mock_pass2,
                "pass3_style": mock_pass3,
                "pass4_commercial": mock_pass4,
            }
            return mapping[kind]

        with mock.patch.object(batch_mod, "ROOT", self.root_dir), \
             mock.patch("batch.pipeline.run_pass", side_effect=fake_run_pass), \
             mock.patch("batch.compliance_mod.scan_asset", return_value=([], [])):
            res = batch_mod.run_book(src, "urban", None, dry_run=False)

        self.assertIsNotNone(res)
        self.assertEqual(res["name"], "novel3")
        self.assertIn("voice", res)
        self.assertIn("structure", res)
        self.assertIn("commercial", res)
        # 验证 assets 文件存在
        vc_file = self.root_dir / "assets" / "novel3-voice-card.json"
        self.assertTrue(vc_file.is_file())

    def test_generate_reports_writes_files(self):
        out_dir = self.root_dir / "reports"
        results = [
            {
                "name": "book_a",
                "voice": {"meta": {"name": "book_a"}},
                "structure": {},
                "commercial": {},
            },
            None,
        ]
        with mock.patch("report.build_report", return_value="# 拆书报告\n内容"):
            batch_mod.generate_reports(results, out_dir)

        report_file = out_dir / "book_a-拆书报告.md"
        self.assertTrue(report_file.is_file())
        self.assertIn("拆书报告", report_file.read_text(encoding="utf-8"))

    def test_main_cli_nonexistent_and_empty_corpus(self):
        # 1. 目录不存在
        with mock.patch("sys.argv", ["batch.py", str(self.root_dir / "missing"), "--genre", "urban"]):
            with self.assertRaises(SystemExit) as cm:
                batch_mod.main()
            self.assertIn("目录不存在", str(cm.exception))

        # 2. 目录中没有 TXT
        empty_dir = self.root_dir / "empty_corpus"
        empty_dir.mkdir()
        with mock.patch("sys.argv", ["batch.py", str(empty_dir), "--genre", "urban"]):
            with self.assertRaises(SystemExit) as cm:
                batch_mod.main()
            self.assertIn("目录中没有 TXT", str(cm.exception))

    def test_main_cli_success_with_report(self):
        corpus_dir = self.root_dir / "corpus_txt"
        corpus_dir.mkdir()
        book1 = corpus_dir / "book1.txt"
        book1.write_text("第1章\n" + "正文" * 500, encoding="utf-8")

        mock_res = {"name": "book1", "voice": {}, "structure": {}, "commercial": {}}
        test_argv = ["batch.py", str(corpus_dir), "--genre", "urban", "--report"]

        with mock.patch("sys.argv", test_argv), \
             mock.patch.object(batch_mod, "ROOT", self.root_dir), \
             mock.patch("batch.run_book", return_value=mock_res), \
             mock.patch("batch.generate_reports") as mock_gen_rep, \
             mock.patch("sys.stdout", new_callable=io.StringIO) as fake_out:
            batch_mod.main()
            output = fake_out.getvalue()
            self.assertIn("发现 1 本 TXT", output)
            self.assertIn("完成: 成功 1 / 1 本", output)
            mock_gen_rep.assert_called_once()


if __name__ == "__main__":
    unittest.main()
