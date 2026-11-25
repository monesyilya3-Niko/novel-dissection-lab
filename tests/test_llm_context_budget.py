#!/usr/bin/env python3
"""上下文预算守卫：请求装不进模型窗口时必须当场拦下，而不是发出去拿回空文本。

背景（2026-11-16 实测，纠正 11-11 的初判）
----------------------------------------
拆书 pass1 把采样章节全文拼成一条 user 消息。一本 1431 章的书采样 27 章后，
user 有 313,137 字符。模型配置里写着 ``context_window: 128000``，
但 ``_chat_one`` 从来没读过这个字段——请求照发。

11-11 曾把这归因为「313K 字符塞进 128K 窗口」，**该归因是错的**：
那本是英文语料，按 4 字符/token 只合 78,524 tokens，窗口装得下。

真正缺的是**任何**预算检查。中文语料才是真会撑爆的场景——

    英文 313,137 字符 ->  78,524 tokens  (128K 窗口装得下)
    中文 313,137 字符 -> 313,137 tokens  (窗口的 2.4 倍，装不下)

而 novel-lab 的主场景正是中文网文，所以这个缺口必须堵。

超限的请求网关不一定报错：可能返回空文本，也可能直接断开。上层 ``run_pass``
只看到「JSON 解析失败」，重试 3 轮后抛 ``PassRefused``，用户看到的是
「模型拒绝本 pass」——指不到真正原因（装不下），还白烧 3 次请求的钱。

这个缺陷的性质：**静默失败**。没有异常、没有错误码、没有日志线索，
只有一份空结果。比报错更糟，因为用户会以为模型能力不行。

守卫清单
--------
1. ``estimate_tokens`` 的估算口径（中文按字、ASCII 按 4 字符）
2. 装得下时不拦（不能把正常请求误杀）
3. 装不下时抛 LLMError，且错误信息含窗口/预算/超出量三个数字
4. 未配置 ``context_window`` 的模型不做判断（不能凭猜测拦截）
5. 超预算错误**不可重试**——同样输入再发一次还是一样超
6. ``_chat_one`` 真的调用了检查（接线守卫，防「函数写了但没接」）
7. 检查发生在发请求**之前**（防「先烧钱再报错」）

纯标准库（铁律三）。
"""
from __future__ import annotations

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


class TestEstimateTokens(unittest.TestCase):
    """token 估算口径。"""

    def test_empty_text_is_zero(self):
        self.assertEqual(llm_client.estimate_tokens(""), 0)

    def test_chinese_counts_one_per_char(self):
        """中文按 1 字 1 token——保守取值，宁可高估提前拦下。"""
        self.assertEqual(llm_client.estimate_tokens("拆书分析"), 4)

    def test_ascii_counts_four_chars_per_token(self):
        self.assertEqual(llm_client.estimate_tokens("abcd"), 1)
        self.assertEqual(llm_client.estimate_tokens("abcdefgh"), 2)

    def test_ascii_rounds_up(self):
        """不足 4 字符也要算 1 token，不能向下取整成 0。"""
        self.assertEqual(llm_client.estimate_tokens("ab"), 1)
        self.assertEqual(llm_client.estimate_tokens("abcde"), 2)

    def test_mixed_text_adds_both(self):
        # 4 个汉字 + 8 个 ASCII = 4 + 2 = 6
        self.assertEqual(llm_client.estimate_tokens("拆书分析abcdefgh"), 6)

    def test_estimate_is_monotonic(self):
        """文本变长，估算不能变小。"""
        prev = 0
        for n in (1, 10, 100, 1000):
            cur = llm_client.estimate_tokens("拆" * n)
            self.assertGreater(cur, prev)
            prev = cur


class TestCheckContextBudgetPasses(unittest.TestCase):
    """装得下时必须放行——不能把正常请求误杀。"""

    def test_small_prompt_passes(self):
        model = {"context_window": 128000}
        info = llm_client.check_context_budget(
            "m1", model, "你是助手", "帮我拆书", max_tokens=8192)
        self.assertTrue(info["ok"])
        self.assertEqual(info["context_window"], 128000)

    def test_exactly_at_budget_passes(self):
        """恰好等于预算时放行（边界含等号）。"""
        model = {"context_window": 1000}
        # budget = 1000 - 100 - 512 = 388
        budget = 1000 - 100 - llm_client._RESPONSE_HEADROOM_TOKENS
        info = llm_client.check_context_budget(
            "m1", model, "", "拆" * budget, max_tokens=100)
        self.assertTrue(info["ok"])
        self.assertEqual(info["prompt_tokens"], budget)

    def test_missing_context_window_does_not_block(self):
        """未配置 context_window 的模型（自定义中转站常见）不做判断。

        不能凭猜测拦截——那会让所有自建端点直接不可用。
        """
        model = {}
        info = llm_client.check_context_budget(
            "m1", model, "", "拆" * 500000, max_tokens=8192)
        self.assertTrue(info["ok"])
        self.assertIsNone(info["context_window"])

    def test_invalid_context_window_does_not_block(self):
        for bad in (0, -1, None, "128000", 128000.0):
            with self.subTest(bad=bad):
                info = llm_client.check_context_budget(
                    "m1", {"context_window": bad}, "", "拆" * 500000, max_tokens=8192)
                self.assertTrue(info["ok"])


class TestCheckContextBudgetBlocks(unittest.TestCase):
    """装不下时必须拦下，且说清楚差多少。"""

    def test_oversized_prompt_raises(self):
        model = {"context_window": 1000}
        with self.assertRaises(llm_client.LLMError) as ctx:
            llm_client.check_context_budget(
                "m1", model, "", "拆" * 5000, max_tokens=100)
        msg = str(ctx.exception)
        # 三个关键数字都要在错误信息里，否则用户不知道该改什么
        self.assertIn("1000", msg)          # 窗口
        self.assertIn("5000", msg)          # 实际 prompt
        self.assertIn("超出", msg)

    def test_error_says_it_is_not_a_refusal(self):
        """必须明确区分「装不下」和「模型拒答」——这是原始缺陷最误导人的地方。"""
        with self.assertRaises(llm_client.LLMError) as ctx:
            llm_client.check_context_budget(
                "m1", {"context_window": 1000}, "", "拆" * 5000, max_tokens=100)
        self.assertIn("不是模型拒答", str(ctx.exception))

    def test_error_names_the_model(self):
        with self.assertRaises(llm_client.LLMError) as ctx:
            llm_client.check_context_budget(
                "my-model", {"context_window": 1000}, "", "拆" * 5000, max_tokens=100)
        self.assertIn("my-model", str(ctx.exception))

    def test_system_prompt_counts_toward_budget(self):
        """system 也占预算，不能只算 user。"""
        model = {"context_window": 1000}
        budget = 1000 - 100 - llm_client._RESPONSE_HEADROOM_TOKENS
        # user 本身没超，加上 system 就超了
        with self.assertRaises(llm_client.LLMError):
            llm_client.check_context_budget(
                "m1", model, "拆" * budget, "拆" * 10, max_tokens=100)

    def test_max_tokens_reduces_available_budget(self):
        """max_tokens 越大，留给 prompt 的空间越小。"""
        model = {"context_window": 1000}
        text = "拆" * 300
        # max_tokens=100 → budget=388，300 装得下
        llm_client.check_context_budget("m1", model, "", text, max_tokens=100)
        # max_tokens=600 → budget=-112，装不下
        with self.assertRaises(llm_client.LLMError):
            llm_client.check_context_budget("m1", model, "", text, max_tokens=600)


class TestBudgetErrorIsNotRetryable(unittest.TestCase):
    """超预算不能重试——同样输入再发一次还是一样超，重试只是白烧钱。"""

    def test_budget_error_marked_non_retryable(self):
        try:
            llm_client.check_context_budget(
                "m1", {"context_window": 1000}, "", "拆" * 5000, max_tokens=100)
        except llm_client.LLMError as exc:
            self.assertFalse(llm_client._is_retryable_error(exc))
        else:
            self.fail("应当抛 LLMError")

    def test_network_error_still_retryable(self):
        """对照：网络错误仍应可重试，别把重试机制整个关掉。"""
        self.assertTrue(llm_client._is_retryable_error(
            llm_client.LLMError("连接超时")))

    def test_auth_error_still_non_retryable(self):
        """既有契约不回退：401 依然不可重试。"""
        self.assertFalse(llm_client._is_retryable_error(
            llm_client.LLMError("HTTP 401 Unauthorized")))


class TestChatOneWiresTheCheck(unittest.TestCase):
    """接线守卫：函数写了但没接进调用链，等于没写。"""

    def test_chat_one_calls_check_before_request(self):
        """检查必须在 handler 之前发生——先烧钱再报错等于没防。"""
        calls = []

        def fake_handler(model, api_key, system, user, max_tokens, temperature):
            calls.append("handler")
            return {"text": "ok", "prompt_tokens": 1, "completion_tokens": 1}

        def fake_check(*args, **kwargs):
            calls.append("check")
            return {"ok": True}

        model = {"protocol": "openai", "model_name": "m",
                 "base_url": "http://x", "api_key_env": "K",
                 "context_window": 128000}
        with mock.patch.dict(llm_client.PROTOCOL_HANDLERS, {"openai": fake_handler}), \
             mock.patch.object(llm_client, "check_context_budget", fake_check), \
             mock.patch.object(llm_client, "resolve_api_key", return_value="k"):
            llm_client._chat_one("m1", model, "u", "s", 100, 0.3, 0, None, False)

        self.assertEqual(calls, ["check", "handler"],
                         "check_context_budget 必须在 handler 之前调用")

    def test_chat_one_caps_output_to_available_context(self):
        captured = {}

        def fake_handler(model, api_key, system, user, max_tokens, temperature):
            captured["max_tokens"] = max_tokens
            return {"text": "ok", "prompt_tokens": 1, "completion_tokens": 1}

        model = {"protocol": "openai", "model_name": "m",
                 "base_url": "http://x", "api_key_env": "K",
                 "context_window": 32768}
        with mock.patch.dict(llm_client.PROTOCOL_HANDLERS, {"openai": fake_handler}), \
             mock.patch.object(llm_client, "resolve_api_key", return_value="k"):
            llm_client._chat_one("m1", model, "拆书输入", "系统要求", 32768, 0.3, 0, None, False)

        self.assertGreater(captured["max_tokens"], 0)
        self.assertLess(captured["max_tokens"], 32768)
        prompt_tokens = llm_client.estimate_tokens("拆书输入") + llm_client.estimate_tokens("系统要求")
        self.assertLessEqual(
            prompt_tokens + captured["max_tokens"] + llm_client._RESPONSE_HEADROOM_TOKENS,
            32768,
        )

    def test_chat_one_keeps_output_budget_when_it_fits(self):
        captured = {}

        def fake_handler(model, api_key, system, user, max_tokens, temperature):
            captured["max_tokens"] = max_tokens
            return {"text": "ok", "prompt_tokens": 1, "completion_tokens": 1}

        model = {"protocol": "openai", "model_name": "m",
                 "base_url": "http://x", "api_key_env": "K",
                 "context_window": 128000}
        with mock.patch.dict(llm_client.PROTOCOL_HANDLERS, {"openai": fake_handler}), \
             mock.patch.object(llm_client, "resolve_api_key", return_value="k"):
            llm_client._chat_one("m1", model, "u", "s", 8192, 0.3, 0, None, False)

        self.assertEqual(captured["max_tokens"], 8192)

    def test_chat_one_propagates_budget_error(self):
        """超预算的异常必须冒泡出去，不能被 _chat_one 吞掉。"""
        def fake_handler(*a, **k):
            raise AssertionError("handler 不该被调用——请求应该已被拦下")

        model = {"protocol": "openai", "model_name": "m",
                 "base_url": "http://x", "api_key_env": "K",
                 "context_window": 1000}
        with mock.patch.dict(llm_client.PROTOCOL_HANDLERS, {"openai": fake_handler}), \
             mock.patch.object(llm_client, "resolve_api_key", return_value="k"):
            with self.assertRaises(llm_client.LLMError) as ctx:
                llm_client._chat_one("m1", model, "拆" * 5000, "", 100, 0.3, 0, None, False)
        self.assertIn("超出上下文预算", str(ctx.exception))

    def test_chat_one_does_not_retry_budget_error(self):
        """单模型路径下也不能重试超预算错误。"""
        attempts = []

        def fake_handler(*a, **k):
            attempts.append(1)
            return {"text": "ok", "prompt_tokens": 1, "completion_tokens": 1}

        model = {"protocol": "openai", "model_name": "m",
                 "base_url": "http://x", "api_key_env": "K",
                 "context_window": 1000}
        with mock.patch.dict(llm_client.PROTOCOL_HANDLERS, {"openai": fake_handler}), \
             mock.patch.object(llm_client, "resolve_api_key", return_value="k"):
            with self.assertRaises(llm_client.LLMError):
                # retries=3 也不该重试
                llm_client._chat_one("m1", model, "拆" * 5000, "", 100, 0.3, 3, None, False)
        self.assertEqual(attempts, [], "超预算时 handler 一次都不该被调用")


class TestRealWorldRegression(unittest.TestCase):
    """用实测数据回归：中文语料撑爆窗口必须拦下，英文同字符数则放行。"""

    def test_chinese_313k_chars_blocked_by_128k_model(self):
        """2026-11-16 实测：313,137 个汉字 ≈ 313,137 tokens，是 128K 窗口的 2.4 倍。"""
        model = {"context_window": 128000}
        with self.assertRaises(llm_client.LLMError) as ctx:
            llm_client.check_context_budget(
                "deepseek-4.1-flash", model, "你是拆书助手", "拆" * 313137,
                max_tokens=8192)
        msg = str(ctx.exception)
        self.assertIn("128000", msg)
        # prompt 估算含 system（6 字），故为 313143 而非 313137
        self.assertIn("313143", msg)

    def test_english_313k_chars_passes_128k_model(self):
        """对照（纠正 11-11 的错误归因）：同样 313,137 字符的英文只合 78,524 tokens，
        128K 窗口装得下，必须放行——不能按字符数一刀切。"""
        model = {"context_window": 128000}
        info = llm_client.check_context_budget(
            "m1", model, "", "a" * 313137, max_tokens=8192)
        self.assertTrue(info["ok"])
        self.assertLess(info["prompt_tokens"], 128000)

    def test_pass4_130k_chinese_chars_blocked(self):
        """pass4 中文 130,578 字符，同样超 128K 窗口。"""
        with self.assertRaises(llm_client.LLMError):
            llm_client.check_context_budget(
                "m1", {"context_window": 128000}, "", "拆" * 130578, max_tokens=8192)

    def test_pass3_40k_chars_passes(self):
        """对照：pass3 只有 40K 字符，必须放行——不能一刀切全拦。"""
        info = llm_client.check_context_budget(
            "m1", {"context_window": 128000}, "", "拆" * 40000, max_tokens=16384)
        self.assertTrue(info["ok"])


if __name__ == "__main__":
    unittest.main()
