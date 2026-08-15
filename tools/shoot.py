"""
Renders an HTML file to a PNG of an exact size with headless Chromium.

    python tools/shoot.py page.html out.png 1080 2340

Why this exists rather than a one-line subprocess call: headless=new keeps
about 90 pixels of the window for browser chrome, so asking for a window of
exactly 1080x2340 gives a viewport of 1080x2250. Chromium still writes a
2340-tall PNG, but the bottom 90 pixels are never painted -- which quietly
slices the app's bottom bar in half. Every screen renderer goes through this
function so that bug cannot come back one file at a time.

The taller window has a sharp edge of its own: an element positioned
`absolute; bottom:0` inside a body that is NOT itself positioned resolves
against the VIEWPORT, so the extra slack pushes it below the crop and it
disappears. shoot() refuses to render such a page rather than writing a
plausible-looking broken image.
"""
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
SLACK = 240  # window rows to add, then crop away


def _check_positioning(html_text: str, path: Path) -> None:
    """Absolute children need a positioned body, or SLACK moves them."""
    if "position:absolute" not in html_text.replace(" ", ""):
        return
    body_rule = re.search(r"body\s*\{([^}]*)\}", html_text, re.S)
    if body_rule and "position:relative" in body_rule.group(1).replace(" ", ""):
        return
    raise SystemExit(
        f"{path}: this page positions elements absolutely but its body{{}} has no "
        f"position:relative. Add it, or the bottom bar will render off the crop."
    )


def shoot(html: Path, png: Path, w: int, h: int) -> Path:
    _check_positioning(html.read_text(encoding="utf-8"), html)
    png.parent.mkdir(parents=True, exist_ok=True)
    png.unlink(missing_ok=True)          # never let a stale file look like success
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                        "--force-device-scale-factor=1", f"--window-size={w},{h + SLACK}",
                        f"--screenshot={png}", f"file://{html.resolve()}"],
                       capture_output=True, timeout=120)
    if r.returncode != 0 or not png.exists():
        raise SystemExit(f"chrome failed on {html} (exit {r.returncode}): "
                         f"{r.stderr.decode(errors='replace')[:500]}")
    with Image.open(png) as im:
        if im.width < w or im.height < h:
            raise SystemExit(f"{png}: chrome produced {im.size}, need at least {(w, h)}. "
                             f"Cropping would pad it with black.")
        if im.size != (w, h):
            im.convert("RGB").crop((0, 0, w, h)).save(png)
    return png


def main() -> int:
    if len(sys.argv) != 5:
        print(__doc__.strip())
        return 1
    html, png, w, h = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    out = shoot(html, png, w, h)
    print(f"{out}  {out.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
