"""API 手册覆盖守卫（2026-11-03）。

背景：``docs/AGENT_API.md`` 自称「全量端点清单」，实际长期滞后——第 5 节标题
停在「97 端点」，而 ``len(gui.router.ROUTES)`` 早已是 132；有 34 个端点
（离线工具库 10 个、精华库 17 个、写作分析 4 个、平台诊断 3 个）根本没写进手册。
外部智能体（Qoder / Cline / Claude）是**按手册调用 API 的**，手册缺失＝功能对它们不存在。

本测试用 ``gui.router.ROUTES``（唯一真相源）反查文档文本：
每个端点的路径签名（``/api/book/{book_id}/chapter/{idx}`` 形式）必须在文档里出现。
路径参数统一写成 ``{name}``，与手册既有风格一致。
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DOC = ROOT / "docs" / "AGENT_API.md"


def _signature(pattern: str) -> str:
    """把路由正则转成手册写法。

    ``^/api/book/(?P<book_id>[^/]+)/chapter/(?P<idx>\\d+)$``
    → ``/api/book/{book_id}/chapter/{idx}``
    """
    s = pattern.lstrip("^").rstrip("$")
    s = re.sub(r"\(\?P<(\w+)>[^)]*\)", r"{\1}", s)
    return s.replace("\\/", "/").replace("\\.", ".")


class TestAdminAssetKindOptions(unittest.TestCase):
    """管理后台的资产类型下拉必须与后端白名单一致（2026-11-05）。

    原先前端写的是 'voice_card' / 'genre_prose_card'，不在后端
    asset_index.ASSET_KINDS 里——选中即 400「未知资产类型」，整块变红色错误；
    'report' 虽是虚拟 kind 能过，但恒为 0 条。
    """

    def test_frontend_kinds_subset_of_backend(self):
        import re
        from pathlib import Path as _P
        root = _P(__file__).resolve().parent.parent
        admin = (root / "gui/web/src/components/AdminWorkbench.tsx").read_text(
            encoding="utf-8")
        m = re.search(r"const ASSET_KINDS = \[(.*?)\]", admin, re.S)
        self.assertIsNotNone(m, "找不到前端 ASSET_KINDS")
        fe = [k.strip().strip("'\"") for k in m.group(1).replace("\n", " ").split(",")]
        fe = [k for k in fe if k]

        src = (root / "gui/asset_index.py").read_text(encoding="utf-8")
        start = src.index("ASSET_KINDS = (")
        depth = 0
        end = start
        for i in range(src.index("(", start), len(src)):
            if src[i] == "(":
                depth += 1
            elif src[i] == ")":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        be = set(re.findall(r"[\"']([a-z_]+)[\"']", src[start:end]))

        bad = [k for k in fe if k not in be]
        self.assertEqual(bad, [],
                         f"前端提供了后端不认的 kind：{bad}（后端合法：{sorted(be)}）")


class TestApiDocCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from gui import router
        cls.routes = router.ROUTES
        cls.doc = DOC.read_text(encoding="utf-8")

    def test_every_route_documented(self):
        missing = []
        for method, pat, _fn in self.routes:
            sig = _signature(pat.pattern)
            # 手册可能写完整签名，也可能只写到参数前的固定前缀
            # （如 /api/book/{book_id} 覆盖了所有 /api/book/{book_id}/... 的说明）
            short = sig.split("{")[0].rstrip("/")
            if sig in self.doc or (short and short in self.doc):
                continue
            missing.append(f"{method} {sig}")
        self.assertEqual(
            missing, [],
            "下列端点未写进 docs/AGENT_API.md（外部智能体按手册调用，缺失即等于不存在）：\n  "
            + "\n  ".join(sorted(missing)),
        )

    def test_endpoint_count_in_heading_matches_reality(self):
        """第 5 节标题里的端点数必须与 ROUTES 实测一致。"""
        m = re.search(r"## 5\. 全量 REST API 端点清单（(\d+) 端点速查）", self.doc)
        self.assertIsNotNone(m, "找不到第 5 节标题，或标题格式被改动")
        self.assertEqual(
            int(m.group(1)), len(self.routes),
            "第 5 节标题的端点数与 len(router.ROUTES) 不一致；"
            "新增/删除端点后请同步该数字。",
        )


if __name__ == "__main__":
    unittest.main()
