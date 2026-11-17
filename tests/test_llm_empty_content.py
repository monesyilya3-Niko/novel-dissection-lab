#!/usr/bin/env python3
"""空正文守卫：``content: null`` 必须当失败，不能静默转成空字符串当成功。

根因（2026-11-16 实测定案）
--------------------------
推理型模型（deepseek-4.1-flash 等）把 ``max_tokens`` 全烧在思考上时，
返回的是 ``content: null`` + ``finish_reason: "length"``，
``completion_tokens`` 顶到上限。旧实现：

    text = msg.get("content")
    if text is None:
        text = ""          # <- 静默转空串，当成功返回

后果链：``run_pass`` 拿到空字符串 → ``extract_json`` 失败 → 重试 3 轮
（同样烧满 3 次预算）→ 抛 ``PassRefused`` → 用户看到「模型拒绝本 pass」。
用户以为模型能力不行，实际是 max_tokens 给小了。

实测对照（同一模型、同一 prompt，只改 max_tokens）::

    max_tokens=32    completion=32(满额)   textlen=0    <- 空正文
    max_tokens=256   completion=97         textlen=39   <- 正常
    max_tokens=1024  completion=95         textlen=41   <- 正常

这个缺陷的性质：**把失败伪装成成功**。上层无法区分「模型说空话」和
「模型根本没说话」，于是错误被归因到模型能力上，而不是配置上。

守卫清单
--------
1. ``content: null`` → 抛 LLMError，不返回空串
2. ``content: ""`` / 全空白 → 同样抛错（等价于没生成）
3. ``finish_reason: "length"`` 时错误信息必须提示调大 max_tokens
4. 错误信息必须带 finish_reason / completion_tokens / max_tokens
5. 正常正文照常返回（不能把好响应误杀）
6. 空正文错误不可重试——重试只会再烧一次预算
7. 非 openai 协议（anthropic / ollama）不受影响

纯标准库（铁律三）。
"""
from __future__ import annotations

import json
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

import llm_client  # noqa: E402


def _model(**over):
    m = {
        "protocol": "openai",
        "model_name": "test-model",
        "base_url": "http://example.test/v1",
        "api_key_env": "TEST_KEY",
        "context_window": 128000,
    }
    m.update(over)
    return m


def _response(content, finish_reason=None, completion_tokens=0):
    """构造一个 OpenAI 兼容响应。"""
    choice = {"message": {"role": "assistant", "content": content}}
    if finish_reason is not None:
        choice["finish_reason"] = finish_reason
    return {
        "choices": [choice],
        "usage": {"prompt_tokens": 10, "completion_tokens": completion_tokens},
    }


class TestEmptyContentIsFailure(unittest.TestCase):
    """空正文必须抛错，不能当成功。"""

    def test_null_content_raises(self):
        """核心回归：content 为 null 时旧实现返回 ""，现在必须抛错。"""
        with mock.patch.object(llm_client, "_post_json",
                               return_value=_response(None, "length", 32)):
            with self.assertRaises(llm_client.LLMError) as ctx:
                llm_client._call_openai_compatible(
                    _model(), "k", "sys", "user", max_tokens=32, temperature=0.3)
        self.assertIn("返回空正文", str(ctx.exception))

    def test_empty_string_content_raises(self):
        """content 为空串等价于没生成，同样要抛错。"""
        with mock.patch.object(llm_client, "_post_json",
                               return_value=_response("", "stop", 0)):
            with self.assertRaises(llm_client.LLMError):
                llm_client._call_openai_compatible(
                    _model(), "k", "sys", "user", max_tokens=256, temperature=0.3)

    def test_whitespace_only_content_raises(self):
        """只有空白也算空——不能靠 strip 后的空白骗过检查。"""
        with mock.patch.object(llm_client, "_post_json",
                               return_value=_response("   \n\t  ", "stop", 5)):
            with self.assertRaises(llm_client.LLMError):
                llm_client._call_openai_compatible(
                    _model(), "k", "sys", "user", max_tokens=256, temperature=0.3)


class TestErrorDiagnostics(unittest.TestCase):
    """错误信息必须让人能直接改配置，而不是猜。"""

    def _raise_with(self, resp, max_tokens=32):
        with mock.patch.object(llm_client, "_post_json", return_value=resp):
            try:
                llm_client._call_openai_compatible(
                    _model(), "k", "sys", "user",
                    max_tokens=max_tokens, temperature=0.3)
            except llm_client.LLMError as exc:
                return str(exc)
        self.fail("应当抛 LLMError")

    def test_length_finish_suggests_larger_max_tokens(self):
        """finish_reason=length 是 max_tokens 用尽的信号，必须明说。"""
        msg = self._raise_with(_response(None, "length", 32), max_tokens=32)
        self.assertIn("max_tokens", msg)
        self.assertIn("调大", msg)
        self.assertIn("32", msg)

    def test_error_carries_finish_reason(self):
        msg = self._raise_with(_response(None, "length", 32))
        self.assertIn("finish_reason=length", msg)

    def test_error_carries_completion_tokens(self):
        msg = self._raise_with(_response(None, "length", 32))
        self.assertIn("completion_tokens=32", msg)

    def test_error_names_the_model(self):
        msg = self._raise_with(_response(None, "length", 32))
        self.assertIn("test-model", msg)

    def test_reasoning_content_reported_when_present(self):
        """推理模型把内容放在 reasoning_content 时，错误里要说明这点。"""
        resp = _response(None, "length", 32)
        resp["choices"][0]["message"]["reasoning_content"] = "思考" * 100
        msg = self._raise_with(resp)
        self.assertIn("思考内容", msg)


class TestGoodResponsesStillPass(unittest.TestCase):
    """不能把正常响应误杀。"""

    def test_normal_content_returns(self):
        with mock.patch.object(llm_client, "_post_json",
                               return_value=_response("正常回复", "stop", 5)):
            r = llm_client._call_openai_compatible(
                _model(), "k", "sys", "user", max_tokens=256, temperature=0.3)
        self.assertEqual(r["text"], "正常回复")
        self.assertEqual(r["completion_tokens"], 5)

    def test_content_with_leading_space_kept(self):
        """有内容的响应原样返回，不 strip（正文格式是调用方的事）。"""
        with mock.patch.object(llm_client, "_post_json",
                               return_value=_response("  缩进内容", "stop", 5)):
            r = llm_client._call_openai_compatible(
                _model(), "k", "sys", "user", max_tokens=256, temperature=0.3)
        self.assertEqual(r["text"], "  缩进内容")

    def test_json_mode_content_passes(self):
        with mock.patch.object(llm_client, "_post_json",
                               return_value=_response('{"a": 1}', "stop", 8)):
            r = llm_client._call_openai_compatible(
                _model(json_mode=True), "k", "sys", "user",
                max_tokens=256, temperature=0.3)
        self.assertEqual(json.loads(r["text"]), {"a": 1})


class TestEmptyContentNotRetryable(unittest.TestCase):
    """空正文重试没有意义：max_tokens 和 prompt 都没变，只会再烧一次预算。"""

    def test_empty_content_marked_non_retryable(self):
        try:
            with mock.patch.object(llm_client, "_post_json",
                                   return_value=_response(None, "length", 32)):
                llm_client._call_openai_compatible(
                    _model(), "k", "sys", "user", max_tokens=32, temperature=0.3)
        except llm_client.LLMError as exc:
            self.assertFalse(llm_client._is_retryable_error(exc))
        else:
            self.fail("应当抛 LLMError")

    def test_chat_one_does_not_retry_empty_content(self):
        """端到端：retries=3 时空正文也只调用一次。"""
        attempts = []

        def fake_post(*a, **k):
            attempts.append(1)
            return _response(None, "length", 32)

        with mock.patch.object(llm_client, "_post_json", side_effect=fake_post), \
             mock.patch.object(llm_client, "resolve_api_key", return_value="k"):
            with self.assertRaises(llm_client.LLMError):
                llm_client._chat_one("m1", _model(), "u", "s", 32, 0.3, 3, None, False)
        self.assertEqual(len(attempts), 1, "空正文不该重试")


class TestOtherProtocolsAlsoGuarded(unittest.TestCase):
    """三个协议都要守：只修 openai 会留下两处同样的坑。"""

    def test_anthropic_empty_text_raises(self):
        """anthropic 空 content block 列表 → 抛错，不再返回空串。

        2026-11-16 补齐：上一轮只修了 openai，anthropic 的
        ``"".join([])`` 同样会产出空串当成功。
        """
        resp = {"content": [{"type": "text", "text": ""}],
                "usage": {"input_tokens": 5, "output_tokens": 0}}
        with mock.patch.object(llm_client, "_post_json", return_value=resp):
            with self.assertRaises(llm_client.LLMError) as ctx:
                llm_client._call_anthropic(
                    _model(protocol="anthropic"), "k", "sys", "user",
                    max_tokens=256, temperature=0.3)
        self.assertIn("返回空正文", str(ctx.exception))

    def test_anthropic_empty_block_list_raises(self):
        """content 是空列表时，旧实现 join 出空串；现在必须抛错。"""
        resp = {"content": [], "usage": {"input_tokens": 5, "output_tokens": 0}}
        with mock.patch.object(llm_client, "_post_json", return_value=resp):
            with self.assertRaises(llm_client.LLMError):
                llm_client._call_anthropic(
                    _model(protocol="anthropic"), "k", "sys", "user",
                    max_tokens=256, temperature=0.3)

    def test_anthropic_max_tokens_stop_suggests_larger(self):
        """stop_reason=max_tokens 等价于 openai 的 finish_reason=length。"""
        resp = {"content": [{"type": "text", "text": ""}],
                "stop_reason": "max_tokens",
                "usage": {"input_tokens": 5, "output_tokens": 256}}
        with mock.patch.object(llm_client, "_post_json", return_value=resp):
            with self.assertRaises(llm_client.LLMError) as ctx:
                llm_client._call_anthropic(
                    _model(protocol="anthropic"), "k", "sys", "user",
                    max_tokens=256, temperature=0.3)
        self.assertIn("调大", str(ctx.exception))

    def test_anthropic_normal_text_passes(self):
        """对照：正常正文照常返回。"""
        resp = {"content": [{"type": "text", "text": "正常回复"}],
                "usage": {"input_tokens": 5, "output_tokens": 3}}
        with mock.patch.object(llm_client, "_post_json", return_value=resp):
            r = llm_client._call_anthropic(
                _model(protocol="anthropic"), "k", "sys", "user",
                max_tokens=256, temperature=0.3)
        self.assertEqual(r["text"], "正常回复")

    def test_ollama_null_content_raises(self):
        """ollama 的 message.content:null 同样必须抛错。"""
        resp = {"message": {"role": "assistant", "content": None},
                "prompt_eval_count": 5, "eval_count": 32, "done_reason": "length"}
        with mock.patch.object(llm_client, "_post_json", return_value=resp):
            with self.assertRaises(llm_client.LLMError) as ctx:
                llm_client._call_ollama(
                    _model(protocol="ollama"), "", "sys", "user",
                    max_tokens=32, temperature=0.3)
        self.assertIn("返回空正文", str(ctx.exception))

    def test_ollama_normal_text_passes(self):
        resp = {"message": {"role": "assistant", "content": "正常回复"},
                "prompt_eval_count": 5, "eval_count": 3}
        with mock.patch.object(llm_client, "_post_json", return_value=resp):
            r = llm_client._call_ollama(
                _model(protocol="ollama"), "", "sys", "user",
                max_tokens=256, temperature=0.3)
        self.assertEqual(r["text"], "正常回复")


class TestConnectivityTestUsesEnoughTokens(unittest.TestCase):
    """连通性测试不能用小 max_tokens——会把「预算给小了」误报成「模型不通」。"""

    def test_test_model_requests_enough_tokens(self):
        """2026-11-16 实测：max_tokens=32 时推理模型返回空正文。

        旧值 32 会让 `python novel.py 模型` 把好模型报成不通，
        用户照着提示去查密钥和网络，白折腾。
        """
        captured = {}

        def fake_chat(**kwargs):
            captured.update(kwargs)
            return {"text": "正常", "prompt_tokens": 10, "completion_tokens": 2,
                    "elapsed": 0.1, "cost": 0.0}

        with mock.patch.object(llm_client, "load_models",
                               return_value={"models": {"m1": {}}}), \
             mock.patch.object(llm_client, "chat", side_effect=fake_chat):
            res = llm_client.test_model("m1")

        self.assertTrue(res["ok"])
        self.assertGreaterEqual(
            captured["max_tokens"], 4096,
            "连通性测试的 max_tokens 太小：推理模型会把预算烧在思考上，"
            "返回空正文，导致好模型被误报成不通")

    def test_test_model_still_single_model(self):
        """既有契约不回退：连通性测试必须只测一个模型。"""
        captured = {}

        def fake_chat(**kwargs):
            captured.update(kwargs)
            return {"text": "正常", "prompt_tokens": 1, "completion_tokens": 1,
                    "elapsed": 0.1, "cost": 0.0}

        with mock.patch.object(llm_client, "load_models",
                               return_value={"models": {"m1": {}}}), \
             mock.patch.object(llm_client, "chat", side_effect=fake_chat):
            llm_client.test_model("m1")

        self.assertFalse(captured["allow_fallback"],
                         "连通性测试不能启用备用模型")


if __name__ == "__main__":
    unittest.main()
