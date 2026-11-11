# 贡献指南 · Contributing

**中文** ｜ [English](#english)

感谢关注 novel-lab。动手之前请先读完本文——这个项目有几条不太常见的硬约束。

> Thanks for your interest. Please read this first — the project has a few unusual hard constraints.

---

## 环境准备 · Setup

- Windows 10/11 + Git Bash（开发环境按此假设；代码本身跨平台）
- Python 3.10+（开发机实际使用 3.13）
- Node 22 + npm（仅前端开发需要；`gui/web/dist` 预构建产物入库，纯后端开发免装）

```bash
git clone https://github.com/monesyilya3-Niko/novel-dissection-lab.git
cd novel-dissection-lab
git config core.hooksPath .githooks   # 启用提交前自动测试（强烈建议）
python run_tests.py                    # 确认基线全绿
```

---

## 四条铁律 · The Four Iron Laws（违反即视为 bug）

1. **题材隔离 Genre isolation**
   不同题材的资产/配置严格隔离。聚合题材包时 `source_books` 的 genre 必须全部一致，
   不一致显式 `sys.exit(1)`，禁止静默跳过。

2. **万字报告硬校验 Report length gate**
   拆书报告 + 笔法分析**合计**字符数 ≥ 10000。判定单一来源在
   `scripts/report.py::combined_report_ok`，禁止另立口径。

3. **纯标准库 Stdlib only**
   `scripts/` 与 `gui/` 后端只能 import Python 标准库
   （sqlite3 / json / urllib / http.server / ctypes 等）。
   前端（Vite + React）不受此约束。CI 会自动扫描违规 import。

4. **语料高准入 Strict corpus admission**
   单本正文字数 ≥ 300,000 字、章节数 ≥ 60、均章 1,500 ~ 4,000 字。
   判定实现在 `scripts/batch_100_books.py::is_acceptable_webnovel`，
   与 `CORE_PHILOSOPHY.md` / `docs/internal/PROJECT_LAW.md` 逐字对齐。

---

## 架构约束 · Architectural Constraints

- `gui/engine_adapter.py` 是**唯一** import `scripts/` 的层
- `gui/db.py` 是**唯一** import `sqlite3` 的层
- 路径常量唯一来源：`gui/config.py`；新增路径常量必须同步登记
  `tests/_isolation.py::DATA_PATH_CONSTANTS`，否则测试隔离防线会 FAIL
- `gui_state/`（SQLite）是运行时唯一权威数据源；`gui/state/` 只是派生镜像，均不入库

---

## 测试纪律 · Testing Discipline

- 提交前 pre-commit 钩子会跑全量测试，红测试阻止提交
  （绕过：`--no-verify`，仅限紧急且需在提交信息中说明）
- 新功能必须带测试；测试涉及路径常量时必须 patch **全部**相关常量并在
  `tearDownClass` 恢复（历史血泪教训见 `AGENTS.md` §4）
- 数据真实性红线：文档中的数字以实测磁盘为准，不得臆造或沿用旧口径

---

## 提交规范 · Commit Convention

[Conventional Commits](https://www.conventionalcommits.org/)：

```
feat|fix|docs|refactor|test|chore: 摘要

正文说明动机（可选）。
```

一次提交只做一件事。**版本号由 Agent 自主递增**（授权见 `AGENTS.md` §7
「发布与版本授权」），递增时须同步 6 + 2 处标记点并重建前端 dist。

`CHANGELOG.md` 不要手改——发版说明由 `.github/workflows/release.yml`
在推送 `v*` tag 时从 Conventional Commits 自动生成。

---

## 提交什么、绝不提交什么 · What to Commit / Never Commit

**绝不提交 Never commit:**

- API 密钥 `config/.secrets.json` / `.secrets.bin`
- 范文语料 `corpus/`（版权材料）
- 运行时数据 `gui_state/`、`gui/state/`、`novel/`
- 用户数据目录内容（`%LOCALAPPDATA%\暮冬念春`）

`.gitignore` 已覆盖上述大部分，但请自觉。

**发现密钥疑似泄露** → **立即**按 [SECURITY.md](SECURITY.md) 报告，不要先开 issue。

---

## Pull Request

- 描述写清楚：改了什么、为什么、如何验证（贴测试输出）
- 保持提交历史整洁（squash 或按功能分组）
- CI 全绿是合并前提

---

## English

Thanks for your interest in novel-lab. Before you start, read the constraints below —
several of them are unusual.

### Setup

- Windows 10/11 + Git Bash (the dev environment assumes this; the code itself is cross-platform)
- Python 3.10+ (the dev machine runs 3.13)
- Node 22 + npm (frontend development only; `gui/web/dist` is pre-built and committed,
  so backend-only work needs no Node at all)

```bash
git clone https://github.com/monesyilya3-Niko/novel-dissection-lab.git
cd novel-dissection-lab
git config core.hooksPath .githooks   # enable pre-commit test hook (strongly recommended)
python run_tests.py                    # confirm the baseline is green
```

### The four iron laws

Violating any of these is treated as a bug.

1. **Genre isolation** — when aggregating a genre pack, every `source_books` entry must
   share the same genre; otherwise `sys.exit(1)`. No silent skips.
2. **Report length gate** — deconstruction report + craft analysis must total
   **≥ 10,000 characters**. Single source of truth: `scripts/report.py::combined_report_ok`.
3. **Stdlib only** — `scripts/` and the `gui/` backend may import the Python standard
   library exclusively. The frontend (Vite + React) is exempt. CI scans for violations.
4. **Strict corpus admission** — a source book must be ≥ 300,000 characters, ≥ 60 chapters,
   and 1,500–4,000 characters per chapter on average. Implemented in
   `scripts/batch_100_books.py::is_acceptable_webnovel`.

### Architectural constraints

- `gui/engine_adapter.py` is the **only** layer allowed to import `scripts/`
- `gui/db.py` is the **only** layer allowed to import `sqlite3`
- Path constants have a single source: `gui/config.py`. Adding a new one requires
  registering it in `tests/_isolation.py::DATA_PATH_CONSTANTS`, or the isolation guard
  will fail.
- `gui_state/` (SQLite) is the authoritative runtime data source; `gui/state/` is only a
  derived mirror. Neither is committed.

### Testing discipline

- The pre-commit hook runs the full suite and blocks on failure. Bypass with
  `--no-verify` only in emergencies, and explain why in the commit message.
- New features need tests. If a test touches path constants, you must patch **all**
  of them and restore in `tearDownClass`.
- Numbers in documentation must be measured, never carried over from older docs.

### Commit convention

[Conventional Commits](https://www.conventionalcommits.org/): `feat|fix|docs|refactor|test|chore: summary`.

One logical change per commit. Version bumps are made by the agent autonomously
(see `AGENTS.md` §7); bumping requires updating the version markers across 6 files
plus 2 placeholders and rebuilding the frontend `dist`. Never edit `CHANGELOG.md`
by hand — release notes are generated from Conventional Commits by
`.github/workflows/release.yml` when a `v*` tag is pushed.

### Never commit

API keys (`config/.secrets*.json`, `.secrets.bin`), source corpus (`corpus/`),
runtime data (`gui_state/`, `gui/state/`, `novel/`), or user data
(`%LOCALAPPDATA%\暮冬念春`).

**Suspected key leak** → report per [SECURITY.md](SECURITY.md) immediately; do not
open a public issue first.

### Pull requests

Describe what changed, why, and how you verified it (include test output). Keep history
tidy. CI must be green before merge.
