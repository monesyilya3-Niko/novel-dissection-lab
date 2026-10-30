"""gzip 响应压缩回归（2026-10-30）。

背景：/api/tropes 返回 176 条桥段的完整骨架，实测 369KB 明文。前端打开
「桥段灵感」面板需要一次拉全量（本地全文搜索依赖骨架文本），于是每次
打开都要等这部分传输。服务端此前没有压缩，纯文本吃满带宽。

设计约束（测试逐条守住）：
1. 只在客户端声明 Accept-Encoding: gzip 时才压缩；
2. 小响应（< 1KB）不压缩——压缩头本身会抵消收益；
3. 解压后必须与明文**逐字节一致**（否则前端 JSON.parse 直接炸）；
4. 压缩失败要退回明文，不能因为"优化"把接口搞挂。

隔离纪律（AGENTS.md §4）：真实 GuiServer 会初始化 SQLite / 备份 / 锁，
路径常量必须成对 patch，否则会写进真实的 gui_state/。
"""
from __future__ import annotations

import gzip
import json
import socket
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _isolation  # noqa: E402

from gui import config  # noqa: E402


class TestGzipResponses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from gui import server as server_mod

        cls._tmp = Path(tempfile.mkdtemp(prefix="gzip_qa_"))
        cls._orig = {k: getattr(config, k) for k in (
            "ASSETS_ROOT", "REPORTS_DIR", "CORPUS_DIR", "CONFIG_DIR",
            "STATE_ROOT", "DB_PATH", "LOCK_PATH", "STATE_JSON_DIR", "API_TOKEN")}
        config.ASSETS_ROOT = cls._tmp / "assets"
        config.REPORTS_DIR = cls._tmp / "reports"
        config.CORPUS_DIR = cls._tmp / "corpus"
        config.CONFIG_DIR = cls._tmp / "config"
        config.STATE_ROOT = cls._tmp / "gui_state"
        config.DB_PATH = config.STATE_ROOT / "index.db"
        config.LOCK_PATH = config.STATE_ROOT / ".lock"
        config.STATE_JSON_DIR = cls._tmp / "gui_state"
        config.API_TOKEN = ""  # 免令牌，聚焦压缩行为
        for d in (config.ASSETS_ROOT, config.REPORTS_DIR, config.CORPUS_DIR,
                  config.CONFIG_DIR, config.STATE_ROOT):
            d.mkdir(parents=True, exist_ok=True)

        # 备份钩子替换为 no-op：真实备份会写用户数据目录
        cls._orig_bk = (server_mod.auto_backup.startup_backup,
                        server_mod.auto_backup.daily_backup_if_due)
        server_mod.auto_backup.startup_backup = lambda: None
        server_mod.auto_backup.daily_backup_if_due = lambda: None

        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        cls.srv = server_mod.GuiServer(preferred_port=port)
        _host, cls.port = cls.srv.start()

    @classmethod
    def tearDownClass(cls):
        from gui import server as server_mod

        cls.srv.shutdown()
        server_mod.auto_backup.startup_backup, server_mod.auto_backup.daily_backup_if_due = cls._orig_bk
        for k, v in cls._orig.items():
            setattr(config, k, v)
        _isolation.remove_tree(cls._tmp)

    def _fetch(self, path: str, accept_gzip: bool = True):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
        if accept_gzip:
            req.add_header("Accept-Encoding", "gzip")
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read(), r.headers.get("Content-Encoding"), r.status

    def test_large_response_is_gzipped_and_identical(self):
        """/api/tropes 体积大，应压缩；解压后必须与明文完全一致。"""
        raw_gz, enc, status = self._fetch("/api/tropes", True)
        raw_plain, enc_plain, _ = self._fetch("/api/tropes", False)
        self.assertEqual(status, 200)
        self.assertGreater(len(raw_plain), 1024, "该端点应是大响应，否则本测试无意义")
        self.assertEqual(enc, "gzip")
        self.assertIsNone(enc_plain, "未声明 Accept-Encoding 时不应压缩")
        self.assertEqual(gzip.decompress(raw_gz), raw_plain,
                         "解压后必须与明文逐字节一致，否则前端 JSON.parse 会失败")
        self.assertLess(len(raw_gz), len(raw_plain), "压缩后应该更小")

    def test_no_accept_encoding_header_returns_plain(self):
        raw, enc, _ = self._fetch("/api/tropes", False)
        self.assertIsNone(enc)
        json.loads(raw)  # 明文可直接解析

    def test_small_response_not_compressed(self):
        """< 1KB 的响应压缩头会抵消收益，应保持明文。"""
        raw, enc, _ = self._fetch("/api/overview", True)
        self.assertIsNone(enc, "小响应不应压缩")
        json.loads(raw)

    def test_gzip_payload_parses_as_json(self):
        raw_gz, enc, _ = self._fetch("/api/assets", True)
        if enc == "gzip":
            data = json.loads(gzip.decompress(raw_gz))
            self.assertIn("code", data)
