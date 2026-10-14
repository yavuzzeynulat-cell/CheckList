import compare
import detect
import rules
from fixtures import CHECK_HEADER, RIA_HEADER, check, ria, xlsx

A = "26437-RIA-04C-QC-PIT-OP-00004"
B = "26437-RIA-02B-DR-PR2-BX-00031"
C = "26437-RIA-04D-EW-REX-MW-00906"
D = "26437-RIA-02B-ST-IN2-RW-00571"


def _tables(tmp_path, rias, checks):
    r = detect.read(xlsx(tmp_path / "r.xlsx", RIA_HEADER, rias))
    c = detect.read(xlsx(tmp_path / "c.xlsx", CHECK_HEADER, checks))
    return [r], [c]


def test_matched_and_missing(tmp_path):
    r, c = _tables(tmp_path, [ria(A), ria(B), ria(D)],
                   [check("CHL-1", A), check("CHL-2", A, "CLOSED"), check("CHL-3", B), check("x", "-"),
                    check("y", "123")])
    res = compare.run(r, c)
    assert [(m[0][1], m[1][0]) for m in res.matched] == [(A, "CHL-1"), (A, "CHL-2"), (B, "CHL-3")]
    assert [m[1] for m in res.missing] == [D]
    assert res.with_checklist == 2
    assert res.orphans == 2                    # '-' ve '123'


def test_rejected_checklists_are_dropped(tmp_path):
    r, c = _tables(tmp_path, [ria(A), ria(B), ria(D)],
                   [check("CHL-1", A, "REJECTED"), check("CHL-2", A, "OPEN"), check("CHL-3", B, " rejected "),
                    check("CHL-4", "26437-RIA-04D-EW-REX-MW-00906", "REJECTED")])
    res = compare.run(r, c)
    assert [m[1][0] for m in res.matched] == ["CHL-2"]
    assert [m[1] for m in res.missing] == [B, D]          # yalniz REJECTED'i olan B eksik sayilir
    assert res.rejected == 3
    assert res.orphans == 0                               # REJECTED olan yetim de sayilmaz


def test_match_ignores_case_and_spaces(tmp_path):
    r, c = _tables(tmp_path, [ria(A)], [check("CHL-1", " " + A.lower() + " ")])
    assert len(compare.run(r, c).matched) == 1


def test_part_filter_and_rule(tmp_path):
    r, c = _tables(tmp_path, [ria(A), ria(C), ria(B, title="Reinforcement of slab"), ria(D)], [check("CHL-1", A)])
    res = compare.run(r, c, exclude={"Activity": {"REX"}}, rules=rules.DEFAULT_RULES)
    assert [m[1] for m in res.missing] == [D]
    assert res.removed == {"Activity=REX": 1, "Document Title starts with Reinforcement": 1}
    assert (res.total, res.kept) == (4, 2)


def test_rule_switched_off(tmp_path):
    r, c = _tables(tmp_path, [ria(B, title="REINFORCEMENT check")], [])
    off = [dict(rules.DEFAULT_RULES[0], on=False)]
    assert len(compare.run(r, c, rules=off).missing) == 1
    assert len(compare.run(r, c, rules=rules.DEFAULT_RULES).missing) == 0


def test_several_ria_files_dedupe_and_column_union(tmp_path):
    t1 = detect.read(xlsx(tmp_path / "1.xlsx", RIA_HEADER, [ria(A), ria(B)]))
    t2 = detect.read(xlsx(tmp_path / "2.xlsx", RIA_HEADER + ["Chainage Start"],
                          [ria(B) + ["1+000"], ria(D) + ["2+000"]]))
    header, rows, dup = compare.ria_rows([t1, t2])
    assert header[-1] == "Chainage Start"
    assert [r[1] for r in rows] == [A, B, D]
    assert dup == 1
    assert rows[0][-1] is None and rows[2][-1] == "2+000"


def test_duplicate_column_names_kept_apart(tmp_path):
    c1 = detect.read(xlsx(tmp_path / "c1.xlsx", CHECK_HEADER, [check("T1", A)]))
    c2 = detect.read(xlsx(tmp_path / "c2.xlsx", CHECK_HEADER, [check("T2", B)]))
    header, rows = compare.combine([c1, c2])
    assert header == CHECK_HEADER
    assert [r[0] for r in rows] == ["T1", "T2"]


def test_no_checklist_means_all_missing(tmp_path):
    r = [detect.read(xlsx(tmp_path / "r.xlsx", RIA_HEADER, [ria(A), ria(B)]))]
    res = compare.run(r, [])
    assert len(res.missing) == 2 and res.check_header == []
