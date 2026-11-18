"""Round-2 后端加固回归测试套件。

覆盖：
1. 测试隔离与启动卫生（XUAN_DATA_DIR 隔离、真实用户目录快照、延迟迁移、动态日志路径、动态质检阈值自检）；
2. 报告 SQLite 实时同步、assemble 合成 manifest 与前置校验、无泄漏报告直连触发；
3. 离线 Web-AI 五遍拆书接管与纯离线双报告生成（+3 新端点，总路由 140）；
4. 章节标题持久化入库回显与无就绪密钥快速降级；
5. SQLite BEGIN IMMEDIATE + 嵌套 SAVEPOINT、连接池死线程回收、SSE 订阅上限、6 类脏输入 400 拦截；
6. 多格式导出加固（DOCX/EPUB/Shunn/Platform）与去 AI 味误报修复。
"""
from __future__ import annotations

import base64
import io
import json
import logging
import os
import sys
import tempfile
import threading
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock

_TESTS_DIR = Path(__file__).resolve().parent
_ROOT = _TESTS_DIR.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

import _isolation  # noqa: E402

from gui import (  # noqa: E402
    config,
    db,
    deslop_service,
    engine_adapter,
    essence_service,
    logging_setup,
    migrate,
    model_service,
    name_generator,
    platform_service,
    router,
    services,
    sse,
    system_service,
    writing_extra,
    writing_service,
)
from gui.services import ServiceError  # noqa: E402


def _valid_pass_payloads() -> dict[str, dict]:
    """构造可通过 validate_asset_card 严苛校验且足够支撑万字报告的五遍扫描 JSON。"""
    long_note = "叙事推进紧凑扎实，冲突层层递进，人物动机与伏笔暗线严丝合缝。" * 8
    ch_analyses = [
        {
            "chapter": str(i),
            "title": f"第{i}章 寒江夜雪",
            "role": "推进" if i % 2 else "爆发",
            "beats": [f"节拍A：{long_note[:80]}", f"节拍B：{long_note[:80]}"],
            "hook": {"type": "危机降临", "strength": "strong", "note": long_note[:80]},
            "foreshadow": [f"暗线埋设{i}：{long_note[:60]}"],
            "summary": f"主角在风雪绝境中识破陷阱并完成反制。{long_note}",
        }
        for i in range(1, 12)
    ]
    pass1 = {
        "chapter_analyses": ch_analyses,
        "aggregate": {
            "hook_type_freq": {"危机降临": 6, "悬念揭示": 5},
            "hook_min_interval": 1,
            "foreshadow_avg_span": 4,
            "foreshadow_max_span": 9,
            "foreshadow_concurrent_open": 3,
            "climax_cycle": 4,
        },
    }
    roles = ["主角", "女主", "反派", "导师", "配角", "配角"]
    pass2 = {
        "characters": [
            {
                "name": f"角色{idx}",
                "role": roles[idx - 1],
                "speech_style": f"言辞冷峻克制，短句机锋鲜明（{long_note[:60]}）",
                "catchphrases": ["先看证据", "不必多言"],
                "forbidden_words": ["人家", "嘤嘤"],
                "emotional_tell": f"情绪紧绷时指节轻叩桌面，呼吸微沉。{long_note[:60]}",
            }
            for idx in range(1, 7)
        ]
    }
    pass3 = {
        "narration": {
            "pov": "third_limited",
            "burst_pattern": f"长句铺陈环境压迫，短句收束致命动作。{long_note}",
            "sentence_rhythm": {
                "avg_length": 17.5,
                "short_ratio": 0.35,
                "long_ratio": 0.12,
            },
            "paragraph": {"avg_lines": 2.4, "chars_per_para": 68.0},
        },
        "dialogue": {
            "dialogue_ratio": 0.32,
            "tags": ["短促", "冷峻"],
        },
        "emotion": {
            "mode": "动作外化式",
            "direct_statement_ratio": 0.12,
            "show_dont_tell": f"以呼吸停顿与视线偏移承载剧烈情绪波动。{long_note}",
        },
        "imagery": {
            "domains": ["寒江", "残灯", "铁锈"],
            "examples": [f"残灯火苗在寒风中摇曳。{long_note[:60]}"],
        },
        "banned": {
            "words": ["霎时间", "恐怖如斯", "倒吸一口凉气"],
            "phrases": ["不由得"],
        },
    }
    pass4 = {
        "payoff_density": {
            "per_thousand_words": 0.85,
            "payoff_types": [
                {
                    "type": "反杀",
                    "buildup_length": 1600,
                    "skeleton": f"反派设局围堵施压，主角借规则漏洞当场反制。{long_note}",
                }
            ],
        },
        "opening_analysis": {
            "chapter_1": {
                "hook_position": 120,
                "first_300_words_task": f"寒江生死追杀直接切入主线危机。{long_note}",
            },
            "common_mistakes": [f"忌开篇堆砌千字世界观百科说明。{long_note[:60]}"],
        },
        "paywall": {
            "chapter_range": "15-20",
            "cliffhanger_strategy": f"卷末暗线揭晓引发更高层势力对决。{long_note}",
        },
        "skeleton": f"三段式蓄势与爽点兑现骨架。{long_note}",
        "dry_spell_tolerance": 2,
        "update_rhythm": "日更两章，每章约 2500 字",
        "retention_risk_points": [{"chapter": "2", "reason": "中段过渡需保持次级冲突"}],
    }
    craft_dims = (
        "foreshadowing",
        "information_release",
        "pov_control",
        "scene_transition",
        "tension_building",
        "dialogue_craft",
        "rhythm_control",
        "sensory_craft",
        "narrative_engine",
        "emotional_algorithm",
    )
    pass5 = {
        "craft_analysis": {
            dim: {
                "techniques": [
                    {
                        "name": f"{dim}_核心技法_{k}",
                        "description": f"技法深度拆解与文本机制说明：{long_note}",
                        "effect": f"读者体验与追读张力强化效果：{long_note[:100]}",
                        "skeleton": f"可迁移四步结构骨架：{long_note[:100]}",
                        "anti_pattern": f"常见失效反例警示：{long_note[:80]}",
                    }
                    for k in range(1, 4)
                ]
            }
            for dim in craft_dims
        },
        "craft_summary": {
            "top_3_strengths": [f"核心长板优势 {k}：{long_note[:80]}" for k in range(1, 4)],
            "unique_techniques": [f"独创叙事技法 {k}：{long_note[:80]}" for k in range(1, 4)],
            "reusable_patterns": [f"可复用实战模板 {k}：{long_note[:80]}" for k in range(1, 4)],
        },
    }
    return {
        "pass1_structure": pass1,
        "pass2_character": pass2,
        "pass3_style": pass3,
        "pass4_commercial": pass4,
        "pass5_craft": pass5,
    }


class TestIsolationAndStartupHygiene(unittest.TestCase):
    def test_isolate_paths_manages_xuan_data_dir(self):
        prev = os.environ.get("XUAN_DATA_DIR")
        tmp = Path(tempfile.mkdtemp(prefix="r2_iso_"))
        with _isolation.isolate_paths(tmp):
            self.assertEqual(os.environ.get("XUAN_DATA_DIR"), str(tmp))
            self.assertEqual(config._user_data_dir(), tmp)
        self.assertEqual(os.environ.get("XUAN_DATA_DIR"), prev)
        self.assertFalse(tmp.exists())

    def test_migrate_legacy_state_explicit_target_idempotent(self):
        tmp = Path(tempfile.mkdtemp(prefix="r2_mig_"))
        try:
            target = tmp / "user_data"
            target.mkdir(parents=True, exist_ok=True)
            # 预置用户新文件，验证不会被覆盖
            (target / "assets").mkdir(parents=True, exist_ok=True)
            sentinel = target / "assets" / "trope-library.json"
            sentinel.write_text('{"custom": true}', encoding="utf-8")
            config.migrate_legacy_state(target)
            self.assertEqual(json.loads(sentinel.read_text(encoding="utf-8")), {"custom": True})
            self.assertTrue((target / "assets" / ".migration-complete").is_file())
            # 幂等重跑不报错
            config.migrate_legacy_state(target)
        finally:
            _isolation.remove_tree(tmp)

    def test_setup_logging_follows_dynamic_state_root(self):
        tmp = Path(tempfile.mkdtemp(prefix="r2_log_"))
        root_logger = logging.getLogger(logging_setup.LOGGER_NAME)
        orig_handlers = list(root_logger.handlers)
        for h in orig_handlers:
            root_logger.removeHandler(h)
        try:
            with _isolation.isolate_paths(tmp):
                log_path = Path(logging_setup.setup_logging())
                self.assertEqual(log_path, config.STATE_ROOT / "logs" / "gui.log")
                self.assertTrue(log_path.parent.is_dir())
                for h in list(root_logger.handlers):
                    root_logger.removeHandler(h)
                    h.close()
        finally:
            for h in list(root_logger.handlers):
                root_logger.removeHandler(h)
                h.close()
            for h in orig_handlers:
                root_logger.addHandler(h)
            _isolation.remove_tree(tmp)

    def test_adapter_self_check_accepts_custom_user_thresholds(self):
        tmp = Path(tempfile.mkdtemp(prefix="r2_thr_"))
        with _isolation.isolate_paths(tmp):
            system_service.update_settings({
                "thresholds": {"quality_pass_line": 82, "quality_warn_line": 66}
            })
            self.assertTrue(engine_adapter.adapter_self_check())


class TestReportSyncAssembleAndFullAnalysis(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="r2_rep_"))
        self._iso = _isolation.isolate_paths(self._tmp)
        self._iso.__enter__()
        db.init_schema()
        db.apply_migrations()

    def tearDown(self):
        db.close()
        self._iso.__exit__(None, None, None)

    def test_sync_report_and_list_reports_merge_disk_and_db(self):
        config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        fp1 = config.REPORTS_DIR / "b1-拆书报告.md"
        fp1.write_text("# 拆书报告\n" + "内容" * 3000, encoding="utf-8")
        self.assertTrue(migrate.sync_report(fp1))

        db_rows = db.list_reports(book_id="b1")
        self.assertEqual(len(db_rows), 1)
        self.assertEqual(db_rows[0]["type"], "book")

        # 额外在磁盘写入一份尚未入库的报告，验证 services.list_reports 合并无遗漏
        fp2 = config.REPORTS_DIR / "b1-笔法分析.md"
        fp2.write_text("# 笔法分析\n" + "笔法" * 3000, encoding="utf-8")
        listed = services.list_reports()
        ids = {r["id"] for r in listed}
        self.assertIn("report:b1-拆书报告", ids)
        self.assertIn("report:b1-笔法分析", ids)

    def test_writing_assemble_synthesizes_manifest_validates_and_marks_done(self):
        bid = "book_asm_1"
        with db.tx() as conn:
            migrate._upsert_book(conn, bid, "星河长明", None, "xuanhuan", "idle")

        raw_dir = config.CORPUS_DIR / "raw" / bid
        raw_dir.mkdir(parents=True, exist_ok=True)
        payloads = _valid_pass_payloads()
        for p_name, data in payloads.items():
            (raw_dir / f"{p_name}.json").write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )

        # 不提供 manifest.json，验证自动合成 sample_chapters >= 3 且通过 schema 校验
        res = writing_service.assemble(bid, "xuanhuan")
        self.assertEqual(len(res["written"]), 4)
        vc = json.loads((config.ASSETS_ROOT / f"{bid}-voice-card.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(vc["meta"]["sample_chapters"]), 3)
        self.assertEqual(vc["meta"]["source_title"], "星河长明")

        # SQLite 已同步资产且 books.status 已推进为 done
        self.assertEqual(db.get_books(book_id=bid)[0]["status"], "done")
        self.assertGreaterEqual(len(db.list_asset_rows(book_id=bid)), 4)

        # 若某张卡校验失败（如 commercial-obs 缺失必填结构），必须 400 且不覆盖磁盘已有合法卡
        bad_pass4 = {"payoff_density": "INVALID_NOT_A_DICT"}
        (raw_dir / "pass4_commercial.json").write_text(json.dumps(bad_pass4, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(ServiceError) as cm:
            writing_service.assemble(bid, "xuanhuan")
        self.assertEqual(cm.exception.code, 400)
        co_after = json.loads((config.ASSETS_ROOT / f"{bid}-commercial-obs.json").read_text(encoding="utf-8"))
        self.assertIsInstance(co_after["payoff_density"], dict)

    def test_run_full_analysis_triggers_reports_directly_without_watch_thread(self):
        src = self._tmp / "full_book.txt"
        src.write_text(
            "第1章 初入风雪\n" + "寒风呼啸，少年握紧铁剑。" * 80 + "\n\n"
            "第2章 剑鸣残夜\n" + "剑光破开夜幕，强敌退避。" * 80 + "\n\n"
            "第3章 破局而出\n" + "真相水落石出，众人哗然。" * 80,
            encoding="utf-8",
        )
        imp = services.import_book(str(src), batch_size=4000)
        bid = imp["book_id"]
        payloads = _valid_pass_payloads()

        def fake_run_batch(kind, *_args, **_kwargs):
            return payloads[kind]

        with (
            mock.patch.object(engine_adapter, "any_model_configured", return_value=True),
            mock.patch.object(engine_adapter, "is_known_genre", return_value=True),
            mock.patch.object(engine_adapter, "run_batch", side_effect=fake_run_batch),
            mock.patch.object(
                engine_adapter,
                "build_report",
                return_value="# 拆书报告\n\n" + ("深度拆书分析正文段落。" * 1200),
            ),
        ):
            services.run_full_analysis(bid, "xuanhuan")
            # 确认不存在旧版 report-* 24h 轮询线程
            report_threads = [t.name for t in threading.enumerate() if t.name.startswith("report-")]
            self.assertEqual(report_threads, [])

            deadline = time.time() + 8.0
            while time.time() < deadline:
                if services.get_status(bid)["status"] in ("done", "error"):
                    break
                time.sleep(0.05)

        st = services.get_status(bid)
        self.assertEqual(st["status"], "done")
        self.assertEqual(st["report_error"], "")
        self.assertTrue((config.REPORTS_DIR / f"{bid}-拆书报告.md").is_file())
        self.assertEqual(len(db.list_reports(book_id=bid)), 1)


class TestTakeoverAndOfflineReportsEndpoints(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="r2_tk_"))
        self._iso = _isolation.isolate_paths(self._tmp)
        self._iso.__enter__()
        db.init_schema()
        db.apply_migrations()

    def tearDown(self):
        with services._books_lock:
            services._BOOKS.clear()
            services._BOOK_INDEX.clear()
        db.close()
        self._iso.__exit__(None, None, None)

    def test_route_count_is_140(self):
        self.assertEqual(len(router.ROUTES), 140)

    def test_takeover_flow_and_offline_report_generation(self):
        # 构造 10 章大体积语料以验证采样与 Pass 5 ~40,000 字截断保护
        chapters_txt = []
        for idx in range(1, 11):
            body = f"“你当真要拔剑？”陆沉冷声问道。第{idx}章风雪夜战。" * 600
            chapters_txt.append(f"第{idx}章 风雪第{idx}重\n{body}")
        src = self._tmp / "takeover_novel.txt"
        src.write_text("\n\n".join(chapters_txt), encoding="utf-8")

        imp, _ = router.dispatch("POST", "/api/import", {"path": str(src)}, {})
        self.assertEqual(imp["code"], 0)
        bid = imp["data"]["book_id"]

        # 路径穿越校验
        with self.assertRaises(ServiceError) as bad_id_cm:
            services.get_takeover_bundle("../evil")
        self.assertEqual(bad_id_cm.exception.code, 400)

        # 1. GET 总览（尚未采样）
        ov, _ = router.dispatch("GET", f"/api/analyze/takeover/{bid}", {}, {})
        self.assertEqual(ov["code"], 0)
        self.assertFalse(ov["data"]["sampled_ready"])
        self.assertEqual(len(ov["data"]["passes"]), 5)

        # 非法 pass_name -> 400
        with self.assertRaises(ServiceError) as bad_pass_cm:
            router.dispatch("GET", f"/api/analyze/takeover/{bid}", {}, {"pass_name": "pass9_bad"})
        self.assertEqual(bad_pass_cm.exception.code, 400)

        # 2. GET 单 Pass Prompt 包（自动触发离线采样 + 长度安全受控）
        p5_resp, _ = router.dispatch(
            "GET", f"/api/analyze/takeover/{bid}", {}, {"pass_name": "pass5_craft"}
        )
        self.assertEqual(p5_resp["code"], 0)
        bundle = p5_resp["data"]["prompt_bundle"]
        self.assertIn("严禁连续摘抄原文超过 11 字", bundle)
        self.assertLess(len(bundle), 55000)

        # 3. POST 非法 JSON 与空对象拦截 -> 400
        for bad_content in ("完全没有花括号的废话", "```json\n{}\n```", ""):
            with self.assertRaises(ServiceError) as bad_post_cm:
                router.dispatch(
                    "POST",
                    f"/api/analyze/takeover/{bid}",
                    {"pass_name": "pass1_structure", "content": bad_content},
                    {},
                )
            self.assertEqual(bad_post_cm.exception.code, 400)

        # 4. POST 五遍合法回复（含 ```json 代码块包裹形态）
        payloads = _valid_pass_payloads()
        for p_name, p_obj in payloads.items():
            wrapped = f"好的，以下是 {p_name} 的分析结果：\n```json\n{json.dumps(p_obj, ensure_ascii=False)}\n```\n"
            save_resp, _ = router.dispatch(
                "POST",
                f"/api/analyze/takeover/{bid}",
                {"pass_name": p_name, "content": wrapped},
                {},
            )
            self.assertEqual(save_resp["code"], 0)
            self.assertGreater(save_resp["data"]["size_bytes"], 20)

        # 5. 清空内存 _BOOKS 且强制 any_model_configured=False，验证 100% 纯离线组装 + 万字报告生成
        with services._books_lock:
            services._BOOKS.clear()
            services._BOOK_INDEX.clear()

        with mock.patch.object(engine_adapter, "any_model_configured", return_value=False):
            rep_resp, _ = router.dispatch(
                "POST",
                f"/api/book/{bid}/reports",
                {"genre": "xuanhuan", "assemble": True},
                {},
            )
        self.assertEqual(rep_resp["code"], 0)
        rep_data = rep_resp["data"]
        self.assertEqual(len(rep_data["assembled"]), 4)
        self.assertTrue(rep_data["report_ok"], rep_data)
        self.assertGreaterEqual(rep_data["total_chars"], 10000)
        self.assertEqual(len(rep_data["reports"]), 2)
        self.assertEqual(len(db.list_reports(book_id=bid)), 2)


class TestChapterTitleAndFastDegrade(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="r2_ch_"))
        self._iso = _isolation.isolate_paths(self._tmp)
        self._iso.__enter__()
        db.init_schema()
        db.apply_migrations()
        config.ASSETS_ROOT.mkdir(parents=True, exist_ok=True)
        vc = {
            "meta": {"title": "测试书", "genre": "xuanhuan", "confidence": 0.8},
            "narration": {"pov": "third_limited"},
            "dialogue": {"character_voices": []},
            "emotion_handling": {"mode": "体感"},
            "banned": {"never_used_words": []},
        }
        (config.ASSETS_ROOT / "tvoice-voice-card.json").write_text(
            json.dumps(vc, ensure_ascii=False), encoding="utf-8"
        )

    def tearDown(self):
        db.close()
        self._iso.__exit__(None, None, None)

    def test_import_chapter_title_persistence_and_get_chapter_title(self):
        resp, _ = router.dispatch(
            "POST",
            "/api/writing/chapters",
            {
                "project": "剑道独尊",
                "chapter_no": 1,
                "title": "第1章 雪夜拔剑",
                "content": "风雪扑面而来，他按住剑柄。",
            },
            {},
        )
        self.assertEqual(resp["code"], 0)

        got, _ = router.dispatch("GET", "/api/writing/projects/剑道独尊/chapters/1", {}, {})
        self.assertEqual(got["code"], 0)
        self.assertEqual(got["data"]["title"], "第1章 雪夜拔剑")
        self.assertTrue(got["data"]["content"].startswith("第1章 雪夜拔剑\n\n风雪扑面而来"))

        # 再次保存已带该标题的正文时不得重复拼接两遍标题
        router.dispatch(
            "POST",
            "/api/writing/chapters",
            {
                "project": "剑道独尊",
                "chapter_no": 1,
                "title": "第1章 雪夜拔剑",
                "content": got["data"]["content"],
            },
            {},
        )
        got2, _ = router.dispatch("GET", "/api/writing/projects/剑道独尊/chapters/1", {}, {})
        self.assertEqual(got2["data"]["content"].count("第1章 雪夜拔剑"), 1)

    def test_generate_fast_degrades_when_model_not_ready(self):
        with (
            mock.patch.object(engine_adapter, "any_model_configured", return_value=True),
            mock.patch.object(engine_adapter, "any_model_ready", return_value=False),
        ):
            res = writing_service.generate(
                voice="voice:tvoice-voice-card",
                project="剑道独尊",
                chapter_no=2,
                task="写第二章",
            )
        self.assertEqual(res["status"], "degraded")
        self.assertEqual(res["mode"], "no_model")


class TestDbTransactionsSseAndValidation(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="r2_dbv_"))
        self._iso = _isolation.isolate_paths(self._tmp)
        self._iso.__enter__()
        db.init_schema()
        db.apply_migrations()

    def tearDown(self):
        db.close()
        self._iso.__exit__(None, None, None)

    def test_begin_immediate_and_nested_savepoint_rollback(self):
        with db.tx() as outer_conn:
            self.assertTrue(outer_conn.in_transaction)
            outer_conn.execute(
                "INSERT INTO writing_notes (project, title, content, created_at, updated_at)"
                " VALUES ('p1', 'outer', 'keep', '2026-01-01', '2026-01-01')"
            )
            with self.assertRaises(RuntimeError):
                with db.tx() as inner_conn:
                    inner_conn.execute(
                        "INSERT INTO writing_notes (project, title, content, created_at, updated_at)"
                        " VALUES ('p1', 'inner', 'rollback_me', '2026-01-01', '2026-01-01')"
                    )
                    raise RuntimeError("inner abort")
            self.assertTrue(outer_conn.in_transaction)

        notes = writing_extra.list_notes("p1")
        self.assertEqual([n["title"] for n in notes], ["outer"])

    def test_adopt_book_to_project_atomic_rollback_on_mid_loop_failure(self):
        essence_service.create_or_update_book("eb1", "测试神作", genre="xuanhuan", platform="qidian")
        essence_service.create_asset("eb1", "outline", "大纲A", "大纲正文A")
        essence_service.create_asset("eb1", "character", "角色B", "角色正文B")

        orig_adopt = essence_service.adopt_asset_to_project
        calls = [0]

        def fail_second(*args, **kwargs):
            calls[0] += 1
            if calls[0] == 2:
                raise ServiceError("模拟中途失败", 500)
            return orig_adopt(*args, **kwargs)

        with mock.patch.object(essence_service, "adopt_asset_to_project", side_effect=fail_second):
            with self.assertRaises(ServiceError):
                essence_service.adopt_book_to_project("eb1", "atomic_proj")

        # 第一条已插入的 outline 必须随外层事务完整回滚
        self.assertEqual(writing_extra.list_outlines("atomic_proj"), [])
        self.assertEqual(writing_extra.list_characters("atomic_proj"), [])

    def test_dead_thread_connections_pruned_above_8(self):
        barrier = threading.Barrier(10)

        def worker():
            db.get_conn().execute("SELECT 1").fetchone()
            barrier.wait(timeout=5.0)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 10 个并发线程同时登记后均已退出（len(_conns) >= 10 > 8），主线程调用 get_conn 即刻回收死连接
        db.get_conn()
        with db._conns_lock:
            self.assertLessEqual(len(db._conns), 2)

    def test_sse_broker_caps_max_subscribers(self):
        b = sse.SseBroker(max_subscribers=4)
        qs = [b.subscribe() for _ in range(6)]
        self.assertEqual(len(b._subscribers), 4)
        b.publish({"status": "running"})
        self.assertTrue(qs[0].empty())
        self.assertTrue(qs[1].empty())
        self.assertFalse(qs[5].empty())

    def test_six_input_validation_500_to_400_cases(self):
        # 1) name_generator gender 非枚举 -> 400
        with self.assertRaises(ServiceError) as cm1:
            name_generator.generate(kind="character", gender="mars")
        self.assertEqual(cm1.exception.code, 400)

        # 2) PUT outlines/characters/notes 携带同名主键或非预期类型字段不抛 TypeError 500，脏类型抛 400
        o = writing_extra.create_outline("val_proj", "chapter", "初稿大纲")
        resp_upd, _ = router.dispatch(
            "PUT",
            f"/api/writing/outlines/{o['id']}",
            {"outline_id": 999, "title": "更新后标题"},
            {},
        )
        self.assertEqual(resp_upd["code"], 0)
        self.assertEqual(resp_upd["data"]["title"], "更新后标题")

        for method, path, bad_body in (
            ("PUT", f"/api/writing/outlines/{o['id']}", {"title": 123}),
            ("PUT", f"/api/writing/outlines/{o['id']}", {"sort_order": 1.5}),
            ("POST", "/api/writing/characters", {"project": "val_proj", "name": "甲", "extra": "not_dict"}),
            ("PUT", "/api/writing/characters/1", {"extra": ["not_dict"]}),
            ("PUT", "/api/writing/notes/1", {"content": {"bad": 1}}),
            # 3) POST /api/essence/analyze 非字符串参数
            ("POST", "/api/essence/analyze", {"text": "正文", "title": "书", "genre": 123}),
            ("POST", "/api/essence/analyze", {"text": "正文", "title": "书", "book_id": ["bad"]}),
            # 4) POST /api/essence/chains 非字符串参数
            ("POST", "/api/essence/chains", {"book_id": "eb", "clue_name": "线索", "hook_text": 123}),
            ("POST", "/api/essence/chains", {"book_id": "eb", "clue_name": "线索", "status": 99}),
            # 5) POST /api/essence/constitution/check 脏 rules / characters_forbidden
            ("POST", "/api/essence/constitution/check", {"text": "修仙测试", "rules": "not_list"}),
            ("POST", "/api/essence/constitution/check", {"text": "修仙测试", "rules": [{"terms": [123]}]}),
            ("POST", "/api/essence/constitution/check", {"text": "修仙测试", "rules": [{"terms": ["修仙"], "penalty": "high"}]}),
            ("POST", "/api/essence/constitution/check", {"text": "修仙测试", "characters_forbidden": {"主角": "not_list"}}),
        ):
            with self.subTest(path=path, body=bad_body):
                with self.assertRaises(ServiceError) as cm:
                    router.dispatch(method, path, bad_body, {})
                self.assertEqual(cm.exception.code, 400)

        # 6) model_service api_key 非字符串必须在 models_save 之前抛 400，不得污染 models.json
        before_models = model_service.list_models()["models"]
        with self.assertRaises(ServiceError) as cm_m:
            model_service.add_model({
                "id": "bad-key-model",
                "protocol": "openai",
                "base_url": "https://api.example.com/v1",
                "model_name": "gpt-test",
                "api_key": 12345,  # type: ignore[dict-item]
            })
        self.assertEqual(cm_m.exception.code, 400)
        after_models = model_service.list_models()["models"]
        self.assertEqual(before_models, after_models)


class TestExportersAndDeslopFixes(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="r2_exp_"))
        self._iso = _isolation.isolate_paths(self._tmp)
        self._iso.__enter__()
        db.init_schema()
        db.apply_migrations()

    def tearDown(self):
        db.close()
        self._iso.__exit__(None, None, None)

    def test_exporters_hardening_epub_shunn_docx_and_format_whitelist(self):
        proj = "StarlightSaga"
        cdir = config.NOVEL_DIR / proj / "chapters" / "arc-1"
        cdir.mkdir(parents=True, exist_ok=True)
        (cdir / "chapter-001.md").write_text(
            "# Chapter 1 The Awakening\n\nHe stepped into the rain-soaked street and drew his silver blade.",
            encoding="utf-8",
        )
        writing_extra.update_project_meta(
            proj,
            platform="royalroad",
            genre="progression",
            meta={"author": 'Jane "A." Doe\nInjected', "contact": "jane@example.com\r\nextra"},
        )

        # 不支持的导出格式 -> 400
        with self.assertRaises(ServiceError) as cm_fmt:
            writing_extra.export_project(proj, fmt="pdf")
        self.assertEqual(cm_fmt.exception.code, 400)

        # Shunn：英文词数统计 + 5 空格缩进 + 剥除 # + 换行清理
        shunn = writing_extra.export_project_shunn(proj)
        self.assertGreaterEqual(shunn["words"], 12)
        self.assertIn("\n     He stepped into the rain-soaked street", shunn["content"])
        self.assertNotIn("# CHAPTER", shunn["content"])
        self.assertNotIn("Injected\n\n", shunn["content"].splitlines()[0])

        # EPUB：英文语言标识 + 作者转义 + 剥除 Markdown #
        epub = writing_extra.export_project_epub(proj)
        raw_zip = base64.b64decode(epub["content_base64"])
        with zipfile.ZipFile(io.BytesIO(raw_zip), "r") as z:
            opf = z.read("OEBPS/content.opf").decode("utf-8")
            ch1 = z.read("OEBPS/chapter_001.xhtml").decode("utf-8")
            self.assertIn("<dc:language>en</dc:language>", opf)
            self.assertIn("&quot;A.&quot;", opf)
            self.assertIn('xml:lang="en"', ch1)
            self.assertIn("<h2>Chapter 1 The Awakening</h2>", ch1)

        # 全部章节为空/不可读时，docx / epub / shunn 均必须返回 400
        empty_proj = "EmptyReadableProj"
        edir = config.NOVEL_DIR / empty_proj / "chapters" / "arc-1"
        edir.mkdir(parents=True, exist_ok=True)
        (edir / "chapter-001.txt").write_text("   \n  ", encoding="utf-8")
        for fn in (
            writing_extra.export_project_docx,
            writing_extra.export_project_epub,
            writing_extra.export_project_shunn,
        ):
            with self.assertRaises(ServiceError) as cm_empty:
                fn(empty_proj)
            self.assertEqual(cm_empty.exception.code, 400)

    def test_platform_export_preserves_untitled_first_para_and_unique_numbers(self):
        bdir = self._tmp / "plat_book"
        bdir.mkdir(parents=True, exist_ok=True)
        # 无标题章节：首段就是带逗号句号的正文，绝不能被吞作标题
        (bdir / "第2章.txt").write_text("狂风卷着碎雪灌入破庙，少年猛地睁开双眼。\n\n火堆早已熄灭。", encoding="utf-8")
        (bdir / "番外_日常.txt").write_text("# 番外 闲暇\n\n院中落满了槐花，茶香袅袅。", encoding="utf-8")

        out = platform_service.export_book_for_platform("fanqie", str(bdir))
        self.assertEqual(out["total_chapters"], 2)
        nums = [c["num"] for c in out["chapters"]]
        self.assertEqual(len(nums), len(set(nums)), f"章号发生冲突: {nums}")
        self.assertIn("狂风卷着碎雪灌入破庙", out["chapters"][0]["full_chapter"])
        self.assertNotIn("# 番外", out["chapters"][1]["title"])

    def test_corrupt_chapter_overwrite_does_not_fail_get_chapter_words(self):
        proj = "corrupt_recover"
        cdir = config.NOVEL_DIR / proj / "chapters" / "arc-1"
        cdir.mkdir(parents=True, exist_ok=True)
        (cdir / "chapter-001.txt").write_bytes(b"\xff\xfe\x00\x01\x02")
        self.assertEqual(writing_extra.get_chapter_words(proj, 1), 0)
        res = writing_service.import_chapter(proj, 1, "修复后的全新第一章正文。" * 20)
        self.assertTrue(res["overwrote"])

    def test_deslop_false_positives_cursor_routing_and_sorting(self):
        # 1) 具象描写「眼底掠过霓虹倒影」不得误报
        r_img = deslop_service.analyze_deslop("她站在天桥上，眼底掠过霓虹倒影，风吹起衣角。")
        self.assertEqual(r_img["ai_score"], 0.0, r_img["issues"])
        self.assertEqual(r_img["verdict"], "NATURAL")

        # 2) 「带着」跨逗号子句不得误连到下一分句的「笑意」
        r_zhe = deslop_service.analyze_deslop("他推门进来，带着一身寒气，她脸上浮起笑意。")
        self.assertNotIn("dangling_zhe", {it["type"] for it in r_zhe["issues"]})

        # 3) 「不过…也不过…」「不仅…也不仅…」不得误判为 negation_pair
        r_neg = deslop_service.analyze_deslop(
            "不过是寻常试探，也不过是举手之劳。不仅实力强横，也不仅限于此。不少弟子到了，也不少长老观战。" * 2
        )
        self.assertNotIn("negation_pair", {it["type"] for it in r_neg["issues"]})

        # 4) 含有 1 个汉字的纯英文章节在 auto 模式下仍走英文引擎
        en_chap = (
            "Master 林 stood atop the obsidian tower. "
            "His courage was a testament to the ancient order, a beacon of hope in the storm. "
            "He walked through the dark hall and drew his sword."
        )
        r_en = deslop_service.analyze_deslop(en_chap, lang="auto")
        self.assertGreater(r_en["stats"]["word_count"], 20)
        self.assertIn("adverb_density", r_en["stats"])

        # 5) issues 按 (-weight, index) 排序，高危问题排在低权重口癖之前
        mixed = "就在这时，他不是畏惧强敌，而是等待致命一击的契机。"
        r_sort = deslop_service.analyze_deslop(mixed)
        weights = [it["weight"] for it in r_sort["issues"]]
        self.assertEqual(weights, sorted(weights, reverse=True))


if __name__ == "__main__":
    unittest.main()
