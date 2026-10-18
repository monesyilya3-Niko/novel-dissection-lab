"""全书内容质检引擎（book_quality.py）全维独立测试套件。

覆盖维度：
1. 跨章重复检测（check_duplicate_chapters / check_duplicate_paragraphs / check_duplicate_sentences）
2. 章内碎片与重复句检测（_fragment_repeat_ratio / check_intra_chapter_repeats / 样本保护门槛）
3. 情节连贯性（check_plot_continuity：时间线混乱 / 情绪矛盾）
4. 文笔风格一致性（check_style_consistency：比喻密度突增 / 情绪写法模式漂移）
5. 凑字数与乱编检测（check_word_padding / check_fabrication：实体表驱动人名错误 / 数字矛盾）
6. AI味模板检测（check_ai_flavor 8类模式）
7. 覆盖率与截断指示（_voice_card_mode / _book_quality_coverage / format_truncation_hint）
8. 综合质检入口与 CLI（book_quality_check / main：错误处理 / 截断 / 实体表探测 / verdict 裁决）
"""
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
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import book_quality
import chapter_loader


class TestDuplicateDetection(unittest.TestCase):
    """跨章重复检测测试集（整章/段落/句子）。"""

    def test_check_duplicate_chapters(self):
        # 构造两章中段内容几乎完全一致的文本（长度各 >= 300字）
        filler_head = "这是一段长篇小说的初始开场白，交代背景故事与环境。" * 10
        mid_content = "关键的情节转折点发生了，暴风雨突然降临在大地之上，所有人都感到前所未有的震撼与不安。" * 8
        filler_tail = "最终夜幕完全降临，大家各自回到房间休息，等待着明天的到来。" * 10

        ch1_text = filler_head + mid_content + filler_tail
        ch2_text = filler_head + mid_content + filler_tail
        texts = {1: ch1_text, 2: ch2_text}

        issues = book_quality.check_duplicate_chapters(texts)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["type"], "duplicate_chapter")
        self.assertEqual(issues[0]["severity"], "critical")
        self.assertEqual(issues[0]["chapters"], [1, 2])
        self.assertGreater(issues[0]["similarity"], 0.7)

        # 文本过短（中段 < 100 字）跳过检测
        short_texts = {1: "短章一内容", 2: "短章二内容"}
        self.assertEqual(book_quality.check_duplicate_chapters(short_texts), [])

        # 内容不同不应报警
        diff_texts = {
            1: filler_head + mid_content + filler_tail,
            2: filler_head + "截然不同的一段情节故事发展，充满欢声笑语和阳光。" * 8 + filler_tail,
        }
        self.assertEqual(book_quality.check_duplicate_chapters(diff_texts), [])

    def test_check_duplicate_paragraphs(self):
        long_para = "这是一个超过三十个字的完全重复段落，在不同的章节中被作者无意识地直接复制粘贴使用了。"
        short_para = "这是短段落重复。"
        texts = {
            1: f"第一章引言。\n{long_para}\n{short_para}\n第一章结语。",
            2: f"第二章开启。\n{long_para}\n{short_para}\n第二章结语。",
        }
        issues = book_quality.check_duplicate_paragraphs(texts)
        # 仅长段落 (>30字) 报警，短段落被忽略
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["type"], "duplicate_paragraph")
        self.assertEqual(issues[0]["severity"], "high")
        self.assertEqual(issues[0]["chapters"], [1, 2])
        self.assertIn(long_para[:20], issues[0]["detail"])

    def test_check_duplicate_sentences(self):
        sent1 = "清晨的微风轻轻吹拂着古老的银杏树叶。"  # >12字
        sent2 = "远处的钟楼传来了沉闷而悠扬的九声钟响。"  # >12字

        # 相邻两章重复 -> severity=low, adjacent=True
        texts_adjacent = {
            1: f"开始。{sent1}结束。",
            2: f"第二章。{sent1}结尾。",
        }
        issues = book_quality.check_duplicate_sentences(texts_adjacent)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["type"], "duplicate_sentence")
        self.assertEqual(issues[0]["severity"], "low")
        self.assertTrue(issues[0]["adjacent"])
        self.assertIn("（相邻章）", issues[0]["detail"])

        # 非相邻两章重复 (Ch1 与 Ch3) -> adjacent=False
        texts_non_adjacent = {
            1: f"开始。{sent1}结束。",
            3: f"第三章。{sent1}结尾。",
        }
        issues_na = book_quality.check_duplicate_sentences(texts_non_adjacent)
        self.assertEqual(len(issues_na), 1)
        self.assertEqual(issues_na[0]["severity"], "low")
        self.assertFalse(issues_na[0]["adjacent"])
        self.assertNotIn("（相邻章）", issues_na[0]["detail"])

        # 跨 >=3 章重复 -> severity=medium
        texts_three = {
            1: f"第一章。{sent2}结束。",
            2: f"第二章。{sent2}继续。",
            4: f"第四章。{sent2}结尾。",
        }
        issues_three = book_quality.check_duplicate_sentences(texts_three)
        self.assertEqual(len(issues_three), 1)
        self.assertEqual(issues_three[0]["severity"], "medium")
        self.assertTrue(issues_three[0]["adjacent"])  # 1 和 2 是相邻的


class TestFragmentRepeatAndIntraChapter(unittest.TestCase):
    """无标点碎片重复与章内重复测试集。"""

    def test_fragment_repeat_ratio(self):
        # 1. 文本长度小于 2 * ngram -> 返回 (0.0, "")
        ratio, sample = book_quality._fragment_repeat_ratio("短文本", ngram=20)
        self.assertEqual(ratio, 0.0)
        self.assertEqual(sample, "")

        # 2. 汉字数不足 12 或字符种类少于 4
        all_same = "甲" * 50
        ratio, _ = book_quality._fragment_repeat_ratio(all_same, ngram=20)
        self.assertEqual(ratio, 0.0)

        # 3. 构造有效重复片段（20字，且重复间隔足够）
        fragment = "苍茫天地之间唯有一柄孤剑静静横陈在石台之上"  # 21字，均为汉字，种类丰富
        pad1 = "天色渐暗四周风声萧萧落叶漫天飘零飞向远方大地"
        pad2 = "深山古刹钟声沉闷响起惊醒了林间无数栖息飞鸟"
        pad3 = "大河滔滔奔流向东流入大海掀起万丈白茫巨浪"
        full_text = pad1 + fragment + pad2 + fragment + pad3 + fragment
        ratio, sample = book_quality._fragment_repeat_ratio(full_text, ngram=20)
        self.assertGreater(ratio, 0.0)
        self.assertLessEqual(ratio, 1.0)
        self.assertIn("苍茫天地", sample)

    def test_check_intra_chapter_repeats(self):
        # 1. 无重复清洁文本
        clean_text = "这是第一句话，描述风景很美。" + "这是第二句话，讲述行人的匆忙。" + "第三句话则是夜色深沉后的安静。"
        self.assertEqual(book_quality.check_intra_chapter_repeats({1: clean_text}), [])

        # 2. 句读重复，但样本过小 (< MIN_SAMPLE_SENTS_FOR_RATIO = 8) -> low_sample=True, severity="low"
        repeat_sent = "这一柄绝世神剑在月光下闪烁着冰冷的寒芒。"
        short_sents = [repeat_sent, repeat_sent, "第三句正常的描述情节句子。"]
        text_small = "。".join(short_sents) + "。"
        issues_small = book_quality.check_intra_chapter_repeats({1: text_small})
        self.assertEqual(len(issues_small), 1)
        self.assertEqual(issues_small[0]["severity"], "low")
        self.assertTrue(issues_small[0]["low_sample"])
        self.assertEqual(issues_small[0]["source"], "句")

        # 3. 句读重复，样本充足 (>= 8句)，且重复占比高 (>= 25%) -> severity="high"
        sents_high = [repeat_sent] * 4 + [f"这是第{i}个不同填充句子用于扩充样本基数。" for i in range(8)]
        text_high = "。".join(sents_high) + "。"
        issues_high = book_quality.check_intra_chapter_repeats({1: text_high})
        self.assertEqual(len(issues_high), 1)
        self.assertEqual(issues_high[0]["severity"], "high")
        self.assertFalse(issues_high[0]["low_sample"])

        # 4. 句读重复，样本充足，重复占比中等 (10% <= ratio < 25%) -> severity="medium"
        # 16句中有2句重复 (dup=1/16 = 6.25% < 10% -> low; 如果 10 句中有 2 句重复 dup=1/10=10% -> medium)
        sents_med = [repeat_sent, repeat_sent] + [f"这是第{i}个独一无二的风景叙述句子呀。" for i in range(8)]
        text_med = "。".join(sents_med) + "。"
        issues_med = book_quality.check_intra_chapter_repeats({1: text_med})
        self.assertEqual(len(issues_med), 1)
        self.assertEqual(issues_med[0]["severity"], "medium")

        # 5. 纯碎片重复（无句读分句，长文本且紧凑字数 >= 200） -> source="碎片"
        frag = "九霄云外狂风大作群山峻岭在一瞬间崩塌瓦解化为乌有"
        pad = "天地初开混沌未分宇宙洪荒浩瀚无垠日月星辰流转不息" * 3
        text_frag = pad + frag + pad + frag + pad + frag
        issues_frag = book_quality.check_intra_chapter_repeats({1: text_frag})
        self.assertEqual(len(issues_frag), 1)
        self.assertEqual(issues_frag[0]["source"], "碎片")


class TestPlotContinuity(unittest.TestCase):
    """情节连贯性检测测试集。"""

    def test_timeline_contradiction(self):
        # "第二天" 出现 >= 4 次 -> timeline_contradiction
        bad_text = "到了第二天清晨，他启程了。次日傍晚，又发生了大战。隔天拂晓，敌人退兵。第二天夜里，大家庆祝。"
        issues = book_quality.check_plot_continuity({1: bad_text})
        self.assertTrue(any(i["type"] == "timeline_contradiction" for i in issues))
        issue = [i for i in issues if i["type"] == "timeline_contradiction"][0]
        self.assertEqual(issue["severity"], "medium")
        self.assertEqual(issue["chapter"], 1)

        # 正常文本出现 1-2 次时间推进词不报警
        ok_text = "第二天清晨，队伍整装待发，开启了新的旅程。"
        issues_ok = book_quality.check_plot_continuity({1: ok_text})
        self.assertFalse(any(i["type"] == "timeline_contradiction" for i in issues_ok))

    def test_mood_contradiction(self):
        # 紧张词 >= 3 且 平静词 >= 3 -> mood_contradiction, severity="low"
        mixed_text = (
            "他内心极度紧张、害怕又恐惧，甚至充满了焦虑。"
            "然而片刻之后，他又感到异常放松，神色平静，内心极为安心从容。"
        )
        issues = book_quality.check_plot_continuity({1: mixed_text})
        self.assertTrue(any(i["type"] == "mood_contradiction" for i in issues))
        issue = [i for i in issues if i["type"] == "mood_contradiction"][0]
        self.assertEqual(issue["severity"], "low")

        # 仅紧张或仅平静不报错
        calm_only = "他坐在庭院中，神情放松，心情平静，格外安心从容。"
        issues_calm = book_quality.check_plot_continuity({1: calm_only})
        self.assertFalse(any(i["type"] == "mood_contradiction" for i in issues_calm))


class TestStyleConsistency(unittest.TestCase):
    """文笔风格一致性测试集。"""

    def test_metaphor_density_spike(self):
        # Ch1-3 正常比喻密度，Ch4 比喻密度超标 (> avg * 2.5)
        ch_normal = "山峰高耸入云，天边有云彩，他走在石板路上。" * 20  # 约400字，0 比喻
        ch_spike = "她的笑容如同春风，眼神宛如星辰，身形仿佛飞燕，话语好像甘霖，步履宛如浮云。" * 10  # 密集比喻
        texts = {1: ch_normal, 2: ch_normal, 3: ch_normal, 4: ch_spike}
        issues = book_quality.check_style_consistency(texts)
        self.assertTrue(any(i["type"] == "metaphor_density_spike" for i in issues))
        issue = [i for i in issues if i["type"] == "metaphor_density_spike"][0]
        self.assertEqual(issue["chapter"], 4)
        self.assertEqual(issue["severity"], "medium")

        # 纯英文或无中文字符章节不崩溃
        empty_texts = {1: "Hello world this is pure ascii text without chinese"}
        self.assertEqual(book_quality.check_style_consistency(empty_texts), [])

    def test_emotion_mode_drift(self):
        # voice_card 期望模式为 "体感白描"（非 "直陈式"）
        voice_card = {"emotion_handling": {"mode": "体感白描"}}
        # 直陈情绪词 >= 3 -> emotion_mode_drift
        drift_text = "他听到消息后感到难过，心中很伤心，而且感到害怕。"
        issues = book_quality.check_style_consistency({1: drift_text}, voice_card=voice_card)
        self.assertTrue(any(i["type"] == "emotion_mode_drift" for i in issues))
        issue = [i for i in issues if i["type"] == "emotion_mode_drift"][0]
        self.assertEqual(issue["severity"], "medium")

        # 如果 voice_card 期望模式就是 "直陈式" -> 不应报错
        voice_card_direct = {"emotion_handling": {"mode": "直陈式"}}
        issues_direct = book_quality.check_style_consistency({1: drift_text}, voice_card=voice_card_direct)
        self.assertFalse(any(i["type"] == "emotion_mode_drift" for i in issues_direct))

        # voice_card 为空或模式非字符串 -> 不应报错
        issues_none = book_quality.check_style_consistency({1: drift_text}, voice_card={})
        self.assertFalse(any(i["type"] == "emotion_mode_drift" for i in issues_none))


class TestWordPaddingAndFabrication(unittest.TestCase):
    """凑字数与乱编检测测试集。"""

    def test_check_word_padding(self):
        # 1. 段落重复 (长度 > 20 且在该章出现 >= 2 次)
        dup_p = "这是一个在同一章节之内重复出现的长描写段落文字内容。"
        ch_text = f"开篇情节。\n{dup_p}\n中间故事进展。\n{dup_p}\n结尾内容。"
        issues = book_quality.check_word_padding({1: ch_text})
        self.assertTrue(any(i["type"] == "paragraph_repeat" for i in issues))
        p_issue = [i for i in issues if i["type"] == "paragraph_repeat"][0]
        self.assertEqual(p_issue["severity"], "high")

        # 2. 环境描写占比过高 (> 40% 的非空段落)
        env_text = "\n".join([
            "窗外的雨水不停地落下。",
            "路灯在夜色中柔和地照。",
            "月光清冷地洒在庭院里。",
            "他站起身来准备出发去往城镇。",  # 唯一非环境描写段落 (3/4 = 75% > 40%)
        ])
        env_issues = book_quality.check_word_padding({1: env_text})
        self.assertTrue(any(i["type"] == "excessive_environment" for i in env_issues))
        e_issue = [i for i in issues if i["type"] == "paragraph_repeat"]
        self.assertIsNotNone(e_issue)

    def test_check_fabrication_entities(self):
        # 实体表定义：主名 "萧炎"，别名 "药老传人"
        entities = {
            "characters": [
                {"name": "萧炎", "aliases": ["药老传人"]}
            ]
        }
        # 出现别名 "药老传人" 但全章未出现正确主名 "萧炎" -> name_error
        bad_text = "只见那药老传人一步踏出，威震四方豪杰。"
        issues = book_quality.check_fabrication({1: bad_text}, entities=entities)
        self.assertTrue(any(i["type"] == "name_error" for i in issues))
        n_issue = [i for i in issues if i["type"] == "name_error"][0]
        self.assertEqual(n_issue["severity"], "medium")

        # 同时出现主名和别名 -> 正常无报警
        good_text = "萧炎微微一笑，众人皆知他便是名动天下的药老传人。"
        issues_good = book_quality.check_fabrication({1: good_text}, entities=entities)
        self.assertFalse(any(i["type"] == "name_error" for i in issues_good))

        # 无实体表 -> 跳过人名检查
        self.assertEqual(book_quality.check_fabrication({1: bad_text}, entities=None), [])

    def test_check_fabrication_number_contradiction(self):
        # 同一章内出现多个不同的 11 位手机号码 -> number_contradiction
        bad_phones = "他拨通了13800138000，但对方却让他改拨13900139000进行核验。"
        issues = book_quality.check_fabrication({1: bad_phones})
        self.assertTrue(any(i["type"] == "number_contradiction" for i in issues))
        issue = [i for i in issues if i["type"] == "number_contradiction"][0]
        self.assertEqual(issue["severity"], "high")

        # 相同手机号重复出现多次 -> 正常无报警
        ok_phones = "他反复核对13800138000这个号码，随后拨通了13800138000。"
        self.assertEqual(book_quality.check_fabrication({1: ok_phones}), [])


class TestAiFlavor(unittest.TestCase):
    """AI味痕迹检测测试集。"""

    def test_check_ai_flavor(self):
        ai_text = (
            "她不知道，接下来的日子里将会面临巨大变故。"
            "那一刻，她忽然明白了所有的真相。"
            "那个画面浮现在脑海深处久久不散。"
        )
        issues = book_quality.check_ai_flavor({1: ai_text})
        self.assertEqual(len(issues), 3)
        for issue in issues:
            self.assertEqual(issue["type"], "ai_flavor")
            self.assertEqual(issue["severity"], "medium")
            self.assertEqual(issue["chapter"], 1)

        # 真实自然文本 -> 无报警
        clean_text = "他拉开抽屉取出了地图，并在桌上铺平，借着烛火细细辨认山径。"
        self.assertEqual(book_quality.check_ai_flavor({1: clean_text}), [])


class TestCoverageAndTruncation(unittest.TestCase):
    """检测覆盖率元数据与输出截断测试集。"""

    def test_voice_card_mode(self):
        self.assertEqual(book_quality._voice_card_mode(None), "")
        self.assertEqual(book_quality._voice_card_mode("not a dict"), "")
        self.assertEqual(book_quality._voice_card_mode({}), "")
        self.assertEqual(book_quality._voice_card_mode({"emotion_handling": "invalid"}), "")
        self.assertEqual(book_quality._voice_card_mode({"emotion_handling": {"mode": 123}}), "")
        self.assertEqual(book_quality._voice_card_mode({"emotion_handling": {"mode": "白描"}}), "白描")

    def test_book_quality_coverage(self):
        # 1. 单章且无 voice_card 和 entities
        single_cov = book_quality._book_quality_coverage({1: "一章内容"})
        self.assertFalse(single_cov["entities_loaded"])
        self.assertFalse(single_cov["voice_card_loaded"])
        self.assertEqual(single_cov["chapters"], 1)
        self.assertIn("duplicate_chapters", single_cov["skipped"])
        self.assertIn("style_consistency", single_cov["skipped"])
        self.assertIn("fabrication_name", single_cov["skipped"])
        self.assertIn("仅 1 章", single_cov["skipped_reason"])

        # 2. 多章且有完整 entities 与 voice_card
        multi_cov = book_quality._book_quality_coverage(
            texts={1: "第一章", 2: "第二章"},
            entities={"characters": [{"name": "张三"}]},
            voice_card={"emotion_handling": {"mode": "白描"}},
        )
        self.assertTrue(multi_cov["entities_loaded"])
        self.assertTrue(multi_cov["voice_card_loaded"])
        self.assertEqual(multi_cov["chapters"], 2)
        self.assertEqual(multi_cov["skipped"], [])
        self.assertEqual(multi_cov["skipped_reason"], "")

    def test_format_truncation_hint(self):
        # 渲染数 >= 总数 -> 空串
        self.assertEqual(book_quality.format_truncation_hint(10, 10), "")
        self.assertEqual(book_quality.format_truncation_hint(5, 10), "")
        # 渲染数 < 总数 -> 提示信息
        hint = book_quality.format_truncation_hint(100, 15)
        self.assertEqual(hint, "⚠ 共 100 条，仅显示前 15 条")


class TestBookQualityCheckAndMain(unittest.TestCase):
    """主检查流程 book_quality_check 与 main CLI 测试集。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_bq_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_book_quality_check_missing_or_empty(self):
        # 不存在的目录
        non_existent = Path(self.temp_dir) / "no_such_dir"
        res = book_quality.book_quality_check(str(non_existent))
        self.assertIn("error", res)

        # 空目录
        empty_dir = Path(self.temp_dir) / "empty"
        empty_dir.mkdir()
        res_empty = book_quality.book_quality_check(str(empty_dir))
        self.assertIn("error", res_empty)

    def test_book_quality_check_chapter_loader_error(self):
        # 模拟 chapter_loader.load_chapter_texts 抛出 ChapterLoadError
        with mock.patch.object(book_quality.chapter_loader, "load_chapter_texts",
                               side_effect=chapter_loader.ChapterLoadError("chapters", 1, ["ch1_a.txt", "ch1_b.txt"])):
            res = book_quality.book_quality_check(self.temp_dir)
            self.assertEqual(res.get("error_type"), "chapter_load")
            self.assertIn("第1章", res.get("error"))

    def test_book_quality_check_voice_card_errors(self):
        # 创建一章常规内容
        ch1 = Path(self.temp_dir) / "chapter-001.txt"
        ch1.write_text("第一章内容开端。", encoding="utf-8")

        # 1. voice_card 路径不存在
        res_missing = book_quality.book_quality_check(str(self.temp_dir), voice_card_path="non_existent_vc.json")
        self.assertEqual(res_missing.get("error_type"), "voice_card_missing")

        # 2. voice_card 内容损坏
        corrupt_vc = Path(self.temp_dir) / "corrupt_vc.json"
        corrupt_vc.write_text("{bad json: 123", encoding="utf-8")
        res_corrupt = book_quality.book_quality_check(str(self.temp_dir), voice_card_path=str(corrupt_vc))
        self.assertEqual(res_corrupt.get("error_type"), "voice_card_unreadable")

    def test_book_quality_check_verdict_and_entities_detection(self):
        # 构建 novel_dir 结构自动探测 entities.json
        novel_dir = Path(self.temp_dir) / "my_novel"
        chapters_dir = novel_dir / "chapters"
        settings_dir = novel_dir / "settings"
        chapters_dir.mkdir(parents=True)
        settings_dir.mkdir(parents=True)

        entities_file = settings_dir / "entities.json"
        entities_file.write_text(json.dumps({
            "characters": [{"name": "萧峰", "aliases": ["南院大王"]}]
        }, ensure_ascii=False), encoding="utf-8")

        # 写入章节：包含名字别名孤立（产出 medium）、AI味（产出 medium）
        ch1 = chapters_dir / "chapter-001.txt"
        ch1.write_text("南院大王策马奔腾在广袤的草原之上。那一刻，她忽然明白了所有事情。", encoding="utf-8")
        ch2 = chapters_dir / "chapter-002.txt"
        ch2.write_text("第二章平静地开始了，没有任何问题与瑕疵。", encoding="utf-8")

        res = book_quality.book_quality_check(str(chapters_dir))
        self.assertEqual(res["total_chapters"], 2)
        self.assertIn("PASS", res["verdict"])  # 仅 medium/low -> PASS
        self.assertTrue(res["coverage"]["entities_loaded"])

        # 构造 critical 问题：整章内容重复
        ch2.write_text("南院大王策马奔腾在广袤的草原之上。那一刻，她忽然明白了所有事情。" * 10, encoding="utf-8")
        ch1.write_text("南院大王策马奔腾在广袤的草原之上。那一刻，她忽然明白了所有事情。" * 10, encoding="utf-8")
        res_crit = book_quality.book_quality_check(str(chapters_dir))
        self.assertEqual(res_crit["verdict"], "FAIL")

    def test_book_quality_check_issues_truncation(self):
        # 模拟生成超过 50 个问题以验证截断逻辑
        ch1 = Path(self.temp_dir) / "chapter-001.txt"
        ch1.write_text("第一章纯洁内容。", encoding="utf-8")

        fake_issues = [{"type": "mock_issue", "severity": "low", "detail": f"问题 {i}"} for i in range(60)]
        with mock.patch.object(book_quality, "check_intra_chapter_repeats", return_value=fake_issues):
            res = book_quality.book_quality_check(str(self.temp_dir))
            self.assertEqual(res["total_issues"], 60)
            self.assertTrue(res["issues_truncated"])
            self.assertEqual(len(res["issues"]), 50)
            self.assertEqual(res["issues_limit"], 50)

    def test_main_cli_error_flow(self):
        # CLI 遇到不存在的路径时返回非零退出码
        with mock.patch("sys.argv", ["book_quality.py", "non_existent_path"]), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out, \
             self.assertRaises(SystemExit) as cm:
            book_quality.main()
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("[X]", mock_out.getvalue())

        # CLI 带 --json 遇到错误时输出 JSON 并返回非零
        with mock.patch("sys.argv", ["book_quality.py", "non_existent_path", "--json"]), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out, \
             self.assertRaises(SystemExit) as cm:
            book_quality.main()
        self.assertEqual(cm.exception.code, 1)
        data = json.loads(mock_out.getvalue())
        self.assertIn("error", data)

    def test_main_cli_success_and_json(self):
        ch1 = Path(self.temp_dir) / "chapter-001.txt"
        ch1.write_text("清风徐来，水波不兴。这是完美纯净的一章作品。", encoding="utf-8")

        # 1. 纯文本模式运行且通过
        with mock.patch("sys.argv", ["book_quality.py", str(self.temp_dir)]), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out, \
             self.assertRaises(SystemExit) as cm:
            book_quality.main()
        self.assertEqual(cm.exception.code, 0)
        out = mock_out.getvalue()
        self.assertIn("全书内容质检", out)
        self.assertIn("判定: PASS", out)

        # 2. JSON 模式运行
        with mock.patch("sys.argv", ["book_quality.py", str(self.temp_dir), "--json"]), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out, \
             self.assertRaises(SystemExit) as cm:
            book_quality.main()
        self.assertEqual(cm.exception.code, 0)
        data = json.loads(mock_out.getvalue())
        self.assertEqual(data["verdict"], "PASS")
        self.assertEqual(data["total_chapters"], 1)


if __name__ == "__main__":
    unittest.main()
