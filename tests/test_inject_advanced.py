"""资产注入器高级特性与完整装配（inject.py）全维独立测试套件。

覆盖维度：
1. 蒸馏资产归一化（_normalize_distilled_assets：单维/多维/按书分组/非字典容错）
2. 写作意图语义检索桥接（retrieve_for_intent：题材解析三优先级 / 原始资产建索引 / 蒸馏结构兜底 / 空索引保护）
3. 口头禅与语气词类型适配（_vt_to_str：字符串 / 中英文情境字典 / 混合类型）
4. 题材包规则渲染（render_genre_pack：语言铁律 / 必需与禁忌要素 / 疲劳词限额 / 结构模板 / 商业爽点与卡点 / 世界观惯例）
5. 写作技法卡渲染（render_craft_card：最强技法TOP3 / 10维技法骨架与反例截断 / 可复用模式）
6. 题材文风卡渲染（render_genre_prose_card：软约束标注 / 低置信度告警 / 语言与结构及商业参考 / prose小节完整兜底）
7. 完整 System Prompt 装配与防空守卫（build_prompt：题材规则 / 软约束 / 蒸馏段 / 意图检索 / 观测占位符过滤 / 状态追踪 / 九项执行清单）
8. 命令行接口（main：全参数解析 / 跨文件读取 / 输出落盘与格式化日志）
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

import inject


class TestNormalizeDistilledAssets(unittest.TestCase):
    """测试蒸馏资产结构归一化 _normalize_distilled_assets。"""

    def test_non_dict_input(self):
        self.assertEqual(inject._normalize_distilled_assets(None), {})
        self.assertEqual(inject._normalize_distilled_assets("invalid"), {})
        self.assertEqual(inject._normalize_distilled_assets([1, 2, 3]), {})

    def test_single_dimension_dict(self):
        distilled = {
            "meta": {"dimension": "dialogue_craft", "genre": "都市异能"},
            "rules": ["对话短促有力"],
        }
        res = inject._normalize_distilled_assets(distilled)
        self.assertEqual(res, {"dialogue_craft": distilled})

    def test_multi_dimension_or_grouped_by_book(self):
        distilled_multi = {
            "dim1": {"meta": {"dimension": "tension_building"}, "data": 1},
            "dim2": {"meta": {}, "data": 2},  # 缺 inner meta.dimension 回退到 key
            "invalid_non_dict": "skip me",
        }
        res = inject._normalize_distilled_assets(distilled_multi)
        self.assertEqual(len(res), 2)
        self.assertIn("tension_building", res)
        self.assertIn("dim2", res)
        self.assertEqual(res["tension_building"]["data"], 1)
        self.assertEqual(res["dim2"]["data"], 2)


class TestRetrieveForIntent(unittest.TestCase):
    """测试按写作意图检索资产片段 retrieve_for_intent。"""

    def test_empty_intent_returns_empty(self):
        self.assertEqual(inject.retrieve_for_intent(""), [])
        self.assertEqual(inject.retrieve_for_intent(None), [])

    def test_resolve_genre_and_retrieve_with_collected_assets(self):
        fake_assets = {"dim": {"key": "value"}}
        mock_index = mock.MagicMock()
        mock_index.docs = ["doc1", "doc2"]

        with mock.patch("inject.collect_assets", return_value=fake_assets) as mock_collect, \
             mock.patch("inject.build_index", return_value=mock_index) as mock_build, \
             mock.patch("inject._retrieve", return_value=[{"asset_id": "hit1", "score": 0.9}]) as mock_ret:

            # 1. 直接通过入参 genre 确定
            hits = inject.retrieve_for_intent("悬疑反转", genre="悬疑推理")
            self.assertEqual(len(hits), 1)
            mock_collect.assert_called_with("悬疑推理")
            mock_build.assert_called_with(fake_assets)
            mock_ret.assert_called_with("悬疑反转", mock_index, top_k=5)

            # 2. 从 distilled.meta.genre 确定
            distilled = {"meta": {"genre": "科幻末世"}}
            hits2 = inject.retrieve_for_intent("末日危机", distilled=distilled)
            self.assertEqual(len(hits2), 1)
            mock_collect.assert_called_with("科幻末世")

            # 3. 从 distilled 各维度的 inner meta 确定
            distilled_inner = {"dim1": {"meta": {"genre": "修真仙侠"}}}
            hits3 = inject.retrieve_for_intent("渡劫突破", distilled=distilled_inner)
            self.assertEqual(len(hits3), 1)
            mock_collect.assert_called_with("修真仙侠")

    def test_fallback_to_distilled_assets(self):
        mock_index = mock.MagicMock()
        mock_index.docs = ["doc_fallback"]

        with mock.patch("inject.collect_assets") as mock_collect, \
             mock.patch("inject.build_index", return_value=mock_index) as mock_build, \
             mock.patch("inject._retrieve", return_value=[{"asset_id": "fallback_hit"}]) as mock_ret:

            # 无 genre 时直接走兜底
            distilled = {"rules": ["无genre的蒸馏规则"]}
            hits = inject.retrieve_for_intent("战斗节奏", distilled=distilled)
            self.assertEqual(len(hits), 1)
            mock_collect.assert_not_called()
            mock_build.assert_called_once()
            mock_ret.assert_called_once()

    def test_index_none_returns_empty(self):
        with mock.patch("inject.build_index", return_value=None):
            hits = inject.retrieve_for_intent("日常对话", distilled={"test": 1})
            self.assertEqual(hits, [])


class TestVerbalTicsToString(unittest.TestCase):
    """测试口头禅格式化辅助函数 _vt_to_str。"""

    def test_vt_to_str_various_types(self):
        # 1. 普通字符串
        self.assertEqual(inject._vt_to_str("岂有此理"), "岂有此理")

        # 2. 中文键字典 {情境, 规则}
        dict_zh = {"情境": "被质疑时", "规则": "冷笑一声"}
        self.assertEqual(inject._vt_to_str(dict_zh), "被质疑时：冷笑一声")

        # 3. 英文键字典 {context, rule}
        dict_en = {"context": "愤怒时", "rule": "咬牙切齿"}
        self.assertEqual(inject._vt_to_str(dict_en), "愤怒时：咬牙切齿")

        # 4. 场景别名 {场景}
        dict_scene = {"场景": "遇到故人"}
        self.assertEqual(inject._vt_to_str(dict_scene), "遇到故人")

        # 5. 空字典或其他类型回退
        self.assertEqual(inject._vt_to_str({}), "{}")
        self.assertEqual(inject._vt_to_str(12345), "12345")


class TestRenderGenrePack(unittest.TestCase):
    """测试题材包规则渲染器 render_genre_pack。"""

    def test_empty_genre_pack(self):
        self.assertEqual(inject.render_genre_pack({}), "（无题材包）")
        self.assertEqual(inject.render_genre_pack(None), "（无题材包）")

    def test_full_genre_pack(self):
        gp = {
            "language_rules": {
                "iron_rules": [
                    {"rule": "禁止现代网络流行梗", "bad_example": "YYDS", "good_example": "绝代风华"}
                ],
                "required_elements": ["命盘显化", "灵兽嘶鸣"],
                "forbidden_elements": ["手机电话", "枪械火器"],
                "banned_phrases": ["降维打击", "薛定谔的猫"],
                "fatigue_words": [{"word": "恐怖如斯", "max_per_chapter": 1}],
            },
            "structure": {
                "chapter_roles": [
                    {"role": "高潮推进", "ratio": "30%", "typical_position": "章中段", "beats": ["冲突爆发", "底牌出尽"]}
                ],
                "hook_system": {
                    "hook_types": [{"type": "生死反转", "frequency": "每3章", "skeleton": "致命攻击突现"}],
                    "anti_repetition_rule": "连续两章不得使用相同类型钩子",
                },
                "foreshadow_pattern": {
                    "avg_span": 5,
                    "concurrent_open": 3,
                    "plant_technique": ["偶遇旧物", "梦呓低语"],
                },
            },
            "commercial": {
                "payoff_density": {
                    "payoff_types": [
                        {"type": "绝地打脸", "ratio": "40%", "buildup_length": 1500, "skeleton": "先抑后扬当众揭露"}
                    ]
                },
                "paywall": {"position_chapter": 30, "cliffhanger_technique": "主角生死一线"},
                "update_rhythm": {"daily_words": 6000},
            },
            "world_conventions": {
                "power_system_type": "九阶练气筑基金丹",
                "naming_conventions": ["古风二字名", "宗门四字规整名"],
            },
        }
        res = inject.render_genre_pack(gp)
        self.assertIn("### 题材铁律（违反即题材崩塌）", res)
        self.assertIn("禁止现代网络流行梗（✗ YYDS）（✓ 绝代风华）", res)
        self.assertIn("### 每章必需要素", res)
        self.assertIn("□ 命盘显化", res)
        self.assertIn("### 章节禁止要素", res)
        self.assertIn("✗ 手机电话", res)
        self.assertIn("### 题材禁忌词（全文禁用）", res)
        self.assertIn("降维打击、薛定谔的猫", res)
        self.assertIn("恐怖如斯≤1次", res)
        self.assertIn("### 章节结构模板（各段职责与占比）", res)
        self.assertIn("高潮推进（占比 30%，章中段）：冲突爆发、底牌出尽", res)
        self.assertIn("### 钩子系统（章末钩子按此选型）", res)
        self.assertIn("生死反转（频率 每3章）：致命攻击突现", res)
        self.assertIn("防重复：连续两章不得使用相同类型钩子", res)
        self.assertIn("伏笔节奏：平均 5 章回收，同时开放 3 条", res)
        self.assertIn("### 爽点类型（按占比选型铺垫）", res)
        self.assertIn("绝地打脸（占比 40%，铺垫 1500 字）：先抑后扬当众揭露", res)
        self.assertIn("付费卡点规划：第 30 章，卡点手法：主角生死一线", res)
        self.assertIn("力量体系：九阶练气筑基金丹", res)
        self.assertIn("命名惯例：古风二字名、宗门四字规整名", res)


class TestRenderCraftCard(unittest.TestCase):
    """测试写作技法卡渲染器 render_craft_card。"""

    def test_empty_craft_card(self):
        self.assertEqual(inject.render_craft_card({}), "")
        self.assertEqual(inject.render_craft_card(None), "")

    def test_full_craft_card(self):
        cc = {
            "craft_summary": {
                "top_3_strengths": ["高频伏笔埋设", "多视角交织切换", "呼吸感极强短句爆发"],
                "reusable_patterns": ["先抑后扬三段打脸模型", "双线并进悬念留白法"],
            },
            "craft_analysis": {
                "foreshadowing": {
                    "techniques": [
                        {"name": "草蛇灰线法", "skeleton": "第3章埋下信物，第20章揭露真相", "anti_pattern": "机械降神突然出现"}
                    ]
                },
                "tension_building": {
                    "techniques": [
                        {"name": "倒计时压迫", "skeleton": "明确时间节点逐步缩短主角回旋余地"}
                    ]
                },
            },
        }
        res = inject.render_craft_card(cc)
        self.assertIn("### 最强技法（写作时优先运用）", res)
        self.assertIn("- 高频伏笔埋设", res)
        self.assertIn("### 伏笔技法", res)
        self.assertIn("草蛇灰线法：第3章埋下信物，第20章揭露真相（✗ 反例：机械降神突然出现）", res)
        self.assertIn("### 张力构建", res)
        self.assertIn("倒计时压迫：明确时间节点逐步缩短主角回旋余地", res)
        self.assertIn("### 最值得复用的写作模式", res)
        self.assertIn("- 先抑后扬三段打脸模型", res)


class TestRenderGenreProseCard(unittest.TestCase):
    """测试题材文风卡渲染器 render_genre_prose_card。"""

    def test_empty_prose_card(self):
        self.assertEqual(inject.render_genre_prose_card({}), "")
        self.assertEqual(inject.render_genre_prose_card(None), "")

    def test_low_confidence_prose_card(self):
        card_low = {
            "meta": {"name": "都市玄幻", "confidence": 0.35},
            "language_rules": {"forbidden_elements": ["文绉绉长句"], "voice_notes": "多用短句"},
        }
        res_low = inject.render_genre_prose_card(card_low)
        self.assertIn("【低置信·仅供参考】", res_low)
        self.assertIn("题材：都市玄幻", res_low)
        self.assertIn("置信度：0.35（来源自报，未经验证）", res_low)
        self.assertIn("✗ 文绉绉长句", res_low)
        self.assertIn("多用短句", res_low)

    def test_high_confidence_prose_card_with_sections(self):
        card_high = {
            "meta": {"name": "悬疑惊悚", "confidence": 0.85},
            "structure": {"hook_notes": "章尾切断逃生通道", "arc_rhythm_notes": "每三章一次生死危机"},
            "commercial": {"payoff_notes": "解谜后获得安全庇护所"},
            "prose": {
                "sections": {
                    "环境阴郁描写": "雨夜中，破旧的钟表发出滴答声响。",
                    "心跳微反应": "冷汗瞬间浸透了衣衫，呼吸随之停滞。",
                }
            },
        }
        res_high = inject.render_genre_prose_card(card_high)
        self.assertNotIn("【低置信·仅供参考】", res_high)
        self.assertIn("参考·章尾钩子 / 正文落点", res_high)
        self.assertIn("参考·节奏密度 / 前中后期打法", res_high)
        self.assertIn("参考·爽点与情绪释放", res_high)
        self.assertIn("### 原文参考（完整小节，兜底）", res_high)
        self.assertIn("#### 环境阴郁描写", res_high)
        self.assertIn("雨夜中，破旧的钟表发出滴答声响。", res_high)


class TestBuildPromptIntegrations(unittest.TestCase):
    """测试 build_prompt 整体装配逻辑与防空守卫。"""

    def setUp(self):
        self.base_voice = {
            "meta": {"source_title": "凡人修仙标杆", "genre": "仙侠"},
            "narration": {"pov": "第三人称限制视角", "tense_feel": "冷峻克制"},
            "dialogue": {
                "character_voices": [
                    {"name": "韩立", "role": "主角", "speech_signature": {"verbal_tics": ["道友留步"]}}
                ]
            },
            "emotion_handling": {"mode": "体感白描", "body_reaction_vocabulary": ["心头一凛"]},
            "imagery": {"high_freq_metaphor_domains": ["草木", "灵兽"]},
            "banned": {"never_used_words": ["突然间", "居然"]},
        }

    def test_build_prompt_full_assembly(self):
        # 传入所有扩展参数
        genre_pack = {"language_rules": {"banned_phrases": ["天神下凡"]}}
        genre_prose_card = {"meta": {"name": "仙侠文风", "confidence": 0.9}}
        craft_card = {"craft_summary": {"top_3_strengths": ["沉稳铺垫"]}}
        distilled = {"meta": {"genre": "仙侠"}, "dim": {"rules": ["凡人步步为营"]}}
        tracking_state = {"schema_version": 2, "timeline": []}

        with mock.patch("inject.render_distilled", return_value="## 蒸馏规则段\n- 稳扎稳打"), \
             mock.patch("inject.retrieve_for_intent", return_value=[{"asset_id": "hit1"}]), \
             mock.patch("inject.render_retrieval", return_value="## 意图命中片段\n- 绝境逢生"), \
             mock.patch("inject._build_tracking_context", return_value="## 长文本状态卡\n- 活跃伏笔三条"):

            prompt = inject.build_prompt(
                voice=self.base_voice,
                structure={"aggregate": {"foreshadow_avg_span": 3}},
                commercial={"payoff_density": {"per_thousand_words": 1.5}},
                genre_pack=genre_pack,
                craft_card=craft_card,
                distilled=distilled,
                context_intent="破局战斗",
                tracking_state=tracking_state,
                genre_prose_card=genre_prose_card,
            )

            # 校验各主要区块
            self.assertIn("# 写作风格注入 · 来自《凡人修仙标杆》的拆书资产", prompt)
            self.assertIn("## 〇、题材规则（genre-pack · 最高优先级）", prompt)
            self.assertIn("## 〇、题材参考提示（genre-prose-card", prompt)
            self.assertIn("## 蒸馏规则段", prompt)
            self.assertIn("## 意图命中片段", prompt)
            self.assertIn("## 一、叙述层（narration）", prompt)
            self.assertIn("## 二、角色声线（dialogue.character_voices）", prompt)
            self.assertIn("## 三、情绪写法（emotion_handling）", prompt)
            self.assertIn("## 四、意象与感官（imagery）", prompt)
            self.assertIn("## 五、结构规律（structure-obs）", prompt)
            self.assertIn("## 六、商业节奏（commercial-obs）", prompt)
            self.assertIn("## 七、写作技法（craft-card · 可执行的写作技巧）", prompt)
            self.assertIn("## 八、禁忌（banned）", prompt)
            self.assertIn("## 长文本状态卡", prompt)
            self.assertIn("## 九、写作执行清单（硬性要求，逐条自查）", prompt)

    def test_build_prompt_empty_obs_sections_excluded(self):
        # 当 structure 和 commercial 为 None 或空时，"五、结构规律" 与 "六、商业节奏" 不应注入（防空守卫）
        prompt = inject.build_prompt(
            voice=self.base_voice,
            structure=None,
            commercial={},
        )
        self.assertNotIn("## 五、结构规律", prompt)
        self.assertNotIn("## 六、商业节奏", prompt)
        self.assertNotIn("（无结构观测）", prompt)
        self.assertNotIn("（无商业观测）", prompt)


class TestMainCLI(unittest.TestCase):
    """测试命令行接口 main 执行流程与文件输出。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_inject_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_main_cli_execution(self):
        voice_path = Path(self.temp_dir) / "demo-voice-card.json"
        voice_path.write_text(json.dumps({
            "meta": {"source_title": "测试小说"},
            "narration": {"pov": "第三人称"},
        }, ensure_ascii=False), encoding="utf-8")

        gp_path = Path(self.temp_dir) / "demo-genre-pack.json"
        gp_path.write_text(json.dumps({
            "language_rules": {"banned_phrases": ["测试禁语"]}
        }, ensure_ascii=False), encoding="utf-8")

        out_path = Path(self.temp_dir) / "output-prompt.md"

        args = [
            "inject.py",
            str(voice_path),
            "--genre-pack", str(gp_path),
            "--out", str(out_path),
        ]

        with mock.patch("sys.argv", args), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            rc = inject.main()

        self.assertEqual(rc, 0)
        out_text = mock_out.getvalue()
        self.assertIn("✓ 注入完成", out_text)
        self.assertIn("genre-pack: 已注入", out_text)
        self.assertIn("craft-card: 未注入", out_text)

        self.assertTrue(out_path.exists())
        content = out_path.read_text(encoding="utf-8")
        self.assertIn("# 写作风格注入 · 来自《测试小说》的拆书资产", content)
        self.assertIn("测试禁语", content)

    def test_main_cli_explicit_argv(self):
        voice_path = Path(self.temp_dir) / "demo-voice-card.json"
        voice_path.write_text(json.dumps({
            "meta": {"source_title": "显式参数小说"},
            "narration": {"pov": "第三人称"},
        }, ensure_ascii=False), encoding="utf-8")
        out_path = Path(self.temp_dir) / "explicit-prompt.md"

        f = io.StringIO()
        with mock.patch("sys.stdout", f):
            rc = inject.main([str(voice_path), "--out", str(out_path)])
        self.assertEqual(rc, 0)
        self.assertTrue(out_path.exists())

    def test_main_cli_missing_voice_returns_nonzero(self):
        f = io.StringIO()
        with mock.patch("sys.stderr", f):
            rc = inject.main([str(Path(self.temp_dir) / "not-found.json")])
        self.assertEqual(rc, 1)
        self.assertIn("voice-card 文件不存在", f.getvalue())


class TestGenrePackDialogueStyleRendered(unittest.TestCase):
    """题材包的对话风格与漂移护栏必须进 prompt（2026-11-03 补）。

    背景：45 个题材包都写了 ``language_rules.dialogue_style``，但
    ``render_genre_pack`` 从未渲染它——用户/资产作者写的对话要求
    对生成结果毫无影响。drift_guard 同理。
    """

    def test_string_form_dialogue_style(self):
        from scripts import inject  # noqa: F401  (import 由 conftest 保证)
        gp = {"language_rules": {"dialogue_style": "主角台词短硬，反派有身份感。"}}
        out = inject.render_genre_pack(gp)
        self.assertIn("### 对话风格", out)
        self.assertIn("主角台词短硬", out)

    def test_dict_form_dialogue_style(self):
        gp = {"language_rules": {"dialogue_style": {
            "dominant_subtype": "极致冲突短平快",
            "note": "对白短促有力",
        }}}
        from scripts import inject
        out = inject.render_genre_pack(gp)
        self.assertIn("极致冲突短平快", out)
        self.assertIn("对白短促有力", out)

    def test_drift_guard_rendered(self):
        from scripts import inject
        gp = {"language_rules": {"drift_guard": "不要把电竞写成玄幻。"}}
        out = inject.render_genre_pack(gp)
        self.assertIn("### 禁止漂移", out)
        self.assertIn("不要把电竞写成玄幻", out)

    def test_empty_values_add_no_heading(self):
        from scripts import inject
        out = inject.render_genre_pack({"language_rules": {}})
        self.assertNotIn("### 对话风格", out)
        self.assertNotIn("### 禁止漂移", out)


class TestCommercialObsRendersAllFields(unittest.TestCase):
    """商业观测的可信度声明与留存风险必须进 prompt（2026-11-03 补）。

    背景：render_commercial_obs 只渲染 payoff_density 与 opening_analysis，
    资产里写着的 paywall / update_rhythm / retention_risk_points /
    common_mistakes / payoff_density_note 全部被丢弃。
    其中 payoff_density_note 是**数据可信度声明**（"估计值，非全书统计"），
    丢了等于让模型把估算当实测。
    """

    def test_confidence_note_rendered(self):
        from scripts import inject
        co = {"payoff_density_note": "估计值：基于采样章类型学，非全书统计。"}
        out = inject.render_commercial_obs(co)
        self.assertIn("数据说明", out)
        self.assertIn("估计值", out)

    def test_paywall_rendered(self):
        from scripts import inject
        co = {"paywall": {"position_chapter": 12,
                          "cliffhanger_technique": "关系升温未确立处断章"}}
        out = inject.render_commercial_obs(co)
        self.assertIn("付费卡点", out)
        self.assertIn("第 12 章", out)
        self.assertIn("关系升温未确立处断章", out)

    def test_update_rhythm_string_not_doubled(self):
        """数字写成字符串时不能拼出「日更 更」。"""
        from scripts import inject
        co = {"update_rhythm": {"chapters_per_day": "多为稳定日更"}}
        out = inject.render_commercial_obs(co)
        self.assertIn("多为稳定日更", out)
        self.assertNotIn("日更 更", out)

    def test_update_rhythm_int_formats_as_count(self):
        from scripts import inject
        out = inject.render_commercial_obs({"update_rhythm": {"chapters_per_day": 2}})
        self.assertIn("每日 2 更", out)

    def test_retention_and_mistakes_rendered(self):
        from scripts import inject
        co = {"retention_risk_points": ["多视角章连续超2章易掉主频"],
              "common_mistakes": ["开篇倒叙生平"]}
        out = inject.render_commercial_obs(co)
        self.assertIn("留存风险点", out)
        self.assertIn("多视角章连续超2章易掉主频", out)
        self.assertIn("常见失误", out)
        self.assertIn("开篇倒叙生平", out)


class TestStructureObsRendersParams(unittest.TestCase):
    """结构观测的节奏参数必须进 prompt（2026-11-03 补）。

    背景：此前 render_structure_obs 只输出章节功能分布、3 条钩子骨架、钩子频次
    和伏笔平均跨度；钩子最小间隔 / 高潮周期 / 并发伏笔上限 / 常见结构失误
    全被丢弃——而"按这本书的节奏写"恰恰依赖这些数字。
    """

    def test_all_rhythm_params_rendered(self):
        from scripts import inject
        so = {"aggregate": {
            "hook_min_interval": 2,
            "climax_cycle": 15,
            "foreshadow_avg_span": 40,
            "foreshadow_max_span": 120,
            "foreshadow_concurrent_open": 3,
        }}
        out = inject.render_structure_obs(so)
        for token in ("钩子最小间隔 2 章", "高潮周期 15 章",
                      "伏笔平均跨度 40 章", "伏笔最长跨度 120 章",
                      "同时未回收伏笔上限 3 条"):
            self.assertIn(token, out)

    def test_common_mistakes_rendered(self):
        from scripts import inject
        so = {"common_mistakes": ["每章都堆钩子导致疲劳"]}
        out = inject.render_structure_obs(so)
        self.assertIn("常见结构失误", out)
        self.assertIn("每章都堆钩子导致疲劳", out)

    def test_notes_rendered(self):
        from scripts import inject
        so = {"aggregate": {"notes": "样本来自开篇、中段与终局附近，非全量"}}
        out = inject.render_structure_obs(so)
        self.assertIn("结构说明", out)
        self.assertIn("非全量", out)

    def test_empty_aggregate_adds_no_heading(self):
        from scripts import inject
        out = inject.render_structure_obs({"aggregate": {}})
        self.assertNotIn("### 结构参数", out)


if __name__ == "__main__":
    unittest.main()
