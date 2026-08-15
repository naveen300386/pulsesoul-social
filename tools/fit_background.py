"""
Learns the PulseSoul store-card background from the cards you already have,
and bakes it to assets/template/background.png.

Nothing here is invented. It samples the real gradient from your existing
artwork -- the parts not covered by the phone or the headline -- fits a smooth
surface through those samples, and reconstructs the whole canvas including the
area hidden behind the phone. So new cards sit on the same background as the
eight you already published, not an approximation of it.

Run once:  python tools/fit_background.py
"""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "screenshots"
OUT = ROOT / "assets" / "template"

W, H = 1080, 1920
PHONE = (168, 300, 912, 1860)   # left, top, right, bottom - covered by the mockup
TEXT_BOTTOM = 260               # everything above this may contain headline text
DEGREE = 3                      # polynomial order per axis


def design_matrix(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    xs, ys = x / W, y / H
    return np.stack([xs ** i * ys ** j
                     for i in range(DEGREE + 1)
                     for j in range(DEGREE + 1)], axis=-1)


def background_mask() -> np.ndarray:
    """True where a pixel is pure background in every source card."""
    mask = np.ones((H, W), bool)
    l, t, r, b = PHONE
    mask[t:b, l:r] = False          # phone mockup
    mask[:TEXT_BOTTOM, :] = False   # headline and subhead
    return mask


def main() -> int:
    cards = sorted(SRC.glob("pulsesoul_*.png"))
    if not cards:
        print(f"No source cards in {SRC}")
        return 1

    mask = background_mask()
    ys, xs = np.where(mask)
    # thin the samples out; tens of thousands is plenty and keeps the fit quick
    step = max(1, len(xs) // 40000)
    xs, ys = xs[::step], ys[::step]

    stacks = []
    for card in cards:
        img = Image.open(card).convert("RGB")
        if img.size != (W, H):
            print(f"  skipping {card.name} ({img.size}, expected {W}x{H})")
            continue
        stacks.append(np.array(img).astype(float))
    if not stacks:
        print("No usable cards.")
        return 1

    # median across cards: kills any dialog dimming or overlay in one of them
    plate = np.median(np.stack(stacks), axis=0)
    print(f"sampled {len(stacks)} cards, {len(xs)} background points")

    A = design_matrix(xs, ys)
    gy, gx = np.mgrid[0:H, 0:W]
    G = design_matrix(gx.ravel(), gy.ravel())

    out = np.zeros((H, W, 3))
    for ch in range(3):
        coef, *_ = np.linalg.lstsq(A, plate[ys, xs, ch], rcond=None)
        out[..., ch] = (G @ coef).reshape(H, W)
        resid = np.abs(A @ coef - plate[ys, xs, ch])
        print(f"  channel {'RGB'[ch]}: mean error {resid.mean():.2f}, worst {resid.max():.1f} (of 255)")

    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(OUT / "background.png")
    print(f"\nwrote {(OUT / 'background.png').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
