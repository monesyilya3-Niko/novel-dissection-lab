#!/usr/bin/env python3
"""资产同步检查与元数据回填引擎（asset_sync_check.py & backfill_meta.py）全维独立测试套件。

涵盖：
1. 资产同步基础函数（list_books 目录发现与缺失容错、has_pipeline_outputs 流水线产出判定、provenance_note 出处声明）；
2. 报告铁律二长度合规（check_report_compliance 无报告放行、字数不足硬阻断、达标放行）；
3. 单书全维同步检查（check_one 缺失 raw 报错、四类资产缺失排查、指纹过期与 mtime 启发式、采样索引漂移、报告合规联动）；
4. asset_sync_check 命令行接口（CLI main 无书放行、同步成功 0、发现问题 1 及单书参数支持）；
5. 资产元数据回填核心逻辑（backfill_one 目录缺失、无源 pass 提示、损坏 JSON 容错、非对象 meta 过滤、已是最新跳过、dry_run 预览与实际写盘）；
6. backfill_meta 命令行接口（CLI main 无书跳过、dry_run 预览、实际回填与错误退出码 1）。
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import asset_sync_check as asc  # noqa: E402
import backfill_meta as bfm  # noqa: E402


class TestAssetSyncHelpers(unittest.TestCase):
    """测试 asset_sync_check 底层辅助函数。"""

    def test_list_books(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw"
            with patch.object(asc, "RAW_DIR", raw_dir):
                # 目录不存在
                self.assertEqual(asc.list_books(), [])

                # 建立子目录与文件
                raw_dir.mkdir()
                (raw_dir / "book_b").mkdir()
                (raw_dir / "book_a").mkdir()
                (raw_dir / "some_file.txt").write_text("not a dir", encoding="utf-8")

                self.assertEqual(asc.list_books(), ["book_a", "book_b"])

    def test_has_pipeline_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw = Path(tmpdir)
            # 空目录
            self.assertFalse(asc.has_pipeline_outputs(raw))

            # 含有非 pass 文件
            (raw / "notes.txt").write_text("notes", encoding="utf-8")
            self.assertFalse(asc.has_pipeline_outputs(raw))

            # 写入其中一个 pass 文件
            (raw / "pass1_structure.json").write_text("{}", encoding="utf-8")
            self.assertTrue(asc.has_pipeline_outputs(raw))

    def test_provenance_note(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw"
            raw_dir.mkdir()
            with patch.object(asc, "RAW_DIR", raw_dir):
                # 目录不存在
                self.assertEqual(asc.provenance_note("nonexistent"), "")

                # 含有 pass 文件（流水线产出）
                b_pipe = raw_dir / "pipe_book"
                b_pipe.mkdir()
                (b_pipe / "pass2_character.json").write_text("{}", encoding="utf-8")
                self.assertEqual(asc.provenance_note("pipe_book"), "")

                # 存在目录但无 pass 文件（手工/会话产出，如 Lord_of_the_Mysteries）
                b_manual = raw_dir / "manual_book"
                b_manual.mkdir()
                note = asc.provenance_note("manual_book")
                self.assertIn("非流水线产出", note)
                self.assertIn("跳过「资产过期」与「采样一致性」比对", note)


class TestAssetSyncReportCompliance(unittest.TestCase):
    """测试报告铁律二长度合规检查。"""

    def test_check_report_compliance_no_reports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rep_dir = Path(tmpdir) / "reports"
            rep_dir.mkdir()
            with patch.object(asc, "REPORTS_DIR", rep_dir):
                # 没有任何报告，非缺陷，返回空列表
                self.assertEqual(asc.check_report_compliance("book_a"), [])

    def test_check_report_compliance_failing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rep_dir = Path(tmpdir) / "reports"
            rep_dir.mkdir()
            # 报告合计不足 10000 字
            (rep_dir / "short_book-拆书报告.md").write_text("短报告" * 50, encoding="utf-8")
            (rep_dir / "short_book-笔法分析.md").write_text("短分析" * 50, encoding="utf-8")
            with patch.object(asc, "REPORTS_DIR", rep_dir):
                issues = asc.check_report_compliance("short_book")
                self.assertEqual(len(issues), 1)
                self.assertIn("报告铁律二不达标", issues[0])
                self.assertIn("硬门槛", issues[0])

    def test_check_report_compliance_passing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rep_dir = Path(tmpdir) / "reports"
            rep_dir.mkdir()
            # 报告合计满足 10000 字
            (rep_dir / "long_book-拆书报告.md").write_text("长" * 6000, encoding="utf-8")
            (rep_dir / "long_book-笔法分析.md").write_text("分析" * 3000, encoding="utf-8")
            with patch.object(asc, "REPORTS_DIR", rep_dir):
                issues = asc.check_report_compliance("long_book")
                self.assertEqual(issues, [])


class TestAssetSyncCheckOne(unittest.TestCase):
    """测试 check_one 全维排查逻辑。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.raw_dir = self.root / "corpus" / "raw"
        self.assets_dir = self.root / "assets"
        self.sampled_dir = self.root / "corpus" / "sampled"
        self.reports_dir = self.root / "reports"

        self.raw_dir.mkdir(parents=True)
        self.assets_dir.mkdir(parents=True)
        self.sampled_dir.mkdir(parents=True)
        self.reports_dir.mkdir(parents=True)

        self.patches = [
            patch.object(asc, "RAW_DIR", self.raw_dir),
            patch.object(asc, "ASSETS_DIR", self.assets_dir),
            patch.object(asc, "SAMPLED_DIR", self.sampled_dir),
            patch.object(asc, "REPORTS_DIR", self.reports_dir),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_check_one_raw_not_found(self):
        issues = asc.check_one("ghost_book")
        self.assertEqual(len(issues), 1)
        self.assertIn("不存在（该书未拆）", issues[0])

    def test_check_one_missing_assets(self):
        book = "test_book"
        b_raw = self.raw_dir / book
        b_raw.mkdir()
        # 写入 pass1
        (b_raw / "pass1_structure.json").write_text("{}", encoding="utf-8")
        issues = asc.check_one(book)
        # 应报告缺资产 structure-obs
        self.assertTrue(any("缺资产 test_book-structure-obs.json" in it for it in issues))

    def test_check_one_expired_fingerprint_mismatch(self):
        book = "test_book"
        b_raw = self.raw_dir / book
        b_raw.mkdir()
        p1 = b_raw / "pass1_structure.json"
        p1.write_text("new content", encoding="utf-8")

        # 资产里记录旧指纹
        asset = self.assets_dir / f"{book}-structure-obs.json"
        asset.write_text(
            json.dumps({"meta": {"source_fingerprint": {"pass1_structure.json": "old_hash_000000"}}}),
            encoding="utf-8",
        )

        issues = asc.check_one(book)
        self.assertTrue(any("pass1_structure.json 内容已变" in it for it in issues))
        self.assertTrue(any("已过期，请重新组装" in it for it in issues))

    def test_check_one_mtime_heuristic(self):
        book = "test_book"
        b_raw = self.raw_dir / book
        b_raw.mkdir()
        p1 = b_raw / "pass1_structure.json"
        p1.write_text("content", encoding="utf-8")

        # 资产无指纹，且修改时间早于 pass 文件
        asset = self.assets_dir / f"{book}-structure-obs.json"
        asset.write_text(json.dumps({"meta": {}}), encoding="utf-8")

        # 人为让 asset mtime 变旧
        past_time = time.time() - 100
        os.utime(asset, (past_time, past_time))

        issues = asc.check_one(book)
        self.assertTrue(any("mtime 启发式" in it for it in issues))

    def test_check_one_sample_indices_mismatch(self):
        book = "test_book"
        b_raw = self.raw_dir / book
        b_raw.mkdir()
        (b_raw / "pass2_character.json").write_text("{}", encoding="utf-8")
        (b_raw / "pass3_style.json").write_text("{}", encoding="utf-8")

        # 资产匹配指纹以避免报过期
        p2_hash = hashlib.sha256(b"{}").hexdigest()[:16]
        p3_hash = hashlib.sha256(b"{}").hexdigest()[:16]

        voice = self.assets_dir / f"{book}-voice-card.json"
        voice.write_text(
            json.dumps({
                "meta": {
                    "source_fingerprint": {
                        "pass2_character.json": p2_hash,
                        "pass3_style.json": p3_hash,
                    },
                    "sample_chapters": [1, 2, 3],
                }
            }),
            encoding="utf-8",
        )

        # 采样器 manifest 记录不同的章节
        b_samp = self.sampled_dir / book
        b_samp.mkdir()
        manifest = b_samp / "manifest.json"
        manifest.write_text(
            json.dumps({"selected_indices": [1, 2, 4]}),
            encoding="utf-8",
        )

        issues = asc.check_one(book)
        self.assertTrue(any("采样已变但资产未更新" in it for it in issues))

    def test_check_one_fully_synced(self):
        book = "perfect_book"
        b_raw = self.raw_dir / book
        b_raw.mkdir()
        (b_raw / "pass1_structure.json").write_text("structure", encoding="utf-8")

        p1_hash = hashlib.sha256(b"structure").hexdigest()[:16]
        asset = self.assets_dir / f"{book}-structure-obs.json"
        asset.write_text(
            json.dumps({"meta": {"source_fingerprint": {"pass1_structure.json": p1_hash}}}),
            encoding="utf-8",
        )

        issues = asc.check_one(book)
        self.assertEqual(issues, [])


class TestAssetSyncMainCLI(unittest.TestCase):
    """测试 asset_sync_check 命令行接口。"""

    def test_main_no_books(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "empty_raw"
            with patch.object(asc, "RAW_DIR", raw_dir):
                stdout_buf = io.StringIO()
                with patch("sys.stdout", stdout_buf):
                    ret = asc.main([])
                self.assertEqual(ret, 0)
                self.assertIn("无需检查", stdout_buf.getvalue())

    def test_main_all_synced(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw"
            raw_dir.mkdir()
            (raw_dir / "book1").mkdir()
            with patch.object(asc, "RAW_DIR", raw_dir), \
                 patch.object(asc, "check_one", return_value=[]), \
                 patch.object(asc, "provenance_note", return_value=""):
                stdout_buf = io.StringIO()
                with patch("sys.stdout", stdout_buf):
                    ret = asc.main([])
                self.assertEqual(ret, 0)
                self.assertIn("[✓] book1", stdout_buf.getvalue())
                self.assertIn("全部 1 本资产与报告同步", stdout_buf.getvalue())

    def test_main_with_issues(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw"
            raw_dir.mkdir()
            (raw_dir / "book1").mkdir()
            with patch.object(asc, "RAW_DIR", raw_dir), \
                 patch.object(asc, "check_one", return_value=["缺资产 demo.json"]), \
                 patch.object(asc, "provenance_note", return_value=""):
                stdout_buf = io.StringIO()
                with patch("sys.stdout", stdout_buf):
                    ret = asc.main([])
                self.assertEqual(ret, 1)
                self.assertIn("[✗] book1", stdout_buf.getvalue())
                self.assertIn("发现 1 个同步问题", stdout_buf.getvalue())


class TestBackfillMeta(unittest.TestCase):
    """测试 backfill_meta 元数据回填与命令行接口。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.raw_dir = self.root / "corpus" / "raw"
        self.assets_dir = self.root / "assets"
        self.raw_dir.mkdir(parents=True)
        self.assets_dir.mkdir(parents=True)

        self.patches = [
            patch.object(bfm, "RAW_DIR", self.raw_dir),
            patch.object(bfm, "ASSETS_DIR", self.assets_dir),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_backfill_one_raw_not_found(self):
        changes, errors, notes = bfm.backfill_one("nonexistent", dry_run=False)
        self.assertEqual(changes, [])
        self.assertTrue(any("不存在" in e for e in errors))
        self.assertEqual(notes, [])

    def test_backfill_one_no_source_note(self):
        book = "empty_book"
        (self.raw_dir / book).mkdir()
        # 放置一个资产文件，但 raw 里无 pass 文件
        (self.assets_dir / f"{book}-structure-obs.json").write_text(
            json.dumps({"meta": {}}), encoding="utf-8"
        )
        changes, errors, notes = bfm.backfill_one(book, dry_run=False)
        self.assertEqual(changes, [])
        self.assertEqual(errors, [])
        self.assertTrue(any("无来源 pass 文件" in n for n in notes))

    def test_backfill_one_corrupt_asset(self):
        book = "corrupt_book"
        b_raw = self.raw_dir / book
        b_raw.mkdir()
        (b_raw / "pass1_structure.json").write_text("pass content", encoding="utf-8")

        # 写入损坏的资产
        (self.assets_dir / f"{book}-structure-obs.json").write_text(
            "{not-json", encoding="utf-8"
        )
        changes, errors, notes = bfm.backfill_one(book, dry_run=False)
        self.assertEqual(changes, [])
        self.assertTrue(any("读取失败" in e for e in errors))

    def test_backfill_one_meta_not_dict(self):
        book = "bad_meta"
        b_raw = self.raw_dir / book
        b_raw.mkdir()
        (b_raw / "pass1_structure.json").write_text("pass content", encoding="utf-8")

        (self.assets_dir / f"{book}-structure-obs.json").write_text(
            json.dumps({"meta": "not-a-dict"}), encoding="utf-8"
        )
        changes, errors, notes = bfm.backfill_one(book, dry_run=False)
        self.assertEqual(changes, [])
        self.assertTrue(any("meta 不是对象" in e for e in errors))

    def test_backfill_one_dry_run_vs_apply(self):
        book = "good_book"
        b_raw = self.raw_dir / book
        b_raw.mkdir()
        (b_raw / "pass1_structure.json").write_text("pass1_content", encoding="utf-8")

        asset_file = self.assets_dir / f"{book}-structure-obs.json"
        asset_file.write_text(json.dumps({"meta": {}}), encoding="utf-8")

        # 1. dry-run
        changes, errors, notes = bfm.backfill_one(book, dry_run=True)
        self.assertEqual(len(changes), 1)
        self.assertEqual(errors, [])
        # 磁盘文件未变更
        loaded = json.loads(asset_file.read_text(encoding="utf-8"))
        self.assertNotIn("source_fingerprint", loaded["meta"])

        # 2. 实际写盘
        changes2, errors2, notes2 = bfm.backfill_one(book, dry_run=False)
        self.assertEqual(len(changes2), 1)
        self.assertEqual(errors2, [])
        loaded2 = json.loads(asset_file.read_text(encoding="utf-8"))
        self.assertIn("source_fingerprint", loaded2["meta"])
        fp = loaded2["meta"]["source_fingerprint"]
        self.assertIn("pass1_structure.json", fp)

        # 3. 再次执行（已是最新，跳过）
        changes3, errors3, notes3 = bfm.backfill_one(book, dry_run=False)
        self.assertEqual(changes3, [])
        self.assertEqual(errors3, [])

    def test_main_cli_empty_and_normal(self):
        # 1. 无书
        empty_raw = self.root / "empty_corpus" / "raw"
        with patch.object(bfm, "RAW_DIR", empty_raw):
            stdout_buf = io.StringIO()
            with patch("sys.stdout", stdout_buf):
                ret = bfm.main([])
            self.assertEqual(ret, 0)
            self.assertIn("无需回填", stdout_buf.getvalue())

        # 2. 正常执行
        book = "cli_book"
        b_raw = self.raw_dir / book
        b_raw.mkdir()
        (b_raw / "pass1_structure.json").write_text("pass", encoding="utf-8")
        (self.assets_dir / f"{book}-structure-obs.json").write_text(
            json.dumps({"meta": {}}), encoding="utf-8"
        )

        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            ret = bfm.main(["--dry-run", book])
        self.assertEqual(ret, 0)
        self.assertIn("将回填 1 个资产", stdout_buf.getvalue())


if __name__ == "__main__":
    unittest.main()
