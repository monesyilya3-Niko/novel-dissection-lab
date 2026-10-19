#!/usr/bin/env python3
"""
Unit tests for scripts/consistency.py (Style Consistency Checker)
100% pure Python standard library unittest, zero external dependencies.
"""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from scripts import consistency


class TestExtractKeywords(unittest.TestCase):
    """测试 extract_keywords 各种边界条件与长短描述抽取。"""

    def test_non_string_input(self):
        self.assertEqual(consistency.extract_keywords(None), [])
        self.assertEqual(consistency.extract_keywords(123), [])
        self.assertEqual(consistency.extract_keywords(["list"]), [])
        self.assertEqual(consistency.extract_keywords({"key": "val"}), [])

    def test_short_string_within_bounds(self):
        # 长度 2 到 10 之间整段收录
        self.assertEqual(consistency.extract_keywords("休想逃跑"), ["休想逃跑"])
        self.assertEqual(consistency.extract_keywords("哼"), [])  # 长度 1 < 2
        self.assertEqual(consistency.extract_keywords("一二三四五六七八九十"), ["一二三四五六七八九十"])  # 长度 10

    def test_long_string_without_quotes(self):
        # 长度 > 10 且无引号片段，返回空
        long_str = "这是一段非常冗长而且没有任何标点引号的纯文本描述"
        self.assertEqual(consistency.extract_keywords(long_str), [])

    def test_long_string_with_various_quotes(self):
        # 测试各类中文和英文引号提取
        text = (
            "说话时经常使用「绝对不行」与『休想得逞』，"
            "偶尔冷笑并说“痴心妄想”，‘无可奉告’，"
            '还有英文 "never" 与 \'give up\''
        )
        kws = consistency.extract_keywords(text)
        expected = ["绝对不行", "休想得逞", "痴心妄想", "无可奉告", "never", "give up"]
        self.assertEqual(kws, expected)

    def test_quotes_length_filtering(self):
        # 引号内片段长度 < 2 或 > 10 应被跳过
        text = "他习惯说「啊」还有「这是一段非常长超过十个字的无效口头禅」以及「好的」"
        kws = consistency.extract_keywords(text)
        self.assertEqual(kws, ["好的"])

    def test_max_kws_capping(self):
        text = "「一」「二二」「三三」「四四」「五五」「六六」「七七」「八八」「九九」"
        # 默认 max_kws=8
        kws = consistency.extract_keywords(text)
        self.assertEqual(len(kws), 8)
        self.assertEqual(kws[0], "二二")
        # 自定义 max_kws=3
        kws_capped = consistency.extract_keywords(text, max_kws=3)
        self.assertEqual(len(kws_capped), 3)


class TestVtToStr(unittest.TestCase):
    """测试 _vt_to_str verbal_tics 统一转换。"""

    def test_string_item(self):
        self.assertEqual(consistency._vt_to_str("哼"), "哼")

    def test_dict_with_chinese_keys(self):
        d1 = {"情境": "紧张", "规则": "咬嘴唇"}
        self.assertEqual(consistency._vt_to_str(d1), "紧张：咬嘴唇")
        d2 = {"场景": "愤怒", "规则": "握拳"}
        self.assertEqual(consistency._vt_to_str(d2), "愤怒：握拳")
        d3 = {"情境": "独处"}
        self.assertEqual(consistency._vt_to_str(d3), "独处")

    def test_dict_with_english_keys(self):
        d = {"context": "battle", "rule": "shout"}
        self.assertEqual(consistency._vt_to_str(d), "battle：shout")
        d_only_rule = {"rule": "silence"}
        self.assertEqual(consistency._vt_to_str(d_only_rule), "silence")

    def test_fallback_and_non_dict(self):
        d_empty = {}
        self.assertEqual(consistency._vt_to_str(d_empty), "{}")
        self.assertEqual(consistency._vt_to_str(12345), "12345")


class TestCheckVoices(unittest.TestCase):
    """测试角色声线执行度 check_voices。"""

    def test_no_characters_present(self):
        voices = [{"name": "林远"}]
        text = "今天天气很好，阳光洒在街道上。"
        score, details = consistency.check_voices(text, voices)
        self.assertEqual(score, 0.0)
        self.assertIn("本章无角色出场", details[0])

    def test_empty_voices_list(self):
        score, details = consistency.check_voices("林远走在街上", [])
        self.assertEqual(score, 0.0)
        self.assertIn("本章无角色出场", details[0])

    def test_character_matched_full_hits(self):
        voices = [
            {
                "name": "林远",
                "speech_signature": {
                    "verbal_tics": ["休想", "可恶"],
                    "refusal_pattern": "「绝不妥协」",
                    "anger_pattern": "「不可饶恕」"
                }
            }
        ]
        text = "林远冷哼一声：休想！可恶，绝不妥协，不可饶恕！"
        score, details = consistency.check_voices(text, voices)
        self.assertEqual(score, 35.0)
        self.assertTrue(any("林远: 命中" in d and "35.0/35.0" in d for d in details))

    def test_character_matched_zero_hits(self):
        voices = [
            {
                "name": "林远",
                "speech_signature": {
                    "verbal_tics": ["休想", "可恶"]
                }
            }
        ]
        text = "林远只是默默地喝茶，什么也没说。"
        score, details = consistency.check_voices(text, voices)
        self.assertEqual(score, 0.0)
        self.assertTrue(any("命中 0/2" in d and "0.0/35.0" in d for d in details))

    def test_character_matched_single_hit(self):
        voices = [
            {
                "name": "林远",
                "speech_signature": {
                    "verbal_tics": ["休想", "可恶", "绝不"]
                }
            }
        ]
        text = "林远咬牙切齿：休想！"
        score, details = consistency.check_voices(text, voices)
        # hit == 1: score = round(per * 0.7, 1) = round(35 * 0.7, 1) = 24.5
        self.assertEqual(score, 24.5)

    def test_character_without_speech_signature(self):
        voices = [{"name": "林远"}]
        text = "林远走了过来。"
        score, details = consistency.check_voices(text, voices)
        # no kws: score = round(per * 0.5, 1) = 17.5
        self.assertEqual(score, 17.5)

    def test_multiple_characters_present(self):
        voices = [
            {
                "name": "林远",
                "speech_signature": {"verbal_tics": ["休想"]}
            },
            {
                "name": "苏晓",
                "speech_signature": {"verbal_tics": ["放心"]}
            }
        ]
        text = "林远喊道：休想！苏晓微笑着说：放心吧。"
        score, details = consistency.check_voices(text, voices)
        # per = 35 / 2 = 17.5
        # both hit 1/1 -> full per = 17.5 each -> total 35.0
        self.assertEqual(score, 35.0)
        self.assertEqual(len(details), 2)


class TestCheckEmotion(unittest.TestCase):
    """测试情绪写法 check_emotion。"""

    def test_hit_sensation_levels(self):
        # 0 hits
        score, details = consistency.check_emotion("纯逻辑推理文本，毫无身体反应。", {})
        self.assertEqual(score, 0)

        # 1-3 hits -> 15
        text_2_hits = "他感到心跳加速，呼吸变粗。"
        score, details = consistency.check_emotion(text_2_hits, {})
        self.assertEqual(score, 15)

        # 4+ hits -> 20
        text_4_hits = "他心跳剧烈，呼吸急促，手心出汗，喉咙发紧。"
        score, details = consistency.check_emotion(text_4_hits, {})
        self.assertEqual(score, 20)

    def test_direct_emotion_penalty(self):
        # 4 hits sensation (20) - 2 direct emotions (-4) = 16
        text = "他心跳剧烈，呼吸急促，手心出汗，喉咙发紧。但他心里很愤怒，非常开心。"
        score, details = consistency.check_emotion(text, {})
        self.assertEqual(score, 16)

        # Penalty capped at 10
        many_direct = " ".join(consistency.DIRECT_EMOTION)
        text_heavy_penalty = "他心跳呼吸手心喉咙。" + many_direct
        score, details = consistency.check_emotion(text_heavy_penalty, {})
        # sensation_score = 20, direct_penalty = min(12 * 2, 10) = 10 -> score = 10
        self.assertEqual(score, 10)

    def test_custom_asset_vocabulary(self):
        emotion_cfg = {
            "body_reaction_vocabulary": ["尾椎骨泛起凉意", "后颈汗毛倒竖"]
        }
        text = "瞬间，他的尾椎骨泛起凉意，后颈汗毛倒竖。"
        score, details = consistency.check_emotion(text, emotion_cfg)
        self.assertEqual(score, 15)
        self.assertTrue(any("资产词 2 + 兜底" in d for d in details))


class TestCheckNarration(unittest.TestCase):
    """测试叙述层 check_narration。"""

    def test_third_person_default(self):
        text = "他走在雨中。\n\n路很长。\n天很黑。\n风很大。\n\n周围一片寂静"
        score, details = consistency.check_narration(text, {})
        # hit_pov (他) -> +5
        # short_streak >= 3 -> +5
        # single_sentence_paragraphs: "周围一片寂静" (1 para) < 5 -> +0
        self.assertEqual(score, 10)
        self.assertTrue(any("第三人称 ✓(+5)" in d for d in details))
        self.assertTrue(any("短句爆发 5 连续 ✓(+5)" in d for d in details))

    def test_first_person_declared(self):
        narration = {"pov": "第一人称视角"}
        text = "我看着窗外。\n\n路灯昏暗。\n夜色渐浓。\n街道空荡。\n\n屋里很暖和"
        score, details = consistency.check_narration(text, narration)
        self.assertEqual(score, 10)
        self.assertTrue(any("第一人称 ✓(+5)" in d for d in details))

    def test_single_sentence_paragraphs_bonus(self):
        # 5 or more lines with len <= 20 and no sentence-ending punctuation
        paras = [
            "他走在前面",
            "风吹起衣角",
            "灯火忽明忽暗",
            "影子被拉得很长",
            "脚步声回荡",
            "一切都安静下来"
        ]
        text = "\n\n".join(paras)
        score, details = consistency.check_narration(text, {})
        # pov +5, short streak +5, single sentence paras (6 >= 5) +5 -> total 15
        self.assertEqual(score, 15)
        self.assertTrue(any("单句成段 6 段 ✓(+5)" in d for d in details))


class TestCheckBanned(unittest.TestCase):
    """测试禁忌词 check_banned。"""

    def test_banned_none_or_empty(self):
        score, details = consistency.check_banned("随便写的内容", None)
        self.assertEqual(score, 20)
        self.assertTrue(any("禁忌词表为空" in d for d in details))

        score2, details2 = consistency.check_banned("随便写的内容", [])
        self.assertEqual(score2, 20)
        self.assertTrue(any("禁忌词表为空" in d for d in details2))

    def test_banned_no_hits(self):
        banned = ["违禁词A", "违禁词B"]
        score, details = consistency.check_banned("这是合规内容", banned)
        self.assertEqual(score, 20)
        self.assertTrue(any("命中 0 个" in d for d in details))

    def test_banned_hits_deduction(self):
        banned = ["禁词1", "禁词2", "禁词3", "禁词4", "禁词5"]
        # hit 2 -> penalty = 10 -> score = 10
        score, details = consistency.check_banned("这里包含禁词1和禁词2", banned)
        self.assertEqual(score, 10)
        self.assertTrue(any("命中 2 个" in d for d in details))

        # hit 5 -> penalty = 20 -> score = 0
        score2, details2 = consistency.check_banned("包含禁词1禁词2禁词3禁词4禁词5", banned)
        self.assertEqual(score2, 0)


class TestCheckImagery(unittest.TestCase):
    """测试意象 check_imagery。"""

    def test_imagery_scoring_levels(self):
        # 0 hits -> 3
        score, details = consistency.check_imagery("纯抽象议论", {})
        self.assertEqual(score, 3)

        # 1-2 hits -> 6 ("声音", "光线")
        score, details = consistency.check_imagery("听到了声音，看到了光线。", {})
        self.assertEqual(score, 6)

        # 3+ hits -> 10 ("声音", "光线", "植物")
        score, details = consistency.check_imagery("听到了声音，看到了光线，抚摸着植物。", {})
        self.assertEqual(score, 10)

    def test_custom_asset_domains(self):
        imagery_cfg = {
            "high_freq_metaphor_domains": ["星辰大海", "荒芜废土"]
        }
        score, details = consistency.check_imagery("漫步在星辰大海与荒芜废土之中，吹着风。", imagery_cfg)
        self.assertEqual(score, 10)
        self.assertTrue(any("含资产领域 2 个" in d for d in details))


class TestScoreText(unittest.TestCase):
    """测试 score_text 完整多维打分接口。"""

    def test_score_text_structure_and_integration(self):
        voice_card = {
            "dialogue": {
                "character_voices": [
                    {
                        "name": "李云",
                        "speech_signature": {"verbal_tics": ["绝不"]}
                    }
                ]
            },
            "emotion_handling": {"body_reaction_vocabulary": ["手心冒汗"]},
            "narration": {"pov": "第三人称"},
            "banned_words": None,
            "imagery": {"high_freq_metaphor_domains": ["星宿"]}
        }
        text = (
            "他叫李云。\n\n"
            "「绝不！」\n\n"
            "手心冒汗。\n"
            "心跳加速。\n"
            "呼吸困难。\n"
            "抬头看星宿。"
        )
        total_score, details, raw = consistency.score_text(voice_card, text, label="第一章")
        self.assertIsInstance(total_score, (int, float))
        self.assertIsInstance(details, list)
        self.assertIn("voice", raw)
        self.assertIn("emotion", raw)
        self.assertIn("narration", raw)
        self.assertIn("banned", raw)
        self.assertIn("imagery", raw)
        self.assertIn("voice_details", raw)
        self.assertTrue(any("第一章" in d for d in details))


class TestConsistencyCheckAndCLI(unittest.TestCase):
    """测试 consistency_check 与 main CLI 入口。"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmppath = Path(self.tmpdir.name)
        self.vc_file = self.tmppath / "voice-card.json"
        self.ch_file = self.tmppath / "chapter.txt"

        vc_data = {
            "dialogue": {
                "character_voices": [
                    {
                        "name": "主角",
                        "speech_signature": {"verbal_tics": ["休想"]}
                    }
                ]
            },
            "emotion_handling": {},
            "narration": {},
            "banned_words": [],
            "imagery": {}
        }
        self.vc_file.write_text(json.dumps(vc_data, ensure_ascii=False), encoding="utf-8")
        self.ch_file.write_text("主角站在门前大喊：休想！他心跳剧烈，呼吸急促，手心冒汗，喉咙发紧。看着天上的云和月光。\n\n风很大\n路很长\n天很冷", encoding="utf-8")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_consistency_check_quiet_and_verbose(self):
        # quiet=True 应不向 stdout 输出
        f = io.StringIO()
        with mock.patch("sys.stdout", f):
            res = consistency.consistency_check(str(self.vc_file), str(self.ch_file), quiet=True)
        self.assertEqual(f.getvalue(), "")
        self.assertIn("score", res)
        self.assertIn("voice", res)

        # quiet=False 应有控制台报告
        f_verbose = io.StringIO()
        with mock.patch("sys.stdout", f_verbose):
            res_verbose = consistency.consistency_check(str(self.vc_file), str(self.ch_file), quiet=False)
        out = f_verbose.getvalue()
        self.assertIn("=== 风格一致性自检 ===", out)
        self.assertIn("总分:", out)

    def test_main_cli_pass_and_fail(self):
        # 默认 PASS 阈值 75，本章应高分通过返回 0
        ret_pass = consistency.main([str(self.vc_file), str(self.ch_file), "-q"])
        self.assertEqual(ret_pass, 0)

        # 提高阈值至 99.9，应未达标返回 1
        ret_fail = consistency.main([str(self.vc_file), str(self.ch_file), "--threshold", "99.9", "-q"])
        self.assertEqual(ret_fail, 1)

    def test_main_cli_json_output(self):
        f = io.StringIO()
        with mock.patch("sys.stdout", f):
            code = consistency.main([str(self.vc_file), str(self.ch_file), "--json"])
        self.assertEqual(code, 0)
        data = json.loads(f.getvalue())
        self.assertTrue(data["pass"])
        self.assertEqual(data["threshold"], 75.0)
        self.assertIn("score", data)
        self.assertIn("voice", data)


if __name__ == "__main__":
    unittest.main()
