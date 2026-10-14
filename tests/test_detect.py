from pathlib import Path

import pytest

import detect
from fixtures import CHECK_HEADER, LAB_HEADER, RIA_HEADER, check, ria, xlsx

SAMPLE = Path(__file__).parent.parent / "DataGrid - 2026-10-14T150932.277.xlsx"


def test_kinds_from_header(tmp_path):
    r = detect.read(xlsx(tmp_path / "DataGrid.xlsx", RIA_HEADER, [ria("26437-RIA-04C-QC-PIT-OP-00004")]))
    c = detect.read(xlsx(tmp_path / "DataGrid (1).xlsx", CHECK_HEADER,
                         [check("T-1", "26437-RIA-04C-QC-PIT-OP-00004")]))
    lab = detect.read(xlsx(tmp_path / "DataGrid (2).xlsx", LAB_HEADER, [["x", "y", "z"]]))
    assert (r.kind, c.kind, lab.kind) == ("ria", "checklist", "other")
    assert "Lab report" in lab.error
    assert c.header.count("Task Number") == 2


def test_trims_and_skips_blank_rows(tmp_path):
    rows = [ria(" 26437-RIA-04C-QC-PIT-OP-00004  "), [None] * 7, ["  "] * 7]
    t = detect.read(xlsx(tmp_path / "a.xlsx", RIA_HEADER, rows))
    assert len(t.rows) == 1
    assert t.rows[0][1] == "26437-RIA-04C-QC-PIT-OP-00004"


def test_unreadable_file(tmp_path):
    p = tmp_path / "bad.xlsx"
    p.write_text("not excel")
    t = detect.read(p)
    assert t.kind == "other" and t.error.startswith("Cannot read")


def test_expand_drop_folder_and_lock(tmp_path):
    xlsx(tmp_path / "a.xlsx", RIA_HEADER, [])
    (tmp_path / "~$a.xlsx").write_text("lock")
    (tmp_path / "notes.txt").write_text("x")
    assert [p.name for p in detect.expand_drop([tmp_path])] == ["a.xlsx"]


@pytest.mark.skipif(not SAMPLE.exists(), reason="ornek checklist yok")
def test_real_checklist_sample():
    t = detect.read(SAMPLE)
    assert t.kind == "checklist"
    assert len(t.rows) == 107
    assert t.header[6] == "Related RIA"
