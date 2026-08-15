"""
Proves the card builder matches your existing artwork.

It takes a card you already published, cuts the phone screenshot back out of
it, feeds that through tools/make_card.py with the same headline, and compares
the result to the original pixel by pixel.

    python tools/verify_card.py

If the difference is small, a new card built from a fresh screenshot will sit
next to the old eight without looking out of place. If it is large, the
measurements in make_card.py have drifted and new cards would look wrong --
which you would otherwise only discover after they had been posted.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.make_card import PHONE_BOX, build  # noqa: E402

CASES = [
    ("pulsesoul_06", "A quiet safety net", "CareShield: optional, and never an alarm"),
    ("pulsesoul_11", "Made the way you like", "Themes, quality, notifications, control"),
]


def main() -> int:
    tmp = ROOT / "assets" / "template" / "_verify"
    tmp.mkdir(parents=True, exist_ok=True)
    worst = 0.0

    for name, headline, subhead in CASES:
        original_path = ROOT / "assets" / "screenshots" / f"{name}.png"
        if not original_path.exists():
            print(f"  {name}: missing, skipped")
            continue

        original = Image.open(original_path).convert("RGB")
        crop = original.crop(PHONE_BOX)
        shot = tmp / f"{name}_phone.png"
        crop.save(shot)

        # crop=0: this is an exact phone crop out of a finished card, not a
        # raw screenshot, so it has no status or navigation bar to trim.
        rebuilt = build(shot, headline, subhead, crop_top=0.0, crop_bottom=0.0)
        a = np.array(original).astype(int)
        b = np.array(rebuilt).astype(int)
        diff = np.abs(a - b).mean(axis=2)

        l, t, r, bo = PHONE_BOX
        bg = diff.copy()
        bg[t:bo, l:r] = 0
        text_band = diff[100:260].mean()
        phone_band = diff[t:bo, l:r].mean()
        gradient = np.concatenate([diff[300:1860, :l].ravel(), diff[300:1860, r:].ravel()]).mean()

        print(f"{name}:")
        print(f"   background gradient  mean diff {gradient:5.2f} / 255")
        print(f"   phone area           mean diff {phone_band:5.2f} / 255")
        print(f"   headline band        mean diff {text_band:5.2f} / 255")

        side = Image.new("RGB", (1080, 960))
        side.paste(original.resize((540, 960)), (0, 0))
        side.paste(rebuilt.resize((540, 960)), (540, 0))
        side.save(tmp / f"{name}_compare.png")
        worst = max(worst, gradient, phone_band)

    print(f"\nside-by-side images in {tmp.relative_to(ROOT)}/")
    if worst > 12:
        print(f"FAIL: worst mean difference {worst:.1f}/255 - the template has drifted")
        return 1
    print(f"OK: worst mean difference {worst:.1f}/255")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
