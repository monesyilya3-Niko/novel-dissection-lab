"""题材包「示例句」质量守卫（2026-11-03）。

背景：``derive_genre_packs.py`` 早期把每条铁律的 good_example 写成固定句式
``落在具体场景与人物选择上，而非 {规则}``，bad_example 写死
``通篇{规则}，读者读不到实际推进``。31 个派生题材包因此共用同一句话——
写进 prompt 等于没给示例，用户看到「示例」却得不到任何具体写法。

修复后正例取自该题材 prose 卡的真实段落（场景颗粒 / 正文提示词 / 爽点释放），
理由也不再与规则重复。本测试防止模板句回潮。
"""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 历史上的机械模板句：出现任意一条即视为回潮
BANNED_TEMPLATE_SNIPPETS = (
    "落在具体场景与人物选择上",
    "读者读不到实际推进",
)
ASSETS = ROOT / "assets"


def _load_derive_module():
    spec = importlib.util.spec_from_file_location(
        "derive_genre_packs_under_test", ROOT / "scripts" / "derive_genre_packs.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class TestGenrePackExamples(unittest.TestCase):
    def test_no_mechanical_template_in_assets(self):
        """assets/ 下任何题材包都不得再出现机械模板句。"""
        offenders = []
        for fp in sorted(ASSETS.glob("*-genre-pack.json")):
            text = fp.read_text(encoding="utf-8")
            for snip in BANNED_TEMPLATE_SNIPPETS:
                if snip in text:
                    offenders.append(f"{fp.name}: {snip}")
        self.assertEqual(offenders, [], "题材包出现机械模板句（示例失效）：\n  " + "\n  ".join(offenders))

    def test_generated_examples_draw_from_source_card(self):
        """新生成的示例必须来自该题材原文，且 rationale 不与 rule 同义重复。"""
        derive = _load_derive_module()
        card_path = ASSETS / "genre-prose-card-genre-dushi-gaowu.json"
        if not card_path.exists():
            self.skipTest("缺少 dushi-gaowu 文风卡")
        card = json.loads(card_path.read_text(encoding="utf-8"))
        pack = derive.build_pack(card, "dushi-gaowu")

        rules = pack["language_rules"]["iron_rules"]
        self.assertGreater(len(rules), 0, "该题材应有铁律")

        sections_text = " ".join((card.get("prose") or {}).get("sections", {}).values())
        for r in rules:
            with self.subTest(rule=r["rule"]):
                # 1. 不得是机械模板
                for snip in BANNED_TEMPLATE_SNIPPETS:
                    self.assertNotIn(snip, r["good_example"],
                                     f"good_example 仍是模板句: {r['good_example']}")
                # 2. 正例必须能在原卡文本里找到（允许拼接，取最长片段核对）
                body = r["good_example"].split("（而不是")[0].strip()
                head = body[:12]
                self.assertIn(head, sections_text,
                              f"正例不是出自该题材原文: {body[:50]}")
                # 3. rationale 不能只是把 rule 换个说法
                self.assertNotEqual(r["rationale"], r["rule"])
                self.assertNotIn("该题材的常见失手点：", r["rationale"],
                                 "rationale 退回了「重复规则」的旧写法")

    def test_every_pack_has_distinct_examples_within_itself(self):
        """同一个包内，多条铁律不应共用同一句 good_example 前缀。"""
        for fp in sorted(ASSETS.glob("*-genre-pack.json")):
            data = json.loads(fp.read_text(encoding="utf-8"))
            rules = (data.get("language_rules") or {}).get("iron_rules") or []
            if len(rules) < 2:
                continue
            heads = [str(r.get("good_example", ""))[:20] for r in rules]
            dupes = {h for h in heads if heads.count(h) > 1}
            self.assertEqual(
                dupes, set(),
                f"{fp.name} 内有多条铁律共用同一示例开头: {dupes}",
            )


if __name__ == "__main__":
    unittest.main()
