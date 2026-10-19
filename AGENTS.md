# AGENTS.md — novel-lab 项目规约（AI 协作者必读）

> 🚨 **核心理念与最高宪法**：所有 AI 协作者必须首先研读并无条件遵守根目录 [CORE_PHILOSOPHY.md](CORE_PHILOSOPHY.md)。
> 本文件是**可执行的硬约束**，面向所有 AI 协作者。任何违反即视为 bug。
> 生成日期：2026-09-11 ｜ 项目已从另一套 niko 实例迁移至 niko 工作区

---

## 0. 项目定位

**novel-lab** 是一套网文创作辅助系统，覆盖全链路：

```
导入语料 → 拆书分析(pass1-4) → 多维资产蒸馏 → 万字报告 → 质检 → 题材包/文风卡 → 注入辅助写作
```

双形态交付：**CLI 引擎**（`novel.py`，20+ 子命令）+ **GUI 工作台**（浏览器访问 `http://127.0.0.1:8000/`，Python 标准库常驻 + 预构建前端）。

> 外部桌面智能体（Qoder / Cline / Claude / OpenCode / Antigravity）调用本项目时，
> **优先使用 HTTP API**（CLI 仅作一次性备选），调用手册见 [docs/AGENT_API.md](docs/AGENT_API.md)。

---

## 1. 四条核心铁律（违反即视为 bug）

### 铁律一：题材隔离
- 不同题材的资产/配置严格隔离，注入时按题材匹配，**禁止跨题材污染**
- 执行机制：聚合题材包时 `source_books` 的 genre 必须全部一致，不一致 → `pass5_aggregate.py` 显式断言 + `sys.exit(1)`，禁止静默跳过
- 执行机制：`craft-card.meta.genre` 必须 ∈ `CORE_GENRES`（完整链题材白名单，`validate.py` 校验；warn 级，不阻断拆书但阻断聚合）
- 执行机制：题材集**不存在人工维护清单**——由 `scripts/genre_registry.py` 扫描 `assets/` 派生（`CORE_GENRES` 完整链 ∪ `PROSE_GENRES` prose 卡 = `KNOWN_GENRES`），磁盘是唯一真相源
- 执行机制：`genre-prose-card.meta.id` 必须符合 `genre-<slug>` 命名规范，且文件名与之严格对应（`tests/test_genre_registry.py` 双向守卫）
- 执行机制：桥段库每个 trope 必须标注 `genre_scope`（universal / 题材专属 id）

### 铁律二：万字报告硬校验
- 拆书报告 + 笔法分析**合计**字符数 ≥ **10000**（硬门槛）
- 执行机制：`novel.py 分析` 收尾做合计校验，不足 `sys.exit(1)` 阻断交付
- `report.py` / `report_craft.py` 各自单份 < 10000 仅 soft warning，不阻断
- 最终以「分析」命令的合计校验为准

### 铁律三：纯标准库零第三方依赖
- **`scripts/` 与 `gui/` 后端只能用 Python 标准库**（sqlite3 / json / urllib / http.server / ctypes 等）
- 前端层（Vite + React）不受此约束
- 已用 `ctypes` 实现 Windows 进程探活——**禁止引入 psutil** 等替代

### 铁律四：语料极高品质准入
- **所有拿过来使用的书籍，必须是质量极高的书籍**。严禁机翻劣质、公版杂篇、生僻碎片及无参考价值的小说充数
- 执行机制：参考书籍必须为纯正主流中文原创长篇网络小说或文学传世典范（字数 $\ge$ 300,000 字，章节 $\ge$ 60 章）
- 执行机制：精华库必须配置齐全五维核心解构资产（大纲、开篇、人设、桥段、文风）与伏笔暗线
- 执行机制：语料库禁止导入并定期清洗 `book_%` 无名碎片垃圾语料，保障知识库纯净度

---

## 2. 依赖方向禁令（不可倒置）

| 约束 | 说明 |
|---|---|
| `gui/engine_adapter.py` | **唯一** import `scripts/` 的层 |
| `gui/db.py` | **唯一** import sqlite3 的层 |

其他任何模块都不得直接 import `scripts/` 或 `sqlite3`。

---

## 3. 路径常量（唯一来源：`gui/config.py`）

```python
ROOT_DIR       = novel-lab/
SCRIPTS_DIR    = novel-lab/scripts/
WEB_DIR        = novel-lab/gui/web/
DIST_DIR       = novel-lab/gui/web/dist/
ASSETS_ROOT    = novel-lab/assets/
STATE_ROOT     = novel-lab/gui_state/     # 运行时产物：index.db + WAL + .lock + 备份
STATE_JSON_DIR = novel-lab/gui/state/     # 状态 JSON 降级副本（不入库·SQLite 派生镜像）
DB_PATH        = gui_state/index.db       # ← 注意不是 gui/state/
LOCK_PATH      = gui_state/.lock
REPORTS_DIR    = novel-lab/reports/
CORPUS_DIR     = novel-lab/corpus/
CONFIG_DIR     = novel-lab/config/
NOVEL_DIR      = novel-lab/novel/
```

### ⚠️ 路径易混淆点
- **DB 在 `gui_state/index.db`**，状态 JSON 在 `gui/state/`——两者已分离，勿混淆
- `gui_state/` 被 `.gitignore` **整目录**忽略（纯运行时产物）
- `gui/state/` 同样**不入库**（`.gitignore` 整目录忽略）：它是 SQLite 的派生镜像，SQLite 才是唯一权威来源（§6 已裁决）
- **正文路径准入（`gui/text_access.py`）**：打分 `chapter_path`、合规 `book_path`、投稿导出 `book_dir`、
  质检 `target` 一律**不限目录、只限内容**（`.txt`/`.md`、非符号链接、体积与数量上限）。
  旧实现要求"必须在项目目录或用户数据目录内"，用户的稿子放在别处就直接 403，反馈原话是"有些路径放不进去"。
  **别把目录前缀检查加回来**，也别因为它看起来"删掉了安全校验"就回滚：防护目标没变（仍然读不到正文以外的东西），
  只是判据从路径换成了内容。回归锚点在 `tests/test_text_access.py` + `tests/test_security_fixes.py`。
- **正文解码口径**：UTF-8 优先、失败退 GBK（国内 `.txt` 稿子大量是 GBK）。唯一实现在
  `scripts/chapter_loader.read_text_file`，GUI 侧经 `engine_adapter.read_chapter_text` 出口（铁律二：不直连 scripts）。
  只按 UTF-8 读会让真稿报成"读取章节失败"，措辞像路径被禁，实际是编码——别再往回调 `read_text(encoding="utf-8")`。

---

## 4. 测试规范（关键：隔离）

### 运行方式
```bash
python run_tests.py          # 全量门禁（用例数只认 §7 的权威口径行，别在此处另写一份）
```

### 隔离要求（血泪教训）
**新增 config 路径常量时，所有 patch 该类路径的测试必须同步审查。**

已发生的事故 ①（2026-09-11）：`gui/config.py` 的 L2 修复新增 `STATE_JSON_DIR` 后，`tests/test_overview_api.py` 与 `tests/test_asset_index.py` 的 `setUpClass` 只 patch 了 `STATE_ROOT`，漏了 `STATE_JSON_DIR`，导致测试夹具数据写进**真实的 `gui/state/`** 并跨轮累积，造成 2 个测试持续失败。

已发生的事故 ②（2026-09-23）：`gui/system_service.py` 把 settings.json 路径写成**模块级常量** `_SETTINGS_FILE = config.STATE_ROOT / "settings.json"`。该赋值在**导入期**执行、路径被固化，因此 `setattr(config, "STATE_ROOT", tmp)` 这类重定向**对它完全无效**，`tests/test_system_service.py` 实际写进了**真实** `gui_state/settings.json`（受控实验：写入哨兵值 → 跑全量测试 → 哨兵被完全抹掉、内容变成测试入参值）。事故 ① 的防线只覆盖 `gui/state/`，故未能拦住。

**规矩**：
- 测试若涉及路径常量，必须 patch **全部**相关常量，不得只 patch 其中一部分
- patch 后必须在 `tearDownClass` 恢复
- 临时目录要覆盖所有被 patch 的路径
- **运行时路径一律在函数内实时求值**（`config.STATE_ROOT / "x.json"`），禁止写成模块级常量——导入期快照无法被 patch 重定向
- 已有防线测试守护此约束（见 `tests/`），**不得删除或弱化**：
  - `tests/test_config_isolation.py`（登记表全覆盖 + 确定性路径跟随）
  - `tests/test_module_config_snapshot.py`（AST 扫描导入期快照，白名单需附理由）
  - `tests/test_zz_state_dir_leak_guard.py`（`gui/state/` 与 `gui_state/` 双目录泄漏守卫）
  - `tests/test_doc_metrics.py`（`AGENTS.md` §7 口径与实测一致）

### 提交前自动测试守卫
仓库内 `.githooks/pre-commit` 会在每次提交前跑 `python run_tests.py`，失败则阻止提交。
新克隆后启用一次：

```bash
git config core.hooksPath .githooks
```

临时绕过：`git commit --no-verify`。详见 `.githooks/README.md`。

---

## 5. 环境（迁移后）

| 项 | 值 |
|---|---|
| 项目根（唯一权威工作副本） | `C:\Users\monesy\workspace\projects\novel-lab` |
| 主解释器 | `C:/Users/monesy/.niko/binaries/python/versions/3.13.12/python.exe` |
| 解释器版本 | **实际 3.13.14**（目录名 3.13.12 是历史 artifact，属正常） |
| 项目 venv | `C:/Users/monesy/.niko/binaries/python/envs/default`（3.13.14，含 fontTools / numpy / Pillow，仅番茄抓书用） |
| Node | `C:/Program Files/nodejs`（实测 v24.21.0 + npm 11.19.0） |
| npm 镜像 | 实测 `~/.npmrc` 为 `https://registry.npmjs.org/`（官方源本机 `npm ci` 实测可用；旧的 npmmirror 口径已过时） |
| pip 镜像 | 实测 `pip config list` 为空（未配置镜像，走默认源） |
| GitHub | 直连可用（2026-10-08 实测 `git push` 到 origin 成功）；备用镜像 `ghfast.top` |

#### ⚠️ 本机有第二个 novel-lab 克隆（2026-10-08 实测确认）

`C:\Users\monesy\niko\novel-lab` 是**迁移前的旧副本**：分支 `master`、最后提交 `edfae04`（2026-09-23）、
工作区停留在 2026-09-24，68 个文件未提交。它的已提交历史已完整包含于权威副本（`git cat-file -e edfae04` 可验），
但工作区里留着**从未进过任何分支的草稿**（`APP_PLAN.md`、`electron/`、`skills/`，以及 6 个未入库的 React 组件：
AssetEditor / ChapterManager / ExportImportPanel / GlobalSearch / NotificationCenter / QuickStartLoop）。

规矩：
- **只在权威副本开发**。旧副本里改文件、提交，会得到一份 2026-09-23 的陈旧产物。
- **不要删除旧副本**。上述草稿未受版本控制保护，删掉即永久丢失；要清理必须先确认它们已被取代。
- 旧副本的组件草稿若日后需要，从磁盘取回并在新前端结构下重写，不要整目录覆盖 `gui/web/src`。

### Windows / Git Bash 坑（来自 RULES.md 第七节）
1. **路径**：`/c/xxx` 传给 Python 会被当字面路径 → 用 `C:/xxx` 或先 `cd`
2. **删除**：本机沙箱回收站不可用，`shutil.rmtree` 会失败 → 项目内测试数据用逐文件 `unlink` + `rmdir`
3. **tail -c 按字节截断 UTF-8** 会显示乱码 → 用 Python 读文件验证内容
4. **路径叠加**：`cd novel` 后再 init 会创建 `novel/novel` 嵌套 → 统一在项目根操作

---

## 6. 已裁决事项

| # | 事项 | 裁决 |
|---|---|---|
| 1 | `gui/state/` 是否入 git | **不入库**（2026-09-11 裁决）。它是 SQLite（`gui_state/index.db`）的派生镜像，SQLite 才是唯一权威来源；跟踪派生数据会造成双真相源漂移与提交噪声，与「长期稳定可维护」相悖。`.gitignore` 已改为整目录忽略；备份由 `gui_state/*.bak-*` 与 migrate CLI 的 backup 机制承担。 |

---

## 7. 数据真实性红线

- 所有资产/报告数字**以实测磁盘为准**，不得臆造或沿用旧口径
- 当前实测口径（2026-10-19）：资产 **105** / 报告 **12** / 书 **9**（已拆 7，磁盘语料 2）/ 测试 **2193** / API 端点 **130** / 版本 **2.2.0**
  - ⚠️ "资产 105" 指 `assets/*.json` **文件数**（也是 `assets-manifest.json` 的登记数、桌面打包校验用的数）。UI 首页"资产总数"与 `/api/overview.total_assets` 在干净环境下报的是 **104**：`trope-library.json` 是桥段库**容器**、不是资产卡，`asset_index` 按 `ASSET_KINDS` 计数时有意排除（同口径还排除 report/book 虚拟 kind）。两个数都对，别再互相"纠正"。（版本号 2.0.3→2.1.0，正式引入精华库传世神作编纂矩阵、资产启动自动补漏重索引、宪法守卫与大纲节拍导出引擎；此前括号内全部内容沿用）（新增：写作创作页 14 路由——大纲/人物卡/灵感便签/码字统计/TXT 导出；新增 14 个题材 prose 卡，题材 32→46；新增 102 个题材专属桥段，桥段库 68→170（46 个 prose 题材各 3 条）+ 每题材 3 条不变式回归测试；AI 生成流码字统计异常隔离 + record_words AST 静态回归测试 + record_words 异常行为级测试（AI 生成任务仍进 done、手动入库不受影响）；测试文件直接运行 sys.path 约定修复（test_writing_extra/test_b3_cross_thread_close/test_concurrent_writes/test_deepwater_regressions/test_p2_validation 共 5 文件）+ test_direct_run_convention 行为级守卫；桥段数量徽标 total_count 契约修复；gui/web package-lock 根版本 2.0.1→2.0.2 对齐；102 条新桥段 niko 逐条精读审计完成（修复 11 处元叙事：T-BW-003/T-DT-003/SA-001/KJ-002/DT-002/CY-002/MF-002/ND-003/SA-003/WU-001/WY-003 + T-XN-001 中英混杂；题材漂移/同构 0 问题）；14 张 prose 卡逐张精读审计完成（共修改 7 张卡：其中 5 张真实 IP/人名借用——电竞卡 LGD/娃娃/召唤师峡谷/Pentakill→虚构名、武侠卡沈浪→沈砚、无限流卡寂静岭/无限恐怖台词→原创、盗墓卡王胖子/九龙抬棺→原创、网游卡熔火之心→烈焰深渊；2 张读者指代——美食/历史穿越卡与桥段库标准对齐）；迁移 0002 新增 writing_outlines/characters/notes/daily_stats 四表；新桌面图标；gui/server.py 直接执行兼容（`python3 gui/server.py`）+ test_server_direct_run 回归测试；章节重复入库幂等（record_words 支持带符号增量，import_chapter/_run_generate 落盘前快照旧章节、只记增量不重复累加章节数，返回 overwrote 标记）+ 5 个幂等行为测试；_CHAPTER_WRITE_LOCK 章节写锁（快照→落盘→记账原子化，防并发重复入库竞态）+ 并发 20 线程回归测试；write_manifest 真幂等（无变化重跑不写文件）+ 回归测试；2026-10-08 总工批次：ruff 存量清零（纯净 HEAD 上 19 处：B904×12 / I001×5 / F401×1 / B007×1 → 0）；测试在 Windows 退出时释放 SQLite 连接（消除 tearDown 的 WinError 32）并让跨线程 FD 断言只在 POSIX 分支执行；补齐 desktop/build/python-win 后 6 条桌面打包门禁在本机真跑（此前 setUpClass 跳过，故 "Ran" 只报 1256 而口径为 1262）；AGENTS.md §5 环境表按磁盘实测重写（旧项目根指向迁移前的陈旧克隆，Node/npm 镜像/pip 镜像口径已失效）+ §7 收编发版禁令与安装包 NotSigned 实测；test_doc_metrics 口径行守卫加固（锚定列表项、断言唯一、别处提及不再顶掉解析，+2 用例）；质检 target 支持 novel/corpus 之外的任意本机路径（外部目录按章节加载器规则隔离复制，engine_adapter 新增 chapter_scan_rules() 出口 + 三道上限），外部副本改为按 qc-external-* 整棵回收、qc 任务 scratch 清理改 rmtree，+7 用例；e2e 选择器跟上品牌改名并给 dummy 模型注册加收尾（此前它会写脏被跟踪的 config/models.json）；CI 触发分支扩到 feat/** 且锁死 ruff/coverage 版本，据此查出并修好ubuntu 三条腿（FD 采样顺序）与 e2e 全灭（npx 抓到未锁定的 playwright 版本、三处过期选择器）、登录时序断言改为两路径对照；派生路径常量 patch 守卫 + test_system_service 不再量到用户真实库，+9 用例；docs/AGENT_API.md 新增 §4.6 质检端点手册（此前手册完全没有质检），check/book/qc 三端点经真实 HTTP 验证；测试临时目录回收：`_isolation` 新增 `remove_tree()`（先按 PRAGMA database_list 只关"开在该目录内"的 SQLite 连接再整棵删，Windows 句柄未释放是过去删不掉的根因），`isolate_paths()` 退出时自动回收它接管的临时根，13 个测试模块补上 teardown，`test_config_isolation` 加 3 条回收守卫；A/B 实测旧代码每轮全量在 %TEMP% 留 72 个目录、修复后 0 个，实测累计残留 3453 个，其中 2869 个已删除（30 分钟内新建的 176 个保留、40 个被其它在跑的会话占着句柄删不掉）；安全审计批次：访问日志脱敏从只认 auth= 扩到 auth / handshake / handshake_token——实机证明桌面版握手令牌原本明文落进 gui.log（改前 1 次、改后 0 次），并修掉旧替换串里的 SOH 控制字节与吞掉 ?/& 分隔符的过度匹配；管理员初始密码改为只进数据目录指引文件、不进长期留存的日志（仅当指引文件写不出来才退回日志），文件名收口为 admin.ADMIN_HINT_FILE_NAME 单一来源，+6 用例）；2026-10-08 总工批次②：Electron 握手门禁补回归测试（查询参数豁免只适用于 `/api/events`，普通 API 必须带 `X-Handshake-Token`）；打分 `chapter_path`、合规 `book_path`、投稿导出 `book_dir` 统一接入 `gui/text_access.py`（目录不设界、内容设界，+19 用例；旧“项目根外 403”安全断言按新判据重写而非删除）；投稿标题重复章号修复（“第1章 初见”曾导出为“第1章 第1章 初见”），知乎纯 `{title}` 模板不剥前缀，`chapter_num` 为 0/负数/bool 一律 400（+11 用例）；docs/AGENT_API.md 补 §4.7 平台投稿手册（此前该组端点在本手册里完全没有条目）并订正 `chapter_num` 与正文路径准入口径；`announce_initial_password` try 块缩进对齐；正文读取收口到 `gui/text_access.py`（在同一个 fd 上做 O_NOFOLLOW / fstat / 体积校验，再 UTF-8→GBK 解码），`services._secure_read_text` 改为声明策略后复用同一实现（原有措辞与状态码逐条覆盖保留）；引擎侧新增 `scripts/chapter_loader.read_text_file`，QC 单章、`novel.py 检查`/`打分`/`合规`/`清洗`/`批量`/`采样`/`指标`/`组装`/`写作` 全部改走它——GBK 稿子此前在质检里报"读取章节失败"，措辞像路径被禁，实际是只认 UTF-8；默认参数不再冻结模块常量（`max_bytes=None` 才让上限可调，同 §4 的导入期快照坑）；+11 用例（两种编码分数必须一致、FIFO/目录当文件、GBK 单章质检与整本导出静默丢章）；`POST /api/import` 撤掉"导入路径必须在项目目录内"的墙（M8 遗留，与质检同一句话），任意文件读取的防线由 `services._secure_read_text` 承担（只收 .txt / 不跟随链接 / 常规文件 / 100MB），`path` 非字符串补 400（原来会 TypeError 变 500）；docs/AGENT_API.md 补 §4.0 拆书导入（此前 `/api/import*` 一个条目都没有，并写明路径式=就地引用、上传式=归一化落 corpus 的差别）；+7 用例；`writing_extra` 的码字统计/导出/入库记账改走统一解码（用户按 `chapter-NNN.txt` 摆进 novel/ 的 GBK 稿子此前会变成不带文件名的 500），+3 用例；`.githooks/pre-commit` 补 `ruff check .`（CI 每个分支都跑 lint，本地只跑测试导致一条 F401 推上去把 ubuntu 三条腿同时弄红；本机没有 ruff 时只警告不拦）；桌面版新增原生路径选择器：`desktop/preload.js` 用 contextBridge 只暴露 `pickPath(kind)`（不把 ipcRenderer 交给页面），`main.js` 的 `ipcMain.handle` 只认 `dir`/`file` 两个枚举值，`electron-builder.yml` 的 `files` 白名单补 `preload.js`（漏一行就等于功能装机版上静默消失，已加 4 条打包守卫）；质检三个路径输入框在桌面版出现「选择文件…/选择目录…」，浏览器版不渲染。本机真机验证过完整链路：起 dev 版 Electron → 点按钮 → 系统对话框（标题「选择章节文件」、过滤器「正文」）→ 选项目外的 GBK 章节 → 路径回填 → 「检查」出分（质量 73.7 / 一致性 36.0）；目录分支也实测（对话框标题「选择章节目录」→ 选一份混合编码的整本目录 → 全书质检出 Ch1/Ch2 两条章内重复，GBK 那章的文字解码正确）；文风分析的对白统计改走引擎单一口径 `engine_adapter.dialogue_char_count`（原正则只认 ASCII 引号与直角引号，中文弯引号 `“…”` 整段漏计：实测对白占 17% 的稿子被读成 4%，`apply_style_prompt` 据此给出"对话密度较低、以叙述为主"的反向建议）；风格卡落盘改原子写（tmp + `os.replace`；崩溃留下的半份 JSON 会被 `list_styles` 当坏文件跳过，用户看到的是"卡片凭空消失"）；`analyze`/`save`/`apply` 补请求体类型校验（`text`/`style_card`/`base_prompt` 传脏值此前一律变 500），磁盘风格卡里的指标被手改成非数值时回落默认值而不是崩；+10 用例。同一模块的切句口径也一起收口到 `engine_adapter.split_sentences`（`metrics.SENT_RE`：省略号/分号/换行都算句边界）——旧正则只切 `。！？!?`，实测同一篇稿子 140 句被读成 100 句、平均句长 5.6 读成 8.4，句长阈值（15/40）因此可能给出反向建议；+2 用例；另做了一轮全路由脏输入扫描（把 `router.ROUTES` 全表用非字符串/越界/系统目录等 body 打一遍真实 HTTP 服务，凡返回 500 即视为缺陷），修掉 9 处缺参数校验：`project`/`name`/`text`/`style_card`/`base_prompt` 传非字符串此前都是 AttributeError/TypeError → 500「内部错误，请稍后重试」，调用方不知道哪个参数错了，现在一律 400 并指名参数；质检 `target` 指向整盘目录（如 `C:\Windows`）此前会走遍系统目录再撞 MAX_PATH，以 FileNotFoundError 变 500，现在加 `_EXTERNAL_MAX_DIRS=2000` 早停并把复制期 OSError 收成 400（半份副本照旧清理）；新增 `tests/test_api_input_validation.py`（11 条脏 body + 2 条「正常输入仍然可用」反向守卫）。第二轮扫描补上章节序号两道闸：`_safe_chapter_no` 拒绝 2.5 / true 这类会被 `_safe_int` 静默截断的值（截断意味着"第 2.5 章"覆盖掉真正的第 2 章——是数据丢失，不只是报错难看），服务层再加 `chapter_no ≤ 100000` 上限（章节号直接拼成 `chapter-%03d.txt` 并参与目录排序与字数记账）；+4 条边界断言；`test_import_upload` 两个真实 HTTP 用例类的临时根改由 `_isolation.remove_tree` 回收（`TemporaryDirectory.cleanup` 会被工作线程里仍开着的 SQLite 句柄挡住，Windows 上留下删不掉的目录——实测残留 3 个，改后 0 个）；帮助文案同步补选择按钮与编码口径；前端 +7 用例，dist 重建；2026-10-10 企业级升级：新增大纲原子批量重排 POST /api/writing/outlines/reorder；新增去 AI 味全维度诊断 POST /api/writing/deslop；writing_extra 导出升级支持 Markdown 与纯标准库 Word (docx) 规范导出；API 端点 95→97；测试 1353→1363；新增 test_deslop_and_export.py 回归测试，含去 AI 味经典网文俗套库扩充与 DOCX XML 1.0 非法控制字符过滤；2026-10-10 实操资产与离线引擎升级：扩充 11 个高热度题材包与 3 大实战资产库，资产 86→100；研发智能起名工坊与 7 大核心毒点避雷排查引擎，新增 /api/tools/* 5 个端点，API 端点 97→102；前端写作台挂载灵感工坊抽屉、质检台挂载毒点避雷面板；新增 test_tools_services.py 全覆盖测试，测试 1363→1384 全绿；2026-10-10 毒点防御与起名全维深化：起名工坊扩充电竞战队/末日避难所/怪谈收容机构生成分类，毒点避雷升级为 10 大核心毒点全覆盖（补齐 nerfed_powers 剥夺削弱/broken_promise 承诺烂尾/brainless_antagonist 反派无脑复读）及 10000 行扫描安全上限，章节编辑器内置一键毒点排查闭环诊断弹窗，新增 5 条后端单测，测试 1384→1389 全绿；2026-10-10 爽点逆袭与世界观力量体系升级：扩充 assets/shuangdian-library.json (12大成熟爽点打脸逆袭模型) 与 assets/world-library.json (10大热门题材世界观设定与力量阶梯)，资产 100→102；实现离线服务与 GET /api/tools/shuangdians、GET /api/tools/worlds 路由，API 端点 102→104；前端灵感工坊集成爽点打脸与世界观设定选项卡及一键复制；新增 test_tools_services.py 单元测试与 InspirationWorkbench 前端测试，测试 1389→1391 全绿；2026-10-10 爆款书名生成、名场面台词库与签约深度诊断升级：起名工坊升级支持 5 大热门题材爆款书名生成；扩充 assets/dialogue-library.json (12组名场面高阶台词与反AI口语对照)，资产 102→103；实现离线服务与 GET /api/tools/dialogues、POST /api/platform/diagnose 路由，API 端点 104→106；前端灵感工坊集成爆款书名与名场面台词库，平台面板集成签约过稿深度诊断评级报告与致命劝退排查；新增 6 条后端测试与前端全覆盖测试，测试 1391→1397 全绿；2026-10-10 人物反差弧光矩阵与情绪五感高潮演出库升级：扩充 assets/character-library.json (12大爆款人设反差模型与成长弧光) 与 assets/emotion-library.json (10大高潮情绪五感微表情与通感演出)，资产 103→105；实现离线服务与 GET /api/tools/characters、GET /api/tools/emotions 路由，API 端点 106→108；前端灵感工坊集成爆款人设矩阵与情绪高潮演出选项卡及一键复制；新增 test_tools_services.py 单元测试与 InspirationWorkbench 前端测试，测试 1397→1399 全绿；2026-10-10 多平台签约深度诊断与创作参数升级：PLATFORMS 扩充 climax_interval/dialogue_sweet_spot/rhythm_type/platform_taboos，签约过稿自检全面覆盖起点无原则圣母与纯对白失衡、晋江油腻霸总与细腻神态微表情、七猫受辱无底牌反制及 AI 指纹库扩充，新增 4 条测试，测试 1399→1403 全绿；2026-10-10 小说精华数据库与作品多平台属性升级：迁移 0003 新增 essence_books/essence_assets/essence_chains/essence_tasks 四表，迁移 0004 新增 writing_projects_meta 表；新增伏笔暗线图谱与作品生态平台题材持久化，API 端点 116→121，测试 1409→1411 全绿；2026-10-11 小说精华库全库宏观聚合与全文检索升级：新增 GET /api/essence/stats 聚合指标端点与 query 全文关键字检索、同义词分类归一化，API 端点 121→122，测试 1411→1413 全绿；2026-10-11 路由层输入安全与整型防御加固：收口 writing_extra 与 essence_service 接口的 ID 与整型字段转换至 _safe_int 防御，非法参数优雅返回 400，测试 1413→1414 全绿；2026-10-11 对标 GitHub 前沿实践升级小说宪法正典守卫与大纲节拍导出引擎：借鉴 NovelKit 与 NovelParser，新增 export-outline、export-beats、constitution/check 三大端点，提供全书大纲与轻提纲导出及角色声线与世界观违宪深度审查，API 端点 122→125，测试 1414→1416 全绿；2026-10-15 传世神作编纂矩阵扩充：新增《吞噬星空》《学霸的黑科技系统》《惊悚乐园》《全职高手》，精选库 8→12 部题材标杆大圆满，五维资产 40→60、伏笔暗线 16→24，测试 1597 全绿；2026-10-15 章节情绪张力起伏波形分析与神作标杆比对引擎：新增 POST /api/writing/tension-analysis，测试 1597→1604，端点 127→128 全绿；2026-10-15 西方传世神作标杆矩阵与 Exoscribe 英文去 AI 味引擎深度扩充：新增《迷雾之子：最后帝国》与《玄元仙道：无魂》两部西方奇幻与修仙天花板，精选神作库 12→14 部，五维资产 60→70、伏笔暗线 24→28；扩充英文去 AI 味规则表（labyrinthine / resonated deeply / palpable tension / shivers / 分词悬垂起手）并修复跨段落合并单调排序，测试 1604→1605 全绿；2026-10-15 国际化出海与海外平台合规引擎：新增 Royal Road 与 Amazon KDP 平台签约合规体检、LitRPG 属性面板与 BBCode 折叠排版、纯 Python 标准库零依赖 EPUB 3.0 电子书与 William Shunn 国际标准投稿格式（SMF）导出，新增 POST /api/platform/litrpg/stat-box 与 POST /api/platform/royalroad/format，端点 128→130，测试 1605→1612 全绿；2026-10-15 海外现象级神作编纂收录：编纂入库《末日地牢卡尔》（LitRPG/末日地牢真人秀/Matt Dinniman）与《学习之母》（西幻时间循环/Domagoj Kurmaic），精选传世神作库 14→16 部（海外标杆 2→4 部），五维资产卡 70→80、伏笔暗线 28→32，测试 1612 全绿；2026-10-15 前端 LitRPG 属性面板与 Royal Road 格式化工坊落地：多平台工作台新增 LitRPG 状态面板提取与 BBCode [spoiler] 折叠排版选项卡，优化 vitest forks 资源配置，前端测试 144→146 全绿；2026-10-16 西方奇幻与海外网文天花板神作编纂收录：编纂入库经典诗性西幻神作《风之名》（The Name of the Wind / Patrick Rothfuss）与海外现象级网文《与怪为伴》（He Who Fights with Monsters / Travis Deverell），精选传世神作矩阵 16→18 部（西方巨作 4→6 部），五维资产卡 80→90、伏笔暗线 32→36，单测与全量 1612 项测试保持全绿；2026-10-16 世界科幻史殿堂与独狼升级流巅峰神作编纂收录：编纂入库太空歌剧生态史诗《沙丘》（Dune / Frank Herbert）与 Royal Road 长期霸榜 #1 独狼升级神作《原始猎人》（The Primal Hunter / Zogarth），精选传世神作编纂矩阵 18→20 部（西方先锋巨作 6→8 部），五维核心资产卡 90→100、伏笔暗线 36→40 达成全题材大圆满；前端精华工坊全面对齐出海平台与西方奇幻题材，单测与全量 1612 项测试保持全绿；2026-10-16 Webnovel 阅文出海平台签约合规与多平台工坊双语国际化：平台工坊新增 Webnovel（出海英文仙侠玄幻/都市）合规体检与签约深度诊断规则（含行话拼音黑话过度堆砌与金手指出现节奏审查）；多平台工坊（PlatformPanel）全量接入 I18nProvider 双语国际化词典，单测 1612→1613 全绿，前端测试 146→147 全绿；2026-10-16 中英双语核心毒点扫描引擎扩充与避雷面板双语国际化：POISON_PATTERNS 扩充 10 大核心毒点原生英文规则（涵盖海外网文与 LitRPG 憋屈受辱、圣母资敌、降智舔狗、战力断崖、长篇说教、女配送命、绿帽背叛、外挂剥夺、誓言烂尾与反派找茬）；毒点避雷面板（PoisonCheckPanel）全量接入 I18nProvider 双语国际化词典，单测 1613→1615 全绿，前端测试 147→148 全绿；2026-10-16 去 AI 味深度诊断与双栏对比审校双语国际化：DeslopPanel 与 DiffReviewView 全量接入 I18nProvider 双语国际化词典，新增 DiffReviewView.test.tsx 与 en-US 语言回归测试，前端测试 148→153 全绿（27 套件全绿）；2026-10-16 创作扩展企划中心与沉浸创作室工作台双语国际化：WritingExtras（大纲/人物卡/便签/创作者仪表盘/多格式规范导出）与 WritingWorkbench 顶栏模式及流水线标签页全量接入 I18nProvider 双语词典，新增 WritingExtras en-US 语言回归测试，前端测试 153→154 全绿（27 套件全绿）；2026-10-16 灵感与毒点避雷工坊（InspirationWorkbench）全量双语国际化接入：起名工坊、开篇钩子库、金手指机制库、爽点打脸设计、世界观体系、名场面台词库、爆款人设矩阵、情绪高潮演出 8 大模块全量接入 I18nProvider 双语词典，新增 InspirationWorkbench en-US 语言回归测试，前端测试 154→155 全绿（27 套件全绿）；2026-10-17 小说精华数据库与宪法正典审查工坊（EssenceWorkbench）全量双语国际化接入：离线深度精读解构、五维精华资产库、伏笔暗线图谱、已精读书籍档案与小说宪法正典审查 5 大核心模块全量接入 I18nProvider 双语词典，新增 EssenceWorkbench en-US 语言回归测试，前端测试 155→156 全绿（27 套件全绿）；2026-10-17 作品质检与QC审查工坊（QualityWorkbench）全量双语国际化接入：单章检查、全书质检（含中英文动态截断提示与条数同步）、QC综合（四层十二维指标与落盘报告）及毒点避雷 4 大核心模块全量接入 I18nProvider 双语词典，新增 QualityWorkbench en-US 语言回归测试，前端测试 156→157 全绿（27 套件全绿）；2026-10-17 资产库与全品类资产矩阵浏览工坊（AssetLibrary）全量双语国际化接入：11大资产类型标签、分类筛选树（All/全部）、详情可读摘要与高级原始数据折叠全量接入 I18nProvider 双语词典，新增 AssetLibrary.test.tsx 单元测试与 en-US 语言回归测试，前端测试 157→160 全绿（28 套件全绿）；2026-10-17 首页仪表盘与系统全景矩阵（HomeDashboard）全量双语国际化接入：四大KPI指标卡、品牌标题、外部模型状态提示、全品类资产饼图切片与快捷创作入口全量接入 I18nProvider 双语词典，新增 HomeDashboard en-US 语言回归测试，前端测试 160→161 全绿（28 套件全绿）；2026-10-17 拆书分析工坊（AnalysisWorkbench Suite）全量双语国际化接入：导入面板、执行控制栏、进度追踪、结果资产卡与质量一致性图表全量接入 I18nProvider 双语词典，新增 AnalysisView/AnalysisControlBar/AnalysisResultView en-US 语言回归测试，前端测试 161→169 全绿（30 套件全绿）；2026-10-17 帮助中心与功能指南（HelpWorkbench）全量双语国际化接入：新手上路生态全景与数据流图谱、四大典型工作流、16项核心术语表与分类检索、9大模块详细功能指南及常见问题解答全量接入 I18nProvider 双语词典，新增 HelpWorkbench.test.tsx 单元测试与 en-US 语言回归测试，前端测试 169→173 全绿（31 套件全绿）；2026-10-17 高级功能工坊（AdvancedWorkbench Suite）全量双语国际化接入：题材蒸馏（状态/执行/产物/JSON查看器）、批量拆书状态（Pass徽标/已有资产标识）、资产编辑（分类下拉/活体JSON校验/未保存状态/只读寻址提示）全量接入 I18nProvider 双语词典，新增 AdvancedWorkbench.test.tsx 单元测试与 en-US 语言回归测试，前端测试 173→175 全绿（32 套件全绿）；2026-10-17 系统与合规工作台（SystemWorkbench Suite & ModelManager）全量双语国际化接入：系统状态（磁盘占用/数据统计/模型状态/路径）、版权合规（全量扫描/结果摘要/判定徽标）、模型管理（模型卡片/协议与角色/API Key加密存储/增删改查/测试/快速预设）、系统设置（服务端口/批次大小/环境变量覆盖/只读提示）全量接入 I18nProvider 双语词典，新增 SystemWorkbench.test.tsx 单元测试与 en-US 语言回归测试，前端测试 175→177 全绿（33 套件全绿）；2026-10-17 设置工作台（SettingsWorkbench）全量双语国际化接入：打分阈值（一致性目标分/质量及格线/质量警告线）、写作设置（默认字数/最大改写轮数）、即时数值边界与交叉校验规则、保存与重置操作、服务只读配置全量接入 I18nProvider 双语词典，强化 SettingsWorkbench.test.tsx 单元与组件双语测试，前端测试 177→180 全绿（33 套件全绿）；2026-10-17 管理工作台与安全运维面板（AdminWorkbench Suite）全量双语国际化接入：登录门禁（本机访问说明/凭据表单/密码提示）、强制改密状态提示与功能锁定、顶栏Tabs与管理员注销、系统仪表盘（KPI指标卡/磁盘细分/最近书籍/最近操作/运行时长本地化）、书库管理（书库列表/分析状态保护/二次确认彻底删除弹窗）、资产管理（全类别筛选/回收站删除提示）、操作日志（动作与用户过滤/防抖筛选/清除）、会话管理（在线会话列表/当前会话与其它会话分别吊销确认）、安全设置（双重密码比对校验/长度校验/密码更新成功通知/安全说明规范）全量接入 I18nProvider 双语词典，新增 AdminWorkbench.test.tsx 单元测试与 en-US 语言回归测试，前端测试 180→185 全绿（34 套件全绿）；2026-10-17 全量交互浮层与向导（CommandPalette / OnboardingWizard / InlineGuide）全量双语国际化接入：全局命令面板（CommandPalette）接入 I18n 词典（工作台跳转/模式切换/空态/快捷键操作/触发按钮）、首启向导（OnboardingWizard）三步进向导接入 I18n 词典（欢迎/导入/质检三步双语说明与跳转导航）、就地说明（InlineGuide）接入 I18n 词典（折叠与展开 aria-label 及示例标识），新增 CommandPalette.test.tsx、OnboardingWizard.test.tsx 与 InlineGuide.test.tsx 单元与集成测试，前端测试 185→194 全绿（34→37 套件全绿，达成 Exoscribe 全组件 100% 完整双语国际化矩阵）；2026-10-18 写作辅助抽屉（TropePanel/StylePanel）、阅读器（ReaderPanel）与加载错误边界（AsyncBoundary/ErrorBoundary）全量双语国际化接入：桥段灵感面板全量中英双语与分类隔离筛选（__all__）、文风面板（分析提取/保存/删除/空态）、长文本阅读器（双向翻章/章节标题参数插值）、数据四态加载边界与全局错误边界函数钩子降级全量接入 I18nProvider 双语词典；I18nContext 支持动态参数插值与 initialLocale 响应同步；新增 StylePanel.test.tsx 与 ReaderPanel.test.tsx 单元测试，补充 TropePanel/AsyncBoundary/I18nContext 双语回归测试，前端测试 194→204 全绿（37→39 套件全绿，总测试用例 204 项全量通过），生产 bundle 构建干净（dist/ 27s 通过）；2026-10-18 质检报告可视化（QcVisuals）与专业叙事图表矩阵（EmotionWave/RhythmRadar/CreationRate/通用图表）全量双语国际化接入：12维总览条形图、章节×维度得分率热力图、章节问题按严重度分布图、情绪起伏波形图与神作标杆基准比对、爽点与网文六维节奏雷达、每日字数与平滑速率折线图及柱状/饼状/雷达/仪表盘默认 aria-label 全量接入 I18nProvider 双语词典；新增 QcVisuals.test.tsx 与 SpecializedCharts.test.tsx 单元测试，前端测试 204→215 全绿（39→41 套件全绿，总测试用例 215 项全量通过），生产 bundle 构建干净（dist/ 24.5s 通过）；2026-10-18 章节编辑器三维排查诊断弹窗（Poison/Deslop/Constitution）与应用顶层交互全量双语国际化接入：ChapterEditor 正文为空拦截提示、毒点排查弹窗（标题/合规提示/风险条目数/行号/命中词/改法建议）、去AI味体检弹窗（标题/AI指数徽标/合规提示/套路项/扣分权重/优化建议）、设定与宪法审查弹窗（标题/得分徽标/合规与违规状态/合规提示/违宪项/禁用词/角色声线脱缰警告）及 App 顶层（初始化失败提示/抽屉导航切换/帮助中心悬浮按钮 Tooltip 与 aria-label）全量接入 I18nProvider 双语词典；新增 App.test.tsx 单元测试并完善 ChapterEditor.test.tsx 双语诊断弹窗测试，前端测试 215→221 全绿（41→42 套件全绿，总测试用例 221 项全量通过），生产 bundle 构建干净（dist/ 26.1s 通过）；2026-10-18 写作工作台创作室 8 大交互弹窗与张力测算多格式导出全量双语国际化接入：WritingWorkbench（新建项目/企划定位与多平台描述/新建小说作品/全书导出排版与统计插值/章节大纲规划/核心人设卡与角色定位/灵感便签速记/草蛇灰线暗线追踪与伏笔类型）与 WritingExtras（章节情绪张力测算弹窗/Word·EPUB·Shunn·MD·TXT 状态通知与导出按钮）全量接入 I18nProvider 双语词典；完善 WritingWorkbench.test.tsx 与 WritingExtras.test.tsx 双语对话框隔离测试，前端测试 221→223 全绿（42 套件全绿，总测试用例 223 项全量通过），生产 bundle 构建干净（dist/ 27.5s 通过）；2026-10-18 多平台适配与海外 LitRPG·Royal Road 排版工坊全量双语国际化接入：PlatformPanel（目标平台选择/爽点周期与建议字数/合规体检结果与字数统计/签约过稿深度诊断评级报告与致命劝退排查/平台连载短篇要求清单/LitRPG 状态面板解析识别与类型位置插值/Royal Road 连载排版参数与顶部底部作者说/BBCode [spoiler] 折叠排版稿与一键复制通知）全量接入 I18nProvider 双语词典；扩展 PlatformPanel.test.tsx 达成 en-US 语言环境下的深度合规体检、签约过稿诊断与 LitRPG/Royal Road 排版全链路断言覆盖，前端测试 223 项全量通过（42 套件全绿），生产 bundle 构建干净（dist/ 22.8s 通过）；2026-10-18 拆书分析流水线与报告套件（ChapterList/ImportPanel/ProgressPanel/ResultPanel/ContextHelpButton/MarkdownReport）全面硬化与双语测试全覆盖：修复 I18nContext 空串翻译键降级穿透缺陷，修复 ChapterList 列表文字与段落嵌套警告，补全 6 组拆书流水线核心子面板单元测试与中英双语断言覆盖，前端测试套件 42→48 套件全绿（总测试用例 223→249 项全量通过），生产 bundle 构建干净（dist/ 31.0s 通过）；2026-10-18 基础主题、动效骨架屏体系硬化与模型管理组件全量双语测试覆盖：实现 ThemeModeContext 主题模式与系统偏好切换及 localStorage 持久化单测、ModelManager 模型管理面板（预设/增删改查/密钥加密/连通性测试/英文双语）单测、SkeletonBlocks 水墨设计系统骨架屏套件（仪表盘/列表/图表/表单/水墨空态）单测、WorkbenchTransition 工作台切流动效容器（RAF挂载与卸载回收）单测与 theme.ts 墨体系色板及 ECharts 主题工厂单测，前端测试套件 48→53 套件全绿（总测试用例 249→278 项全量通过），生产 bundle 构建干净（dist/ 22.8s 通过）；2026-10-18 导航架构、语言切换与图表基础底座硬化：修复 I18nContext 在声明 initialLocale 时忽略用户手动切换语言的重置缺陷（引入 ref 追踪 prop 真实变更），新增 LanguageToggle 国际化中英文双向切换单测、WorkbenchNav 左侧导航栏 3 大分组 10 大工作台入口切换与双语渲染单测、BaseChart ECharts 统一底座（实例生命周期/setOption/图表尺寸 ResizeObserver/加载态/销毁回收）单测，前端测试套件 53→56 套件全绿（总测试用例 278→288 项全量通过），生产 bundle 构建干净（dist/ 25.8s 通过）；2026-10-18 通用叙事可视化图表套件全维单元测试覆盖：为 BarChart（垂直/横向布局/堆叠模式/类目防重叠倾斜/系列颜色与覆盖）、PieChart（环形内外径/全饼半径/百分比与切片文本模板/圆角与图例）、RadarChart（指标极值/交替水墨晕染底色/半透明填充区域/多系列对比）与 GaugeChart（单值仪表盘/起止角度/单位后缀与标题偏移/阈值配置）构建完整独立的单元测试体系，前端测试套件 56→60 套件全绿（总测试用例 288→307 项全量通过），生产 bundle 构建干净（dist/ 24.0s 通过）；2026-10-18 应用顶层架构与全局状态上下文全链路集成测试覆盖：vite.config.ts 迁移适配 Vitest 5 top-level maxWorkers: 2，彻底根除高并发 worker 进程意外退出（exit code 134）；扩展 App.test.tsx 覆盖品牌多语言、ModeToggle 三态循环切换、Alt+1..9 全局工作台快捷键与表单输入防护、帮助中心悬浮按钮（FAB）路由与自动隐藏、移动端抽屉开关与首启向导（OnboardingWizard）弹窗；新建 AppContext.test.tsx 覆盖 useApp/useAppOptional 环境约束、挂载期三项初始数据加载与 initError 容错恢复、refreshThresholds 动态设置刷新、书目导入三路径（importBook/uploadBook/importSampleBook）与批次状态初始化、selectChapter 章节拉取、拆书分析全套控制指令（start/full/pause/resume/retry）、openHelp 自增 nonce 定向跳转、loadBookResults 拆书报告加载及 SSE 进度流驱动与自动刷新，前端测试套件 60→61 套件全绿（总测试用例 307→324 项全量通过），生产 bundle 构建干净（dist/ 48.7s 通过）；2026-10-18 设计系统视觉 Token、图表配色方案与 4700 行双语国际化词典全维一致性校验：新建 ink.test.ts 覆盖 v4 极简白语义色板、v3 别名映射、夜读暗色对比度、衬线与非衬线及等宽字体栈、card/glassCard 玻璃拟态/ambientGradient 氛围微渐变/cardHover 悬浮微动及 fadeUp/stagger 动效截断逻辑；新建 inkPalette.test.ts 覆盖 inkPaletteLight 与 inkPaletteDark 八色序列、getInkPalette 切换器、inkTextStyle 与 inkTooltip 墨纸浮层样式；新建 translations.test.ts 针对全部 4700 余行双语词条执行全量双向对齐校验（覆盖 zh-CN 与 en-US 完整性、分析后缀合法空串特判、花括号单侧闭合语法、动态参数插值占位符 {param} 双语完全镜像对齐及核心品牌基石标识不变式断言），前端测试套件 61→64 套件全绿（总测试用例 324→343 项全量通过），生产 bundle 构建干净（dist/ 21.7s 通过）；2026-10-18 专用叙事图表矩阵（CreationRateChart/EmotionWaveChart/RhythmRadarChart）独立深度单测全覆盖：新建 CreationRateChart.test.tsx 覆盖 MM-DD 日期截取、3 日移动平滑速率算法、每日字数与速率双折线、空数据退化及 en-US 国际化；新建 EmotionWaveChart.test.tsx 覆盖 11 节拍默认曲线、高潮阈值警戒线、神作标杆双曲线基准比对、自定义节拍标签与 en-US 双语断言；新建 RhythmRadarChart.test.tsx 覆盖预设/自定义网文六维爽感雷达（爽点节奏/打脸期待/信息密度/金手指展开/章末钩子/冲突升级）、背景网格切分与 en-US 双语断言，前端测试套件 64→67 套件全绿（总测试用例 343→354 项全量通过），生产 bundle 构建干净（dist/ 25.7s 通过）；2026-10-18 novel.py 统一命令行入口与语料四层解析策略深度单元测试覆盖：新建 test_cli_novel_core.py 覆盖 resolve_book_src 物理直接返回/直连txt/chosen专属/模糊单命中/模糊多命中歧义报错/未命中可用书目清单提示/空语料库提示/无语料目录安全退出、run_script 缺失脚本判定与 GBK 容错环境变量注入、cmd_reset_admin_password 密码重置与异常降级、cmd_status synthetic_* 虚拟资产过滤/非数字型置信度降级回退/缺失 models.json 智能兜底及创作与报告展示、main 顶层 10 项核心子命令（无参帮助/状态/重置密码/模型/校验/合规/笔法报告/同步检查/回填元数据）参数解析分发，后端测试套件 91→92 套件全绿（总测试用例 1615→1641 项全量通过）；2026-10-18 纯标准库轻量 YAML 解析器与小说分层采样器全维独立测试覆盖：新建 test_yaml_lite.py 覆盖 _strip_comment、_unquote、_parse_scalar（bool/int/float/null/str 类型推导）、_split_inline_list（引号感知切分）、_parse_value（内联数组与字典）、_split_key_value（冒号引号防御）、parse_yaml（标量映射/块级列表/列表内多行字典嵌套/缩进多层展开/注释与空行过滤）、load_frontmatter（--- 与 +++ 双分隔符识别/未闭合安全回退/空内容容错）；新建 test_sampler.py 覆盖 split_chapters（第N章/回/节/卷、Chapter N、CHAPTER N、首章前无标题开头、空章过滤）、detect_volumes（多卷识别与单卷退化）、select（≤10章短篇全取、100章长篇开篇段与25%/50%/75%三处各连续5章及卷末全书末章联合采样）、last_n_chars（尾部截取）、split_sentences 与 _sentence_at（多类型标点断句与越界回退）、extract_dialogue（中文四类引号「」『』“”‘’对话抽取与前后文定位）、build_slices（四层切片生成）、main CLI 产物写入（落盘生成 manifest.json、slices.json 与 pass1-4 切片文件），后端测试套件 92→94 套件全绿（总测试用例 1641→1668 项全量通过）；2026-10-18 版权合规扫描引擎与密钥加密存储矩阵全维独立测试覆盖：新建 test_compliance.py 覆盖 load_json（合法读取与畸形退出）、build_ngram_index（短文本处理/换行与制表符及空白清理/12-gram 滑窗索引构造）、walk_strings 与 walk_all_values（字典与列表深层嵌套路径寻址及叶子节点布尔/数值/字符串全量提取）、find_quoted_fragments（中英文 6 类引号对「」『』“”‘’""''片段提取与空串处理）、scan_asset（abstraction_level verbal 红线拦截/contains_verbatim true 红线拦截/12 字连续命中原文硬错误拦截/.title 章节标题元数据豁免/>20 字长引号人工复核警告/干净资产零错误放行）、main CLI 退出码（PASS 0 / REJECT 1 / WARN 2）；新建 test_secret_store.py 覆盖 Windows DPAPI _dpapi_protect 与 _dpapi_unprotect 底层加解密往返及损坏密文 OSError 容错、load_secrets（空目录安全回退/密文 .secrets.bin 准确还原/损坏 bin 容错/历史明文 .secrets.json 自动无感迁移加密并删除明文/损坏明文容错/非 Windows 回退读取）、save_secrets（Windows DPAPI 加密写入 .secrets.bin 与旧明文清理/Unicode 中文 UTF-8 安全编码/非 Windows 0o600 明文写入）、storage_mode（dpapi-encrypted/plaintext 待迁移/dpapi 未初始化/非 Windows 回退诊断枚举）、main CLI 诊断输出，后端测试套件 94→96 套件全绿（总测试用例 1668→1694 项全量通过）；2026-10-18 原文引用自动清洗器与笔法深度拆解报告全维独立测试覆盖：新建 test_clean_verbatim.py 覆盖 clean_string（正常文本零改动/例如与比如及如后紧跟 >8 字疑似原文引号清理/12 字连续命中原文 12-gram 匹配清理/≤12 字非原文短引用保留/清理后孤立残存引号修复/标点冗余消除）、main CLI 批处理（无 --apply 纯报告且不修改磁盘/带 --apply 递归遍历字典与列表原地写回/合规复扫输出）；新建 test_report_craft.py 覆盖 _technique_block（技法名称与序号回退/手法/效果/骨架/反例及 deep_analysis 7 维深度分析段落格式化）、_dimension_section（空数据容错/list 技法数组与 dict 复合对象双形态兼容/伏笔回收率百分比化及主要风格张力起伏模式解析）、render_craft_report（头部元数据/最强技法与独有技法及复用模式总览/8 维技法深度拆解/尾部免责声明）、main CLI（缺失文件退出码 1/默认与自定义 --out 导出/低于 MIN_REPORT_CHARS 字数警戒提示），后端测试套件 96→98 套件全绿（总测试用例 1694→1707 项全量通过）；2026-10-18 长文本连续性状态追踪引擎（state_tracker.py）全维独立测试覆盖：新建 test_state_tracker.py 覆盖底层辅助与快照容量校验（_utf8_bytes 中英字符字节测算/_snapshot_bytes 序列化体积/_is_retired_status 四类回收状态识别/_validate_snapshot_limits 4096 字节警告与 8192 字节硬上限拦截）、权威状态骨架与原子持久化（_empty_state 8大骨架键值/load_state 缺失文件空状态回退/save_state 临时文件写入与原子替换）、逐章事务安全防线（schema 版本不匹配/mode 非法枚举/stale 修订号多分支拦截/快照硬上限阻断/活跃角色非列表与超 6 人上限拦截/append 模式活跃角色缺快照拦截）、事务生命周期推进与状态派生（init 事务顶层伏笔与时间线事件直接采纳/append 事务 foreshadow_changes 与 timeline_events 之 upsert/delete 双语义/retired_context_items 长期约束与风险消除/retired_characters 角色快照与活跃名单退役清理/recent_chapters 派生去重同章覆盖与最多 3 章滑动窗口截尾/next_chapter_commitments 状态保护/state_revision 单调递增与 last_chapter 推进/state_path 原子写盘）、续写状态卡生成（build_injection_context 4 大核心区块 markdown 格式化/已回收与作废伏笔自动过滤）、修订号预检（validate_revision 一致与 stale 诊断说明）、命令行接口（CLI show / apply 成功推进与 stale 错误码 2 / validate 匹配 0 与失配 1 / context 状态卡导出），后端测试套件 98→99 套件全绿（总测试用例 1707→1732 项全量通过）；2026-10-18 题材文风散文卡转换引擎（import_genre_prose_cards.py）全维独立测试覆盖：新建 test_import_genre_prose_cards.py 覆盖底层辅助（_now_iso ISO8601 UTC 时间戳/_confidence_map 字符串与数值置信度归一化/_as_str_list 别名与标签规范列表/_extract_forbidden_elements 禁忌标记分句精准提取）、Markdown 小节动态解析（parse_sections 忽略一级标题/动态解析所有二级小节并保留段落排版）、题材 ID 确定性解析（resolve_genre_id 查 32 项映射表/fallback_id 覆盖/genre-前缀兜底）、散文卡组装规范（build_genre_prose_card 元数据/语言规则/结构钩子与节奏/商业爽点/prose 原文全量兜底）、批处理与索引导出（import_cards 目录校验/无 frontmatter 跳过/缺失二级小节报错/成功落盘/write_index 生成全题材索引）、命令行接口（CLI main 批量处理完成返回 0 与文件损坏返回 1），后端测试套件 99→100 套件大圆满（总测试用例 1732→1748 项全量通过）；2026-10-18 100本小说严选建库与高质量精华重萃取引擎全维独立测试覆盖：新建 test_batch_100_books.py 覆盖书名与作者清洗（clean_title_and_author 括号后缀清洗/书名作者连字符切分/纯数字带分隔符前缀剥离与汉字数词保护/10大题材启发式推断）、严选把关规则（is_acceptable_webnovel 外国书黑名单/外国国籍标签/60章门槛/25万字门槛/千字均长门槛/首章规范启动校验）、文本与标识符工具（sanitize_book_id 确定性哈希标识/format_full_novel_text 章节段落规整化）、双库原子入库与去重查重（check_book_exists 物理文件校验/ingest_book_atomic 双库原子双写与五维资产/伏笔链沉淀）、台账同步（sync_full_work_log 从数据库权威生成 WORK_LOG_100_BOOKS.md 表格）、精华库质量刷新重萃取（refresh_essence_quality.main 遍历更新 meta_json/清空重建 assets 与 chains/调用 work log 同步），后端测试套件 100→101 套件全绿（总测试用例 1748→1762 项全量通过）；2026-10-18 单章12维质量检测与连续打分引擎全维独立测试覆盖：新建 test_chapter_check.py 覆盖底层辅助（_ramp 分段线性插值与退化夹紧边界/_score1 浮点防噪/_fmt_score 规范数字）、12维质量检测算法（check_word_count 字数阶梯插值/resolve_dialogue_band 题材包覆盖与回退/check_dialogue_ratio 连续衰减与区间校验/check_hook 中英文章末钩与截断惩罚/check_opening 四要素开场吸引力/check_emotion_density 体感词密度/check_direct_emotion 直陈式扣减/check_paragraph_rhythm 短段节奏占比/check_structure 完整三段式/check_ai_tics 模板句式/check_fatigue_words 了字分位数标定与连接词滥用/check_rang_character 让字密度/check_emotion_tags 旁白情绪标签）、阈值与综合判定（resolve_thresholds 题材包覆盖与安全回退/chapter_check 综合判定与 P0-1 逐维上限超发拦截守卫）、命令行接口（CLI 缺失退出/纯文本报告与 --json 结构化输出分流及退出码），后端测试套件 101→102 套件全绿（总测试用例 1762→1786 项全量通过）；2026-10-18 世界观约束与角色属性别名一致性检测引擎全维独立测试覆盖：新建 test_setting_check.py 覆盖世界观规则禁用词提取与违规拦截（_extract_banned_keywords / _check_world_rules 常见禁止句式与无/没有句式及停用词过滤）、角色数值属性冲突（_check_attributes 别名穿透定位与年龄冲突）、别名一致性与称呼混用排查（_check_alias_consistency 全名与别称跨章检测）、检测覆盖率分析（setting_coverage 缺失 entities/world_rules/attributes/alias 与无章节跳过提示/_format_coverage_warning）、综合设定质检入口与命令行接口（check_setting / main 纯文本与 --json 分流及退出码），后端测试套件 102→103 套件全绿（总测试用例 1786→1803 项全量通过）；2026-10-18 体裁散文卡转换引擎全维独立测试覆盖：新建 test_convert_genre_card.py 覆盖底层辅助与类型映射（_now_iso / _confidence_map 字符串与浮点直通及兜底 / _extract_required_elements 提示要素提取 / _extract_banned_phrases 禁止与不得标记及长度过滤 / _extract_hook_types 钩子抽取与去重 / _extract_payoff_types 爽点映射与去重）、Markdown小节切分（parse_sections 标准13小节提取与未列出小节容错）、规则包数据结构组装（build_genre_pack 完整元数据/结构字段/商业爽点/语言规则与缺省兜底）、文件转换与幂等保护（_load_existing 损坏容错 / convert 输入缺失处理 / 正常写出 / --force 同版本幂等跳过与异版本覆盖）、命令行接口与弃用拦截（CLI main 弃用安全退出码 1 与 stderr 引导说明 / 缺失参数 argparse 拦截），后端测试套件 103→104 套件全绿（总测试用例 1803→1821 项全量通过）；2026-10-18 资产同步检查与元数据回填引擎全维独立测试覆盖：新建 test_asset_sync_and_backfill.py 覆盖资产同步辅助判定（list_books 目录发现与缺失容错 / has_pipeline_outputs 流水线产出判定 / provenance_note 出处声明）、报告铁律二长度合规（check_report_compliance 无报告放行 / 字数不足硬阻断 / 达标放行）、单书全维同步检查（check_one 缺失 raw 报错 / 四类资产缺失排查 / 指纹过期与 mtime 启发式 / 采样索引漂移 / 报告合规联动）、asset_sync_check 命令行接口（CLI main 无书放行 / 同步成功 0 / 发现问题 1 及单书参数支持）、资产元数据回填核心逻辑（backfill_one 目录缺失 / 无源 pass 提示 / 损坏 JSON 容错 / 非对象 meta 过滤 / 已是最新跳过 / dry_run 预览与实际写盘）、backfill_meta 命令行接口（CLI main 无书跳过 / dry_run 预览 / 实际回填与错误退出码 1），后端测试套件 104→105 套件全绿（总测试用例 1821→1842 项全量通过）；2026-10-18 Pass5 题材包聚合与全流程批量拆书引擎全维独立测试覆盖：新建 test_pass5_and_batch.py 覆盖 pass5_aggregate 资产发现与过滤机制（collect_books 合成文件过滤 / 题材匹配与 mismatch 收集 / book_names 筛选 / obs 结构加载）、跨书特征提取与出现率测算（extract_features POV / 爆发节奏核心词 / 情绪模式 / 高频比喻领域 / 禁忌词抽取与频率测算）、特征阈值分类与排序（summarize_thresholds 铁律 ≥80% / 建议项 40-80% / 个人特色 <40% 排序切分）、聚合提示词组装（build_prompt 多书特征 / 候选列表 / 输出约束）、pass5_aggregate 命令行接口与防线（CLI main 题材名正则防御 / 无书退出 / 显式指定书目题材不匹配阻断 / --dry-run 快速分支 / verbatim 标记拦截 / schema 校验失败拦截 / 完整聚合写盘与自定义 --out 导出）、批量拆书全流程引擎（run_book 章节过少跳过 / dry-run 采样与量化验证 / 合规扫描失败拦截 / 四遍组装入库）、拆书报告生成（generate_reports 渲染写盘与 None 容错）、batch 命令行接口（CLI main 目录不存在拦截 / 无 TXT 拦截 / 批量执行与 --report 报告生成），后端测试套件 105→106 套件全绿（总测试用例 1842→1863 项全量通过）；2026-10-18 拆书流水线编排核心（pipeline.py）全维独立测试覆盖：新建 test_pipeline.py 覆盖核心辅助与解析（load_prompt 提取系统与用户模板 / extract_json 剥离代码围栏与前后杂音 / _sample_words 优先采样字数与全书回退 / _pass_field_contract 提取旧产出字段契约）、分层切片组装（build_user_input pass1-5 消息与切片组装及未知 Pass 异常）、四遍扫描执行与重试门禁（run_pass dry-run 快速分支 / 正常 LLM 调用与元数据附加 / Pass2 角色数不足门禁重试 / JSON 损坏调试记录保存与超限重试失败）、资产组装与置信度算法（assemble_voice_card 小样本与大样本置信度分级 / assemble_voice_card_v2 归一化装配 / assemble_obs 观测卡待聚合标注）、合规与蒸馏 Hook（run_compliance 错误警告返回码 / _run_distill_hook <3 本跳过与 ≥3 本重跑蒸馏 / write_ai_takeover_guide 生成接管任务清单）、pipeline 命令行接口与异常门禁（CLI main 缺失文件拦截 / 章节过少拦截 / 无外部模型降级任务生成 / dry-run 快速分支 / Schema 校验失败拦截 / 合规扫描失败拦截与全流程成功入库），后端测试套件 106→107 套件全绿（总测试用例 1863→1889 项全量通过）；2026-10-18 语义检索与桥段检索引擎（retrieve.py）全维独立测试覆盖：新建 test_retrieve.py 覆盖底层分词与文本展开（_tokenize 英文大小写与标点及 CJK 双字切分 / _flatten_value 基础类型与递归展开 / _flatten_asset_body 顶层键递归展开 / _build_snippet rules 优先与长句截断）、N-gram 与向量测算（_ngram_counter / _norm 零向量安全保护 / _cosine_sim 余弦相似度归一化）、索引构建与原子持久化（build_index 维度模式与整书模式 / _save_index 与 _load_index 序列化往返及损坏文件空字典容错）、BM25 与融合打分算法（_idf 倒排词频与防负平滑 / _bm25_score 精确词与 CJK 子串双轨匹配及 k1 与 b 参数防御 / _vector_score 语义相似度 / _fused_score 双路融合加权打分）、意图驱动语义检索（retrieve_for_intent 写作意图映射扩充 / 噪声过滤 / 组合分排序与 asset_id 稳定平局裁决 / top_k 截断 / render_retrieval 提示词注水渲染）、桥段库检索与题材隔离铁律（_load_tropes 缺失回退 / _trope_score 权重测算 / retrieve_tropes 题材作用域隔离：universal 全局开放、指定题材严格隔离过滤、genre 为空仅暴露通用桥段），后端测试套件 107→108 套件全绿（总测试用例 1889→1907 项全量通过）；2026-10-18 全书内容质检引擎（book_quality.py）全维独立测试覆盖：新建 test_book_quality.py 覆盖跨章重复检测（check_duplicate_chapters 中段相似度判定与短章安全跳过 / check_duplicate_paragraphs >30字跨章段落过滤 / check_duplicate_sentences >12字跨章句子与 adjacent 相邻章标记及 severity 阶梯分档）、章内重复与无标点碎片检测（_fragment_repeat_ratio 汉字数与字符集种类门槛及非重叠并集覆盖测算 / check_intra_chapter_repeats 句读与碎片双轨识别及 MIN_SAMPLE_SENTS_FOR_RATIO 样本保护）、情节连贯性（check_plot_continuity 频繁次日时间线混乱与紧张平静情绪矛盾）、文笔风格一致性（check_style_consistency 比喻密度突增与 voice_card 驱动直陈式情绪漂移）、凑字数与乱编检测（check_word_padding 章内同段重复与环境描写超标 / check_fabrication 实体表驱动人名别名孤立排查与多手机号矛盾）、AI味痕迹检测（check_ai_flavor 预告旁白/闪回/伤口比喻等 8 类模板）、覆盖率与截断指示（_voice_card_mode 容错解析 / _book_quality_coverage 9项检测跳过原因与单章/多章状态 / format_truncation_hint 动态截断提示文案）、综合质检入口与命令行接口（book_quality_check 缺失目录优雅处理 / ChapterLoadError 结构化异常映射 / voice-card 缺失与损坏错误通道 / settings/entities.json 自动两级探测 / MAX_REPORTED_ISSUES 截断与 verdict 综合裁决 / main CLI 退出码与纯文本及 --json 双模分流），后端测试套件 108→109 套件全绿（总测试用例 1907→1930 项全量通过）；2026-10-18 资产注入器高级装配引擎（inject.py）全维独立测试覆盖：新建 test_inject_advanced.py 覆盖蒸馏资产归一化（_normalize_distilled_assets 单维/多维/按书分组/非字典容错）、写作意图语义检索桥接（retrieve_for_intent 入参 genre 与 distilled 及内部多维三层优先级解析 / 原始资产索引构建与蒸馏结构兜底 / 索引空对象保护）、口头禅与语气词类型适配（_vt_to_str 纯字符串与中英文字典情境规则格式化）、题材包规则渲染（render_genre_pack 语言铁律与好坏对照 / 必需与禁忌要素 / 疲劳词限额 / 结构模板与节拍 / 商业爽点与付费卡点 / 世界观惯例）、写作技法卡渲染（render_craft_card 最强技法 TOP3 / 10 维技法骨架与反例截断 / 可复用模式）、题材文风卡渲染（render_genre_prose_card 软约束标注 / 低置信度告警 / 语言与结构及商业参考 / prose 小节完整兜底）、完整 System Prompt 装配与防空守卫（build_prompt 题材规则 / 软约束 / 蒸馏段 / 意图检索 / 观测占位符过滤 / 状态追踪 / 九项执行清单）、命令行接口（main 全参数解析 / 跨文件读取 / 输出落盘与格式化日志），后端测试套件 109→110 套件全绿（总测试用例 1930→1948 项全量通过）；2026-10-18 资产组装引擎核心（assemble.py）全维独立测试覆盖与BOM回退修复：修复 load_json 在遇 UTF-8 BOM 时因 json.loads 抛出 JSONDecodeError 未触发 utf-8-sig 回退的缺陷；新建 test_assemble_core.py 覆盖文件读取与 BOM 编码容错（load_json）、置信度与样本字数（_confidence <10章与≥10章分档 / _sample_words 优先 manifest 与回退 metrics）、原文引用树形递归清洗（_clean_verbatim 命中替换与未命中保留）、voice-card 资产装配规范（assemble_voice_card 声线回填与元数据溯源）、观测资产组装与容错补齐（assemble_obs 从标题正则抽取章号 / common_mistakes 双路兜底 / 待聚合状态标注）、craft-card 组装与 4 类格式兼容（assemble_craft_card 结构直取 / 维度直取 / 章节拆解关键词命中 / 技法列表兜底归入张力构建 / 技法名缺失自动截取骨架）、来源文件内容指纹（source_fingerprint 16位 sha256 摘要与缺失文件安全过滤）、CLI 流程与内存校验防线（main 缺失清单早停退出 / 内存校验失败严格阻止写盘保护旧资产 / 校验通过原子落盘与指纹注入），后端测试套件 110→111 套件全绿（总测试用例 1948→1964 项全量通过）；2026-10-18 章节生成与改写流水线（write.py）全维独立测试覆盖：新建 test_write_advanced.py 覆盖一致性打分与质量门禁（run_consistency 分数达标 PASS / 建议改写 / 异常优雅降级）、实体冲突排查（run_conflict_check 实体表缺失与空表 / 别名孤立混用拦截 / 称呼正常通过）、无模型本地任务接管模式（main 未配置模型时自动生成 AI 接管写作任务.md 清单并安全退出 0）、LLM 生成异常处理（main 捕获 LLMError 并调用降级描述输出错误 1）、生成-自检-改写多轮闭环（main 一致性与质量未达标提取扣分项与角色核心词触发改写指令 / 达标双维度早停 break / 最终章节入库与全书 QA）、大纲注入与达标线解析（main 已有大纲 chapters/outline.md 上下文合并 / CLI 与题材包 quality_target 达标线解析），后端测试套件 111→112 套件全绿（总测试用例 1964→1971 项全量通过）；2026-10-18 QC 统一质检引擎（qc.py）四层十二维全维独立测试覆盖：新建 test_qc_core.py 覆盖质检扣分与裁决逻辑（_severity_to_deduct 四级严重度加权折算与 100 封顶 / _score_from_issues 换算 / _wrap_issues 统一归一化 / _judge 裁决规则 / _severity_count 严重度统计）、十二维独立评测（D1剧情连贯 / D2逻辑合理 / D3结构完整 / D4人物弧线 / D5设定一致 / D6手法运用 / D7节奏 / D8爽点 / D9句子重复 / D10章节重复 / D11AI味 / D12禁用词）、声线与手法空卡保护（D4/D6 缺失声线卡或 character_voices 为空时避免假 0 分与 65 分制重归一）、全书 QC 编排管线（run_qc 缺失章节异常拦截 / 书名三优先级解析 / 实体表双路探测 / 四层等权加权 / 元数据与覆盖率聚合）、报告双模序列化（to_json 与 to_markdown 排版）、CLI 接口（main 支持 --json / --no-save / 报告自动落盘 reports/qc/ / 退出码判定），后端测试套件 112→113 套件全绿（总测试用例 1971→1986 项全量通过）；2026-10-18 资产 Schema 校验与全模型规范门禁（validate.py）全维独立测试覆盖：新建 test_validate_core.py 覆盖底层标量与容器检查器（check_enum/check_bool/check_probability/check_strength/check_obj/check_list/check_str/is_num）、声线卡全维校验（validate_voice_card 之 meta/narration/dialogue/emotion/banned/imagery/provenance）、题材包全维校验（validate_genre_pack 之 meta/structure/commercial/language_rules）、桥段库全维校验（validate_trope_library 之 abstraction_level/verbal与verbatim版权红线/skeleton四阶段/genre_scope白名单）、技法卡全维校验（validate_craft_card 之 meta.genre铁律一白名单/技法覆盖率/craft_summary/provenance）、结构与商业观测校验（validate_structure_obs/validate_commercial_obs）、题材文风卡轻量校验（validate_genre_prose_card 之 meta.id命名规范/MIT归因三大件/软规则/原文兜底）、实操工具库校验（validate_tool_library 八大工具库键存在性）、纯数据无污染接口与自动类型推断（validate_asset_data/auto_kind 9大资产类型精准推断）、CLI 命令行入口与退出状态码（main 之 PASS 0 / WARN 2 / REJECT 1 / JSON解析异常 1 / genre-prose-card 题材隔离文件名守卫），后端测试套件 113→114 套件全绿（总测试用例 1986→2010 项全量通过，正式突破 2000 测试大关）；2026-10-18 语料库爬虫切片缺陷普查与全书质量核验引擎（scripts/audit_crawler_defects.py、check_all_books.py 等）全维加固与独立测试覆盖：修复 CLEAN_START_PATTERN 误将非零十位章号匹配为开篇的隐式缺陷，彻底消除 scripts/ 巡检工具群的本地绝对路径硬编码，增加 EXOSCRIBE_CORPUS_DB 与平台动态路径回退及 CLI 参数支持；新建 test_audit_crawler_defects.py 覆盖章节标题提取、标点与超长正文误判标题、短章物理切片、高频重复标题、综合文本诊断、数据库巡检与文件缺失检测、首章规范开篇、爬虫清洗标签、全书质量综合体检报告（资产卡/链数量、重名、未清洗标签）、广告模式定位（check_ad）、行序列切片（check_seq）、单书标题分析（check_dp_titles）、资产关键词检索（check_search）与短章分布（check_shorts）全链路，后端测试套件 114→115 套件全绿（总测试用例 2010→2032 项全量通过）；2026-10-18 技法深度分析质量校验组装器（scripts/deep_analyze.py）与语料库深度瑕疵排查工具群全维独立测试覆盖：新建 test_deep_analyze.py 覆盖 check_technique_depth（7维深度字段完整性与类型污染容错）、ensure_technique_depth（缺失键自动补齐与既有保留）、analyze_craft_card（全维度遍历、统计与缺段映射）以及 main CLI 命令行入口（支持 --in-place 就地写盘）；在 test_audit_crawler_defects.py 中进一步覆盖 debug_flaws（资产/伏笔链过短、切片与广告排查）、inspect_issue_books（章节正则包含/排除模式切片对照）与 scan_all_books_crawler_artifacts（全库爬虫伪标题与切片扫描），后端测试套件 115→116 套件全绿（总测试用例 2032→2044 项全量通过）；2026-10-19 100本全量语料库六维全景深度审计引擎（scripts/deep_audit_100_books.py）加固与独立测试覆盖：彻底解耦本地路径硬编码并接入 get_default_corpus_db，支持 CLI --db / -q / --expected-books 参数分流；防御性适配 conn.row_factory 并增强序/引子/楔子章节提取正则；加固 essence_service._format_chain_dict 字符串章号数值清洗；实现安全无污染连接重定向；新建 test_deep_audit_100_books.py 覆盖六大维度与 CLI 异常分支，后端测试套件 116→117 套件全绿（总测试用例 2044→2068 项全量通过）；2026-10-19 深海级盲区穿透审计引擎（scripts/exhaustive_audit_all_aspects.py）加固与独立测试覆盖：彻底解耦数据库路径并支持 EXOSCRIBE_CORPUS_DB 与 CLI --db / -q / --expected-books / --min-chapters / --min-avg-len，防御性加固 essence_service.adopt_asset_to_project 资产分类与题材字段缺失防护，安全重定向服务层测试沙盒，新建 test_exhaustive_audit_all_aspects.py 覆盖盲区 A-E 五大维度与 CLI 异常分支，后端测试套件 117→118 套件全绿（总测试用例 2068→2087 项全量通过）；2026-10-19 缺陷书籍剔除与严苛六维补齐引擎（scripts/replace_defective_books.py）加固与独立测试覆盖：彻底解耦数据库路径接入 get_default_corpus_db，支持 CLI --db / --target-count / --purge-only / --dry-run / -q，支持 fetch_chunk_func 自定义切片获取与网络异常重试恢复，支持级联物理文件清理与 dry-run 演练模式保护，新建 test_replace_defective_books.py 覆盖准入六维校验、级联清理、切片重组与 CLI 调度，后端测试套件 118→119 套件全绿（总测试用例 2087→2111 项全量通过）；2026-10-19 隔离性能与边界可复现检查引擎（scripts/perf_check.py）加固与独立测试覆盖：消除 Linux /proc 单一依赖，基于标准库 ctypes 实现 Windows 进程物理内存 (RSS) 真实采样与 macOS 回退，加固 RssSampler 启停生命周期，支持 CLI --tests 用例筛选与 -q，新建 test_perf_check.py 覆盖跨平台 RSS、黑洞服务、T1-T5 性能断言与 CLI，后端测试套件 119→120 套件全绿（总测试用例 2111→2125 项全量通过）；2026-10-19 全链路真机实测自动化探测引擎（scripts/live_e2e_verification.py）加固与独立测试覆盖：补全 CONFIG_DIR 沙箱隔离防线，加固 gc.collect 与资源无残留安全回收，支持 CLI --port / -q / --keep-sandbox 参数注入，新建 test_live_e2e_verification.py 覆盖 VerificationClient、异常继承与 6 大模块真实闭环全链路集成测试，后端测试套件 120→121 套件全绿（总测试用例 2125→2132 项全量通过）；2026-10-19 风格一致性自检引擎（scripts/consistency.py）加固与全维独立测试覆盖：规范脚本直接运行 sys.path 依赖与 chapter_loader 防御导入，加固 extract_keywords 类型防御与长短文本及中英 6 类引号片段提取，consistency_check 与 main CLI 新增 --json 结构化输出与 -q/--quiet 静默模式，调整 score_text 结构与 main 入口生命周期规范，新建 test_consistency_core.py 覆盖声线执行度、情绪体感词与直陈扣减、叙述视角与短句爆发、禁忌拦截与意象领域全链路，后端测试套件 121→122 套件全绿（总测试用例 2132→2164 项全量通过）；2026-10-19 量化指标流式计算引擎（scripts/metrics.py）加固与全维独立测试覆盖：规范脚本直接运行 sys.path 依赖与 chapter_loader 防御导入，强化 sentences/paragraphs/cjk_runs/char_ttr/bigram_freq/dialogue_char_count/sensory_counts/sentence_length_profile 全套函数非字符串类型防御，main CLI 增加 -q/--quiet 静默模式与参数化测试入口，新建 test_metrics_core.py 覆盖标点断句、段落切分、字符级 TTR、2-gram 词频、成对四类引号与嵌套对白统计、五感词频、句长分布剖面、综合指标及命令行文件与目录批处理全链路，后端测试套件 122→123 套件全绿（总测试用例 2164→2193 项全量通过））



- 第三方衍生资产必须携带 `provenance.source / license / copyright` 三要素，并在 `THIRD_PARTY_NOTICES.md` 逐张登记（`validate.py` 硬校验 + `tests/test_third_party_notices.py` 守卫）；许可证原文须以逐字副本存于 `LICENSES/<上游>/`
- ⚠️ 历史文档中的「17 资产 / 33 测试 / 3 本书 / 68 资产 / 272 测试 / 353/373/648 测试 / 44 端点」等均为**过时或错误口径**
- 用户数据（财务等）永远留空待用户填写，**AI 不得代填**
- Git Data API 推送教训（2026-09-30）：blob 创建后必须用 GET 验证内容再建 tree（曾推送过根版本仍为 2.0.1 的错误 blob）；tree 必须基于远端最新 commit 的 tree；推送后 fetch + reset --hard 对齐本地（API 创建的 commit SHA 与本地不同但 tree 一致属正常）

### 发布与版本授权（2026-10-11 用户授权：改版与发版由 Agent 自主决定）

> **授权变更记录**：本节原为「发布与版本禁令」（用户下达，要求改版本号 / 打 tag / 建 Release / 发版前必须经用户点头）。
> 2026-10-11 用户明确指示「改一下发版禁令，由你自主决定」，该前置审批环节**已解除**。
> 下文保留全部**技术性护栏**——它们约束的是"怎么安全地做"，与"谁来决定"无关，不得因授权放宽而一并删减。

- **授权主体**：改版本号、打 tag、建 Release、发版，均由 Agent **自主决定并执行**，无需逐次征询用户。判断依据是工程完成度（测试全绿 + 构建成功 + 验证通过），不是"流程是否跑通"。
- **但"自主"不等于"随意"**：打 tag / 建 Release 会触发 `release.yml` 直接产出**对外发布物**，属不可逆的对外动作。自主执行的前提是下列护栏全部满足，且发版后须向用户完整报告产物哈希与验证证据。
- 版本号单一真相源是 `gui/__init__.py::__version__`，`tests/test_version_consistency.py` 强制各处一致；改版本后必须重建前端 dist（`cd gui/web && npm run build`）。**版本号一旦推送即已对外可见，改错要走新的补丁版本，不能就地改回**——所以递增前先把下列 6 处标记点核对一遍：
  1. `gui/__init__.py` → `__version__`（canonical，其余各处向它对齐）
  2. `desktop/package.json` → `"version"`
  3. `gui/web/package.json` → `"version"`
  4. `gui/web/src/layout/WorkbenchNav.tsx` → 导航栏显示的 `vX.Y.Z`
  5. `build/installer.iss` → `#define AppVersion`
  6. `AGENTS.md` §7「当前实测口径」行 → `版本 **X.Y.Z**`
  （另有两处**占位符**守卫不得破坏：`packaging/installer_template.sh` 保留 `__VERSION__`、`packaging/build_installer.sh` 从 `$2` 取版本。）
- 以下两件事此前只写在桌面《novel-lab-项目交接文档》里，仓库内没有副本，故收编于此（文档丢失即等于约束丢失）：
  - Release 资产上传曾遇到 `custom.github` 凭证对 `uploads.github.com` 返回 401（对 `api.github.com` 正常），当时改用浏览器网页端上传成功。**本机实测状态**：`gh auth status` 已通过（账号 monesyilya3-Niko，token scopes 含 `repo`/`workflow`）。自 2026-10-11 授权放宽后，`gh release upload` 路径**已进入可验证范围**：首次发版时优先试它，成功即在本行补记实测结论；若仍 401，退回网页端上传并在本行记录。
  - **v2.2.0 实测结论（2026-10-14，已跑通，不再有 401）**：`gh release upload` 与 `gh api -X POST <uploads.github.com url>` 都能成功上传（93,724,986 字节）。但**两个路径都会丢失文件名里的非 ASCII 字符**——传 `暮冬念春-Setup-2.2.0-win64.exe` 上去后只剩 `-Setup-2.2.0-win64.exe`；`gh release upload <file>#<中文名>` 的 `#` 重命名语法同样无效。可用做法是**主名用 ASCII、中文名放进 `label`**（`gh api ...?name=novel-lab-Setup-2.2.0-win64.exe&label=暮冬念春-...`），页面显示 label，下载时仍落 ASCII 名。下次发版直接照此办理，别再逐个试。上传后务必 `gh release download` 回来比 SHA-256（v2.2.0 实测与本地、与 CI artifact 三方一致：`435C6E99…F39212`）。
  - 桌面安装产物**未做代码签名**（2026-10-08 对 v2.0.3 资产实测 `Get-AuthenticodeSignature` = `NotSigned`），Windows SmartScreen 必然弹"未知发布者"，用户侧需要手动"更多信息 → 仍要运行"。**发版报告里必须写明这一点**，否则用户装新包时会把 SmartScreen 警告误当成包损坏。

### 发布物溯源与真机实测（2026-10-08，Windows 10 19045）

- **溯源方法（有效，下次发版照做）**：`gh run download <run-id> -n windows-installer` 取 CI artifact，与 Release 资产逐字节比 SHA-256。已用此法证明 v2.0.3 的 Release 资产与 run `37496901677`（提交 `d10cd72`）的构建产物**完全相同**（`78370d75…5e0765`，93,401,448 字节）。
- ⚠️ **安装器不是可复现构建**：`desktop/package-lock.json` 入库后依赖版本已锁定，但同一提交在 CI 上构建两次，产物**字节不同**（2026-10-08 实测：均 93,404,140 字节，SHA-256 分别 `e60dba1c…` 与 `08d5fe94…`）——NSIS / electron-builder 会嵌入时间戳一类的构建期差异。
  因此溯源只能比"**产出该发布物的那一次 run**"的 artifact，**不要**用"重新构建一个来对哈希"的方式去判断发布物有没有被改动，那样必然对不上。
- **产物名 ≠ 上传名**：`desktop/electron-builder.yml` 的 `artifactName` 产出的文件是 `暮冬念春-Setup-<ver>-win64.exe`；v2.0.3 上传时被人工改名成了 `novel-lab-Setup-…`。到 artifact 里找包要按 yml 的名字找，别信历史文档里的文件名（CI 的 `path: desktop/release/*-Setup-*-win64.exe` 两种名字都吃得下）。
- **真机安装实测**：提权安装走 `/allusers` → `C:\Program Files\novel-lab-desktop`；exe `ProductVersion 2.0.3.0`；随包含 `gui/ scripts/ assets/ config/ reports/ python-win/`，`assets-manifest.json` 版本与资产数（86）与 §7 口径一致；`http://127.0.0.1:8000/` 返回 200。**用户数据不在安装目录**，在 `%LOCALAPPDATA%\暮冬念春`（`index.db` + `.lock` + 备份 + `corpus` + `assets`），全用户安装下权限正常。
- **真机卸载实测**：卸载注册表项、公共桌面与开始菜单快捷方式均清除，8000 端口不再监听，`%LOCALAPPDATA%\暮冬念春` 按设计保留（已验证：拷贝该目录后用同一套后端代码起服务，能读出 6 本书 / 25 个资产 / 14 张 prose 卡）。残留两处：安装目录剩**空目录**壳（NSIS 不删根目录，轻微，卸载前后都在）；`%LOCALAPPDATA%\novel-lab-desktop-updater\installer.exe` 89.1 MB（electron-updater 下载的整包，NSIS 卸载原本完全不碰）。
  - 后者已由 `desktop/build/installer.nsh` 的 `customUnInstall` 修掉，并做了真机前后对照：同一台机器上，旧包卸载后该目录仍在（89MB）；用带该脚本的构建产物静默装到 `%LOCALAPPDATA%\Programs\` 再静默卸载 → 目录**已清除**，`%LOCALAPPDATA%\暮冬念春` 仍完整保留 17 项，且程序未被启动过。注意：逐字节搜安装包里的路径字符串是**无效验证**（NSIS 脚本块被压缩，新包只比旧包大 14 字节），只有实跑卸载才算证明。
- **桌面版在跑时跑测试**：`migrate._server_is_running()` 读 `config.LOCK_PATH`（`config.py` 的导入期常量，patch `STATE_ROOT` 带不动它）。任何手工隔离路径的测试都必须一并隔离 `LOCK_PATH`，否则用户的桌面版一开，全量门禁误红（2026-10-08 实修，见提交 `dc2b716`）。

#### 安装包改动的复验方法（不需要用户点 UAC）

`perMachine: false` + 不提权时，NSIS 会**静默装进当前用户目录**，Agent 可以自己跑完整装卸循环：

```bash
"<安装包路径>" /S                      # 装到 %LOCALAPPDATA%\Programs\novel-lab-desktop
"%LOCALAPPDATA%\Programs\novel-lab-desktop\Uninstall 暮冬念春.exe" /S   # 卸载
```

卸载后必查三项：`%LOCALAPPDATA%\暮冬念春`（用户数据，必须完整保留）、
`%LOCALAPPDATA%\novel-lab-desktop-updater`（缓存，应被清掉）、`tasklist` 里程序是否被误启动（不应有）。
测完把测试留下的空目录删掉即可；这条路径只做**安装包改动的复验**，不产出发布物——用它跑完装卸循环不等于发版，反之发版也不许省掉它的验证步骤。
（上面两条命令已按原样实跑验证：仅 `/S` 即可静默装到用户目录，卸载清掉 updater 缓存，用户数据 17 项无损。）

---

## 8. 相关文档索引

| 文件 | 用途 | 可信度 |
|---|---|---|
| `CORE_PHILOSOPHY.md` | **项目核心理念设定与最高工程宪章**（思想基石 + 四大铁律 + 创作者主权） | 👑 最高权威，所有规则之源 |
| `docs/internal/PROJECT_LAW.md` | **规则单一权威来源**（四铁律 + 六条工程约束，含判定标准与事故依据） | ✅ 权威，优先于本文件 |
| `docs/internal/RULES.md` | 可执行规则全集（操作层细则） | ✅ 大体可用 |
| `AGENTS.md` | 本文件（AI 协作者入口 + 当前实测口径） | ✅ 权威 |
| `docs/internal/PROJECT_SUMMARY.md` | 项目总结 | ✅ 已重写（2026-09-11，基于实测） |
| `docs/internal/HANDOFF.md` | 交接文档 | ✅ 已重写（2026-09-11，基于实测） |
| `docs/DESIGN_gui_phase2_writing_quality.md` | 阶段二设计（W10-W18） | ✅ 权威 |
| `docs/compose/spec/` | Compose Next 特性文档 | ✅ 按需 |
