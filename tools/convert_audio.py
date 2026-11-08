"""Convert every .mp3 under assets/ to .ogg (needed for the browser build). Requires ffmpeg on your PATH.
Run from the project folder:  python tools/convert_audio.py
The .mp3 files stay where they are (desktop play uses them); the web build looks for the .ogg next to each one."""
import pathlib
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parent.parent / "assets"
files = sorted(root.rglob("*.mp3"))
if not files:
    sys.exit("No .mp3 files found under assets/.")
for mp3 in files:
    ogg = mp3.with_suffix(".ogg")
    if ogg.exists() and ogg.stat().st_mtime >= mp3.stat().st_mtime:
        continue
    print("Converting", mp3.relative_to(root))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-c:a", "libvorbis", "-q:a", "3", str(ogg)], check=True)
print("Done.")
