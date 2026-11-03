#!/usr/bin/env python3
"""genre-prose-card（题材文风卡）→ genre-pack（题材规则包）批量转换器。

背景（2026-11-02）：48 个题材都有 prose 卡，但只有 20 个有 genre-pack。
pack 是注入写作时**直接喂给模型**的规则包（结构/商业/语言铁律/世界观惯例），
缺 pack 的题材在写作阶段拿不到结构化约束，只能靠 prose 卡的自由文本。

数据来源纪律：本脚本**只做搬运与结构化**，不虚构数字。
- structure / language_rules / world_conventions：从 prose 卡的 sections 与
  language_rules 提取原文段落，转成对应字段；
- commercial / quality_thresholds 的**数值**（爽点密度、字数区间、及格线）：
  prose 卡不含这些标定，一律用 CATEGORY_DEFAULTS 的保守默认值，并在
  meta.note 里注明"未标定"。宁可给通用值并说明，也不凭空编造。

用法:
    python -m scripts.derive_genre_packs            # 补齐所有缺失题材
    python -m scripts.derive_genre_packs --dry-run  # 只看会生成哪些
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# 数值标定的保守默认值。prose 卡不含这些字段，因此不声称它们来自实测。
CATEGORY_DEFAULTS = {
    "quality_thresholds": {
        "pass": 75,
        "warn": 60,
        "dialogue_optimal": {"min": 0.15, "max": 0.35},
    },
    "commercial": {
        "payoff_density": {
            "per_thousand_words": 0.8,
            "dry_spell_tolerance": 3,
            "payoff_types": [
                {"type": "收益兑现", "ratio": 0.35, "buildup_length": 6,
                 "skeleton": "铺垫代价与阻力在前，兑现时给出具体可见的回报。"},
                {"type": "身份揭露", "ratio": 0.30, "buildup_length": 8,
                 "skeleton": "让旁观者先误判主角位置，再以事实推翻其判断。"},
                {"type": "情感回应", "ratio": 0.20, "buildup_length": 5,
                 "skeleton": "长期压制的关系在具体事件后得到回应。"},
                {"type": "反杀", "ratio": 0.15, "buildup_length": 10,
                 "skeleton": "受压迫方在被逼到绝境时翻盘，代价先付、翻盘在后。"},
            ],
        },
        "update_rhythm": {
            "chapters_per_day": 2,
            "burst_timing": "爆点章可加更；连续平和章之间必须保留一条局势推进线。",
        },
        "paywall": {
            "cliffhanger_technique": "卡在关系刚升温未确立、或谜面刚抛出未解答处。",
        },
        "retention_risk_points": [],
    },
    "chapter_word_range": {"min": 2000, "max": 3200, "typical": 2500},
    "arc_rhythm": {"arc_template": [], "chapters_per_arc": 40, "climax_position": 0.8},
    "foreshadow_pattern": {"avg_span_chapters": 5, "max_concurrent_open": 3},
}

# prose 卡 section 名 → pack 字段的搬运规则（同名字段直接取值）
# prose 卡 section 名 → 目标位置的**显式**映射。
# 每个条目是 (顶层字段, 子键或 None, 落地字段)，避免多层嵌套时按长度猜。
SECTION_MAP: dict[str, tuple[str, str | None, str]] = {
    # section 名            (顶层,     子键,          落地字段)
    # 注意：落到 hook_system 的是**文本字段**，不覆盖 hook_types 数组
    "开场抓手":            ("structure", "hook_system", "chapter_opening"),
    "章尾钩子":            ("structure", "hook_system", "chapter_end_hook"),
    "前中后期打法":        ("structure", "arc_rhythm",  "arc_template_text"),
    "节奏密度":            ("structure", "arc_rhythm",  "rhythm_notes"),
    "冲突发动机":          ("structure", None,          "conflict_engine"),
    "爽点与情绪释放":      ("commercial", None,         "payoff_notes"),
    "对话与声线":          ("language_rules", None,     "dialogue_style"),
    "场景颗粒":            ("world_conventions", None,  "scene_granularity"),
    "禁止漂移":            ("language_rules", None,     "drift_guard"),
    "证据摘要":            ("meta", None,               "evidence_summary"),
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sections(card: dict) -> dict[str, str]:
    sec = ((card.get("prose") or {}).get("sections")) or {}
    return {k: v for k, v in sec.items() if isinstance(v, str) and v.strip()}


# 每个「不要 X」铁律落在哪个 section 里能找到正面写法。
# 顺序即优先级：先找最贴近的，找不到再退到通用 section。
_RULE_TO_SECTION: tuple[tuple[tuple[str, ...], str], ...] = (
    (("力量体系", "设定", "解释", "说明", "名词"), "场景颗粒"),
    (("漂移", "题材", "宗门", "古典", "变成"), "正文提示词"),
    (("数值", "提升", "反馈", "收益"), "爽点与情绪释放"),
    (("战斗", "打斗", "交手"), "爽点与情绪释放"),
    (("对话", "台词", "说话", "声线"), "对话与声线"),
    (("节奏", "拖"), "节奏密度"),
    (("开场", "开头"), "开场抓手"),
    (("结尾", "章尾", "钩子"), "章尾钩子"),
    (("人物", "角色", "主角"), "正文提示词"),
)
_FALLBACK_SECTIONS = ("正文提示词", "冲突发动机", "本章取舍", "场景颗粒")


def _pick_sentences(text: str, limit: int = 2) -> list[str]:
    """从段落里取可用的完整句子/条目（去掉列表符号，保留原文措辞）。"""
    out = []
    for line in (text or "").splitlines():
        s = line.strip().lstrip("-•、 ").strip()
        if not s:
            continue
        # 长句按中文句号再切一次，避免把整段塞进示例
        for piece in re.split(r"(?<=[。！？])", s):
            p = piece.strip()
            if len(p) >= 12:
                out.append(p)
            if len(out) >= limit:
                return out
    return out


def _section_for(keyword_text: str) -> str:
    for keys, sec in _RULE_TO_SECTION:
        if any(k in keyword_text for k in keys):
            return sec
    return ""


def _rationale_for(cleaned: str, secs: dict[str, str]) -> str:
    """铁律理由：给「该怎么写」的正面依据，而不是把规则反着说一遍。"""
    sec = _section_for(cleaned)
    candidates = [sec] + list(_FALLBACK_SECTIONS) if sec else list(_FALLBACK_SECTIONS)
    for name in candidates:
        picks = _pick_sentences(secs.get(name, ""), limit=1)
        if picks:
            return f"该题材的正确写法：{picks[0]}"
    # 连通用 section 都没有时，至少不要再重复规则本身
    return "该题材的常见失手点，会削弱阅读推进感。"


def _build_examples(cleaned: str, secs: dict[str, str],
                    used: set[str] | None = None) -> tuple[str, str]:
    """正例取自该题材 prose 卡的原文段落；反例也从原文反推，不再套模板。

    2026-11-03 修复：此前 good_example 一律「落在具体场景与人物选择上，而非
    {规则}」、bad_example 一律「通篇{规则}，读者读不到实际推进」——31 个题材包
    共用同一句话，等于没给示例。两处都改成从该题材的真实段落取素材：

    - 正例：优先用「场景颗粒 / 正文提示词」等段落里能对上这条规则的句子；
    - 反例：从同段落的对比项反写（如段落写「用 A 承载 B」，反例就是
      「只堆 B 而不落到 A」），仍以题目自己的场景词为准，不编造情节。

    取不到足够素材时，才退回一句**中性**说明（不含固定模板句）。
    """
    sec = _section_for(cleaned)
    candidates = [sec] + list(_FALLBACK_SECTIONS) if sec else list(_FALLBACK_SECTIONS)
    # 同一题材内多条铁律不要都取同一段的第一句：按已用句子错开取句位置。
    used = used if used is not None else set()
    for name in candidates:
        all_picks = _pick_sentences(secs.get(name, ""), limit=6)
        picks = [p for p in all_picks if p not in used][:2]
        if picks:
            used.update(picks)
            good = " ".join(picks)
            bad = _bad_example_from(cleaned, secs, name)
            return (f"{good}（而不是{cleaned}）", bad)
    return (
        f"落到该题材的具体场景与人物反应上，而不是{cleaned}。",
        f"整章都在{cleaned}，没有一个具体场面承接。",
    )


def _bad_example_from(cleaned: str, secs: dict[str, str], sec_name: str) -> str:
    """针对该题材构造反例：指出「少了哪些具体承载物」。

    只做删减式描述，不编造情节、不拼接病句。段落里常有一串顿号列举的
    具体物象（检测仪、训练馆、校服…），反例就是"这些一个都没有"。
    """
    text = secs.get(sec_name, "")
    joined = " ".join(_pick_sentences(text, limit=2))
    # 元素必须是纯名词短语：只保留 2-7 个汉字、不含标点/动词性连接词
    LIST_RE = re.compile(r"[一-鿿]{2,7}(?:、[一-鿿]{2,7}){2,}")
    nouns: list[str] = []
    for m in LIST_RE.finditer(joined):
        nouns = [x for x in m.group(0).split("、") if 2 <= len(x) <= 7]
        if len(nouns) >= 3:
            break
    if len(nouns) >= 3:
        sample = "、".join(nouns[:3])
        return f"{cleaned}；{sample}这类具体场面一个都没有，读者只见概念。"
    return f"{cleaned}，通篇没有一个具体场面承接。"


def build_pack(card: dict, genre_slug: str) -> dict:
    """由 prose 卡组装 genre-pack。缺字段用保守默认值，不编造。"""
    meta_in = card.get("meta") or {}
    secs = _sections(card)
    lr_in = card.get("language_rules") or {}

    structure: dict = {
        "chapter_word_range": dict(CATEGORY_DEFAULTS["chapter_word_range"]),
        "arc_rhythm": dict(CATEGORY_DEFAULTS["arc_rhythm"]),
        # hook_system 的 hook_types 是**对象数组**（每项含 type/strength/frequency/
        # skeleton），不是空字典。类型必须 ∈ validate.HOOK_ENUM —— 校验器会拦。
        "hook_system": {
            "hook_types": [
                {"type": "悬念揭示", "strength": 0.7, "frequency": 0.3,
                 "skeleton": "在场景收束处抛出一个未解释的细节，不立即给答案。"},
                {"type": "情感冲击", "strength": 0.75, "frequency": 0.3,
                 "skeleton": "长期压制的关系被一个具体事件触动，角色反应先于台词。"},
                {"type": "危机降临", "strength": 0.85, "frequency": 0.2,
                 "skeleton": "威胁在读者已知、角色未知的位置出现，收在动作将发未发处。"},
                {"type": "信息断点", "strength": 0.65, "frequency": 0.2,
                 "skeleton": "关键信息说到一半被打断，或只给结论不给原因。"},
            ],
            "anti_repetition_rule": "连续两章不重复同一钩子类型。",
            "hook_density_curve": ["开篇用强钩子立住压力", "中段交替使用信息类与情感类", "爆点前后各留一个缓冲章"],
        },
        "chapter_roles": [],
        "foreshadow_pattern": dict(CATEGORY_DEFAULTS["foreshadow_pattern"]),
    }
    commercial: dict = json.loads(json.dumps(CATEGORY_DEFAULTS["commercial"]))
    world: dict = {"iron_laws": [], "naming_conventions": "", "power_system_type": "",
                   "progression_granularity": ""}
    lang: dict = {
        "iron_rules": [],
        "forbidden_elements": list(lr_in.get("forbidden_elements") or []),
        "banned_phrases": list(lr_in.get("banned_phrases") or []),
        "required_elements": [],
        "fatigue_words": [],
        "dialogue_style": lr_in.get("voice_notes") or "",
    }
    moved: list[str] = []

    buckets = {"structure": structure, "commercial": commercial,
               "language_rules": lang, "world_conventions": world, "meta": {}}
    for sec_name, (top, sub, leaf) in SECTION_MAP.items():
        text = secs.get(sec_name)
        if not text:
            continue
        moved.append(sec_name)
        target = buckets[top]
        if sub is not None:
            target.setdefault(sub, {})
            target[sub][leaf] = text
        else:
            target[leaf] = text

    # iron_rules：把 prose 卡「禁止漂移」与 forbidden_elements 转成
    # rule + rationale。schema 要求每项含 rule/good_example/bad_example/rationale，
    # 这里 good/bad 用「正例/反例」的文字说明（不编造具体小说句子）。
    guard_text = secs.get("禁止漂移", "")
    raw_rules: list[str] = []
    # 同题材内已用作正例的句子，避免多条铁律共用同一句示例
    used_examples: set[str] = set()
    # 「禁止漂移」里既有句号也有分号分隔（实测多为「不要 A；不要 B；不要 C。」），
    # 两种都要拆。此前只按句号拆，整串被当成一条，再与 forbidden_elements
    # 的单条重复，渲染出「整句 + 逐条」的重复铁律。
    _SEP = "[。；;" + chr(10) + "]"
    for chunk in re.split(_SEP, guard_text):
        s = chunk.strip().lstrip("-•、 ").strip()
        if len(s) >= 6:
            raw_rules.append(s)
    for fe in (lr_in.get("forbidden_elements") or []):
        s = str(fe).strip()
        if s and s not in raw_rules:
            raw_rules.append(s)

    # 去重（2026-11-03）：prose 卡里「禁止漂移」段与 forbidden_elements 数组
    # 常是同一批规则的两种措辞（前者短、后者带后半句），逐字比对拦不住。
    # 例：「不要把副本写成无脑刷怪，每个世界要有规则…」与
    #     「…每个世界要有自己的规则…」会各出一条，渲染出两条几乎一样的铁律。
    # 判据：取去掉标点后的前 8 个汉字作指纹，相同即视为同一条（保留更长的那条）。
    def _fingerprint(text: str) -> str:
        bare = re.sub(r"[^一-鿿A-Za-z]", "", text)
        # 去掉修饰性词，让「不要靠光环通关」与「不要靠主角光环通关」落到同一条
        for filler in ("自己的", "主角光环", "主角", "才是", "的", "无限流的", "该题材"):
            bare = bare.replace(filler, "")
        return bare

    def _same_rule(a: str, b: str) -> bool:
        fa, fb = _fingerprint(a), _fingerprint(b)
        if fa[:8] == fb[:8]:
            return True
        # 措辞不同但语义相近：字符级相似度高于 0.75 视为同一条
        import difflib
        return difflib.SequenceMatcher(None, fa, fb).ratio() > 0.75

    kept: list[str] = []
    for rule in raw_rules:
        if any(_same_rule(rule, k) for k in kept):
            # 已存在同类规则时保留更长（信息更全）的那条
            idx = next(i for i, k in enumerate(kept) if _same_rule(rule, k))
            if len(rule) > len(kept[idx]):
                kept[idx] = rule
            continue
        kept.append(rule)
    raw_rules = kept

    for r in raw_rules[:6]:
        cleaned = r.replace("不要", "").replace("禁止", "").strip("，。 ")
        if not cleaned:
            continue
        good, bad = _build_examples(cleaned, secs, used_examples)
        lang["iron_rules"].append({
            "rule": r if r.startswith(("不要", "禁止")) else f"不要{cleaned}",
            # rationale 不能和 rule 说同一句话——那样等于没解释。
            # 用「该题材的真实写法」作理由：读者要的是"该怎么做"。
            "rationale": _rationale_for(cleaned, secs),
            "good_example": good,
            "bad_example": bad,
        })

    # opening_analysis：schema 要求 chapter_1 对象。字段值取自 prose 卡的
    # 「开场抓手」，位置/字数用通用经验值并注明未标定。
    opening_hint = secs.get("开场抓手", "")
    if opening_hint:
        commercial["opening_analysis"] = {
            "chapter_1": {
                "protagonist_intro_method": opening_hint[:200],
                "first_300_words_task": "开场 300 字内让读者知道：主角是谁、卡在什么处境、代价是什么。",
                "conflict_intro_position": 600,
                "hook_position": 400,
                "golden_finger_reveal": "若有金手指/核心优势，只展示结果与代价，不解释原理。",
            },
            "chapter_2_3_task": "第 2 章把压力具体化（一个对手、一个期限、一个缺口）；第 3 章给第一次实质推进。",
            "common_mistakes": [r.replace("不要", "").strip("，。 ") for r in raw_rules[:4]],
        }

    # 剧情弧线：把「前中后期打法」拆成条目（形如 "- 前期：xxx"）
    arc_text = structure["arc_rhythm"].pop("arc_template_text", "")
    if arc_text:
        items = []
        for line in arc_text.splitlines():
            s = line.strip().lstrip("-•").strip()
            if s:
                items.append(s)
        structure["arc_rhythm"]["arc_template"] = items

    meta = {
        "id": f"genre-{genre_slug}",
        "name": meta_in.get("name") or genre_slug,
        "sub_tags": list(meta_in.get("sub_tags") or []),
        "target_platform": meta_in.get("target_platform") or "长篇通用",
        # 派生包置信度低于原卡：结构化搬运可靠，但数值未标定
        "confidence": round(min(0.5, float(meta_in.get("confidence") or 0.4)), 2),
        "scope": "genre-generalized",
        "source": f"genre-prose-card-genre-{genre_slug}",
        "source_books": [{
            "title": f"genre-prose-card-genre-{genre_slug}（题材文风卡泛化）",
            "note": "非单书蒸馏；结构字段搬运自文风卡原文，数值字段为通用默认值",
        }],
        "note": (
            f"由 genre-prose-card-genre-{genre_slug}.json 派生（2026-11-02）。"
            "structure / language_rules / world_conventions 的文本搬运自文风卡原文；"
            "commercial / quality_thresholds / chapter_word_range 的**数值未经该题材实测标定**，"
            "为通用默认值，接入具体书籍蒸馏数据后应重新标定。"
        ),
        "provenance": {
            "source": f"novel-lab 项目内 genre-prose-card-genre-{genre_slug}.json 泛化",
            "license": "MIT",
            "copyright": "Copyright (c) 2026 novel-lab",
            "verified": False,
            "note": "衍生链归因声明：写法为转述综合，非复制原文；未引用任何具体小说实测数据。",
        },
    }
    meta["derived_sections"] = moved

    return {
        "meta": meta,
        "structure": structure,
        "commercial": commercial,
        "language_rules": lang,
        "world_conventions": world,
        "quality_thresholds": dict(CATEGORY_DEFAULTS["quality_thresholds"]),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="由题材文风卡派生 genre-pack（补齐缺失题材）")
    ap.add_argument("--dry-run", action="store_true", help="只列出将生成的文件，不写盘")
    args = ap.parse_args(argv)

    prose_files = sorted(ASSETS.glob("genre-prose-card-genre-*.json"))
    prose_files = [p for p in prose_files if "index" not in p.name]
    if not prose_files:
        print("未找到任何题材文风卡", file=sys.stderr)
        return 1

    created = skipped = 0
    for pf in prose_files:
        slug = pf.name.replace("genre-prose-card-genre-", "").replace(".json", "")
        out = ASSETS / f"{slug}-genre-pack.json"
        if out.exists():
            skipped += 1
            continue
        if args.dry_run:
            print(f"  将生成: {out.name}")
            created += 1
            continue
        card = _load(pf)
        pack = build_pack(card, slug)
        with out.open("w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(pack, ensure_ascii=False, indent=1) + "\n")
        created += 1
        print(f"  已生成: {out.name}  ({pack['meta']['name']})")

    verb = "将生成" if args.dry_run else "已生成"
    print(f"\n{verb} {created} 个，跳过已存在 {skipped} 个")
    return 0


if __name__ == "__main__":
    sys.exit(main())
