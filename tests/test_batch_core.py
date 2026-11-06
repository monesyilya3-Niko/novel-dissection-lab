#!/usr/bin/env python3
"""
batch.py 批量拆书编排全维独立测试套件 — 纯标准库 unittest，零第三方依赖

覆盖范围：
1. run_book:
   - 文件不存在保护
   - 章节过少 (<5) 保护与跳过
   - dry_run 分支（采样、量化、写入 manifest 与 slices，不调外部组装）
   - 完整非 dry_run 拆解流（采样、量化、四遍扫描组装、Schema 校验、合规检查与资产落盘）
   - 合规扫描失败拦截（REJECT 错误发生时放弃并返回 None）
2. generate_reports:
   - 包含 None / 非字典等脏数据容错
   - 正常结果渲染与报告 Markdown 文件写盘
3. main CLI:
   - 目录不存在拦截（返回 1）
   - 目录下无 TXT 文本拦截（返回 1）
   - 正常批量 dry-run 处理（返回 0）
   - 带有 --report 生成报告流程（返回 0）
"""

import io
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

import batch as batch_mod  # noqa: E402


def _make_book_txt(path: Path, chapters: int = 8, words_per_chapter: int = 100):
    parts = []
    for i in range(1, chapters + 1):
        parts.append(f"第{i}章 标题{i}\n" + ("正文内容。" * words_per_chapter) + "\n")
    path.write_text("\n".join(parts), encoding="utf-8")


class TestRunBook(unittest.TestCase):
    """测试 run_book 核心调度逻辑。"""

    def test_run_book_nonexistent_file(self):
        res = batch_mod.run_book(Path("nonexistent_book.txt"), "urban")
        self.assertIsNone(res)

    def test_run_book_str_path(self):
        res = batch_mod.run_book("nonexistent_book.txt", "urban")
        self.assertIsNone(res)

    def test_run_book_too_few_chapters(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "short.txt"
            _make_book_txt(p, chapters=3)
            res = batch_mod.run_book(p, "urban")
            self.assertIsNone(res)

    def test_run_book_dry_run_success(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            book_path = td / "book1.txt"
            _make_book_txt(book_path, chapters=6)
            with mock.patch.object(batch_mod, "ROOT", td):
                res = batch_mod.run_book(book_path, "urban", model_id=None, dry_run=True)
            self.assertIsNone(res)
            manifest = td / "corpus" / "sampled" / "book1" / "manifest.json"
            slices = td / "corpus" / "sampled" / "book1" / "slices.json"
            metrics = td / "corpus" / "metrics" / "book1.json"
            self.assertTrue(manifest.is_file())
            self.assertTrue(slices.is_file())
            self.assertTrue(metrics.is_file())

    def test_run_book_full_success(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            book_path = td / "book_full.txt"
            _make_book_txt(book_path, chapters=6)

            mock_passes = {
                "pass1_structure": {"climax": "c1"},
                "pass2_character": {"voices": [{"name": "张三", "speech_signature": "清冷"}]},
                "pass3_style": {
                    "narration": {"pov": "第三人称", "sentence_rhythm": {}},
                    "dialogue": {"subtext_level": "含蓄"},
                    "emotion": {"mode": "克制"},
                    "imagery": {"devices": []},
                    "banned": {"never_used": []},
                },
                "pass4_commercial": {"skeleton": "三段式"},
            }

            def fake_run_pass(kind, slices, m, dry_run, model_id):
                return mock_passes[kind]

            with mock.patch.object(batch_mod, "ROOT", td), \
                 mock.patch.object(batch_mod.pipeline, "run_pass", side_effect=fake_run_pass), \
                 mock.patch.dict(batch_mod.validate_mod.DISPATCH, {"voice-card": lambda obj: None}), \
                 mock.patch.object(batch_mod.compliance_mod, "scan_asset", return_value=([], [])):
                res = batch_mod.run_book(book_path, "urban", model_id=None, dry_run=False)

            self.assertIsNotNone(res)
            self.assertEqual(res["name"], "book_full")
            self.assertIn("voice", res)
            self.assertIn("structure", res)
            self.assertIn("commercial", res)

            # 验证资产写入 assets
            self.assertTrue((td / "assets" / "book_full-voice-card.json").is_file())
            self.assertTrue((td / "assets" / "book_full-structure-obs.json").is_file())
            self.assertTrue((td / "assets" / "book_full-commercial-obs.json").is_file())

    def test_run_book_compliance_failure(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            book_path = td / "book_fail.txt"
            _make_book_txt(book_path, chapters=6)

            mock_passes = {
                "pass1_structure": {},
                "pass2_character": {},
                "pass3_style": {},
                "pass4_commercial": {},
            }

            with mock.patch.object(batch_mod, "ROOT", td), \
                 mock.patch.object(batch_mod.pipeline, "run_pass", return_value={}), \
                 mock.patch.dict(batch_mod.validate_mod.DISPATCH, {"voice-card": lambda obj: None}), \
                 mock.patch.object(batch_mod.compliance_mod, "scan_asset", return_value=(["REJECT: 原文抄袭"], [])):
                res = batch_mod.run_book(book_path, "urban", model_id=None, dry_run=False)

            self.assertIsNone(res)


class TestGenerateReports(unittest.TestCase):
    """测试 generate_reports 报告批量生成。"""

    def test_generate_reports_with_empty_and_valid(self):
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "reports"
            results = [
                None,
                "not a dict",
                {
                    "name": "book1",
                    "voice": {"meta": {"book": "book1"}},
                    "structure": {"meta": {"book": "book1"}},
                    "commercial": {"meta": {"book": "book1"}},
                },
            ]
            with mock.patch("scripts.report.build_report", return_value="# 报告内容"):
                batch_mod.generate_reports(results, out_dir)

            report_file = out_dir / "book1-拆书报告.md"
            self.assertTrue(report_file.is_file())
            self.assertEqual(report_file.read_text(encoding="utf-8"), "# 报告内容")


class TestMainCLI(unittest.TestCase):
    """测试 main(argv) 命令行入口分发。"""

    def test_main_nonexistent_corpus_dir(self):
        with self.assertRaises(SystemExit) as cm:
            batch_mod.main(["nonexistent_dir", "--genre", "urban"])
        self.assertIn("目录不存在", str(cm.exception))

    def test_main_empty_corpus_dir(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(SystemExit) as cm:
                batch_mod.main([td, "--genre", "urban"])
            self.assertIn("目录中没有正文文件", str(cm.exception))

    def test_main_dry_run_success(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            corpus_dir = td / "corpus"
            corpus_dir.mkdir()
            _make_book_txt(corpus_dir / "b1.txt", chapters=6)
            _make_book_txt(corpus_dir / "b2.txt", chapters=6)

            buf = io.StringIO()
            with mock.patch("sys.stdout", buf), \
                 mock.patch.object(batch_mod, "ROOT", td):
                code = batch_mod.main([str(corpus_dir), "--genre", "urban", "--dry-run"])

            self.assertEqual(code, 0)
            out = buf.getvalue()
            self.assertIn("发现 2 本正文:", out)
            self.assertIn("完成: 成功 0 / 2 本", out)  # dry-run 产物在 run_book 返回 None

    def test_main_with_reports(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            corpus_dir = td / "corpus"
            corpus_dir.mkdir()
            _make_book_txt(corpus_dir / "b1.txt", chapters=6)

            fake_result = {
                "name": "b1",
                "voice": {"meta": {"book": "b1"}},
                "structure": {"meta": {"book": "b1"}},
                "commercial": {"meta": {"book": "b1"}},
            }

            with mock.patch.object(batch_mod, "ROOT", td), \
                 mock.patch.object(batch_mod, "run_book", return_value=fake_result), \
                 mock.patch("scripts.report.build_report", return_value="# 报告"):
                code = batch_mod.main([str(corpus_dir), "--genre", "urban", "--report"])

            self.assertEqual(code, 0)
            report_file = td / "reports" / "b1-拆书报告.md"
            self.assertTrue(report_file.is_file())


if __name__ == "__main__":
    unittest.main()
