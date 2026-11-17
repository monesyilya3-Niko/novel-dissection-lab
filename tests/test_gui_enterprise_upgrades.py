"""GUI 后端企业级加固与无模型离线闭环回归测试。

覆盖：
1. server.py：DNS Rebinding 非法 Host 拦截、跨站 GET Origin 拦截、安全响应头、OPTIONS 预检
2. model_service.py：test_model 在 ok=False（如 HTTP 402）时返回 success=False 与错误原文
3. services.py：HTTP 402/401 熔断并生成 AI 接管任务包、全批失败不伪报 done、POST /api/analyze/offline
4. essence_service.py：0005 迁移后 reveal_chapter 落库持久化（刷新不丢失）
5. advanced_service.py：Windows 盘符注入 `D:evil` 拦截、delete_asset 清理 SQLite 与缓存
6. admin.py：running 状态书 409 禁删、不存在 book_id 不泄漏 _delete_locks、整书资产与报告同步清理
7. writing_service.py：无声线卡纯题材/文风卡注入 + 项目上下文拼装、已存章节列举与读取、生成遇 402 回吐 Prompt
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import time
import unittest
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

import _isolation  # noqa: E402

from gui import (  # noqa: E402
    admin,
    advanced_service,
    config,
    db,
    essence_service,
    model_service,
    router,
    services,
    writing_extra,
    writing_service,
)
from gui.server import _Handler  # noqa: E402
from gui.services import ServiceError  # noqa: E402


def _make_dummy_handler(
    method: str = "GET",
    path: str = "/api/overview",
    headers: dict[str, str] | None = None,
    bind_host: str = "127.0.0.1",
    handshake_token: str | None = None,
) -> tuple[_Handler, io.BytesIO, list[tuple[int, list[tuple[str, str]]]]]:
    h = _Handler.__new__(_Handler)
    h.command = method
    h.path = path
    h.request_version = "HTTP/1.1"
    h.client_address = ("127.0.0.1", 54321)
    h.server = SimpleNamespace(
        server_address=(bind_host, 8000),
        handshake_token=handshake_token,
    )
    msg = Message()
    for k, v in (headers or {}).items():
        msg[k] = v
    h.headers = msg
    wbuf = io.BytesIO()
    h.wfile = wbuf
    h.rfile = io.BytesIO(b"")
    recorded: list[tuple[int, list[tuple[str, str]]]] = []
    cur_status = [200]
    cur_headers: list[tuple[str, str]] = []

    def _send_response(code: int, _msg: str | None = None) -> None:
        cur_status[0] = code

    def _send_header(k: str, v: str) -> None:
        cur_headers.append((k, v))

    def _end_headers() -> None:
        recorded.append((cur_status[0], list(cur_headers)))

    h.send_response = _send_response  # type: ignore[method-assign]
    h.send_header = _send_header  # type: ignore[method-assign]
    h.end_headers = _end_headers  # type: ignore[method-assign]
    return h, wbuf, recorded


class TestServerSecurityHardening(unittest.TestCase):
    def test_dns_rebinding_evil_host_blocked_403(self):
        h, _w, rec = _make_dummy_handler(
            "GET", "/api/overview", headers={"Host": "evil.attacker.com:8000"}
        )
        self.assertFalse(h._check_auth())
        self.assertEqual(rec[0][0], 403)

    def test_cross_origin_get_blocked_403(self):
        h, _w, rec = _make_dummy_handler(
            "GET",
            "/api/books",
            headers={"Host": "127.0.0.1:8000", "Origin": "https://evil.example.com"},
        )
        self.assertFalse(h._check_auth())
        self.assertEqual(rec[0][0], 403)

    def test_same_host_origin_and_security_headers(self):
        h, _w, rec = _make_dummy_handler(
            "OPTIONS",
            "/api/models",
            headers={"Host": "localhost:8000", "Origin": "http://localhost:5173"},
        )
        h.do_OPTIONS()
        status, hdrs = rec[0]
        hdr_map = {k.lower(): v for k, v in hdrs}
        self.assertEqual(status, 204)
        self.assertEqual(hdr_map.get("access-control-allow-origin"), "http://localhost:5173")
        self.assertEqual(hdr_map.get("x-content-type-options"), "nosniff")
        self.assertEqual(hdr_map.get("x-frame-options"), "DENY")
        self.assertEqual(hdr_map.get("referrer-policy"), "no-referrer")


class TestModelConnectivityTruthfulness(unittest.TestCase):
    def test_http_402_reported_as_failure_not_success(self):
        err_msg = "HTTP 402: SUBSCRIPTION_REQUIRED - API key expired"
        with mock.patch(
            "gui.model_service.engine_adapter.model_test",
            return_value={"ok": False, "error": err_msg},
        ):
            res = model_service.test_model("ds-main")
        self.assertFalse(res["success"])
        self.assertEqual(res["error"], err_msg)
        self.assertFalse(res["result"]["ok"])


class TestGuiBackendEnterpriseUpgrades(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="gui_ent_")
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()
        db.init_schema()
        db.apply_migrations()

    @classmethod
    def tearDownClass(cls):
        db.close()
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    def setUp(self):
        services._BOOKS.clear()
        services._runtime.clear()

    def test_analysis_circuit_breaker_on_402_and_offline_takeover(self):
        book_fp = config.CORPUS_DIR / "breaker_novel.txt"
        config.CORPUS_DIR.mkdir(parents=True, exist_ok=True)
        chapters_txt = "\n\n".join(
            f"第{i}章 风起\n" + ("少年握紧铁剑，冷风掠过庭院。「你敢拦我？」他低声喝道。" * 40)
            for i in range(1, 7)
        )
        book_fp.write_text(chapters_txt, encoding="utf-8")
        imp = services.import_book(str(book_fp))
        bid = imp["book_id"]

        calls = []

        def _fail_402(*_a, **_kw):
            calls.append(1)
            raise RuntimeError("HTTP 402: SUBSCRIPTION_REQUIRED (key expired)")

        with (
            mock.patch.object(services.engine_adapter, "any_model_configured", return_value=True),
            mock.patch.object(services.engine_adapter, "is_known_genre", return_value=True),
            mock.patch.object(services.engine_adapter, "run_batch", side_effect=_fail_402),
        ):
            services.start_analysis(bid, "xianxia")
            deadline = time.time() + 5.0
            while time.time() < deadline:
                st = services.get_status(bid)
                if st["status"] in ("error", "done"):
                    break
                time.sleep(0.05)

        st = services.get_status(bid)
        self.assertEqual(st["status"], "error", "402 必须置为 error 而非伪装成 done")
        self.assertEqual(len(calls), 1, "遇到 402 鉴权/订阅错误应在首批次立即熔断")
        self.assertIn("402", st["last_error"])
        self.assertTrue(st["takeover_guide_path"])
        self.assertTrue(Path(st["takeover_guide_path"]).is_file())

        # 验证离线拆书路由 POST /api/analyze/offline
        with mock.patch.object(services.engine_adapter, "is_known_genre", return_value=True):
            resp, _ = router.dispatch(
                "POST", "/api/analyze/offline", {"book_id": bid, "genre": "xianxia"}, {}
            )
        self.assertEqual(resp["code"], 0)
        data = resp["data"]
        self.assertEqual(data["total_chapters"], 6)
        self.assertIn("AI接管任务.md", data["guide_path"])
        self.assertIn("会话内智能接管任务", data["guide_markdown"])

    def test_essence_chain_reveal_chapter_persists_across_reload(self):
        essence_service.create_or_update_book("eb_rev", "测试精读书", total_chapters=50, total_chars=120000)
        resp, _ = router.dispatch(
            "POST",
            "/api/essence/chains",
            {
                "bookId": "eb_rev",
                "title": "残玉身世",
                "plant_chapter": 2,
                "revealChapter": 19,
                "climax_chapter": 40,
                "description": "开篇玉佩微光",
            },
            {},
        )
        self.assertEqual(resp["code"], 0)
        self.assertEqual(resp["data"]["revealChapter"], 19)

        # 重新查询数据库（模拟刷新页面），不得退回 (2 + 40) // 2 = 21
        reloaded = essence_service.list_chains("eb_rev")
        self.assertEqual(len(reloaded), 1)
        self.assertEqual(reloaded[0]["revealChapter"], 19)

    def test_asset_colon_blocked_and_delete_cleans_sqlite(self):
        with self.assertRaises(ServiceError) as cm:
            advanced_service.create_asset("D:evil_escape", "voice", {"meta": {"kind": "test"}})
        self.assertEqual(cm.exception.code, 400)

        created = advanced_service.create_asset(
            "ent-clean-voice-card",
            "voice",
            {"meta": {"title": "测试", "genre": "xianxia"}},
        )
        self.assertTrue(created["created"])
        row_before = db.get_conn().execute(
            "SELECT COUNT(*) AS n FROM assets WHERE asset_key LIKE '%ent-clean-voice-card%'"
        ).fetchone()
        self.assertEqual(row_before["n"], 1)

        advanced_service.delete_asset("voice", "ent-clean-voice-card")
        row_after = db.get_conn().execute(
            "SELECT COUNT(*) AS n FROM assets WHERE asset_key LIKE '%ent-clean-voice-card%'"
        ).fetchone()
        self.assertEqual(row_after["n"], 0, "软删移入回收站后必须同步移除 SQLite 幽灵索引行")

    def test_admin_delete_book_running_409_and_no_lock_leak(self):
        admin.ensure_initialized()
        locks_before = len(admin._delete_locks)
        with self.assertRaises(ServiceError) as cm404:
            admin.delete_book("never_existed_book_999", "admin", "127.0.0.1")
        self.assertEqual(cm404.exception.code, 404)
        self.assertEqual(len(admin._delete_locks), locks_before, "404 不得在 _delete_locks 残留锁对象")

        # running 状态（真实分析中状态名）必须 409 拦截
        config.STATE_JSON_DIR.mkdir(parents=True, exist_ok=True)
        st_fp = config.STATE_JSON_DIR / "gui_state_runbook.json"
        st_fp.write_text(json.dumps({"book_id": "runbook", "status": "running"}), encoding="utf-8")
        with self.assertRaises(ServiceError) as cm409:
            admin.delete_book("runbook", "admin", "127.0.0.1")
        self.assertEqual(cm409.exception.code, 409)

        # 改为 done 后可正常删除，并连带清理整书卡与报告
        st_fp.write_text(json.dumps({"book_id": "runbook", "status": "done"}), encoding="utf-8")
        vc_fp = config.ASSETS_ROOT / "runbook-voice-card.json"
        vc_fp.parent.mkdir(parents=True, exist_ok=True)
        vc_fp.write_text("{}", encoding="utf-8")
        rpt_fp = config.REPORTS_DIR / "runbook-拆书报告.md"
        rpt_fp.parent.mkdir(parents=True, exist_ok=True)
        rpt_fp.write_text("# 报告", encoding="utf-8")

        del_res = admin.delete_book("runbook", "admin", "127.0.0.1")
        self.assertEqual(del_res["status"], "ok")
        self.assertFalse(vc_fp.exists())
        self.assertFalse(rpt_fp.exists())

    def test_writing_inject_without_voice_and_chapter_read_and_402_prompt_recovery(self):
        # 1. 创建写作项目 + 大纲 + 人物 + 落盘章节
        writing_service.create_project("剑起长夜")
        writing_extra.create_outline("剑起长夜", kind="chapter", title="第1章 寒潭断剑", summary="主角于寒潭拾得残剑")
        writing_extra.create_character("剑起长夜", name="陆沉", role="主角", description="冷峻果决")
        prose = {
            "meta": {"id": "genre-xianxia", "kind": "genre-prose-card", "genre": "xianxia"},
            "language_rules": {"sentence": "短句凌厉"},
            "prose": {"imagery": ["寒霜"]},
            "structure": {},
            "commercial": {},
        }
        (config.ASSETS_ROOT / "genre-prose-card-genre-xianxia.json").write_text(
            json.dumps(prose, ensure_ascii=False), encoding="utf-8"
        )

        # 无 voice 卡、仅靠 prose_card + 项目上下文组装完整 Prompt
        inj = writing_service.inject(
            voice="",
            prose_card="prose_card:genre-prose-card-genre-xianxia",
            project="剑起长夜",
            chapter_no=1,
            task_outline="寒潭潜入，拔出残剑触发禁制",
        )
        self.assertIn("prose_card", inj["injected_kinds"])
        self.assertIn("陆沉", inj["prompt"])
        self.assertIn("第1章 寒潭断剑", inj["prompt"])
        self.assertIn("寒潭潜入", inj["prompt"])

        # 2. 保存章节并通过新增 REST 路由读取列表与全文（解决刷新丢稿）
        vc = {
            "meta": {"title": "剑道", "genre": "xianxia", "confidence": 0.9},
            "narration": {"pov": "third_limited"},
            "dialogue": {"character_voices": []},
            "emotion_handling": {"mode": "动作外化"},
            "banned": {"never_used_words": []},
        }
        (config.ASSETS_ROOT / "jiandao-voice-card.json").write_text(
            json.dumps(vc, ensure_ascii=False), encoding="utf-8"
        )
        writing_service.import_chapter(
            project="剑起长夜",
            chapter_no=1,
            content="第1章 寒潭断剑\n\n寒风卷过潭面，陆沉伸手握住锈迹斑斑的剑柄。" * 20,
            voice="voice:jiandao-voice-card",
        )
        list_resp, _ = router.dispatch("GET", "/api/writing/projects/剑起长夜/chapters", {}, {})
        self.assertEqual(list_resp["code"], 0)
        self.assertEqual(len(list_resp["data"]["chapters"]), 1)
        self.assertEqual(list_resp["data"]["chapters"][0]["chapter_no"], 1)

        ch_resp, _ = router.dispatch("GET", "/api/writing/projects/剑起长夜/chapters/1", {}, {})
        self.assertEqual(ch_resp["code"], 0)
        self.assertIn("陆沉伸手握住", ch_resp["data"]["content"])

        # 3. 外部模型抛 402 时，写作任务在 error 状态下仍保留组装好的 prompt 与 AI接管写作任务.md
        with (
            mock.patch.object(writing_service.engine_adapter, "any_model_configured", return_value=True),
            mock.patch.object(
                writing_service.engine_adapter,
                "llm_chat",
                side_effect=RuntimeError("HTTP 402: SUBSCRIPTION_REQUIRED"),
            ),
        ):
            gen = writing_service.generate(
                voice="voice:jiandao-voice-card",
                project="剑起长夜",
                chapter_no=2,
                task="第二章试剑",
            )
            tid = gen["task_id"]
            deadline = time.time() + 5.0
            while time.time() < deadline:
                ts = writing_service.task_state(tid)
                if ts["status"] in ("error", "done"):
                    break
                time.sleep(0.05)
        ts = writing_service.task_state(tid)
        self.assertEqual(ts["status"], "error")
        self.assertTrue(ts.get("prompt"))
        self.assertIn("内置智能接管写作任务", ts.get("guide_markdown", ""))


if __name__ == "__main__":
    unittest.main()
