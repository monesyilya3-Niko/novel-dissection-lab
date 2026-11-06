#!/usr/bin/env python3
"""100 本小说严选建库与高质量精华重萃取引擎（batch_100_books.py & refresh_essence_quality.py）全维独立测试套件。

涵盖：
1. 书名与作者清洗（clean_title_and_author 爬虫后缀过滤/书名作者分离/纯数字前缀剥离且保护汉字数词/10大题材启发式推断）；
2. 严选把关规则（is_acceptable_webnovel 外国书黑名单/外国国籍标签/60章门槛/30万字门槛/均章1500-4000字门槛/首章规范启动校验）；
3. 文本与标识符工具（sanitize_book_id 确定性哈希标识/format_full_novel_text 章节段落规整化）；
4. 双库原子入库与去重查重（check_book_exists 物理文件校验/ingest_book_atomic 双库原子双写与五维资产/伏笔链沉淀）；
5. 台账同步（sync_full_work_log 从数据库权威生成 WORK_LOG_100_BOOKS.md 表格）；
6. 精华库质量刷新重萃取（refresh_essence_quality.main 遍历更新 meta_json/清空重建 assets 与 chains/调用 work log 同步）。
"""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_TESTS_DIR = Path(__file__).resolve().parent
ROOT = _TESTS_DIR.parent
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(_TESTS_DIR))

import _isolation  # noqa: E402

from gui import config, db  # noqa: E402
from scripts import batch_100_books as b100  # noqa: E402
from scripts import refresh_essence_quality as req  # noqa: E402


class TestBatch100BooksCleanAndSanitize(unittest.TestCase):
    """测试书名、作者与题材清洗及 ID 生成算法。"""

    def test_clean_title_and_author_suffixes(self):
        raw = "《遮天》(正文全)【校对版】(VIP完结)"
        title, author, genre = b100.clean_title_and_author(raw)
        self.assertEqual(title, "《遮天》")
        self.assertEqual(author, "佚名")

    def test_clean_title_and_author_hyphen_split(self):
        raw = "斗破苍穹-天蚕土豆"
        title, author, genre = b100.clean_title_and_author(raw)
        self.assertEqual(title, "斗破苍穹")
        self.assertEqual(author, "天蚕土豆")
        self.assertEqual(genre, "xuanhuan")

    def test_clean_title_and_author_numeric_prefix(self):
        # 纯数字前缀剥离
        t1, _, _ = b100.clean_title_and_author("01. 凡人修仙传")
        self.assertEqual(t1, "凡人修仙传")

        t2, _, _ = b100.clean_title_and_author("003_大明王朝")
        self.assertEqual(t2, "大明王朝")

        # 保护汉字数字不被残害
        t3, _, _ = b100.clean_title_and_author("八荒剑神")
        self.assertEqual(t3, "八荒剑神")

    def test_genre_heuristics(self):
        cases = [
            ("艾泽拉斯旅行指南", "naodong"),
            ("凡人修仙之问道长生", "xianxia"),
            ("大明崇祯中兴录", "lishi"),
            ("星际异能进化", "kehuan"),
            ("诡秘怪谈事件簿", "xuanyi"),
            ("豪门总裁的替嫁甜妻", "yanqing"),
            ("修罗殿狂兵龙王归来", "zhanshen"),
            ("签到十万年的快穿模拟器", "naodong"),
            ("都市绝品神医合租记", "dushi"),
            ("武动乾坤大主宰", "xuanhuan"),
        ]
        for raw, expected_genre in cases:
            _, _, genre = b100.clean_title_and_author(raw)
            self.assertEqual(genre, expected_genre, f"Title {raw} expected {expected_genre}, got {genre}")

    def test_sanitize_book_id(self):
        book_id = b100.sanitize_book_id("《凡人修仙传》")
        self.assertTrue(book_id.startswith("book_"))
        self.assertIn("凡人修仙传", book_id)
        # 相同标题产生相同 ID
        self.assertEqual(book_id, b100.sanitize_book_id("《凡人修仙传》"))

    def test_format_full_novel_text(self):
        chapters = [
            {"chapter": "第1章 山村风云", "text": "少年缓缓抬头。"},
            {"chapter": "初入宗门", "text": "仙门巍峨耸立。"},
            {"chapter": "", "text": "剑光划破长空。"},
        ]
        formatted = b100.format_full_novel_text(chapters)
        self.assertIn("第1章 山村风云\n\n少年缓缓抬头。", formatted)
        self.assertIn("第2章 初入宗门\n\n仙门巍峨耸立。", formatted)
        self.assertIn("第3章\n\n剑光划破长空。", formatted)


class TestIsAcceptableWebnovel(unittest.TestCase):
    """测试严选把关规则。"""

    def test_foreign_blacklist_rejected(self):
        self.assertFalse(b100.is_acceptable_webnovel("百年孤独", "百年孤独", 100, 300000, "第1章"))
        self.assertFalse(b100.is_acceptable_webnovel("基督山伯爵", "基督山伯爵", 120, 500000, "第1章"))

    def test_foreign_nationality_rejected(self):
        self.assertFalse(b100.is_acceptable_webnovel("(美)冰与火之歌", "冰与火之歌", 80, 400000, "第1章"))
        self.assertFalse(b100.is_acceptable_webnovel("世界名著选集", "名著选集", 90, 400000, "第1章"))

    def test_length_and_chapter_thresholds(self):
        """门槛必须与 CORE_PHILOSOPHY.md 逐字对齐（2026-11-05）。

        原实现是 250,000 字 / 均章 ≥1,000 字且**无上限**，与宪法
        （≥300,000 字、≥60 章、均章 1,500~4,000 字）不一致——门槛放宽会让
        25 万字的书混进「传世神作」库，均章 1,000 字则放进大量注水短章书。
        """
        # 章节少于 60 章
        self.assertFalse(b100.is_acceptable_webnovel("玄幻", "玄幻", 59, 400000, "第1章"))
        # 总字数少于 300,000 字
        self.assertFalse(b100.is_acceptable_webnovel("玄幻", "玄幻", 100, 299999, "第1章"))
        # 均章低于 1,500 字（300 章 / 30 万字 = 1,000）
        self.assertFalse(b100.is_acceptable_webnovel("玄幻", "玄幻", 300, 300000, "第1章"))
        # 均章高于 4,000 字（60 章 / 40 万字 ≈ 6,667）
        self.assertFalse(b100.is_acceptable_webnovel("玄幻", "玄幻", 60, 400000, "第1章"))
        # 标准长篇应通过（100 章 / 35 万字 = 均章 3,500）
        self.assertTrue(b100.is_acceptable_webnovel("玄幻", "玄幻", 100, 350000, "第1章"))

    def test_first_chapter_clean_start(self):
        # 合法开头
        self.assertTrue(b100.is_acceptable_webnovel("长篇神作", "长篇神作", 100, 350000, "第1章 惊变"))
        self.assertTrue(b100.is_acceptable_webnovel("长篇神作", "长篇神作", 100, 350000, "序章 沧海桑田"))
        self.assertTrue(b100.is_acceptable_webnovel("长篇神作", "长篇神作", 100, 350000, "楔子 诸神之战"))
        self.assertTrue(b100.is_acceptable_webnovel("长篇神作", "长篇神作", 100, 350000, "Chapter 1 Begin"))

        # 断头断章开头拒绝
        self.assertFalse(b100.is_acceptable_webnovel("断头书", "断头书", 100, 350000, "第18章 中途再遇"))
        self.assertFalse(b100.is_acceptable_webnovel("断头书", "断头书", 100, 350000, "无标题开头"))


class TestBatch100BooksDatabaseOperations(unittest.TestCase):
    """测试原子双写入库、查重、台账同步与精华重萃取。"""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="b100_test_"))
        self._iso = _isolation.isolate_paths(self._tmp)
        self._iso.__enter__()
        config.DB_PATH = db.db_path()
        self._orig_work_log = b100.WORK_LOG_FILE
        self._dummy_log = self._tmp / "WORK_LOG_TEST.md"
        b100.WORK_LOG_FILE = self._dummy_log
        db.init_schema()
        db.apply_migrations()
        self.conn = b100.init_db_connection()

    def tearDown(self):
        b100.WORK_LOG_FILE = self._orig_work_log
        self.conn.close()
        db.close()
        self._iso.__exit__(None, None, None)

    def _sample_chapters(self, count: int = 65, words_per_ch: int = 1500) -> list[dict[str, str]]:
        chapters = []
        for i in range(1, count + 1):
            chapters.append({
                "chapter": f"第{i}章 历练之路{i}",
                "text": f"这是第{i}章正文。" + ("少年执剑，斩破云霄。" * (words_per_ch // 10)),
            })
        return chapters

    def test_check_book_exists(self):
        book_id = "book_test_123"
        title = "仙道长青"
        self.assertFalse(b100.check_book_exists(self.conn, book_id, title))

        # 写入数据库但磁盘无文件仍为 False
        self.conn.execute("INSERT INTO books (book_id, title, source_path) VALUES (?, ?, ?)",
                          (book_id, title, str(config.CORPUS_DIR / "no_file.txt")))
        self.conn.execute("INSERT INTO essence_books (book_id, title, source_path) VALUES (?, ?, ?)",
                          (book_id, title, str(config.CORPUS_DIR / "no_file.txt")))
        self.assertFalse(b100.check_book_exists(self.conn, book_id, title))

        # 写入物理文件后为 True
        config.CORPUS_DIR.mkdir(parents=True, exist_ok=True)
        txt_path = config.CORPUS_DIR / "test_book.txt"
        txt_path.write_text("正文内容" * 300, encoding="utf-8")  # > 1000 字节
        self.conn.execute("UPDATE books SET source_path = ? WHERE book_id = ?", (str(txt_path), book_id))
        self.conn.execute("UPDATE essence_books SET source_path = ? WHERE book_id = ?", (str(txt_path), book_id))
        self.assertTrue(b100.check_book_exists(self.conn, book_id, title))

    def test_ingest_book_atomic(self):
        chapters = self._sample_chapters(65, 1200)
        book_id = "book_wandao_01"
        title = "万道争锋"
        author = "辰东风"
        genre = "xuanhuan"
        platform = "起点"

        res = b100.ingest_book_atomic(
            conn=self.conn,
            book_id=book_id,
            title=title,
            author=author,
            genre=genre,
            platform=platform,
            chapters=chapters,
        )

        self.assertEqual(res["book_id"], book_id)
        self.assertEqual(res["title"], title)
        self.assertEqual(res["chapters"], 65)
        self.assertGreater(res["chars"], 60000)
        self.assertGreaterEqual(res["assets_count"], 1)

        # 验证 books 表
        b_row = self.conn.execute("SELECT * FROM books WHERE book_id = ?", (book_id,)).fetchone()
        self.assertIsNotNone(b_row)
        self.assertEqual(b_row["title"], title)
        self.assertEqual(b_row["status"], "ready")

        # 验证 essence_books 表
        eb_row = self.conn.execute("SELECT * FROM essence_books WHERE book_id = ?", (book_id,)).fetchone()
        self.assertIsNotNone(eb_row)
        self.assertEqual(eb_row["total_chapters"], 65)

        # 验证 essence_assets 表
        assets = self.conn.execute("SELECT * FROM essence_assets WHERE book_id = ?", (book_id,)).fetchall()
        self.assertGreaterEqual(len(assets), 1)

        # 验证 essence_chains 表
        chains = self.conn.execute("SELECT * FROM essence_chains WHERE book_id = ?", (book_id,)).fetchall()
        self.assertEqual(len(chains), 1)
        self.assertEqual(chains[0]["status"], "resolved")

    def test_sync_full_work_log(self):
        # 先入库一本书
        chapters = self._sample_chapters(60, 1000)
        b100.ingest_book_atomic(
            conn=self.conn,
            book_id="book_xuan_01",
            title="仙道大帝",
            author="耳根清",
            genre="xianxia",
            platform="起点",
            chapters=chapters,
        )

        # 同步工作台账
        dummy_log = self._tmp / "WORK_LOG_TEST.md"
        with patch.object(b100, "WORK_LOG_FILE", dummy_log):
            b100.sync_full_work_log(self.conn)

        self.assertTrue(dummy_log.exists())
        content = dummy_log.read_text(encoding="utf-8")
        self.assertIn("# 100 本小说建库与小说精华库工程总台账", content)
        self.assertIn("仙道大帝", content)
        self.assertIn("仙侠古典", content)

    def test_refresh_essence_quality_main(self):
        # 入库一本书
        chapters = self._sample_chapters(60, 1000)
        b100.ingest_book_atomic(
            conn=self.conn,
            book_id="book_refresh_01",
            title="暴力前锋",
            author="林海听涛",
            genre="dushi",
            platform="起点",
            chapters=chapters,
        )

        dummy_log = self._tmp / "WORK_LOG_TEST_REFRESH.md"
        with patch.object(b100, "WORK_LOG_FILE", dummy_log):
            f = io.StringIO()
            with patch("sys.stdout", f):
                ret = req.main([])

            self.assertEqual(ret, 0)
            output = f.getvalue()
            self.assertIn("全量 100 本小说精华库高质量刷新完毕", output)

            # 验证资产和伏笔链依然饱满
            assets = self.conn.execute("SELECT count(*) FROM essence_assets WHERE book_id = 'book_refresh_01'").fetchone()[0]
            self.assertGreaterEqual(assets, 1)

            chains = self.conn.execute("SELECT count(*) FROM essence_chains WHERE book_id = 'book_refresh_01'").fetchone()[0]
            self.assertEqual(chains, 1)

    def test_batch_100_books_main_test_one(self):
        dummy_log = self._tmp / "WORK_LOG_TEST_BATCH.md"
        with patch.object(b100, "WORK_LOG_FILE", dummy_log), \
             patch.object(b100, "init_db_connection", return_value=self.conn), \
             patch.object(b100, "check_book_exists", return_value=True):
            f = io.StringIO()
            with patch("sys.stdout", f):
                ret = b100.main(["--dry-run", "--test-one"])
            self.assertEqual(ret, 0)
            self.assertIn("单本测试模式结束", f.getvalue())


if __name__ == "__main__":
    unittest.main()
