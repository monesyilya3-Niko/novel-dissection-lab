"""gui/server.py 直接执行兼容：`python3 gui/server.py`（不走 -m）必须能启动。

回归：曾报 ModuleNotFoundError: No module named 'gui'，已加仓库根 sys.path 自举。
本测试不继承 PYTHONPATH、从仓库外目录执行 --help，断言无导入错误且退出码 0。
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_ROOT = _TESTS_DIR.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_TESTS_DIR))

import _isolation  # noqa: E402


class ServerDirectRunTest(unittest.TestCase):
    def test_direct_run_help(self) -> None:
        tmp_data = Path(tempfile.mkdtemp(prefix="srv_help_"))
        try:
            env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
            env["XUAN_DATA_DIR"] = str(tmp_data)
            proc = subprocess.run(
                [sys.executable, str(_ROOT / "gui" / "server.py"), "--help"],
                cwd=tempfile.gettempdir(),
                env=env,
                capture_output=True,
                text=True,
                timeout=90,
            )
            self.assertNotIn("ModuleNotFoundError", proc.stderr, proc.stderr[-500:])
            self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
            self.assertIn("--no-browser", proc.stdout)
            self.assertFalse(
                (tmp_data / "logs" / "gui.log").exists(),
                "--help 不应提前初始化日志文件 gui.log",
            )
        finally:
            _isolation.remove_tree(tmp_data)


if __name__ == "__main__":
    unittest.main()
