import datetime as dt

import openpyxl

import dailyrias
import detect
from fixtures import RIA_HEADER, ria, xlsx

DR = "26437-RIA-04C-DR-IN2-BX-000{:02d}"


def _rows(*pairs):
    out = []
    for no, when in pairs:
        r = ria(no)
        r[4] = when
        out.append(r)
    return out


def _tables(tmp_path, rows):
    return [detect.read(xlsx(tmp_path / "r.xlsx", RIA_HEADER, rows))]


def test_all_rows_sorted_by_time_dateless_last(tmp_path):
    rows = _rows(("A-2", "25/04/2025 15:00"), ("A-1", "24/04/2025 18:30"), ("A-0", dt.datetime(2025, 4, 25)),
                 ("a-2", "25/04/2025 15:00"), ("N-1", None), ("N-0", ""))
    got = dailyrias.rows_for(_tables(tmp_path, rows))
    assert [r[1] for r in got] == ["A-1", "A-0", "A-2", "N-0", "N-1"]
    assert [dailyrias.when_text(r[0], True) for r in got] == ["Thu 24 Apr · 18:30", "Fri 25 Apr", "Fri 25 Apr · 15:00",
                                                              "time not given", "time not given"]
    assert dailyrias.when_text(got[2][0], False) == "15:00"
    assert dailyrias.many_days(got)


def test_part_filter_and_rules_leave_out(tmp_path):
    rows = _rows((DR.format(1), "25/04/2025 09:00"), ("26437-RIA-04C-DR-GEM-BX-00002", "25/04/2025 10:00"))
    rows.append(ria(DR.format(3), title="Reinforcement of wall"))
    t = _tables(tmp_path, rows)
    rules = [{"column": "Document Title", "op": "starts", "text": "Reinforcement", "on": True}]
    exclude = {"Activity": {"GEM"}}
    assert [r[1] for r in dailyrias.rows_for(t, exclude, rules)] == [DR.format(1)]
    assert dict(dailyrias.removed(t, exclude, rules)) == {"Activity=GEM": 1,
                                                          "Document Title starts with Reinforcement": 1}


def test_heading_from_first_and_last_time():
    t = lambda d, h: dt.datetime(2025, 4, d, h, 0)
    assert dailyrias.heading([(t(24, 18), "A", "", ""), (t(25, 19), "B", "", "")]) == \
        ("RIAs from 24 Apr 2025, 18:00 to 25 Apr 2025, 19:00", "2 RIAs")
    assert dailyrias.heading([(t(25, 9), "A", "", ""), (None, "B", "", "")]) == \
        ("RIAs on 25 Apr 2025, 09:00", "2 RIAs · 1 time not given")
    assert dailyrias.heading([(t(24, 0), "A", "", ""), (t(25, 0), "B", "", "")])[0] == \
        "RIAs from 24 Apr 2025 to 25 Apr 2025"
    assert dailyrias.heading([(None, "A", "", "")]) == ("Daily RIAs", "1 RIA · 1 time not given")


def test_sheet_has_boxes_and_tick_choice(tmp_path):
    p = xlsx(tmp_path / "r.xlsx", RIA_HEADER, _rows((DR.format(16), "25/04/2025 09:00")))
    out = dailyrias.make([p], tmp_path, today=dt.date(2025, 4, 25))
    assert out.name == "Daily RIAs 2025-04-25.xlsx"
    ws = openpyxl.load_workbook(out)[dailyrias.SHEET]
    assert ws.cell(1, 1).value == "RIAs on 25 Apr 2025, 09:00"
    assert [c.value for c in ws[4]] == [None, *dailyrias.HEADER[1:]]
    assert [c.value for c in ws[5]] == [dailyrias.BOX, "Drainage", DR.format(16), "Concrete pouring", "09:00"]
    assert dailyrias.TICK in ws.data_validations.dataValidation[0].formula1


def test_nothing_left_is_error(tmp_path):
    p = xlsx(tmp_path / "r.xlsx", RIA_HEADER, _rows((DR.format(1), "25/04/2025 09:00")))
    try:
        dailyrias.make([p], tmp_path, exclude={"Discipline": {"DR"}})
    except dailyrias.DailyRiasError:
        return
    raise AssertionError("no error")


def test_department_from_ria_number(tmp_path):
    rows = _rows((DR.format(16), "25/04/2025 09:00"), ("26437-RIA-04C-XY-IN2-BX-00017", "25/04/2025 10:00"),
                 ("26437-RIA-04C-QQ-IN2-BX-00018", "25/04/2025 11:00"))
    rows.append(ria("26437-RIA-04C-ZZ-IN2-BX-00001"))
    rows[-1][0] = "XY-Somewhere"
    # DR sabit tablodan, XY dosyadaki "XY-Somewhere" degerinden, QQ hicbir yerde yok -> kod
    assert [r[3] for r in dailyrias.rows_for(_tables(tmp_path, rows))][:3] == ["Drainage", "QQ", "Somewhere"]


def test_departments_grouped_then_time(tmp_path):
    rows = _rows(("26437-RIA-04C-EW-IN2-BX-00001", "24/04/2025 19:00"), ("26437-RIA-04C-DR-IN2-BX-00002", "25/04/2025 10:00"),
                 ("26437-RIA-04C-QQ-IN2-BX-00003", "24/04/2025 18:10"), ("26437-RIA-04C-DR-IN2-BX-00004", "24/04/2025 20:00"),
                 ("26437-RIA-04C-ST-IN2-BX-00005", "25/04/2025 08:00"))
    got = dailyrias.rows_for(_tables(tmp_path, rows))
    assert [(r[3], r[1][-1]) for r in got] == [("Drainage", "4"), ("Drainage", "2"), ("Structures", "5"),
                                               ("Earthworks", "1"), ("QQ", "3")]
