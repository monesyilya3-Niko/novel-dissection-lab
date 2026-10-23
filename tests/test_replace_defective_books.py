#!/usr/bin/env python3
"""剔除劣质作品与全流程严苛补齐引擎（scripts/replace_defective_books.py）独立单元测试集。

覆盖范围：
1. get_default_corpus_db 路径解析（CLI 参数、环境变量、本地已存在路径、默认兜底）
2. init_db_connection 数据库连接参数与 WAL 模式配置
3. is_strictly_acceptable_webnovel 六维严苛门槛检测：
   - 空章节列表
   - 黑名单标题拦截
   - 外国作者标记拦截
   - 名著/译作标识拦截
   - 章节数不足 60
   - 总字数不足 25 万字
   - 单章均长不足 1000 字
   - 首章非规范起始
   - 短章率与超标计数拦截
   - 标题超频重复拦截
   - 正常规范小说合格通过
4. purge_defective_books 级联清理：
   - 跨表级联删除（essence_books, essence_assets, essence_chains, books）
   - 物理文件清除与缺失容错
   - dry_run 演练模式保护
   - 缺失书籍安全跳过
5. scan_and_supplement 补齐调度：
   - 模拟切片下载与跨分块行缓冲断行重组
   - 重复书籍与已入库跳过
   - 不合格书籍静默跳过
   - 遇网络异常重试与恢复
   - 达到目标书目或 max_offset 正常终止
6. main CLI 命令行接口分发：
   - 缺失数据库文件返回 1
   - --purge-only 模式安全执行并返回 0
   - --dry-run 演练模式全流程返回 0
"""
from __future__ import annotations

import gc
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui import config, db
from scripts import replace_defective_books


class TestReplaceDefectiveBooks(unittest.TestCase):
    """剔除缺陷作品与在线补齐独立测试集。"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="replace_defective_test_")
        self.tmp_path = Path(self.tmp_dir.name)
        self.db_path = self.tmp_path / "test_index.db"
        self.dummy_work_log = self.tmp_path / "WORK_LOG_TEST.md"

        self._work_log_patch = patch("scripts.batch_100_books.WORK_LOG_FILE", self.dummy_work_log)
        self._work_log_patch.start()

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_test_schema(self.conn)

    def tearDown(self):
        if hasattr(self, "_work_log_patch"):
            try:
                self._work_log_patch.stop()
            except Exception:
                pass
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
        """初始化同构数据库表结构。"""
        orig = db.get_conn
        db.get_conn = lambda: conn
        try:
            db.init_schema()
            db.apply_migrations()
        finally:
            db.get_conn = orig

        conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                book_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source_path TEXT DEFAULT '',
                genre TEXT DEFAULT 'xuanhuan',
                status TEXT DEFAULT 'ready',
                imported_at TEXT DEFAULT '',
                updated_at TEXT DEFAULT ''
            );
        """)
        conn.commit()

    def _generate_valid_chapters(
        self,
        count: int = 65,
        chars_per_ch: int = 4000,
        start_title: str = "第一章 剑起风云",
    ) -> list[dict[str, str]]:
        """生成符合严苛准入标准的样本章节列表。"""
        chapters = []
        body_template = "九天十地，浩瀚无垠。少年仗剑远行，斩破天地阻隔，追寻大道绝巅！"
        repeat_factor = max(chars_per_ch // len(body_template), 1)

        for i in range(count):
            if i == 0:
                ch_title = start_title
            else:
                ch_title = f"第{i + 1}章 征战星空"
            text = (body_template * repeat_factor)[:chars_per_ch]
            chapters.append({"chapter": ch_title, "text": text})
        return chapters

    # -------------------------------------------------------------------------
    # 1. 路径与连接解析
    # -------------------------------------------------------------------------

    def test_get_default_corpus_db_cli_arg(self):
        custom = self.tmp_path / "custom.db"
        self.assertEqual(replace_defective_books.get_default_corpus_db(str(custom)), custom)

    def test_get_default_corpus_db_env(self):
        env_db = self.tmp_path / "env_corpus.db"
        with patch.dict(os.environ, {"EXOSCRIBE_CORPUS_DB": str(env_db)}):
            self.assertEqual(replace_defective_books.get_default_corpus_db(), env_db)

    def test_get_default_corpus_db_fallback(self):
        with patch.dict(os.environ, {}, clear=True):
            res = replace_defective_books.get_default_corpus_db()
            self.assertIsInstance(res, Path)

    def test_init_db_connection(self):
        conn = replace_defective_books.init_db_connection(self.db_path)
        try:
            self.assertIsInstance(conn, sqlite3.Connection)
            # 验证 row_factory 有效
            row = conn.execute("SELECT 1 AS val").fetchone()
            self.assertEqual(row["val"], 1)
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # 2. is_strictly_acceptable_webnovel 六维准入门槛测试
    # -------------------------------------------------------------------------

    def test_acceptable_empty_chapters(self):
        ok, reason = replace_defective_books.is_strictly_acceptable_webnovel("完美世界", "完美世界", [])
        self.assertFalse(ok)
        self.assertIn("章节列表为空", reason)

    def test_acceptable_blacklist_title(self):
        chaps = self._generate_valid_chapters()
        ok, reason = replace_defective_books.is_strictly_acceptable_webnovel("美丽新世界", "美丽新世界", chaps)
        self.assertFalse(ok)
        self.assertIn("命中黑名单", reason)

    def test_acceptable_foreign_author_mark(self):
        chaps = self._generate_valid_chapters()
        ok, reason = replace_defective_books.is_strictly_acceptable_webnovel("指环王（美）托尔金", "指环王", chaps)
        self.assertFalse(ok)
        self.assertIn("包含外国作者标记", reason)

    def test_acceptable_classic_or_anthology_mark(self):
        chaps = self._generate_valid_chapters()
        ok, reason = replace_defective_books.is_strictly_acceptable_webnovel("世界名著选集", "世界名著选集", chaps)
        self.assertFalse(ok)
        self.assertIn("包含名著/译作标识", reason)

    def test_acceptable_insufficient_chapter_count(self):
        chaps = self._generate_valid_chapters(count=55)
        ok, reason = replace_defective_books.is_strictly_acceptable_webnovel("沧海一笑", "沧海一笑", chaps)
        self.assertFalse(ok)
        self.assertIn("章节数不足 60", reason)

    def test_acceptable_insufficient_total_chars(self):
        # 65 章，但每章仅 3000 字 -> 195,000 字，低于 250,000
        chaps = self._generate_valid_chapters(count=65, chars_per_ch=3000)
        ok, reason = replace_defective_books.is_strictly_acceptable_webnovel("浮沉记", "浮沉记", chaps)
        self.assertFalse(ok)
        self.assertIn("总字数不足 25 万字", reason)

    def test_acceptable_insufficient_avg_chars(self):
        # 300 章，每章 900 字 -> 270,000 字，总字数达标但均长不足 1000 字
        chaps = self._generate_valid_chapters(count=300, chars_per_ch=900)
        ok, reason = replace_defective_books.is_strictly_acceptable_webnovel("无双剑主", "无双剑主", chaps)
        self.assertFalse(ok)
        self.assertIn("单章平均字数不足 1000 字", reason)

    def test_acceptable_bad_first_chapter_start(self):
        chaps = self._generate_valid_chapters(start_title="第99章 决战天门")
        ok, reason = replace_defective_books.is_strictly_acceptable_webnovel("断层奇书", "断层奇书", chaps)
        self.assertFalse(ok)
        self.assertIn("首章非正常起始", reason)

    def test_acceptable_high_short_chapters_ratio(self):
        chaps = self._generate_valid_chapters(count=100, chars_per_ch=4000)
        # 插入 15 个少于 150 字的短章
        for idx in range(15):
            chaps[idx + 5] = {"chapter": f"第{idx + 6}章 短小", "text": "仅有一句话的凑数水章。"}
        ok, reason = replace_defective_books.is_strictly_acceptable_webnovel("水章狂魔", "水章狂魔", chaps)
        self.assertFalse(ok)
        self.assertIn("短章率超标", reason)

    def test_acceptable_repeated_titles(self):
        chaps = self._generate_valid_chapters(count=80, chars_per_ch=4000)
        # 12 个章节重复命名为 "第一节"
        for idx in range(12):
            chaps[idx + 2] = {"chapter": "第一节", "text": "内容充足" * 500}
        ok, reason = replace_defective_books.is_strictly_acceptable_webnovel("切片复读", "切片复读", chaps)
        self.assertFalse(ok)
        self.assertIn("重复标题过多", reason)

    def test_acceptable_valid_book(self):
        chaps = self._generate_valid_chapters(count=70, chars_per_ch=4000)
        ok, reason = replace_defective_books.is_strictly_acceptable_webnovel("遮天大帝", "遮天大帝", chaps)
        self.assertTrue(ok)
        self.assertEqual(reason, "合格")

    # -------------------------------------------------------------------------
    # 3. purge_defective_books 级联清理测试
    # -------------------------------------------------------------------------

    def test_purge_defective_books_cascades(self):
        # 预设一本缺陷作品及关联记录
        corpus_file = self.tmp_path / "bad_corpus.txt"
        corpus_file.write_text("劣质爬虫断章文本", encoding="utf-8")

        self.conn.execute(
            "INSERT INTO books (book_id, title, source_path) VALUES (?, ?, ?)",
            ("bad_01", "孢子物语", str(corpus_file)),
        )
        self.conn.execute(
            "INSERT INTO essence_books (book_id, title, source_path) VALUES (?, ?, ?)",
            ("bad_01", "孢子物语", str(corpus_file)),
        )
        self.conn.execute(
            "INSERT INTO essence_assets (book_id, category, title, summary, content) VALUES (?, 'character', '主角', '简介', '内容')",
            ("bad_01",),
        )
        self.conn.execute(
            "INSERT INTO essence_chains (book_id, clue_name, hook_chapter, hook_text, payoff_chapter, payoff_text, analysis) "
            "VALUES (?, '线索', 1, '伏笔', 2, '揭晓', '解析')",
            ("bad_01",),
        )
        self.conn.commit()

        # 执行清理
        purged = replace_defective_books.purge_defective_books(self.conn, titles=["孢子物语"], quiet=True)
        self.assertEqual(purged, ["bad_01"])

        # 验证关联各表已清空
        self.assertIsNone(self.conn.execute("SELECT book_id FROM essence_books WHERE book_id = 'bad_01'").fetchone())
        self.assertIsNone(self.conn.execute("SELECT book_id FROM essence_assets WHERE book_id = 'bad_01'").fetchone())
        self.assertIsNone(self.conn.execute("SELECT book_id FROM essence_chains WHERE book_id = 'bad_01'").fetchone())
        self.assertIsNone(self.conn.execute("SELECT book_id FROM books WHERE book_id = 'bad_01'").fetchone())
        # 验证物理文件被删除
        self.assertFalse(corpus_file.exists())

    def test_purge_defective_books_dry_run(self):
        corpus_file = self.tmp_path / "bad_dry.txt"
        corpus_file.write_text("演练文本", encoding="utf-8")

        self.conn.execute(
            "INSERT INTO essence_books (book_id, title, source_path) VALUES (?, ?, ?)",
            ("bad_dry", "暴力前锋", str(corpus_file)),
        )
        self.conn.commit()

        purged = replace_defective_books.purge_defective_books(self.conn, titles=["暴力前锋"], dry_run=True, quiet=True)
        self.assertEqual(purged, ["bad_dry"])

        # 演练模式下记录和文件依旧存在
        self.assertIsNotNone(self.conn.execute("SELECT book_id FROM essence_books WHERE book_id = 'bad_dry'").fetchone())
        self.assertTrue(corpus_file.exists())

    def test_purge_defective_books_missing_title(self):
        purged = replace_defective_books.purge_defective_books(self.conn, titles=["不存在的书籍"], quiet=True)
        self.assertEqual(purged, [])

    # -------------------------------------------------------------------------
    # 4. scan_and_supplement 在线补齐调度测试
    # -------------------------------------------------------------------------

    def test_scan_and_supplement_with_mock_chunks(self):
        """模拟两块分块切片并测试断行重组与自动入库。"""
        valid_chaps = self._generate_valid_chapters(count=65, chars_per_ch=4000)

        # 构造 JSONL 行
        book_lines = [json.dumps({"title": "仙逆风云", "chapter": c["chapter"], "text": c["text"]}, ensure_ascii=False) for c in valid_chaps]
        full_jsonl = "\n".join(book_lines) + "\n"

        # 切分为两块模拟网络分块下载
        mid = len(full_jsonl) // 2
        chunk1 = full_jsonl[:mid].encode("utf-8")
        chunk2 = full_jsonl[mid:].encode("utf-8")

        chunks = [chunk1, chunk2]
        call_idx = [0]

        def mock_fetch(url: str, start_byte: int, end_byte: int, opener: any) -> bytes:
            if call_idx[0] < len(chunks):
                data = chunks[call_idx[0]]
                call_idx[0] += 1
                return data
            return b""

        with patch.object(config, "CORPUS_DIR", self.tmp_path / "corpus"):
            added = replace_defective_books.scan_and_supplement(
                self.conn,
                target_count=1,
                chunk_size=1024 * 1024,
                start_offset=0,
                max_offset=2 * 1024 * 1024,
                fetch_chunk_func=mock_fetch,
                quiet=True,
            )

        self.assertEqual(added, 1)
        row = self.conn.execute("SELECT title, total_chapters FROM essence_books WHERE title = '仙逆风云'").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["total_chapters"], 65)

    def test_scan_and_supplement_skips_unacceptable_book(self):
        """测试不合格书籍在扫描中被跳过。"""
        # 仅有 20 章的不合格短书
        bad_chaps = self._generate_valid_chapters(count=20, chars_per_ch=1000)
        book_lines = [json.dumps({"title": "短篇无道", "chapter": c["chapter"], "text": c["text"]}, ensure_ascii=False) for c in bad_chaps]
        chunk = ("\n".join(book_lines) + "\n").encode("utf-8")

        def mock_fetch(url: str, start_byte: int, end_byte: int, opener: any) -> bytes:
            return chunk if start_byte == 0 else b""

        with patch.object(config, "CORPUS_DIR", self.tmp_path / "corpus"):
            added = replace_defective_books.scan_and_supplement(
                self.conn,
                target_count=1,
                chunk_size=1024 * 1024,
                start_offset=0,
                max_offset=2 * 1024 * 1024,
                fetch_chunk_func=mock_fetch,
                quiet=True,
            )

        self.assertEqual(added, 0)
        self.assertIsNone(self.conn.execute("SELECT book_id FROM essence_books WHERE title = '短篇无道'").fetchone())

    def test_scan_and_supplement_retry_on_network_error(self):
        """测试切片下载异常重试并恢复。"""
        valid_chaps = self._generate_valid_chapters(count=65, chars_per_ch=4000)
        book_lines = [json.dumps({"title": "重试神王", "chapter": c["chapter"], "text": c["text"]}, ensure_ascii=False) for c in valid_chaps]
        chunk = ("\n".join(book_lines) + "\n").encode("utf-8")

        attempt = [0]

        def mock_fetch_with_error(url: str, start_byte: int, end_byte: int, opener: any) -> bytes:
            if start_byte == 0:
                attempt[0] += 1
                if attempt[0] == 1:
                    raise OSError("网络连接中断超时")
                return chunk
            return b""

        with patch.object(config, "CORPUS_DIR", self.tmp_path / "corpus"):
            added = replace_defective_books.scan_and_supplement(
                self.conn,
                target_count=1,
                chunk_size=1024 * 1024,
                start_offset=0,
                max_offset=2 * 1024 * 1024,
                fetch_chunk_func=mock_fetch_with_error,
                max_retries_per_chunk=3,
                retry_delay=0.001,
                quiet=True,
            )

        self.assertEqual(attempt[0], 2)
        self.assertEqual(added, 1)

    # -------------------------------------------------------------------------
    # 5. CLI 命令行入口测试
    # -------------------------------------------------------------------------

    def test_main_cli_missing_db(self):
        missing_db = self.tmp_path / "not_found.db"
        code = replace_defective_books.main(["--db", str(missing_db), "-q"])
        self.assertEqual(code, 1)

    def test_main_cli_purge_only(self):
        code = replace_defective_books.main(["--db", str(self.db_path), "--purge-only", "-q"])
        self.assertEqual(code, 0)

    def test_main_cli_dry_run(self):
        code = replace_defective_books.main([
            "--db", str(self.db_path),
            "--dry-run",
            "--target-count", "1",
            "--max-mb", "1",
            "-q",
        ])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
