import pathlib

p = pathlib.Path("tests/test_deslop_and_export.py")
s = p.read_text(encoding="utf-8")
marker = "class TestWritingExportAndReorder(unittest.TestCase):"
assert marker in s, "marker 未找到"

NL = chr(92) + "n"   # 生成字面量 \n（两字符），避免落到源码里成为真换行

new = (
    "class TestLoneSurrogateHandling(unittest.TestCase):" + NL +
    '    """孤立代理字符（U+D800-D+DFFF）不能进 XML / 不能以 500 收场（2026-11-05）。' + NL +
    NL +
    "    这类字符无法编码成 UTF-8。正常读文件不会产生（严格解码会拒绝），但前端" + NL +
    "    贴文本、剪贴板工具可以带进来。原来的表现：落盘时 UnicodeEncodeError →" + NL +
    "    500「内部错误」；若绕过去进了 docx/epub，产出的 XML 直接非法。" + NL +
    '    """' + NL +
    NL +
    "    SUR = chr(0xD800)   # 源码里不写真实代理字符（写不出来）" + NL +
    NL +
    "    def test_escape_xml_strips_surrogates(self):" + NL +
    "        import xml.etree.ElementTree as ET" + NL +
    "        from gui import writing_extra" + NL +
    '        out = writing_extra._escape_xml(f"正文{self.SUR}孤立")' + NL +
    '        ET.fromstring(f"<r>{out}</r>")      # 不抛即合法' + NL +
    "        self.assertNotIn(self.SUR, out)" + NL +
    NL +
    "    def test_import_chapter_rejects_with_400(self):" + NL +
    "        import tempfile" + NL +
    "        from pathlib import Path as _P" + NL +
    "        from gui import writing_service" + NL +
    "        from gui.services import ServiceError" + NL +
    "        from tests import _isolation" + NL +
    '        tmp = tempfile.mkdtemp(prefix="sur_")' + NL +
    "        iso = _isolation.isolate_paths(_P(tmp))" + NL +
    "        iso.__enter__()" + NL +
    "        try:" + NL +
    "            from gui import db" + NL +
    "            db.init_schema()" + NL +
    "            db.apply_migrations()" + NL +
    "            with self.assertRaises(ServiceError) as cm:" + NL +
    '                writing_service.import_chapter("p1", 1, f"第1章' + NL + '正文{self.SUR}坏")' + NL +
    "            self.assertEqual(cm.exception.code, 400)" + NL +
    '            self.assertIn("U+D800", cm.exception.message)' + NL +
    "        finally:" + NL +
    "            iso.__exit__(None, None, None)" + NL +
    NL +
    NL
)

p.write_text(s.replace(marker, new + marker, 1), encoding="utf-8")
print("测试已插入")
