#!/usr/bin/env python3
"""全量小说深度六维审计引擎（scripts/deep_audit_100_books.py）单元测试。

覆盖范围：
1. get_default_corpus_db 环境变量与兜底策略
2. 维度一：数据库记录与引用完整性（表计数、孤儿记录、资产卡与伏笔链配比）
3. 维度二：正文实质内容与汉字纯度（缺失文件、低纯度乱码、短章率、广告文本）
4. 维度三：章节首末完整性与连续性（首章合规起点匹配、跳章断层）
5. 维度四：精华资产卡与暗线深度（内容长度阈值、空白占位拦截、分类覆盖）
6. 维度五：题材真实性与外国译著拦截（黑名单命中、国籍符号、题材矩阵）
7. 维度六：服务层真实端到端读取兼容性（essence_service 实测集成、连接重定向）
8. CLI main 入口与退出状态码（参数解析、--db / -q / --expected-books、全量通过/失败裁决）
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
from scripts import deep_audit_100_books


class TestDeepAudit100Books(unittest.TestCase):
    """深度六维审计引擎独立单元测试集。"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="deep_audit_test_")
        self.tmp_path = Path(self.tmp_dir.name)
        self.db_path = self.tmp_path / "test_corpus.db"

        # 构建基础 schema
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
        """初始化测试所需的最小全集 schema。"""
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS books (
                book_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                genre TEXT DEFAULT 'xuanhuan',
                created_at TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS essence_books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                source_path TEXT DEFAULT '',
                genre TEXT DEFAULT 'xuanhuan',
                platform TEXT DEFAULT 'qidian',
                total_chapters INTEGER DEFAULT 0,
                total_chars INTEGER DEFAULT 0,
                analyzed_chapters INTEGER DEFAULT 0,
                status TEXT DEFAULT 'ready',
                meta_json TEXT DEFAULT '{}',
                created_at TEXT DEFAULT '',
                updated_at TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS essence_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                content TEXT NOT NULL,
                rating REAL DEFAULT 5.0,
                source_chapter TEXT DEFAULT '',
                tags_json TEXT DEFAULT '[]',
                user_notes TEXT DEFAULT '',
                created_at TEXT DEFAULT '',
                updated_at TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS essence_chains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT NOT NULL,
                clue_name TEXT NOT NULL,
                hook_chapter TEXT NOT NULL,
                hook_text TEXT NOT NULL,
                payoff_chapter TEXT NOT NULL,
                payoff_text TEXT NOT NULL,
                analysis TEXT NOT NULL,
                rating REAL DEFAULT 5.0,
                created_at TEXT DEFAULT ''
            );
        """)
        conn.commit()

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
                "第一章 宗门风云\n"
                "天地不仁，以万物为刍狗。少年林晨站在悬崖边缘，目光坚定如铁。"
                "修仙之路，本就是逆天而行，纵使粉身碎骨，亦绝不后退半步！\n" * 5 + "\n"
                "第二章 绝处逢生\n"
                "悬崖之下，灵气汇聚成海。林晨在古洞深处偶得太古传承，体内的古老血脉轰然觉醒！\n" * 5
            )
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def _insert_valid_book_data(
        self,
        book_id: str = "book_001",
        title: str = "九霄武皇",
        source_path: str = "",
        genre: str = "xuanhuan",
    ) -> None:
        """插入一条完全合规的书籍、4张资产卡及1条伏笔链。"""
        self.conn.execute(
            "INSERT INTO books (book_id, title, genre) VALUES (?, ?, ?)",
            (book_id, title, genre),
        )
        self.conn.execute(
            """INSERT INTO essence_books
               (book_id, title, source_path, genre, platform, total_chapters, total_chars)
               VALUES (?, ?, ?, ?, 'qidian', 10, 20000)""",
            (book_id, title, source_path, genre),
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
               VALUES (?, '古戒秘钥', '第1章', '父亲临终前留下的青铜古戒隐隐发光。', '第50章', '古戒开启神庙大门，揭开身世谜团。', '典型悬念伏笔长线回收。')""",
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
            resolved = deep_audit_100_books.get_default_corpus_db()
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
            resolved = deep_audit_100_books.get_default_corpus_db()
            self.assertTrue(isinstance(resolved, Path))
            self.assertTrue(str(resolved).endswith("index.db"))
        finally:
            if old_env is not None:
                os.environ["EXOSCRIBE_CORPUS_DB"] = old_env

    # -------------------------------------------------------------------------
    # 维度一：数据库外键与记录级完整性
    # -------------------------------------------------------------------------

    def test_audit_dimension_1_pass(self):
        """测试维度一在规范结构下通过。"""
        self._insert_valid_book_data("b1", "苍穹之主")
        self._insert_valid_book_data("b2", "剑破九天")

        # 期望 2 本
        passed = deep_audit_100_books.audit_dimension_1_database_integrity(
            self.conn, expected_books=2, quiet=True
        )
        self.assertTrue(passed)

        # 自适应数量 (expected_books=None)
        passed_auto = deep_audit_100_books.audit_dimension_1_database_integrity(
            self.conn, expected_books=None, quiet=True
        )
        self.assertTrue(passed_auto)

    def test_audit_dimension_1_fail_book_count_mismatch(self):
        """测试维度一书目数量不匹配时失败。"""
        self._insert_valid_book_data("b1", "苍穹之主")
        passed = deep_audit_100_books.audit_dimension_1_database_integrity(
            self.conn, expected_books=100, quiet=True
        )
        self.assertFalse(passed)

    def test_audit_dimension_1_fail_orphans_and_abnormal_cards(self):
        """测试维度一检测孤儿记录和不匹配的资产卡数。"""
        self._insert_valid_book_data("b1", "苍穹之主")
        # 插入孤儿 essence_books
        self.conn.execute(
            "INSERT INTO essence_books (book_id, title) VALUES ('orphan_b', '孤儿书')"
        )
        # 为孤儿插入多余卡
        self.conn.execute(
            "INSERT INTO essence_assets (book_id, category, title, summary, content) VALUES ('orphan_b', 'opening', 't', 's', 'c')"
        )
        self.conn.commit()

        passed = deep_audit_100_books.audit_dimension_1_database_integrity(
            self.conn, expected_books=None, quiet=True
        )
        self.assertFalse(passed)

    # -------------------------------------------------------------------------
    # 维度二：正文实质内容与汉字纯度
    # -------------------------------------------------------------------------

    def test_audit_dimension_2_pass(self):
        """测试维度二在饱满正文下通过。"""
        p = self._create_sample_novel_file("novel_good.txt")
        self._insert_valid_book_data("b1", "九霄武皇", str(p))

        passed = deep_audit_100_books.audit_dimension_2_text_substance(
            self.conn, quiet=True
        )
        self.assertTrue(passed)

    def test_audit_dimension_2_fail_empty_file(self):
        """测试维度二在空文件/不存在文件时报错。"""
        empty_p = self.tmp_path / "empty.txt"
        empty_p.write_text("", encoding="utf-8")
        self._insert_valid_book_data("b1", "空书", str(empty_p))

        passed = deep_audit_100_books.audit_dimension_2_text_substance(
            self.conn, quiet=True
        )
        self.assertFalse(passed)

    def test_audit_dimension_2_fail_low_chinese_purity(self):
        """测试维度二在汉字纯度过低（英文或乱码堆砌）时拦截。"""
        p = self._create_sample_novel_file(
            "garbled.txt",
            content="Chapter 1 The Beginning of Time\n" + "abcdefg 1234567890\n" * 50,
        )
        self._insert_valid_book_data("b1", "乱码书", str(p))

        passed = deep_audit_100_books.audit_dimension_2_text_substance(
            self.conn, quiet=True
        )
        self.assertFalse(passed)

    def test_audit_dimension_2_empty_table(self):
        """测试维度二在空表时返回 False。"""
        passed = deep_audit_100_books.audit_dimension_2_text_substance(
            self.conn, quiet=True
        )
        self.assertFalse(passed)

    # -------------------------------------------------------------------------
    # 维度三：章节首末完整性与连续性
    # -------------------------------------------------------------------------

    def test_audit_dimension_3_pass(self):
        """测试维度三首章合规匹配（第一章、第01章、序章、Chapter 1）。"""
        for i, header in enumerate(["第一章 崛起", "第01章 初始", "序 九州", "Chapter 1 Begin"]):
            p = self._create_sample_novel_file(f"novel_{i}.txt", f"{header}\n天道茫茫。")
            self._insert_valid_book_data(f"b_{i}", f"书目_{i}", str(p))

        passed = deep_audit_100_books.audit_dimension_3_chapter_continuity(
            self.conn, quiet=True
        )
        self.assertTrue(passed)

    def test_audit_dimension_3_fail_broken_start(self):
        """测试维度三首章非规范起步（例如从第50章起）被精准拦截。"""
        p = self._create_sample_novel_file("broken.txt", "第50章 突遭变故\n正文开始。")
        self._insert_valid_book_data("b_broken", "断头小说", str(p))

        passed = deep_audit_100_books.audit_dimension_3_chapter_continuity(
            self.conn, quiet=True
        )
        self.assertFalse(passed)

    def test_audit_dimension_3_fail_no_headers_or_missing_file(self):
        """测试维度三无章节标题或文件缺失。"""
        p = self._create_sample_novel_file("no_headers.txt", "这是没有章节标题的正文。\n没有任何标记。")
        self._insert_valid_book_data("b1", "无章节书", str(p))
        self._insert_valid_book_data("b2", "丢失文件书", str(self.tmp_path / "not_found.txt"))

        passed = deep_audit_100_books.audit_dimension_3_chapter_continuity(
            self.conn, quiet=True
        )
        self.assertFalse(passed)

    # -------------------------------------------------------------------------
    # 维度四：精华资产卡与暗线萃取质量
    # -------------------------------------------------------------------------

    def test_audit_dimension_4_pass(self):
        """测试维度四资产卡内容充分、伏笔暗链健全时通过。"""
        self._insert_valid_book_data("b1", "神魔争霸")
        passed = deep_audit_100_books.audit_dimension_4_essence_depth(
            self.conn, quiet=True
        )
        self.assertTrue(passed)

    def test_audit_dimension_4_fail_empty_or_short(self):
        """测试维度四当资产卡或伏笔链内容过短或为空时拦截。"""
        self._insert_valid_book_data("b1", "空白小说")
        # 破坏资产卡内容
        self.conn.execute("UPDATE essence_assets SET content = '太短' WHERE category = 'opening'")
        self.conn.commit()

        passed = deep_audit_100_books.audit_dimension_4_essence_depth(
            self.conn, quiet=True
        )
        self.assertFalse(passed)

    def test_audit_dimension_4_fail_empty_chains(self):
        """测试维度四当暗线伏笔为空时拦截。"""
        self._insert_valid_book_data("b1", "缺线小说")
        self.conn.execute("DELETE FROM essence_chains")
        self.conn.commit()

        passed = deep_audit_100_books.audit_dimension_4_essence_depth(
            self.conn, quiet=True
        )
        self.assertFalse(passed)

    # -------------------------------------------------------------------------
    # 维度五：题材真实性与外国译著复核
    # -------------------------------------------------------------------------

    def test_audit_dimension_5_pass(self):
        """测试维度五纯正中文题材通过。"""
        self._insert_valid_book_data("b1", "大奉打更人", genre="xuanhuan")
        self._insert_valid_book_data("b2", "赤心巡天", genre="xianxia")

        passed = deep_audit_100_books.audit_dimension_5_genre_legitimacy(
            self.conn, quiet=True
        )
        self.assertTrue(passed)

    def test_audit_dimension_5_fail_blacklist(self):
        """测试维度五命中外国译作黑名单（如《基督山伯爵》）。"""
        self._insert_valid_book_data("b1", "基督山伯爵")
        passed = deep_audit_100_books.audit_dimension_5_genre_legitimacy(
            self.conn, quiet=True
        )
        self.assertFalse(passed)

    def test_audit_dimension_5_fail_foreign_symbols(self):
        """测试维度五命中外国国籍或译者点号（如《某某·某某》或《(美)xxx》）。"""
        self._insert_valid_book_data("b1", "约翰·克利斯朵夫")
        passed = deep_audit_100_books.audit_dimension_5_genre_legitimacy(
            self.conn, quiet=True
        )
        self.assertFalse(passed)

        self.conn.execute("DELETE FROM essence_books")
        self._insert_valid_book_data("b2", "（美）海明威文集")
        passed2 = deep_audit_100_books.audit_dimension_5_genre_legitimacy(
            self.conn, quiet=True
        )
        self.assertFalse(passed2)

    # -------------------------------------------------------------------------
    # 维度六：服务层与 GUI 接口端到端兼容
    # -------------------------------------------------------------------------

    def test_audit_dimension_6_pass(self):
        """测试维度六在真实 essence_service API 下读取 4 卡 1 链完全合规。"""
        p = self._create_sample_novel_file("book_svc.txt")
        self._insert_valid_book_data("svc_001", "大周仙吏", str(p))

        passed = deep_audit_100_books.audit_dimension_6_service_read_e2e(
            self.conn, quiet=True, db_path=self.db_path
        )
        self.assertTrue(passed)

    def test_audit_dimension_6_fail_empty_table(self):
        """测试维度六在空表时返回 False。"""
        passed = deep_audit_100_books.audit_dimension_6_service_read_e2e(
            self.conn, quiet=True, db_path=self.db_path
        )
        self.assertFalse(passed)

    def test_audit_dimension_6_fail_card_mismatch(self):
        """测试维度六当资产卡不全时读取判定不合格。"""
        p = self._create_sample_novel_file("book_svc2.txt")
        self._insert_valid_book_data("svc_002", "天道图书馆", str(p))
        # 删除 1 张资产卡，使其变成 3 张
        self.conn.execute("DELETE FROM essence_assets WHERE category = 'style'")
        self.conn.commit()

        passed = deep_audit_100_books.audit_dimension_6_service_read_e2e(
            self.conn, quiet=True, db_path=self.db_path
        )
        self.assertFalse(passed)

    # -------------------------------------------------------------------------
    # CLI main() 集成测试
    # -------------------------------------------------------------------------

    def test_main_cli_success(self):
        """测试 main() 接收 CLI 参数并返回 0 (全部通过)。"""
        p = self._create_sample_novel_file("full_pass.txt")
        self._insert_valid_book_data("b1", "遮天", str(p))
        self._insert_valid_book_data("b2", "完美世界", str(p))

        ret = deep_audit_100_books.main([
            "--db", str(self.db_path),
            "--expected-books", "2",
            "-q",
        ])
        self.assertEqual(ret, 0)

    def test_main_cli_db_not_found(self):
        """测试 main() 指定不存在的数据库时返回 1。"""
        non_existent = self.tmp_path / "does_not_exist.db"
        ret = deep_audit_100_books.main([
            "--db", str(non_existent),
            "-q",
        ])
        self.assertEqual(ret, 1)

    def test_main_cli_failure_on_audit_defect(self):
        """测试 main() 在存在缺陷时返回 1。"""
        p = self._create_sample_novel_file("broken.txt", "第80章 跳跃开篇\n内容。")
        self._insert_valid_book_data("b1", "缺陷作品", str(p))

        ret = deep_audit_100_books.main([
            "--db", str(self.db_path),
            "--expected-books", "1",
            "-q",
        ])
        self.assertEqual(ret, 1)


if __name__ == "__main__":
    unittest.main()
