#!/usr/bin/env python3
"""全方位深海级终极体检与盲区穿透审计（scripts/exhaustive_audit_all_aspects.py）单元测试。

覆盖范围：
1. get_default_corpus_db 路径解析与环境变量覆盖
2. 盲区 A：文本底层坏字符、乱码符 (\ufffd)、HTML 实体与二进制空字节 (\x00)
3. 盲区 B：章节首末完整性、分卷结构与体量实质连续性（开篇正则、最小章节数、单章均长）
4. 盲区 C：SQLite 数据库底层物理完整性与外键约束 (integrity_check & foreign_key_check)
5. 盲区 D：反哺写作工坊服务层真实贯通与闭环撤销测试 (outline / character / note)
6. 盲区 E：统计汇总服务与 API 聚合契约深度检验 (list_books / list_assets / get_book / list_chains)
7. main CLI 命令行分发与状态码裁决 (--db / -q / --expected-books / --min-chapters / --min-avg-len)
"""
from __future__ import annotations

import gc
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui import db
from scripts import exhaustive_audit_all_aspects


class TestExhaustiveAuditAllAspects(unittest.TestCase):
    """深海级全方位盲区穿透体检独立单元测试集。"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="exhaustive_audit_test_")
        self.tmp_path = Path(self.tmp_dir.name)
        self.db_path = self.tmp_path / "test_corpus.db"

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_test_schema(self.conn)

    def tearDown(self):
        if hasattr(self, "conn") and self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
        db.close()
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except OSError:
            pass

    def _init_test_schema(self, conn: sqlite3.Connection) -> None:
        """初始化测试数据库表结构（与生产环境 schema 和 migrations 完全同构）。"""
        orig = db.get_conn
        db.get_conn = lambda: conn
        try:
            db.init_schema()
            db.apply_migrations()
        finally:
            db.get_conn = orig

    def _create_sample_novel_file(
        self,
        filename: str = "book1.txt",
        content: str | None = None,
    ) -> Path:
        """创建样本小说文件。"""
        file_path = self.tmp_path / filename
        if content is None:
            # 默认合规正文：第一章起步，汉字纯度高
            content = (
                "第一章 荒古禁地\n"
                "九龙拉棺，穿破星河浩渺。少年叶凡伫立泰山之巅，俯瞰沧海桑田。"
                "前路漫漫，古道苍凉，这一去便是星空彼岸，征战无止境！\n" * 15 + "\n"
                "第二章 绝代仙路\n"
                "星空彼岸，铜棺震动。古老而荒凉的大地横亘于虚空之中，无尽奥秘正在静静等待。\n" * 15
            )
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def _insert_valid_book_data(
        self,
        book_id: str = "book_001",
        title: str = "星辰变",
        source_path: str = "",
        total_chapters: int = 100,
        total_chars: int = 200000,
    ) -> None:
        """插入一条完全合规的书籍、4张资产卡及1条伏笔链。"""
        self.conn.execute(
            "INSERT INTO books (book_id, title, genre) VALUES (?, ?, 'xuanhuan')",
            (book_id, title),
        )
        self.conn.execute(
            """INSERT INTO essence_books
               (book_id, title, source_path, genre, platform, total_chapters, total_chars, meta_json)
               VALUES (?, ?, ?, 'xuanhuan', 'qidian', ?, ?, '{"summary": "神作总结"}')""",
            (book_id, title, source_path, total_chapters, total_chars),
        )
        categories = ["opening", "outline", "persona", "style"]
        for cat in categories:
            self.conn.execute(
                """INSERT INTO essence_assets
                   (book_id, category, title, summary, content, rating)
                   VALUES (?, ?, ?, ?, ?, 5.0)""",
                (
                    book_id,
                    cat,
                    f"《{title}》{cat}分析",
                    f"这是《{title}》的{cat}核心提炼摘要，具备充分深度。",
                    f"正文深度拆解分析：剖析了《{title}》在{cat}维度的起承转合与技法精髓，结构严密无空白。" * 2,
                ),
            )
        self.conn.execute(
            """INSERT INTO essence_chains
               (book_id, clue_name, hook_chapter, hook_text, payoff_chapter, payoff_text, analysis)
               VALUES (?, '流星泪', 1, '黑夜之中流星陨落融入主角胸膛。', 50, '流星泪彻底融合觉醒生命主神之力。', '典型悬念伏笔长线回收。')""",
            (book_id,),
        )
        self.conn.commit()

    # -------------------------------------------------------------------------
    # 路径与环境变量解析测试
    # -------------------------------------------------------------------------

    def test_get_default_corpus_db_env(self):
        """测试 EXOSCRIBE_CORPUS_DB 优先覆盖。"""
        custom_target = self.tmp_path / "custom_env.db"
        old_env = os.environ.get("EXOSCRIBE_CORPUS_DB")
        try:
            os.environ["EXOSCRIBE_CORPUS_DB"] = str(custom_target)
            resolved = exhaustive_audit_all_aspects.get_default_corpus_db()
            self.assertEqual(resolved, custom_target.resolve())
        finally:
            if old_env is None:
                os.environ.pop("EXOSCRIBE_CORPUS_DB", None)
            else:
                os.environ["EXOSCRIBE_CORPUS_DB"] = old_env

    def test_get_default_corpus_db_fallback(self):
        """测试默认兜底解析有效。"""
        old_env = os.environ.pop("EXOSCRIBE_CORPUS_DB", None)
        try:
            resolved = exhaustive_audit_all_aspects.get_default_corpus_db()
            self.assertTrue(isinstance(resolved, Path))
            self.assertTrue(str(resolved).endswith("index.db"))
        finally:
            if old_env is not None:
                os.environ["EXOSCRIBE_CORPUS_DB"] = old_env

    # -------------------------------------------------------------------------
    # 盲区 A：文本底层坏字符与乱码符扫描
    # -------------------------------------------------------------------------

    def test_audit_blindspot_a_pass(self):
        """测试盲区 A 在干净文本下通过。"""
        p = self._create_sample_novel_file("clean.txt")
        self._insert_valid_book_data("b1", "星辰变", str(p))

        passed = exhaustive_audit_all_aspects.audit_blindspot_a_encoding_and_bad_chars(
            self.conn, quiet=True
        )
        self.assertTrue(passed)

    def test_audit_blindspot_a_fail_missing_file(self):
        """测试盲区 A 在物理文件缺失时报告异常。"""
        self._insert_valid_book_data("b1", "缺失书目", str(self.tmp_path / "not_found.txt"))
        passed = exhaustive_audit_all_aspects.audit_blindspot_a_encoding_and_bad_chars(
            self.conn, quiet=True
        )
        self.assertFalse(passed)

    def test_audit_blindspot_a_fail_null_bytes(self):
        """测试盲区 A 拦截空字节 (\\x00) 污染。"""
        p = self.tmp_path / "null_byte.txt"
        p.write_bytes(b"hello \x00 world \xe4\xb8\xad\xe6\x96\x87")
        self._insert_valid_book_data("b1", "二进制污染书", str(p))

        passed = exhaustive_audit_all_aspects.audit_blindspot_a_encoding_and_bad_chars(
            self.conn, quiet=True
        )
        self.assertFalse(passed)

    def test_audit_blindspot_a_fail_ufffd_corruption(self):
        """测试盲区 A 拦截 \\ufffd 乱码符。"""
        p = self._create_sample_novel_file("garbled.txt", "第一章 乱码\n\ufffd\ufffd异常文本")
        self._insert_valid_book_data("b1", "乱码书", str(p))

        passed = exhaustive_audit_all_aspects.audit_blindspot_a_encoding_and_bad_chars(
            self.conn, quiet=True
        )
        self.assertFalse(passed)

    def test_audit_blindspot_a_empty_table(self):
        """测试盲区 A 在空表时返回 False。"""
        passed = exhaustive_audit_all_aspects.audit_blindspot_a_encoding_and_bad_chars(
            self.conn, quiet=True
        )
        self.assertFalse(passed)

    # -------------------------------------------------------------------------
    # 盲区 B：章节序号递增性与实质体量连续性
    # -------------------------------------------------------------------------

    def test_audit_blindspot_b_pass(self):
        """测试盲区 B 在规范起始与充分体量下通过。"""
        # 构造包含 3 章且均长达标的文本，并设置 min_chapters=2, min_avg_len=50
        content = (
            "第一章 启程\n" + "正文内容。" * 20 + "\n"
            "第二章 历练\n" + "正文内容。" * 20 + "\n"
            "第三章 巅峰\n" + "正文内容。" * 20 + "\n"
        )
        p = self._create_sample_novel_file("novel_b.txt", content)
        self._insert_valid_book_data("b1", "星辰变", str(p), total_chapters=3, total_chars=600)

        passed = exhaustive_audit_all_aspects.audit_blindspot_b_chapter_number_sequence(
            self.conn, min_chapters=2, min_avg_len=50, quiet=True
        )
        self.assertTrue(passed)

    def test_audit_blindspot_b_fail_broken_first_chapter(self):
        """测试盲区 B 拦截从非规范章节（如第 99 章）开头的跳跃断层书。"""
        content = "第99章 突兀开头\n" + "正文内容。" * 20 + "\n"
        p = self._create_sample_novel_file("broken_start.txt", content)
        self._insert_valid_book_data("b1", "断头小说", str(p), total_chapters=10, total_chars=1000)

        passed = exhaustive_audit_all_aspects.audit_blindspot_b_chapter_number_sequence(
            self.conn, min_chapters=1, min_avg_len=10, quiet=True
        )
        self.assertFalse(passed)

    def test_audit_blindspot_b_fail_low_chapter_count_or_length(self):
        """测试盲区 B 拦截章节总数过少或单章均长不足的书籍。"""
        content = "第一章 极短\n短内容。\n"
        p = self._create_sample_novel_file("too_short.txt", content)
        self._insert_valid_book_data("b1", "极短小说", str(p), total_chapters=1, total_chars=10)

        # 默认阈值 min_chapters=60, min_avg_len=800
        passed = exhaustive_audit_all_aspects.audit_blindspot_b_chapter_number_sequence(
            self.conn, min_chapters=60, min_avg_len=800, quiet=True
        )
        self.assertFalse(passed)

    # -------------------------------------------------------------------------
    # 盲区 C：SQLite 数据库底层物理完整性
    # -------------------------------------------------------------------------

    def test_audit_blindspot_c_pass(self):
        """测试盲区 C 数据库物理与外键完整性通过。"""
        passed = exhaustive_audit_all_aspects.audit_blindspot_c_sqlite_integrity(
            self.conn, quiet=True
        )
        self.assertTrue(passed)

    # -------------------------------------------------------------------------
    # 盲区 D：一键反哺写作工坊服务层真实贯通与闭环撤销
    # -------------------------------------------------------------------------

    def test_audit_blindspot_d_pass(self):
        """测试盲区 D 反哺大纲、人物卡、灵感便签并彻底清理沙盒数据。"""
        self._insert_valid_book_data("b1", "吞噬星空")

        passed = exhaustive_audit_all_aspects.audit_blindspot_d_feed_into_writing_workshop(
            self.conn, quiet=True
        )
        self.assertTrue(passed)

        # 验证沙盒数据已被干净自清理
        test_proj = "test_audit_isolation_project"
        c_out = self.conn.execute("SELECT count(*) FROM writing_outlines WHERE project = ?", (test_proj,)).fetchone()[0]
        c_char = self.conn.execute("SELECT count(*) FROM writing_characters WHERE project = ?", (test_proj,)).fetchone()[0]
        c_note = self.conn.execute("SELECT count(*) FROM writing_notes WHERE project = ?", (test_proj,)).fetchone()[0]
        self.assertEqual(c_out, 0)
        self.assertEqual(c_char, 0)
        self.assertEqual(c_note, 0)

    def test_audit_blindspot_d_fail_no_assets(self):
        """测试盲区 D 在无可反哺资产时返回 False。"""
        passed = exhaustive_audit_all_aspects.audit_blindspot_d_feed_into_writing_workshop(
            self.conn, quiet=True
        )
        self.assertFalse(passed)

    # -------------------------------------------------------------------------
    # 盲区 E：统计汇总服务与 API 聚合契约深度检验
    # -------------------------------------------------------------------------

    def test_audit_blindspot_e_pass(self):
        """测试盲区 E 在完全合规数据下通过。"""
        self._insert_valid_book_data("b1", "遮天")

        # 传 expected_books=1
        passed = exhaustive_audit_all_aspects.audit_blindspot_e_api_contract_and_stats(
            self.conn, expected_books=1, quiet=True
        )
        self.assertTrue(passed)

        # 传 expected_books=None 自动适应
        passed_auto = exhaustive_audit_all_aspects.audit_blindspot_e_api_contract_and_stats(
            self.conn, expected_books=None, quiet=True
        )
        self.assertTrue(passed_auto)

    def test_audit_blindspot_e_fail_expected_mismatch(self):
        """测试盲区 E 在书目数量与期望不符时拦截。"""
        self._insert_valid_book_data("b1", "遮天")
        passed = exhaustive_audit_all_aspects.audit_blindspot_e_api_contract_and_stats(
            self.conn, expected_books=100, quiet=True
        )
        self.assertFalse(passed)

    def test_audit_blindspot_e_fail_empty_table(self):
        """测试盲区 E 在空库时返回 False。"""
        passed = exhaustive_audit_all_aspects.audit_blindspot_e_api_contract_and_stats(
            self.conn, expected_books=None, quiet=True
        )
        self.assertFalse(passed)

    # -------------------------------------------------------------------------
    # CLI main() 集成测试
    # -------------------------------------------------------------------------

    def test_main_cli_success(self):
        """测试 main() 接收 CLI 参数并返回 0 (全部通过)。"""
        content = (
            "第一章 初入仙门\n" + "正文内容。" * 20 + "\n"
            "第二章 纵横四海\n" + "正文内容。" * 20 + "\n"
        )
        p = self._create_sample_novel_file("main_pass.txt", content)
        self._insert_valid_book_data("b1", "凡人修仙传", str(p), total_chapters=2, total_chars=400)

        ret = exhaustive_audit_all_aspects.main([
            "--db", str(self.db_path),
            "--expected-books", "1",
            "--min-chapters", "2",
            "--min-avg-len", "50",
            "-q",
        ])
        self.assertEqual(ret, 0)

    def test_main_cli_db_not_found(self):
        """测试 main() 数据库文件不存在时返回 1。"""
        non_existent = self.tmp_path / "does_not_exist.db"
        ret = exhaustive_audit_all_aspects.main([
            "--db", str(non_existent),
            "-q",
        ])
        self.assertEqual(ret, 1)

    def test_main_cli_failure_on_audit_defect(self):
        """测试 main() 存在缺陷时返回 1。"""
        # 插入空字节文件引发盲区 A 失败
        bad_p = self.tmp_path / "bad.txt"
        bad_p.write_bytes(b"\x00 bad data")
        self._insert_valid_book_data("b1", "坏书", str(bad_p))

        ret = exhaustive_audit_all_aspects.main([
            "--db", str(self.db_path),
            "--expected-books", "1",
            "-q",
        ])
        self.assertEqual(ret, 1)


if __name__ == "__main__":
    unittest.main()
