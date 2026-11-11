# novel-lab · 网文拆书与创作工作台

**中文** ｜ [English](README.en.md)

[![CI](https://github.com/monesyilya3-Niko/novel-dissection-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/monesyilya3-Niko/novel-dissection-lab/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) ![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white) ![Zero Deps](https://img.shields.io/badge/backend-stdlib--only-success)

把优秀小说拆成可复用的结构化资产，再用这些资产驱动 AI 创作。

> **Turn good novels into reusable structured assets, then let those assets drive AI-assisted writing.**

novel-lab 是一套本地优先（local-first）的网文创作辅助系统，覆盖全链路：

```
导入语料 → 拆书分析（多遍扫描） → 多维资产蒸馏 → 万字分析报告 → 质量检查 → 资产注入辅助写作
```

双形态交付：**CLI 引擎**（`novel.py`，24 个子命令）+ **GUI 工作台**（浏览器访问 `http://127.0.0.1:8000/`）。

> 🏛️ **核心理念宪章**：[CORE_PHILOSOPHY.md](CORE_PHILOSOPHY.md) ｜ [English](CORE_PHILOSOPHY_EN.md)
> 📖 **人类作者指南**：[docs/USER_GUIDE.md](docs/USER_GUIDE.md)
> 🤖 **外部智能体调用**：[docs/AGENT_API.md](docs/AGENT_API.md) —— Qoder / Cline / Claude / OpenCode / Antigravity 等桌面 Agent 请优先走 HTTP API

| 亮色首页 | 暗色写作台 |
|---|---|
| ![亮色首页](docs/screenshots/home-light.png) | ![暗色写作台](docs/screenshots/writing-dark.png) |

---

## 目录 / Table of Contents

- [下载安装](#下载安装--installation)
- [功能总览](#功能总览--features)
- [快速开始](#快速开始--quick-start)
- [架构](#架构--architecture)
- [开发](#开发--development)
- [安全模型](#安全模型--security-model)
- [许可证](#许可证--license)

---

## 下载安装 / Installation

从 [Releases](https://github.com/monesyilya3-Niko/novel-dissection-lab/releases) 下载：

| 产物 | 适合 | 用法 |
|---|---|---|
| `novel-lab-setup-v*.exe` | 普通用户 | 双击安装（免管理员），开始菜单/桌面快捷方式启动 |
| `novel-lab-portable-v*.zip` | 便携场景 | 解压后双击 `Start.bat` |

两者都**内置 Python 运行时**，无需安装任何依赖；完全本地运行，不上传任何数据。

> Both packages bundle a Python runtime — no dependencies to install. Everything runs locally; no data leaves your machine.

> ⚠️ 安装包**未做代码签名**，Windows SmartScreen 会提示"未知发布者"，需手动点击"更多信息 → 仍要运行"。
> The installer is **not code-signed**; Windows SmartScreen will warn about an unknown publisher.

---

## 功能总览 / Features

| 模块 | 能力 |
|---|---|
| **拆书引擎** Deconstruction | TXT 全本 → 分层采样 → 量化 → 多遍扫描 → 归一化 → 结构化资产 |
| **资产体系** Asset system | 声线卡 / 笔法卡 / 结构观测 / 商业观测 / 题材包 / 蒸馏资产 / 题材文风卡 / 桥段库 |
| **写作工作台** Writing studio | 创作者全景大盘（速率折线 / 情绪波形 / 爽点雷达）+ 细纲原子重排 + 人物卡树 + 双栏审校对比 |
| **润色与去 AI 味** De-slop | 多维度纯算法诊断（假大空修辞、直白情绪喊话、极端程度词、口癖词、「让」字句、同构排比） |
| **出版级导出** Export | Word (.docx) 纯标准库 OpenXML 构建 + Markdown + 纯文本 + EPUB 3.0 + Shunn 投稿格式 |
| **质检台** Quality control | 单章检查（12 维百分制）+ 全书质检（6 类）+ QC 四层十二维 |
| **题材隔离** Genre isolation | 不同题材的资产/配置严格隔离，聚合与注入全链路校验 |
| **多平台适配** Platform fit | 起点 / 番茄 / 晋江 / 知乎 / Royal Road / Amazon KDP / Webnovel 合规体检与排版 |

---

## 快速开始 / Quick Start

### 方式一：绿色版（需要本机已装 Python 3.10+）

```bash
git clone https://github.com/monesyilya3-Niko/novel-dissection-lab.git
cd novel-dissection-lab
./Start.bat        # 双击亦可；自动探测 python 并启动 GUI
```

启动后浏览器自动打开 `http://127.0.0.1:8000/`。

### 方式二：CLI 引擎

```bash
python novel.py 状态                                        # 查看项目状态
python novel.py 拆书 book.txt --genre campus-redemption     # 拆一本新书
python novel.py 注入 voice.json                             # 资产生成写作 prompt
python novel.py 检查 chapter.txt --voice voice.json         # 章节质量检查
```

完整命令清单见 `python novel.py --help`（共 24 个子命令）。

### 方式三：GUI 工作台

```bash
python -m gui.launch
```

首页概览 / 拆书分析 / 资产库 / 写作台 / 质检台 / 高级（蒸馏·批量·资产编辑）/ 系统状态。

---

## 架构 / Architecture

```
前端  Vite + React + MUI + ECharts（预构建产物入库，用户免装 Node）
  │  HTTP REST + SSE（134 个端点，详见 AGENTS.md §7）
后端  Python 纯标准库（http.server + sqlite3，零第三方依赖）
  │  同进程 engine_adapter
引擎  scripts/ 纯标准库脚本（pipeline / qc / distill / write / report …）
```

**四条项目铁律**（违反即视为 bug，CI 自动守护）：

1. **题材隔离** —— 聚合题材包时 `source_books` 的 genre 必须全一致，不一致 `sys.exit(1)`
2. **万字报告硬校验** —— 拆书报告 + 笔法分析合计 ≥ 10000 字符，不足阻断交付
3. **纯标准库** —— `scripts/` 与 `gui/` 后端零第三方依赖
4. **语料高准入** —— 单本 ≥ 300,000 字、≥ 60 章、均章 1,500 ~ 4,000 字

> Four iron laws, enforced by CI: genre isolation · ≥10,000-char report gate · stdlib-only backend · strict corpus admission.

---

## 开发 / Development

```bash
python run_tests.py                    # 全量测试（当前基线见 AGENTS.md §7）
git config core.hooksPath .githooks    # 启用提交前自动测试
ruff check .                           # 代码风格（CI 强制）
```

开发规范、架构约束与贡献流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。
项目规约（AI 协作者必读）见 [AGENTS.md](AGENTS.md)。

---

## 安全模型 / Security Model

本应用设计为**仅本机使用**：服务硬绑定 `127.0.0.1`，无公网暴露。可选 token 认证见 [SECURITY.md](SECURITY.md)。

> Designed for local use only: the server binds to `127.0.0.1` and is never exposed publicly.

---

## 许可证 / License

[MIT](LICENSE) ｜ 本仓库不包含任何受版权保护的范文语料，`corpus/` 仅存在于本地。

> This repository contains no copyrighted source texts; `corpus/` exists locally only.

---

## English

A **local-first** toolkit for Chinese web-novel deconstruction and AI-assisted writing.

It takes a full novel, splits it into structured assets (voice cards, craft cards,
structure/commercial observations, genre packs, distilled rules, trope libraries),
then uses those assets to guide generation — all running offline on the Python
standard library.

**Highlights**

- **Deconstruction engine** — layered sampling → metrics → multi-pass LLM scan → normalized assets
- **Writing studio** — creator dashboard, outline reordering, character trees, side-by-side revision
- **De-slop diagnostics** — pure-algorithm detection of AI-flavored prose patterns
- **Publication-grade export** — DOCX / Markdown / TXT / EPUB 3.0 / Shunn manuscript format
- **Quality control** — 12-dimension single-chapter scoring, 6-category whole-book audit
- **Genre isolation** — assets never leak across genres, enforced at aggregation time
- **Multi-platform fit** — Qidian / Fanqie / Jinjiang / Zhihu / Royal Road / Amazon KDP / Webnovel

**Requirements** — Python 3.10+ (stdlib only, no `pip install`). Node is only needed
if you want to rebuild the frontend.

**Quick start**

```bash
git clone https://github.com/monesyilya3-Niko/novel-dissection-lab.git
cd novel-dissection-lab
python -m gui.launch          # opens http://127.0.0.1:8000/
```

See [README.en.md](README.en.md) for the full English documentation.
