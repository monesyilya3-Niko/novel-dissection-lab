#!/usr/bin/env python3
"""密钥加密存储（铁律三：纯标准库）。

Windows：DPAPI（crypt32 的 CryptProtectData/CryptUnprotectData，经 ctypes）——
  密文与当前 Windows 用户绑定，免密钥管理；文件为 ``config/.secrets.bin``。
非 Windows：降级为 0600 权限的明文 JSON（原行为），并在 load 时提示。

迁移：发现旧明文 ``.secrets.json`` 时，读取 → 加密落盘 → 删除明文，全程无感。

安全性质：
- DPAPI 密文不可跨用户/跨机器解密，泄漏的 .bin 无法在他人机器还原
- 比较用 hmac.compare_digest 的场景由调用方负责；本模块只管存取
"""

from __future__ import annotations

import ctypes
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
SECRETS_JSON = CONFIG_DIR / ".secrets.json"      # 旧明文（POSIX 回退也用它）
SECRETS_BIN = CONFIG_DIR / ".secrets.bin"        # Windows DPAPI 密文

_CRYPTPROTECT_UI_FORBIDDEN = 0x1


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.c_ulong),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _make_blob(data: bytes) -> _DATA_BLOB:
    buf = ctypes.create_string_buffer(data, len(data))
    return _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))


def _dpapi_protect(data: bytes) -> bytes:
    out = _DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(_make_blob(data)),      # pDataIn
        None,                                # szDataDescr
        None,                                # pOptionalEntropy
        None,                                # pvReserved
        None,                                # pPromptStruct
        _CRYPTPROTECT_UI_FORBIDDEN,          # dwFlags
        ctypes.byref(out),                   # pDataOut
    )
    if not ok:
        raise OSError(f"CryptProtectData 失败（err={ctypes.GetLastError()}）")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def _dpapi_unprotect(blob: bytes) -> bytes:
    out = _DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(_make_blob(blob)),
        None,
        None,
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out),
    )
    if not ok:
        raise OSError(f"CryptUnprotectData 失败（err={ctypes.GetLastError()}）——"
                      "密文可能来自其他用户/机器")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def _is_windows() -> bool:
    return sys.platform == "win32"


def _config_dir(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".secrets.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        try:
            os.chmod(tmp_path, 0o600)
        except OSError:
            pass
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def load_secrets(directory: Path = CONFIG_DIR) -> dict:
    """读密钥字典。优先加密 .bin；发现旧明文 .json 时自动迁移加密。目录不存在时不创建。"""
    directory = Path(directory)
    if not directory.is_dir():
        return {}
    bin_path = directory / SECRETS_BIN.name
    json_path = directory / SECRETS_JSON.name

    if _is_windows():
        if bin_path.exists():
            try:
                data = json.loads(_dpapi_unprotect(bin_path.read_bytes()))
                return data if isinstance(data, dict) else {}
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                print(
                    f"[secret_store] 警告: 无法解密或解析密钥文件 {bin_path}: {exc}",
                    file=sys.stderr,
                )
                return {}
        if json_path.exists():
            # 明文迁移：读 → 加密 → 删明文。迁移失败不阻塞（返回明文内容）。
            try:
                plaintext = json.loads(json_path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                return {}
            if isinstance(plaintext, dict):
                try:
                    enc = _dpapi_protect(
                        json.dumps(plaintext, ensure_ascii=False).encode("utf-8")
                    )
                    _atomic_write_bytes(bin_path, enc)
                    json_path.unlink()
                except OSError:
                    pass  # 加密失败则保留明文，下次再试
                return plaintext
        return {}

    # POSIX 回退：明文 JSON（0600）。
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8-sig"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def save_secrets(secrets: dict, directory: Path = CONFIG_DIR) -> Path:
    """写密钥字典。Windows 走 DPAPI 加密，POSIX 走 0600 明文。返回落盘路径。"""
    directory = _config_dir(Path(directory))
    payload = json.dumps(secrets, ensure_ascii=False, indent=2).encode("utf-8")
    if _is_windows():
        bin_path = directory / SECRETS_BIN.name
        if bin_path.exists():
            unreadable = False
            try:
                old_obj = json.loads(_dpapi_unprotect(bin_path.read_bytes()))
                if not isinstance(old_obj, dict):
                    unreadable = True
            except (OSError, json.JSONDecodeError, ValueError):
                unreadable = True
            if unreadable:
                bak_path = directory / f"{SECRETS_BIN.name}.corrupt.bak"
                try:
                    shutil.copy2(bin_path, bak_path)
                    print(
                        f"[secret_store] 警告: 原 {bin_path} 无法解密，覆写前已备份至 {bak_path}",
                        file=sys.stderr,
                    )
                except OSError:
                    pass
        _atomic_write_bytes(bin_path, _dpapi_protect(payload))
        # 清理历史明文（若存在）
        legacy = directory / SECRETS_JSON.name
        if legacy.exists():
            legacy.unlink()
        try:
            os.chmod(bin_path, 0o600)
        except OSError:
            pass
        return bin_path
    json_path = directory / SECRETS_JSON.name
    # 安全：mkstemp 创建临时文件即指定 0o600 权限，写入完成后原子替换，消除 TOCTOU 与半写风险。
    _atomic_write_bytes(json_path, payload)
    return json_path


def storage_mode(directory: Path = CONFIG_DIR) -> str:
    """返回当前存储模式描述（诊断用）。"""
    directory = Path(directory)
    if _is_windows():
        if (directory / SECRETS_BIN.name).exists():
            return "dpapi-encrypted"
        if (directory / SECRETS_JSON.name).exists():
            return "plaintext（待迁移）"
        return "dpapi（未初始化）"
    return "plaintext-0600（非 Windows 回退）"


if __name__ == "__main__":
    # 诊断入口：python scripts/secret_store.py
    _scripts_dir = Path(__file__).resolve().parent
    if str(_scripts_dir) not in sys.path:
        sys.path.insert(0, str(_scripts_dir))
    import llm_client

    _sec_dir = llm_client.resolve_secrets_dir()
    print(f"密钥目录: {_sec_dir}")
    print(f"存储模式: {storage_mode(_sec_dir)}")
    print(f"密钥条目: {len(load_secrets(_sec_dir))}")
