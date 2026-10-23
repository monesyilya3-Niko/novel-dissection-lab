#!/usr/bin/env python3
"""单章 12 维质量检测与连续打分引擎（scripts/chapter_check.py）全维独立测试套件。

遵循纯 Python 标准库，零第三方依赖（铁律三）。
全面覆盖：
1. 线性分段插值与格式化辅助（_ramp 边界与插值、_score1 浮点防噪、_fmt_score 规范输出）；
2. 12 维质量检测算法（字数、对话占比、章末钩子、开头吸引力、情绪密度、直陈式情绪词、
   段落节奏、结构完整性、AI味、疲劳词、让字专项、情绪标签词）；
3. 对话区间与评分阈值解析（resolve_dialogue_band / resolve_thresholds 题材包覆盖与安全回退）；
4. 综合质检与守卫（chapter_check PASS/WARN/FAIL 判定与 P0-1 逐维上限守卫）；
5. 命令行接口（CLI 帮助、参数解析、纯文本及 JSON 结构化输出）。
"""

from __future__ import annotations

import io
import json
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

import chapter_check as cc  # noqa: E402


class TestChapterCheckInterpolationAndFormat(unittest.TestCase):
    """测试底层分段插值与格式化辅助函数。"""

    def test_ramp_degenerate(self):
        # x1 <= x0 退化分支
        self.assertEqual(cc._ramp(10.0, 5.0, 5.0, 1.0, 2.0), 2.0)
        self.assertEqual(cc._ramp(4.0, 5.0, 5.0, 1.0, 2.0), 1.0)
        self.assertEqual(cc._ramp(3.0, 6.0, 4.0, 0.0, 5.0), 0.0)

    def test_ramp_clamping(self):
        # x <= x0 夹紧到 y0
        self.assertEqual(cc._ramp(2.0, 5.0, 10.0, 10.0, 20.0), 10.0)
        # x >= x1 夹紧到 y1
        self.assertEqual(cc._ramp(15.0, 5.0, 10.0, 10.0, 20.0), 20.0)

    def test_ramp_interpolation(self):
        # 区间内线性映射
        # 中点: x=7.5 -> y=15.0
        val = cc._ramp(7.5, 5.0, 10.0, 10.0, 20.0)
        self.assertAlmostEqual(val, 15.0)

        # 逆向斜率 (从大到小)
        val_inv = cc._ramp(7.5, 5.0, 10.0, 20.0, 10.0)
        self.assertAlmostEqual(val_inv, 15.0)

    def test_score1(self):
        self.assertEqual(cc._score1(7.44), 7.4)
        self.assertEqual(cc._score1(7.46), 7.5)
        self.assertEqual(cc._score1(8.0), 8.0)

    def test_fmt_score(self):
        self.assertEqual(cc._fmt_score(8.0), "8")
        self.assertEqual(cc._fmt_score(7.5), "7.5")
        self.assertEqual(cc._fmt_score(7.40000000001), "7.4")


class TestChapterCheckDimensions(unittest.TestCase):
    """测试 12 维质量检测各个独立子算法。"""

    def test_check_word_count_ranges(self):
        # ≥1500 满分 8.0
        score, label = cc.check_word_count("这是一段合格字数的正文测试文本。" * 100)
        self.assertEqual(score, 8.0)
        self.assertIn("✓", label)

        # 1200 ~ 1500 字，略短
        text_1300 = "这是略短的一千三百字正文段落测试。" * 75
        score, label = cc.check_word_count(text_1300)
        self.assertTrue(6.0 <= score <= 8.0)
        self.assertIn("略短", label)

        # 1000 ~ 1200 字，偏短
        text_1100 = "这是偏短的一千一百字正文段落测试。" * 65
        score, label = cc.check_word_count(text_1100)
        self.assertTrue(3.0 <= score <= 6.0)
        self.assertIn("偏短", label)

        # < 1000 字，严重不足
        text_500 = "这是字数严重不足的短篇文本测试。" * 30
        score, label = cc.check_word_count(text_500)
        self.assertTrue(0.0 <= score <= 3.0)
        self.assertIn("严重不足", label)

    def test_resolve_dialogue_band(self):
        # 默认回退
        self.assertEqual(cc.resolve_dialogue_band(None), cc.DEFAULT_DIALOGUE_BAND)
        self.assertEqual(cc.resolve_dialogue_band("invalid"), cc.DEFAULT_DIALOGUE_BAND)
        self.assertEqual(cc.resolve_dialogue_band({}), cc.DEFAULT_DIALOGUE_BAND)

        # commercial.quality_thresholds.dialogue_optimal 优先
        pack_commercial = {
            "commercial": {
                "quality_thresholds": {
                    "dialogue_optimal": {"min": 0.20, "max": 0.35}
                }
            }
        }
        self.assertEqual(cc.resolve_dialogue_band(pack_commercial), (0.20, 0.35))

        # 顶层 quality_thresholds.dialogue_optimal 覆盖
        pack_top = {
            "quality_thresholds": {
                "dialogue_optimal": {"min": 0.18, "max": 0.42}
            }
        }
        self.assertEqual(cc.resolve_dialogue_band(pack_top), (0.18, 0.42))

        # 非法数值安全回退（如 min >= max，布尔类型或越界）
        bad_packs = [
            {"commercial": {"quality_thresholds": {"dialogue_optimal": {"min": 0.5, "max": 0.4}}}},
            {"commercial": {"quality_thresholds": {"dialogue_optimal": {"min": True, "max": 0.4}}}},
            {"commercial": {"quality_thresholds": {"dialogue_optimal": {"min": -0.1, "max": 0.5}}}},
            {"commercial": {"quality_thresholds": {"dialogue_optimal": {"min": 0.2, "max": 1.2}}}},
        ]
        for bad in bad_packs:
            self.assertEqual(cc.resolve_dialogue_band(bad), cc.DEFAULT_DIALOGUE_BAND)

    def test_check_dialogue_ratio_ranges(self):
        # 无文本
        self.assertEqual(cc.check_dialogue_ratio(""), (0, "无文本"))

        # 合适对话比例（25% 落在默认 0.15 ~ 0.40 区间内，满分 12.0）
        narrative = "窗外的落叶纷纷扬扬落下，街道两旁的行人行色匆匆。" * 6
        dialogue = "“这件事情究竟是谁做的，你能不能跟我说个实话？”他开口问道。“我真的完全不知道，你不要再逼我了行不行？”她回答。" * 2
        balanced_text = narrative + dialogue
        score, label = cc.check_dialogue_ratio(balanced_text)
        self.assertEqual(score, 12.0)
        self.assertIn("✓", label)

        # 几乎无对话（纯叙述）
        score_none, label_none = cc.check_dialogue_ratio(narrative)
        self.assertTrue(score_none <= 2.0)
        self.assertIn("几乎无对话", label_none)

        # 对话过多（纯台词）
        pure_dialogue = "“你好！”“你好呀！”“今天吃了吗？”“吃过了，你呢？”“我也吃了。”" * 20
        score_over, label_over = cc.check_dialogue_ratio(pure_dialogue)
        self.assertTrue(score_over <= 4.0)
        self.assertIn("对话过多", label_over)

    def test_check_hook_patterns(self):
        # 有效收束 + 3类关键词 -> 满分 12.0
        # 关键词：突然(突发)、她不知道(悬念)、站起(动作)、但是(转折)
        good_tail = "远处的天空渐渐暗了下来。突然之间，雷声轰鸣。她不知道明天究竟会如何，猛然站起身来。但是风暴已经无法停止了！"
        score, label = cc.check_hook("正文前情提要铺垫。" * 20 + good_tail)
        self.assertEqual(score, 12.0)
        self.assertIn("12.0/12", label)
        self.assertIn("hits=", label)

        # 截断风险（末尾无标点且长度 > 4 扣 3 分）
        truncated_tail = "窗外风吹树摇，他猛然回头看着门外没有写完的半句话"
        score_trunc, label_trunc = cc.check_hook(truncated_tail)
        self.assertIn("trunc=1", label_trunc)

        # 英文钩子模式支持 (Suddenly / didn't know / turned around)
        en_tail = "The night grew colder. Suddenly without warning, he didn't know what tomorrow would bring and stepped forward."
        score_en, label_en = cc.check_hook(en_tail)
        self.assertTrue(score_en >= 6.0)

    def test_check_opening_aspects(self):
        # 涵盖场景建立、冲突引入、对话开场、动作开场 (满分 8 分)
        opening_text = '“快点收拾东西！”他在教室里焦急地喊道。矛盾瞬间爆发，大家神色慌张，她一把抓起书包往外跑。'
        score, label = cc.check_opening(opening_text + "后续平静叙述。" * 30)
        self.assertEqual(score, 8)
        self.assertIn("场景建立", label)
        self.assertIn("冲突引入", label)
        self.assertIn("对话开场", label)
        self.assertIn("动作开场", label)

        # 缺失开场元素的平淡开头
        dull_opening = "天气很好，天空很蓝。时间在一分一秒地过去。一切都很安静。"
        score_dull, _ = cc.check_opening(dull_opening)
        self.assertTrue(score_dull <= 2)

    def test_check_emotion_density(self):
        # 无文本
        self.assertEqual(cc.check_emotion_density(""), (0, "无文本"))

        # 每 400 字至少 1 处体感词（心跳、指尖、呼吸、脊背）
        dense_text = (
            "指尖微微发凉，心跳声在寂静的房间里格外清晰。呼吸渐渐急促，脊背泛起一阵寒意。" * 5
        )
        score, label = cc.check_emotion_density(dense_text)
        self.assertEqual(score, 12.0)
        self.assertIn("✓", label)

        # 缺少体感词的纯客观叙述
        sparse_text = "桌子上放着一本书，旁边有一支钢笔。墙壁被刷成白色，窗帘是蓝色的。" * 30
        score_sparse, label_sparse = cc.check_emotion_density(sparse_text)
        self.assertTrue(score_sparse < 8.0)
        self.assertTrue("严重不足" in label_sparse or "少" in label_sparse)

    def test_check_direct_emotion(self):
        # 零出现满分 8
        clean_text = "他的声音很平静，眼底闪过一丝冷意。"
        self.assertEqual(cc.check_direct_emotion(clean_text), (8, "直陈式情绪词 0 ✓"))

        # 出现 1~2 处扣分
        mild_text = "他很愤怒地看着对方，心里感到害怕。"
        score_mild, label_mild = cc.check_direct_emotion(mild_text)
        self.assertTrue(4.0 <= score_mild < 8.0)
        self.assertIn("扣", label_mild)

        # 严重直陈情绪词堆砌
        heavy_text = "他很愤怒，非常开心，感到难过，又很伤心，非常生气。"
        score_heavy, label_heavy = cc.check_direct_emotion(heavy_text)
        self.assertTrue(score_heavy <= 2.0)
        self.assertIn("严重扣分", label_heavy)

    def test_check_paragraph_rhythm(self):
        # 无段落
        self.assertEqual(cc.check_paragraph_rhythm(""), (0, "无段落"))

        # 短段 (<=15字) 比例在 10%~40% 之间，2/10 = 20%，得满分 8.0
        paras = [
            "夜色如浓稠的墨汁般在天际散开，整座城市陷入了长久的沉寂之中。",
            "路灯在秋风中微微晃动，昏黄的光晕洒在湿漉漉的青石板街道上。",
            "空气中弥漫着潮湿的泥土清香与初冬逼人的寒意，让人忍不住打个寒战。",
            "黑暗中并没有人回答他的问询，只有远处的汽笛在空旷的港口呜咽。",
            "他静静地站在原地等待着对方的回应，神色严峻而警惕。",
            "远处的钟楼敲响了十二下，沉重的钟声在夜空中久久回荡。",
            "街道尽头驶来一辆黑色的汽车，车灯划破了长久的漆黑。",
            "车门缓缓打开，从里面走出来一个身穿黑色风衣的神秘男子。",
            "风起了。",
            "走吧。",
        ]
        score, label = cc.check_paragraph_rhythm("\n\n".join(paras))
        self.assertEqual(score, 8.0)
        self.assertIn("✓", label)

    def test_check_structure(self):
        # 段落过少
        self.assertEqual(cc.check_structure("只有一段话"), (0, "段落过少"))

        # 完整三段式结构 (开头 > 50字，中段发展 > 100字，收束 > 30字且有标点)
        p_open = ["这是开头的第一个段落，用来介绍人物背景与登场环境，建立起最初的氛围感与叙事基调。" * 2]
        p_mid = [
            "随着剧情推进，主要矛盾开始显现出来，双方在争辩中逐步暴露出各自真正的意图与筹码。" * 2,
            "局势急转直下，突如其来的意外变故让原本平静的谈判彻底陷入僵局，危机一触即发。" * 2,
        ]
        p_end = ["最终尘埃落定，远处的夕阳将两人的影子拉得很长很长，未来的路依然充满变数。"]

        all_paras = p_open + p_mid + p_end
        score, label = cc.check_structure("\n\n".join(all_paras))
        self.assertEqual(score, 8)
        self.assertIn("有开头", label)
        self.assertIn("有发展", label)
        self.assertIn("有收束", label)

    def test_check_ai_tics(self):
        # 干净文本满分 4 分
        clean_text = "他端起茶杯喝了一口，没有多说什么。"
        score, label = cc.check_ai_tics(clean_text)
        self.assertEqual(score, 4)
        self.assertIn("无 ✓", label)

        # 命中 AI 味模板句式
        ai_text = "她不知道，这一去将会彻底改变命运。像一道小小的伤口，镀了一层很薄的金色。"
        score_ai, label_ai = cc.check_ai_tics(ai_text)
        self.assertTrue(score_ai < 4)
        self.assertIn("模板", label_ai)

    def test_check_fatigue_words(self):
        # 无文本
        self.assertEqual(cc.check_fatigue_words(""), (0, "无文本"))

        # 正常文本
        clean = "清晨的阳光透过窗棂洒在桌上，少年执卷默读，神情专注而沉静。" * 10
        score, label = cc.check_fatigue_words(clean)
        self.assertEqual(score, 8.0)
        self.assertIn("✓", label)

        # 严重疲劳词："了"字密度超标，大量连接词与感叹词
        fatigue = "他吃了饭了，看了书了，走了路了，睡了觉了，开了门了，笑了哭了。" * 20
        fatigue += " 突然，忽然间，就在这时，正在这时，忽然又来了。" * 5
        score_f, label_f = cc.check_fatigue_words(fatigue)
        self.assertTrue(score_f < 6.0)
        self.assertIn("了字密度", label_f)

    def test_check_rang_character(self):
        # 密度 <= 1 满分 5
        clean = "少年手握长剑，剑尖微颤，目光如电般扫过全场。" * 20
        self.assertEqual(cc.check_rang_character(clean)[0], 5)

        # 让字密度过高 (AI味重灾区)
        heavy_rang = "这件事情让他感到疑惑，让他心烦意乱，让他不知所措，让他想要逃离。" * 10
        score, label = cc.check_rang_character(heavy_rang)
        self.assertTrue(score <= 3.0)
        self.assertIn("过多", label)

    def test_check_emotion_tags(self):
        # 0 处旁白情绪标签满分 7
        clean = "天色昏暗，风雨交加。"
        self.assertEqual(cc.check_emotion_tags(clean)[0], 7)

        # 滥用旁白情绪标签
        heavy_tags = "她觉得很难过，她意识到危险在靠近，她内心十分痛苦，她忽然感到一切都完了。" * 3
        score, label = cc.check_emotion_tags(heavy_tags)
        self.assertTrue(score <= 4.0)
        self.assertIn("情绪标签", label)


class TestChapterCheckAggregateAndGuards(unittest.TestCase):
    """测试综合判定、阈值解析与单维上限守卫。"""

    def test_resolve_thresholds(self):
        # 默认 75 / 60
        self.assertEqual(cc.resolve_thresholds(None), (75, 60))
        self.assertEqual(cc.resolve_thresholds({}), (75, 60))

        # 题材包合法配置覆盖
        pack = {
            "commercial": {
                "quality_thresholds": {"pass": 82, "warn": 68}
            }
        }
        self.assertEqual(cc.resolve_thresholds(pack), (82, 68))

        # 异常配置（如 warn > pass 或类型非 int）安全回退
        bad_pack = {"commercial": {"quality_thresholds": {"pass": 60, "warn": 80}}}
        self.assertEqual(cc.resolve_thresholds(bad_pack), (75, 60))

        # pass == warn 允许
        equal_pack = {"commercial": {"quality_thresholds": {"pass": 70, "warn": 70}}}
        self.assertEqual(cc.resolve_thresholds(equal_pack), (70, 70))

    def test_chapter_check_pass_text(self):
        # 构建一篇高分规范章节
        p1 = '“你终于来了。”林羽推开教室的门，神色严峻地看着眼前的少年。“出了什么事？”'
        p2 = "窗外的秋风呼啸而过，卷起地上的枯黄落叶。两人的呼吸在略显沉重的气氛中交织，指尖微微有些发凉。"
        p3 = "长久的沉默在房间里蔓延。他将手中的卷宗递过去，低声解释着最近一系列怪事的来龙去脉与隐藏在背后的端倪。" * 8
        p4 = "局势远比他们预想的要复杂得多。不仅涉及城西的古老传闻，更牵扯到多方势力的明争暗斗与暗中博弈。" * 8
        p5 = "“无论如何，今晚必须查明真相。”林羽站起身来，目光坚定地望向窗外渐浓的夜色。但是风暴已经逼近了！"

        full_chapter = "\n\n".join([p1, p2, p3, p4, p5])
        res = cc.chapter_check(full_chapter)

        self.assertIn("score", res)
        self.assertIn("max_score", res)
        self.assertEqual(res["max_score"], 100)
        self.assertEqual(res["verdict"], "PASS")
        self.assertGreaterEqual(res["score"], 75.0)
        self.assertEqual(len(res["details"]), 12)

    def test_chapter_check_fail_text(self):
        # 极差的空文本或超短断头文本 -> FAIL
        bad_text = "几句话断头没有收尾"
        res = cc.chapter_check(bad_text)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertLess(res["score"], 60.0)
        self.assertGreaterEqual(len(res["issues"]), 1)

    def test_dimension_count_and_cap_guards(self):
        # P0-1 维度上限防漂移防超发测试
        # 当某维度模拟打出超过自身权重的分数时，必须坚决抛出 RuntimeError
        with patch.object(cc, "check_word_count", return_value=(9.0, "溢出超发")):
            with self.assertRaises(RuntimeError) as cm:
                cc.chapter_check("测试正文")
            self.assertIn("word_count", str(cm.exception))
            self.assertIn("超过其权重上限", str(cm.exception))


class TestChapterCheckCLI(unittest.TestCase):
    """测试命令行接口 CLI 行为与退出码。"""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="cc_cli_test_"))

    def test_cli_file_not_found(self):
        f = io.StringIO()
        with patch("sys.stderr", f):
            with patch("sys.argv", ["chapter_check.py", str(self._tmp / "nonexistent.txt")]):
                exit_code = cc.main()
                self.assertEqual(exit_code, 1)
                self.assertIn("文件不存在", f.getvalue())

    def test_cli_text_and_json_output(self):
        # 准备一个标准章节文件
        ch_file = self._tmp / "test_chapter.txt"
        sample_text = (
            '“开门！”他猛地推开大门，走廊里回荡着沉闷的脚步声。\n\n'
            '心跳声在胸口剧烈跳动，指尖因过度用力而微微发白。\n\n'
            + "事情的起因还要从上个月的那场罕见大雨说起，整个过程扑朔迷离充满疑点。" * 12 + "\n\n"
            + "夜色深沉，前方的灯火若隐若现。他深吸了一口气，猛然回头望去。但是答案究竟在哪里？"
        )
        ch_file.write_text(sample_text, encoding="utf-8")

        # 1. 文本输出模式
        f_out = io.StringIO()
        with patch("sys.stdout", f_out):
            with patch("sys.argv", ["chapter_check.py", str(ch_file)]):
                exit_code = cc.main()
                self.assertIn(exit_code, (0, 1))
        text_res = f_out.getvalue()
        self.assertIn("章节质量检查: test_chapter.txt", text_res)
        self.assertIn("总分:", text_res)

        # 2. JSON 模式
        f_json = io.StringIO()
        with patch("sys.stdout", f_json):
            with patch("sys.argv", ["chapter_check.py", str(ch_file), "--json"]):
                exit_code = cc.main()
                self.assertIn(exit_code, (0, 1))
        parsed = json.loads(f_json.getvalue())
        self.assertIn("score", parsed)
        self.assertIn("verdict", parsed)
        self.assertIn("details", parsed)

    def test_cli_with_explicit_argv(self):
        ch_file = self._tmp / "explicit_chapter.txt"
        ch_file.write_text("“开门！”他大步向前，心跳如鼓。夜色深沉。", encoding="utf-8")
        f_json = io.StringIO()
        with patch("sys.stdout", f_json):
            exit_code = cc.main([str(ch_file), "--json"])
            self.assertIn(exit_code, (0, 1))
        parsed = json.loads(f_json.getvalue())
        self.assertIn("score", parsed)


if __name__ == "__main__":
    unittest.main()
