#!/bin/bash
# 隔离 E2E：工作树副本 → 独立端口 → 跑 Playwright → 删副本。
# 真实 gui_state/、corpus/、assets/ 零写入；跑完无残留。
# 空库用例：E2E_EMPTY_LIBRARY=1 bash scripts/e2e_isolated.sh e2e/onboarding.spec.ts
#
# 端口说明：先选一个当前空闲端口；服务若仍顺延（--port 占用自动 +1），
# 则以服务实际打印的启动 URL 为准，绝不假设端口。
set -euo pipefail

# Windows 的 WindowsApps python3 别名可能返回 49；必须试运行，不能只查 PATH。
PYTHON_CMD=()
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 \
    && "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >/dev/null 2>&1; then
    PYTHON_CMD=("$candidate")
    break
  fi
done
if [ "${#PYTHON_CMD[@]}" -eq 0 ] && command -v py >/dev/null 2>&1 \
  && py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >/dev/null 2>&1; then
  PYTHON_CMD=(py -3)
fi
if [ "${#PYTHON_CMD[@]}" -eq 0 ]; then
  echo "隔离 E2E 需要可运行的 Python 3.11+（python3、python 或 py -3）" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$HOME/workspace/.tmp/e2e-$(date +%Y%m%d-%H%M%S)-$$"
PORT="${E2E_PORT:-$("${PYTHON_CMD[@]}" -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1]); s.close()")}"

mkdir -p "$WORK"
# rsync 工作树（含未提交改动），排除大体积/运行时目录。
# E2E_EMPTY_LIBRARY=1：额外排除仓库种子数据（corpus/、assets/、reports/），
# 得到真正空库（OnboardingWizard 首启引导用例需要；smoke/journey 依赖种子
# assets/，不得默认排除）。
RSYNC_EXTRA=()
if [ "${E2E_EMPTY_LIBRARY:-0}" = "1" ]; then
  # 注意：必须用 / 锚定到同步根，否则 'assets/' 会误伤 gui/web/dist/assets/（前端产物）。
  RSYNC_EXTRA=(--exclude='/corpus/' --exclude='/assets/' --exclude='/reports/' --exclude='/gui/state/')
fi
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete \
    --exclude='.git/' \
    --exclude='gui/web/node_modules/' \
    --exclude='gui_state/' \
    --exclude='__pycache__/' \
    --exclude='.coverage' \
    --exclude='/config/.secrets.bin' \
    --exclude='/config/.secrets.json' \
    "${RSYNC_EXTRA[@]}" \
    "$ROOT/" "$WORK/"
else
  ROOT="$ROOT" WORK="$WORK" E2E_EMPTY_LIBRARY="${E2E_EMPTY_LIBRARY:-0}" \
    "${PYTHON_CMD[@]}" - <<'PY'
import os
import shutil
from pathlib import Path

root = Path(os.environ["ROOT"])
work = Path(os.environ["WORK"])
ignored_names = {".git", "node_modules", "gui_state", "__pycache__", ".coverage"}


def ignore(directory: str, names: list[str]) -> set[str]:
    current = Path(directory)
    ignored = {name for name in names if name in ignored_names}
    ignored.update({"test-results", "playwright-report", ".pytest_cache", ".ruff_cache"})
    if current == root / "config":
        ignored.update({".secrets.bin", ".secrets.json"})
    if os.environ["E2E_EMPTY_LIBRARY"] == "1" and current == root:
        ignored.update({"corpus", "assets", "reports", "gui/state"})
    return ignored


shutil.copytree(root, work, dirs_exist_ok=True, ignore=ignore)
PY
fi

# 服务与 Playwright 都只允许使用沙箱数据；仓库 config/ 不得再作为密钥回落源。
# 必须在 rsync --delete 之后创建 data/，否则同步会把预置目录当额外文件删除。
export XUAN_DATA_DIR="$WORK/data"
mkdir -p "$XUAN_DATA_DIR/config"
cat >"$XUAN_DATA_DIR/config/models.json" <<'JSON'
{
  "version": 1,
  "models": {
    "e2e-isolated-dummy": {
      "protocol": "openai",
      "base_url": "http://127.0.0.1:9",
      "model_name": "dummy",
      "api_key_env": "E2E_ISOLATED_DUMMY_API_KEY"
    }
  },
  "roles": {
    "default": "e2e-isolated-dummy",
    "cheap": "e2e-isolated-dummy",
    "strong": "e2e-isolated-dummy"
  },
  "routes": {
    "pass1_structure": "cheap",
    "pass2_character": "cheap",
    "pass3_style": "strong",
    "pass4_commercial": "strong",
    "pass5_craft": "strong",
    "pass5_aggregate": "strong",
    "writing": "strong",
    "consistency_check": "cheap"
  }
}
JSON
printf '{}\n' >"$XUAN_DATA_DIR/config/.secrets.json"
export E2E_ISOLATED_DUMMY_API_KEY="dummy-e2e-key"

SRV_LOG="$WORK/server.log"
cleanup() {
  ROOT="$ROOT" WORK="$WORK" SRV="$SRV" E2E_EMPTY_LIBRARY="${E2E_EMPTY_LIBRARY:-0}" \
    "${PYTHON_CMD[@]}" - <<'PY'
import os
import shutil
import signal
import stat
import time
from pathlib import Path

pids = {int(os.environ["SRV"])}
for candidate in Path(os.environ["WORK"]).rglob(".lock"):
    try:
        pids.add(int(candidate.read_text(encoding="ascii").strip()))
    except (OSError, ValueError):
        continue
import ctypes

for pid in pids:
    if os.name == "nt":
        handle = ctypes.windll.kernel32.OpenProcess(0x0001, False, pid)
        if handle:
            ctypes.windll.kernel32.TerminateProcess(handle, 0)
            ctypes.windll.kernel32.CloseHandle(handle)
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
for _ in range(200):
    live = []
    for pid in pids:
        if os.name == "nt":
            handle = ctypes.windll.kernel32.OpenProcess(0x00100000, False, pid)
            if handle:
                if ctypes.windll.kernel32.WaitForSingleObject(handle, 0) != 0:
                    live.append(pid)
                ctypes.windll.kernel32.CloseHandle(handle)
            continue
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        live.append(pid)
    if not live:
        break
    time.sleep(0.1)

work = Path(os.environ["WORK"])
root = Path(os.environ["ROOT"])
node_modules = root / "gui" / "web" / "node_modules"
for attempt in range(10):
    try:
        shutil.rmtree(work)
        break
    except OSError as exc:
        if attempt == 9 or exc.winerror not in {5, 32, 33, 145}:
            raise
        if node_modules.is_dir() and not (work / "gui" / "web" / "node_modules").exists():
            shutil.copytree(
                node_modules,
                work / "gui" / "web" / "node_modules",
                symlinks=True,
                dirs_exist_ok=True,
            )
        for path in work.rglob("*"):
            if path.is_symlink() or path.is_file():
                path.chmod(stat.S_IWRITE | stat.S_IREAD)
        time.sleep(0.5 * (attempt + 1))
PY
}
trap cleanup EXIT

cd "$WORK"
"${PYTHON_CMD[@]}" -u - "$PORT" <<'PY' >"$SRV_LOG" 2>&1 &
import sys

from gui import server

port = int(sys.argv[1])
server.setup_logging()
app = server.GuiServer(preferred_port=port)
try:
    host, actual_port = app.start()
except RuntimeError as exc:
    print(f"[GUI] 启动失败: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc

print(f"[GUI] novel-lab 书籍分析服务已启动: http://{host}:{actual_port}/", flush=True)
print("[GUI] 按 Ctrl+C 停止。", flush=True)
try:
    app.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    app.shutdown()
PY
SRV=$!

# 等服务打印启动 URL，以其实际端口为准
ACTUAL_PORT=""
for _ in $(seq 1 30); do
  if grep -q "已启动" "$SRV_LOG" 2>/dev/null; then
    ACTUAL_PORT="$(grep -o '127\.0\.0\.1:[0-9]*' "$SRV_LOG" | head -1 | cut -d: -f2)"
    break
  fi
  sleep 1
done
if [ -z "$ACTUAL_PORT" ]; then
  echo "E2E 服务未就绪"
  cat "$SRV_LOG"
  exit 1
fi
curl -sf "http://127.0.0.1:$ACTUAL_PORT/" >/dev/null \
  || { echo "E2E 服务端口 $ACTUAL_PORT 无响应"; cat "$SRV_LOG"; exit 1; }

cd "$ROOT/gui/web"
if [ ! -d node_modules ] && [ -d "$WORK/gui/web/node_modules" ]; then
  ln -s "$WORK/gui/web/node_modules" node_modules
fi
E2E_BASE_URL="http://127.0.0.1:$ACTUAL_PORT" E2E_SERVER_ROOT="$WORK" npx playwright test "$@"
