# Hosting THE LAST CONVOY in the browser (GitHub Pages)

1. Run `python tools/convert_audio.py` once (needs ffmpeg) and commit the new `.ogg` files next to the `.mp3` files.
2. Put `.github/workflows/pages.yml` in your repo and keep `main.py` in the repo root.
3. On GitHub: Settings -> Pages -> Source: **GitHub Actions**.
4. Push to `main`. The workflow builds with pygbag and publishes; the address appears in the workflow run (Actions tab).
5. The game page asks for one click/tap before it starts: that click is what lets the browser play sound.

Desktop play is unchanged (`python main.py` with normal pygame). Only the cloud build uses pygame-ce.
Settings and saves live in the browser's localStorage (per browser and device).


## Audio (updated)
You no longer need to run `tools/convert_audio.py` or commit `.ogg` files. The workflow builds from a temporary copy in which every `.mp3` is converted to `.ogg` and the `.mp3` removed (pygbag refuses to build while any `.mp3` is present). Your repo keeps the `.mp3` files for the desktop game. If you already committed `.ogg` files, that is harmless.
