"""工具库响应形状守卫（2026-11-03）。

背景：8 个 ``/api/tools/*`` GET 端点走 ``services.get_*``，正常路径直接返回
库文件原样 ``{meta, goldfingers}``——``total_count`` 埋在 meta 里；而文件缺失
时返回 ``{total_count: 0, goldfingers: []}``。两种形状不一致，前端类型声明的是
``{totalCount, items}``，拿到的 totalCount 永远是 undefined，计数徽标空白。

修复：``_library_payload`` 统一把 total_count 提到顶层。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui import services  # noqa: E402

LIBRARIES = (
    ("goldfingers", "goldfinger-library.json"),
    ("hooks", "hook-library.json"),
    ("taboos", "taboo-library.json"),
    ("shuangdians", "shuangdian-library.json"),
    ("worlds", "world-library.json"),
    ("dialogues", "dialogue-library.json"),
    ("characters", "character-library.json"),
    ("emotions", "emotion-library.json"),
)


class TestToolsLibraryShape(unittest.TestCase):
    def test_every_library_exposes_total_count(self):
        for items_key, _fname in LIBRARIES:
            fn = getattr(services, f"get_{items_key}")
            with self.subTest(library=items_key):
                data = fn()
                self.assertIsInstance(data, dict)
                self.assertIn("total_count", data,
                              f"{items_key} 未把 total_count 提到顶层")
                self.assertIsInstance(data["total_count"], int)
                self.assertGreater(data["total_count"], 0,
                                   f"{items_key} 条目数为 0，库文件可能缺失")
                self.assertIsInstance(data.get(items_key), list)
                self.assertEqual(len(data[items_key]), data["total_count"],
                                 f"{items_key} 的 total_count 与实际条目数不符")

    def test_meta_preserved(self):
        """meta 仍要保留（版本/名称/描述），不能被归一化丢掉。"""
        data = services.get_hooks()
        self.assertIn("meta", data)
        self.assertIsInstance(data["meta"], dict)

    def test_missing_file_returns_same_shape(self, ):
        """库文件缺失时形状必须与正常路径一致。"""
        orig = services._load_library
        try:
            services._load_library = lambda _f: None
            data = services.get_hooks()
            self.assertEqual(data, {"total_count": 0, "hooks": []})
        finally:
            services._load_library = orig


if __name__ == "__main__":
    unittest.main()
