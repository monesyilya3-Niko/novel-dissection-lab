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


if __name__ == "__main__":
    unittest.main()
