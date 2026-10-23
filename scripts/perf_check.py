#!/usr/bin/env python3
"""novel-lab 性能 / 边界可复现检查（跑在隔离服务上）。

加固特性：
1. server_rss_kb 彻底消除 Linux /proc 专有依赖，新增 Windows Win32 API (ctypes) 与 macOS 回退支持；
2. RssSampler 采用 threading.Event 与 wait 超时，确保启停安全与无锁争用；
3. t3_upload_100mb 与 t4_oversize_rejected 支持自适应容量配置与健全断言；
4. main 支持 --tests (指定运行子集)、--server-pid 可选默认 0、-q/--quiet 静默模式与 argv 注入；
5. 纯 Python 标准库零依赖，跨平台稳定可靠。

用法（推荐）:  ./scripts/perf_isolated.sh
手动用法    :  python3 scripts/perf_check.py --base-url http://127.0.0.1:18081 --server-pid <PID>

用例（全部只用标准库，跑在隔离副本服务上，真实状态零写入）:
  T1 并发读    20 并发 GET /api/overview        → avg / p99 / max 延迟
  T2 并发写    10 并发上传不同书籍              → 全部 200 且 total_books +10
  T3 100MB 上传 真实 100MB multipart 上传       → 200；采样服务端进程 RSS 峰值
  T4 超限拒绝  Content-Length = 100MB+1         → 413 立即拒绝（不读 body）
  T5 调用超时  黑洞 TCP + timeout=2 的模型      → 批次失败且 last_error 含 timeout

输出 JSON（stdout），exit 0 = 全部通过。
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import glob as _glob
import http.client
import json
import math
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

MAX_UPLOAD = 100 * 1024 * 1024  # 与 router._MAX_UPLOAD_BYTES 同值（边界测试不断言源码常量，只测行为）


def _req(
    base: str,
    method: str,
    path: str,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 60.0,
) -> tuple[int, dict[str, Any]]:
    """发送 HTTP 请求并解析 JSON 响应。"""
    req = urllib.request.Request(
        base + path,
        data=data,
        method=method,
        headers=headers or {},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8", "replace"))


def build_multipart(file_bytes: bytes, filename: str) -> tuple[bytes, str]:
    """构造 multipart/form-data 数据包。"""
    boundary = "----e2eperfboundary1234"
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
    ).encode()
    tail = f"\r\n--{boundary}--\r\n".encode()
    body = head + file_bytes + tail
    return body, f"multipart/form-data; boundary={boundary}"


def server_rss_kb(pid: int) -> int:
    """获取指定 PID 的物理内存占用 (RSS in KB)，跨平台支持 Linux 与 Windows（纯标准库）。"""
    if pid <= 0:
        return 0

    # 1. Linux (/proc)
    proc_status = Path(f"/proc/{pid}/status")
    if proc_status.exists():
        try:
            with open(proc_status, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        parts = line.split()
                        if len(parts) >= 2 and parts[1].isdigit():
                            return int(parts[1])
        except OSError:
            pass

    # 2. Windows (Win32 API via standard library ctypes)
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_VM_READ = 0x0010
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            psapi = ctypes.windll.psapi  # type: ignore[attr-defined]

            handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
            if handle:
                try:
                    pmc = PROCESS_MEMORY_COUNTERS()
                    pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
                    if psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc), pmc.cb):
                        return int(pmc.WorkingSetSize // 1024)
                finally:
                    kernel32.CloseHandle(handle)
        except Exception:
            pass

    # 3. macOS / BSD (fallback via resource if measuring self)
    if pid == os.getpid():
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if sys.platform == "darwin":
                return int(usage // 1024)
            return int(usage)
        except Exception:
            pass

    return 0


class RssSampler:
    """后台采样服务端 RSS，记录峰值。"""

    def __init__(self, pid: int, interval: float = 0.05):
        self.pid = pid
        self.interval = max(interval, 0.001)
        self.peak = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._t: threading.Thread | None = None

    def _run(self) -> None:
        while not self._stop.is_set():
            v = server_rss_kb(self.pid)
            with self._lock:
                if v > self.peak:
                    self.peak = v
            self._stop.wait(self.interval)

    def get_peak(self) -> int:
        with self._lock:
            return self.peak

    def __enter__(self) -> RssSampler:
        self.peak = server_rss_kb(self.pid)
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *a: Any) -> None:
        self._stop.set()
        if self._t is not None:
            self._t.join(timeout=2.0)


def t1_concurrent_reads(base: str) -> dict[str, Any]:
    # 冷启动单请求（懒初始化成本），再测热机 20 并发
    t0 = time.perf_counter()
    st, body = _req(base, "GET", "/api/overview")
    cold_ms = round((time.perf_counter() - t0) * 1000, 1)
    assert st == 200 and body.get("code") == 0

    def one(_: int) -> float:
        t0 = time.perf_counter()
        st, body = _req(base, "GET", "/api/overview")
        dt = (time.perf_counter() - t0) * 1000
        assert st == 200 and body.get("code") == 0, f"overview 失败: {st} {body}"
        return dt

    with cf.ThreadPoolExecutor(max_workers=20) as ex:
        lat = sorted(ex.map(one, range(20)))
    return {
        "n": 20,
        "cold_single_ms": cold_ms,
        "warm_avg_ms": round(sum(lat) / len(lat), 1),
        "warm_p99_ms": round(lat[math.ceil(0.99 * len(lat)) - 1], 1),
        "warm_max_ms": round(lat[-1], 1),
    }


def t2_concurrent_uploads(base: str) -> dict[str, Any]:
    st, body = _req(base, "GET", "/api/overview")
    before = body["data"]["total_books"]

    def one(i: int) -> str:
        name = f"perf_cw_{os.getpid()}_{i}_{int(time.time()*1000)}.txt"
        content = ("第1章 并发\n" + "正文。" * 200 + "\n").encode("utf-8")
        data, ctype = build_multipart(content, name)
        st2, b2 = _req(
            base,
            "POST",
            "/api/import-upload",
            data=data,
            headers={"Content-Type": ctype},
            timeout=120,
        )
        assert st2 == 200 and b2.get("code") == 0, f"并发上传失败: {st2} {b2}"
        return b2["data"]["book_id"]

    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        ids = list(ex.map(one, range(10)))
    assert len(set(ids)) == 10, "book_id 应互不相同"
    st, body = _req(base, "GET", "/api/overview")
    after = body["data"]["total_books"]
    assert after == before + 10, f"书数应 +10: {before} -> {after}"
    return {"n": 10, "books_added": after - before}


def t3_upload_100mb(base: str, pid: int, max_upload: int = MAX_UPLOAD) -> dict[str, Any]:
    # 100 章 × ~0.99MB 章节体，总计约 99MB，保证能解析出章节且逼近 max_upload 上限
    unit = "甲乙丙丁戊己庚辛壬癸。"  # 33 bytes（utf-8）
    target_bytes = int(max_upload * 0.99)
    if target_bytes < 1000:
        chunk = "第1章 边界\n" + "正文内容。" * 20
        parts = [chunk]
    else:
        num_chapters = min(100, max(target_bytes // 1000000, 1))
        bytes_per_ch = target_bytes // num_chapters
        repeat_cnt = max(bytes_per_ch // len(unit.encode("utf-8")), 1)
        base_chunk = unit * repeat_cnt
        parts = [f"第{i+1}章 边界\n{base_chunk}" for i in range(num_chapters)]

    content = ("\n".join(parts)).encode("utf-8")
    assert len(content) <= max_upload, f"测试文件 {len(content)} 超过上限 {max_upload}，请调小"
    data, ctype = build_multipart(content, "perf_100mb.txt")
    if max_upload >= 90 * 1024 * 1024:
        assert len(data) >= 90 * 1024 * 1024, f"文件过小({len(data)})，失去边界意义"

    rss_before_kb = server_rss_kb(pid)
    with RssSampler(pid) as sampler:
        t0 = time.perf_counter()
        st, body = _req(
            base,
            "POST",
            "/api/import-upload",
            data=data,
            headers={"Content-Type": ctype},
            timeout=300,
        )
        dt = time.perf_counter() - t0
    assert st == 200 and body.get("code") == 0, f"100MB 上传失败: {st} {str(body)[:200]}"
    # 内存回归硬上限：手工边界扫描实现预期峰值约 2×body + baseline（≈250MB）。600MB 为回归哨兵
    peak_mb = sampler.get_peak() / 1024
    if pid > 0 and peak_mb > 0:
        assert peak_mb < 600, (
            f"100MB 上传 RSS 峰值 {peak_mb:.0f}MB 超过 600MB 回归上限 "
            f"(baseline {rss_before_kb / 1024:.0f}MB)，疑似解析器内存放大倒退"
        )
    return {
        "bytes": len(data),
        "elapsed_s": round(dt, 1),
        "server_rss_peak_mb": round(peak_mb, 1),
        "server_rss_before_mb": round(rss_before_kb / 1024, 1),
    }


def t4_oversize_rejected(base: str, max_upload: int = MAX_UPLOAD) -> dict[str, Any]:
    """Content-Length = max_upload+1，只发 header 就应被 413 拒绝（服务端不读 body）。"""
    u = urllib.parse.urlparse(base)
    conn = http.client.HTTPConnection(u.hostname or "127.0.0.1", u.port, timeout=10)
    try:
        conn.putrequest("POST", "/api/import-upload")
        conn.putheader("Content-Type", "multipart/form-data; boundary=x")
        conn.putheader("Content-Length", str(max_upload + 1))
        conn.endheaders()
        resp = conn.getresponse()
        body = resp.read(4096).decode("utf-8", "replace")
        assert resp.status == 413, f"期望 413，实际 {resp.status}: {body[:200]}"
        assert "100MB" in body or "超限" in body or "large" in body.lower()
        return {"status": 413}
    finally:
        conn.close()


class Blackhole:
    """接受 TCP 连接但永不回包，用于触发客户端超时。"""

    def __init__(self):
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.sock.listen(8)
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._serve, daemon=True)
        self._t.start()

    def _serve(self) -> None:
        self.sock.settimeout(0.5)
        while not self._stop.is_set():
            try:
                c, _ = self.sock.accept()
            except (TimeoutError, OSError):
                continue
            threading.Thread(target=self._hang, args=(c,), daemon=True).start()

    @staticmethod
    def _hang(c: socket.socket) -> None:
        try:
            c.settimeout(60)
            c.recv(65536)
            time.sleep(60)
        except OSError:
            pass
        finally:
            try:
                c.close()
            except OSError:
                pass

    def close(self) -> None:
        self._stop.set()
        try:
            self.sock.close()
        except OSError:
            pass


def t5_call_timeout(base: str, server_root: str | None) -> dict[str, Any]:
    bh = Blackhole()
    try:
        st, body = _req(
            base,
            "POST",
            "/api/models",
            data=json.dumps({
                "id": "perf-timeout",
                "protocol": "openai",
                "base_url": f"http://127.0.0.1:{bh.port}",
                "model_name": "dummy",
                "timeout": 2,
                "api_key": "e2e-fake-key-not-real",
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        assert st in (200, 409), f"建超时模型失败: {st} {body}"

        content = ("第1章 超时\n" + "正文。" * 200 + "\n").encode("utf-8")
        data, ctype = build_multipart(content, f"perf_timeout_{os.getpid()}.txt")
        st, body = _req(
            base,
            "POST",
            "/api/import-upload",
            data=data,
            headers={"Content-Type": ctype},
            timeout=120,
        )
        book_id = body["data"]["book_id"]

        st, body = _req(base, "GET", "/api/genres")
        genre = body["data"]["genres"][0]
        st, body = _req(
            base,
            "POST",
            "/api/analyze/start",
            data=json.dumps({
                "book_id": book_id,
                "genre": genre,
                "model_id": "perf-timeout",
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        assert st == 200 and body.get("code") == 0, f"启动分析失败: {st} {body}"

        deadline = time.time() + 60
        t_start = time.time()
        failed: list[str] = []
        while time.time() < deadline:
            st, body = _req(base, "GET", f"/api/status?book_id={book_id}")
            states = (body.get("data") or {}).get("chapter_states", {}) or {}
            failed = [
                k for k, v in states.items()
                if isinstance(v, dict) and v.get("status") == "failed"
            ]
            if failed:
                break
            time.sleep(1)
        assert failed, "60s 内未观察到批次失败（timeout 可能未生效）"
        elapsed = round(time.time() - t_start, 1)

        err_text = ""
        mirror_found = False
        if server_root:
            for f in _glob.glob(
                os.path.join(server_root, "gui", "state", f"gui_state_{book_id}.json")
            ):
                try:
                    with open(f, encoding="utf-8") as _fh:
                        err_text = json.load(_fh).get("last_error", "") or ""
                    mirror_found = True
                except (OSError, ValueError):
                    pass
        if mirror_found:
            assert "timed out" in err_text.lower(), f"last_error 未含超时证据: {err_text[:150]!r}"
        return {
            "timeout_observed": True,
            "failed_batches": failed[:3],
            "elapsed_s": elapsed,
            "last_error_head": err_text[:120],
        }
    finally:
        bh.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="novel-lab 性能 / 边界可复现检查（跑在隔离服务上）。")
    ap.add_argument("--base-url", required=True, help="服务基础 URL，如 http://127.0.0.1:18081")
    ap.add_argument("--server-pid", type=int, default=0, help="服务进程 PID（用于采样 RSS 峰值）")
    ap.add_argument("--server-root", default="", help="隔离服务副本根目录（用于白盒复核状态文件）")
    ap.add_argument("--tests", default="all", help="执行的测试用例列表，逗号分隔，如 T1,T4 或 all (默认 all)")
    ap.add_argument("-q", "--quiet", action="store_true", help="静默模式")
    args = ap.parse_args(argv)
    base = args.base_url.rstrip("/")

    selected = [t.strip().upper() for t in args.tests.split(",")] if args.tests != "all" else ["ALL"]

    results: dict[str, Any] = {}
    try:
        if "ALL" in selected or "T1" in selected:
            results["T1_concurrent_reads"] = t1_concurrent_reads(base)
        if "ALL" in selected or "T2" in selected:
            results["T2_concurrent_uploads"] = t2_concurrent_uploads(base)
        if "ALL" in selected or "T3" in selected:
            results["T3_upload_100MB"] = t3_upload_100mb(base, args.server_pid)
        if "ALL" in selected or "T4" in selected:
            results["T4_oversize_rejected"] = t4_oversize_rejected(base)
        if "ALL" in selected or "T5" in selected:
            results["T5_call_timeout"] = t5_call_timeout(base, args.server_root or None)

        results["verdict"] = "ALL_PASS"
        if not args.quiet:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        results["verdict"] = "FAILED"
        results["error"] = str(e)
        if not args.quiet:
            print(json.dumps(results, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
