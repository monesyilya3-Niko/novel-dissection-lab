"""章节生成与改写流水线（write.py）全维独立测试套件。

覆盖维度：
1. 一致性打分与质量门禁（run_consistency：PASS / 建议改写 / 异常优雅降级）
2. 实体冲突检测（run_conflict_check：实体表缺失 / 实体表为空 / 别名混用拦截 / 称呼正常）
3. 无模型本地接管模式（main：未配置外部模型时自动输出《AI接管写作任务.md》并安全返回 0）
4. LLM 异常与优雅中断（main：LLMError 捕获 / 降级描述打印 / 返回非零状态码 1）
5. 生成-自检-改写三轮循环（main：未达标提取扣分点与角色声线核心词 / 触发改写 / 达标早停 break / 章节入库落盘）
6. 大纲注入与题材包质量线解析（main：已有大纲 outline.md 提示词合并 / CLI 与题材包 quality_target 达标线解析）
"""
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import llm_client
import write


class TestConsistencyAndConflictGates(unittest.TestCase):
    """测试 consistency 打分门禁与 entities 冲突排查。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_write_gates_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_run_consistency_pass_and_warn(self):
        vc_file = Path(self.temp_dir) / "voice.json"
        vc_file.write_text('{"name": "vc"}', encoding="utf-8")
        ch_file = Path(self.temp_dir) / "ch.txt"
        ch_file.write_text("正文内容", encoding="utf-8")

        # 1. 分数 >= 75 -> PASS
        mock_consistency = mock.MagicMock()
        mock_consistency.score_text.return_value = (82.5, ["细节通过"], {})
        with mock.patch.dict("sys.modules", {"consistency": mock_consistency}), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            write.run_consistency(vc_file, ch_file)
            out = mock_out.getvalue()
            self.assertIn("一致性打分: 82.5/100", out)
            self.assertIn("PASS", out)

        # 2. 分数 < 75 -> 建议改写
        mock_consistency.score_text.return_value = (68.0, ["未达标"], {})
        with mock.patch.dict("sys.modules", {"consistency": mock_consistency}), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            write.run_consistency(vc_file, ch_file)
            out = mock_out.getvalue()
            self.assertIn("一致性打分: 68.0/100", out)
            self.assertIn("建议改写", out)

        # 3. 异常处理
        mock_consistency.score_text.side_effect = RuntimeError("打分引擎故障")
        with mock.patch.dict("sys.modules", {"consistency": mock_consistency}), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            write.run_consistency(vc_file, ch_file)
            out = mock_out.getvalue()
            self.assertIn("[跳过] 一致性打分异常", out)

    def test_run_conflict_check_scenarios(self):
        novel_dir = Path(self.temp_dir) / "my_novel"
        settings_dir = novel_dir / "settings"
        settings_dir.mkdir(parents=True)
        entities_file = settings_dir / "entities.json"

        # 1. 实体表不存在
        with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            write.run_conflict_check(Path(self.temp_dir) / "empty_novel", "正文")
            self.assertIn("实体表不存在", mock_out.getvalue())

        # 2. 实体表为空
        entities_file.write_text('{"characters": []}', encoding="utf-8")
        with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            write.run_conflict_check(novel_dir, "正文")
            self.assertIn("实体表为空", mock_out.getvalue())

        # 3. 别名孤立出现但主名未出现 -> 报警
        entities_data = {
            "characters": [
                {"name": "唐雨", "aliases": ["小雨", "唐小雨"]}
            ]
        }
        entities_file.write_text(json.dumps(entities_data, ensure_ascii=False), encoding="utf-8")
        text_mixed = "窗外雨水不停，小雨转过身来微笑着。"
        with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            write.run_conflict_check(novel_dir, text_mixed)
            self.assertIn("别名混用提示", mock_out.getvalue())
            self.assertIn("唐雨(仅以别称出现: 小雨)", mock_out.getvalue())

        # 4. 主名和别名正常使用 -> 通过
        text_clean = "唐雨站在门前，大家都亲切地喊她小雨。"
        with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            write.run_conflict_check(novel_dir, text_clean)
            self.assertIn("实体称呼无异常", mock_out.getvalue())


class TestWriteMainNoModelTakeover(unittest.TestCase):
    """测试无外部模型时的任务生成与退出流程。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_write_nomodel_")
        self.prompt_file = Path(self.temp_dir) / "prompt.md"
        self.prompt_file.write_text("# 写作Prompt", encoding="utf-8")
        self.novel_dir = Path(self.temp_dir) / "novel"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_no_model_generates_takeover_guide(self):
        args = [
            "write.py",
            "--prompt", str(self.prompt_file),
            "--chapter", "1",
            "--task", "期末复习剧情",
            "--novel-dir", str(self.novel_dir),
            "--novel-name", "青春纪念册",
            "--words", "2000",
        ]

        with mock.patch.object(write.llm_client, "any_model_configured", return_value=False), \
             mock.patch("sys.argv", args), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:

            exit_code = write.main()
            self.assertEqual(exit_code, 0)
            self.assertIn("未配置外部模型 —— 已生成 AI 接管写作任务清单", mock_out.getvalue())

            # 验证 AI 接管写作任务.md 真实落盘
            guide_file = self.novel_dir / "AI接管写作任务.md"
            self.assertTrue(guide_file.exists())
            guide_content = guide_file.read_text(encoding="utf-8")
            self.assertIn("青春纪念册", guide_content)
            self.assertIn("第 1 章", guide_content)
            self.assertIn("期末复习剧情", guide_content)
            self.assertIn("chapter-001.txt", guide_content)


class TestWriteMainLLMExecutionAndRewrite(unittest.TestCase):
    """测试主流程 LLM 异常、自检达标、多轮改写循环与全书 QA。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_write_llm_")
        self.prompt_file = Path(self.temp_dir) / "prompt.md"
        self.prompt_file.write_text("# 写作SystemPrompt", encoding="utf-8")
        self.voice_file = Path(self.temp_dir) / "voice.json"
        self.voice_file.write_text(json.dumps({
            "dialogue": {
                "character_voices": [
                    {"name": "主角A", "speech_signature": {"verbal_tics": ["休想"]}}
                ]
            }
        }, ensure_ascii=False), encoding="utf-8")
        self.novel_dir = Path(self.temp_dir) / "novel"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_missing_prompt_path_exits(self):
        args = [
            "write.py",
            "--prompt", str(Path(self.temp_dir) / "non_existent.md"),
            "--chapter", "1",
            "--task", "任务要点",
        ]
        with mock.patch("sys.argv", args), \
             self.assertRaises(SystemExit) as cm:
            write.main()
        self.assertIn("写作 prompt 不存在", str(cm.exception))

    def test_llm_error_graceful_exit(self):
        args = [
            "write.py",
            "--prompt", str(self.prompt_file),
            "--chapter", "1",
            "--task", "任务要点",
            "--novel-dir", str(self.novel_dir),
        ]

        with mock.patch.object(write.llm_client, "any_model_configured", return_value=True), \
             mock.patch.object(write.llm_client, "chat", side_effect=llm_client.LLMError("API 超过配额限制")), \
             mock.patch("sys.argv", args), \
             mock.patch("sys.stderr", new_callable=io.StringIO) as mock_err:

            exit_code = write.main()
            self.assertEqual(exit_code, 1)
            self.assertIn("写作生成中断", mock_err.getvalue())

    def test_rewrite_cycle_and_pass(self):
        # 模拟第1轮未达标（一致性 70 < 90），第2轮改写达标（一致性 95 >= 90）
        r1 = {"text": "第一稿正文主角A登场，但表现平淡。", "elapsed": 1.2, "prompt_tokens": 100, "completion_tokens": 200}
        r2 = {"text": "第二稿正文主角A说休想，情绪充沛，体感描写丰富。", "elapsed": 1.5, "prompt_tokens": 150, "completion_tokens": 250}

        mock_consistency = mock.MagicMock()
        # 依次返回第1轮与第2轮的分数
        mock_consistency.score_text.side_effect = [
            (70.0, ["缺少核心口头禅 → 扣分"], {}),
            (95.0, ["核心词命中 ✓"], {}),
            # 入库后门禁的第三次调用
            (95.0, ["核心词命中 ✓"], {}),
        ]
        mock_consistency.extract_keywords.return_value = ["休想"]

        mock_qc = mock.MagicMock()
        mock_qc.resolve_thresholds.return_value = (75, 60)
        mock_qc.chapter_check.return_value = {
            "score": 85,
            "issues": [],
            "verdict": "PASS",
        }

        mock_bq = mock.MagicMock()
        mock_bq.book_quality_check.return_value = {
            "total_chapters": 1,
            "total_issues": 0,
            "verdict": "PASS",
            "issues": [],
        }

        args = [
            "write.py",
            "--prompt", str(self.prompt_file),
            "--chapter", "1",
            "--task", "绝地反击剧情",
            "--novel-dir", str(self.novel_dir),
            "--voice", str(self.voice_file),
            "--target-score", "90",
            "--words", "1000",
        ]

        with mock.patch.object(write.llm_client, "any_model_configured", return_value=True), \
             mock.patch.object(write.llm_client, "chat", side_effect=[r1, r2]) as mock_chat, \
             mock.patch.dict("sys.modules", {"consistency": mock_consistency, "chapter_check": mock_qc, "book_quality": mock_bq}), \
             mock.patch("sys.argv", args), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:

            exit_code = write.main()
            self.assertEqual(exit_code, 0)  # 成功完成显式返回 0
            out = mock_out.getvalue()
            self.assertIn("未达标，携带扣分明细改写（第2轮）", out)
            self.assertIn("双维度达标，无需改写", out)
            self.assertIn("完成: 第1章已写入", out)

            # 校验 chat 被调用了 2 次
            self.assertEqual(mock_chat.call_count, 2)
            # 校验第 2 次调用的 user 提示词带有改写指令与角色核心词
            second_user_prompt = mock_chat.call_args_list[1][1]["user"]
            self.assertIn("请【改写】上一稿", second_user_prompt)
            self.assertIn("主角A：务必让对话中出现「休想」", second_user_prompt)

            # 验证章节文件最终真实入库
            ch_saved = self.novel_dir / "chapters" / "arc-1" / "chapter-001.txt"
            self.assertTrue(ch_saved.exists())
            self.assertEqual(ch_saved.read_text(encoding="utf-8"), r2["text"])

    def test_outline_context_and_quality_target_parsing(self):
        # 预先在 novel_dir 下放置大纲 outline.md
        chapters_dir = self.novel_dir / "chapters"
        chapters_dir.mkdir(parents=True)
        (chapters_dir / "outline.md").write_text("第1章大纲：宗门大比开始", encoding="utf-8")

        r_ok = {"text": "大纲指导下的正文内容。", "elapsed": 1.0, "prompt_tokens": 80, "completion_tokens": 150}

        args = [
            "write.py",
            "--prompt", str(self.prompt_file),
            "--chapter", "1",
            "--task", "大纲推进任务",
            "--novel-dir", str(self.novel_dir),
            "--quality-target", "80",
        ]

        with mock.patch.object(write.llm_client, "any_model_configured", return_value=True), \
             mock.patch.object(write.llm_client, "chat", return_value=r_ok) as mock_chat, \
             mock.patch("sys.argv", args), \
             mock.patch("sys.stdout", new_callable=io.StringIO):

            write.main()
            first_user_prompt = mock_chat.call_args_list[0][1]["user"]
            self.assertIn("【已有大纲】", first_user_prompt)
            self.assertIn("第1章大纲：宗门大比开始", first_user_prompt)


    def test_main_with_explicit_argv_and_dry_run(self):
        argv = [
            "--prompt", str(self.prompt_file),
            "--chapter", "1",
            "--task", "测试任务",
            "--novel-dir", str(self.novel_dir),
            "--dry-run",
        ]
        with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = write.main(argv)
            self.assertEqual(code, 0)
            self.assertIn("[dry-run]", mock_out.getvalue())

    def test_main_oversized_chapter_number_error(self):
        argv = [
            "--prompt", str(self.prompt_file),
            "--chapter", "100001",
            "--task", "测试任务",
            "--novel-dir", str(self.novel_dir),
        ]
        with self.assertRaises(SystemExit) as cm:
            write.main(argv)
        self.assertIn("章节号过大", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
