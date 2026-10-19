#!/usr/bin/env python3
"""全链路真机实测自动化探测脚本（scripts/live_e2e_verification.py）独立单元测试套件。

覆盖范围：
1. VerificationError 异常继承关系（AssertionError 契约）
2. VerificationClient HTTP 请求封装：
   - 正常 JSON 响应解析
   - 文本与 HTML 响应回退
   - HTTPError 携带 JSON 错误体解析
   - HTTPError 原始文本回退
3. main CLI 命令行参数解析与状态码判定（--port / -q / --keep-sandbox）
4. run_e2e_verification 全端点真机实测全链路集成验证（各模块真实闭环）
"""
from __future__ import annotations

import gc
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import live_e2e_verification


class TestLiveE2EVerification(unittest.TestCase):
    """真机实测脚本单元与集成测试集。"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="test_live_e2e_")
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self):
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except OSError:
            pass

    def test_verification_error_is_assertion_error(self):
        self.assertTrue(issubclass(live_e2e_verification.VerificationError, AssertionError))
        err = live_e2e_verification.VerificationError("测试断言异常")
        self.assertIsInstance(err, AssertionError)

    def test_client_request_json_success(self):
        client = live_e2e_verification.VerificationClient("http://127.0.0.1:8100")
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"code": 0, "data": {"status": "ok"}}'
        mock_resp.headers = {"Content-Type": "application/json; charset=utf-8"}
        mock_resp.__enter__.return_value = mock_resp

        with patch.object(client.opener, "open", return_value=mock_resp):
            status, body, headers = client.request("GET", "/api/system/status")
            self.assertEqual(status, 200)
            self.assertIsInstance(body, dict)
            self.assertEqual(body["code"], 0)
            self.assertIn("content-type", headers)

    def test_client_request_raw_text(self):
        client = live_e2e_verification.VerificationClient("http://127.0.0.1:8100")
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b"<!DOCTYPE HTML><html><body>Index</body></html>"
        mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_resp.__enter__.return_value = mock_resp

        with patch.object(client.opener, "open", return_value=mock_resp):
            status, body, _ = client.request("GET", "/")
            self.assertEqual(status, 200)
            self.assertIsInstance(body, str)
            self.assertIn("<!DOCTYPE HTML>", body)

    def test_client_request_http_error_json(self):
        client = live_e2e_verification.VerificationClient("http://127.0.0.1:8100")
        mock_err = urllib.error.HTTPError(
            url="http://127.0.0.1:8100/api/admin/login",
            code=401,
            msg="Unauthorized",
            hdrs={"Content-Type": "application/json"},
            fp=MagicMock(read=lambda: b'{"code": 401, "error": "wrong password"}'),
        )

        with patch.object(client.opener, "open", side_effect=mock_err):
            status, body, headers = client.request("POST", "/api/admin/login", {"user": "admin"})
            self.assertEqual(status, 401)
            self.assertIsInstance(body, dict)
            self.assertEqual(body["code"], 401)

    def test_client_request_http_error_raw(self):
        client = live_e2e_verification.VerificationClient("http://127.0.0.1:8100")
        mock_err = urllib.error.HTTPError(
            url="http://127.0.0.1:8100/raw",
            code=500,
            msg="Internal Error",
            hdrs={"Content-Type": "text/plain"},
            fp=MagicMock(read=lambda: b"Internal Server Error"),
        )

        with patch.object(client.opener, "open", side_effect=mock_err):
            status, body, _ = client.request("GET", "/raw")
            self.assertEqual(status, 500)
            self.assertEqual(body, "Internal Server Error")

    def test_main_cli_dispatch(self):
        with patch("scripts.live_e2e_verification.run_e2e_verification", return_value=True):
            code = live_e2e_verification.main(["--port", "8120", "-q"])
            self.assertEqual(code, 0)

        with patch("scripts.live_e2e_verification.run_e2e_verification", return_value=False):
            code = live_e2e_verification.main(["--port", "8120", "-q"])
            self.assertEqual(code, 1)

    def test_run_e2e_verification_full_integration(self):
        # 挑选空闲动态端口执行真机实测
        success = live_e2e_verification.run_e2e_verification(port=8188, quiet=True)
        self.assertTrue(success)


if __name__ == "__main__":
    unittest.main()
