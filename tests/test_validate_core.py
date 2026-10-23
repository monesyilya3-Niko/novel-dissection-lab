"""validate.py 核心架构与全模型 Schema 校验引擎独立测试套件。

覆盖维度：
1. 基础标量与容器检查器（check_enum / check_bool / check_probability / check_strength / check_obj / check_list / check_str / is_num）
2. 声线卡全维校验（validate_voice_card：meta / narration / dialogue / emotion / banned / imagery / provenance）
3. 题材包全维校验（validate_genre_pack：meta / structure / commercial / language_rules）
4. 桥段库全维校验（validate_trope_library：abstraction_level / verbal版权红线 / verbatim红线 / skeleton / genre_scope）
5. 技法卡全维校验（validate_craft_card：meta.genre 铁律一白名单 / 覆盖率 / craft_summary / provenance）
6. 结构观测与商业观测校验（validate_structure_obs / validate_commercial_obs）
7. 题材文风卡轻量校验（validate_genre_prose_card：meta.id 格式规范 / MIT 归因三大件 / 软规则 / 原文兜底）
8. 实操工具库校验（validate_tool_library：八大工具库键存在性）
9. 纯数据无污染接口与自动类型推断（validate_asset_data / auto_kind）
10. CLI 命令行入口与退出状态码（main：PASS=0 / WARN=2 / REJECT=1 / JSON解析失败=1 / 题材隔离文件名守卫）
"""
import copy
import importlib.util
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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))


def _source_of(mod):
    try:
        return Path(mod.__file__).resolve()
    except (AttributeError, TypeError, OSError):
        return None


def _load(name: str):
    path = (SCRIPTS / f"{name}.py").resolve()
    mod = sys.modules.get(name)
    if mod is None or _source_of(mod) != path:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return mod


validate = _load("validate")


class TestValidatePrimitives(unittest.TestCase):
    """测试底层原子检查器。"""

    def setUp(self):
        validate.reset()

    def test_is_num(self):
        self.assertTrue(validate.is_num(0))
        self.assertTrue(validate.is_num(3.14))
        self.assertTrue(validate.is_num(-10))
        self.assertFalse(validate.is_num(True))  # bool 是 int 子类但不是纯数
        self.assertFalse(validate.is_num(False))
        self.assertFalse(validate.is_num("123"))
        self.assertFalse(validate.is_num(None))

    def test_check_enum(self):
        allowed = {"a", "b", "c"}
        validate.check_enum("a", allowed, "field")
        self.assertEqual(len(validate.ERRORS), 0)

        validate.check_enum("x", allowed, "field")
        self.assertEqual(len(validate.ERRORS), 1)
        self.assertIn("不在允许集合", validate.ERRORS[0])

    def test_check_bool(self):
        validate.check_bool(True, "b_field")
        validate.check_bool(False, "b_field")
        self.assertEqual(len(validate.ERRORS), 0)

        validate.check_bool(1, "b_field")
        validate.check_bool("True", "b_field")
        self.assertEqual(len(validate.ERRORS), 2)

    def test_check_probability(self):
        validate.check_probability(0, "prob")
        validate.check_probability(0.5, "prob")
        validate.check_probability(1.0, "prob")
        self.assertEqual(len(validate.ERRORS), 0)

        validate.check_probability(-0.1, "prob")
        validate.check_probability(1.1, "prob")
        validate.check_probability("0.5", "prob")
        self.assertEqual(len(validate.ERRORS), 3)

    def test_check_strength(self):
        validate.check_strength(1, "str")
        validate.check_strength(10, "str")
        validate.check_strength(5, "str")
        self.assertEqual(len(validate.ERRORS), 0)

        validate.check_strength(0, "str")
        validate.check_strength(11, "str")
        validate.check_strength(7.5, "str")  # 小数拒收
        validate.check_strength(True, "str")  # bool 排除
        self.assertEqual(len(validate.ERRORS), 4)

    def test_check_obj_and_list(self):
        self.assertTrue(validate.check_obj({"a": 1}, "obj"))
        self.assertFalse(validate.check_obj([1, 2], "obj"))
        self.assertEqual(len(validate.ERRORS), 1)

        validate.reset()
        self.assertTrue(validate.check_list([1, 2, 3], "lst", min_items=2))
        self.assertFalse(validate.check_list("not list", "lst"))
        self.assertTrue(validate.check_list([1], "lst", min_items=2))
        self.assertEqual(len(validate.ERRORS), 2)

    def test_check_str(self):
        self.assertTrue(validate.check_str("hello", "s", min_len=2, max_len=10))
        self.assertEqual(len(validate.ERRORS), 0)
        self.assertEqual(len(validate.WARNS), 0)

        self.assertFalse(validate.check_str(123, "s"))
        self.assertTrue(validate.check_str("a", "s", min_len=2))
        self.assertTrue(validate.check_str("too long string here", "s", max_len=5))
        self.assertEqual(len(validate.ERRORS), 2)
        self.assertEqual(len(validate.WARNS), 1)


class TestValidateVoiceCard(unittest.TestCase):
    """测试 voice-card 声线卡校验器。"""

    def setUp(self):
        self.valid_card = {
            "meta": {
                "source_title": "测试书",
                "genre": "campus-redemption",
                "extracted_at": "2026-10-18",
                "sample_chapters": [1, 2, 3],
                "confidence": 0.9,
                "human_reviewed": True,
            },
            "narration": {
                "pov": "第三人称限知",
                "sentence_rhythm": {
                    "avg_length": 15.2,
                    "short_ratio": 0.3,
                    "long_ratio": 0.1,
                    "burst_pattern": "长短交错有致",
                },
                "paragraph": {
                    "avg_lines": 2.5,
                    "single_line_para_ratio": 0.4,
                },
            },
            "dialogue": {
                "dialogue_ratio": 0.45,
                "subtext_level": "大量潜台词",
                "character_voices": [
                    {
                        "name": "主角",
                        "role": "主角",
                        "speech_signature": {
                            "refusal_pattern": "冷冷地移开视线",
                            "never_says": ["呜呜呜", "好可怕"],
                        },
                    }
                ],
            },
            "emotion_handling": {
                "mode": "动作外化式",
                "examples": [
                    {
                        "pattern": "指节泛白，深呼吸三次",
                        "anti_pattern": "他感到十分痛苦",
                    }
                ],
            },
            "banned": {
                "never_used_words": ["绝对", "极其"],
            },
            "imagery": {
                "high_freq_metaphor_domains": ["刀剑", "霜雪"],
                "sensory_preference": {"视觉": 0.5, "听觉": 0.5},
                "signature_devices": ["通感"],
            },
            "provenance": {
                "contains_verbatim": False,
            },
        }

    def test_valid_voice_card_passes(self):
        validate.validate_voice_card(self.valid_card)
        self.assertEqual(validate.ERRORS, [])
        self.assertEqual(validate.WARNS, [])

    def test_missing_required_keys_and_invalid_enum(self):
        card = copy.deepcopy(self.valid_card)
        del card["meta"]
        del card["banned"]
        card["narration"]["pov"] = "未知人称视角"
        validate.validate_voice_card(card)
        self.assertGreaterEqual(len(validate.ERRORS), 3)

    def test_character_voices_and_never_says_validation(self):
        card = copy.deepcopy(self.valid_card)
        # 1. 角色缺 name
        card["dialogue"]["character_voices"] = [{"role": "反派"}]
        validate.validate_voice_card(card)
        self.assertTrue(any("角色缺少 name" in e for e in validate.ERRORS))

        # 2. never_says 包含非字符串
        card["dialogue"]["character_voices"] = [{
            "name": "反派", "role": "反派",
            "speech_signature": {"never_says": [123, ""]}
        }]
        validate.validate_voice_card(card)
        self.assertTrue(any("never_says 条目应为非空字符串" in e for e in validate.ERRORS))

    def test_imagery_domain_and_provenance_verbatim(self):
        card = copy.deepcopy(self.valid_card)
        card["imagery"]["high_freq_metaphor_domains"] = ["比喻取材领域过长文字超过六个字符标签", "刀剑"]
        card["provenance"]["contains_verbatim"] = True
        validate.validate_voice_card(card)
        self.assertTrue(any("contains_verbatim 必须恒为 false" in e for e in validate.ERRORS))
        self.assertTrue(any("过长" in w for w in validate.WARNS))


class TestValidateGenrePackAndTrope(unittest.TestCase):
    """测试 genre-pack 题材包与 trope-library 桥段库校验器。"""

    def setUp(self):
        self.valid_genre_pack = {
            "meta": {
                "id": "gp-campus",
                "name": "校园救赎",
                "source_books": ["b1", "b2", "b3"],
                "confidence": 0.85,
            },
            "structure": {
                "chapter_roles": [{"role": "铺垫"}, {"role": "推进"}],
                "hook_system": {
                    "hook_types": [{"type": "悬念揭示"}, {"type": "危机降临"}]
                },
            },
            "commercial": {
                "payoff_density": {
                    "per_thousand_words": 1.5,
                    "payoff_types": [
                        {
                            "type": "打脸",
                            "buildup_length": 800,
                            "skeleton": "先抑后扬",
                        }
                    ],
                },
                "opening_analysis": {
                    "chapter_1": {
                        "hook_position": 200,
                        "first_300_words_task": "立住主角绝境",
                    }
                },
            },
            "language_rules": {
                "iron_rules": [
                    {
                        "rule": "禁止直陈抒情",
                        "bad_example": "他很难过",
                        "good_example": "他背过身去",
                    }
                ]
            },
        }

        self.valid_trope_library = {
            "tropes": [
                {
                    "abstraction_level": "structural",
                    "contains_verbatim": False,
                    "genre_scope": "campus-redemption",
                    "parameters": {"intensity": "high"},
                    "skeleton": {
                        "setup": "伏笔",
                        "escalation": "升级",
                        "payoff": "爆发",
                        "aftermath": "收尾",
                    },
                    "effectiveness": {
                        "payoff_strength": 8,
                    },
                }
            ]
        }

    def test_valid_genre_pack_passes(self):
        validate.validate_genre_pack(self.valid_genre_pack)
        self.assertEqual(validate.ERRORS, [])
        self.assertEqual(validate.WARNS, [])

    def test_genre_pack_errors_and_warnings(self):
        gp = copy.deepcopy(self.valid_genre_pack)
        gp["meta"]["source_books"] = ["b1"]  # < 3 本引发 warn
        gp["structure"]["chapter_roles"][0]["role"] = "非法角色"  # err
        gp["commercial"]["payoff_density"]["payoff_types"][0]["buildup_length"] = -5  # err
        gp["language_rules"]["iron_rules"][0]["rule"] = ""  # 缺 rule
        validate.validate_genre_pack(gp)
        self.assertTrue(any("不在允许集合" in e for e in validate.ERRORS))
        self.assertTrue(any("buildup_length 必须给具体数字" in e for e in validate.ERRORS))
        self.assertTrue(any("缺少 'rule'" in e for e in validate.ERRORS))
        self.assertTrue(any("题材包应由 ≥3 本聚合" in w for w in validate.WARNS))

    def test_trope_library_verbal_and_verbatim_rejection(self):
        # 1. 正常通过
        validate.validate_trope_library(self.valid_trope_library)
        self.assertEqual(validate.ERRORS, [])

        # 2. verbal 版权红线
        t1 = copy.deepcopy(self.valid_trope_library)
        t1["tropes"][0]["abstraction_level"] = "verbal"
        validate.validate_trope_library(t1)
        self.assertTrue(any("verbal 级别一律拒收" in e for e in validate.ERRORS))

        # 3. contains_verbatim=true 红线
        t2 = copy.deepcopy(self.valid_trope_library)
        t2["tropes"][0]["contains_verbatim"] = True
        validate.validate_trope_library(t2)
        self.assertTrue(any("contains_verbatim=true 一律拒收" in e for e in validate.ERRORS))

        # 4. genre_scope 缺失或非法
        t3 = copy.deepcopy(self.valid_trope_library)
        del t3["tropes"][0]["genre_scope"]
        validate.validate_trope_library(t3)
        self.assertTrue(any("缺少 genre_scope 字段" in e for e in validate.ERRORS))

        t4 = copy.deepcopy(self.valid_trope_library)
        t4["tropes"][0]["genre_scope"] = "nonexistent-fantasy-999"
        validate.validate_trope_library(t4)
        self.assertTrue(any("非法" in e for e in validate.ERRORS))


class TestValidateCraftAndObservations(unittest.TestCase):
    """测试 craft-card / structure-obs / commercial-obs / tool-library。"""

    def test_validate_craft_card(self):
        craft = {
            "meta": {
                "source_title": "测试书",
                "genre": "campus-redemption",
                "extracted_at": "2026-10-18",
                "sample_chapters": [1, 2, 3],
                "confidence": 0.9,
            },
            "craft_analysis": {
                "foreshadowing": {"techniques": ["双向伏笔"]},
                "tension_building": {"techniques": ["情绪阶梯"]},
                "rhythm_control": {"techniques": ["快慢交织"]},
            },
            "craft_summary": {
                "top_3_strengths": ["节奏", "伏笔", "反转"],
                "unique_techniques": ["技法A"],
                "reusable_patterns": ["模板B"],
            },
            "provenance": {"contains_verbatim": False},
        }
        validate.validate_craft_card(craft)
        self.assertEqual(validate.ERRORS, [])

        # 空 genre 报硬错误
        craft_bad_genre = copy.deepcopy(craft)
        craft_bad_genre["meta"]["genre"] = ""
        validate.validate_craft_card(craft_bad_genre)
        self.assertTrue(any("meta.genre 为空" in e for e in validate.ERRORS))

    def test_validate_structure_obs(self):
        obs = {
            "meta": {"source_title": "书A", "genre": "urban", "scope": "full"},
            "chapter_analyses": [{"chapter": 1, "role": "铺垫", "hook": "h1"}],
            "aggregate": {
                "hook_type_freq": {"悬念": 5},
                "hook_min_interval": 2,
                "foreshadow_avg_span": 3.5,
                "foreshadow_max_span": 10,
                "foreshadow_concurrent_open": 2,
            },
        }
        validate.validate_structure_obs(obs)
        self.assertEqual(validate.ERRORS, [])

        bad_obs = copy.deepcopy(obs)
        del bad_obs["aggregate"]["hook_min_interval"]
        validate.validate_structure_obs(bad_obs)
        self.assertTrue(any("缺少必填字段 'hook_min_interval'" in e for e in validate.ERRORS))

    def test_validate_commercial_obs(self):
        obs = {
            "meta": {"source_title": "书A", "genre": "urban", "scope": "full"},
            "payoff_density": {"per_thousand": 2},
            "opening_analysis": {"hook": "strong"},
            "paywall": {"chapter": 20},
        }
        validate.validate_commercial_obs(obs)
        self.assertEqual(validate.ERRORS, [])

        bad_com = copy.deepcopy(obs)
        del bad_com["paywall"]
        validate.validate_commercial_obs(bad_com)
        self.assertTrue(any("缺少必填结构 'paywall'" in e for e in validate.ERRORS))

    def test_validate_tool_library(self):
        tl = {
            "meta": {"name": "实操库", "version": "1.0"},
            "goldfingers": [{"name": "金手指A"}],
            "hooks": [{"type": "悬念"}],
        }
        validate.validate_tool_library(tl)
        self.assertEqual(validate.ERRORS, [])

        # 缺少有效实操库键
        tl_bad = {"meta": {"name": "空库"}}
        validate.validate_tool_library(tl_bad)
        self.assertTrue(any("缺少有效实操库条目列表" in e for e in validate.ERRORS))


class TestValidateGenreProseCardAndAutoKind(unittest.TestCase):
    """测试 genre-prose-card 轻量卡与 auto_kind 自动推断。"""

    def setUp(self):
        self.prose_card = {
            "meta": {
                "kind": "genre-prose-card",
                "id": "genre-xuanhuan-cultivation",
                "name": "玄幻修真文风",
                "confidence": 0.9,
                "upgrade_status": "seed",
                "provenance": {
                    "source": "开源典范库",
                    "license": "CC-BY-4.0",
                    "copyright": "原作者社区",
                    "verified": False,
                },
            },
            "language_rules": {
                "forbidden_elements": ["现代网络流行梗"]
            },
            "prose": {
                "sections": {
                    "opening": "晨曦初露，群峰如聚。"
                }
            },
        }

    def test_valid_genre_prose_card_passes(self):
        validate.validate_genre_prose_card(self.prose_card)
        self.assertEqual(validate.ERRORS, [])

    def test_genre_prose_card_id_regex_and_provenance_three_keys(self):
        # 1. id 不符合 genre-<slug> 命名
        bad_card = copy.deepcopy(self.prose_card)
        bad_card["meta"]["id"] = "INVALID_UPPERCASE"
        validate.validate_genre_prose_card(bad_card)
        self.assertTrue(any("不符合 'genre-<slug>' 命名规范" in e for e in validate.ERRORS))

        # 2. provenance 缺少 copyright
        bad_prov = copy.deepcopy(self.prose_card)
        del bad_prov["meta"]["provenance"]["copyright"]
        validate.validate_genre_prose_card(bad_prov)
        self.assertTrue(any("provenance.copyright 必须为非空字符串" in e for e in validate.ERRORS))

    def test_auto_kind_deduction(self):
        # 1. 显式 kind == genre-prose-card
        self.assertEqual(validate.auto_kind(self.prose_card), "genre-prose-card")

        # 2. genre-prose-card-index
        index_data = {"_count": 1, "cards": {"玄幻": {"id": "g-1", "file": "f.json"}}}
        self.assertEqual(validate.auto_kind(index_data, "genre-prose-card-index.json"), "genre-prose-card-index")

        # 3. distilled
        dist_data = {"meta": {"dimension": "voice-card"}, "rules": [], "blindspots": [], "stats": {}}
        self.assertEqual(validate.auto_kind(dist_data), "distilled")

        # 4. tool-library
        tool_data = {"goldfingers": [1]}
        self.assertEqual(validate.auto_kind(tool_data), "tool-library")

        # 5. craft-card
        craft_data = {"craft_analysis": {}}
        self.assertEqual(validate.auto_kind(craft_data), "craft-card")

        # 6. structure-obs
        struct_data = {"chapter_analyses": []}
        self.assertEqual(validate.auto_kind(struct_data), "structure-obs")

        # 7. commercial-obs
        com_data = {"payoff_density": {}, "paywall": {}}
        self.assertEqual(validate.auto_kind(com_data), "commercial-obs")

        # 8. genre-pack
        gp_data = {"commercial": {}, "language_rules": {}, "structure": {}, "world_conventions": {}}
        self.assertEqual(validate.auto_kind(gp_data), "genre-pack")

        # 9. 兜底 voice-card
        self.assertEqual(validate.auto_kind({}), "voice-card")


class TestValidateCLIAndDataInterface(unittest.TestCase):
    """测试纯数据接口 validate_asset_data 与 CLI main() 入口。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_val_cli_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_asset_data_isolation(self):
        validate.ERRORS = ["existing_error"]
        validate.WARNS = ["existing_warn"]

        # 校验未知类型
        errors, warns = validate.validate_asset_data("unknown_kind", {})
        self.assertEqual(len(errors), 1)
        self.assertIn("未知资产类型", errors[0])

        # 外部全局状态必须被完全恢复
        self.assertEqual(validate.ERRORS, ["existing_error"])
        self.assertEqual(validate.WARNS, ["existing_warn"])
        validate.reset()

    def test_main_cli_pass_warn_and_reject(self):
        # 1. 准备 PASS 文件（实操工具库）
        pass_file = Path(self.temp_dir) / "tool-lib.json"
        pass_file.write_text(json.dumps({
            "meta": {"name": "工具库"},
            "goldfingers": [{"name": "随身空间"}]
        }), encoding="utf-8")

        with mock.patch("sys.argv", ["validate.py", str(pass_file)]), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = validate.main()
        self.assertEqual(code, 0)
        self.assertIn("结论: PASS", mock_out.getvalue())

        # 2. 准备 REJECT 文件（空对象判为 voice-card 并产生硬错误）
        reject_file = Path(self.temp_dir) / "bad.json"
        reject_file.write_text("{}", encoding="utf-8")
        with mock.patch("sys.argv", ["validate.py", str(reject_file)]), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = validate.main()
        self.assertEqual(code, 1)
        self.assertIn("结论: REJECT", mock_out.getvalue())

        # 3. 损坏的 JSON 格式
        corrupt_file = Path(self.temp_dir) / "corrupt.json"
        corrupt_file.write_text("{not valid json", encoding="utf-8")
        with mock.patch("sys.argv", ["validate.py", str(corrupt_file)]), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = validate.main()
        self.assertEqual(code, 1)
        self.assertIn("JSON 解析失败", mock_out.getvalue())

    def test_main_cli_genre_prose_card_filename_mismatch(self):
        # 题材文风卡文件名与 meta.id 不一致引发隔离拒收
        card_file = Path(self.temp_dir) / "mismatched-name.json"
        card_file.write_text(json.dumps({
            "meta": {
                "kind": "genre-prose-card",
                "id": "genre-xuanhuan",
                "name": "玄幻文风",
                "confidence": 0.9,
                "provenance": {
                    "source": "src", "license": "MIT", "copyright": "cp", "verified": False
                }
            },
            "language_rules": {},
            "prose": {"sections": {"a": "b"}}
        }), encoding="utf-8")

        with mock.patch("sys.argv", ["validate.py", str(card_file)]), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = validate.main()
        self.assertEqual(code, 1)
        self.assertIn("题材隔离失败", mock_out.getvalue())

    def test_main_cli_with_explicit_argv(self):
        pass_file = Path(self.temp_dir) / "explicit_pass.json"
        pass_file.write_text(json.dumps({
            "meta": {"kind": "tool-library", "name": "显式测试工具库"},
            "goldfingers": [{"name": "随身空间"}]
        }), encoding="utf-8")
        with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = validate.main([str(pass_file)])
        self.assertEqual(code, 0)
        self.assertIn("结论: PASS", mock_out.getvalue())


if __name__ == "__main__":
    unittest.main()
