"""分析结束后整书资产卡组装（2026-11-05 补测）。

背景：GUI 分析只落批级 ``assets/{book_id}/cN-bM-passK.json``，而结果页与报告
读的是整书卡 ``assets/{book_id}-voice-card.json``。原实现**没有任何代码生成
它们**——用户看到「分析完成」，结果页资产全空、报告 0 字、铁律二必然判失败。

``_assemble_after_analysis`` 负责合并批级产物。此前**零测试覆盖**，
因此这里用真实批级文件形态做端到端验证。
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests import _isolation  # noqa: E402


class TestAssembleAfterAnalysis(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="nl-assemble-")
        self._ctx = _isolation.isolate_paths(Path(self._tmp))
        self._ctx.__enter__()
        from gui import config, migrate, services, state_store
        self.config = config
        self.services = services
        self.state_store = state_store
        # 本文件只验证「合并批级产物 → 组装整书卡 → 校验 → 原子落盘」，
        # 落盘后的 SQLite 重索引（migrate.sync_asset）是另一条能力，有 68 条
        # 专属测试（test_migrate / test_asset_sync_and_backfill / test_builtin_sync）。
        #
        # 这里把重索引用 no-op 顶掉，理由是可移植性：每个用例都 init_schema()
        # 建一次库，再随隔离目录整棵回收，会反复触发 gui.db 的「路径变化→关闭
        # 全部连接→重建」路径。实测在 GitHub Actions 的 Ubuntu + Python 3.13
        # 组合下，累积到 ~1100 个用例后会 Segfault（exit 139）；同一提交在
        # 3.11 / 3.12 / Windows 上全绿。减少无谓的全局连接池抖动比"顺带测到
        # 重索引"更有价值。
        self._sync_calls: list[str] = []
        self._patch = mock.patch.object(
            migrate, "sync_asset",
            side_effect=lambda fp: self._sync_calls.append(str(fp)) or True)
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self.book_id = "assemble-book"
        self.batch_dir = config.ASSETS_ROOT / self.book_id
        self.batch_dir.mkdir(parents=True, exist_ok=True)
        # 注册一本带 metrics 的书：生产里 _books_get 会返回实测指标，
        # assemble 的 _backfill_rhythm 靠它把句长三项填成真实值。
        src = Path(self._tmp) / "source.txt"
        src.write_text("占位", encoding="utf-8")
        with services._books_lock:
            services._books_put_locked(
                self.book_id,
                {
                    "title": "测试书",
                    "source_path": str(src),
                    "chapters": [("第1章", "正文")],
                    "metrics": {
                        "total_chars": 60000,
                        "sentence_count": 2400,
                        "avg_sentence_len": 18.5,
                        "short_ratio": 0.34,
                        "long_ratio": 0.12,
                        "paragraph_count": 520,
                    },
                },
            )

    def tearDown(self):
        try:
            with self.services._books_lock:
                self.services._BOOKS.pop(self.book_id, None)
                self.services._BOOK_INDEX.pop(self.book_id, None)
            self._ctx.__exit__(None, None, None)
        finally:
            _isolation.remove_tree(Path(self._tmp))

    def _write_batch(self, chapter: int, batch: int, pass_name: str, payload: dict):
        fp = self.batch_dir / f"c{chapter}-b{batch}-{pass_name}.json"
        fp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return fp

    def _state(self) -> dict:
        return {"book_id": self.book_id, "title": "测试书", "status": "done"}

    def _rich_pass3(self) -> dict:
        """一份能过校验的 pass3 形态（含实测口径的句长/段落数值）。"""
        return {
            "narration": {
                "pov": "third_limited",
                "burst_pattern": "短句收束，长句铺陈",
                "sentence_rhythm": {
                    "avg_length": 18.5, "short_ratio": 0.34, "long_ratio": 0.12,
                },
                "paragraph": {"avg_lines": 4.2, "chars_per_para": 96.0},
            },
            "dialogue": {"dialogue_ratio": 0.32, "tags": ["短促", "带刺"]},
            "emotion": {"direct_statement_ratio": 0.2, "show_dont_tell": "以动作替代直陈"},
            "imagery": {"domains": ["水", "灯"], "examples": ["灯芯爆了一下"]},
            "banned": {"words": ["不禁", "竟然"], "phrases": ["不由得"]},
        }

    def _chapters(self, n: int = 3) -> list:
        return [(f"第{i}章", f"正文{i}" * 100) for i in range(1, n + 1)]

    def test_no_batch_files_returns_empty(self):
        """没有任何批级产物时不得崩，也不得产出空卡。"""
        written = self.services._assemble_after_analysis(
            self.book_id, "urban", self._chapters(), self._state())
        self.assertEqual(written, [])

    def test_written_cards_trigger_reindex(self):
        """契约：每张成功落盘的卡都要触发一次 SQLite 重索引。

        只写文件不重索引，资产库里搜不到这张卡——文件在磁盘上却"不存在"，
        用户只能通过重新迁移才看得见。
        """
        self._write_batch(1, 0, "pass2_character", {
            "characters": [{"name": "林昭", "role": "主角"}],
        })
        self._write_batch(1, 0, "pass3_style", self._rich_pass3())

        written = self.services._assemble_after_analysis(
            self.book_id, "urban", self._chapters(), self._state())

        self.assertTrue(written, "前置条件：应至少产出一张卡")
        indexed = {Path(p).name for p in self._sync_calls}
        self.assertEqual(
            indexed, set(written),
            "落盘的卡与触发重索引的卡必须一一对应（写盘了却漏索引 = 资产库看不见）")

    def test_manifest_carries_sample_chapters(self):
        """回归：manifest 缺 selected_indices → sample_chapters=[] → 校验必失败。

        这是「组装函数写了但卡永远出不来」的直接原因：validate_voice_card 要求
        meta.sample_chapters ≥3 项，空列表必然 ERR，_write 于是静默跳过落盘。
        结果页资产全空、报告 0 字、铁律二必判失败，日志里只有一行 warning。
        """
        self._write_batch(1, 0, "pass2_character", {
            "characters": [{"name": "林昭", "role": "主角", "traits": ["冷静"]}],
        })
        self._write_batch(1, 0, "pass3_style", self._rich_pass3())

        written = self.services._assemble_after_analysis(
            self.book_id, "urban", self._chapters(3), self._state())

        self.assertIn(f"{self.book_id}-voice-card.json", written,
                      "voice-card 未能落盘——manifest 的 sample_chapters 口径可能又断了")
        card = json.loads(
            (self.config.ASSETS_ROOT / f"{self.book_id}-voice-card.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(card["meta"]["sample_chapters"], [1, 2, 3])

    def test_sample_chapters_inferred_from_batch_keys_when_chapters_absent(self):
        """chapters 参数为空时，用 chapter_states 的 cN 反推章节数。"""
        state = self._state()
        state["chapter_states"] = {"c1-b0": {"status": "success"},
                                   "c2-b0": {"status": "success"},
                                   "c4-b0": {"status": "success"}}
        self._write_batch(1, 0, "pass2_character", {
            "characters": [{"name": "林昭", "role": "主角"}],
        })
        self._write_batch(1, 0, "pass3_style", self._rich_pass3())

        written = self.services._assemble_after_analysis(
            self.book_id, "urban", [], state)
        self.assertIn(f"{self.book_id}-voice-card.json", written)
        card = json.loads(
            (self.config.ASSETS_ROOT / f"{self.book_id}-voice-card.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(card["meta"]["sample_chapters"], [1, 2, 3, 4])

    def test_merges_pass2_across_batches(self):
        """pass2 跨批合并：两个批的角色都出现在 voice-card 里（不丢、不覆盖）。"""
        self._write_batch(1, 0, "pass2_character", {
            "characters": [{"name": "林昭", "role": "主角", "traits": ["冷静"]}],
        })
        self._write_batch(1, 1, "pass2_character", {
            "characters": [{"name": "沈砚", "role": "配角", "traits": ["隐忍"]}],
        })
        self._write_batch(1, 1, "pass3_style", self._rich_pass3())

        written = self.services._assemble_after_analysis(
            self.book_id, "urban", self._chapters(3), self._state())

        self.assertIn(f"{self.book_id}-voice-card.json", written)
        card = json.loads(
            (self.config.ASSETS_ROOT / f"{self.book_id}-voice-card.json")
            .read_text(encoding="utf-8"))
        names = {v.get("name") for v in
                 (card.get("dialogue", {}).get("character_voices") or [])}
        self.assertEqual(names, {"林昭", "沈砚"},
                         "两批的角色必须都进 voice-card，合并时不能互相覆盖")

    def test_batch_order_is_numeric_not_lexicographic(self):
        """c10-b0 必须排在 c2-b0 之后（字典序会把 10 排到 2 前面）。"""
        from gui.services import _batch_sort_key
        names = ["c10-b0-pass1_structure.json", "c2-b0-pass1_structure.json",
                 "c1-b0-pass1_structure.json"]
        self.assertEqual(sorted(names, key=_batch_sort_key),
                         ["c1-b0-pass1_structure.json",
                          "c2-b0-pass1_structure.json",
                          "c10-b0-pass1_structure.json"])

    def test_meta_and_model_keys_are_not_merged_into_card(self):
        """批级的 _meta / model / tokens 是元信息，不能混进资产卡。"""
        self._write_batch(1, 0, "pass1_structure", {
            "chapter_analyses": [
                {"chapter": str(i), "role": "铺垫", "beats": ["起"], "hook": "悬念",
                 "foreshadow": "玉佩"}
                for i in (1, 2, 3)
            ],
            "aggregate": {
                "hook_type_freq": {"悬念": 0.6},
                "hook_min_interval": 1,
                "foreshadow_avg_span": 2.0,
                "foreshadow_max_span": 4,
                "foreshadow_concurrent_open": 1,
            },
            "_meta": {"pass": "pass1_structure"},
            "model": "deepseek-4.1-flash",
            "tokens": 1234,
        })
        written = self.services._assemble_after_analysis(
            self.book_id, "urban", self._chapters(3), self._state())
        self.assertIn(f"{self.book_id}-structure-obs.json", written)
        card = json.loads(
            (self.config.ASSETS_ROOT / f"{self.book_id}-structure-obs.json")
            .read_text(encoding="utf-8"))
        blob = json.dumps(card, ensure_ascii=False)
        self.assertNotIn("deepseek-4.1-flash", blob)
        self.assertNotIn('"tokens"', blob)

    def test_corrupt_batch_file_is_skipped_not_fatal(self):
        """一个批文件损坏不得让整次组装失败——其余批仍要进卡。"""
        self._write_batch(1, 0, "pass2_character", {
            "characters": [{"name": "林昭", "role": "主角"}]})
        self._write_batch(1, 0, "pass3_style", self._rich_pass3())
        bad = self.batch_dir / "c1-b1-pass2_character.json"
        bad.write_text("{ 这不是 JSON", encoding="utf-8")

        written = self.services._assemble_after_analysis(
            self.book_id, "urban", self._chapters(3), self._state())
        self.assertIn(f"{self.book_id}-voice-card.json", written)
        card = json.loads(
            (self.config.ASSETS_ROOT / f"{self.book_id}-voice-card.json")
            .read_text(encoding="utf-8"))
        names = {v.get("name") for v in
                 (card.get("dialogue", {}).get("character_voices") or [])}
        self.assertIn("林昭", names, "坏文件只应被跳过，不能拖垮整卡")

    def test_refusal_only_batches_produce_no_voice_card(self):
        """整批都是拒答（characters 为空）时不得写出空 voice-card。

        这正是 2026-11-05 修的 pipeline 缺陷在生产里留下的形态：批次被误判
        success，落盘的全是 ``{"status": "no_input", "characters": []}``。
        """
        for b in range(3):
            self._write_batch(1, b, "pass2_character", {
                "status": "no_input",
                "message": "未收到任何对话切片文本",
                "characters": [],
            })
        written = self.services._assemble_after_analysis(
            self.book_id, "urban", self._chapters(3), self._state())
        self.assertNotIn(f"{self.book_id}-voice-card.json", written)


if __name__ == "__main__":
    unittest.main()
