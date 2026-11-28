"""Build the public StoryBridge page into the SmileCard website: smilecard-site/storybridge/.

The live SmileCard website (Vercel, Root Directory smilecard-site/) has no build step, so the page is
built here and committed. It is the hosted copy of the app (`--mode hosted`): it explains StoryBridge,
has no upload form, and never calls the StoryBridge server. Its SmileCard menu links point to "/",
where the SmileCard pages are on the live site.

Run from the repo root after changing the frontend:
    .\\.venv\\Scripts\\python.exe scripts\\build_storybridge_page.py
It leaves frontend/dist/ alone (the volunteer's own copy of the app).
"""
import hashlib
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
OUT = ROOT / "smilecard-site" / "storybridge"
HILLS = FRONTEND / "src" / "assets" / "hero-hills.svg"


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    env = {**os.environ, "VITE_SMILECARD_SITE": "/"}
    subprocess.run(
        "npx vite build --mode hosted --base /storybridge/ --outDir ../smilecard-site/storybridge --emptyOutDir",
        cwd=FRONTEND, env=env, shell=True, check=True,
    )
    # The hills drawing carries a content credential, so it must be copied byte for byte.
    want = hashlib.sha256(HILLS.read_bytes()).hexdigest()
    copies = list(OUT.rglob("hero-hills*.svg"))
    if not copies or any(hashlib.sha256(p.read_bytes()).hexdigest() != want for p in copies):
        raise SystemExit("hero-hills.svg was not copied byte for byte")
    html = (OUT / "index.html").read_text(encoding="utf-8")
    if 'src="/storybridge/' not in html:
        raise SystemExit("index.html does not load its files from /storybridge/")
    files = sorted(p for p in OUT.rglob("*") if p.is_file())
    for p in files:
        print(f"{p.stat().st_size:>9,}  {p.relative_to(OUT).as_posix()}")
    print(f"{len(files)} files in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
