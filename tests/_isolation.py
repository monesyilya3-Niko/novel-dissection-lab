"""测试隔离公共设施：把 ``gui.config`` 的项目内数据路径常量重定向到临时目录。

R1 回归防线（根因：``STATE_JSON_DIR`` 新增后，多个测试只 patch ``STATE_ROOT``，
导致夹具写进真实 ``gui/state/`` 并跨轮累积）。本模块提供：

- ``DATA_PATH_CONSTANTS``：**必须被测试隔离**的 config 路径常量登记表；
- ``discover_data_path_constants()``：内省 config，自动发现所有项目内 Path 常量；
- ``isolate_paths()``：上下文管理器，成对重定向全部登记常量、还原并删除临时根；
- ``remove_tree()``：Windows 安全的临时目录回收（teardown 复用）；
- ``snapshot_real_state_json_dir()``：真实 ``gui/state/`` 快照，供泄漏守卫比对。

新增 config 路径常量而忘记登记时，``tests/test_config_isolation.py`` 会失败——
这正是防线生效点，禁止为让它变绿而删除断言。

纯标准库，不 import 任何第三方包（铁律三）。
"""
from __future__ import annotations

import contextlib
import hashlib
import os
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from gui import config

ROOT_DIR = config.ROOT_DIR
CONFIG_SOURCE = ROOT_DIR / "gui" / "config.py"

# 代码布局类常量（非「可重定向的数据目录」），不参与隔离。
INFRASTRUCTURE_CONSTANTS: tuple[str, ...] = (
    "GUI_DIR",
    "ROOT_DIR",
    "SCRIPTS_DIR",
    "WEB_DIR",
    "DIST_DIR",
)

# 项目内数据路径常量登记表 —— 新增 config 路径常量必须在此登记。
DATA_PATH_CONSTANTS: tuple[str, ...] = (
    "ASSETS_ROOT",
    "STATE_ROOT",
    "STATE_JSON_DIR",
    "DB_PATH",
    "LOCK_PATH",
    "REPORTS_DIR",
    "CORPUS_DIR",
    "CONFIG_DIR",
    "NOVEL_DIR",
    "PROMPTS_DIR",
)

# 真实状态 JSON 目录：由项目根推导，**不读 config**，避免被 patch 影响。
REAL_STATE_JSON_DIR = ROOT_DIR / "gui" / "state"

# 真实运行时状态目录（SQLite 索引 + settings.json + 锁）。
# 2026-09-23 新增：既有守卫只覆盖 REAL_STATE_JSON_DIR（派生镜像），而当日发现的隔离
# 事故发生在 **gui_state/**（settings.json 被测试覆写），故必须单独守卫。
REAL_GUI_STATE_DIR = ROOT_DIR / "gui_state"


def _canonical_config_namespace() -> dict[str, Any]:
    """在全新命名空间里重新执行 ``gui/config.py`` 源码，取**规范值**。

    不能用运行时 ``getattr(config, name)``：其它测试会 monkeypatch config 常量
    （指向临时目录），使「是否位于项目根内」的判定失真。重新执行源码可得到
    与任何 patch 无关的、定义期的真实值。
    """
    namespace: dict[str, Any] = {
        "__file__": str(CONFIG_SOURCE),
        "__name__": "gui._config_canonical_probe",
    }
    exec(compile(CONFIG_SOURCE.read_text(encoding="utf-8"), str(CONFIG_SOURCE), "exec"), namespace)
    return namespace


def discover_data_path_constants() -> dict[str, Path]:
    """内省 ``gui/config.py``，返回所有「位于项目根内」的模块级 Path 常量。

    基于**定义期规范值**（非运行时被 patch 的值），排除下划线私有名与
    ``INFRASTRUCTURE_CONSTANTS``（代码布局，非数据目录）。
    """
    namespace = _canonical_config_namespace()
    root = namespace["ROOT_DIR"]
    found: dict[str, Path] = {}
    for name, value in namespace.items():
        if name.startswith("_") or name in INFRASTRUCTURE_CONSTANTS:
            continue
        if not isinstance(value, Path):
            continue
        # 数据路径：项目根内，或已登记的用户数据目录（如 STATE_ROOT 已迁至
        # %LOCALAPPDATA%/xuan，不在项目根内但仍需隔离）。
        if value.is_relative_to(root) or name in DATA_PATH_CONSTANTS:
            found[name] = value
    return found


@contextlib.contextmanager
def isolate_paths(tmp_root: Path) -> Iterator[dict[str, Path]]:
    """把全部 ``DATA_PATH_CONSTANTS`` 重定向到 ``tmp_root/<常量名小写>``，退出还原并删除。

    同时设置 ``XUAN_DATA_DIR = str(tmp_root)``，确保 ``scripts/llm_client.py`` 与
    ``scripts/secret_store.py`` 等按环境变量解析用户数据目录的代码也完全隔离，不触碰
    真实平台用户数据目录（如 ``%LOCALAPPDATA%\\暮冬念春``）。

    Yields:
        重定向前的原值映射（便于断言还原正确）。
    """
    tmp_root = Path(tmp_root)
    saved = {name: getattr(config, name) for name in DATA_PATH_CONSTANTS}
    saved_xuan = os.environ.get("XUAN_DATA_DIR")
    os.environ["XUAN_DATA_DIR"] = str(tmp_root)
    for name in DATA_PATH_CONSTANTS:
        setattr(config, name, tmp_root / name.lower())
    _svc_mod = sys.modules.get("gui.services")
    if _svc_mod is not None and hasattr(_svc_mod, "invalidate_library_cache"):
        _svc_mod.invalidate_library_cache()
    try:
        yield saved
    finally:
        if saved_xuan is None:
            os.environ.pop("XUAN_DATA_DIR", None)
        else:
            os.environ["XUAN_DATA_DIR"] = saved_xuan
        for name, value in saved.items():
            setattr(config, name, value)
        _svc_mod = sys.modules.get("gui.services")
        if _svc_mod is not None and hasattr(_svc_mod, "invalidate_library_cache"):
            _svc_mod.invalidate_library_cache()
        # ⚠️ 只在**当前线程**释放自己登记的连接，绝不跨线程 close（2026-11-05 第三次修正）。
        #
        # 历史（三次试错，记录以免再绕）：
        #   v1 `db._reset_conn()`：关全部线程的连接 → Ubuntu 3.11/3.12 Segfault
        #   v2 完全不关            ：本目录连接悬空指向已删库 → 3.13 Segfault
        #   v3 `_close_conns_under`：仍会跨线程 close → Ubuntu 3.12/3.13 Segfault
        #
        # 共同点：任何**跨线程** close 都可能命中某条正被使用的连接（守护线程
        # _watch 会走 db.tx()），在 SQLite C 库里是未定义行为。Python 版本差异
        # 只决定它崩不崩、什么时候崩。
        #
        # 现在的做法是彻底不做跨线程动作：只摘掉当前线程自己的那条。
        # 残留连接留给 gui.db 自己在下次 get_conn() 时处理——它已经会按路径变化
        # 重建（这是生产路径，比测试里的强行清理可靠）。目录回收由 remove_tree
        # 尽力而为；Windows 上删不掉的残留目录由 _isolation 的清理守卫覆盖。
        try:
            from gui import db as _db
            _db._drop_current_thread_conn()
        except Exception:  # noqa: BLE001 - 精简环境/属性缺失时保持原行为
            pass
        remove_tree(tmp_root)


def _close_conns_under(root: Path) -> None:
    """只关闭"数据库文件确实开在 root 之内"的连接。

    Windows 上未释放的 SQLite 句柄会让整棵目录删不掉（[WinError 32]）；而直接全局
    ``db.close()`` 会波及同一进程里并行进行中的其它用例，所以按
    ``PRAGMA database_list`` 报出的真实文件路径逐个判定。
    """
    try:
        from gui import db as _db
    except Exception:  # pragma: no cover - 精简环境下没有 db 模块
        return
    if not (hasattr(_db, "_conns") and hasattr(_db, "_conns_lock")):
        return
    # 全程持 _conns_lock：只关"文件在 root 之内"的那几个，并从登记表里摘掉。
    # 不能用 db._reset_conn()——它关的是全部连接，会误伤同进程里别的在用例。
    with _db._conns_lock:
        for tid, conn in list(_db._conns.items()):
            try:
                row = conn.execute("PRAGMA database_list").fetchone()
                file_path = Path(row[2]).resolve() if row and row[2] else None
            except Exception:
                continue
            if file_path is None or not file_path.is_relative_to(root):
                continue
            try:
                conn.close()
            except Exception:
                pass
            _db._conns.pop(tid, None)


def remove_tree(path: Path | str) -> None:
    """删除临时目录树，绝不抛错（供测试 teardown 复用）。

    先释放开在该目录内的 SQLite 连接，再整棵删；rmtree 失败时逐文件兜底——
    残留目录会让人误以为"测试还在写真实数据"。
    """
    p = Path(path)
    if not p.exists():
        return
    _close_conns_under(p)
    try:
        shutil.rmtree(p)
        return
    except OSError:
        pass
    for dirpath, dirnames, filenames in os.walk(p, topdown=False):
        for name in filenames:
            try:
                Path(dirpath, name).unlink()
            except OSError:
                pass
        for name in dirnames:
            try:
                Path(dirpath, name).rmdir()
            except OSError:
                pass
    try:
        p.rmdir()
    except OSError:
        pass


def snapshot_real_state_json_dir() -> frozenset:
    """返回真实 ``gui/state/`` 下状态 JSON 文件名集合（目录不存在则为空集）。"""
    if not REAL_STATE_JSON_DIR.is_dir():
        return frozenset()
    return frozenset(p.name for p in REAL_STATE_JSON_DIR.glob("gui_state_*.json"))


def snapshot_real_gui_state() -> dict[str, Any]:
    """真实 ``gui_state/`` 的可观测快照：文件集合 + ``settings.json`` 内容 sha256 + mtime。

    只取「稳定可判定的可观测量」：**不含** SQLite 的 ``-wal`` / ``-shm`` 边车——
    SQLite 在只读打开 WAL 库时也可能创建它们，纳入比对会造成假阳性。

    同时记录 **mtime** 而不只是内容哈希：若测试把文件覆写成**相同内容**
    （例如真实文件恰好已是测试写入值），哈希不变会漏报，mtime 仍会变化。
    测试期间没有任何合法理由写这个文件，故 mtime 变化本身就是泄漏信号。

    2026-09-23 新增：用于捕获「模块级路径常量在导入期固化、config patch 失效」
    这一类隔离漏洞（既有登记表机制只能覆盖通过 config 属性访问的代码）。
    """
    if not REAL_GUI_STATE_DIR.is_dir():
        return {"files": frozenset(), "settings_exists": False,
                "settings_sha256": None, "settings_mtime_ns": None}
    files = frozenset(p.name for p in REAL_GUI_STATE_DIR.iterdir() if p.is_file())
    settings = REAL_GUI_STATE_DIR / "settings.json"
    exists = settings.is_file()
    digest = mtime = None
    if exists:
        st = settings.stat()
        digest = hashlib.sha256(settings.read_bytes()).hexdigest()
        mtime = st.st_mtime_ns
    return {"files": files, "settings_exists": exists,
            "settings_sha256": digest, "settings_mtime_ns": mtime}


# 测试会话开始时的真实目录快照（本模块在 discover 阶段被首个测试模块 import，
# 早于任何测试执行），供末位泄漏守卫比对。
def real_user_data_dir() -> Path:
    """计算真实平台用户数据目录（忽略 ``XUAN_DATA_DIR`` 环境变量覆盖）。"""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "暮冬念春"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "暮冬念春"
    return Path.home() / ".local" / "share" / "暮冬念春"


REAL_USER_DATA_DIR = real_user_data_dir()


def snapshot_real_user_data_dir() -> dict[str, Any]:
    """真实平台用户数据目录快照（排除运行中桌面端可能写入的 index.db/-wal/-shm/logs）。

    重点守护：
    - ``config/`` 下所有文件集合及其 ``(sha256, mtime_ns)``（防测试篡改密钥与模型配置）；
    - ``assets/`` 下文件集合（防未隔离服务启动往真实用户目录写资产）；
    - ``state_json/`` 下状态文件集合（防未隔离任务状态落入真实用户目录）。
    """
    root = REAL_USER_DATA_DIR
    if not root.is_dir():
        return {
            "exists": False,
            "config_files": {},
            "assets_files": frozenset(),
            "state_json_files": frozenset(),
        }
    cfg_dir = root / "config"
    config_files: dict[str, tuple[str, int]] = {}
    if cfg_dir.is_dir():
        for p in sorted(cfg_dir.iterdir()):
            if p.is_file():
                try:
                    st = p.stat()
                    digest = hashlib.sha256(p.read_bytes()).hexdigest()
                    config_files[p.name] = (digest, st.st_mtime_ns)
                except OSError:
                    continue
    assets_dir = root / "assets"
    assets_files = (
        frozenset(p.name for p in assets_dir.iterdir() if p.is_file())
        if assets_dir.is_dir()
        else frozenset()
    )
    state_json_dir = root / "state_json"
    state_json_files = (
        frozenset(p.name for p in state_json_dir.glob("gui_state_*.json"))
        if state_json_dir.is_dir()
        else frozenset()
    )
    return {
        "exists": True,
        "config_files": config_files,
        "assets_files": assets_files,
        "state_json_files": state_json_files,
    }


SESSION_START_STATE_JSON_SNAPSHOT = snapshot_real_state_json_dir()
SESSION_START_GUI_STATE_SNAPSHOT = snapshot_real_gui_state()
SESSION_START_USER_DATA_SNAPSHOT = snapshot_real_user_data_dir()
