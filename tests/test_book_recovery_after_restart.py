"""重启后必须能找回已导入的书（2026-11-04）。

背景：``_books_get`` 只查进程内 ``_BOOK_INDEX``。它是内存字典，重启后为空，
于是所有已导入的书一律 404「未导入（请先 import）」——断点续传彻底失效。

``books`` 表里一直有正确的 ``source_path``（``import_book`` 会 upsert 进去），
只是从来没人读它。现在内存未命中时回退查表。
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


class TestBookRecoveryAfterRestart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()
        from gui import db
        db.init_schema()
        from gui import config
        for d in (config.ASSETS_ROOT, config.NOVEL_DIR, config.REPORTS_DIR):
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    def _simulate_restart(self):
        """清空所有进程内缓存，等价于重启。"""
        from gui import services
        with services._books_lock:
            services._BOOKS.clear()
            services._BOOK_INDEX.clear()

    def test_book_survives_restart(self):
        from gui import services
        src = Path(self._tmp.name) / "重启书.txt"
        src.write_text("第1章\n\n" + "正文。" * 100, encoding="utf-8")
        bid = services.import_book(str(src))["book_id"]

        self._simulate_restart()
        book = services.get_book(bid)
        self.assertEqual(book["total_chapters"], 1)
        self.assertEqual(book["title"], "重启书")

    def test_chapter_readable_after_restart(self):
        from gui import services
        src = Path(self._tmp.name) / "重启书2.txt"
        src.write_text("第1章\n\n" + "正文。" * 100, encoding="utf-8")
        bid = services.import_book(str(src))["book_id"]

        self._simulate_restart()
        ch = services.get_chapter(bid, 1)
        self.assertIn("正文", ch["text"])

    def test_unknown_book_still_404(self):
        """表里没有的书必须保持 404，不能因为回退而变成 500。"""
        from gui import services
        from gui.services import ServiceError
        self._simulate_restart()
        with self.assertRaises(ServiceError) as ctx:
            services.get_book("从未导入过的书-00000000")
        self.assertEqual(ctx.exception.code, 404)

    def test_source_missing_on_disk_still_404(self):
        """表里有记录但源文件已删除时，回退不应崩，仍按未导入处理。"""
        from gui import services
        from gui.services import ServiceError
        src = Path(self._tmp.name) / "会消失的书.txt"
        src.write_text("第1章\n\n" + "正文。" * 100, encoding="utf-8")
        bid = services.import_book(str(src))["book_id"]
        src.unlink()

        self._simulate_restart()
        with self.assertRaises(ServiceError):
            services.get_book(bid)


if __name__ == "__main__":
    unittest.main()
