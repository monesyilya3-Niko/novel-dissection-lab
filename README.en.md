# novel-lab · Web Novel Deconstruction & Writing Workbench

[中文](README.md) ｜ **English**

[![CI](https://github.com/monesyilya3-Niko/novel-dissection-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/monesyilya3-Niko/novel-dissection-lab/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) ![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white) ![Zero Deps](https://img.shields.io/badge/backend-stdlib--only-success)

Turn good novels into reusable structured assets, then let those assets drive AI-assisted writing.

novel-lab is a **local-first** workbench for Chinese web-novel deconstruction and
writing assistance. The full pipeline:

```
Import corpus → Deconstruct (multi-pass scan) → Distill multi-dimensional assets
→ 10k+ character analysis reports → Quality inspection → Inject assets into writing
```

Two delivery forms: a **CLI engine** (`novel.py`, 24 subcommands) and a
**GUI workbench** (browser at `http://127.0.0.1:8000/`).

> 🏛️ **Core philosophy**: [CORE_PHILOSOPHY_EN.md](CORE_PHILOSOPHY_EN.md) ｜ [中文](CORE_PHILOSOPHY.md)
> 📖 **User guide**: [docs/USER_GUIDE.md](docs/USER_GUIDE.md) (Chinese)
> 🤖 **Agent integration**: [docs/AGENT_API.md](docs/AGENT_API.md) — desktop agents (Qoder / Cline / Claude / OpenCode / Antigravity) should prefer the HTTP API over the CLI

| Light home | Dark writing studio |
|---|---|
| ![Light home](docs/screenshots/home-light.png) | ![Dark studio](docs/screenshots/writing-dark.png) |

---

## Installation

Download from [Releases](https://github.com/monesyilya3-Niko/novel-dissection-lab/releases):

| Artifact | For | How to use |
|---|---|---|
| `novel-lab-setup-v*.exe` | Regular users | Double-click to install (no admin needed); launch from Start Menu / desktop shortcut |
| `novel-lab-portable-v*.zip` | Portable use | Unzip, then double-click `Start.bat` |

Both bundles include a **Python runtime** — no dependencies to install.
Everything runs locally; no data leaves your machine.

> ⚠️ The installer is **not code-signed**. Windows SmartScreen will show an
> "unknown publisher" warning — click *More info → Run anyway*.

---

## Requirements

- **Python 3.10+** for the CLI and backend (standard library only — no `pip install`)
- **Node.js 22+** only if you want to rebuild the frontend from source
- No database server, no external services, no network access required at runtime

---

## Features

| Module | Capability |
|---|---|
| **Deconstruction engine** | Full TXT → layered sampling → metrics → multi-pass scan → normalization → structured assets |
| **Asset system** | Voice cards / craft cards / structure observations / commercial observations / genre packs / distilled rules / genre-prose cards / trope library |
| **Writing studio** | Creator dashboard (output-rate curves, emotional waveforms, payoff radar) + atomic outline reordering + character trees + side-by-side revision compare |
| **De-slop diagnostics** | Multi-dimensional pure-algorithm detection: hollow rhetoric, direct emotion shouting, extremity words, verbal tics, filler constructions, parallel-structure repetition |
| **Publication-grade export** | Word (.docx) via pure-stdlib OpenXML + Markdown + plain text + EPUB 3.0 + Shunn manuscript format |
| **Quality control** | Single-chapter check (12 dimensions, 100-point scale) + whole-book audit (6 categories) + QC four-layer twelve-dimension |
| **Genre isolation** | Assets and configs are strictly isolated per genre; enforced across aggregation and injection |
| **Multi-platform fit** | Compliance checks and formatting for Qidian / Fanqie / Jinjiang / Zhihu / Royal Road / Amazon KDP / Webnovel |

---

## Quick Start

### Option 1 — Portable package (requires Python 3.10+ installed)

```bash
git clone https://github.com/monesyilya3-Niko/novel-dissection-lab.git
cd novel-dissection-lab
./Start.bat          # or double-click; auto-detects python and launches the GUI
```

The browser opens `http://127.0.0.1:8000/` automatically.

### Option 2 — CLI engine

```bash
python novel.py 状态                                        # project status
python novel.py 拆书 book.txt --genre campus-redemption     # deconstruct a new book
python novel.py 注入 voice.json                             # assets → writing prompt
python novel.py 检查 chapter.txt --voice voice.json         # chapter quality check
```

Run `python novel.py --help` for the full command list (24 subcommands).

> The CLI subcommand names are Chinese. This is intentional — the primary audience
> writes in Chinese, and `拆书` / `检查` are the terms they use.

### Option 3 — GUI workbench

```bash
python -m gui.launch
```

Workbenches: Overview / Analysis / Asset Library / Writing / Quality / Advanced
(distill · batch · asset editor) / System.

---

## Architecture

```
Frontend   Vite + React + MUI + ECharts
             (pre-built into the repo — end users don't need Node)
    │  HTTP REST + SSE  (134 endpoints, see AGENTS.md §7)
Backend    Python standard library only
             (http.server + sqlite3, zero third-party dependencies)
    │  in-process engine adapter
Engine     scripts/ — pure-stdlib modules
             (pipeline / qc / distill / write / report …)
```

### The four iron laws

Violating any of these is treated as a bug, and CI enforces them:

1. **Genre isolation** — when aggregating a genre pack, every `source_books` entry
   must share the same genre; otherwise `sys.exit(1)`. No silent skips.
2. **Report length gate** — deconstruction report + craft analysis must total
   **≥ 10,000 characters**; below that, delivery is blocked.
3. **Stdlib only** — `scripts/` and the `gui/` backend use the Python standard
   library exclusively. No `pip install`, ever.
4. **Strict corpus admission** — a source book must be ≥ 300,000 characters,
   ≥ 60 chapters, and 1,500–4,000 characters per chapter on average.

---

## Development

```bash
python run_tests.py                    # full test suite (baseline: see AGENTS.md §7)
git config core.hooksPath .githooks    # enable pre-commit test hook
ruff check .                           # lint (enforced by CI)
```

- Contribution workflow and architectural constraints: [CONTRIBUTING.md](CONTRIBUTING.md)
- Project rules (required reading for AI collaborators): [AGENTS.md](AGENTS.md)

**Test baseline**: see `AGENTS.md` §7 for the authoritative count (single source of truth —
the README deliberately does not hardcode it, to avoid drift).
**CI matrix**: Python 3.11 / 3.12 / 3.13 on Ubuntu, 3.13 on Windows, plus frontend build + lint + unit tests.

### Frontend rebuild

```bash
cd gui/web
npm ci
npm run build          # outputs to gui/web/dist/ (committed — CI checks freshness)
npm run test -- --run
```

---

## Security Model

This application is designed for **local use only**:

- The HTTP server binds to `127.0.0.1` — never exposed to the network
- Optional token authentication (see [SECURITY.md](SECURITY.md))
- API keys are stored with Windows DPAPI (`config/.secrets.bin`), never in the repo
- No telemetry, no outbound connections except to the LLM endpoint you configure

---

## Data Locations

| What | Where |
|---|---|
| Project data (database, corpus, assets) | `%LOCALAPPDATA%\暮冬念春` (Windows) |
| Repository | contains source code only; `corpus/` is local and gitignored |
| API keys | `config/.secrets.bin` (DPAPI-encrypted, machine-bound) |

---

## License

[MIT](LICENSE)

This repository contains no copyrighted source texts. The `corpus/` directory
exists locally only and is gitignored.

---

## 中文

完整中文文档见 [README.md](README.md)。

核心概念：

- **拆书**（deconstruction）— 把一本小说拆成结构化的可复用资产
- **资产**（assets）— 声线卡、笔法卡、结构观测、商业观测、题材包等
- **注入**（injection）— 把资产组装成写作 prompt
- **铁律**（iron laws）— 四条不可违反的工程约束，CI 自动守护
