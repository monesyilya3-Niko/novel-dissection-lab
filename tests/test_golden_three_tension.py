"""测试黄金三章张力曲线重叠比对引擎（Golden Three Chapters Tension Comparator）。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui import router, writing_extra
from gui.services import ServiceError


class TestGoldenThreeTension(unittest.TestCase):
    def test_invalid_inputs_rejected(self):
        """输入非列表、空列表或章节非字符串时，严格抛出 400 ServiceError。"""
        with self.assertRaises(ServiceError) as cm:
            writing_extra.analyze_golden_three_tension(None)  # type: ignore[arg-type]
        self.assertEqual(cm.exception.code, 400)

        with self.assertRaises(ServiceError) as cm:
            writing_extra.analyze_golden_three_tension([])
        self.assertEqual(cm.exception.code, 400)

        with self.assertRaises(ServiceError) as cm:
            writing_extra.analyze_golden_three_tension("not a list")  # type: ignore[arg-type]
        self.assertEqual(cm.exception.code, 400)

        with self.assertRaises(ServiceError) as cm:
            writing_extra.analyze_golden_three_tension(["第一章有效文本", 12345])  # type: ignore[list-item]
        self.assertEqual(cm.exception.code, 400)

    def test_empty_and_whitespace_chapters(self):
        """空字符串或空白文本章节安全处理，返回零张力与完备数据结构。"""
        res = writing_extra.analyze_golden_three_tension(["", "   \n\t  "])
        self.assertEqual(res["total_chapters"], 2)
        self.assertEqual(len(res["chapters_metrics"]), 2)
        self.assertEqual(res["chapters_metrics"][0]["tension_curve"], [0] * 10)
        self.assertEqual(res["chapters_metrics"][1]["tension_curve"], [0] * 10)
        self.assertEqual(res["total_chars"], 0)
        self.assertEqual(res["verdict"], "WARNING_FLAT")
        self.assertIn("recommendations", res)

    def test_single_and_two_chapters(self):
        """单章与双章输入时，平稳兼容且连接动量 (handoffs) 数量自适应。"""
        ch1 = "风雪漫天，刺客长刀劈落！少年翻滚拔剑，生死一线！"
        res1 = writing_extra.analyze_golden_three_tension([ch1], points_per_chapter=5)
        self.assertEqual(res1["total_chapters"], 1)
        self.assertEqual(len(res1["handoffs"]), 0)
        self.assertEqual(len(res1["combined_curve"]), 5)
        self.assertEqual(len(res1["combined_benchmark_curve"]), 5)

        ch2 = "反派冷笑：“今日你插翅难飞！”轰然一掌击碎山岩！"
        res2 = writing_extra.analyze_golden_three_tension([ch1, ch2], points_per_chapter=6)
        self.assertEqual(res2["total_chapters"], 2)
        self.assertEqual(len(res2["handoffs"]), 1)
        self.assertEqual(res2["handoffs"][0]["from_chapter"], 1)
        self.assertEqual(res2["handoffs"][0]["to_chapter"], 2)
        self.assertEqual(len(res2["combined_curve"]), 12)

    def test_standard_three_chapters_flow(self):
        """标准黄金三章（起承转合）全流程计算与多维指标验证。"""
        ch1 = (
            "深夜长街，杀机骤起！\n"
            "黑衣刺客长刀撕裂长空，狠厉劈向少年头颅！“受死吧！”\n"
            "狂暴的刀芒带着刺耳呼啸，鲜血瞬间染红了青石砖。少年目眦欲裂，咬牙翻滚！\n"
            "砰！身后的巨石崩裂成碎块！生死悬于一线，章末神秘玉佩突然发光！"
        )
        ch2 = (
            "玉佩散发灼热光芒，一股浩瀚灵力涌入经脉！\n"
            "刺客眼中掠过一抹贪婪：“至宝！竟是上古神物！”\n"
            "少年强忍经脉撕裂剧痛，借力急退。身后是万丈悬崖，身前是绝顶杀手！\n"
            "“想要我的命？拿你的命来换！”少年握紧断剑，杀意升腾！"
        )
        ch3 = (
            "“狂妄小儿！”刺客怒吼，狂暴刀意如浪潮席卷！\n"
            "少年身形如电，断剑骤然爆发惊天龙吟！噗嗤！一剑洞穿刺客咽喉！\n"
            "鲜血喷涌，强敌轰然倒地！全场震撼死寂！\n"
            "然而还未等喘息，夜空中突然降临数道更恐怖的威压锁定了少年！绝杀之局！"
        )

        res = writing_extra.analyze_golden_three_tension(
            [ch1, ch2, ch3],
            benchmark="classic",
            points_per_chapter=10,
        )

        self.assertEqual(res["total_chapters"], 3)
        self.assertEqual(len(res["chapters_metrics"]), 3)
        self.assertEqual(len(res["handoffs"]), 2)
        self.assertEqual(len(res["combined_curve"]), 30)
        self.assertEqual(len(res["combined_benchmark_curve"]), 30)
        self.assertGreater(res["total_chars"], 100)

        # 检查各章节核心指标
        for cm in res["chapters_metrics"]:
            self.assertIn("tension_curve", cm)
            self.assertIn("benchmark_curve", cm)
            self.assertIn("climax_index", cm)
            self.assertIn("opening_score", cm)
            self.assertIn("hook_score", cm)
            self.assertIn("chapter_verdict", cm)

        # 检查全局裁决与高潮
        self.assertIn("global_climax", res)
        self.assertGreater(res["global_climax"]["max_tension"], 50)
        self.assertIn("verdict", res)
        self.assertIn("verdict_title", res)
        self.assertIn("cliffhanger_rating", res)
        self.assertIsInstance(res["recommendations"], list)

    def test_cliff_drop_detection(self):
        """测试跨章断崖式失速检测（上一章极高潮，下一章骤降35分以上）。"""
        ch1_high_tension = "杀！杀！受死！轰！狂暴绝杀！鲜血喷涌！刀光剑影！生死一击！" * 15
        ch2_calm = "清晨的阳光洒在木桌上，微风拂过落叶。老书生泡了一壶茶，静静看书，岁月静好。" * 15

        res = writing_extra.analyze_golden_three_tension([ch1_high_tension, ch2_calm])
        handoff = res["handoffs"][0]
        self.assertEqual(handoff["status"], "CLIFF_DROP")
        self.assertGreater(handoff["drop"], 35)
        self.assertEqual(res["verdict"], "WARNING_DROP")
        self.assertTrue(any("断崖失速" in r for r in res["recommendations"]))

    def test_all_flat_warning(self):
        """三章全篇平静无冲突文本，应触发平缓警告 WARNING_FLAT。"""
        calm_text = "阳光明媚，微风轻拂。茶香袅袅，落叶纷飞。岁月静好，一片安宁祥和。" * 10
        res = writing_extra.analyze_golden_three_tension([calm_text, calm_text, calm_text])
        self.assertEqual(res["verdict"], "WARNING_FLAT")
        self.assertIn("平缓", res["verdict_title"])

    def test_benchmarks_and_resampling(self):
        """测试四套标杆（classic/upgrade_shuangwen/fast_hook/suspense_mystery）与自定义切片点数。"""
        sample_chapters = [
            "黑夜伏击，刀光突现！生死关头！",
            "金手指觉醒，绝境反击，一拳震碎强敌！",
            "首卷大决战，狂暴对轰，震撼全场，留下神秘追杀令！",
        ]
        benchmarks = ["classic", "upgrade_shuangwen", "fast_hook", "suspense_mystery"]
        for bm in benchmarks:
            res = writing_extra.analyze_golden_three_tension(
                sample_chapters, benchmark=bm, points_per_chapter=8
            )
            self.assertEqual(res["benchmark"], bm)
            self.assertEqual(res["points_per_chapter"], 8)
            self.assertEqual(len(res["combined_curve"]), 24)
            self.assertEqual(len(res["combined_benchmark_curve"]), 24)
            self.assertGreaterEqual(res["combined_alignment_score"], 0)
            self.assertLessEqual(res["combined_alignment_score"], 100)

    def test_router_api_dispatch(self):
        """验证 /api/writing/golden-three-tension 路由与参数防御。"""
        # 1. 正常请求
        payload = {
            "chapters": [
                "第一章：杀机骤现，绝地拔刀！",
                "第二章：反败为胜，金手指觉醒！",
                "第三章：轰杀反派，震撼全场，大仇得报！",
            ],
            "benchmark": "upgrade_shuangwen",
            "points_per_chapter": 7,
        }
        resp, _ = router.dispatch("POST", "/api/writing/golden-three-tension", payload, {})
        self.assertEqual(resp["code"], 0)
        data = resp["data"]
        self.assertEqual(data["total_chapters"], 3)
        self.assertEqual(data["points_per_chapter"], 7)
        self.assertEqual(len(data["combined_curve"]), 21)
        self.assertIn("global_climax", data)

        # 2. 异常请求防御：chapters 为空列表
        with self.assertRaises(ServiceError) as cm:
            router.dispatch("POST", "/api/writing/golden-three-tension", {"chapters": []}, {})
        self.assertEqual(cm.exception.code, 400)

        # 3. 异常请求防御：chapters 包含非字符串
        with self.assertRaises(ServiceError) as cm:
            router.dispatch(
                "POST", "/api/writing/golden-three-tension", {"chapters": ["第1章", 999]}, {}
            )
        self.assertEqual(cm.exception.code, 400)

        # 4. 异常请求防御：points_per_chapter 格式非法
        with self.assertRaises(ServiceError) as cm:
            router.dispatch(
                "POST",
                "/api/writing/golden-three-tension",
                {"chapters": ["第1章"], "points_per_chapter": "invalid"},
                {},
            )
        self.assertEqual(cm.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
