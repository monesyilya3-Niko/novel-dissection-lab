# Git 钩子（提交前自动测试守卫）

本目录纳入版本控制，保证「提交前必须跑通全量回归测试」这条纪律随仓库一起分发。

## 启用（每个新克隆执行一次）

```sh
git config core.hooksPath .githooks
```

Git 会把钩子查找路径从默认的 `.git/hooks/` 改为仓库内的 `.githooks/`。
之后每次 `git commit` 都会先执行 `.githooks/pre-commit`。

> 说明：`core.hooksPath` 属于本地仓库配置，不会被提交，所以需要每人手动启用一次。

**兜底：钩子未生效时**——git 只执行具备可执行位的钩子文件，权限位缺失时会**静默跳过**（不报错、不提示）。
仓库索引中 `.githooks/pre-commit` 已标记为 `100755`（`git ls-files -s .githooks/pre-commit` 可核对），
但某些克隆/打包方式（如 zip 解压、跨文件系统复制）会丢失该权限位。此时执行：

```sh
chmod +x .githooks/pre-commit
```

> Windows 无需此步（NTFS 上无 POSIX 可执行位，git 不会因此跳过钩子）。

## 行为

1. 运行 `python run_tests.py`（约 2328 tests / ~2min，超时 180s，有进度提示）。
   - **测试失败 → 非零退出，提交被阻止**，并打印「测试未通过，提交已阻止」及绕过方式。
   - **仅文档变更时（fast-path）**：若本次暂存文件均不含 `py/ts/tsx/js/json/yml/yaml/toml/sh/iss` 后缀，则跳过全量测试，仅跑 lint + 资产校验（见下）。
   - 超时 180s（`timeout`/`gtimeout` 可用时）自动终止并提示，避免 125s+ 挂死导致用户误以为卡住。
2. 测试通过后，校验本次**暂存**的 `assets/*.json`（`python scripts/validate.py <资产>`）。
   - 无暂存资产 → 打印「无变更资产，跳过 schema 校验。」并正常放行（不增加耗时）。
   - 全部 PASS（返回码 0）→ 打印「资产 schema 校验通过（N 个）。」并放行。
   - 出现 WARN（返回码 2）→ 打印警告，**不阻止提交**。
   - 出现 REJECT（返回码 1）→ 打印该资产完整校验输出，**阻止提交**并列出不合规清单。
   - 校验脚本异常返回码 → 同样视为失败并阻止提交。

## 绕过

仅在确知要临时跳过时使用：

```sh
git commit --no-verify
# 或显式环境变量（推荐，可被 CI 审计）：
NOVEL_LAB_SKIP_HOOKS=1 git commit -m "..."
```

### 仅文档 fast-path

若本次暂存文件全部为非代码文件（如 `*.md`、`docs/**`、图片等，不含 `py/ts/tsx/js/json/yml/yaml/toml/sh/iss` 后缀），钩子自动跳过全量回归测试，仅执行 lint 和资产校验。无需手动配置。如需对纯文档提交强制跑全量，可暂存一个空代码文件或设置 `NOVEL_LAB_SKIP_HOOKS=0` 覆盖。

### 超时保护

当系统提供 `timeout` 或 `gtimeout` 时，测试运行被限制在 180s 内，超时返回码 124 并打印提示；Windows Git Bash 通常无此命令，此时退化为直接运行（无超时）。进度行会显示 `约 2328 tests / ~2min，超时 180s`，避免用户误判为挂死。

## 解释器选择（健壮降级）

按以下顺序解析，任一步命中即用；**都不会因「指定解释器不存在」而崩溃**：

1. 环境变量 `NOVEL_LAB_PYTHON`（若设置但不可执行，打印警告后继续）。
2. 项目内 venv：`.venv/Scripts/python.exe`、`.venv/bin/python`、`venv/...`（可移植，无机器相关绝对路径）。
3. 回退到 `PATH` 的 `python3` / `python`（打印警告）。
4. 全部找不到 → 明确报错并提示绕过方式（非静默崩溃）。

示例：

```sh
NOVEL_LAB_PYTHON=/c/Python313/python.exe git commit -m "..."
```

## 停用

```sh
git config --unset core.hooksPath
```
