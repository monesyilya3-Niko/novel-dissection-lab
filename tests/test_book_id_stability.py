"""book_id 必须对同一文件稳定（2026-11-04）。

背景：``book_id_from_title`` 此前直接 md5 源路径字符串，看起来相同的一个文件
换个写法就是一本"新书"。实测五种写法五个 id：

    C:/books/a.txt、C:\\books\\a.txt、C:\\books\\.\\a.txt、
    C:\\books\\A.TXT、C:\\BOOKS\\a.txt

后果不是报错，而是用户第二次导入同一本书时，之前跑完的分析、已生成资产、
报告全部挂在旧 book_id 下，界面上表现为"书不见了"。

修复：哈希前规范化路径（分隔符、冗余分隔符与 ``.`` 段、大小写）。
不做 ``resolve()``——它会跟随符号链接并依赖文件是否存在，导入后移动源文件
会让 id 漂移，比不解析更糟。
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

from gui.state_store import (  # noqa: E402
    _normalize_source_path,
    book_id_from_title,
    legacy_book_id_from_title,
)


class TestBookIdStability(unittest.TestCase):
    def test_same_file_different_spellings_same_id(self):
        """同一文件的不同路径写法必须得到同一个 book_id。"""
        variants = [
            "C:\\books\\a.txt",
            "C:/books/a.txt",
            "C:\\books\\.\\a.txt",
            "C:\\books\\A.TXT",
            "C:\\BOOKS\\a.txt",
            "c:/books//a.txt",
        ]
        ids = {book_id_from_title("我的书", p) for p in variants}
        self.assertEqual(len(ids), 1, f"同一文件的写法生成了多个 id：{ids}")

    def test_different_files_get_different_ids(self):
        a = book_id_from_title("书", "C:/books/a.txt")
        b = book_id_from_title("书", "C:/books/b.txt")
        c = book_id_from_title("另一本书", "C:/books/a.txt")
        self.assertNotEqual(a, b, "不同文件不应共用 id")
        self.assertNotEqual(a, c, "不同书名不应共用 id")

    def test_id_shape(self):
        bid = book_id_from_title("我的 书/名", "C:/a.txt")
        self.assertRegex(bid, r"^[\w-]+-[0-9a-f]{8}$",
                         f"book_id 形状异常：{bid}")

    def test_normalize_handles_empty(self):
        self.assertEqual(_normalize_source_path(""), "")
        self.assertEqual(_normalize_source_path(None), "")

    def test_normalize_is_idempotent(self):
        once = _normalize_source_path("C:\\Books\\.\\a.txt")
        self.assertEqual(_normalize_source_path(once), once)

    def test_empty_path_still_produces_id(self):
        """路径为空也不能崩（历史数据/异常调用）。"""
        self.assertTrue(book_id_from_title("书", ""))


class TestLegacyBookIdCompatibility(unittest.TestCase):
    """规则变更前的旧 book_id 必须仍能被找回（2026-11-04）。

    规范化路径改变了 id，若不做兼容，用户升级后所有已导入的书都会失联
    （实测生产库 12 本真实导入的书 id 全部变化）。
    """

    @classmethod
    def setUpClass(cls):
        # 用项目标准的 _isolation：它会连带重定向 DB_PATH / LOCK_PATH 等派生常量
        # （手工 patch STATE_ROOT 带不动导入期快照，守卫 test_config_isolation 会拦）
        cls._tmp = tempfile.TemporaryDirectory()
        cls._iso = _isolation.isolate_paths(Path(cls._tmp.name))
        cls._iso.__enter__()
        from gui import config
        config.STATE_JSON_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)
        cls._tmp.cleanup()

    @staticmethod
    def _resolve_branch(title: str, src: str) -> str:
        """复刻 import_book 的 id 选择逻辑。"""
        from gui import state_store
        new_id = state_store.book_id_from_title(title, src)
        old_id = state_store.legacy_book_id_from_title(title, src)
        if (new_id != old_id
                and state_store.resolve_state_path(new_id) is None
                and state_store.resolve_state_path(old_id) is not None):
            return old_id
        return new_id

    def test_legacy_id_differs_from_new(self):
        title, src = "旧书", "C:\\books\\a.txt"
        self.assertNotEqual(book_id_from_title(title, src),
                            legacy_book_id_from_title(title, src))

    def test_resolve_finds_legacy_state_file(self):
        from gui import config, state_store
        title, src = "旧书B", "C:\\books\\b.txt"
        old_id = state_store.legacy_book_id_from_title(title, src)
        (config.STATE_JSON_DIR / f"gui_state_{old_id}.json").write_text(
            "{}", encoding="utf-8")
        self.assertIsNotNone(state_store.resolve_state_path(old_id))
        new_id = state_store.book_id_from_title(title, src)
        self.assertIsNone(state_store.resolve_state_path(new_id),
                          "新 id 不该凭空找到状态文件")

    def test_import_prefers_legacy_when_only_legacy_exists(self):
        from gui import config, state_store
        title, src = "旧书C", "C:\\books\\c.txt"
        old_id = state_store.legacy_book_id_from_title(title, src)
        (config.STATE_JSON_DIR / f"gui_state_{old_id}.json").write_text(
            "{}", encoding="utf-8")
        self.assertEqual(self._resolve_branch(title, src), old_id)

    def test_new_book_uses_new_id(self):
        title, src = "全新书", "C:\\books\\new.txt"
        self.assertEqual(self._resolve_branch(title, src),
                         book_id_from_title(title, src))


if __name__ == "__main__":
    unittest.main()
