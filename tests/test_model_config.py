#!/usr/bin/env python3
"""
model_config 模块全维单元测试与导入回归测试 — 纯标准库 unittest，零第三方依赖

测试覆盖：
1. TestModelConfigImport: 模块加载、secret_store 模块级导出、llm_client 依赖符号与预设完整性
2. TestMaskHelper: API Key 掩码防护（空/短字符串/长字符串/非字符串容错）
3. TestCmdPresets: 预设列表展示与价格说明
4. TestCmdList: 空配置提示、多模型列表、角色反向绑定、环境变量/密钥库状态展示
5. TestCmdRoutes: 任务到角色到模型的三级路由表输出
6. TestCmdAdd: 预设合法性校验、同名模型防误触与 --force 覆盖、必填项校验、首模型角色绑定、密钥录入与跳过
7. TestCmdKey: 模型存在性校验、空 Key 拦截、密钥更新保存
8. TestCmdTest: 无模型检测、单模型/全模型测试分发、测试通过与失败退出码
9. TestCmdRole: 模型存在性校验、角色绑定更新与持久化
10. TestCmdRoute: 未知任务防御、路由关系更新与持久化
11. TestCmdFallback: 主模型与备用模型存在性校验、备用链配置与清空
12. TestCmdRemove: 模型删除、角色级联解绑、密钥同步销毁
13. TestMainDispatch: CLI main(argv) 空参数帮助与各子命令分发
"""

import importlib.util
import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _load(name: str):
    """按文件名从 scripts/ 动态加载模块（模块名与文件名一致）。"""
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


model_config = _load("model_config")


class TestModelConfigImport(unittest.TestCase):
    """model_config 必须可导入（否则 `novel 模型` 全线不可用）。"""

    def test_imports_without_error(self):
        mod = _load("model_config")
        self.assertTrue(callable(mod.main))

    def test_secret_store_available_at_module_level(self):
        """secret_store 必须在模块级可见——它被 storage_mode() 直接调用。"""
        mod = _load("model_config")
        self.assertTrue(hasattr(mod, "secret_store"))
        self.assertTrue(callable(mod.secret_store.storage_mode))

    def test_llm_client_symbols_still_imported(self):
        """重构 import 时不得顺手丢掉原有符号。"""
        mod = _load("model_config")
        for sym in ("load_models", "save_models", "load_secrets", "save_secrets",
                    "test_model", "DEFAULT_ROUTES", "MODELS_FILE", "SECRETS_FILE"):
            with self.subTest(sym=sym):
                self.assertTrue(hasattr(mod, sym))

    def test_presets_present(self):
        mod = _load("model_config")
        self.assertIn("deepseek", mod.PRESETS)


class TestMaskHelper(unittest.TestCase):
    """API Key 掩码工具测试。"""

    def test_mask_empty_and_none(self):
        self.assertEqual(model_config._mask(""), "(未设置)")
        self.assertEqual(model_config._mask(None), "(未设置)")

    def test_mask_short_key(self):
        self.assertEqual(model_config._mask("sk-1234"), "sk***")
        self.assertEqual(model_config._mask("1234567890"), "12***")

    def test_mask_long_key(self):
        self.assertEqual(model_config._mask("sk-1234567890abcdef"), "sk-123...cdef")

    def test_mask_non_string(self):
        self.assertEqual(model_config._mask(123456789012), "123456...9012")


class _ModelConfigTestBase(unittest.TestCase):
    """统一模型配置与密钥打桩基类。"""

    def setUp(self):
        self.cfg = {
            "version": 1,
            "models": {
                "m_cheap": {
                    "protocol": "openai",
                    "base_url": "https://api.cheap.com/v1",
                    "model_name": "cheap-chat",
                    "api_key_env": "CHEAP_KEY",
                    "context_window": 32768,
                },
                "m_strong": {
                    "protocol": "openai",
                    "base_url": "https://api.strong.com/v1",
                    "model_name": "strong-chat",
                    "api_key_env": "",
                    "context_window": 65536,
                },
                "m_local": {
                    "protocol": "ollama",
                    "base_url": "http://localhost:11434",
                    "model_name": "qwen2.5:14b",
                    "api_key_env": "",
                    "context_window": 32768,
                },
            },
            "roles": {"cheap": "m_cheap", "strong": "m_strong", "default": "m_cheap"},
            "routes": dict(model_config.DEFAULT_ROUTES),
        }
        self.secrets = {"m_strong": "sk-strong-secret-key-123456"}
        self._orig = {
            "load_models": model_config.load_models,
            "save_models": model_config.save_models,
            "load_secrets": model_config.load_secrets,
            "save_secrets": model_config.save_secrets,
            "test_model": model_config.test_model,
        }
        model_config.load_models = lambda: self.cfg
        model_config.save_models = self._mock_save_models
        model_config.load_secrets = lambda: self.secrets
        model_config.save_secrets = self._mock_save_secrets

    def tearDown(self):
        model_config.load_models = self._orig["load_models"]
        model_config.save_models = self._orig["save_models"]
        model_config.load_secrets = self._orig["load_secrets"]
        model_config.save_secrets = self._orig["save_secrets"]
        model_config.test_model = self._orig["test_model"]

    def _mock_save_models(self, new_cfg):
        self.cfg = new_cfg

    def _mock_save_secrets(self, new_secrets):
        self.secrets = new_secrets


class TestCmdPresets(unittest.TestCase):
    """cmd_presets 输出格式测试。"""

    def test_cmd_presets_output(self):
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            model_config.cmd_presets(None)
        out = buf.getvalue()
        self.assertIn("内置服务商预设", out)
        self.assertIn("deepseek", out)
        self.assertIn("anthropic", out)
        self.assertIn("ollama", out)


class TestCmdList(_ModelConfigTestBase):
    """cmd_list 展示测试。"""

    def test_cmd_list_empty(self):
        self.cfg["models"] = {}
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            model_config.cmd_list(None)
        out = buf.getvalue()
        self.assertIn("尚未配置任何模型", out)

    def test_cmd_list_with_models(self):
        with mock.patch.dict(os.environ, {"CHEAP_KEY": "env-cheap-key"}):
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                model_config.cmd_list(None)
            out = buf.getvalue()
            self.assertIn("已配置 3 个模型", out)
            self.assertIn("环境变量 CHEAP_KEY ✓", out)
            self.assertIn("sk-str...3456", out)
            self.assertIn("本地无需", out)
            self.assertIn("cheap    → m_cheap", out)


class TestCmdRoutes(_ModelConfigTestBase):
    """cmd_routes 任务路由表展示测试。"""

    def test_cmd_routes_output(self):
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            model_config.cmd_routes(None)
        out = buf.getvalue()
        self.assertIn("任务路由表", out)
        self.assertIn("拆书·结构层", out)
        self.assertIn("章节生成", out)
        self.assertIn("m_cheap", out)
        self.assertIn("m_strong", out)


class TestCmdAdd(_ModelConfigTestBase):
    """cmd_add 添加模型命令测试。"""

    def test_add_unknown_preset(self):
        args = mock.MagicMock(preset="unknown_preset")
        code = model_config.cmd_add(args)
        self.assertEqual(code, 1)

    def test_add_existing_without_force(self):
        args = mock.MagicMock(preset="deepseek", id="m_cheap", force=False)
        code = model_config.cmd_add(args)
        self.assertEqual(code, 1)

    def test_add_custom_missing_base_url(self):
        args = mock.MagicMock(
            preset="custom",
            id="custom1",
            force=False,
            base_url="",
            model_name="test",
            interactive=False,
        )
        code = model_config.cmd_add(args)
        self.assertEqual(code, 1)

    def test_add_custom_missing_model_name(self):
        args = mock.MagicMock(
            preset="custom",
            id="custom1",
            force=False,
            base_url="https://api.test/v1",
            model_name="",
            interactive=False,
        )
        code = model_config.cmd_add(args)
        self.assertEqual(code, 1)

    def test_add_success_first_model_binds_roles(self):
        self.cfg["models"] = {}
        self.cfg["roles"] = {}
        args = mock.MagicMock(
            preset="deepseek",
            id="ds",
            force=False,
            base_url=None,
            model_name=None,
            key="ds-secret-key",
            no_key=False,
            interactive=False,
        )
        code = model_config.cmd_add(args)
        self.assertEqual(code, 0)
        self.assertIn("ds", self.cfg["models"])
        self.assertEqual(self.cfg["roles"]["default"], "ds")
        self.assertEqual(self.cfg["roles"]["cheap"], "ds")
        self.assertEqual(self.cfg["roles"]["strong"], "ds")
        self.assertEqual(self.secrets["ds"], "ds-secret-key")

    def test_add_with_no_key(self):
        args = mock.MagicMock(
            preset="deepseek",
            id="ds_nokey",
            force=False,
            base_url=None,
            model_name=None,
            key=None,
            no_key=True,
            interactive=False,
        )
        code = model_config.cmd_add(args)
        self.assertEqual(code, 0)
        self.assertIn("ds_nokey", self.cfg["models"])
        self.assertNotIn("ds_nokey", self.secrets)

    def test_add_force_overwrite(self):
        args = mock.MagicMock(
            preset="deepseek",
            id="m_cheap",
            force=True,
            base_url="https://new.deepseek.com/v1",
            model_name="new-deepseek",
            key=None,
            no_key=True,
            interactive=False,
        )
        code = model_config.cmd_add(args)
        self.assertEqual(code, 0)
        self.assertEqual(self.cfg["models"]["m_cheap"]["base_url"], "https://new.deepseek.com/v1")
        self.assertEqual(self.cfg["models"]["m_cheap"]["model_name"], "new-deepseek")


class TestCmdKey(_ModelConfigTestBase):
    """cmd_key 密钥设置测试。"""

    def test_key_model_not_found(self):
        args = mock.MagicMock(model_id="nonexistent", value="sk-123")
        code = model_config.cmd_key(args)
        self.assertEqual(code, 1)

    def test_key_empty_value(self):
        args = mock.MagicMock(model_id="m_cheap", value="")
        code = model_config.cmd_key(args)
        self.assertEqual(code, 1)

    def test_key_success(self):
        args = mock.MagicMock(model_id="m_cheap", value="sk-new-cheap-key")
        code = model_config.cmd_key(args)
        self.assertEqual(code, 0)
        self.assertEqual(self.secrets["m_cheap"], "sk-new-cheap-key")


class TestCmdTest(_ModelConfigTestBase):
    """cmd_test 连通性测试分发。"""

    def test_test_no_models(self):
        self.cfg["models"] = {}
        args = mock.MagicMock(model_id=None)
        code = model_config.cmd_test(args)
        self.assertEqual(code, 1)

    def test_test_all_success(self):
        model_config.test_model = mock.MagicMock(return_value={
            "ok": True, "elapsed": 0.5, "tokens": 10, "reply": "正常"
        })
        args = mock.MagicMock(model_id=None)
        code = model_config.cmd_test(args)
        self.assertEqual(code, 0)
        self.assertEqual(model_config.test_model.call_count, 3)

    def test_test_single_success(self):
        model_config.test_model = mock.MagicMock(return_value={
            "ok": True, "elapsed": 0.5, "tokens": 10, "reply": "正常"
        })
        args = mock.MagicMock(model_id="m_cheap")
        code = model_config.cmd_test(args)
        self.assertEqual(code, 0)
        model_config.test_model.assert_called_once_with("m_cheap")

    def test_test_single_fail(self):
        model_config.test_model = mock.MagicMock(return_value={
            "ok": False, "error": "HTTP 401: Unauthorized"
        })
        args = mock.MagicMock(model_id="m_cheap")
        code = model_config.cmd_test(args)
        self.assertEqual(code, 1)


class TestCmdRole(_ModelConfigTestBase):
    """cmd_role 角色绑定测试。"""

    def test_role_model_not_found(self):
        args = mock.MagicMock(role="strong", model_id="ghost")
        code = model_config.cmd_role(args)
        self.assertEqual(code, 1)

    def test_role_success(self):
        args = mock.MagicMock(role="strong", model_id="m_cheap")
        code = model_config.cmd_role(args)
        self.assertEqual(code, 0)
        self.assertEqual(self.cfg["roles"]["strong"], "m_cheap")


class TestCmdRoute(_ModelConfigTestBase):
    """cmd_route 路由配置测试。"""

    def test_route_task_unknown(self):
        args = mock.MagicMock(task="nonexistent_task", role="cheap")
        code = model_config.cmd_route(args)
        self.assertEqual(code, 1)

    def test_route_success(self):
        args = mock.MagicMock(task="pass3_style", role="cheap")
        code = model_config.cmd_route(args)
        self.assertEqual(code, 0)
        self.assertEqual(self.cfg["routes"]["pass3_style"], "cheap")


class TestCmdFallback(_ModelConfigTestBase):
    """cmd_fallback 备用模型配置测试。"""

    def test_fallback_model_not_found(self):
        args = mock.MagicMock(model_id="ghost", fallback_models=["m_strong"])
        code = model_config.cmd_fallback(args)
        self.assertEqual(code, 1)

    def test_fallback_target_not_found(self):
        args = mock.MagicMock(model_id="m_cheap", fallback_models=["ghost"])
        code = model_config.cmd_fallback(args)
        self.assertEqual(code, 1)
        self.assertNotIn("fallback", self.cfg["models"]["m_cheap"])

    def test_fallback_set_targets(self):
        args = mock.MagicMock(model_id="m_cheap", fallback_models=["m_strong", "m_local"])
        code = model_config.cmd_fallback(args)
        self.assertEqual(code, 0)
        self.assertEqual(self.cfg["models"]["m_cheap"]["fallback"], ["m_strong", "m_local"])

    def test_fallback_clear(self):
        self.cfg["models"]["m_cheap"]["fallback"] = ["m_strong"]
        args = mock.MagicMock(model_id="m_cheap", fallback_models=[])
        code = model_config.cmd_fallback(args)
        self.assertEqual(code, 0)
        self.assertNotIn("fallback", self.cfg["models"]["m_cheap"])


class TestCmdRemove(_ModelConfigTestBase):
    """cmd_remove 模型删除测试。"""

    def test_remove_model_not_found(self):
        args = mock.MagicMock(model_id="ghost")
        code = model_config.cmd_remove(args)
        self.assertEqual(code, 1)

    def test_remove_success(self):
        args = mock.MagicMock(model_id="m_strong")
        code = model_config.cmd_remove(args)
        self.assertEqual(code, 0)
        self.assertNotIn("m_strong", self.cfg["models"])
        self.assertNotIn("strong", self.cfg["roles"])
        self.assertNotIn("m_strong", self.secrets)


class TestMainDispatch(_ModelConfigTestBase):
    """main(argv) 命令行分发入口测试。"""

    def test_main_no_args_prints_help(self):
        code = model_config.main([])
        self.assertEqual(code, 0)

    def test_main_dispatch_list(self):
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            code = model_config.main(["list"])
        self.assertEqual(code, 0)
        self.assertIn("已配置 3 个模型", buf.getvalue())

    def test_main_dispatch_presets(self):
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            code = model_config.main(["presets"])
        self.assertEqual(code, 0)
        self.assertIn("内置服务商预设", buf.getvalue())

    def test_main_dispatch_routes(self):
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            code = model_config.main(["routes"])
        self.assertEqual(code, 0)
        self.assertIn("任务路由表", buf.getvalue())

    def test_main_dispatch_fallback(self):
        code = model_config.main(["fallback", "m_cheap", "m_strong"])
        self.assertEqual(code, 0)
        self.assertEqual(self.cfg["models"]["m_cheap"]["fallback"], ["m_strong"])


if __name__ == "__main__":
    unittest.main()
