"""已导入书目端点与导入登记（2026-11-03）。

背景：普通工作台此前没有任何「我的书」入口——import_book 只写内存 LRU
与状态文件，books 表要等下一次 migrate 全量扫描才出现这本书；导入后
刷新页面前端也不知道 book_id，书就"找不回来"了。
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

import _isolation  # noqa: E402


class TestBooksEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()
        # 隔离后的 DB 是空的，先建 schema（否则 _db_ready() 为 False，
        # get_books 返回空列表，测不出登记是否成功）
        from gui import db
        db.init_schema()

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    def test_import_registers_book(self):
        """导入后必须立刻出现在 books 表里（不必等 migrate）。"""
        from gui import db, services
        src = Path(self._tmp.name) / "登记.txt"
        src.write_text("第1章 开端\n\n" + "正文内容。" * 200, encoding="utf-8")
        result = services.import_book(str(src))
        bid = result["book_id"]
        rows = db.get_books(book_id=bid)
        self.assertEqual(len(rows), 1, "导入后 books 表没有这本书")
        self.assertEqual(rows[0]["status"], "idle")

    def test_analysis_done_syncs_books_status(self):
        """分析完成后 books.status 必须推进到 done（2026-11-05 修）。

        /api/books 的 status 取自 SQLite，而分析完成原先只改状态文件——
        全库没有任何代码把 books.status 从导入时的 "idle" 推进到 "done"。
        实测 db.get_books(status='done') 恒为 0 条，用户看到拆完的书仍标「待拆」。
        """
        from gui import db, services
        src = Path(self._tmp.name) / "状态同步.txt"
        src.write_text("第1章 开端\n\n" + "正文内容。" * 200, encoding="utf-8")
        bid = services.import_book(str(src))["book_id"]
        self.assertEqual(db.get_books(book_id=bid)[0]["status"], "idle")

        services._sync_book_status(bid, "done")
        self.assertEqual(db.get_books(book_id=bid)[0]["status"], "done",
                         "分析完成后 books.status 必须变成 done")

    def test_status_endpoint_exposes_last_error(self):
        """get_status 必须回传 last_error（2026-11-05）。

        否则用户只看到 status="error"，不知道错在哪。
        """
        from gui import services, state_store
        bid = "err-book"
        state_store.save_state(state_store.new_state(bid, "错误书"))
        with state_store.update_state(bid) as st:
            st["status"] = "error"
            st["last_error"] = "未配置外部模型"
        out = services.get_status(bid)
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["last_error"], "未配置外部模型")

    def test_books_route_listed(self):
        from gui import router
        paths = [p.pattern for m, p, _f in router.ROUTES if m == "GET"]
        self.assertTrue(any("api/books" in p for p in paths),
                        "缺少 GET /api/books 端点")

    def test_endpoint_returns_shape(self):
        from gui import router
        handler = next(f for m, p, f in router.ROUTES
                       if m == "GET" and p.pattern.endswith("/api/books$"))
        out = handler({}, {})
        data = out["data"]
        self.assertIn("total", data)
        self.assertIn("books", data)
        self.assertIsInstance(data["books"], list)
        for b in data["books"]:
            for key in ("book_id", "title", "status"):
                self.assertIn(key, b)

    def test_status_filter_validates_type(self):
        from gui import router
        from gui.services import ServiceError
        handler = next(f for m, p, f in router.ROUTES
                       if m == "GET" and p.pattern.endswith("/api/books$"))
        with self.assertRaises(ServiceError):
            handler({"status": 123}, {})


class TestReportErrorSurface(unittest.TestCase):
    """报告生成失败的原因必须能通过 API 拿到（2026-11-05）。

    铁律二未过 / 组装异常时后端会写 state["report_error"] 并广播
    status="report_error"，但：
    - 前端完全不处理 report_error 事件
    - /api/status 也从不返回该字段
    于是用户只看到「报告未生成」，不知道是字数不到一万还是组装失败。
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._iso = _isolation.isolate_paths(Path(self._tmp.name))
        self._iso.__enter__()
        from gui import db
        db.init_schema()

    def tearDown(self):
        self._iso.__exit__(None, None, None)
        self._tmp.cleanup()

    def test_status_exposes_report_error(self):
        from gui import services, state_store
        bid = "rpt-err-book"
        state_store.save_state(state_store.new_state(bid, "报告失败"))
        with state_store.update_state(bid) as st:
            st["status"] = "done"
            st["report_error"] = "铁律二未通过：合计 8000 字 < 10000"
        out = services.get_status(bid)
        self.assertEqual(out.get("report_error"),
                         "铁律二未通过：合计 8000 字 < 10000")

    def test_report_error_empty_when_absent(self):
        from gui import services, state_store
        bid = "rpt-ok-book"
        state_store.save_state(state_store.new_state(bid, "正常"))
        out = services.get_status(bid)
        self.assertEqual(out.get("report_error"), "")


if __name__ == "__main__":
    unittest.main()
