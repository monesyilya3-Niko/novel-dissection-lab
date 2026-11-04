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

    def test_books_route_listed(self):
        """路由表必须包含 GET /api/books。"""
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


if __name__ == "__main__":
    unittest.main()
