"""仓库内 assets-manifest.json 必须与 assets/ 实际内容同步（2026-11-03）。

背景：改了资产内容却忘了刷新 manifest，本机实测就踩到过一次——
``realistic-romance-genre-pack.json`` 删掉一个拼写错误键后 hash 与
manifest 记录不符。后果不是立刻报错，而是**发布版升级时**内置同步会把
这份资产当成「用户改过」而永不覆盖，用户永远收不到修复。

manifest 是发布物升级判定的唯一依据，必须与磁盘逐字节一致。
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestManifestFreshness(unittest.TestCase):
    def setUp(self):
        self.manifest_path = ROOT / "assets-manifest.json"
        self.assets = ROOT / "assets"

    def test_manifest_exists(self):
        self.assertTrue(self.manifest_path.is_file(),
                        "assets-manifest.json 缺失，发布包无法判定内置资产版本")

    def test_every_asset_registered(self):
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        files = data.get("files") or {}
        disk = {p.name for p in self.assets.glob("*.json")}
        self.assertEqual(sorted(disk - set(files)), [],
                         "下列资产未登记进 manifest（发布时不会同步给用户）")
        self.assertEqual(sorted(set(files) - disk), [],
                         "manifest 登记了磁盘上不存在的资产")

    def test_hashes_match_disk(self):
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        # 直接复用被测实现，避免测试里再写一份换行归一化逻辑
        # （Windows 工作树是 CRLF、仓库/CI 是 LF，两份实现容易漂移）
        from gui import builtin_sync
        stale = []
        for name, entry in (data.get("files") or {}).items():
            fp = self.assets / name
            if not fp.is_file():
                continue
            if builtin_sync._sha256(fp) != entry.get("sha256"):
                stale.append(name)
        self.assertEqual(
            stale, [],
            "下列资产内容已变但 manifest 未刷新——跑 "
            "`python -m gui.builtin_sync --write-manifest` 后重新提交：\n  "
            + "\n  ".join(stale),
        )

    def test_hash_is_line_ending_agnostic(self):
        """同一份 JSON 用 CRLF 与 LF 落盘，哈希必须相同。

        这是跨平台正确性的核心：manifest 在 Windows 生成、在 Linux CI
        校验，若哈希随换行符变化，两边永远对不上（实测 CI 三条腿全红）。
        """
        from gui import builtin_sync
        body = '{\n  "a": 1\n}\n'
        with tempfile.TemporaryDirectory() as td:
            lf = Path(td) / "lf.json"
            crlf = Path(td) / "crlf.json"
            lf.write_bytes(body.encode("utf-8"))
            crlf.write_bytes(body.replace("\n", "\r\n").encode("utf-8"))
            self.assertEqual(builtin_sync._sha256(lf), builtin_sync._sha256(crlf))


if __name__ == "__main__":
    unittest.main()
