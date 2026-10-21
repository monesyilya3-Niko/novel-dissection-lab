"""原文引用清洗脚本 clean_verbatim.py 单元与行为级测试（纯标准库，零第三方依赖）。

覆盖 scripts/clean_verbatim.py：
1. clean_string 字符串清洗：
   - 无原文引用的正常描述保持原样（changed=False）；
   - 清除「例如/比如/如：」后紧跟的大于 8 字引号片段；
   - 清除引号内大于 12 字且命中原文 n-gram 的连续匹配片段；
   - 保留小于等于 12 字或非原文的短语引号；
   - 中文与英文各色引号对（「」『』“”‘’""''）全面支持；
   - 清洗后孤立残存引号清理；
   - 清洗后标点冗余清理（如、。、、等）。
2. main CLI 批处理与原地覆写：
   - 缺省无 --apply 模式：纯检查报告，不覆写磁盘文件；
   - 带 --apply 模式：递归遍历字典与列表中的字符串，原地写回清洗结果；
   - 清洗后调用 compliance.scan_asset 复扫输出。
"""
from __future__ import annotations

import io
import json
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

import clean_verbatim  # noqa: E402
import compliance  # noqa: E402


class TestCleanString(unittest.TestCase):
    """clean_string 纯函数清洗逻辑测试。"""

    def setUp(self):
        self.corpus = "这是一个非常神秘的修仙古老宗门里面隐藏着无尽的天材地宝与神兵利器"
        self.ngram = compliance.build_ngram_index(self.corpus)

    def test_clean_string_no_change_for_clean_text(self):
        text = "本作采用倒叙手法，通过人物细微的神态描写交代悬念。"
        res, changed = clean_verbatim.clean_string(text, self.ngram, "test.path")
        self.assertEqual(res, text)
        self.assertFalse(changed)

    def test_clean_string_removes_example_long_quotes(self):
        # 「例如：」后紧跟 >8 字的片段
        text = "作者善用心理压迫，例如：『她狠狠地把门给摔上了并且大声叫喊着』，制造紧绷感。"
        res, changed = clean_verbatim.clean_string(text, self.ngram, "test.path")
        self.assertTrue(changed)
        self.assertNotIn("她狠狠地把门给摔上了", res)
        self.assertIn("例如", res)

    def test_clean_string_removes_twelve_gram_verbatim_quotes(self):
        # 命中原文 12-gram
        text = "男主身世成谜，台词道：“这是一个非常神秘的修仙古老宗门”，随后拔剑。"
        res, changed = clean_verbatim.clean_string(text, self.ngram, "test.path")
        self.assertTrue(changed)
        self.assertNotIn("这是一个非常神秘的修仙古老宗门", res)
        self.assertIn("男主身世成谜", res)
        self.assertIn("随后拔剑", res)

    def test_clean_string_preserves_short_non_verbatim_quotes(self):
        # 保留合法短引用
        text = "人物性格坚韧，口头禅是「绝不放弃」与『向前冲』。"
        res, changed = clean_verbatim.clean_string(text, self.ngram, "test.path")
        self.assertIn("「绝不放弃」", res)
        self.assertIn("『向前冲』", res)

    def test_clean_string_fixes_punctuation_artifacts(self):
        # 清洗后产生的标点多余修复
        text = "先看开头，例如：“一段非常冗长而且无意义的流水账说明文字”，、随后推进剧情。"
        res, _changed = clean_verbatim.clean_string(text, self.ngram, "test.path")
        self.assertNotIn("，、", res)
        self.assertNotIn("、、", res)


class TestCleanVerbatimCli(unittest.TestCase):
    """clean_verbatim main 命令行测试。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="clean_verbatim_test_")
        self.dir_path = Path(self.temp_dir)
        self.book_path = self.dir_path / "book.txt"
        self.book_path.write_text("这是一个非常神秘的修仙古老宗门里面隐藏着无尽的天材地宝与神兵利器", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cli_dry_run_does_not_modify_file(self):
        asset_data = {
            "name": "测试资产",
            "desc": "比如：“这是一个非常神秘的修仙古老宗门”的描述。",
        }
        asset_file = self.dir_path / "asset.json"
        asset_file.write_text(json.dumps(asset_data, ensure_ascii=False), encoding="utf-8")

        test_args = ["clean_verbatim.py", str(asset_file), str(self.book_path)]
        with mock.patch("sys.argv", test_args), mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            clean_verbatim.main()
            output = out.getvalue()
            self.assertIn("发现 1 处原文引用待清洗", output)

        # 磁盘文件内容未变
        content = json.loads(asset_file.read_text(encoding="utf-8"))
        self.assertEqual(content["desc"], asset_data["desc"])

    def test_cli_apply_in_place_modifies_file(self):
        asset_data = {
            "name": "测试资产",
            "techniques": [
                {"example": "比如：“这是一个非常神秘的修仙古老宗门”的场景。"},
                {"safe": "纯原创技法分析。"},
            ],
        }
        asset_file = self.dir_path / "asset.json"
        asset_file.write_text(json.dumps(asset_data, ensure_ascii=False), encoding="utf-8")

        test_args = ["clean_verbatim.py", str(asset_file), str(self.book_path), "--apply"]
        with mock.patch("sys.argv", test_args), mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = clean_verbatim.main()
            self.assertEqual(ret, 0)
            output = out.getvalue()
            self.assertIn("已清洗 1 处并保存", output)

        # 磁盘文件内容已改写
        content = json.loads(asset_file.read_text(encoding="utf-8"))
        self.assertNotIn("这是一个非常神秘的修仙古老宗门", content["techniques"][0]["example"])

    def test_cli_with_explicit_argv(self):
        asset_data = {
            "name": "显式传参资产",
            "desc": "原创内容，无引用",
        }
        asset_file = self.dir_path / "explicit_asset.json"
        asset_file.write_text(json.dumps(asset_data, ensure_ascii=False), encoding="utf-8")
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = clean_verbatim.main([str(asset_file), str(self.book_path)])
            self.assertEqual(ret, 0)
            self.assertIn("发现 0 处原文引用待清洗", out.getvalue())


if __name__ == "__main__":
    unittest.main()
