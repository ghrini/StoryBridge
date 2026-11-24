"""Build the SmileCard website for uploading to Wix: build/wix-site/ and build/smilecard-wix-site.zip.

The copy in smilecard-site/ is for this computer: its "StoryBridge" menu item opens the StoryBridge app
served next to it ("../"). On the public website there is no app to open (StoryBridge runs on a
volunteer's computer), so the menu item opens the StoryBridge information page instead. The home page
is also copied to index.html, so the website's main address opens it directly.

Run from the repo root:  .\\.venv\\Scripts\\python.exe scripts\\build_wix_site.py
"""
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "smilecard-site"
BUILD = ROOT / "build"
OUT = BUILD / "wix-site"
ZIP = BUILD / "smilecard-wix-site.zip"
HOME = "SmileCard Home v7.dc.html"
LOCAL_LINK = "href: '../'"
PUBLIC_LINK = "href: 'StoryBridge.dc.html'"
MENUS = ("PageHero.dc.html", HOME)


def build() -> list[Path]:
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SOURCE, OUT)
    for name in MENUS:
        page = OUT / name
        text = page.read_text(encoding="utf-8")
        if text.count(LOCAL_LINK) != 1:
            raise SystemExit(f"Expected exactly one StoryBridge menu link in {name}.")
        page.write_text(text.replace(LOCAL_LINK, PUBLIC_LINK), encoding="utf-8")
    shutil.copyfile(OUT / HOME, OUT / "index.html")  # the website's main address opens the home page

    files = sorted(p for p in OUT.rglob("*") if p.is_file())
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(OUT).as_posix())
    return files


if __name__ == "__main__":
    built = build()
    total = sum(p.stat().st_size for p in built)
    for path in built:
        print(f"{path.stat().st_size:>8,}  {path.relative_to(OUT).as_posix()}")
    print(f"{len(built)} files, {total:,} bytes -> {ZIP.relative_to(ROOT)} ({ZIP.stat().st_size:,} bytes)")
