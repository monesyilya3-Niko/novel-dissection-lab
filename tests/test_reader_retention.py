"""测试商业网文读者留存流失预测模型（Reader Churn & Drop-off Estimator）。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui import router, writing_extra
from gui.services import ServiceError


class TestReaderRetention(unittest.TestCase):
    def test_invalid_inputs(self):
        """输入非列表、空列表或包含非字符串章节内容时，严格抛出 400 ServiceError。"""
        with self.assertRaises(ServiceError) as cm:
            writing_extra.estimate_reader_retention(None)  # type: ignore[arg-type]
        self.assertEqual(cm.exception.code, 400)

        with self.assertRaises(ServiceError) as cm:
            writing_extra.estimate_reader_retention([])
        self.assertEqual(cm.exception.code, 400)

        with self.assertRaises(ServiceError) as cm:
            writing_extra.estimate_reader_retention("string-not-list")  # type: ignore[arg-type]
        self.assertEqual(cm.exception.code, 400)

        with self.assertRaises(ServiceError) as cm:
            writing_extra.estimate_reader_retention(["有效正文", 12345])  # type: ignore[list-item]
        self.assertEqual(cm.exception.code, 400)

    def test_empty_and_whitespace_chapters(self):
        """空白章节内容安全处理，返回降级留存曲线与低评级诊断。"""
        res = writing_extra.estimate_reader_retention(["", "   \t\n  "], points_per_chapter=5)
        self.assertEqual(res["total_chapters"], 2)
        self.assertEqual(len(res["retention_curve"]), 11)  # 2 * 5 + 1
        self.assertEqual(res["overall_grade"], "C")
        self.assertLess(res["final_retention_rate"], 35.0)
        self.assertIn("高危预警", res["grade_description"])

    def test_single_and_multi_chapter_retention(self):
        """单章与多章自适应计算留存衰减曲线与章节级汇总。"""
        ch1 = "黑夜长街，刺客拔刀！少年咬牙翻滚，拔剑迎敌！"
        res1 = writing_extra.estimate_reader_retention([ch1], points_per_chapter=6)
        self.assertEqual(res1["total_chapters"], 1)
        self.assertEqual(len(res1["chapters_retention"]), 1)
        self.assertEqual(len(res1["retention_curve"]), 7)  # 1 * 6 + 1
        self.assertEqual(res1["chapters_retention"][0]["start_retention"], 100.0)

        ch2 = "反派冷喝：“受死吧！”轰然一掌击裂巨石！"
        ch3 = "生死绝杀！断剑爆发惊天龙吟，一剑封喉！"
        res3 = writing_extra.estimate_reader_retention([ch1, ch2, ch3], points_per_chapter=8)
        self.assertEqual(res3["total_chapters"], 3)
        self.assertEqual(len(res3["chapters_retention"]), 3)
        self.assertEqual(len(res3["retention_curve"]), 25)  # 3 * 8 + 1
        self.assertGreaterEqual(res3["final_retention_rate"], 5.0)
        self.assertLessEqual(res3["final_retention_rate"], 100.0)

    def test_cliff_drop_triggers_critical_hotspot(self):
        """跨章断崖失速时（张力落差>35分），高灵敏度捕获流失高危点与改法。"""
        ch1_high = "杀！杀！受死！轰！狂暴绝杀！鲜血喷涌！刀光剑影！生死一击！" * 15
        ch2_calm = "清晨的阳光洒在木桌上，微风拂过落叶。老书生泡了一壶茶，静静看书，岁月静好。" * 15

        res = writing_extra.estimate_reader_retention([ch1_high, ch2_calm])
        self.assertGreater(len(res["dropoff_hotspots"]), 0)
        # 查找发生在第 2 章开头的 hotspot
        ch2_hotspots = [h for h in res["dropoff_hotspots"] if h["chapter_index"] == 2 and h["segment_index"] == 0]
        self.assertGreater(len(ch2_hotspots), 0)
        hotspot = ch2_hotspots[0]
        self.assertIn("断崖式失速", hotspot["reason"])
        self.assertIn(hotspot["risk_level"], ("CRITICAL", "HIGH"))
        self.assertIn("背景", hotspot["fix_suggestion"])

    def test_high_tension_good_grade(self):
        """高冲突、快节奏、入局迅速且章尾强悬念的优质三章，留存评级达到 A 或 S。"""
        ch1 = (
            "深夜长街，杀机骤起！刺客长刀撕裂长空劈向少年！“受死吧！”\n"
            "狂暴刀芒带着刺耳呼啸，鲜血染红青石砖。少年目眦欲裂，咬牙翻滚！\n"
            "身后的巨石崩裂成碎块！生死悬于一线，怀中神秘断玉突然迸发耀眼红芒！"
        )
        ch2 = (
            "断玉散发灼热高温，一股狂暴暖流涌入四肢百骸！\n"
            "刺客惊呼：“上古至宝！”少年借力腾空，反手拔出断剑凌空怒斩！\n"
            "轰！剑气撕裂夜空，反派被震退数丈，眼中贪婪与惊惧交加！"
        )
        ch3 = (
            "“狂妄小儿，纳命来！”刺客怒吼扑杀，刀刀致命！\n"
            "生死刹那，少年眼神骤冷，断玉中觉醒上古无上剑意！嗤啦！一剑洞穿刺客咽喉！\n"
            "反派轰然倒地，全场震撼死寂！长街尽头却突现数道可怖黑影封锁全城！"
        )

        res = writing_extra.estimate_reader_retention([ch1, ch2, ch3], benchmark="upgrade_shuangwen")
        self.assertIn(res["overall_grade"], ("S", "A"))
        self.assertGreaterEqual(res["final_retention_rate"], 50.0)
        self.assertIn("chapters_retention", res)
        self.assertIn("retention_advice", res)

    def test_calm_text_low_grade(self):
        """全程平淡无波描写文段，读者流失过半，触发 C 级警告。"""
        calm_text = "阳光明媚，微风轻拂。茶香袅袅，落叶纷飞。岁月静好，一片安宁祥和。" * 12
        res = writing_extra.estimate_reader_retention([calm_text, calm_text, calm_text])
        self.assertEqual(res["overall_grade"], "C")
        self.assertLess(res["final_retention_rate"], 38.0)
        self.assertIn("高危预警", res["grade_description"])

    def test_router_api_dispatch(self):
        """验证 /api/writing/reader-retention 路由分发与入参校验。"""
        payload = {
            "chapters": [
                "第1章：拔刀决生死！",
                "第2章：断玉觉醒神力！",
                "第3章：一剑封喉震撼全场！",
            ],
            "benchmark": "classic",
            "points_per_chapter": 8,
        }
        resp, _ = router.dispatch("POST", "/api/writing/reader-retention", payload, {})
        self.assertEqual(resp["code"], 0)
        data = resp["data"]
        self.assertEqual(data["total_chapters"], 3)
        self.assertEqual(data["total_segments"], 24)
        self.assertEqual(len(data["retention_curve"]), 25)
        self.assertIn("overall_grade", data)
        self.assertIn("final_retention_rate", data)
        self.assertIn("dropoff_hotspots", data)

        # 异常校验：空列表与脏参数
        with self.assertRaises(ServiceError) as cm:
            router.dispatch("POST", "/api/writing/reader-retention", {"chapters": []}, {})
        self.assertEqual(cm.exception.code, 400)

        with self.assertRaises(ServiceError) as cm:
            router.dispatch("POST", "/api/writing/reader-retention", {"chapters": ["ch1", 999]}, {})
        self.assertEqual(cm.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
