"""Gunun RIA listesinden isaretlenebilir saha listesi (GUI'siz, CheckList karsilastirmasindan bagimsiz).

Aralik (dun aksam -> bugun 18-19) EDMS'te girilip indiriliyor (kullanici 2026-10-23):
dosyadaki butun RIA'lar alinir, baslik araligi dosyadaki ilk ve son zamandan yazar.
Elenenler: RIA parca filtresi (Filter adimindaki gibi) ve Settings'teki kurallar.
Zamanlar birden fazla gune degiyorsa zaman sutununa gun de yazilir ('Wed 22 Oct · 18:30').
Departman, RIA no, baslik ve zamanla
tek sayfalik 'Daily RIAs' yazilir. Her satirin basinda tik kutusu:
hucre ☐/☑ arasinda acilir listeden secilir, ☑ olunca satir yesile doner.
Basili kopyada bos kutu kalir, elle tiklenir.

EDMS'te 'Date and time for Inspection' iki bicimde geliyor (olculdu 2026-10-23):
datetime (Handover_Ornek.xlsx, saat 00:00) ya da '14/08/2025 15:00' metni (Book1.xlsx).
00:00 saat bilinmiyor sayilir: yalniz gun yazilir.
Tarihi hic olmayan RIA'da zaman yerine 'time not given' (kullanici 2026-10-23).

Departman RIA numarasinin 4. parcasindan (26437-RIA-04C-DR-...): 'Department Codes'
sutunu gondereni gosteriyor, isi degil (Handover_Ornek: hepsi ST-Structures, numarada
DR/ST/EW/UT). Ad DEPARTMENTS'tan (kullanici onayladi 2026-10-23); orada olmayan kod
sutundaki 'XX-Ad' degerlerinden, o da yoksa yalniz kod.
"""
import datetime as dt
import sys
from pathlib import Path

import openpyxl
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

import detect
import riafilter
import rules as rulemod

DATE_COLUMN = "Date and time for Inspection"
NUMBER_COLUMN = "Document Number"
TITLE_COLUMN = "Document Title"
DEPARTMENT_COLUMN = "Department Codes"
DEPARTMENTS = {"DR": "Drainage", "ST": "Structures", "EW": "Earthworks", "UT": "Utilities"}
SHEET = "Daily RIAs"
FILE_NAME = "Daily RIAs {day:%Y-%m-%d}.xlsx"
BOX, TICK = "☐", "☑"
HEADER = ("", "Department", "RIA No", "Title", "When")
WIDTHS = (5, 14, 32, 74, 19)
CENTER = (1, 2, 3, 5)    # kutu, departman, RIA no, zaman ortali
HEAD_FILL = "1F3864"
BAND_FILL = "F2F2F2"
DONE_FILL = "E2EFDA"
TEXT_FORMATS = ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%d.%m.%Y %H:%M", "%d.%m.%Y", "%Y-%m-%d %H:%M", "%Y-%m-%d")


class DailyRiasError(Exception):
    pass


def when(v):
    """Hucre degeri -> datetime; okunamazsa None."""
    if isinstance(v, dt.datetime):
        return v
    if isinstance(v, dt.date):
        return dt.datetime(v.year, v.month, v.day)
    s = str(v or "").strip()
    for f in TEXT_FORMATS:
        try:
            return dt.datetime.strptime(s, f)
        except ValueError:
            pass
    return None


def untimed(t):
    return t.hour == 0 and t.minute == 0


NO_TIME = "time not given"


def time_text(t):
    return "" if untimed(t) else f"{t:%H:%M}"


def when_text(t, with_day):
    if t is None:
        return NO_TIME
    if not with_day:
        return time_text(t)
    return f"{t:%a %d %b}" + (f" · {t:%H:%M}" if not untimed(t) else "")


def stamp(t):
    return f"{t:%d %b %Y}" if untimed(t) else f"{t:%d %b %Y, %H:%M}"


def span(rows):
    """(ilk, son) tarihli zaman; hic tarih yoksa None."""
    ws = [r[0] for r in rows if r[0] is not None]
    return (min(ws), max(ws)) if ws else None


def many_days(rows):
    sp = span(rows)
    return bool(sp) and sp[0].date() != sp[1].date()


def department_names(tables):
    """{'DR': 'Drainage'} -- 'Department Codes' sutununda gorulenlerden."""
    names = dict(DEPARTMENTS)
    for t in tables:
        if t.kind == detect.RIA and DEPARTMENT_COLUMN in t.header:
            i = t.header.index(DEPARTMENT_COLUMN)
            for r in t.rows:
                v = str(r[i] or "").strip()
                if "-" in v:
                    code, _, name = v.partition("-")
                    names.setdefault(code.strip().upper(), name.strip())
    return names


def department(number, names):
    p = str(number or "").split("-")
    code = p[3].strip().upper() if len(p) == 7 else ""
    return names.get(code, code)


def heading(rows):
    """(baslik, alt satir): 'RIAs from 22 Oct 2026, 18:00 to 23 Oct 2026, 19:00', '12 RIAs · 2 time not given'."""
    n = len(rows)
    sp = span(rows)
    if not sp:
        title = "Daily RIAs"
    elif stamp(sp[0]) == stamp(sp[1]):
        title = f"RIAs on {stamp(sp[0])}"
    else:
        title = f"RIAs from {stamp(sp[0])} to {stamp(sp[1])}"
    sub = f"{n} RIA{'s' if n != 1 else ''}"
    rest = sum(1 for r in rows if r[0] is None)
    if rest:
        sub += f" · {rest} {NO_TIME}"
    return title, sub


def rows_for(tables, exclude=None, rules=()):
    """[(datetime|None, RIA no, baslik, departman)] -- elenmeyenler; departman bir arada (DEPARTMENTS sirasi,
    bilinmeyenler sonda), icinde zamana (tarihsizler sonda) sonra numaraya gore; ayni RIA bir kez.
    removed(...) ayni elemeyi sayar."""
    return _collect(tables, exclude, rules)[0]


def removed(tables, exclude=None, rules=()):
    """{neden: adet} -- 'Activity=GEM', 'Document Title starts with Reinforcement'."""
    return _collect(tables, exclude, rules)[1]


def _collect(tables, exclude, rules):
    from collections import Counter
    out, seen, gone, names = [], set(), Counter(), department_names(tables)
    for t in tables:
        if t.kind != detect.RIA:
            continue
        if DATE_COLUMN not in t.header:
            raise DailyRiasError(f"{t.path.name}: no '{DATE_COLUMN}' column")
        i_date, i_no, i_title = (t.header.index(c) for c in (DATE_COLUMN, NUMBER_COLUMN, TITLE_COLUMN))
        for r in t.rows:
            no = str(r[i_no] or "").strip()
            if not no or no.upper() in seen:
                continue
            seen.add(no.upper())
            why = riafilter.reason(riafilter.parts(no), exclude or {}) or rulemod.reason(rules, t.header, r)
            if why:
                gone[why] += 1
                continue
            out.append((when(r[i_date]), no, str(r[i_title] or "").strip(), department(no, names)))
    order = list(DEPARTMENTS.values())
    out.sort(key=lambda x: (order.index(x[3]) if x[3] in order else len(order), x[3], x[0] is None,
                            x[0] or dt.datetime.min, x[1]))
    return out, gone


def write(rows, out_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = SHEET
    thin = Side(style="thin", color="BFBFBF")
    grid = Border(left=thin, right=thin, top=thin, bottom=thin)
    n = len(HEADER)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n)
    title, sub = heading(rows)
    ws.cell(1, 1, title).font = Font(size=16, bold=True, color=HEAD_FILL)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=n)
    ws.cell(2, 1, sub).font = Font(size=11, color="595959")
    ws.row_dimensions[1].height = 26

    for c, (name, width) in enumerate(zip(HEADER, WIDTHS), 1):
        cell = ws.cell(4, c, name)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=HEAD_FILL)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = grid
        ws.column_dimensions[cell.column_letter].width = width
    # departman, RIA no, zaman sutunlari en uzun yazi kadar (baslik dahil); Consolas daha genis
    with_day = many_days(rows)
    for col, k, extra in (("B", 1, 3), ("C", 2, 6), ("E", 4, 4)):
        texts = [HEADER[k]] + [(r[3], r[1], None, when_text(r[0], with_day))[k - 1] for r in rows]
        ws.column_dimensions[col].width = max(len(x) for x in texts) + extra
    ws.row_dimensions[4].height = 20

    first = 5
    for k, (w, no, title, dept) in enumerate(rows):
        r = first + k
        values = (BOX, dept, no, title, when_text(w, with_day))
        for c, v in enumerate(values, 1):
            cell = ws.cell(r, c, v)
            cell.border = grid
            cell.alignment = Alignment(horizontal="center" if c in CENTER else "left", vertical="center",
                                       wrap_text=c == 4, shrink_to_fit=c != 4, indent=1 if c == 4 else 0)
            if k % 2:
                cell.fill = PatternFill("solid", fgColor=BAND_FILL)
        ws.cell(r, 1).font = Font(size=14)
        ws.cell(r, 3).font = Font(name="Consolas", size=10)
        ws.row_dimensions[r].height = 15 * max(1, -(-len(title) // 80)) + 6
    last = first + len(rows) - 1

    if rows:
        dv = DataValidation(type="list", formula1=f'"{BOX},{TICK}"', allow_blank=True)
        dv.add(f"A{first}:A{last}")
        ws.add_data_validation(dv)
        ws.conditional_formatting.add(
            f"A{first}:E{last}",
            FormulaRule(formula=[f'$A{first}="{TICK}"'], fill=PatternFill("solid", fgColor=DONE_FILL),
                        font=Font(color="548235")))

    ws.freeze_panes = f"A{first}"
    ws.print_title_rows = "4:4"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_options.horizontalCentered = True
    ws.page_margins.left = ws.page_margins.right = 0.4

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return out_path


def make(paths, out_dir, exclude=None, rules=(), today=None):
    tables = [detect.read(p) for p in paths]
    rows = rows_for(tables, exclude, rules)
    if not rows:
        raise DailyRiasError("No RIA left in the list")
    return write(rows, Path(out_dir) / FILE_NAME.format(day=today or dt.date.today()))


if __name__ == "__main__":
    # python src/dailyrias.py <ria.xlsx> [cikti klasoru]   (eleme yok)
    print(make([sys.argv[1]], sys.argv[2] if len(sys.argv) > 2 else ".").resolve())
