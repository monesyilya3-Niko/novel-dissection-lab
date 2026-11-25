"""分析轮次隔离：重跑重置、Pass5 补跑、失败不得复用旧产物。"""
from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests import _isolation  # noqa: E402


class TestAnalysisOutputIsolation(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="analysis-output-")
        self._iso = _isolation.isolate_paths(Path(self._tmp.name))
        self._iso.__enter__()
        from gui import config, migrate, services, state_store

        self.config = config
        self.services = services
        self.state_store = state_store
        self.book_id = "pass5-book"
        self.source = Path(self._tmp.name) / "source.txt"
        self.source.write_text("第一章\n正文", encoding="utf-8")
        with services._books_lock:
            services._books_put_locked(self.book_id, {
                "title": "Pass5 测试书",
                "source_path": str(self.source),
                "chapters": [("第一章", "正文" * 100)],
                "metrics": {"total_chars": 200},
            })
        self._patches = [
            mock.patch.object(migrate, "sync_asset", return_value=True),
            mock.patch.object(services, "_sync_book_status"),
            mock.patch.object(services.broker, "publish"),
        ]
        for patch in self._patches:
            patch.start()

    def tearDown(self):
        for patch in reversed(self._patches):
            patch.stop()
        with self.services._books_lock:
            self.services._BOOKS.pop(self.book_id, None)
            self.services._BOOK_INDEX.pop(self.book_id, None)
        with self.services._runtime_lock:
            self.services._runtime.pop(self.book_id, None)
        self._iso.__exit__(None, None, None)
        self._tmp.cleanup()

    def _write_pass(
        self, pass_name: str, payload: dict | None = None, *, chapter: int = 1, batch: int = 0,
    ) -> Path:
        fp = self.state_store.asset_path(self.book_id, chapter, batch, pass_name)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps(payload or {"payload": pass_name}, ensure_ascii=False), encoding="utf-8")
        return fp

    def _seed_success(self, passes: dict[str, str] | None = None) -> None:
        for name in self.services.PASS_ORDER[:4]:
            self._write_pass(name)
        with self.state_store.update_state(self.book_id) as state:
            state["title"] = "Pass5 测试书"
            state["genre"] = "dushi-richang"
            state["status"] = "done"
            state["generate_reports"] = False
            if passes is None:
                self.state_store.set_batch_state(state, 1, 0, "success", asset="old")
            else:
                self.state_store.set_batch_state(state, 1, 0, "success", asset="old", passes=passes)

    def _seed_old_outputs(self) -> tuple[Path, Path]:
        card = self.config.ASSETS_ROOT / f"{self.book_id}-craft-card.json"
        report = self.config.REPORTS_DIR / f"{self.book_id}-笔法分析.md"
        card.parent.mkdir(parents=True, exist_ok=True)
        report.parent.mkdir(parents=True, exist_ok=True)
        card.write_text('{"old": true}', encoding="utf-8")
        report.write_text("旧笔法报告", encoding="utf-8")
        return card, report

    def _ctx(self) -> dict:
        return {"stop_flag": threading.Event(), "paused": threading.Event()}

    def test_new_analysis_clears_success_and_archives_old_outputs(self):
        self._seed_success(dict.fromkeys(self.services.PASS_ORDER, "success"))
        old_card, old_report = self._seed_old_outputs()

        with mock.patch.object(self.services.engine_adapter, "any_model_configured", return_value=True), \
             mock.patch.object(self.services, "_run_analysis") as run:
            self.services.start_analysis(self.book_id, "dushi-richang")
            ctx = self.services._runtime[self.book_id]
            ctx["thread"].join(timeout=2)

        state = self.state_store.load_state(self.book_id)
        self.assertEqual(state["chapter_states"], {})
        self.assertEqual(state["status"], "running")
        self.assertFalse(old_card.exists())
        self.assertFalse(old_report.exists())
        archived = list((self.config.STATE_ROOT / "analysis_archive").rglob(old_card.name))
        self.assertEqual(len(archived), 1)
        run.assert_called_once()

    def test_analysis_archive_is_capped_per_book(self):
        """归档按时间戳新建且永不覆盖，必须限制轮次，否则重跑会无声吃满磁盘。"""
        root = self.config.STATE_ROOT / "analysis_archive" / self.book_id
        for i in range(10):
            d = root / f"2020010{i}T000000.000000Z-restart"
            (d / "assets").mkdir(parents=True, exist_ok=True)
            (d / "assets" / "x.json").write_text("{}", encoding="utf-8")

        self._seed_old_outputs()
        self.services._archive_analysis_outputs(self.book_id, "restart")

        remaining = sorted(d.name for d in root.iterdir() if d.is_dir())
        self.assertEqual(len(remaining), self.services._MAX_ANALYSIS_ARCHIVES_PER_BOOK)
        # 保留的是最新几轮，最旧的一定被清掉
        self.assertNotIn("20200100T000000.000000Z-restart", remaining)

    def test_resume_backfills_only_missing_pass5(self):
        self._seed_success()
        old_card, old_report = self._seed_old_outputs()
        called: list[str] = []

        def fake_run(kind, *args, **kwargs):
            called.append(kind)
            return {"craft_analysis": {"marker": "new"}, "craft_summary": {"marker": "new"}}

        with mock.patch.object(self.services.engine_adapter, "run_batch", side_effect=fake_run), \
             mock.patch.object(self.services, "_assemble_after_analysis", return_value=[]):
            self.services._run_analysis(self.book_id, "urban", None, 4000, self._ctx())

        state = self.state_store.load_state(self.book_id)
        self.assertEqual(called, ["pass5_craft"])
        self.assertEqual(state["status"], "done")
        self.assertEqual(state["chapter_states"]["c1-b0"]["passes"]["pass5_craft"], "success")
        self.assertTrue(self.state_store.asset_path(self.book_id, 1, 0, "pass5_craft").is_file())
        self.assertFalse(old_card.exists())
        self.assertFalse(old_report.exists())

    def test_corrupted_batch_record_is_rerun(self):
        self._seed_success()
        with self.state_store.update_state(self.book_id) as state:
            state["chapter_states"]["c1-b0"] = "corrupted"
        called: list[str] = []

        def fake_run(kind, *args, **kwargs):
            called.append(kind)
            return {"payload": kind}

        with mock.patch.object(self.services.engine_adapter, "run_batch", side_effect=fake_run), \
             mock.patch.object(self.services, "_assemble_after_analysis", return_value=[]):
            self.services._run_analysis(self.book_id, "urban", None, 4000, self._ctx())

        state = self.state_store.load_state(self.book_id)
        self.assertEqual(called, list(self.services.PASS_ORDER))
        self.assertEqual(state["chapter_states"]["c1-b0"]["status"], "success")
        self.assertTrue(all(
            status == "success"
            for status in state["chapter_states"]["c1-b0"]["passes"].values()
        ))

    def test_atomic_write_failure_removes_temp_file(self):
        real_replace = self.services.os.replace

        def fail_asset_replace(src, dst):
            if str(dst).endswith("-pass1_structure.json"):
                raise OSError("replace denied")
            return real_replace(src, dst)

        with mock.patch.object(self.services.engine_adapter, "run_batch", return_value={"payload": "new"}), \
             mock.patch.object(self.services.os, "replace", side_effect=fail_asset_replace), \
             mock.patch.object(self.services, "_assemble_after_analysis", return_value=[]):
            self.services._run_analysis(self.book_id, "urban", None, 4000, self._ctx())

        state = self.state_store.load_state(self.book_id)
        self.assertEqual(state["chapter_states"]["c1-b0"]["status"], "failed")
        self.assertFalse(list(self.config.ASSETS_ROOT.rglob("*.tmp")))

    def test_failed_pass5_is_partial_and_stale_card_is_not_reused(self):
        self._seed_success(dict.fromkeys(self.services.PASS_ORDER, "success"))
        self._write_pass("pass5_craft", {"craft_analysis": {"marker": "stale"}})
        old_card, old_report = self._seed_old_outputs()
        with self.state_store.update_state(self.book_id) as state:
            state["chapter_states"]["c1-b0"]["passes"]["pass5_craft"] = "failed"

        with mock.patch.object(
            self.services.engine_adapter, "run_batch",
            side_effect=RuntimeError("pass5 unavailable"),
        ), mock.patch.object(self.services.engine_adapter, "assemble_asset_craft_card") as assemble_craft:
            self.services._run_analysis(self.book_id, "urban", None, 4000, self._ctx())

        state = self.state_store.load_state(self.book_id)
        self.assertEqual(state["status"], "partial")
        self.assertEqual(state["chapter_states"]["c1-b0"]["passes"]["pass5_craft"], "failed")
        self.assertIn("pass5 unavailable", state["last_error"])
        self.assertFalse(old_card.exists())
        self.assertFalse(old_report.exists())
        assemble_craft.assert_not_called()

    def test_merge_uses_only_current_successful_batches_and_passes(self):
        state = {
            "book_id": self.book_id,
            "title": "Pass5 测试书",
            "chapter_states": {
                "c1-b0": {"status": "success", "passes": {"pass5_craft": "failed"}},
                "c2-b0": {"status": "success", "passes": {"pass5_craft": "success"}},
            },
        }
        for chapter in (1, 2, 3):
            self._write_pass("pass5_craft", {
                "craft_analysis": {"marker": chapter},
                "craft_summary": {"marker": chapter},
            }, chapter=chapter)
        # c3 是不同批次尺寸留下的孤儿，状态中没有它。

        with mock.patch.object(
            self.services.engine_adapter, "assemble_asset_craft_card",
            return_value={"meta": {"source_title": "Pass5 测试书"}},
        ) as assemble_craft, mock.patch.object(
            self.services.engine_adapter, "validate_asset_card", return_value=([], []),
        ):
            written = self.services._assemble_after_analysis(
                self.book_id, "urban", [("第一章", "正文")], state,
            )

        self.assertIn(f"{self.book_id}-craft-card.json", written)
        merged = assemble_craft.call_args.args[4]
        self.assertEqual(merged["craft_analysis"]["marker"], 2)
        self.assertEqual(merged["craft_summary"]["marker"], 2)


if __name__ == "__main__":
    unittest.main()
