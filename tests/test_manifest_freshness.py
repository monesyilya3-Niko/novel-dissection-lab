"""仓库内 assets-manifest.json 必须与 assets/ 实际内容同步（2026-11-03）。

背景：改了资产内容却忘了刷新 manifest，本机实测就踩到过一次——
``realistic-romance-genre-pack.json`` 删掉一个拼写错误键后 hash 与
manifest 记录不符。后果不是立刻报错，而是**发布版升级时**内置同步会把
这份资产当成「用户改过」而永不覆盖，用户永远收不到修复。

manifest 是发布物升级判定的唯一依据，必须与磁盘逐字节一致。
"""
from __future__ import annotations

import hashlib
import json
import sys
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
        stale = []
        for name, entry in (data.get("files") or {}).items():
            fp = self.assets / name
            if not fp.is_file():
                continue
            actual = hashlib.sha256(fp.read_bytes()).hexdigest()
            if actual != entry.get("sha256"):
                stale.append(name)
        self.assertEqual(
            stale, [],
            "下列资产内容已变但 manifest 未刷新——跑 "
            "`python -m gui.builtin_sync --write-manifest` 后重新提交：\n  "
            + "\n  ".join(stale),
        )


if __name__ == "__main__":
    unittest.main()
