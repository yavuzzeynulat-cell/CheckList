import zipfile

import publish


def test_zip_contains_whole_src_without_pycache(tmp_path):
    src = tmp_path / "src"
    (src / "steps").mkdir(parents=True)
    (src / "main.py").write_text("x")
    (src / "version.txt").write_text("1.0.0")
    (src / "steps" / "merge.py").write_text("x")
    (src / "__pycache__").mkdir()
    (src / "__pycache__" / "main.cpython-312.pyc").write_bytes(b"x")
    names = publish.make_src_zip(src, tmp_path / "src.zip")
    assert sorted(names) == ["main.py", "steps/merge.py", "version.txt"]
    assert sorted(zipfile.ZipFile(tmp_path / "src.zip").namelist()) == sorted(names)


def test_notes_carry_hashes():
    body = publish.build_notes("a" * 64, "b" * 64, "Fixed dates")
    assert body.splitlines()[0] == "Fixed dates"
    assert "SHA256: " + "a" * 64 in body and "SETUP_SHA256: " + "b" * 64 in body


def test_rebuild_needed_only_for_embedded_files():
    assert publish.exe_needs_rebuild(["src/steps/merge.py", "src/ui.py"]) == ""
    assert "launcher.py" in publish.exe_needs_rebuild(["launcher.py", "src/ui.py"])
    assert publish.exe_needs_rebuild(["assets/app.ico"]) == "assets/app.ico"
    assert publish.exe_needs_rebuild(["build/CheckList.spec"]) == "build/CheckList.spec"


def test_stale_setup_detected(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "version.txt").write_text("0.1.0")
    assert publish.check_setup_is_fresh("0.1.0", tmp_path) == ""
    assert "0.1.0" in publish.check_setup_is_fresh("0.2.0", tmp_path)


def test_notes_declare_min_launcher():
    body = publish.build_notes("a" * 64, None, "", min_launcher=2)
    assert "MIN_LAUNCHER: 2" in body


def test_every_release_carries_setup():
    # releases/latest/download/CheckList-Setup.exe linki hep calissin.
    assert publish.must_attach_setup(min_launcher=1, reason="") is True
