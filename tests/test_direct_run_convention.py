"""测试脚手架约定回归：每个 tests/test_*.py 脱离仓库根目录必须能正常导入。

2026-10-03 实锤 5 例：test_writing_extra 等 4 个文件只把 tests/ 目录加入
sys.path、test_p2_validation 完全没处理 sys.path，直接 `python3 tests/test_xxx.py`
报 ModuleNotFoundError: gui。统一约定：测试文件必须自行把仓库根目录加入
sys.path（参考 test_writing_service.py），保证 run_tests.py 之外也能直跑。

实现：为每个测试文件起子进程执行 `import <模块>`（16 并发），子进程 cwd 为
临时目录且不继承 PYTHONPATH——只走模块顶层执行（含 sys.path 装配与 import），
不触发 `if __name__ == "__main__"`、不跑测试，快且无副作用。
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent


class DirectRunConventionTest(unittest.TestCase):
    def test_every_test_module_imports_without_repo_root_on_path(self):
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        tmpdir = tempfile.gettempdir()
        targets = [f for f in sorted(TESTS_DIR.glob("test_*.py"))
                   if f.name != Path(__file__).name]

        def _check(f: Path) -> str | None:
            # 复刻 `python3 tests/test_xxx.py` 的 sys.path[0]（脚本所在目录），
            # 但不给仓库根目录：能 import 才算直跑合格。
            # 子进程层面的意外（超时、启动失败）也转为失败条目，不抛错中断整批。
            code = (
                "import sys; "
                f"sys.path.insert(0, {str(TESTS_DIR)!r}); "
                f"import {f.stem}"
            )
            try:
                r = subprocess.run(
                    [sys.executable, "-c", code],
                    capture_output=True, text=True, timeout=60,
                    cwd=tmpdir, env=env,
                )
            except Exception as exc:  # noqa: BLE001 — 超时等一律记为该文件失败
                return f"{f.name}: subprocess failed: {type(exc).__name__}: {exc}"[:160]
            err = r.stderr or ""
            if (r.returncode != 0 or "ModuleNotFoundError" in err
                    or "ImportError" in err):
                last = err.strip().splitlines()
                return (f"{f.name}: exit={r.returncode} :: "
                        f"{(last[-1] if last else '')[:120]}")
            return None

        failures = []
        with ThreadPoolExecutor(max_workers=16) as pool:
            for bad in pool.map(_check, targets):
                if bad:
                    failures.append(bad)
        failures.sort()
        self.assertEqual(
            failures, [],
            "以下测试文件脱离仓库根目录后无法导入（直接运行会失败），"
            "请按 test_writing_service.py 的约定补 sys.path 装配：\n"
            + "\n".join(failures),
        )


    def test_unittest_main_block_is_last_statement(self):
        """`unittest.main()` 必须写在文件末尾（2026-11-05 实测 12 例）。

        现象：文件先写了 ``if __name__ == "__main__": unittest.main()``，
        后来又补了新的测试类。discovery 走 ``run_tests.py`` 不受影响，
        但 ``python tests/test_xxx.py`` 直接运行时，main() 在补的类定义
        **之前**就执行了 —— 那些用例永远不会被登记，直跑静默少跑。

        实测差额：test_pipeline 直跑 28 / discovery 38。
        """
        import ast

        offenders = []
        for f in sorted(TESTS_DIR.glob("test_*.py")):
            if f.name == Path(__file__).name:
                continue
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError as exc:
                offenders.append(f"{f.name}: 语法错误 {exc}")
                continue
            main_line = None
            for node in tree.body:
                if not isinstance(node, ast.If):
                    continue
                test = node.test
                is_main_guard = (
                    isinstance(test, ast.Compare)
                    and isinstance(test.left, ast.Name)
                    and test.left.id == "__name__"
                )
                if not is_main_guard or not node.body:
                    continue
                call = ast.unparse(node.body[0])
                if "unittest" in call:
                    main_line = node.lineno
                    break
            if main_line is None:
                continue
            after = [
                n.lineno for n in tree.body
                if isinstance(n, (ast.ClassDef, ast.FunctionDef))
                and n.lineno > main_line
            ]
            if after:
                offenders.append(
                    f"{f.name}: unittest.main() 在第 {main_line} 行，"
                    f"其后还有 {len(after)} 个定义（行 {after[:5]}）→ 直接运行会漏跑"
                )
        self.assertEqual(
            offenders, [],
            "以下测试文件的 unittest.main() 不在文件末尾，直接运行会静默漏跑用例。"
            "请把 `if __name__ == \"__main__\": unittest.main()` 移到文件最后：\n"
            + "\n".join(offenders),
        )

    def test_every_script_module_imports_cleanly(self):
        scripts_dir = TESTS_DIR.parent / "scripts"
        targets = [f for f in sorted(scripts_dir.glob("*.py"))
                   if not f.name.startswith("__")]
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        tmpdir = tempfile.gettempdir()

        def _check_script(f: Path) -> str | None:
            code = (
                "import sys; "
                f"sys.path.insert(0, {str(TESTS_DIR.parent)!r}); "
                f"from scripts import {f.stem}"
            )
            try:
                r = subprocess.run(
                    [sys.executable, "-c", code],
                    capture_output=True, text=True, timeout=60,
                    cwd=tmpdir, env=env,
                )
            except Exception as exc:
                return f"{f.name}: subprocess failed: {type(exc).__name__}: {exc}"[:160]
            err = r.stderr or ""
            if r.returncode != 0 or "ModuleNotFoundError" in err or "ImportError" in err:
                last = err.strip().splitlines()
                return (f"{f.name}: exit={r.returncode} :: "
                        f"{(last[-1] if last else '')[:120]}")
            return None

        failures = []
        with ThreadPoolExecutor(max_workers=16) as pool:
            for bad in pool.map(_check_script, targets):
                if bad:
                    failures.append(bad)
        failures.sort()
        self.assertEqual(
            failures, [],
            "以下 scripts 脚本在独立子进程导入时失败（存在兄弟模块导入缺陷）：\n"
            + "\n".join(failures),
        )


if __name__ == "__main__":
    unittest.main()
