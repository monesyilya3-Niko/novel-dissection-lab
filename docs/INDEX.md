# 文档索引 · Documentation Index

**中文** ｜ [English](#english)

本文件是 `docs/` 与仓库根目录所有文档的导航。按「**我该读哪份**」组织，不按文件名排序。

---

## 一、第一次接触项目

| 顺序 | 文件 | 读它解决什么 |
|---|---|---|
| 1 | [README.md](README.md) ｜ [EN](README.en.md) | 这是什么、怎么装、怎么跑 |
| 2 | [CORE_PHILOSOPHY.md](CORE_PHILOSOPHY.md) ｜ [EN](CORE_PHILOSOPHY_EN.md) | 👑 为什么这样设计——最高宪章，四条铁律 |
| 3 | [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | 完整使用手册、流程图、快捷键 |
| 4 | [docs/internal/HANDOFF_2026-11-11.md](docs/internal/HANDOFF_2026-11-11.md) | **接手开发先读这份**——54 个提交的完整记录、41 项修复、仓库整理与双语化、已知环境问题 |
| 5 | [docs/internal/HANDOFF_2026-11-06.md](docs/internal/HANDOFF_2026-11-06.md) | 上一份交接（40 项修复的详细分类） |

> AI 协作者请改为从 [AGENTS.md](AGENTS.md) 开始，那是可执行的硬约束。

---

## 二、权威规则（冲突时以此为准）

| 文件 | 地位 | 管的范围 |
|---|---|---|
| [CORE_PHILOSOPHY.md](CORE_PHILOSOPHY.md) | 👑 **最高权威** | 思想基石、四条铁律、创作者主权 |
| [docs/internal/PROJECT_LAW.md](docs/internal/PROJECT_LAW.md) | ✅ 权威 | 规则单一来源（铁律判定标准 + 事故依据） |
| [AGENTS.md](AGENTS.md) | ✅ 权威 | AI 协作者可执行约束 + **当前实测口径**（§7） |
| [CONTRIBUTING.md](CONTRIBUTING.md) | ✅ 权威 | 贡献流程、架构约束、提交规范 |
| [SECURITY.md](SECURITY.md) | ✅ 权威 | 安全模型、漏洞报告、密钥泄露应急 |
| [docs/internal/RULES.md](docs/internal/RULES.md) | ✅ 大体可用 | 操作层细则全集 |

**数字口径**：资产数、测试数、端点数、版本号只在 [AGENTS.md §7](AGENTS.md) 维护。
其他地方出现数字一律视为过时，以 §7 为准。

---

## 三、对外接口

| 文件 | 读者 | 内容 |
|---|---|---|
| [docs/AGENT_API.md](docs/AGENT_API.md) | 外部桌面 Agent | HTTP RESTful API 完整手册 + Python SDK |
| [MODELS.md](MODELS.md) | 配置模型的人 | 支持的模型协议、参数、成本 |
| [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) | 合规审查 | 第三方资产逐张登记 + 许可证归属 |

---

## 四、设计与实现

### GUI 与前端

| 文件 | 内容 |
|---|---|
| [docs/DESIGN_gui_workbench.md](docs/DESIGN_gui_workbench.md) | 工作台整体设计 |
| [docs/DESIGN_gui_persistence.md](docs/DESIGN_gui_persistence.md) | 持久化层（SQLite + JSON 镜像） |
| [docs/DESIGN_gui_book_analyzer.md](docs/DESIGN_gui_book_analyzer.md) | 拆书分析器设计 |
| [docs/DESIGN_gui_phase2_writing_quality.md](docs/DESIGN_gui_phase2_writing_quality.md) | 阶段二：写作与质量（W10-W18） |
| [docs/PRD_gui_*.md](docs/) | 对应 PRD |
| [docs/class-diagram.mermaid](docs/class-diagram.mermaid) | 类图 |
| [docs/sequence-diagram.mermaid](docs/sequence-diagram.mermaid) | 时序图 |

### 引擎与检索

| 文件 | 内容 |
|---|---|
| [docs/system_design.md](docs/system_design.md) | 蒸馏层架构（2026-09-07） |
| [docs/system_design_v2.md](docs/system_design_v2.md) | 技法归一化 + 语义检索桥接 |
| [docs/system_design_P0_semantic_retrieval.md](docs/system_design_P0_semantic_retrieval.md) | 语义检索（BM25 + 向量融合） |
| [docs/system_design_P1_trope_library.md](docs/system_design_P1_trope_library.md) | 桥段库 |
| [docs/system_design_P2_threshold_adaptation.md](docs/system_design_P2_threshold_adaptation.md) | 阈值自适应 |
| [docs/system_design_P3_genre_isolation_report.md](docs/system_design_P3_genre_isolation_report.md) | 题材隔离报告 |
| [docs/ARCH_llm_hook_causality.md](docs/ARCH_llm_hook_causality.md) | LLM hook 因果链 |
| [docs/ARCH_genre-prose-card-port.md](docs/ARCH_genre-prose-card-port.md) | 题材文风卡移植架构 |

### 口径与取舍

| 文件 | 内容 |
|---|---|
| [docs/detection-authority.md](docs/detection-authority.md) | **同类检测谁为准**（重复检测 / 钩子 / 开头口径） |
| [docs/lint-debt.md](docs/lint-debt.md) | 有意豁免的存量风格债 |

---

## 五、语料库与实操

| 文件 | 内容 |
|---|---|
| [RULES_100_BOOKS.md](RULES_100_BOOKS.md) | 100 本严选建库规则 |
| [WORK_LOG_100_BOOKS.md](WORK_LOG_100_BOOKS.md) | 建库台账（由数据库生成，勿手改） |
| [docs/指纹拆书_使用说明.md](docs/指纹拆书_使用说明.md) | 指纹式拆书实操 |
| [docs/拆书经验总结_溯雨信笺_2026-09-07.md](docs/拆书经验总结_溯雨信笺_2026-09-07.md) | 实战经验复盘 |
| [docs/技能选用决策表.md](docs/技能选用决策表.md) | 技能包选型 |
| [docs/desktop-research.md](docs/desktop-research.md) | 桌面版技术调研 |

---

## 六、路线与历史

| 文件 | 状态 |
|---|---|
| [ROADMAP.md](ROADMAP.md) | 路线图 |
| [CHANGELOG.md](CHANGELOG.md) | ⚠️ 由 release workflow 从 Conventional Commits 生成，**勿手改** |
| [docs/internal/HANDOFF_2026-11-02.md](docs/internal/HANDOFF_2026-11-02.md) | 上一份交接（架构部分仍权威） |
| [docs/internal/ACCEPTANCE_2026-09-28.md](docs/internal/ACCEPTANCE_2026-09-28.md) | 阶段性验收记录 |
| [docs/internal/perf_2026-09-28.json](docs/internal/perf_2026-09-28.json) | 性能基线快照 |
| [docs/archive/](docs/archive/) | 早期方案与验证报告（**历史存档，勿作依据**） |
| [docs/superpowers/](docs/superpowers/) | 历次优化轮次的计划与设计 |
| [docs/compose/spec/](docs/compose/spec/) | Compose Next 特性记录 |
| [docs/novel-lab_*.md](docs/) | 2026-09 的整改进度与完整度报告（历史） |

---

## 七、English

### Where to start

| Order | File | What it answers |
|---|---|---|
| 1 | [README.en.md](README.en.md) ｜ [中文](README.md) | What is this, how to install, how to run |
| 2 | [CORE_PHILOSOPHY_EN.md](CORE_PHILOSOPHY_EN.md) ｜ [中文](CORE_PHILOSOPHY.md) | 👑 Why it is built this way — supreme charter, four iron laws |
| 3 | [AGENTS.md](AGENTS.md) | Executable hard constraints (Chinese) |

### Authoritative rules

When documents disagree, this is the precedence order:

1. [CORE_PHILOSOPHY.md](CORE_PHILOSOPHY.md) — supreme authority
2. [docs/internal/PROJECT_LAW.md](docs/internal/PROJECT_LAW.md) — single source of rules
3. [AGENTS.md](AGENTS.md) — executable constraints + **the** current metrics (§7)
4. [CONTRIBUTING.md](CONTRIBUTING.md) — workflow and architectural limits
5. [SECURITY.md](SECURITY.md) — security model and disclosure

**Numbers** (asset count, test count, endpoint count, version) live only in
[AGENTS.md §7](AGENTS.md). Anywhere else, treat them as historical.

### Interfaces

| File | Audience |
|---|---|
| [docs/AGENT_API.md](docs/AGENT_API.md) | External desktop agents — full HTTP API manual |
| [MODELS.md](MODELS.md) | Model protocol support and pricing |
| [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) | Third-party asset attribution |

### Design

`docs/DESIGN_gui_*.md`, `docs/PRD_gui_*.md`, `docs/system_design*.md`, and the
`.mermaid` diagrams cover the design history. Most are in Chinese; the code is the
final authority.

### Historical

`docs/archive/`, `docs/superpowers/`, and the dated `docs/novel-lab_*.md` reports
are **archived material** — useful context, not current guidance.
