"""项目名必须能真正建出目录（2026-11-04）。

背景：``_sanitize_project`` 此前只拦 ``/ \ .. 控制字符`` 与 ``default``。
实测这些名字**通过校验但建目录必失败**，用户拿到 500 而不是可读的 400：

    CON / PRN / AUX / NUL / COM1…    Windows 保留设备名 → WinError 267
    项目:测试（冒号）                 → WinError 267 目录名称无效
    项目*名（星号）                   → WinError 123 语法不正确
    300 字符的长名                    → WinError 3 路径找不到

对照组：``style_service._sanitize_name`` 用白名单正则 + 长度上限，是正确写法。
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui.services import ServiceError  # noqa: E402
from gui.writing_service import _sanitize_project  # noqa: E402


class TestProjectNameValidation(unittest.TestCase):
    def test_valid_names_pass(self):
        for name in ("正常项目", "My Project", "第1卷", "my-novel_v2", "  空格  "):
            with self.subTest(name=name):
                self.assertTrue(_sanitize_project(name))

    def test_windows_reserved_names_rejected(self):
        for name in ("CON", "con", "PRN", "AUX", "NUL", "COM1", "LPT9", "con.txt"):
            with self.subTest(name=name):
                with self.assertRaises(ServiceError):
                    _sanitize_project(name)

    def test_illegal_characters_rejected(self):
        for name in ("项目:测试", "项目*名", "a<b", "a>b", "a|b", 'a"b', "a?b"):
            with self.subTest(name=name):
                with self.assertRaises(ServiceError):
                    _sanitize_project(name)

    def test_too_long_rejected(self):
        with self.assertRaises(ServiceError):
            _sanitize_project("a" * 300)

    def test_trailing_dot_rejected(self):
        """Windows 会静默吃掉结尾的点，导致目录名与记录不一致。"""
        with self.assertRaises(ServiceError):
            _sanitize_project("项目.")

    def test_path_separators_still_rejected(self):
        for name in ("../escape", "a/b", "a" + chr(92) + "b", "a..b"):
            with self.subTest(name=name):
                with self.assertRaises(ServiceError):
                    _sanitize_project(name)

    def test_accepted_name_actually_creates_directory(self):
        """端到端：通过校验的名字必须真能建出目录（这是本测试的核心）。"""
        with tempfile.TemporaryDirectory() as td:
            for name in ("正常项目", "My Project", "第1卷", "my-novel_v2"):
                with self.subTest(name=name):
                    (Path(td) / _sanitize_project(name)).mkdir()

    def test_rejected_names_would_have_failed_on_disk(self):
        """反向确认：被拒的名字确实建不出目录（防止校验变成纯粹的形式主义）。"""
        with tempfile.TemporaryDirectory() as td:
            for name in ("CON", "项目:测试", "项目*名"):
                with self.subTest(name=name):
                    with self.assertRaises(OSError):
                        (Path(td) / name).mkdir()


if __name__ == "__main__":
    unittest.main()
