"""隔离 E2E 脚本回归：数据目录、密钥排除与 dummy 配置。

只静态读取 scripts/e2e_isolated.sh 及其内嵌 JSON，不启动服务、不导入产品模块，
也不读取仓库或用户目录中的真实配置/密钥。
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "e2e_isolated.sh"


class TestE2EIsolatedScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = SCRIPT.read_text(encoding="utf-8")

    def test_selects_runnable_python_with_windows_alias_fallback(self) -> None:
        start = self.script.index("PYTHON_CMD=()")
        end = self.script.index('ROOT="$(cd', start)
        selection = self.script[start:end]

        self.assertIn("for candidate in python3 python", selection)
        self.assertIn("PYTHON_CMD=(py -3)", selection)
        self.assertIn("sys.version_info >= (3, 11)", selection)
        self.assertIn(">/dev/null 2>&1", selection)
        self.assertIn("可运行的 Python 3.11+", selection)

    def test_data_dir_exported_before_server_and_playwright(self) -> None:
        export = re.search(
            r'^export XUAN_DATA_DIR="\$WORK/data"$',
            self.script,
            re.MULTILINE,
        )
        mkdir = re.search(
            r'^mkdir -p "\$XUAN_DATA_DIR/config"$',
            self.script,
            re.MULTILINE,
        )
        self.assertIsNotNone(export, "必须显式 export XUAN_DATA_DIR，不能只给单个命令传环境变量")
        self.assertIsNotNone(mkdir, "必须创建独立的 data/config")

        server = self.script.index('"${PYTHON_CMD[@]}" -u - "$PORT"')
        playwright = self.script.index("npx playwright test")
        self.assertLess(export.start(), server, "XUAN_DATA_DIR 必须在服务启动前导出")
        self.assertLess(export.start(), playwright, "XUAN_DATA_DIR 必须在 Playwright 前导出")
        self.assertLess(mkdir.start(), server, "data/config 必须在服务启动前存在")

        rsync_end = self.script.index('"$ROOT/" "$WORK/"') + len('"$ROOT/" "$WORK/"')
        self.assertLess(rsync_end, mkdir.start(), "data/ 必须在 rsync --delete 之后初始化")

    def test_rsync_always_excludes_repository_secret_files(self) -> None:
        start = self.script.index("rsync -a --delete")
        end = self.script.index('"$ROOT/" "$WORK/"', start)
        rsync_block = self.script[start:end]
        unconditional = rsync_block.split('"${RSYNC_EXTRA[@]}"', 1)[0]

        self.assertIn("if command -v rsync", self.script)
        self.assertIn("--exclude='/config/.secrets.bin'", unconditional)
        self.assertIn("--exclude='/config/.secrets.json'", unconditional)
        self.assertIn("--delete", unconditional)

    def test_python_fallback_excludes_secrets_and_test_outputs(self) -> None:
        start = self.script.index("def ignore(directory:")
        end = self.script.index("\nPY\nfi", start)
        fallback = self.script[start:end]

        self.assertIn('current == root / "config"', fallback)
        self.assertIn('ignored.update({".secrets.bin", ".secrets.json"})', fallback)
        self.assertIn('ignored.update({"test-results", "playwright-report"', fallback)
        self.assertIn('os.environ["E2E_EMPTY_LIBRARY"] == "1"', fallback)
        self.assertIn('"gui/state"', fallback)

    def test_sandbox_config_contains_only_dummy_model_and_empty_secrets(self) -> None:
        match = re.search(
            r'cat >"\$XUAN_DATA_DIR/config/models\.json" <<\'JSON\'\n(.*?)\nJSON',
            self.script,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "沙箱必须预置 models.json")
        config = json.loads(match.group(1))

        self.assertEqual(config["version"], 1)
        self.assertEqual(set(config["models"]), {"e2e-isolated-dummy"})
        model = config["models"]["e2e-isolated-dummy"]
        self.assertEqual(model["protocol"], "openai")
        self.assertEqual(model["base_url"], "http://127.0.0.1:9")
        self.assertEqual(model["model_name"], "dummy")
        self.assertEqual(model["api_key_env"], "E2E_ISOLATED_DUMMY_API_KEY")
        self.assertEqual(set(config["roles"].values()), {"e2e-isolated-dummy"})
        self.assertTrue(config["routes"], "dummy 模型必须覆盖任务路由")
        self.assertTrue(set(config["routes"].values()) <= set(config["roles"]))

        server = self.script.index('"${PYTHON_CMD[@]}" -u - "$PORT"')
        dummy_key = self.script.index(
            'export E2E_ISOLATED_DUMMY_API_KEY="dummy-e2e-key"'
        )
        empty_secrets = self.script.index(
            "printf '{}\\n' >\"$XUAN_DATA_DIR/config/.secrets.json\""
        )
        self.assertLess(dummy_key, server, "dummy API key 必须在服务启动前设置")
        self.assertLess(empty_secrets, server, "空 secrets.json 必须在服务启动前预置")

    def test_script_never_references_real_user_data_directory(self) -> None:
        for marker in ("LOCALAPPDATA", "暮冬念春", "AppData", ".local/share"):
            self.assertNotIn(marker, self.script, f"隔离脚本不得引用真实用户数据目录: {marker}")
        self.assertNotIn("$ROOT/config/.secrets", self.script)
        self.assertNotIn("$HOME/.local", self.script)

    def test_service_launch_has_no_stray_heredoc_or_pid_assignment(self) -> None:
        launch = '"${PYTHON_CMD[@]}" -u - "$PORT"'
        self.assertEqual(self.script.count(launch), 1)
        self.assertEqual(self.script.count("SRV=$!"), 1)
        self.assertEqual(self.script.splitlines().count("PY"), 3)

    def test_dynamic_port_empty_library_and_cleanup_are_preserved(self) -> None:
        self.assertIn('PORT="${E2E_PORT:-$("${PYTHON_CMD[@]}" -c "import socket;', self.script)
        self.assertIn("s.bind(('127.0.0.1',0))", self.script)
        self.assertIn('ACTUAL_PORT="$(grep -o', self.script)
        self.assertIn(
            'E2E_BASE_URL="http://127.0.0.1:$ACTUAL_PORT" '
            'E2E_SERVER_ROOT="$WORK" npx playwright test "$@"',
            self.script,
        )

        empty_start = self.script.index('if [ "${E2E_EMPTY_LIBRARY:-0}" = "1" ]; then')
        empty_end = self.script.index("fi", empty_start)
        empty_block = self.script[empty_start:empty_end]
        for path in ("/corpus/", "/assets/", "/reports/", "/gui/state/"):
            self.assertIn(f"--exclude='{path}'", empty_block)

        self.assertIn("trap cleanup EXIT", self.script)
        cleanup_start = self.script.index("cleanup() {")
        cleanup_end = self.script.index("trap cleanup EXIT", cleanup_start)
        cleanup_block = self.script[cleanup_start:cleanup_end]
        self.assertIn("TerminateProcess(handle, 0)", cleanup_block)
        self.assertIn("WaitForSingleObject(handle, 0)", cleanup_block)
        self.assertIn("shutil.rmtree(work)", cleanup_block)
        self.assertNotIn('rm -rf "$WORK"', cleanup_block)


if __name__ == "__main__":
    unittest.main()
