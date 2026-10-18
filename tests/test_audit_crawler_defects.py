"""语料库切片缺陷普查与全书质量核验脚本测试套件。

覆盖：
1. scripts/audit_crawler_defects.py:
   - 默认数据库路径探测与环境变量 EXOSCRIBE_CORPUS_DB 优先机制
   - extract_chapter_titles 章节标题提取与边界过滤
   - detect_sentence_like_titles 标点与超长正文误判标题检测
   - split_raw_chapters / detect_short_chapters 短章物理切片分析
   - detect_max_duplicate_title 重复标题频次统计
   - audit_book_text 文本综合缺陷诊断（短章率、误判标题率、高频重复标题）
   - audit_corpus_db 数据库与物理文件结合巡检（文件缺失、污染识别、limit 参数）
   - main CLI 命令行参数、静默模式与退出码
2. scripts/check_all_books.py:
   - is_clean_start_chapter 首章规范模式判定
   - has_title_tags 爬虫清洗标签探测
   - check_corpus_books 数据库与文件存在性、资产卡/链数量、章节完整性综合体检
   - main CLI 参数与 --strict / --quiet 退出码逻辑
3. scripts/check_ad.py, check_seq.py, check_dp_titles.py, check_search.py, check_shorts.py:
   - 单项数据核验辅助工具的核心函数与 CLI 接口
"""

from __future__ import annotations

import io
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.audit_crawler_defects as acd  # noqa: E402
import scripts.check_ad as cad  # noqa: E402
import scripts.check_all_books as cab  # noqa: E402
import scripts.check_dp_titles as cdp  # noqa: E402
import scripts.check_search as csr  # noqa: E402
import scripts.check_seq as csq  # noqa: E402
import scripts.check_shorts as csh  # noqa: E402


class TestAuditCrawlerDefects(unittest.TestCase):
    """测试 scripts/audit_crawler_defects.py 核心函数与 CLI。"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self):
        import gc
        gc.collect()
        self.tmp_dir.cleanup()

    def test_get_default_corpus_db(self):
        """测试数据库路径解析与环境变量优先机制。"""
        fake_db = self.tmp_path / "custom.db"
        with mock.patch.dict(os.environ, {"EXOSCRIBE_CORPUS_DB": str(fake_db)}):
            self.assertEqual(acd.get_default_corpus_db(), fake_db.resolve())

        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": str(self.tmp_path)}):
                expected = self.tmp_path / "暮冬念春" / "index.db"
                self.assertEqual(acd.get_default_corpus_db(), expected)

    def test_extract_chapter_titles(self):
        """测试章节标题行提取。"""
        content = (
            "前言引言\n"
            "第一章 降临世界\n"
            "这是正文的第一段话。\n\n"
            "第2卷 征程开始\n"
            "第3回 英雄相逢\n"
            "Chapter 4 The End\n"
            "总结附录\n"
        )
        titles = acd.extract_chapter_titles(content)
        self.assertEqual(
            titles,
            ["第一章 降临世界", "第2卷 征程开始", "第3回 英雄相逢", "Chapter 4 The End"],
        )

    def test_detect_sentence_like_titles(self):
        """测试正文误识别为标题（标点与长度）。"""
        titles = [
            "第一章 正常标题",
            "第二章 包含，逗号的句子误入标题",
            "第三章 包含。句号的句子",
            "第四章 包含！感叹号",
            "第五章 包含？问号",
            "第六章 包含……省略号",
            "第七章 “带引号”的标题",
            "第八章 " + "超长字符" * 10,
        ]
        bad = acd.detect_sentence_like_titles(titles, max_len=30)
        self.assertEqual(len(bad), 7)
        self.assertNotIn("第一章 正常标题", bad)

    def test_split_and_detect_short_chapters(self):
        """测试短小章节切片探测。"""
        content = (
            "第1章 正常章节\n" + "正文字符充实内容。" * 20 + "\n"
            "第2章 短章节\n短小\n"
            "第3章 另一个短章节\n也是短小\n"
        )
        chaps = acd.split_raw_chapters(content)
        self.assertEqual(len(chaps), 3)
        shorts = acd.detect_short_chapters(chaps, min_chars=100)
        self.assertEqual(len(shorts), 2)
        self.assertIn("第2章 短章节\n短小", shorts)

    def test_detect_max_duplicate_title(self):
        """测试高频重复标题统计。"""
        self.assertEqual(acd.detect_max_duplicate_title([]), ("", 0))
        titles = ["第一节", "第一节", "第二节", "第一节", "第三节"]
        top_title, count = acd.detect_max_duplicate_title(titles)
        self.assertEqual(top_title, "第一节")
        self.assertEqual(count, 3)

    def test_audit_book_text_clean(self):
        """测试健康文本：无缺陷。"""
        content = "\n".join(
            f"第{i}章 正常标题{i}\n" + "健康小说正文字符" * 25
            for i in range(1, 20)
        )
        report = acd.audit_book_text(content)
        self.assertFalse(report["is_defective"])
        self.assertEqual(report["reasons"], [])

    def test_audit_book_text_short_chapters_defect(self):
        """测试短章率过高缺陷触发。"""
        # 构造超过 10 个短章且占比 > 5% 的文本
        content = "\n".join(
            f"第{i}章 短章节{i}\n短暂" for i in range(1, 15)
        )
        report = acd.audit_book_text(content)
        self.assertTrue(report["is_defective"])
        self.assertTrue(any("短章率过高" in r for r in report["reasons"]))

    def test_audit_book_text_sentence_titles_defect(self):
        """测试正文误作标题率过高缺陷触发。"""
        content = "\n".join(
            f"第{i}章 异常，含有标点句号。的正文误作标题内容{i}\n" + "填充字数" * 30
            for i in range(1, 15)
        )
        report = acd.audit_book_text(content)
        self.assertTrue(report["is_defective"])
        self.assertTrue(any("正文误作标题率高" in r for r in report["reasons"]))

    def test_audit_book_text_repeated_titles_defect(self):
        """测试高频重复标题缺陷触发。"""
        content = "\n".join(
            "第一节\n" + "正文字符" * 30 for _ in range(20)
        )
        report = acd.audit_book_text(content)
        self.assertTrue(report["is_defective"])
        self.assertTrue(any("重复标题过多" in r for r in report["reasons"]))

    def test_audit_corpus_db(self):
        """测试对 SQLite 语料库执行普查（正常、文件缺失与缺陷书籍）。"""
        db_file = self.tmp_path / "test_corpus.db"
        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("""
                CREATE TABLE essence_books (
                    id INTEGER PRIMARY KEY,
                    book_id TEXT,
                    title TEXT,
                    genre TEXT,
                    total_chapters INTEGER,
                    total_chars INTEGER,
                    source_path TEXT
                )
            """)

            # 1. 正常书籍（每章大于 150 字，非短章）
            good_txt = self.tmp_path / "good.txt"
            good_txt.write_text(
                "\n".join(f"第{i}章 正常标题\n" + "文字" * 100 for i in range(1, 20)),
                encoding="utf-8",
            )
            conn.execute(
                "INSERT INTO essence_books VALUES (1, 'b1', '好书', '仙侠', 19, 4000, ?)",
                (str(good_txt),),
            )

            # 2. 缺陷书籍（大量短章）
            bad_txt = self.tmp_path / "bad.txt"
            bad_txt.write_text(
                "\n".join(f"第{i}章 短章\n短" for i in range(1, 15)),
                encoding="utf-8",
            )
            conn.execute(
                "INSERT INTO essence_books VALUES (2, 'b2', '坏书', '科幻', 14, 100, ?)",
                (str(bad_txt),),
            )

            # 3. 缺失物理文件的书籍
            conn.execute(
                "INSERT INTO essence_books VALUES (3, 'b3', '虚无书', '奇幻', 10, 500, ?)",
                (str(self.tmp_path / "nonexistent.txt"),),
            )
            conn.commit()

            # 测试审计所有（传入已有连接）
            defects = acd.audit_corpus_db(conn)
            self.assertEqual(len(defects), 2)
            defect_titles = {d["title"] for d in defects}
            self.assertEqual(defect_titles, {"坏书", "虚无书"})
        finally:
            conn.close()

        # 测试 limit 参数（传入文件路径，内部自动关闭）
        defects_limit = acd.audit_corpus_db(db_file, limit=1)
        self.assertEqual(len(defects_limit), 0)  # 第一本是好书

    def test_main_cli_missing_db(self):
        """测试 CLI 指定不存在的数据库文件。"""
        out = io.StringIO()
        err = io.StringIO()
        with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            code = acd.main(["--db", str(self.tmp_path / "missing.db")])
        self.assertEqual(code, 1)
        self.assertIn("不存在", err.getvalue())

    def test_main_cli_clean_and_defective(self):
        """测试 CLI 发现缺陷时返回 1，健康时返回 0。"""
        db_file = self.tmp_path / "cli_test.db"
        conn = sqlite3.connect(str(db_file))
        try:
            conn.execute("""
                CREATE TABLE essence_books (
                    id INTEGER PRIMARY KEY,
                    book_id TEXT,
                    title TEXT,
                    genre TEXT,
                    total_chapters INTEGER,
                    total_chars INTEGER,
                    source_path TEXT
                )
            """)
            # 插入一本好书（每章大于 150 字）
            good_txt = self.tmp_path / "cli_good.txt"
            good_txt.write_text(
                "\n".join(f"第{i}章 正常标题\n" + "文字" * 100 for i in range(1, 20)),
                encoding="utf-8",
            )
            conn.execute(
                "INSERT INTO essence_books VALUES (1, 'b1', '好书', '仙侠', 19, 4000, ?)",
                (str(good_txt),),
            )
            conn.commit()
        finally:
            conn.close()

        # 好书普查应返回 0
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            code = acd.main(["--db", str(db_file)])
        self.assertEqual(code, 0)
        self.assertIn("发现 0 部", out.getvalue())

        # 静默模式
        code_quiet = acd.main(["--db", str(db_file), "--quiet"])
        self.assertEqual(code_quiet, 0)


class TestCheckAllBooks(unittest.TestCase):
    """测试 scripts/check_all_books.py 核心函数与质量核验引擎。"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self):
        import gc
        gc.collect()
        self.tmp_dir.cleanup()

    def test_is_clean_start_chapter(self):
        """测试首章标题开篇规范判断。"""
        self.assertTrue(cab.is_clean_start_chapter("第一章 重生归来"))
        self.assertTrue(cab.is_clean_start_chapter("第1章 异界"))
        self.assertTrue(cab.is_clean_start_chapter("第01回 结拜"))
        self.assertTrue(cab.is_clean_start_chapter("第1节 序曲"))
        self.assertTrue(cab.is_clean_start_chapter("第1卷 风起"))
        self.assertTrue(cab.is_clean_start_chapter("Chapter 1 Arrival"))
        self.assertTrue(cab.is_clean_start_chapter("Chapter 01 Start"))
        self.assertTrue(cab.is_clean_start_chapter("序言"))
        self.assertTrue(cab.is_clean_start_chapter("引子：星空之下"))
        self.assertTrue(cab.is_clean_start_chapter("楔子"))

        # 疑似中途断章
        self.assertFalse(cab.is_clean_start_chapter("第50章 绝地反击"))
        self.assertFalse(cab.is_clean_start_chapter("第99回 大结局"))
        self.assertFalse(cab.is_clean_start_chapter("Chapter 42 Answer"))

    def test_has_title_tags(self):
        """测试书名残留标签探测。"""
        self.assertTrue(cab.has_title_tags("大奉打更人（正文全）"))
        self.assertTrue(cab.has_title_tags("斗破苍穹【含番外】"))
        self.assertTrue(cab.has_title_tags("诡秘之主 校对版"))
        self.assertTrue(cab.has_title_tags("某小说 全集"))
        self.assertTrue(cab.has_title_tags("未完成的小说（未完）"))
        self.assertFalse(cab.has_title_tags("道诡异仙"))
        self.assertFalse(cab.has_title_tags("赤心巡天"))

    def test_get_default_corpus_db(self):
        """测试 check_all_books 的数据库默认路径探测。"""
        fake_db = self.tmp_path / "default_check.db"
        with mock.patch.dict(os.environ, {"EXOSCRIBE_CORPUS_DB": str(fake_db)}):
            self.assertEqual(cab.get_default_corpus_db(), fake_db.resolve())

    def test_check_corpus_books_full_report(self):
        """测试综合书籍核验报告生成。"""
        db_file = self.tmp_path / "check_corpus.db"
        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("""
                CREATE TABLE essence_books (
                    id INTEGER PRIMARY KEY,
                    book_id TEXT,
                    title TEXT,
                    genre TEXT,
                    total_chapters INTEGER,
                    total_chars INTEGER,
                    source_path TEXT
                )
            """)
            conn.execute("CREATE TABLE essence_assets (id INTEGER PRIMARY KEY, book_id TEXT)")
            conn.execute("CREATE TABLE essence_chains (id INTEGER PRIMARY KEY, book_id TEXT)")

            # 1. 完美书籍
            book1_txt = self.tmp_path / "b1.txt"
            book1_txt.write_text("第一章 开始\n正文内容\n第2章 结束\n结尾", encoding="utf-8")
            conn.execute("INSERT INTO essence_books VALUES (1, 'b1', '好书', '仙侠', 2, 50, ?)", (str(book1_txt),))
            for _ in range(4):
                conn.execute("INSERT INTO essence_assets (book_id) VALUES ('b1')")
            conn.execute("INSERT INTO essence_chains (book_id) VALUES ('b1')")

            # 2. 缺陷书籍（物理缺失、资产卡数量异常、伏笔链异常、重复书名、首章断层、标签未清洗）
            book2_txt = self.tmp_path / "b2.txt"
            book2_txt.write_text("第50章 突兀的开篇\n正文\n第51章 完结\n完", encoding="utf-8")
            conn.execute("INSERT INTO essence_books VALUES (2, 'b2', '好书（正文全）', '玄幻', 2, 50, ?)", (str(book2_txt),))
            # 资产卡只有 2 张，链为 0
            conn.execute("INSERT INTO essence_assets (book_id) VALUES ('b2')")
            conn.execute("INSERT INTO essence_assets (book_id) VALUES ('b2')")

            # 3. 重名书籍
            book3_txt = self.tmp_path / "b3.txt"
            book3_txt.write_text("引子\n正文\n第一章 启程\n正文", encoding="utf-8")
            conn.execute("INSERT INTO essence_books VALUES (3, 'b3', '好书', '仙侠', 2, 50, ?)", (str(book3_txt),))
            for _ in range(4):
                conn.execute("INSERT INTO essence_assets (book_id) VALUES ('b3')")
            conn.execute("INSERT INTO essence_chains (book_id) VALUES ('b3')")

            # 4. 空文件书籍
            empty_txt = self.tmp_path / "empty.txt"
            empty_txt.write_text("", encoding="utf-8")
            conn.execute("INSERT INTO essence_books VALUES (4, 'b4', '空书', '都市', 1, 0, ?)", (str(empty_txt),))

            conn.commit()

            report = cab.check_corpus_books(conn)
            self.assertEqual(report["total_records"], 4)
            # 空书物理文件缺失/为空
            self.assertTrue(any("物理文件缺失或为空" in f for f in report["flaws"]))
            # b2 资产卡异常
            self.assertTrue(any("资产卡数量异常" in f for f in report["flaws"]))
            # b2 伏笔链异常
            self.assertTrue(any("伏笔链数量异常" in f for f in report["flaws"]))
            # 首章断层
            self.assertEqual(len(report["suspicious_starts"]), 1)
            self.assertEqual(report["suspicious_starts"][0]["title"], "好书（正文全）")
            # 重复书名
            self.assertIn("好书", report["duplicate_titles"])
            # 标签未清洗
            self.assertTrue(any(item["title"] == "好书（正文全）" for item in report["flagged_titles"]))
        finally:
            conn.close()

    def test_main_cli(self):
        """测试 check_all_books 的 main 命令行接口。"""
        # 数据库不存在
        code = cab.main(["--db", str(self.tmp_path / "none.db"), "--quiet"])
        self.assertEqual(code, 1)

        # 构造一个含缺陷的库
        db_file = self.tmp_path / "cli_check.db"
        conn = sqlite3.connect(str(db_file))
        conn.execute("""
            CREATE TABLE essence_books (
                id INTEGER PRIMARY KEY,
                book_id TEXT,
                title TEXT,
                genre TEXT,
                total_chapters INTEGER,
                total_chars INTEGER,
                source_path TEXT
            )
        """)
        conn.execute("CREATE TABLE essence_assets (id INTEGER PRIMARY KEY, book_id TEXT)")
        conn.execute("CREATE TABLE essence_chains (id INTEGER PRIMARY KEY, book_id TEXT)")
        conn.execute("INSERT INTO essence_books VALUES (1, 'b1', '缺卡书', '都市', 1, 10, 'dummy.txt')")
        conn.commit()
        conn.close()

        # 普通模式返回 0（即使有缺陷，只做报表输出）
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            code_normal = cab.main(["--db", str(db_file)])
        self.assertEqual(code_normal, 0)
        self.assertIn("深度核验入库小说质量", out.getvalue())

        # strict 模式发现缺陷返回 1
        code_strict = cab.main(["--db", str(db_file), "--strict", "--quiet"])
        self.assertEqual(code_strict, 1)


class TestAncillaryInspectionScripts(unittest.TestCase):
    """测试 check_ad, check_seq, check_dp_titles, check_search, check_shorts 辅助脚本。"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self):
        import gc
        gc.collect()
        self.tmp_dir.cleanup()

    def _create_sample_db(self):
        db_file = self.tmp_path / "sample.db"
        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
        conn.execute("""
            CREATE TABLE essence_books (
                id INTEGER PRIMARY KEY,
                title TEXT,
                source_path TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE essence_assets (
                id INTEGER PRIMARY KEY,
                title TEXT,
                content TEXT
            )
        """)
        return db_file, conn

    def test_check_ad(self):
        """测试 check_ad.py 广告模式定位。"""
        db_file, conn = self._create_sample_db()
        book_txt = self.tmp_path / "ad_book.txt"
        book_txt.write_text("正文内容...请到某某网站首发阅读最新章节！感谢支持。", encoding="utf-8")
        conn.execute("INSERT INTO essence_books VALUES (1, '暴力前锋', ?)", (str(book_txt),))
        conn.commit()

        # 匹配命中
        snippet = cad.check_book_ad(conn, title="暴力前锋")
        self.assertIsNotNone(snippet)
        self.assertIn("首发", snippet)

        # 书名不存在
        self.assertIsNone(cad.check_book_ad(conn, title="不存在的书"))

        # CLI
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            code = cad.main(["--db", str(db_file), "--title", "暴力前锋"])
        self.assertEqual(code, 0)
        self.assertIn("Match in 暴力前锋", out.getvalue())

        conn.close()

    def test_check_seq(self):
        """测试 check_seq.py 行序列切片读取。"""
        db_file, conn = self._create_sample_db()
        book_txt = self.tmp_path / "seq_book.txt"
        book_txt.write_text("\n".join(f"Line {i}" for i in range(100)), encoding="utf-8")
        conn.execute("INSERT INTO essence_books VALUES (1, '奥术神座', ?)", (str(book_txt),))
        conn.commit()

        lines = csq.inspect_book_lines(conn, title="奥术神座", start_line=10, end_line=15)
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0], (10, "Line 10"))

        # 越界与不存在的书
        self.assertEqual(csq.inspect_book_lines(conn, title="无此书"), [])

        # CLI
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            code = csq.main(["--db", str(db_file), "--title", "奥术神座", "--start", "5", "--end", "8"])
        self.assertEqual(code, 0)
        self.assertIn("Line 5", out.getvalue())

        conn.close()

    def test_check_dp_titles(self):
        """测试 check_dp_titles.py 单书章节标题分析。"""
        db_file, conn = self._create_sample_db()
        book_txt = self.tmp_path / "dp_book.txt"
        book_txt.write_text(
            "第一章 陨落的天才\n正文\n"
            "第二章 斗之气，三段！含有标点的异常长标题\n正文\n",
            encoding="utf-8",
        )
        conn.execute("INSERT INTO essence_books VALUES (1, '斗破苍穹', ?)", (str(book_txt),))
        conn.commit()

        total, bad = cdp.inspect_book_titles(conn, title="斗破苍穹")
        self.assertEqual(total, 2)
        self.assertEqual(len(bad), 1)
        self.assertIn("含有标点", bad[0])

        # CLI
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            code = cdp.main(["--db", str(db_file), "--title", "斗破苍穹"])
        self.assertEqual(code, 0)
        self.assertIn("斗破苍穹总章数: 2", out.getvalue())

        conn.close()

    def test_check_search(self):
        """测试 check_search.py 资产库关键词直接检索。"""
        db_file, conn = self._create_sample_db()
        conn.execute("INSERT INTO essence_assets VALUES (1, '主角卡', '萧炎是乌坦城萧家三少爷')")
        conn.execute("INSERT INTO essence_assets VALUES (2, '配角卡', '药老')")
        conn.commit()

        results = csr.search_essence_assets(conn, keyword="萧炎")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], 1)

        # CLI
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            code = csr.main(["--db", str(db_file), "--keyword", "萧炎"])
        self.assertEqual(code, 0)
        self.assertIn("Direct SQL matching 萧炎: 1", out.getvalue())

        conn.close()

    def test_check_shorts(self):
        """测试 check_shorts.py 短章分布提取。"""
        db_file, conn = self._create_sample_db()
        b1_txt = self.tmp_path / "shorts1.txt"
        b1_txt.write_text("第一章 正常\n" + "文字" * 80 + "\n第二章 短章\n短短", encoding="utf-8")
        conn.execute("INSERT INTO essence_books VALUES (1, '孢子物语', ?)", (str(b1_txt),))
        conn.commit()

        data = csh.inspect_book_shorts(conn, titles=["孢子物语"], min_chars=100)
        self.assertIn("孢子物语", data)
        self.assertEqual(data["孢子物语"]["total_chapters"], 2)
        self.assertEqual(len(data["孢子物语"]["short_chapters"]), 1)

        # CLI
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            code = csh.main(["--db", str(db_file), "--titles", "孢子物语", "--min-chars", "100"])
        self.assertEqual(code, 0)
        self.assertIn("=== 孢子物语 ===", out.getvalue())

        conn.close()


if __name__ == "__main__":
    unittest.main()
