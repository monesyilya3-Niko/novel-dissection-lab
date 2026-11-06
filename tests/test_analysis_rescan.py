"""主循环必须真的重扫 pending 批（2026-11-05）。

背景：``retry_failed`` 在线程存活时把失败批改回 ``pending``，并在返回值里
承诺「线程运行中，将在当前循环内重扫」。但原实现是单趟
``for ci: for b:``，循环走过那些位置后不会再回来——pending 批永远不会被
再次访问，接口 200、提示说会重扫、实际什么也没发生。

现在整趟遍历结束后，只要还有 pending 批就再扫一轮，上限
``_MAX_RESCAN_ROUNDS`` 防止「一直失败 → 一直 pending」把线程卡死。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestRescanLoopExists(unittest.TestCase):
    def test_max_rescan_rounds_defined(self):
        from gui import services
        self.assertIsInstance(services._MAX_RESCAN_ROUNDS, int)
        self.assertGreater(services._MAX_RESCAN_ROUNDS, 0,
                           "重扫上限必须为正，否则永远不重扫")
        self.assertLessEqual(services._MAX_RESCAN_ROUNDS, 10,
                             "重扫上限过大可能让线程长时间卡住")

    def test_loop_contains_pending_rescan(self):
        """源码层面确认主循环里真的检查了 pending。"""
        src = (ROOT / "gui" / "services.py").read_text(encoding="utf-8")
        start = src.find("_rescan_rounds = 0")
        self.assertGreater(start, 0, "主循环缺少重扫轮次计数")
        tail = src[start:start + 4000]
        self.assertIn('"pending"', tail,
                      "重扫判定里没有检查 pending 状态")
        self.assertIn("_MAX_RESCAN_ROUNDS", tail,
                      "重扫缺少上限保护")

    def test_rescan_respects_stop_flag(self):
        """停止标志置位时不得继续重扫。"""
        src = (ROOT / "gui" / "services.py").read_text(encoding="utf-8")
        start = src.find("_rescan_rounds = 0")
        tail = src[start:start + 2000]
        self.assertIn("stop_flag", tail,
                      "重扫循环未检查 stop_flag，停止请求可能被忽略")


class TestRetryFailedRollback(unittest.TestCase):
    """retry_failed 在无法真正续传时不得留下卡死的 pending 批（2026-11-05）。

    原实现先把 failed 改成 pending、再调 resume()。resume() 会做题材校验等，
    一旦抛错，刚写的 pending 就永久留着：主循环不在跑、没人重扫、任务状态
    还是 error。实测症状：批状态停在 pending，用户既看不到进度也无法推进。
    """

    def setUp(self):
        import tempfile
        from pathlib import Path as _P

        from tests import _isolation
        self._tmp = tempfile.mkdtemp(prefix="retry_rb_")
        self._iso = _isolation.isolate_paths(_P(self._tmp))
        self._iso.__enter__()
        from gui import db
        db.init_schema()
        db.apply_migrations()

    def tearDown(self):
        self._iso.__exit__(None, None, None)

    def _make_book(self, genre: str) -> str:
        from pathlib import Path as _P

        from gui import services, state_store
        src = _P(self._tmp) / f"book-{genre}.txt"
        src.write_text("\n\n".join(f"第{i}章\n" + "正文。" * 200 for i in range(1, 4)),
                       encoding="utf-8")
        bid = services.import_book(str(src))["book_id"]
        with state_store.update_state(bid) as st:
            st["genre"] = genre
            st["status"] = "error"
            state_store.set_batch_state(st, 1, 0, "failed")
        services._runtime.pop(bid, None)
        return bid

    def test_unknown_genre_leaves_batch_failed(self):
        from gui import services, state_store
        bid = self._make_book("unknown")
        with self.assertRaises(services.ServiceError):
            services.retry_failed(bid)
        st = state_store.load_state(bid)
        self.assertEqual(st["chapter_states"]["c1-b0"]["status"], "failed",
                         "续传失败后批卡在 pending，没人会再处理它")
        self.assertEqual(st.get("status"), "error")

    def test_valid_genre_passes_precheck(self):
        from gui import services
        bid = self._make_book("dushi-richang")
        services._precheck_resumable(bid)   # 不抛即通过


if __name__ == "__main__":
    unittest.main()
