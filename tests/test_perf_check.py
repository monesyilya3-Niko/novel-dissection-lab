#!/usr/bin/env python3
"""性能与边界可复现检查引擎（scripts/perf_check.py）独立单元测试套件。

覆盖范围：
1. server_rss_kb 内存占用采样（PID 边界、当前进程真机物理内存采样、/proc 解析与 Windows ctypes 适配）
2. RssSampler 异步采样上下文管理器生命周期与峰值统计
3. build_multipart multipart/form-data 报文组装规范性
4. Blackhole 挂起服务端口绑定、连接挂起与安全释放
5. _req HTTP 请求与 HTTPError 响应处理
6. t1_concurrent_reads 并发读延时分布测算
7. t2_concurrent_uploads 并发写冲突与去重验证
8. t3_upload_100mb 大文件切片组装与 RSS 峰值回归哨兵
9. t4_oversize_rejected 413 超限早停拒绝
10. t5_call_timeout 黑洞调用与超时状态追踪
11. main CLI 命令行参数解析、用例筛选（--tests）与异常返回码
"""
from __future__ import annotations

import gc
import json
import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import perf_check


class TestPerfCheck(unittest.TestCase):
    """性能检查工具全维独立测试集。"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="perf_check_test_")
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self):
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except OSError:
            pass

    # -------------------------------------------------------------------------
    # 1. server_rss_kb 与 RssSampler 测试
    # -------------------------------------------------------------------------

    def test_server_rss_kb_zero_or_negative(self):
        self.assertEqual(perf_check.server_rss_kb(0), 0)
        self.assertEqual(perf_check.server_rss_kb(-10), 0)

    def test_server_rss_kb_current_process(self):
        # 针对当前测试进程实测采样，必须大于 0 KB
        rss = perf_check.server_rss_kb(os.getpid())
        self.assertGreater(rss, 0)

    def test_server_rss_kb_mock_proc_status(self):
        mock_data = "Name:\tpython\nVmSize:\t  50000 kB\nVmRSS:\t  34567 kB\nVmData:\t  12000 kB\n"
        with patch.object(Path, "exists", return_value=True), \
             patch("builtins.open", unittest.mock.mock_open(read_data=mock_data)):
            rss = perf_check.server_rss_kb(12345)
            self.assertEqual(rss, 34567)

    def test_rss_sampler_lifecycle(self):
        with perf_check.RssSampler(os.getpid(), interval=0.01) as sampler:
            peak = sampler.get_peak()
            self.assertGreater(peak, 0)
        self.assertGreaterEqual(sampler.get_peak(), peak)

    # -------------------------------------------------------------------------
    # 2. build_multipart 与 Blackhole 测试
    # -------------------------------------------------------------------------

    def test_build_multipart(self):
        payload = b"test novel chapter content"
        filename = "chapter_01.txt"
        data, ctype = perf_check.build_multipart(payload, filename)

        self.assertIn("multipart/form-data; boundary=", ctype)
        boundary = ctype.split("boundary=")[1]
        self.assertTrue(data.startswith(f"--{boundary}".encode()))
        self.assertTrue(data.endswith(f"--{boundary}--\r\n".encode()))
        self.assertIn(b'name="file"; filename="chapter_01.txt"', data)
        self.assertIn(payload, data)

    def test_blackhole_lifecycle(self):
        bh = perf_check.Blackhole()
        try:
            self.assertGreater(bh.port, 0)
            s = socket.socket()
            s.settimeout(1.0)
            s.connect(("127.0.0.1", bh.port))
            s.sendall(b"PING")
            s.close()
        finally:
            bh.close()

    # -------------------------------------------------------------------------
    # 3. HTTP 请求与测试用例验证
    # -------------------------------------------------------------------------

    def test_req_success_and_error(self):
        # 成功响应
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"code": 0, "msg": "ok"}'

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            st, body = perf_check._req("http://127.0.0.1:8000", "GET", "/api/overview")
            self.assertEqual(st, 200)
            self.assertEqual(body["code"], 0)

        # HTTPError 响应
        import urllib.error
        mock_err = urllib.error.HTTPError(
            url="http://127.0.0.1:8000/api/overview",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=MagicMock(read=lambda: b'{"code": 400, "error": "invalid"}'),
        )
        with patch("urllib.request.urlopen", side_effect=mock_err):
            st, body = perf_check._req("http://127.0.0.1:8000", "GET", "/api/overview")
            self.assertEqual(st, 400)
            self.assertEqual(body["code"], 400)

    def test_t1_concurrent_reads(self):
        mock_body = {"code": 0, "data": {"status": "running"}}
        with patch("scripts.perf_check._req", return_value=(200, mock_body)):
            res = perf_check.t1_concurrent_reads("http://127.0.0.1:8000")
            self.assertEqual(res["n"], 20)
            self.assertIn("cold_single_ms", res)
            self.assertIn("warm_avg_ms", res)
            self.assertIn("warm_p99_ms", res)
            self.assertIn("warm_max_ms", res)

    def test_t2_concurrent_uploads(self):
        responses = [
            (200, {"code": 0, "data": {"total_books": 5}}),
        ]
        for i in range(10):
            responses.append((200, {"code": 0, "data": {"book_id": f"book_{i}"}}))
        responses.append((200, {"code": 0, "data": {"total_books": 15}}))

        call_idx = [0]

        def mock_req(base, method, path, **kwargs):
            r = responses[min(call_idx[0], len(responses) - 1)]
            call_idx[0] += 1
            return r

        with patch("scripts.perf_check._req", side_effect=mock_req):
            res = perf_check.t2_concurrent_uploads("http://127.0.0.1:8000")
            self.assertEqual(res["n"], 10)
            self.assertEqual(res["books_added"], 10)

    def test_t3_upload_adaptive(self):
        # 使用 2000 字节自定义容量快速验证组装与上报
        mock_body = {"code": 0, "data": {"book_id": "book_100mb"}}
        with patch("scripts.perf_check._req", return_value=(200, mock_body)):
            res = perf_check.t3_upload_100mb("http://127.0.0.1:8000", pid=0, max_upload=2000)
            self.assertIn("bytes", res)
            self.assertIn("elapsed_s", res)
            self.assertIn("server_rss_peak_mb", res)

    def test_t4_oversize_rejected(self):
        mock_conn = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status = 413
        mock_resp.read.return_value = b'{"error": "100MB \xe8\xb6\x85\xe9\x99\x90\xe6\x8b\x92\xe7\xbb\x9d"}'
        mock_conn.getresponse.return_value = mock_resp

        with patch("http.client.HTTPConnection", return_value=mock_conn):
            res = perf_check.t4_oversize_rejected("http://127.0.0.1:8000")
            self.assertEqual(res["status"], 413)

    def test_t5_call_timeout(self):
        # 模拟响应序列：
        # 1. /api/models -> 200
        # 2. /api/import-upload -> 200 {"data": {"book_id": "b_to"}}
        # 3. /api/genres -> 200 {"data": {"genres": ["xuanhuan"]}}
        # 4. /api/analyze/start -> 200 {"code": 0}
        # 5. /api/status -> 200 {"data": {"chapter_states": {"ch_1": {"status": "failed"}}}}
        responses = {
            "/api/models": (200, {"code": 0}),
            "/api/import-upload": (200, {"data": {"book_id": "b_to"}}),
            "/api/genres": (200, {"data": {"genres": ["xuanhuan"]}}),
            "/api/analyze/start": (200, {"code": 0}),
            "/api/status?book_id=b_to": (200, {"data": {"chapter_states": {"ch_1": {"status": "failed"}}}}),
        }

        def mock_req(base, method, path, **kwargs):
            return responses.get(path, (200, {"code": 0}))

        server_root = self.tmp_path / "server_root"
        state_dir = server_root / "gui" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "gui_state_b_to.json"
        state_file.write_text(json.dumps({"last_error": "Connection timed out after 2s"}), encoding="utf-8")

        with patch("scripts.perf_check._req", side_effect=mock_req):
            res = perf_check.t5_call_timeout("http://127.0.0.1:8000", str(server_root))
            self.assertTrue(res["timeout_observed"])
            self.assertEqual(res["failed_batches"], ["ch_1"])
            self.assertIn("timed out", res["last_error_head"].lower())

    # -------------------------------------------------------------------------
    # 4. main CLI 命令行接口测试
    # -------------------------------------------------------------------------

    def test_main_cli_filtered_success(self):
        with patch("scripts.perf_check.t1_concurrent_reads", return_value={"n": 20}):
            code = perf_check.main(["--base-url", "http://127.0.0.1:8000", "--tests", "T1", "-q"])
            self.assertEqual(code, 0)

    def test_main_cli_failure(self):
        with patch("scripts.perf_check.t1_concurrent_reads", side_effect=RuntimeError("connection refused")):
            code = perf_check.main(["--base-url", "http://127.0.0.1:8000", "--tests", "T1", "-q"])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
