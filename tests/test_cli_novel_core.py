"""CLI 统一入口 novel.py 核心调度与语料解析单元测试（纯标准库）。

覆盖：
1. resolve_book_src 四层解析策略：
   - 精确文件路径直接返回（绝对与相对）；
   - 书名直匹配 corpus/<name>.txt；
   - 书名直匹配 corpus/<name>_chosen.txt；
   - 模糊子串唯一命中；
   - 模糊多命中歧义抛出 SystemExit 并列出备选；
   - 未命中抛出 SystemExit 并列出语料库可用书籍清单；
   - 空语料库提示 (空)；
   - corpus 目录不存在时的安全退出。
2. run_script 脚本执行器：
   - 脚本不存在时返回 1 并输出警告；
   - 子进程参数透传与 PYTHONIOENCODING GBK 容错环境变量注入。
3. cmd_reset_admin_password 管理员密码本地紧急重置：
   - 成功生成并打印新密码返回 0；
   - 异常捕获并降级打印返回 1。
4. cmd_status 状态概览高级分支：
   - synthetic_* 虚拟资产自动过滤；
   - 非法或损坏置信度安全回退 "?"；
   - 缺失 models.json 提示 WorkBuddy 内置智能兜底；
   - 创作项目与报告聚合展示。
5. main 顶级子命令解析与分发：
   - 无参数打印帮助并返回 0；
   - 状态、重置管理员密码、模型（列表与测试）、校验、合规、笔法报告、同步检查、回填元数据子命令。
"""
from __future__ import annotations

import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import novel  # noqa: E402


class TestResolveBookSrc(unittest.TestCase):
    """测试 resolve_book_src 的 4 层解析策略。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cli_resolve_"))
        self._orig_root = novel.ROOT
        novel.ROOT = self.tmp

    def tearDown(self):
        novel.ROOT = self._orig_root
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_resolve_exact_existing_file(self):
        """1) 存在的物理路径直接返回。"""
        exact = self.tmp / "my_exact_file.txt"
        exact.write_text("content", encoding="utf-8")
        res = novel.resolve_book_src(str(exact))
        self.assertEqual(res, exact)

    def test_resolve_corpus_direct_name(self):
        """2a) 书名在 corpus/ 下对应 <name>.txt。"""
        corpus = self.tmp / "corpus"
        corpus.mkdir()
        book = corpus / "斗破苍穹.txt"
        book.write_text("text", encoding="utf-8")
        res = novel.resolve_book_src("斗破苍穹")
        self.assertEqual(res, book)

    def test_resolve_corpus_chosen_name(self):
        """2b) 书名在 corpus/ 下对应 <name>_chosen.txt。"""
        corpus = self.tmp / "corpus"
        corpus.mkdir()
        book = corpus / "完美世界_chosen.txt"
        book.write_text("text", encoding="utf-8")
        res = novel.resolve_book_src("完美世界")
        self.assertEqual(res, book)

    def test_resolve_corpus_single_fuzzy_match(self):
        """3) 书名模糊唯一命中。"""
        corpus = self.tmp / "corpus"
        corpus.mkdir()
        book = corpus / "凡人修仙传仙界篇.txt"
        book.write_text("text", encoding="utf-8")
        res = novel.resolve_book_src("凡人修仙")
        self.assertEqual(res, book)

    def test_resolve_corpus_ambiguous_fuzzy_match_exits(self):
        """4a) 模糊多命中时抛出 SystemExit 并列出可用书目。"""
        corpus = self.tmp / "corpus"
        corpus.mkdir()
        (corpus / "遮天前传.txt").write_text("a", encoding="utf-8")
        (corpus / "遮天后传.txt").write_text("b", encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            novel.resolve_book_src("遮天")
        err_msg = str(cm.exception)
        self.assertIn("找不到语料: 遮天", err_msg)
        self.assertIn("遮天前传", err_msg)
        self.assertIn("遮天后传", err_msg)

    def test_resolve_corpus_missing_book_lists_available(self):
        """4b) 书籍不存在时列出 corpus 下所有可用书目。"""
        corpus = self.tmp / "corpus"
        corpus.mkdir()
        (corpus / "诡秘之主.txt").write_text("a", encoding="utf-8")
        (corpus / "宿命之环.txt").write_text("b", encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            novel.resolve_book_src("不存在的书")
        err_msg = str(cm.exception)
        self.assertIn("找不到语料: 不存在的书", err_msg)
        self.assertIn("当前可用: 宿命之环, 诡秘之主", err_msg)

    def test_resolve_corpus_empty_lists_empty_label(self):
        """4c) corpus 目录存在但为空时，提示 '(空)'。"""
        corpus = self.tmp / "corpus"
        corpus.mkdir()
        with self.assertRaises(SystemExit) as cm:
            novel.resolve_book_src("空库搜书")
        err_msg = str(cm.exception)
        self.assertIn("当前可用: (空)", err_msg)

    def test_resolve_missing_corpus_dir_exits(self):
        """4d) corpus 目录根本不存在时，安全退出报文件不存在。"""
        missing_target = self.tmp / "phantom_book"
        with self.assertRaises(SystemExit) as cm:
            novel.resolve_book_src(str(missing_target))
        self.assertIn(f"文件不存在: {missing_target}", str(cm.exception))


class TestRunScript(unittest.TestCase):
    """测试 run_script 脚本执行器与环境透传。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cli_script_"))
        self._orig_scripts = novel.SCRIPTS
        novel.SCRIPTS = self.tmp

    def tearDown(self):
        novel.SCRIPTS = self._orig_scripts
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_run_script_missing_file_returns_1(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = novel.run_script("missing_tool.py", ["--test"])
        self.assertEqual(rc, 1)
        self.assertIn("✗ 脚本不存在", buf.getvalue())

    def test_run_script_invokes_subprocess_with_env(self):
        dummy = self.tmp / "dummy.py"
        dummy.write_text("print('ok')", encoding="utf-8")
        with mock.patch("subprocess.call", return_value=0) as mock_call:
            rc = novel.run_script("dummy.py", ["--foo", "bar"])
            self.assertEqual(rc, 0)
            mock_call.assert_called_once()
            cmd = mock_call.call_args[0][0]
            kwargs = mock_call.call_args[1]
            self.assertEqual(cmd[0], sys.executable)
            self.assertEqual(cmd[1], str(dummy))
            self.assertEqual(cmd[2:], ["--foo", "bar"])
            self.assertEqual(kwargs["env"]["PYTHONIOENCODING"], "utf-8:backslashreplace")


class TestCmdResetAdminPassword(unittest.TestCase):
    """测试本地紧急重置管理员密码。"""

    def test_reset_password_success(self):
        with mock.patch("gui.admin.reset_password", return_value="SecretPass2026"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = novel.cmd_reset_admin_password()
            self.assertEqual(rc, 0)
            out = buf.getvalue()
            self.assertIn("✓ 管理员密码已重置", out)
            self.assertIn("SecretPass2026", out)

    def test_reset_password_failure(self):
        with mock.patch("gui.admin.reset_password", side_effect=RuntimeError("SQLite I/O failure")):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = novel.cmd_reset_admin_password()
            self.assertEqual(rc, 1)
            out = buf.getvalue()
            self.assertIn("✗ 重置失败: SQLite I/O failure", out)


class TestCmdStatusAdvanced(unittest.TestCase):
    """测试项目状态概览在各类异常与扩展边界下的健壮性。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cli_status_"))
        self._orig_root = novel.ROOT
        novel.ROOT = self.tmp
        for d in ("assets", "reports", "novel", "config"):
            (self.tmp / d).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        novel.ROOT = self._orig_root
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = novel.cmd_status()
        return rc, buf.getvalue()

    def test_status_synthetic_assets_excluded(self):
        """synthetic_* 资产应被排除，不计入官方已拆资产。"""
        (self.tmp / "assets" / "synthetic_voice-voice-card.json").write_text(
            '{"meta":{"confidence":0.8,"genre":"test"}}', encoding="utf-8"
        )
        (self.tmp / "assets" / "real_book-voice-card.json").write_text(
            '{"meta":{"confidence":0.95,"genre":"xianxia"}}', encoding="utf-8"
        )
        rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("1 本已拆", out)
        self.assertIn("real_book", out)
        self.assertNotIn("synthetic_voice", out)

    def test_status_confidence_fallback_question_mark(self):
        """非数字型置信度应降级为 ? 而非异常中断。"""
        (self.tmp / "assets" / "odd-voice-card.json").write_text(
            '{"meta":{"confidence":"not_a_number","genre":"fantasy"}}', encoding="utf-8"
        )
        rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("置信 ?", out)

    def test_status_missing_models_json_prints_workbuddy_fallback(self):
        """无 config/models.json 时输出内置智能提示。"""
        rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("未配置外部模型 —— LLM 层由 WorkBuddy 内置智能承担", out)

    def test_status_novel_projects_and_reports_listed(self):
        """展示创作项目进度与已发布报告清单。"""
        proj_dir = self.tmp / "novel" / "my_novel"
        proj_dir.mkdir()
        (proj_dir / "state.json").write_text(
            '{"name":"剑来","current_chapter":12,"current_arc":2,"word_count_today":3600}',
            encoding="utf-8",
        )
        (self.tmp / "reports" / "剑来-拆书报告.md").write_text("# 报告", encoding="utf-8")
        rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("第12章/第2卷, 今日3600字", out)
        self.assertIn("[拆书报告] 1 份", out)
        self.assertIn("剑来-拆书报告.md", out)


class TestMainDispatch(unittest.TestCase):
    """测试 main() 命令行参数解析与子命令分发。"""

    def test_main_no_args_prints_help_and_returns_0(self):
        with mock.patch.object(sys, "argv", ["novel"]), mock.patch(
            "argparse.ArgumentParser.print_help"
        ) as mock_help:
            rc = novel.main()
            self.assertEqual(rc, 0)
            mock_help.assert_called_once()

    def test_main_status_invokes_cmd_status(self):
        with mock.patch.object(sys, "argv", ["novel", "状态"]), mock.patch.object(
            novel, "cmd_status", return_value=0
        ) as mock_cmd:
            rc = novel.main()
            self.assertEqual(rc, 0)
            mock_cmd.assert_called_once()

    def test_main_reset_password_invokes_cmd_reset(self):
        with mock.patch.object(sys, "argv", ["novel", "重置管理员密码"]), mock.patch.object(
            novel, "cmd_reset_admin_password", return_value=0
        ) as mock_cmd:
            rc = novel.main()
            self.assertEqual(rc, 0)
            mock_cmd.assert_called_once()

    def test_main_model_list_dispatches_model_config(self):
        with mock.patch.object(sys, "argv", ["novel", "模型"]), mock.patch.object(
            novel, "run_script", return_value=0
        ) as mock_run:
            rc = novel.main()
            self.assertEqual(rc, 0)
            mock_run.assert_called_once_with("model_config.py", ["list"])

    def test_main_model_test_dispatches_llm_client(self):
        with mock.patch.object(sys, "argv", ["novel", "模型", "--test", "claude-3"]), mock.patch.object(
            novel, "run_script", return_value=0
        ) as mock_run:
            rc = novel.main()
            self.assertEqual(rc, 0)
            mock_run.assert_called_once_with("llm_client.py", ["claude-3"])

    def test_main_validate_dispatches_validate_py(self):
        with mock.patch.object(
            sys, "argv", ["novel", "校验", "sample.json", "--kind", "voice-card"]
        ), mock.patch.object(novel, "run_script", return_value=0) as mock_run:
            rc = novel.main()
            self.assertEqual(rc, 0)
            mock_run.assert_called_once_with("validate.py", ["sample.json", "--kind", "voice-card"])

    def test_main_compliance_dispatches_compliance_py(self):
        with mock.patch.object(
            sys, "argv", ["novel", "合规", "card.json", "book.txt"]
        ), mock.patch.object(novel, "run_script", return_value=0) as mock_run:
            rc = novel.main()
            self.assertEqual(rc, 0)
            mock_run.assert_called_once_with("compliance.py", ["card.json", "book.txt"])

    def test_main_craft_report_dispatches_report_craft(self):
        with mock.patch.object(
            sys, "argv", ["novel", "笔法报告", "craft.json", "--out", "out.md"]
        ), mock.patch.object(novel, "run_script", return_value=0) as mock_run:
            rc = novel.main()
            self.assertEqual(rc, 0)
            mock_run.assert_called_once_with("report_craft.py", ["craft.json", "--out", "out.md"])

    def test_main_sync_check_dispatches_asset_sync_check(self):
        with mock.patch.object(
            sys, "argv", ["novel", "同步检查", "暮冬念春"]
        ), mock.patch.object(novel, "run_script", return_value=0) as mock_run:
            rc = novel.main()
            self.assertEqual(rc, 0)
            mock_run.assert_called_once_with("asset_sync_check.py", ["暮冬念春"])

    def test_main_backfill_dispatches_backfill_meta(self):
        with mock.patch.object(
            sys, "argv", ["novel", "回填元数据", "--dry-run"]
        ), mock.patch.object(novel, "run_script", return_value=0) as mock_run:
            rc = novel.main()
            self.assertEqual(rc, 0)
            mock_run.assert_called_once_with("backfill_meta.py", ["--dry-run"])


if __name__ == "__main__":
    sys.exit(unittest.main())
