#!/usr/bin/env python3
"""长文本状态追踪核心（state_tracker.py）全维独立测试套件。

涵盖：
1. 辅助函数（_utf8_bytes, _snapshot_bytes, _is_retired_status, _validate_snapshot_limits）；
2. 权威状态骨架与原子持久化（_empty_state, load_state, save_state）；
3. 逐章事务校验（schema版本/mode枚举/stale修订号防护/容量硬上限/活跃角色上限及缺失快照拦截）；
4. 事务 Delta 与 Context 更新（foreshadow upsert/delete, timeline_events upsert/delete, 
   retired_context_items, retired_characters, recent_chapters 派生与最多3章截尾, 
   next_chapter_commitments, state_revision 单调递增与 last_chapter 推进）；
5. 续写状态卡生成（build_injection_context 4大区块格式化及已回收伏笔过滤）；
6. 修订号校验（validate_revision）；
7. 命令行接口（CLI show / apply / validate / context 及错误退出码）。
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import state_tracker as st  # noqa: E402


class TestStateTrackerHelpers(unittest.TestCase):
    """测试底层辅助与快照容量校验函数。"""

    def test_utf8_bytes_ascii_and_chinese(self):
        self.assertEqual(st._utf8_bytes("abc"), 3)
        self.assertEqual(st._utf8_bytes("中文"), 6)
        self.assertEqual(st._utf8_bytes(""), 0)

    def test_snapshot_bytes_calculation(self):
        snap = {"name": "林风", "identity": "宗门弟子"}
        serialized = json.dumps(snap, ensure_ascii=False)
        self.assertEqual(st._snapshot_bytes(snap), len(serialized.encode("utf-8")))

    def test_is_retired_status(self):
        for status in ("已回收", "已作废", "回收", "作废"):
            self.assertTrue(st._is_retired_status(status), f"Status {status} should be retired")
        for status in ("未触发", "进行中", "待回收", "活跃", ""):
            self.assertFalse(st._is_retired_status(status), f"Status {status} should not be retired")

    def test_validate_snapshot_limits_normal(self):
        snapshots = {
            "主角": {"identity": "高中生", "goal": "高考考上一本"},
        }
        ok, warnings = st._validate_snapshot_limits(snapshots)
        self.assertTrue(ok)
        self.assertEqual(warnings, [])

    def test_validate_snapshot_limits_warn_and_hard_limit(self):
        # 4096 字节超额警告
        snap_warn = {"text": "字" * 1500}  # 1500*3 = 4500 字节 > 4096
        ok, warnings = st._validate_snapshot_limits({"warn_hero": snap_warn})
        self.assertTrue(ok)
        self.assertEqual(len(warnings), 1)
        self.assertIn("超目标上限 4096", warnings[0])

        # 8192 字节硬上限拒绝
        snap_reject = {"text": "字" * 3000}  # 3000*3 = 9000 字节 > 8192
        ok, warnings = st._validate_snapshot_limits({"huge_hero": snap_reject})
        self.assertFalse(ok)
        self.assertEqual(len(warnings), 1)
        self.assertIn("超硬上限 8192", warnings[0])


class TestStateTrackerStorage(unittest.TestCase):
    """测试权威状态的读取、原子保存与默认骨架。"""

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp_dir.name)

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_empty_state_skeleton(self):
        state = st._empty_state("测试小说")
        self.assertEqual(state["schema_version"], st._SCHEMA_VERSION)
        self.assertEqual(state["book_title"], "测试小说")
        self.assertEqual(state["last_chapter"], 0)
        self.assertEqual(state["state_revision"], 0)
        self.assertIn("context", state)
        self.assertEqual(state["context"]["active_character_names"], [])
        self.assertEqual(state["character_snapshots"], {})
        self.assertEqual(state["foreshadow"], [])
        self.assertEqual(state["timeline_events"], [])

    def test_load_state_non_existent(self):
        dummy_file = self.tmp_path / "non_existent.json"
        state = st.load_state(dummy_file)
        self.assertEqual(state["state_revision"], 0)
        self.assertEqual(state["character_snapshots"], {})

    def test_save_state_and_load_state_roundtrip(self):
        state_file = self.tmp_path / "sub" / "_tracking-state.json"
        state_data = st._empty_state("测试书名")
        state_data["state_revision"] = 5
        state_data["character_snapshots"]["叶凡"] = {"identity": "天帝"}

        st.save_state(state_data, state_file)
        self.assertTrue(state_file.exists())

        loaded = st.load_state(state_file)
        self.assertEqual(loaded["state_revision"], 5)
        self.assertEqual(loaded["character_snapshots"]["叶凡"]["identity"], "天帝")


class TestApplyTransactionValidation(unittest.TestCase):
    """测试 apply_transaction 参数与安全防线校验。"""

    def test_schema_version_mismatch(self):
        state = st._empty_state()
        tx = {"schema_version": 999, "mode": "init"}
        with self.assertRaises(ValueError) as ctx:
            st.apply_transaction(state, tx)
        self.assertIn("不支持的 schema_version: 999", str(ctx.exception))

    def test_illegal_mode(self):
        state = st._empty_state()
        tx = {"mode": "destroy"}
        with self.assertRaises(ValueError) as ctx:
            st.apply_transaction(state, tx)
        self.assertIn("非法 mode: destroy", str(ctx.exception))

    def test_stale_revision_detection(self):
        state = st._empty_state()
        state["state_revision"] = 3

        # mode=init 当 revision != 0
        tx_init = {"mode": "init"}
        with self.assertRaises(ValueError) as ctx:
            st.apply_transaction(state, tx_init)
        self.assertIn("stale 事务", str(ctx.exception))

        # mode=append 缺少 expected_state_revision
        tx_append_no_exp = {"mode": "append"}
        with self.assertRaises(ValueError) as ctx:
            st.apply_transaction(state, tx_append_no_exp)
        self.assertIn("缺少 expected_state_revision", str(ctx.exception))

        # mode=append expected_state_revision 不为整数
        tx_append_str_exp = {"mode": "append", "expected_state_revision": "3"}
        with self.assertRaises(ValueError) as ctx:
            st.apply_transaction(state, tx_append_str_exp)
        self.assertIn("必须为整数", str(ctx.exception))

        # mode=append expected_state_revision 与当前 revision 不一致
        tx_append_stale = {"mode": "append", "expected_state_revision": 2}
        with self.assertRaises(ValueError) as ctx:
            st.apply_transaction(state, tx_append_stale)
        self.assertIn("expected_state_revision=2 但当前 state_revision=3", str(ctx.exception))

    def test_snapshot_hard_limit_rejection(self):
        state = st._empty_state()
        huge_snap = {"info": "超" * 3000}
        tx = {
            "mode": "init",
            "character_snapshots": {"膨胀角色": huge_snap},
        }
        with self.assertRaises(ValueError) as ctx:
            st.apply_transaction(state, tx)
        self.assertIn("超硬上限 8192", str(ctx.exception))

    def test_active_characters_validation(self):
        state = st._empty_state()
        # active_character_names 不是列表
        tx_bad_list = {
            "mode": "init",
            "context": {"active_character_names": "林风,唐雨"},
        }
        with self.assertRaises(ValueError) as ctx:
            st.apply_transaction(state, tx_bad_list)
        self.assertIn("必须为列表", str(ctx.exception))

        # 超过 6 人上限
        tx_too_many = {
            "mode": "init",
            "context": {"active_character_names": ["A", "B", "C", "D", "E", "F", "G"]},
        }
        with self.assertRaises(ValueError) as ctx:
            st.apply_transaction(state, tx_too_many)
        self.assertIn("活跃角色 7 人超上限 6", str(ctx.exception))

        # append 模式下活跃角色缺快照
        state_with_rev = st._empty_state()
        state_with_rev["state_revision"] = 1
        tx_append_missing_snap = {
            "mode": "append",
            "expected_state_revision": 1,
            "context": {"active_character_names": ["张三"]},
            "character_snapshots": {},
        }
        with self.assertRaises(ValueError) as ctx:
            st.apply_transaction(state_with_rev, tx_append_missing_snap)
        self.assertIn("活跃角色缺快照: ['张三']", str(ctx.exception))


class TestApplyTransactionLifecycle(unittest.TestCase):
    """测试 apply_transaction 在 init 与 append 流程下的状态推进与数据合并。"""

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp_dir.name)

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_init_transaction_full(self):
        state = st._empty_state("凡人修仙")
        tx = {
            "mode": "init",
            "chapter": 1,
            "chapter_title": "山村少年",
            "context": {
                "position": {"volume": 1, "stage": "开端"},
                "long_term_constraints": ["凡人流不可出现系统"],
                "active_character_names": ["韩立"],
                "continuity_risks": ["掌天瓶秘密不可暴露"],
                "recent_chapters": [{"chapter": 1, "summary": "韩立上七玄门"}],
                "next_chapter_commitments": ["通过考核进入七玄门"],
            },
            "character_snapshots": {
                "韩立": {"identity": "山村少年", "goal": "进入七玄门", "state": "朴实坚韧"}
            },
            "foreshadow": [
                {"id": "FS-01", "summary": "神秘小绿瓶", "status": "未触发"}
            ],
            "timeline_events": [
                {"id": "EV-01", "event": "离家前往七玄门"}
            ],
        }

        res = st.apply_transaction(state, tx)
        self.assertEqual(res["state_revision"], 1)
        self.assertEqual(res["last_chapter"], 1)
        self.assertIn("韩立", res["character_snapshots"])
        self.assertEqual(len(res["foreshadow"]), 1)
        self.assertEqual(res["foreshadow"][0]["id"], "FS-01")
        self.assertEqual(len(res["timeline_events"]), 1)
        self.assertEqual(res["context"]["next_chapter_commitments"], ["通过考核进入七玄门"])

    def test_append_transaction_deltas(self):
        # 构造初始状态
        state = st._empty_state("凡人修仙")
        state["state_revision"] = 1
        state["last_chapter"] = 1
        state["character_snapshots"] = {
            "韩立": {"identity": "七玄门记名弟子", "state": "中毒受制"},
            "墨大夫": {"identity": "神手谷医师", "state": "暗中图谋"},
            "厉飞雨": {"identity": "七玄门弟子", "state": "服用抽髓丹"},
        }
        state["context"] = {
            "active_character_names": ["韩立", "墨大夫"],
            "long_term_constraints": ["守秘", "不得相信墨大夫"],
            "continuity_risks": ["毒发风险"],
            "recent_chapters": [{"chapter": 1, "summary": "入门"}],
            "next_chapter_commitments": ["旧承诺"],
        }
        state["foreshadow"] = [
            {"id": "FS-01", "summary": "神秘小绿瓶", "status": "未触发"},
            {"id": "FS-02", "summary": "旧伏笔", "status": "进行中"},
        ]
        state["timeline_events"] = [
            {"id": "EV-01", "event": "拜师"},
            {"id": "EV-02", "event": "发现药草异常"},
        ]

        # 构造 append 事务
        tx_append = {
            "mode": "append",
            "chapter": 2,
            "chapter_title": "神手谷风波",
            "expected_state_revision": 1,
            "delta": {
                "result": "韩立突破象甲功第三层并识破药酒",
                "foreshadow_changes": [
                    {"id": "FS-01", "summary": "神秘小绿瓶催熟灵药", "status": "进行中"},  # update
                    {"id": "FS-02", "action": "delete"},  # delete
                    {"id": "FS-03", "summary": "眨眼剑法秘籍", "status": "未触发"},  # insert
                ],
                "timeline_events": [
                    {"id": "EV-02", "action": "delete"},  # delete
                    {"id": "EV-03", "event": "与厉飞雨结盟"},  # insert
                ],
                "retired_context_items": ["不得相信墨大夫"],
                "retired_characters": ["墨大夫"],
                "next_chapter_commitments": ["寻找解药配方"],
            },
            "character_snapshots": {
                "韩立": {"identity": "七玄门正式弟子", "state": "功力大增"},
            },
        }

        save_path = self.tmp_path / "_tracking-state.json"
        new_state = st.apply_transaction(state, tx_append, state_path=save_path)

        # 检查持久化与状态更新
        self.assertTrue(save_path.exists())
        self.assertEqual(new_state["state_revision"], 2)
        self.assertEqual(new_state["last_chapter"], 2)

        # 角色快照更新与退役
        self.assertEqual(new_state["character_snapshots"]["韩立"]["state"], "功力大增")
        self.assertNotIn("墨大夫", new_state["character_snapshots"])
        self.assertNotIn("墨大夫", new_state["context"]["active_character_names"])
        self.assertIn("厉飞雨", new_state["character_snapshots"])

        # 伏笔变更：FS-01 更新, FS-02 删除, FS-03 新增
        fs_ids = [f["id"] for f in new_state["foreshadow"]]
        self.assertIn("FS-01", fs_ids)
        self.assertNotIn("FS-02", fs_ids)
        self.assertIn("FS-03", fs_ids)
        fs_01 = next(f for f in new_state["foreshadow"] if f["id"] == "FS-01")
        self.assertEqual(fs_01["status"], "进行中")

        # 时间线事件：EV-02 删除, EV-03 新增
        ev_ids = [e["id"] for e in new_state["timeline_events"]]
        self.assertIn("EV-01", ev_ids)
        self.assertNotIn("EV-02", ev_ids)
        self.assertIn("EV-03", ev_ids)

        # 上下文条目退役与承诺
        self.assertNotIn("不得相信墨大夫", new_state["context"]["long_term_constraints"])
        self.assertIn("守秘", new_state["context"]["long_term_constraints"])
        self.assertEqual(new_state["context"]["next_chapter_commitments"], ["寻找解药配方"])

        # 近章速记派生：包含第 1 章与第 2 章
        recent_chs = [c["chapter"] for c in new_state["context"]["recent_chapters"]]
        self.assertEqual(recent_chs, [1, 2])


class TestDeriveRecentChapters(unittest.TestCase):
    """测试近章速记派生逻辑（同章覆盖、最多3章截尾）。"""

    def test_derive_dedup_and_max_three(self):
        old_state = {
            "context": {
                "recent_chapters": [
                    {"chapter": 1, "summary": "Ch1"},
                    {"chapter": 2, "summary": "Ch2"},
                    {"chapter": 3, "summary": "Ch3"},
                ]
            }
        }
        # 第 4 章加入，第 1 章应被顶出
        tx4 = {"chapter": 4, "delta": {"result": "Ch4"}}
        recent4 = st._derive_recent_chapters(old_state, tx4, {})
        self.assertEqual(len(recent4), 3)
        self.assertEqual([e["chapter"] for e in recent4], [2, 3, 4])

        # 同章（如第 4 章重写）覆盖
        state_with_4 = {"context": {"recent_chapters": recent4}}
        tx4_rewrite = {"chapter": 4, "delta": {"result": "Ch4-New"}}
        recent4_new = st._derive_recent_chapters(state_with_4, tx4_rewrite, {})
        self.assertEqual(len(recent4_new), 3)
        self.assertEqual(recent4_new[-1]["summary"], "Ch4-New")


class TestBuildInjectionContext(unittest.TestCase):
    """测试 build_injection_context 提示词注入片段渲染。"""

    def test_empty_state_returns_empty_string(self):
        self.assertEqual(st.build_injection_context({}), "")
        self.assertEqual(st.build_injection_context({"context": {}}), "")

    def test_full_context_rendering(self):
        state = {
            "context": {
                "active_character_names": ["陆沉", "宁姚"],
                "recent_chapters": [
                    {"chapter": 1, "summary": "泥瓶巷少年"},
                    {"chapter": 2, "summary": "买药救人"},
                    {"chapter": 3, "summary": "初见剑仙"},
                ],
                "next_chapter_commitments": ["前往龙窑打铁"],
            },
            "character_snapshots": {
                "陆沉": {
                    "identity": "小镇掌柜",
                    "location": "泥瓶巷",
                    "goal": "游戏人间",
                    "state": "从容不迫",
                    "abilities_resources": ["缩地成寸", "三教合一"],
                    "relationships": ["陈平安领路人"],
                    "knowledge": "知晓小镇天机",
                    "open_threads": ["与齐静春对赌"],
                },
                "宁姚": {
                    "identity": "剑气长城剑修",
                    "location": "客栈",
                    "goal": "淬炼剑意",
                    "state": "负伤休养",
                },
            },
            "foreshadow": [
                {"id": "FS-101", "summary": "齐静春本命字", "status": "未触发"},
                {"id": "FS-102", "summary": "老剑条线索", "status": "进行中"},
                {"id": "FS-103", "summary": "已解决的小纠纷", "status": "已回收"},  # 应被过滤
                {"id": "FS-104", "summary": "作废的支线", "status": "作废"},  # 应被过滤
            ],
        }

        output = st.build_injection_context(state)
        self.assertIn("## 长期状态追踪", output)

        # 角色快照
        self.assertIn("### 角色快照", output)
        self.assertIn("- **陆沉**", output)
        self.assertIn("  - 身份：小镇掌柜", output)
        self.assertIn("  - 能力与资源：缩地成寸；三教合一", output)
        self.assertIn("- **宁姚**", output)
        self.assertIn("  - 身份：剑气长城剑修", output)

        # 活跃伏笔（排除已回收与作废）
        self.assertIn("### 活跃伏笔", output)
        self.assertIn("- [FS-101] 齐静春本命字", output)
        self.assertIn("- [FS-102] 老剑条线索", output)
        self.assertNotIn("FS-103", output)
        self.assertNotIn("FS-104", output)

        # 近三章速记
        self.assertIn("### 近三章速记", output)
        self.assertIn("- 第1章：泥瓶巷少年", output)
        self.assertIn("- 第2章：买药救人", output)
        self.assertIn("- 第3章：初见剑仙", output)

        # 下一章承诺
        self.assertIn("### 下一章承诺", output)
        self.assertIn("- 前往龙窑打铁", output)


class TestValidateRevision(unittest.TestCase):
    """测试 validate_revision 修订号预检。"""

    def test_validate_revision_match(self):
        state = {"state_revision": 7}
        ok, reason = st.validate_revision(state, 7)
        self.assertTrue(ok)
        self.assertIn("修订号一致", reason)

    def test_validate_revision_mismatch(self):
        state = {"state_revision": 8}
        ok, reason = st.validate_revision(state, 5)
        self.assertFalse(ok)
        self.assertIn("stale：expected_state_revision=5 但当前 state_revision=8", reason)


class TestStateTrackerCLI(unittest.TestCase):
    """测试 state_tracker main 命令行调用与各子命令。"""

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp_dir.name)

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_cli_no_args_shows_help(self):
        f = io.StringIO()
        with patch("sys.stdout", f):
            code = st.main([])
        self.assertEqual(code, 0)
        self.assertIn("usage:", f.getvalue().lower())

    def test_cli_show_command(self):
        state_file = self.tmp_path / "_tracking-state.json"
        state = st._empty_state("剑来")
        state["state_revision"] = 2
        st.save_state(state, state_file)

        f = io.StringIO()
        with patch("sys.stdout", f):
            code = st.main(["show", "--state", str(state_file)])
        self.assertEqual(code, 0)
        data = json.loads(f.getvalue())
        self.assertEqual(data["book_title"], "剑来")
        self.assertEqual(data["state_revision"], 2)

    def test_cli_apply_success_and_failure(self):
        state_file = self.tmp_path / "_tracking-state.json"
        st.save_state(st._empty_state("雪中"), state_file)

        tx_file = self.tmp_path / "tx.json"
        tx_data = {
            "mode": "init",
            "chapter": 1,
            "context": {"active_character_names": []},
        }
        tx_file.write_text(json.dumps(tx_data, ensure_ascii=False), encoding="utf-8")

        f = io.StringIO()
        with patch("sys.stdout", f):
            code = st.main(["apply", "--state", str(state_file), "--transaction", str(tx_file)])
        self.assertEqual(code, 0)
        self.assertIn("已提交，state_revision=1", f.getvalue())

        # 再次执行相同 init，由于 state_revision 已经为 1，应报错退出码 2
        f_err = io.StringIO()
        with patch("sys.stdout", f_err):
            err_code = st.main(["apply", "--state", str(state_file), "--transaction", str(tx_file)])
        self.assertEqual(err_code, 2)
        self.assertIn("stale 事务", f_err.getvalue())

    def test_cli_validate_command(self):
        state_file = self.tmp_path / "_tracking-state.json"
        state = st._empty_state()
        state["state_revision"] = 4
        st.save_state(state, state_file)

        # 匹配返回 0
        f_ok = io.StringIO()
        with patch("sys.stdout", f_ok):
            code_ok = st.main(["validate", "--state", str(state_file), "--expected-revision", "4"])
        self.assertEqual(code_ok, 0)
        self.assertIn("修订号一致", f_ok.getvalue())

        # 不匹配返回 1
        f_fail = io.StringIO()
        with patch("sys.stdout", f_fail):
            code_fail = st.main(["validate", "--state", str(state_file), "--expected-revision", "3"])
        self.assertEqual(code_fail, 1)
        self.assertIn("stale", f_fail.getvalue())

    def test_cli_context_command(self):
        state_file = self.tmp_path / "_tracking-state.json"
        state = st._empty_state("大道朝天")
        state["context"]["next_chapter_commitments"] = ["柳十岁前往青山"]
        st.save_state(state, state_file)

        f = io.StringIO()
        with patch("sys.stdout", f):
            code = st.main(["context", "--state", str(state_file)])
        self.assertEqual(code, 0)
        self.assertIn("## 长期状态追踪", f.getvalue())
        self.assertIn("柳十岁前往青山", f.getvalue())


if __name__ == "__main__":
    unittest.main()
