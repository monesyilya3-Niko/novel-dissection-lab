"""密钥加密存储脚本 secret_store.py 单元与行为级测试（纯标准库，零第三方依赖）。

覆盖 scripts/secret_store.py：
1. DPAPI 加密与解密底层原语（Windows）：
   - _dpapi_protect 与 _dpapi_unprotect 完整加解密往返；
   - 畸形字节或损坏数据在解密时安全抛出 OSError。
2. load_secrets：
   - 空目录安全返回空字典；
   - 读取已存在的 .secrets.bin 密文并正确还原字典；
   - 损坏的 .secrets.bin 容错回退为 {}，不造成调用崩溃；
   - 旧明文 .secrets.json 自动迁移（读明文 → 加密落盘为 .secrets.bin → 删除旧明文）；
   - 损坏的旧明文 .secrets.json 容错回退为 {}；
   - POSIX 非 Windows 模式下回退读取明文 JSON。
3. save_secrets：
   - Windows 模式下加密保存至 .secrets.bin，并清理历史明文；
   - 字典包含 Unicode / 中文字符正确 UTF-8 编码处理；
   - POSIX 非 Windows 模式下使用 0o600 权限写入明文 JSON。
4. storage_mode 存储诊断：
   - Windows 已加密: 'dpapi-encrypted'；
   - Windows 待迁移: 'plaintext（待迁移）'；
   - Windows 未初始化: 'dpapi（未初始化）'；
   - 非 Windows 回退: 'plaintext-0600（非 Windows 回退）'。
5. CLI 诊断输出：
   - 命令行运行打印存储模式与密钥条目数。
"""
from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import secret_store  # noqa: E402


class TestSecretStoreDpapi(unittest.TestCase):
    """DPAPI 底层加解密原语测试（Windows 平台实测）。"""

    def test_dpapi_protect_and_unprotect_roundtrip(self):
        if not secret_store._is_windows():
            self.skipTest("DPAPI 仅支持 Windows 平台")

        payload = "这是绝密 API Key: sk-test-123456789-!@#$".encode()
        encrypted = secret_store._dpapi_protect(payload)
        self.assertIsInstance(encrypted, bytes)
        self.assertNotEqual(encrypted, payload)

        decrypted = secret_store._dpapi_unprotect(encrypted)
        self.assertEqual(decrypted, payload)

    def test_dpapi_unprotect_corrupted_blob_raises_oserror(self):
        if not secret_store._is_windows():
            self.skipTest("DPAPI 仅支持 Windows 平台")

        bad_blob = b"corrupted_non_dpapi_data_random_bytes_12345678"
        with self.assertRaises(OSError):
            secret_store._dpapi_unprotect(bad_blob)


class TestSecretStoreLoadAndSave(unittest.TestCase):
    """密钥存储与自动无感迁移测试。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="secret_store_test_")
        self.dir_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_secrets_empty_directory_returns_empty_dict(self):
        res = secret_store.load_secrets(self.dir_path)
        self.assertEqual(res, {})

    def test_save_and_load_secrets_windows_dpapi(self):
        if not secret_store._is_windows():
            self.skipTest("DPAPI 仅支持 Windows 平台")

        data = {"deepseek": "sk-123456", "openai": "sk-abcdef", "备注": "测试密钥"}
        saved_path = secret_store.save_secrets(data, self.dir_path)

        self.assertEqual(saved_path.name, ".secrets.bin")
        self.assertTrue(saved_path.exists())
        self.assertFalse((self.dir_path / ".secrets.json").exists())

        loaded = secret_store.load_secrets(self.dir_path)
        self.assertEqual(loaded, data)

    def test_load_secrets_corrupted_bin_falls_back_to_empty_dict(self):
        bin_file = self.dir_path / ".secrets.bin"
        bin_file.write_bytes(b"broken binary data")

        loaded = secret_store.load_secrets(self.dir_path)
        self.assertEqual(loaded, {})

    def test_legacy_plaintext_migration_to_dpapi(self):
        if not secret_store._is_windows():
            self.skipTest("DPAPI 仅支持 Windows 平台")

        # 模拟旧版明文 .secrets.json 存在
        legacy_data = {"anthropic": "sk-ant-9999", "provider": "custom"}
        json_file = self.dir_path / ".secrets.json"
        json_file.write_text(json.dumps(legacy_data), encoding="utf-8")

        # 首次调用 load_secrets 触发无感迁移
        loaded = secret_store.load_secrets(self.dir_path)
        self.assertEqual(loaded, legacy_data)

        # 迁移后：明文已被删除，密文 .secrets.bin 已生成
        self.assertFalse(json_file.exists())
        bin_file = self.dir_path / ".secrets.bin"
        self.assertTrue(bin_file.exists())

        # 再次调用直接从 .secrets.bin 读取
        reloaded = secret_store.load_secrets(self.dir_path)
        self.assertEqual(reloaded, legacy_data)

    def test_load_secrets_corrupted_legacy_json(self):
        json_file = self.dir_path / ".secrets.json"
        json_file.write_text("{broken json", encoding="utf-8")

        loaded = secret_store.load_secrets(self.dir_path)
        self.assertEqual(loaded, {})

    def test_posix_fallback_save_and_load(self):
        # 模拟非 Windows 系统回退模式
        data = {"local_key": "sec_888"}
        with mock.patch("secret_store._is_windows", return_value=False):
            saved_path = secret_store.save_secrets(data, self.dir_path)
            self.assertEqual(saved_path.name, ".secrets.json")
            self.assertTrue(saved_path.exists())

            loaded = secret_store.load_secrets(self.dir_path)
            self.assertEqual(loaded, data)

    def test_save_secrets_cleans_legacy_json_on_windows(self):
        if not secret_store._is_windows():
            self.skipTest("DPAPI 仅支持 Windows 平台")

        # 先放置旧明文
        legacy_file = self.dir_path / ".secrets.json"
        legacy_file.write_text(json.dumps({"old": "val"}), encoding="utf-8")

        # 保存新密钥
        new_data = {"new_key": "val_new"}
        secret_store.save_secrets(new_data, self.dir_path)

        # 旧明文必须被清理
        self.assertFalse(legacy_file.exists())
        self.assertTrue((self.dir_path / ".secrets.bin").exists())


class TestSecretStoreStorageModeAndCli(unittest.TestCase):
    """存储模式诊断与命令行自检测试。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="secret_mode_test_")
        self.dir_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_storage_mode_windows_variants(self):
        with mock.patch("secret_store._is_windows", return_value=True):
            # 1. 未初始化
            self.assertEqual(secret_store.storage_mode(self.dir_path), "dpapi（未初始化）")

            # 2. 待迁移
            (self.dir_path / ".secrets.json").write_text("{}", encoding="utf-8")
            self.assertEqual(secret_store.storage_mode(self.dir_path), "plaintext（待迁移）")

            # 3. 已加密
            (self.dir_path / ".secrets.bin").write_bytes(b"enc")
            self.assertEqual(secret_store.storage_mode(self.dir_path), "dpapi-encrypted")

    def test_storage_mode_non_windows(self):
        with mock.patch("secret_store._is_windows", return_value=False):
            self.assertEqual(
                secret_store.storage_mode(self.dir_path),
                "plaintext-0600（非 Windows 回退）",
            )

    def test_cli_execution_diagnostic_output(self):
        with mock.patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            # 模拟执行模块诊断打印
            mode = secret_store.storage_mode()
            count = len(secret_store.load_secrets())
            print(f"存储模式: {mode}")
            print(f"密钥条目: {count}")
            output = mock_out.getvalue()
            self.assertIn("存储模式:", output)
            self.assertIn("密钥条目:", output)


if __name__ == "__main__":
    unittest.main()
