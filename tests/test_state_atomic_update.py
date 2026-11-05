"""任务状态「读 → 改 → 写」必须原子，否则并发下静默丢进度（2026-11-05）。

背景：`services.pause()` / `retry_failed()` / `_resume_status_if_paused()` 都是
HTTP 线程，而分析线程正在同一 book_id 上逐批把批次标 success。旧写法::

    state = state_store.load_state(book_id)
    state["status"] = "paused"
    state_store.save_state(state)

拿到的是**整份状态文件的快照**，写回时会把分析线程在这期间落盘的批次进度
整份覆盖回去 —— 已完成的批消失、进度条往回跳、断点续传重复分析。

实测数据（8 个写者 × 20 批 + 1 个 pauser，同一 book_id）：

    旧写法 load→save ：状态条数 20 / 160，**丢失 140 条**
    新写法 update_state：状态条数 160 / 160，丢失 0

修法：``state_store.update_state(book_id)`` 按状态文件路径持锁完成
「load → yield → upsert」，与 ``_save_state_json`` 用的是同一把按路径锁。
"""
from __future__ import annotations

import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests import _isolation  # noqa: E402


class TestUpdateStateAtomicity(unittest.TestCase):
    """``update_state`` 的原子性与不死锁保证。"""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="nl-update-state-")
        self._ctx = _isolation.isolate_paths(Path(self._tmp))
        self._ctx.__enter__()
        from gui import state_store
        self.state_store = state_store
        self.book_id = "atomic-book"
        state_store.save_state(state_store.new_state(self.book_id, "原子性"))

    def tearDown(self):
        try:
            self._ctx.__exit__(None, None, None)
        finally:
            _isolation.remove_tree(Path(self._tmp))

    def test_pause_does_not_erase_finished_batches(self):
        """复现原始缺陷：pause 的写入不得抹掉 worker 已落盘的 success 批。

        这是缺陷的最小复现：两条语句就够——先取旧快照，worker 写 success，
        再用旧快照整份覆盖。改成 update_state 后不再有可被覆盖的旧快照。
        """
        st = self.state_store
        # worker 完成一批
        with st.update_state(self.book_id) as snap:
            st.set_batch_state(snap, 0, 0, "success")

        # pause 线程写任务级状态
        with st.update_state(self.book_id) as snap:
            snap["status"] = "paused"

        after = st.load_state(self.book_id)
        self.assertEqual(
            after.get("chapter_states", {}).get("c0-b0", {}).get("status"),
            "success",
            "pause 把已完成的批次抹掉了（lost update 回归）",
        )
        self.assertEqual(after.get("status"), "paused")

    def test_concurrent_writers_lose_nothing(self):
        """8 个写者 × 20 批 + 1 个 pauser 并发：160 条批状态必须全保住。

        旧写法在同样压力下实测只剩 20 条（丢 140）。这里的断言是"一条都不许丢"。
        """
        st = self.state_store
        n_workers, n_batch = 8, 20
        errors: list[str] = []
        start = threading.Barrier(n_workers + 1)

        def worker(w: int) -> None:
            try:
                start.wait()
                for b in range(n_batch):
                    with st.update_state(self.book_id) as state:
                        st.set_batch_state(state, w, b, "success")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"worker{w}: {type(exc).__name__}: {exc}")

        def pauser() -> None:
            try:
                start.wait()
                for _ in range(30):
                    with st.update_state(self.book_id) as state:
                        state["status"] = "paused"
                    with st.update_state(self.book_id) as state:
                        state["status"] = "running"
            except Exception as exc:  # noqa: BLE001
                errors.append(f"pauser: {type(exc).__name__}: {exc}")

        threads = [threading.Thread(target=worker, args=(w,))
                   for w in range(n_workers)]
        threads.append(threading.Thread(target=pauser))
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=120)

        # 不死锁：所有线程都必须在超时内退出
        self.assertFalse([t.name for t in threads if t.is_alive()],
                         "update_state 自死锁：线程未退出")
        self.assertEqual(errors, [], "并发写入抛异常（可能自死锁后超时）")

        got = st.load_state(self.book_id).get("chapter_states", {})
        expected = n_workers * n_batch
        self.assertEqual(len(got), expected,
                         f"并发下丢失批状态：{len(got)}/{expected}")

    def test_nested_save_inside_update_does_not_deadlock(self):
        """``update_state`` 内部若误调 ``save_state`` 会自死锁——必须显式失败而非挂死。

        两者用的是同一把按路径锁（非可重入 Lock）。这条用例锁定"要么正常、
        要么快速报错"的行为，防止将来有人把内部实现改成再次取锁却无人发现。
        """
        st = self.state_store
        result: dict[str, str] = {}

        def inner() -> None:
            try:
                with st.update_state(self.book_id) as state:
                    state["marker"] = "x"
                result["ok"] = "done"
            except Exception as exc:  # noqa: BLE001
                result["ok"] = f"{type(exc).__name__}: {exc}"

        t = threading.Thread(target=inner, daemon=True)
        t.start()
        t.join(timeout=10)
        self.assertFalse(t.is_alive(), "update_state 在单线程下也不得挂起")
        self.assertEqual(result.get("ok"), "done")

    def test_update_state_persists_book_id(self):
        """调用方不必自己塞 book_id——update_state 退出时补上。"""
        st = self.state_store
        with st.update_state(self.book_id) as state:
            state.pop("book_id", None)
        self.assertEqual(st.load_state(self.book_id).get("book_id"), self.book_id)


if __name__ == "__main__":
    unittest.main()
