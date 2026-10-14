"""Guncelleme gonder: src.zip (+ gerekirse kurulum) -> GitHub release.

Kullanim:  python build/publish.py <surum> [not] [--full]
  --full : EXE + kurulum dosyasini her durumda yeniden derle (ilk yayin).

Sira: version.txt -> (gerekirse) EXE + setup derle -> src.zip -> SELFTEST
(dagitilan EXE yeni src ile aciliyor mu) -> release -> git tag + push.
Selftest gecmezse hicbir sey yayinlanmaz.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
DIST = os.path.join(ROOT, "dist", "CheckList")
EXE = os.path.join(DIST, "CheckList.exe")
SETUP = os.path.join(ROOT, "build", "out", "CheckList-Setup.exe")
sys.path.insert(0, SRC)
sys.path.insert(0, ROOT)
import updater  # noqa: E402

RELEASE_REPO = f"{updater.GITHUB_OWNER}/{updater.GITHUB_REPO}"

EXE_EMBEDDED = ("launcher.py", "license_client.py", "license_secret.txt",
                "requirements.txt", "build/CheckList.spec", "build/installer.iss")
EXE_EMBEDDED_DIRS = ("assets/",)


def make_src_zip(src_dir, zip_path):
    """src/'nin tamami (liste elle tutulmaz -> yeni dosya unutulamaz)."""
    names = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for base, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                if f.endswith(".pyc"):
                    continue
                full = os.path.join(base, f)
                rel = os.path.relpath(full, src_dir).replace("\\", "/")
                z.write(full, rel)
                names.append(rel)
    return names


def build_notes(zip_sha, setup_sha, extra, min_launcher=1):
    lines = [extra, ""] if extra else []
    # Kurulu (eski) src bu satira bakip kod yerine tam kurulumu secer.
    lines.append(f"MIN_LAUNCHER: {min_launcher}")
    lines.append("SHA256: " + zip_sha)
    if setup_sha:
        lines.append("SETUP_SHA256: " + setup_sha)
    return "\n".join(lines)


def exe_needs_rebuild(changed_paths):
    hits = []
    for raw in changed_paths or ():
        path = str(raw).replace("\\", "/").strip()
        if path in EXE_EMBEDDED or any(path.startswith(d) for d in EXE_EMBEDDED_DIRS):
            hits.append(path)
    return ", ".join(hits)


def must_attach_setup(min_launcher, reason):
    """Kurulum dosyasi HER release'e eklenir. Paylasilan kurulum linki
    (releases/latest/download/CheckList-Setup.exe) son release'e bakar;
    v0.2.0 yalniz src.zip ile cikinca link kirildi (olculdu). Kurulu
    makineler yine kod yolunu secer (decide_update_kind)."""
    return True


def check_setup_is_fresh(version, dist_dir):
    vfile = os.path.join(dist_dir, "src", "version.txt")
    if not os.path.isfile(vfile):
        return f"Kurulum kaynagi yok: {vfile} (--full ile derle)"
    built = open(vfile, encoding="utf-8").read().strip()
    if built != version:
        return f"Kurulum dosyasi BAYAT: icinde {built} var, yayinlanan {version}."
    return ""


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(cmd, **kw):
    print(">", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT, **kw)


def changed_since_last_release():
    tag = _run(["git", "describe", "--tags", "--abbrev=0"], capture_output=True, text=True)
    if tag.returncode != 0 or not tag.stdout.strip():
        return None   # ilk yayin
    diff = _run(["git", "diff", "--name-only", tag.stdout.strip() + "..HEAD"], capture_output=True, text=True)
    return [l for l in diff.stdout.splitlines() if l.strip()]


def find_iscc():
    found = shutil.which("iscc")
    if found:
        return found
    for base in (os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
                 os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", "")):
        p = os.path.join(base, "Inno Setup 6", "ISCC.exe")
        if base and os.path.isfile(p):
            return p
    return ""


def build_all():
    if not os.path.isfile(os.path.join(ROOT, "license_secret.txt")):
        return "license_secret.txt yok: lisanssiz EXE yayinlanmaz."
    r = _run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
              "--distpath", "dist", "--workpath", os.path.join("build", "work"),
              os.path.join("build", "CheckList.spec")])
    if r.returncode:
        return "PyInstaller basarisiz."
    shutil.rmtree(os.path.join(DIST, "src"), ignore_errors=True)
    shutil.copytree(SRC, os.path.join(DIST, "src"), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    iscc = find_iscc()
    if not iscc:
        return "Inno Setup (ISCC.exe) bulunamadi."
    if _run([iscc, os.path.join("build", "installer.iss")]).returncode:
        return "Inno Setup basarisiz."
    return ""


def selftest(exe, src_dir):
    if not os.path.isfile(exe):
        return f"{exe} yok: once --full ile derle."
    try:
        r = subprocess.run([exe, "--selftest", src_dir], timeout=120)
    except subprocess.TimeoutExpired:
        return "Selftest zaman asimi."
    return "" if r.returncode == 0 else f"Selftest basarisiz (cikis {r.returncode})."


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    version = argv[0].lstrip("v").strip()
    full = "--full" in argv
    rest = [a for a in argv[1:] if a != "--full"]
    notes = rest[0].strip() if rest else ""

    with open(os.path.join(SRC, "version.txt"), "w", encoding="utf-8") as f:
        f.write(version)
    changed = changed_since_last_release()
    reason = "ilk yayin" if changed is None else exe_needs_rebuild(changed)
    import launcher
    if updater.MIN_LAUNCHER > launcher.LAUNCHER_VERSION:
        print(f"[HATA] MIN_LAUNCHER {updater.MIN_LAUNCHER} > LAUNCHER_VERSION {launcher.LAUNCHER_VERSION}")
        return 1
    with_setup = full or must_attach_setup(updater.MIN_LAUNCHER, reason)
    if with_setup:
        print("EXE derleniyor:", reason or "--full")
        problem = build_all() or check_setup_is_fresh(version, DIST)
        if problem:
            print("[HATA]", problem)
            return 1

    tmp = tempfile.mkdtemp(prefix="checklist_pub_")
    zip_path = os.path.join(tmp, updater.ASSET_NAME)
    make_src_zip(SRC, zip_path)
    staged = os.path.join(tmp, "src")
    zipfile.ZipFile(zip_path).extractall(staged)
    problem = selftest(EXE, staged)
    if problem:
        print("[HATA]", problem, "-- yayinlanmadi.")
        return 1
    print("Selftest gecti: dagitilan EXE yeni kodla aciliyor.")

    upload = [zip_path]
    setup_sha = None
    if with_setup:
        setup_sha = _sha(SETUP)
        upload.append(SETUP)
    body = build_notes(_sha(zip_path), setup_sha, notes, updater.MIN_LAUNCHER)
    tag = "v" + version
    _run(["gh", "release", "delete", tag, "--yes", "--cleanup-tag", "--repo", RELEASE_REPO])
    if _run(["gh", "release", "create", tag, *upload, "--title", tag, "--notes", body,
             "--repo", RELEASE_REPO]).returncode:
        print("[HATA] Release olusturulamadi (gh auth?).")
        return 1
    # Dogrulama: istemcinin gordugu releases/latest bu surum mu?
    import json
    import urllib.request
    req = urllib.request.Request(updater.RELEASE_API, headers={"User-Agent": updater._UA})
    latest = json.load(urllib.request.urlopen(req, timeout=15))["tag_name"]
    if latest != tag:
        print(f"[HATA] releases/latest {latest} donuyor, {tag} degil.")
        return 1
    _run(["git", "add", "-A"])
    _run(["git", "commit", "-m", f"Release {tag}"])
    _run(["git", "tag", "-f", tag])
    _run(["git", "push", "--follow-tags"])
    _run(["git", "push", "-f", "origin", tag])
    print(f"[OK] {tag} yayinlandi.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
