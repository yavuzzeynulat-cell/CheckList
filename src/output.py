"""Sonuc Excel'i (GUI'siz): ozet + iki sayfa, satirlar tum sutunlariyla.

'Summary' (ilk sayfa; mailde ekran goruntusu olarak gider): toplamin halka
pastasi, buyuk sayilar, departman basina olan / eksik / yuzde.
'Has Checklist': RIA'nin butun sutunlari + yaninda checklist'in butun
sutunlari; bir RIA'nin birden fazla checklist'i varsa her biri ayri satir.
'Missing Checklist': checklist'i olmayan RIA'lar, butun sutunlari.
(kullanici 2026-10-14: "full satiri verecek", "olmayanlarin da olanlarin da")
"""
import ctypes
import datetime as dt
import os
import tempfile
import uuid
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

SUMMARY_SHEET = "Summary"
CHART_DATA_SHEET = "Chart Data"
SCALE = 0.88   # Summary'nin tum olculeri: %100 olcekte tek A4 dikeye sigar (526pt -> 463pt, yazilabilir 487pt; olculdu)
DEPARTMENT_COLUMN = "Department Codes"
NO_DEPARTMENT = "(no department)"
GREEN = "2B8A3E"
RED = "C92A2A"
MATCHED_SHEET = "Has Checklist"
MISSING_SHEET = "Missing Checklist"
FILE_NAME = "CheckList Result.xlsx"
RIA_FILL = "DDEBF7"          # RIA sutunlarinin basligi
CHECK_FILL = "E2EFDA"        # checklist sutunlarinin basligi
MISSING_TAB = "F4B183"
MATCHED_TAB = "A9D08E"
MAX_WIDTH = 60
_DESKTOP = "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}"


class OutputError(Exception):
    pass


def desktop_dir():
    """Gercek masaustu (OneDrive yonlendirmesi dahil)."""
    try:
        class GUID(ctypes.Structure):
            _fields_ = [("d1", ctypes.c_ulong), ("d2", ctypes.c_ushort),
                        ("d3", ctypes.c_ushort), ("d4", ctypes.c_ubyte * 8)]
        u = uuid.UUID(_DESKTOP)
        g = GUID(u.fields[0], u.fields[1], u.fields[2], (ctypes.c_ubyte * 8).from_buffer_copy(u.bytes[8:]))
        out = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(out)) == 0:
            path = out.value
            ctypes.windll.ole32.CoTaskMemFree(out)
            return Path(path)
    except Exception:
        pass
    return Path.home() / "Desktop"


def base_dir():
    import settings
    return settings.load_out_dir() or desktop_dir() / "CheckList"


def day_dir(today=None):
    return base_dir() / f"{today or dt.date.today():%Y-%m-%d}"


def unique_path(path):
    path = Path(path)
    if not path.exists():
        return path
    n = 2
    while True:
        cand = path.with_name(f"{path.stem} ({n}){path.suffix}")
        if not cand.exists():
            return cand
        n += 1


def _width(v):
    if v is None:
        return 0
    if isinstance(v, (dt.datetime, dt.date)):
        return 16
    return max(len(line) for line in str(v).splitlines() or [""])


def _sheet(ws, header, fills, rows, tab):
    ws.sheet_properties.tabColor = tab
    thin = Side(style="thin", color="BFBFBF")
    ws.append(header)
    for j, fill in enumerate(fills, 1):
        c = ws.cell(1, j)
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor=fill)
        c.border = Border(bottom=thin)
        c.alignment = Alignment(vertical="center", wrap_text=True)
    widths = [len(h) for h in header]
    for r in rows:
        ws.append(r)
        for j, v in enumerate(r):
            widths[j] = max(widths[j], _width(v))
            if isinstance(v, dt.datetime):
                c = ws.cell(ws.max_row, j + 1)
                c.number_format = "dd/mm/yyyy" if (v.hour, v.minute) == (0, 0) else "dd/mm/yyyy hh:mm"
    for j, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(j)].width = min(MAX_WIDTH, max(8, w + 2))
    ws.freeze_panes = "A2"
    if header:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(header))}{max(1, len(rows) + 1)}"


def summary_rows(result):
    """[(departman, yesil, kirmizi)], cok RIA'li departman once. Yesil RIA sayar,
    checklist satiri degil (bir RIA'nin iki checklist'i bir kez sayilir)."""
    h = result.ria_header
    if "Document Number" not in h:
        return []
    d = h.index(DEPARTMENT_COLUMN) if DEPARTMENT_COLUMN in h else None
    n = h.index("Document Number")

    def dept(r):
        v = r[d] if d is not None else None
        return str(v).strip() if v not in (None, "") else NO_DEPARTMENT
    green, red = {}, {}
    seen = set()
    for r, _ in result.matched:
        key = str(r[n]).strip().upper()
        if key not in seen:
            seen.add(key)
            green[dept(r)] = green.get(dept(r), 0) + 1
    for r in result.missing:
        red[dept(r)] = red.get(dept(r), 0) + 1
    names = sorted(set(green) | set(red), key=lambda k: (-(green.get(k, 0) + red.get(k, 0)), k))
    return [(k, green.get(k, 0), red.get(k, 0)) for k in names]


def _project(result):
    """Karsilastirilan RIA'larin tek ortak proje kodu (Document Number'in ilk parcasi); yoksa None."""
    import riafilter
    h = result.ria_header
    if "Document Number" not in h:
        return None
    n = h.index("Document Number")
    found = {riafilter.parts(r[n])[0] for r in [r for r, _ in result.matched] + list(result.missing)}
    return found.pop() if len(found) == 1 and riafilter.OTHER not in found else None


def _version():
    try:
        return (Path(__file__).parent / "version.txt").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _summary(ws, result):
    """Mailde ekran goruntusu olarak giden sayfa (kullanici 2026-10-22): solda
    halka pasta, sagda uc buyuk sayi, altta departman tablosu.
    Altin oran: pasta alani / sag sutun ~ 1.618, pasta yuksekligi / tablo ~ 1.618,
    halka ici / disi = 0.62 (Excel'de olculdu)."""
    from openpyxl.chart import DoughnutChart, Reference
    from openpyxl.chart.label import DataLabelList
    from openpyxl.chart.layout import Layout, ManualLayout
    from openpyxl.chart.series import DataPoint
    from openpyxl.chart.shapes import GraphicalProperties
    from openpyxl.chart.text import RichText
    from openpyxl.drawing.text import CharacterProperties, Paragraph, ParagraphProperties
    from openpyxl.formatting.rule import DataBarRule

    ink, muted = "1D2420", "6B7280"

    def k(v):
        return round(v * SCALE, 2)

    def font(sz=10, b=False, c=ink):
        return Font(name="Segoe UI", size=round(sz * SCALE * 2) / 2, bold=b, color=c)
    thin = Side(style="thin", color="D9DDE1")
    rows = summary_rows(result)
    has, miss = sum(r[1] for r in rows), sum(r[2] for r in rows)
    tot = has + miss
    ws.sheet_properties.tabColor = ink
    ws.sheet_view.showGridLines = False
    for col, w in zip("ABCDEFGHIJ", (2, 14, 14, 14, 14, 3, 12, 14, 8.5, 2)):
        ws.column_dimensions[col].width = k(w)

    ws["B2"] = "Checklist Coverage"
    ws["B2"].font = font(20, True)
    project = _project(result)
    ws["B3"] = "  ·  ".join(([f"Project {project}"] if project else []) + [f"{dt.date.today():%d %b %Y}"])
    ws["B3"].font = font(10, c=muted)
    for c in range(2, 10):
        ws.cell(4, c).border = Border(bottom=Side(style="medium", color=ink))

    # Grafik 5. satirdan baslar, 6-18 esit: yuzde yazisi (seffaf grafigin
    # arkasindaki hucrede) halka merkezine oturur (olculdu, sapma 2px).
    ws.row_dimensions[5].height = k(8.3)
    for r in range(6, 19):
        ws.row_dimensions[r].height = k(19.55)
    ws.merge_cells("B11:E12")
    ws["B11"] = has / tot if tot else 0
    ws["B11"].number_format = "0%"
    ws["B11"].font = font(36, True, GREEN)
    ws["B11"].alignment = Alignment(horizontal="center", vertical="bottom")
    ws.merge_cells("B13:E13")
    ws["B13"] = "COVERAGE"
    ws["B13"].font = font(9, True, muted)
    ws["B13"].alignment = Alignment(horizontal="center", vertical="top")

    # pasta verisi ayri gizli sayfada: Summary'de sagda durunca yazdirmada
    # ikinci sayfaya tasiyordu (kullanici 2026-10-22)
    data = ws.parent.create_sheet(CHART_DATA_SHEET)
    data.sheet_state = "hidden"
    data.append(["Checklist Created", "Missing Checklist"])
    data.append([has, miss])
    pie = DoughnutChart(holeSize=62, firstSliceAng=0)
    pie.add_data(Reference(data, min_col=1, max_col=2, min_row=2, max_row=2), from_rows=True)
    pie.set_categories(Reference(data, min_col=1, max_col=2, min_row=1, max_row=1))
    s = pie.series[0]
    for i, color in enumerate((GREEN, RED)):
        pt = DataPoint(idx=i)
        pt.graphicalProperties.solidFill = color
        pt.graphicalProperties.line.solidFill = "FFFFFF"
        pt.graphicalProperties.line.width = 38100
        s.dPt.append(pt)
    s.dLbls = DataLabelList()
    s.dLbls.showVal = True
    s.dLbls.showPercent = s.dLbls.showCatName = s.dLbls.showSerName = False
    s.dLbls.showLegendKey = s.dLbls.showLeaderLines = False
    white = CharacterProperties(sz=int(1400 * SCALE), b=True, solidFill="FFFFFF")
    s.dLbls.txPr = RichText(p=[Paragraph(pPr=ParagraphProperties(defRPr=white), endParaRPr=white)])
    pie.legend = pie.title = None
    pie.visible_cells_only = False   # veri gizli sayfada; yoksa Excel pastayi hic cizmez (olculdu)
    pie.graphical_properties = GraphicalProperties(noFill=True)
    pie.graphical_properties.line.noFill = True
    pie.plot_area.graphicalProperties = GraphicalProperties(noFill=True)
    pie.plot_area.layout = Layout(manualLayout=ManualLayout(x=0.03, y=0.03, w=0.94, h=0.94))
    pie.height, pie.width = k(8.97), k(10.67)
    ws.add_chart(pie, "B5")

    def stat(r, label, val, color, sub):
        ws.merge_cells(start_row=r, start_column=7, end_row=r, end_column=9)
        ws.cell(r, 7, label).font = font(9, True, muted if color == ink else color)
        ws.cell(r, 7).alignment = Alignment(vertical="bottom")
        ws.merge_cells(start_row=r + 1, start_column=7, end_row=r + 2, end_column=7)
        ws.merge_cells(start_row=r + 1, start_column=8, end_row=r + 2, end_column=9)
        ws.cell(r + 1, 7, val).font = font(24, True, color)
        ws.cell(r + 1, 7).alignment = Alignment(horizontal="left", vertical="center")
        ws.cell(r + 1, 8, sub).font = font(10, c=muted)
        ws.cell(r + 1, 8).alignment = Alignment(vertical="center")
    stat(7, "■  CHECKLIST CREATED", has, GREEN, f"{has / tot:.0%} of RIAs" if tot else "")
    stat(11, "■  MISSING CHECKLIST", miss, RED, f"{miss / tot:.0%} of RIAs" if tot else "")
    stat(15, "TOTAL RIA", tot, ink, "compared")

    r0 = 20
    ws.row_dimensions[r0 - 1].height = k(14)
    ws.row_dimensions[r0].height = k(24)
    ws.cell(r0, 2, "By department").font = font(12, True)
    ws.cell(r0, 2).alignment = Alignment(vertical="center")
    heads = {2: "Department", 4: "Created", 5: "Missing", 7: "Coverage"}
    for c in range(2, 10):
        cell = ws.cell(r0 + 1, c, heads.get(c))
        cell.font = font(9, True, muted)
        cell.border = Border(bottom=Side(style="thin", color=ink))
        cell.alignment = Alignment(horizontal="right" if c in (4, 5) else "left")
    for i, (name, g, m) in enumerate(rows, 1):
        r = r0 + 1 + i
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
        ws.merge_cells(start_row=r, start_column=7, end_row=r, end_column=9)
        ws.cell(r, 2, name).font = font(10, True)
        ws.cell(r, 2).alignment = Alignment(shrink_to_fit=True)
        ws.cell(r, 4, g).font = font(10, c=GREEN)
        ws.cell(r, 5, m).font = font(10, c=RED)
        for c in (4, 5):
            ws.cell(r, c).alignment = Alignment(horizontal="right")
        ws.cell(r, 7, g / (g + m)).number_format = "0%"
        ws.cell(r, 7).font = font(10, True)
        for c in range(2, 10):
            ws.cell(r, c).border = Border(bottom=thin)
        ws.row_dimensions[r].height = k(20)
    if rows:
        ws.conditional_formatting.add(f"G{r0 + 2}:G{r0 + 1 + len(rows)}", DataBarRule(
            start_type="num", start_value=0, end_type="num", end_value=1, color="8CC99B", showValue=True))
    rf = r0 + len(rows) + 3
    ws.row_dimensions[rf - 1].height = k(10)
    notes = [f"Excluded by filter: {sum(result.removed.values())} RIAs",
             f"Rejected checklists ignored: {result.rejected}"]
    if _version():
        notes.append(f"CheckList v{_version()}")
    ws.cell(rf, 2, "  ·  ".join(notes)).font = font(8, c=muted)
    # tek A4 dikey (kullanici 2026-10-22); departman cogalip sigmazsa Excel kucultur
    ws.print_area = f"A1:J{rf}"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.orientation = "portrait"
    ws.print_options.horizontalCentered = True
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = ws.page_setup.fitToHeight = 1


def write(result, out_path):
    out_path = Path(out_path)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = MATCHED_SHEET
    rh, ch = result.ria_header, result.check_header
    _sheet(ws, rh + ch, [RIA_FILL] * len(rh) + [CHECK_FILL] * len(ch),
           [list(r) + list(c) for r, c in result.matched], MATCHED_TAB)
    _sheet(wb.create_sheet(MISSING_SHEET), rh, [RIA_FILL] * len(rh), [list(r) for r in result.missing], MISSING_TAB)
    _summary(wb.create_sheet(SUMMARY_SHEET, 0), result)
    wb.active = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".xlsx", dir=out_path.parent)
    os.close(fd)
    try:
        wb.save(tmp)
        os.replace(tmp, out_path)
    except OSError as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise OutputError(f"Could not save {out_path.name} (open in Excel?). Close it and try again.") from e
    return out_path
