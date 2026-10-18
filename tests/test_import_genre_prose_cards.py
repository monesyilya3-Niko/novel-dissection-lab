#!/usr/bin/env python3
"""题材文风散文卡转换引擎（import_genre_prose_cards.py）全维独立测试套件。

涵盖：
1. 辅助函数（_now_iso, _confidence_map, _as_str_list, _extract_forbidden_elements）；
2. Markdown 小节动态解析（parse_sections 忽略一级标题、动态提取二级标题、保留空行与格式）；
3. 题材 ID 确定性解析（resolve_genre_id 查表、fallback_id 与默认拼接兜底）；
4. 散文卡组装（build_genre_prose_card 字段结构、禁忌句提取、钩子/节奏/爽点映射、prose 原文兜底）；
5. 批处理与索引导出（import_cards 目录校验/跳过无 frontmatter/失败无二级标题/成功落盘；write_index 索引生成）；
6. 命令行接口（CLI main 成功退出码 0 与失败退出码 1）。
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import import_genre_prose_cards as ig  # noqa: E402


class TestImportGenreHelpers(unittest.TestCase):
    """测试底层辅助函数。"""

    def test_now_iso_format(self):
        ts = ig._now_iso()
        # 能够被 ISO 8601 解析
        dt = datetime.fromisoformat(ts)
        self.assertIsNotNone(dt.tzinfo)

    def test_confidence_map(self):
        # 字符串映射
        self.assertEqual(ig._confidence_map("high"), 0.85)
        self.assertEqual(ig._confidence_map("HIGH"), 0.85)
        self.assertEqual(ig._confidence_map(" medium "), 0.65)
        self.assertEqual(ig._confidence_map("low"), 0.4)
        # 浮点数与整型直通（排除 bool）
        self.assertEqual(ig._confidence_map(0.95), 0.95)
        self.assertEqual(ig._confidence_map(1), 1.0)
        self.assertEqual(ig._confidence_map(True), 0.5)
        # 兜底默认值
        self.assertEqual(ig._confidence_map("unknown"), 0.5)
        self.assertEqual(ig._confidence_map(None), 0.5)

    def test_as_str_list(self):
        self.assertEqual(ig._as_str_list(None), [])
        self.assertEqual(ig._as_str_list(""), [])
        self.assertEqual(ig._as_str_list("   "), [])
        self.assertEqual(ig._as_str_list("仙侠"), ["仙侠"])
        self.assertEqual(ig._as_str_list(["玄幻", "  ", "修仙"]), ["玄幻", "修仙"])
        self.assertEqual(ig._as_str_list(123), ["123"])

    def test_extract_forbidden_elements(self):
        text = (
            "开篇要稳。千万不要出现任何现代科技词汇。\n"
            "在设定方面，禁止主角无理由圣母；对于敌人，不得心慈手软放虎归山。"
            "日常对话自然，切勿机械死板。"
        )
        elements = ig._extract_forbidden_elements(text)
        self.assertIn("不要出现任何现代科技词汇", elements)
        self.assertIn("禁止主角无理由圣母", elements)
        self.assertIn("不得心慈手软放虎归山", elements)

        # 空白文本
        self.assertEqual(ig._extract_forbidden_elements(""), [])
        self.assertEqual(ig._extract_forbidden_elements("   \n\t  "), [])


class TestParseSections(unittest.TestCase):
    """测试 markdown 小节动态解析。"""

    def test_parse_sections_dynamic(self):
        body = """# 东方仙侠正文提示卡

前言说明，不属于任何二级小节。

## 正文提示词
高武世界，仙凡有别。
心性第一，机缘第二。

## 禁止漂移
不要出现赛博朋克设定。
不得随意跨境界杀敌。

## 场景颗粒
青石小径，竹林落叶。
"""
        sections = ig.parse_sections(body)
        self.assertEqual(len(sections), 3)
        self.assertIn("正文提示词", sections)
        self.assertIn("禁止漂移", sections)
        self.assertIn("场景颗粒", sections)
        self.assertIn("高武世界，仙凡有别。", sections["正文提示词"])
        self.assertIn("不要出现赛博朋克设定。", sections["禁止漂移"])
        self.assertIn("青石小径，竹林落叶。", sections["场景颗粒"])

    def test_parse_sections_empty_and_no_h2(self):
        self.assertEqual(ig.parse_sections(""), {})
        self.assertEqual(ig.parse_sections("# 纯一级标题\n内容"), {})


class TestResolveGenreId(unittest.TestCase):
    """测试题材 ID 确定性解析。"""

    def test_known_genres_in_map(self):
        self.assertEqual(ig.resolve_genre_id("东方仙侠"), "genre-xianxia")
        self.assertEqual(ig.resolve_genre_id("青春甜宠"), "genre-qingchun-tianchong")
        self.assertEqual(ig.resolve_genre_id("科幻末世"), "genre-kehuan-moshi")

    def test_unknown_genre_with_fallback(self):
        self.assertEqual(ig.resolve_genre_id("赛博修真", fallback_id="genre-cyber-xianxia"), "genre-cyber-xianxia")

    def test_unknown_genre_default(self):
        self.assertEqual(ig.resolve_genre_id("赛博修真"), "genre-赛博修真")


class TestBuildGenreProseCard(unittest.TestCase):
    """测试 build_genre_prose_card 组装结构规范。"""

    def test_full_assembly(self):
        frontmatter = {
            "genre": "东方仙侠",
            "aliases": ["古典仙侠", "凡人流"],
            "platform": "起点",
            "confidence": "high",
        }
        sections = {
            "正文提示词": "凡人修仙，道心唯坚。",
            "禁止漂移": "不要加入机甲元素。不得凭空升级。",
            "对话与声线": "沉稳干练，不言虚妄。",
            "章尾钩子": "神秘残卷现世。",
            "正文落点": "停在破庙避雨瞬间。",
            "节奏密度": "每三章一次小突破。",
            "前中后期打法": "前期苟道，中期入世，后期问道。",
            "爽点与情绪释放": "筑基丹争夺胜出。",
            "证据摘要": "对标《凡人修仙传》前50章数据统计。",
            "场景颗粒": "灵石泛着微弱白光。",
        }

        card = ig.build_genre_prose_card(frontmatter, sections, "genre-xianxia")

        # 1. 元数据
        meta = card["meta"]
        self.assertEqual(meta["id"], "genre-xianxia")
        self.assertEqual(meta["name"], "东方仙侠")
        self.assertEqual(meta["kind"], "genre-prose-card")
        self.assertEqual(meta["sub_tags"], ["古典仙侠", "凡人流"])
        self.assertEqual(meta["target_platform"], "起点")
        self.assertEqual(meta["confidence"], 0.85)
        self.assertEqual(meta["upgrade_status"], "seed")
        self.assertEqual(meta["provenance"]["source"], ig.PROVENANCE_SOURCE)
        self.assertEqual(meta["provenance"]["license"], ig.PROVENANCE_LICENSE)
        self.assertEqual(meta["provenance"]["evidence"], "对标《凡人修仙传》前50章数据统计。")

        # 2. 语言与声线
        lang = card["language_rules"]
        self.assertIn("不要加入机甲元素", lang["forbidden_elements"])
        self.assertIn("不得凭空升级", lang["forbidden_elements"])
        self.assertEqual(lang["voice_notes"], "沉稳干练，不言虚妄。")
        self.assertEqual(lang["banned_phrases"], [])

        # 3. 结构与商业节奏
        struct = card["structure"]
        self.assertIn("神秘残卷现世。", struct["hook_notes"])
        self.assertIn("停在破庙避雨瞬间。", struct["hook_notes"])
        self.assertIn("每三章一次小突破。", struct["arc_rhythm_notes"])
        self.assertIn("前期苟道，中期入世，后期问道。", struct["arc_rhythm_notes"])

        comm = card["commercial"]
        self.assertEqual(comm["payoff_notes"], "筑基丹争夺胜出。")

        # 4. 原始小节兜底
        self.assertEqual(card["prose"]["sections"], sections)

    def test_minimal_assembly_without_optional_sections(self):
        frontmatter = {"genre": "微型题材"}
        sections = {"正文提示词": "极简设定。"}
        card = ig.build_genre_prose_card(frontmatter, sections, "genre-tiny")
        self.assertEqual(card["meta"]["id"], "genre-tiny")
        self.assertNotIn("structure", card)
        self.assertNotIn("commercial", card)
        self.assertEqual(card["language_rules"]["forbidden_elements"], [])


class TestImportCardsAndWriteIndex(unittest.TestCase):
    """测试 import_cards 批处理与 write_index 索引落盘。"""

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp_dir.name)
        self.src_dir = self.tmp_path / "src"
        self.out_dir = self.tmp_path / "assets"
        self.src_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_non_existent_source(self):
        s, sk, f, idx = ig.import_cards(self.tmp_path / "not_exist", self.out_dir)
        self.assertEqual(len(f), 1)
        self.assertIn("源目录不存在", f[0])

    def test_empty_source(self):
        s, sk, f, idx = ig.import_cards(self.src_dir, self.out_dir)
        self.assertEqual(len(f), 1)
        self.assertIn("源目录无 *.md 文件", f[0])

    def test_batch_import_and_index(self):
        # 1. 正常有效卡片
        valid_card = """---
genre: 东方仙侠
aliases: [修真, 仙侠]
platform: 起点
confidence: high
---

# 东方仙侠

## 正文提示词
仙侠正文提示内容。

## 禁止漂移
不要出现热武器。
"""
        (self.src_dir / "东方仙侠.md").write_text(valid_card, encoding="utf-8")

        # 2. 缺少 frontmatter 的文件（应跳过）
        no_fm = """# 纯正文卡片
## 小节
内容
"""
        (self.src_dir / "无元数据.md").write_text(no_fm, encoding="utf-8")

        # 3. 缺少二级小节的文件（应失败）
        no_h2 = """---
genre: 损坏题材
---
# 只有一级标题
没有二级标题
"""
        (self.src_dir / "无小节.md").write_text(no_h2, encoding="utf-8")

        success, skipped, failed, index = ig.import_cards(self.src_dir, self.out_dir)

        self.assertEqual(len(success), 1)
        self.assertEqual(len(skipped), 1)
        self.assertEqual(len(failed), 1)

        self.assertIn("东方仙侠", index)
        self.assertEqual(index["东方仙侠"]["id"], "genre-xianxia")

        # 验证落盘文件
        out_file = self.out_dir / "genre-prose-card-genre-xianxia.json"
        self.assertTrue(out_file.exists())
        saved_data = json.loads(out_file.read_text(encoding="utf-8"))
        self.assertEqual(saved_data["meta"]["name"], "东方仙侠")

        # 验证索引写入
        idx_path = ig.write_index(index, self.out_dir)
        self.assertTrue(idx_path.exists())
        idx_data = json.loads(idx_path.read_text(encoding="utf-8"))
        self.assertEqual(idx_data["_count"], 1)
        self.assertIn("东方仙侠", idx_data["cards"])


class TestImportGenreProseCardsCLI(unittest.TestCase):
    """测试命令行接口。"""

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp_dir.name)
        self.src_dir = self.tmp_path / "src"
        self.out_dir = self.tmp_path / "out"
        self.src_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_cli_success(self):
        card = """---
genre: 传统玄幻
---
## 正文提示词
玄幻提示词内容。
"""
        (self.src_dir / "传统玄幻.md").write_text(card, encoding="utf-8")

        f = io.StringIO()
        with patch("sys.stdout", f):
            code = ig.main(["--src", str(self.src_dir), "--out", str(self.out_dir)])
        self.assertEqual(code, 0)
        output = f.getvalue()
        self.assertIn("转换完成：成功 1 / 跳过 0 / 失败 0", output)
        self.assertTrue((self.out_dir / "genre-prose-card-index.json").exists())

    def test_cli_failure_on_error(self):
        card = """---
genre: 损坏题材
---
无小节文本
"""
        (self.src_dir / "坏卡.md").write_text(card, encoding="utf-8")

        f = io.StringIO()
        with patch("sys.stdout", f):
            code = ig.main(["--src", str(self.src_dir), "--out", str(self.out_dir)])
        self.assertEqual(code, 1)
        output = f.getvalue()
        self.assertIn("失败 1", output)


if __name__ == "__main__":
    unittest.main()
