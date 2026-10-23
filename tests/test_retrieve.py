#!/usr/bin/env python3
"""语义检索与桥段检索引擎（retrieve.py）全维独立测试套件（纯标准库 unittest）。

覆盖范围：
1. _tokenize / _flatten_value / _flatten_asset_body / _build_snippet 文本解析与规范化
2. _ngram_counter / _norm / _cosine_sim 字符 n-gram 与向量余弦计算
3. build_index / _save_index / _load_index 倒排索引构建与持久化往返
4. _idf / _bm25_score / _vector_score / _fused_score 检索打分算法与边界异常防御
5. retrieve_for_intent / render_retrieval 意图检索、意图映射扩展、噪声过滤、排序截断与 Markdown 渲染
6. _load_tropes / _trope_score / retrieve_tropes 桥段库加载、打分与题材隔离（铁律一）
"""
import math
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import retrieve as ret_mod


class TestTokenizeAndFlatten(unittest.TestCase):
    """测试文本切分、值扁平化与摘要生成。"""

    def test_tokenize_basic(self):
        text = "Hello World! 这是一个测试 123"
        tokens = ret_mod._tokenize(text)
        self.assertIn("hello", tokens)
        self.assertIn("world", tokens)
        self.assertIn("这是一个测试", tokens)
        self.assertIn("123", tokens)
        # 空文本返回空列表
        self.assertEqual(ret_mod._tokenize(""), [])
        self.assertEqual(ret_mod._tokenize(None), [])

    def test_flatten_value_types(self):
        self.assertEqual(ret_mod._flatten_value("文本"), "文本")
        self.assertEqual(ret_mod._flatten_value(True), "true")
        self.assertEqual(ret_mod._flatten_value(False), "false")
        self.assertEqual(ret_mod._flatten_value(123), "123")
        self.assertEqual(ret_mod._flatten_value(3.14), "3.14")
        self.assertEqual(ret_mod._flatten_value(["a", "b"]), "a、b")
        self.assertEqual(ret_mod._flatten_value({"k1": "v1", "k2": "v2"}), "k1:v1，k2:v2")
        self.assertEqual(ret_mod._flatten_value(None), "")

    def test_flatten_asset_body(self):
        asset = {
            "meta": {"id": "ignore_me"},
            "provenance": {"ignore": True},
            "rules": [{"ignore": True}],
            "narration": {"pov": "第一人称", "pace": "快节奏"},
            "dialogue": {"tag_style": "轻动词"},
        }
        flat = ret_mod._flatten_asset_body(asset)
        self.assertIn("第一人称", flat)
        self.assertIn("轻动词", flat)
        self.assertNotIn("ignore_me", flat)

    def test_build_snippet(self):
        # 1. 优先从 rules 构建
        asset_with_rules = {
            "rules": [
                {"field": "视角", "value": "第三人称限知"},
                {"field": "节奏", "value": "短句紧凑"},
            ]
        }
        snippet = ret_mod._build_snippet(asset_with_rules)
        self.assertIn("视角: 第三人称限知", snippet)
        self.assertIn("节奏: 短句紧凑", snippet)

        # 2. 无 rules 时从正文退化构建
        asset_no_rules = {
            "narration": {"pov": "全知视角"}
        }
        snippet2 = ret_mod._build_snippet(asset_no_rules)
        self.assertIn("全知视角", snippet2)

        # 3. 超过 200 字符时截断并加省略号
        asset_long = {
            "rules": [{"field": "长规则", "value": "长内容" * 100}]
        }
        snippet3 = ret_mod._build_snippet(asset_long)
        self.assertEqual(len(snippet3), ret_mod.SNIPPET_LEN)
        self.assertTrue(snippet3.endswith("…"))


class TestNgramAndVectorOperations(unittest.TestCase):
    """测试字符 n-gram 生成、向量范数与余弦相似度。"""

    def test_ngram_counter(self):
        text = "悬疑反转"
        ngrams = ret_mod._ngram_counter(text, max_n=3)
        # 包含 1-gram, 2-gram, 3-gram
        self.assertIn("2:悬疑", ngrams)
        self.assertIn("2:反转", ngrams)
        self.assertIn("3:悬疑反", ngrams)
        # 空文本返回空 Counter
        self.assertEqual(ret_mod._ngram_counter(""), Counter())

    def test_norm_zero_and_nonzero(self):
        self.assertEqual(ret_mod._norm(Counter()), 0.0)
        c = Counter({"a": 3, "b": 4})
        self.assertEqual(ret_mod._norm(c), 5.0)

    def test_cosine_sim(self):
        c1 = Counter({"a": 1, "b": 1})
        norm1 = math.sqrt(2)
        c2 = Counter({"a": 1, "b": 1})
        norm2 = math.sqrt(2)
        self.assertAlmostEqual(ret_mod._cosine_sim(c1, norm1, c2, norm2), 1.0)

        # 正交向量 -> 0.0
        c3 = Counter({"c": 1})
        norm3 = 1.0
        self.assertEqual(ret_mod._cosine_sim(c1, norm1, c3, norm3), 0.0)

        # 零向量 -> 0.0
        self.assertEqual(ret_mod._cosine_sim(Counter(), 0.0, c1, norm1), 0.0)


class TestIndexBuildAndPersistence(unittest.TestCase):
    """测试倒排索引构建与持久化存取。"""

    def test_build_index_and_persistence(self):
        assets = {
            "voice-card": {
                "meta": {"id": "urban-voice", "source_title": "都市书"},
                "rules": [{"field": "语言", "value": "干脆利落"}],
            },
            "commercial-obs": {
                "meta": {"id": "urban-comm", "source_title": "都市商业"},
                "rules": [{"field": "爽点", "value": "打脸装逼"}],
            },
        }
        with tempfile.TemporaryDirectory() as td:
            persist_file = str(Path(td) / "index_cache.json")
            # 1. 首次构建并持久化
            idx = ret_mod.build_index(assets, persist_path=persist_file)
            self.assertEqual(len(idx.docs), 2)
            self.assertIn("干脆利落", idx.inverted)
            self.assertTrue(Path(persist_file).is_file())

            # 2. 从持久化加载
            loaded_idx = ret_mod._load_index(persist_file)
            self.assertIsNotNone(loaded_idx)
            self.assertEqual(len(loaded_idx.docs), 2)
            self.assertEqual(loaded_idx.docs[0].asset_id, "urban-voice")

    def test_build_index_none_or_corrupt(self):
        empty_idx = ret_mod.build_index(None)
        self.assertEqual(len(empty_idx.docs), 0)

        with tempfile.TemporaryDirectory() as td:
            corrupt_file = Path(td) / "bad.json"
            corrupt_file.write_text("{ 畸形 JSON", encoding="utf-8")
            self.assertIsNone(ret_mod._load_index(str(corrupt_file)))
            self.assertIsNone(ret_mod._load_index(str(Path(td) / "nonexistent.json")))


class TestBM25AndScoring(unittest.TestCase):
    """测试 BM25 打分、向量打分与融合公式。"""

    def setUp(self):
        self.assets = {
            "craft-card": {
                "meta": {"id": "craft-suspense"},
                "rules": [{"field": "技法", "value": "设置悬念与层层反转钩子"}],
            },
            "commercial-obs": {
                "meta": {"id": "comm-payoff"},
                "rules": [{"field": "爽点", "value": "高潮打脸爆发节奏"}],
            },
        }
        self.index = ret_mod.build_index(self.assets)

    def test_idf_calculation(self):
        idf_val = ret_mod._idf("设置悬念与层层反转钩子", self.index)
        self.assertGreater(idf_val, 0)
        # 验证缓存生效
        self.assertIn("设置悬念与层层反转钩子", self.index.idf_cache)

    def test_bm25_score_and_validation(self):
        doc = self.index.docs[0]
        score = ret_mod._bm25_score(["悬念"], doc, self.index)
        self.assertGreater(score, 0.0)

        # 参数校验
        with self.assertRaises(ValueError):
            ret_mod._bm25_score(["悬念"], doc, self.index, k1=-1.0)
        with self.assertRaises(ValueError):
            ret_mod._bm25_score(["悬念"], doc, self.index, b=1.5)

    def test_fused_score(self):
        fused = ret_mod._fused_score(bm25_raw=2.0, bm25_max=4.0, cos_sim=0.8, alpha=0.5)
        # 0.5 * (2/4) + 0.5 * 0.8 = 0.25 + 0.40 = 0.65
        self.assertAlmostEqual(fused, 0.65)


class TestRetrieveForIntent(unittest.TestCase):
    """测试按意图检索蒸馏片段与结果渲染。"""

    def setUp(self):
        self.assets = {
            "craft-card": {
                "meta": {"id": "craft-suspense"},
                "rules": [{"field": "技法", "value": "设置悬念与危机钩子"}],
            },
            "commercial-obs": {
                "meta": {"id": "comm-payoff"},
                "rules": [{"field": "商业爽点", "value": "极速打脸与收获兑现"}],
            },
        }
        self.index = ret_mod.build_index(self.assets)

    def test_retrieve_empty_or_invalid(self):
        self.assertEqual(ret_mod.retrieve_for_intent("", self.index), [])
        self.assertEqual(ret_mod.retrieve_for_intent(None, self.index), [])
        self.assertEqual(ret_mod.retrieve_for_intent("钩子", None), [])
        self.assertEqual(ret_mod.retrieve_for_intent("钩子", ret_mod.Index()), [])

    def test_retrieve_intent_mapping_hit(self):
        # 意图命中 "钩子" 关键词，应优先召回 craft-card
        hits = ret_mod.retrieve_for_intent("开篇钩子设计", self.index, top_k=2)
        self.assertTrue(len(hits) > 0)
        self.assertEqual(hits[0].asset_id, "craft-suspense")
        self.assertGreaterEqual(hits[0].score, ret_mod.MIN_FUSION_SCORE)

    def test_retrieve_noise_filtering(self):
        # 完全无关的多字意图应返回空列表（噪声归零）
        hits = ret_mod.retrieve_for_intent("完全无关的火星天气预报", self.index)
        self.assertEqual(hits, [])

    def test_render_retrieval(self):
        self.assertEqual(ret_mod.render_retrieval([]), "")
        hit = ret_mod.HitEntry(asset_id="a1", dimension="d1", score=0.8, snippet="规则: 制造悬念")
        rendered = ret_mod.render_retrieval([hit])
        self.assertIn("### 针对性注入（来自检索）", rendered)
        self.assertIn("- 规则: 制造悬念", rendered)


class TestTropeRetrieval(unittest.TestCase):
    """测试桥段库检索与题材隔离机制（铁律一）。"""

    def setUp(self):
        self.mock_tropes = [
            {
                "id": "T01",
                "name": "通识打脸",
                "category": "打脸爽点",
                "genre_scope": "universal",
                "skeleton": {"起": "受辱", "承": "反转"},
            },
            {
                "id": "T02",
                "name": "校园救赎专属桥段",
                "category": "救赎情感",
                "genre_scope": "campus-redemption",
                "skeleton": {"起": "误解", "承": "化解"},
            },
            {
                "id": "T03",
                "name": "玄幻越级反杀",
                "category": "战斗打脸",
                "genre_scope": "xuanhuan",
                "skeleton": {"起": "强敌", "承": "拔剑"},
            },
        ]

    def test_trope_score(self):
        t = self.mock_tropes[0]
        self.assertEqual(ret_mod._trope_score("", t), 0.0)
        score = ret_mod._trope_score("打脸", t)
        self.assertGreater(score, 0.0)

    def test_retrieve_tropes_genre_isolation(self):
        with mock.patch("retrieve._load_tropes", return_value=self.mock_tropes):
            # 1. 目标题材 campus-redemption: 可见 universal (T01) 和 campus (T02)，排除 xuanhuan (T03)
            res_campus = ret_mod.retrieve_tropes("打脸救赎", genre="campus-redemption", top_k=5)
            ids_campus = [t["id"] for t in res_campus]
            self.assertIn("T01", ids_campus)
            self.assertIn("T02", ids_campus)
            self.assertNotIn("T03", ids_campus)

            # 2. 未指定 genre (None): 仅返回 universal (T01)
            res_none = ret_mod.retrieve_tropes("打脸", genre=None, top_k=5)
            ids_none = [t["id"] for t in res_none]
            self.assertIn("T01", ids_none)
            self.assertNotIn("T02", ids_none)
            self.assertNotIn("T03", ids_none)

            # 3. 参数防御
            self.assertEqual(ret_mod.retrieve_tropes("", genre="campus-redemption"), [])
            self.assertEqual(ret_mod.retrieve_tropes("打脸", top_k=0), [])


if __name__ == "__main__":
    unittest.main()
