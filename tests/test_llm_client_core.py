#!/usr/bin/env python3
"""
llm_client 核心协议与适配器全维独立测试 — 纯标准库 unittest，零第三方依赖

覆盖范围：
1. _post_json: 正常 JSON 往返、HTTPError (401/403/500)、URLError、非合法 JSON 响应处理
2. _call_openai_compatible: 消息组装、system/user、json_mode、extra_headers、Bearer token、
   base_url 归一化、usage 映射、content 为 None 兜底、畸形响应拦截
3. _call_anthropic: 协议请求体、system 字段、x-api-key、anthropic-version、content block 拼接、
   input/output tokens 映射、畸形响应拦截
4. _call_ollama: options 参数映射、num_ctx 优先级、prompt_eval_count 映射、畸形响应拦截
5. resolve_api_key: 环境变量优先 > secrets 文件 > 空字符串回退
6. _estimate_cost: 百万 token 计费模型估算、非数字异常容错防御
7. describe_llm_degradation: 错误类型分类解析（未配置 / 额度权限 / 网络超时 / 通用失败）及功能降级清单
8. any_model_configured: 空配置、有配置、异常防御
9. resolve_model: 显式指定 > 任务路由 > default 角色 > 首个模型回退
10. load_models / save_models: 骨架初始化、损坏容错、持久化往返
11. test_model & CLI main(argv): 连通性测试报告、退出码 (0/1/2) 映射
"""

import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import llm_client  # noqa: E402


class TestPostJson(unittest.TestCase):
    """底层 HTTP 请求函数 _post_json 单元测试。"""

    @mock.patch("urllib.request.urlopen")
    def test_post_json_success(self, mock_urlopen):
        resp_data = {"result": "ok", "count": 42}
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = json.dumps(resp_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = llm_client._post_json(
            "http://example.com/api",
            {"prompt": "hello"},
            {"X-Auth": "secret"},
            timeout=30,
        )
        self.assertEqual(res, resp_data)
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "http://example.com/api")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.get_header("Content-type"), "application/json")
        self.assertEqual(req.get_header("X-auth"), "secret")
        self.assertEqual(json.loads(req.data.decode("utf-8")), {"prompt": "hello"})

    @mock.patch("urllib.request.urlopen")
    def test_post_json_http_error(self, mock_urlopen):
        err = urllib.error.HTTPError(
            url="http://example.com",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=io.BytesIO(b'{"error": "invalid_api_key"}'),
        )
        mock_urlopen.side_effect = err
        with self.assertRaises(llm_client.LLMError) as ctx:
            llm_client._post_json("http://example.com", {}, {})
        self.assertIn("HTTP 401", str(ctx.exception))
        self.assertIn("invalid_api_key", str(ctx.exception))

    @mock.patch("urllib.request.urlopen")
    def test_post_json_url_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        with self.assertRaises(llm_client.LLMError) as ctx:
            llm_client._post_json("http://example.com", {}, {})
        self.assertIn("连接失败: Connection refused", str(ctx.exception))

    @mock.patch("urllib.request.urlopen")
    def test_post_json_invalid_json(self, mock_urlopen):
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = b"<html>502 Bad Gateway</html>"
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        with self.assertRaises(llm_client.LLMError) as ctx:
            llm_client._post_json("http://example.com", {}, {})
        self.assertIn("响应非合法 JSON", str(ctx.exception))
        self.assertIn("502 Bad Gateway", str(ctx.exception))


class TestCallOpenAICompatible(unittest.TestCase):
    """OpenAI 兼容协议适配器测试。"""

    @mock.patch.object(llm_client, "_post_json")
    def test_call_openai_standard(self, mock_post):
        mock_post.return_value = {
            "choices": [{"message": {"content": "你好，世界"}}],
            "usage": {"prompt_tokens": 15, "completion_tokens": 8},
        }
        model = {
            "base_url": "https://api.openai.com/v1",
            "model_name": "gpt-4o-mini",
            "timeout": 60,
        }
        res = llm_client._call_openai_compatible(
            model=model,
            api_key="sk-test",
            system="你是一个助手",
            user="讲个笑话",
            max_tokens=100,
            temperature=0.7,
        )
        self.assertEqual(res["text"], "你好，世界")
        self.assertEqual(res["prompt_tokens"], 15)
        self.assertEqual(res["completion_tokens"], 8)

        mock_post.assert_called_once()
        url, payload, headers, timeout = mock_post.call_args[0]
        self.assertEqual(url, "https://api.openai.com/v1/chat/completions")
        self.assertEqual(payload["model"], "gpt-4o-mini")
        self.assertEqual(payload["messages"], [
            {"role": "system", "content": "你是一个助手"},
            {"role": "user", "content": "讲个笑话"},
        ])
        self.assertEqual(payload["max_tokens"], 100)
        self.assertEqual(payload["temperature"], 0.7)
        self.assertEqual(headers.get("Authorization"), "Bearer sk-test")
        self.assertEqual(timeout, 60)

    @mock.patch.object(llm_client, "_post_json")
    def test_call_openai_json_mode_and_no_system(self, mock_post):
        mock_post.return_value = {
            "choices": [{"message": {"content": '{"ok": true}'}}],
            "usage": {},
        }
        model = {
            "base_url": "https://api.deepseek.com/v1/chat/completions",
            "model_name": "deepseek-chat",
            "json_mode": True,
            "extra_headers": {"X-Custom-Trace": "123"},
        }
        res = llm_client._call_openai_compatible(
            model=model,
            api_key="",
            system="",
            user="提取JSON",
            max_tokens=500,
            temperature=0.2,
        )
        self.assertEqual(res["text"], '{"ok": true}')
        self.assertEqual(res["prompt_tokens"], 0)
        self.assertEqual(res["completion_tokens"], 0)

        url, payload, headers, _ = mock_post.call_args[0]
        self.assertEqual(url, "https://api.deepseek.com/v1/chat/completions")
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["messages"], [{"role": "user", "content": "提取JSON"}])
        self.assertNotIn("Authorization", headers)
        self.assertEqual(headers["X-Custom-Trace"], "123")

    @mock.patch.object(llm_client, "_post_json")
    def test_call_openai_content_none_handled(self, mock_post):
        mock_post.return_value = {
            "choices": [{"message": {"content": None}}],
        }
        model = {"base_url": "http://localhost:8000/v1", "model_name": "local-llm"}
        res = llm_client._call_openai_compatible(model, "", "", "ping", 10, 0)
        self.assertEqual(res["text"], "")

    @mock.patch.object(llm_client, "_post_json")
    def test_call_openai_malformed_responses(self, mock_post):
        model = {"base_url": "http://localhost:8000/v1", "model_name": "local-llm"}
        bad_responses = [
            {},
            {"choices": []},
            {"choices": [{"message": "not a dict"}]},
            "string response",
            {"choices": [{"no_message": 123}]},
        ]
        for bad in bad_responses:
            mock_post.return_value = bad
            with self.subTest(bad=bad):
                with self.assertRaises(llm_client.LLMError) as ctx:
                    llm_client._call_openai_compatible(model, "", "", "ping", 10, 0)
                self.assertIn("响应格式异常", str(ctx.exception))


class TestCallAnthropic(unittest.TestCase):
    """Anthropic 协议适配器测试。"""

    @mock.patch.object(llm_client, "_post_json")
    def test_call_anthropic_standard(self, mock_post):
        mock_post.return_value = {
            "content": [{"type": "text", "text": "Hello, "}, {"type": "text", "text": "Claude"}],
            "usage": {"input_tokens": 20, "output_tokens": 12},
        }
        model = {
            "base_url": "https://api.anthropic.com/v1",
            "model_name": "claude-3-5-sonnet-20241022",
            "anthropic_version": "2023-06-01",
        }
        res = llm_client._call_anthropic(
            model=model,
            api_key="anthropic-secret-key",
            system="你是莎士比亚",
            user="念一首十四行诗",
            max_tokens=1000,
            temperature=0.5,
        )
        self.assertEqual(res["text"], "Hello, Claude")
        self.assertEqual(res["prompt_tokens"], 20)
        self.assertEqual(res["completion_tokens"], 12)

        url, payload, headers, _ = mock_post.call_args[0]
        self.assertEqual(url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(payload["system"], "你是莎士比亚")
        self.assertEqual(payload["messages"], [{"role": "user", "content": "念一首十四行诗"}])
        self.assertEqual(headers["x-api-key"], "anthropic-secret-key")
        self.assertEqual(headers["anthropic-version"], "2023-06-01")

    @mock.patch.object(llm_client, "_post_json")
    def test_call_anthropic_no_system_and_existing_url(self, mock_post):
        mock_post.return_value = {
            "content": [{"text": "OK"}],
        }
        model = {
            "base_url": "https://api.anthropic.com/v1/messages",
            "model_name": "claude-3-opus",
            "extra_headers": {"X-Anthropic-Beta": "output-128k-2025-02-19"},
        }
        res = llm_client._call_anthropic(model, "key", "", "hi", 10, 0)
        self.assertEqual(res["text"], "OK")
        url, payload, headers, _ = mock_post.call_args[0]
        self.assertEqual(url, "https://api.anthropic.com/v1/messages")
        self.assertNotIn("system", payload)
        self.assertEqual(headers["X-Anthropic-Beta"], "output-128k-2025-02-19")

    @mock.patch.object(llm_client, "_post_json")
    def test_call_anthropic_malformed_responses(self, mock_post):
        model = {"base_url": "https://api.anthropic.com/v1", "model_name": "claude"}
        bad_responses = [
            {},
            {"content": "not a list"},
            {"content": [123, None]},
            "bad response",
        ]
        for bad in bad_responses:
            mock_post.return_value = bad
            with self.subTest(bad=bad):
                with self.assertRaises(llm_client.LLMError) as ctx:
                    llm_client._call_anthropic(model, "key", "", "hi", 10, 0)
                self.assertIn("响应格式异常", str(ctx.exception))


class TestCallOllama(unittest.TestCase):
    """Ollama 本地模型协议适配器测试。"""

    @mock.patch.object(llm_client, "_post_json")
    def test_call_ollama_standard(self, mock_post):
        mock_post.return_value = {
            "message": {"content": "本地大模型回答"},
            "prompt_eval_count": 50,
            "eval_count": 30,
        }
        model = {
            "base_url": "http://127.0.0.1:11434",
            "model_name": "qwen2.5:14b",
            "num_ctx": 16384,
            "timeout": 300,
        }
        res = llm_client._call_ollama(
            model=model,
            api_key="",
            system="你是一个助手",
            user="你好",
            max_tokens=200,
            temperature=0.8,
        )
        self.assertEqual(res["text"], "本地大模型回答")
        self.assertEqual(res["prompt_tokens"], 50)
        self.assertEqual(res["completion_tokens"], 30)

        url, payload, _, timeout = mock_post.call_args[0]
        self.assertEqual(url, "http://127.0.0.1:11434/api/chat")
        self.assertEqual(payload["messages"], [
            {"role": "system", "content": "你是一个助手"},
            {"role": "user", "content": "你好"},
        ])
        self.assertEqual(payload["options"]["num_ctx"], 16384)
        self.assertEqual(payload["options"]["num_predict"], 200)
        self.assertEqual(payload["options"]["temperature"], 0.8)
        self.assertEqual(timeout, 300)

    @mock.patch.object(llm_client, "_post_json")
    def test_call_ollama_malformed_responses(self, mock_post):
        model = {"base_url": "http://127.0.0.1:11434/api/chat", "model_name": "llama3"}
        bad_responses = [
            {},
            {"message": "string instead of dict"},
            None,
        ]
        for bad in bad_responses:
            mock_post.return_value = bad
            with self.subTest(bad=bad):
                with self.assertRaises(llm_client.LLMError) as ctx:
                    llm_client._call_ollama(model, "", "", "hi", 10, 0)
                self.assertIn("响应格式异常", str(ctx.exception))


class TestResolveApiKey(unittest.TestCase):
    """密钥解析优先级测试。"""

    def test_env_var_preferred(self):
        model = {"api_key_env": "CUSTOM_LLM_KEY_FOR_TEST"}
        with mock.patch.dict(os.environ, {"CUSTOM_LLM_KEY_FOR_TEST": "secret_from_env"}):
            key = llm_client.resolve_api_key("m1", model)
            self.assertEqual(key, "secret_from_env")

    @mock.patch.object(llm_client, "load_secrets")
    def test_fallback_to_secrets_file(self, mock_secrets):
        mock_secrets.return_value = {"m1": "key_from_secrets"}
        model = {"api_key_env": "NON_EXISTENT_VAR"}
        key = llm_client.resolve_api_key("m1", model)
        self.assertEqual(key, "key_from_secrets")

    @mock.patch.object(llm_client, "load_secrets")
    def test_fallback_to_empty_string(self, mock_secrets):
        mock_secrets.return_value = {}
        model = {}
        key = llm_client.resolve_api_key("m1", model)
        self.assertEqual(key, "")


class TestEstimateCost(unittest.TestCase):
    """Token 费用估算函数测试。"""

    def test_standard_cost_calculation(self):
        model = {"price_in_per_1m": 2.0, "price_out_per_1m": 8.0}
        result = {"prompt_tokens": 100_000, "completion_tokens": 50_000}
        # 100000 / 1M * 2.0 = 0.20; 50000 / 1M * 8.0 = 0.40; Total = 0.60
        cost = llm_client._estimate_cost(model, result)
        self.assertEqual(cost, 0.6)

    def test_zero_cost(self):
        model = {}
        result = {"prompt_tokens": 1000, "completion_tokens": 500}
        cost = llm_client._estimate_cost(model, result)
        self.assertEqual(cost, 0.0)

    def test_defensive_against_bad_types(self):
        model = {"price_in_per_1m": "bad", "price_out_per_1m": None}
        result = {"prompt_tokens": "invalid", "completion_tokens": 100}
        cost = llm_client._estimate_cost(model, result)
        self.assertEqual(cost, 0.0)


class TestDescribeLLMDegradation(unittest.TestCase):
    """LLM 降级与可用性提示生成测试。"""

    def test_unconfigured_error(self):
        desc = llm_client.describe_llm_degradation("尚未配置任何模型")
        self.assertIn("[LLM 降级] 尚未配置外部模型", desc)
        self.assertIn("python scripts/model_config.py add", desc)
        self.assertIn("仍然可用（纯本地）", desc)

    def test_insufficient_or_quota_error(self):
        for phrase in ("insufficient_quota", "余额不足", "HTTP 403: Forbidden", "HTTP 401: Unauthorized"):
            with self.subTest(phrase=phrase):
                desc = llm_client.describe_llm_degradation(f"调用失败: {phrase}")
                self.assertIn("[LLM 降级] 模型额度/权限不足", desc)
                self.assertIn("充值或更换可用模型", desc)

    def test_timeout_and_network_error(self):
        for phrase in ("连接失败: Connection reset", "timed out", "timeout reached"):
            with self.subTest(phrase=phrase):
                desc = llm_client.describe_llm_degradation(f"网络异常: {phrase}")
                self.assertIn("[LLM 降级] 网络连接失败", desc)
                self.assertIn("检查网络/代理后重试", desc)

    def test_generic_error(self):
        desc = llm_client.describe_llm_degradation("未知内部错误")
        self.assertIn("[LLM 降级] 模型调用失败", desc)


class TestAnyModelConfigured(unittest.TestCase):
    """any_model_configured 检查测试。"""

    @mock.patch.object(llm_client, "load_models")
    def test_empty_config(self, mock_load):
        mock_load.return_value = {"models": {}}
        self.assertFalse(llm_client.any_model_configured())

    @mock.patch.object(llm_client, "load_models")
    def test_with_models(self, mock_load):
        mock_load.return_value = {"models": {"deepseek": {"model_name": "ds"}}}
        self.assertTrue(llm_client.any_model_configured())

    @mock.patch.object(llm_client, "load_models")
    def test_corrupt_config_exception(self, mock_load):
        mock_load.side_effect = RuntimeError("Disk read error")
        self.assertFalse(llm_client.any_model_configured())


class TestResolveModel(unittest.TestCase):
    """resolve_model 路由策略测试。"""

    def setUp(self):
        self._orig_load = llm_client.load_models
        self.cfg = {
            "version": 1,
            "models": {
                "cheap_model": {"model_name": "cheap"},
                "strong_model": {"model_name": "strong"},
                "default_model": {"model_name": "def"},
            },
            "roles": {
                "cheap": "cheap_model",
                "strong": "strong_model",
                "default": "default_model",
            },
            "routes": {
                "pass1_structure": "cheap",
                "writing": "strong",
            },
        }
        llm_client.load_models = lambda: self.cfg

    def tearDown(self):
        llm_client.load_models = self._orig_load

    def test_no_models_raises(self):
        self.cfg["models"] = {}
        with self.assertRaises(llm_client.LLMError) as ctx:
            llm_client.resolve_model()
        self.assertIn("尚未配置任何模型", str(ctx.exception))

    def test_explicit_model_id_found(self):
        mid, m = llm_client.resolve_model(model_id="cheap_model")
        self.assertEqual(mid, "cheap_model")
        self.assertEqual(m["model_name"], "cheap")

    def test_explicit_model_id_not_found(self):
        with self.assertRaises(llm_client.LLMError) as ctx:
            llm_client.resolve_model(model_id="nonexistent")
        self.assertIn("不存在", str(ctx.exception))

    def test_task_route_found(self):
        mid, m = llm_client.resolve_model(task="writing")
        self.assertEqual(mid, "strong_model")

    def test_default_role_fallback(self):
        mid, m = llm_client.resolve_model(task="unmapped_task")
        self.assertEqual(mid, "default_model")

    def test_first_model_fallback(self):
        self.cfg["roles"] = {}
        mid, m = llm_client.resolve_model(task="unmapped_task")
        self.assertEqual(mid, "cheap_model")


class TestLoadAndSaveModels(unittest.TestCase):
    """load_models 与 save_models 配置持久化测试。"""

    def setUp(self):
        # 2026-11-02：配置改到用户目录后，patch MODELS_FILE 常量不再生效
        # （load_models 走 resolve_models_file() 实时求值）。改用 XUAN_DATA_DIR
        # 隔离——它同时覆盖 models.json 与密钥目录，也贴近真实部署形态。
        self.temp_dir = tempfile.TemporaryDirectory()
        self._orig_env = os.environ.get("XUAN_DATA_DIR")
        os.environ["XUAN_DATA_DIR"] = self.temp_dir.name
        self.cfg_dir = Path(self.temp_dir.name) / "config"
        self.cfg_dir.mkdir(parents=True, exist_ok=True)
        self.cfg_file = self.cfg_dir / "models.json"

    def tearDown(self):
        if self._orig_env is None:
            os.environ.pop("XUAN_DATA_DIR", None)
        else:
            os.environ["XUAN_DATA_DIR"] = self._orig_env
        self.temp_dir.cleanup()

    def test_load_models_when_file_not_exist(self):
        """用户目录无配置时回落到仓库模板（2026-11-02 起的行为）。

        改配置到用户目录后，"文件不存在"不再等于"空骨架"——仓库
        config/models.json 作为模板被回落，让全新安装也有一份可参照的
        结构。要测"完全无模型"应使用 NOVEL_LAB_FORCE_NO_MODEL=1
        （test_write_chapter 就是这么做的）。
        """
        cfg = llm_client.load_models()
        self.assertEqual(cfg["version"], 1)
        self.assertIn("pass1_structure", cfg["routes"])
        # 回落模板时至少结构完整；具体模型取决于仓库模板内容
        self.assertIsInstance(cfg["models"], dict)
        self.assertIsInstance(cfg["roles"], dict)

    def test_no_models_file_anywhere_yields_empty(self):
        """用户目录与仓库都没有配置文件 → 空骨架。"""
        import shutil
        backup = self.cfg_file
        # 临时把仓库模板也挪走
        repo_cfg = llm_client.MODELS_FILE
        hidden = repo_cfg.with_suffix(".json.testbak")
        moved = False
        if repo_cfg.exists():
            shutil.move(str(repo_cfg), str(hidden))
            moved = True
        try:
            cfg = llm_client.load_models()
            self.assertEqual(cfg["models"], {}, "两处都无配置时应返回空骨架")
        finally:
            if moved:
                shutil.move(str(hidden), str(repo_cfg))

    def test_load_models_corrupt_json(self):
        self.cfg_file.write_text("{bad json...", encoding="utf-8")
        cfg = llm_client.load_models()
        self.assertEqual(cfg["models"], {})

    def test_load_models_not_dict(self):
        self.cfg_file.write_text("[\"list\"]", encoding="utf-8")
        cfg = llm_client.load_models()
        self.assertEqual(cfg["models"], {})

    def test_save_and_load_roundtrip(self):
        test_cfg = {
            "version": 1,
            "models": {"m1": {"model_name": "test-m1"}},
            "roles": {"default": "m1"},
            "routes": {"writing": "default"},
        }
        llm_client.save_models(test_cfg)
        loaded = llm_client.load_models()
        self.assertEqual(loaded["models"]["m1"]["model_name"], "test-m1")


class TestTestModelAndCLI(unittest.TestCase):
    """test_model 函数与 CLI main(argv) 测试。"""

    @mock.patch.object(llm_client, "load_models")
    def test_test_model_not_found(self, mock_load):
        mock_load.return_value = {"models": {}}
        res = llm_client.test_model("unknown_id")
        self.assertFalse(res["ok"])
        self.assertIn("不存在", res["error"])

    @mock.patch.object(llm_client, "load_models")
    @mock.patch.object(llm_client, "chat")
    def test_test_model_success(self, mock_chat, mock_load):
        mock_load.return_value = {"models": {"m1": {}}}
        mock_chat.return_value = {
            "text": "正常",
            "elapsed": 0.45,
            "prompt_tokens": 10,
            "completion_tokens": 2,
        }
        res = llm_client.test_model("m1")
        self.assertTrue(res["ok"])
        self.assertEqual(res["reply"], "正常")
        self.assertEqual(res["elapsed"], 0.45)
        self.assertEqual(res["tokens"], 12)

    @mock.patch.object(llm_client, "load_models")
    @mock.patch.object(llm_client, "chat")
    def test_test_model_llm_error(self, mock_chat, mock_load):
        mock_load.return_value = {"models": {"m1": {}}}
        mock_chat.side_effect = llm_client.LLMError("认证失败 401")
        res = llm_client.test_model("m1")
        self.assertFalse(res["ok"])
        self.assertIn("认证失败 401", res["error"])

    def test_main_cli_no_args(self):
        code = llm_client.main([])
        self.assertEqual(code, 2)

    def test_main_cli_help(self):
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            code = llm_client.main(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("用法", buf.getvalue())

    @mock.patch.object(llm_client, "test_model")
    def test_main_cli_success(self, mock_test):
        mock_test.return_value = {"ok": True, "reply": "正常"}
        code = llm_client.main(["m1"])
        self.assertEqual(code, 0)

    @mock.patch.object(llm_client, "test_model")
    def test_main_cli_failure(self, mock_test):
        mock_test.return_value = {"ok": False, "error": "连接超时"}
        code = llm_client.main(["m1"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
