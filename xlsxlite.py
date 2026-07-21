"""极简 xlsx 写入器（纯 stdlib，无 openpyxl 依赖）。

只覆盖本项目周报附件模板所需能力：inline string 单元格、数字单元格、
合并单元格、列宽、行高、四种样式（默认/正文带边框换行/表头/标题）。
样式索引约定：0=默认 1=正文(边框+换行+顶对齐) 2=表头(加粗+底色+边框+居中) 3=标题(加粗)。
"""
import zipfile
from xml.sax.saxutils import escape

NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
{sheet_overrides}
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""

_ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

_STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet {NS}>
<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FFDDEBF7"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"/><right style="thin"/><top style="thin"/><bottom style="thin"/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="4">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment vertical="center"/></xf>
</cellXfs>
</styleSheet>"""


def col_letter(idx: int) -> str:
    """1-based 列号 → 字母。"""
    s = ""
    while idx > 0:
        idx, r = divmod(idx - 1, 26)
        s = chr(65 + r) + s
    return s


class Sheet:
    def __init__(self, name):
        self.name = name
        self.rows = {}        # row_num -> {col_num: (value, style)}
        self.row_heights = {} # row_num -> pt
        self.col_widths = {}  # col_num -> width
        self.merges = []      # "A1:H1"

    def cell(self, row, col, value, style=0):
        self.rows.setdefault(row, {})[col] = (value, style)

    def merge(self, ref):
        self.merges.append(ref)

    def to_xml(self):
        parts = [f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<worksheet {NS}>']
        if self.col_widths:
            parts.append("<cols>")
            for c in sorted(self.col_widths):
                parts.append(f'<col min="{c}" max="{c}" width="{self.col_widths[c]}" customWidth="1"/>')
            parts.append("</cols>")
        parts.append("<sheetData>")
        for r in sorted(self.rows):
            ht = self.row_heights.get(r)
            attr = f' ht="{ht}" customHeight="1"' if ht else ""
            parts.append(f'<row r="{r}"{attr}>')
            for c in sorted(self.rows[r]):
                value, style = self.rows[r][c]
                ref = f"{col_letter(c)}{r}"
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    parts.append(f'<c r="{ref}" s="{style}"><v>{value}</v></c>')
                elif value is None or value == "":
                    parts.append(f'<c r="{ref}" s="{style}"/>')
                else:
                    txt = escape(str(value))
                    parts.append(f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{txt}</t></is></c>')
            parts.append("</row>")
        parts.append("</sheetData>")
        if self.merges:
            parts.append(f'<mergeCells count="{len(self.merges)}">')
            for m in self.merges:
                parts.append(f'<mergeCell ref="{m}"/>')
            parts.append("</mergeCells>")
        parts.append("</worksheet>")
        return "".join(parts)


class Workbook:
    def __init__(self):
        self.sheets = []

    def add_sheet(self, name):
        sh = Sheet(name)
        self.sheets.append(sh)
        return sh

    def save(self, path):
        sheet_tags, rel_tags, overrides = [], [], []
        for i, sh in enumerate(self.sheets, 1):
            sheet_tags.append(
                f'<sheet name="{escape(sh.name)}" sheetId="{i}" r:id="rId{i}"/>')
            rel_tags.append(
                f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>')
            overrides.append(
                f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
        styles_rid = len(self.sheets) + 1
        workbook = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets>{"".join(sheet_tags)}</sheets></workbook>')
        wb_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(rel_tags)
            + f'<Relationship Id="rId{styles_rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>')
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", _CONTENT_TYPES.format(sheet_overrides="".join(overrides)))
            z.writestr("_rels/.rels", _ROOT_RELS)
            z.writestr("xl/workbook.xml", workbook)
            z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
            z.writestr("xl/styles.xml", _STYLES)
            for i, sh in enumerate(self.sheets, 1):
                z.writestr(f"xl/worksheets/sheet{i}.xml", sh.to_xml())
