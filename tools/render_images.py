"""
Reframes the PulseSoul Play Store screenshots into the shapes each social
platform wants.

It does NOT draw any artwork. It takes your existing 1080x1920 store art,
scales it to fit, and fills the leftover space with a blurred, darkened copy
of the same image -- so the dark purple gradient just continues outwards.

Run:  python tools/render_images.py
Out:  rendered/<name>__sq.jpg  1080x1080   (Threads, Bluesky, Mastodon, Telegram, LinkedIn)
      rendered/<name>__p45.jpg 1080x1350   (Instagram, Facebook)
      rendered/<name>__pin.jpg 1000x1500   (Pinterest)
"""
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "screenshots"
OUT = ROOT / "rendered"

SHAPES = {
    "sq": (1080, 1080),
    "p45": (1080, 1350),
    "pin": (1000, 1500),
}

# How much of the source height to trim off the bottom. Keep this SMALL: the
# phone mockup inside a 1920-tall card ends at y=1860, so anything above 0.031
# starts eating the app's own bottom navigation bar. It was 0.06 once, which
# cut 56 pixels of screen off every posted image and removed the dock entirely.
TRIM_BOTTOM = 0.02


def cover(img: Image.Image, w: int, h: int) -> Image.Image:
    """Scale + centre-crop so the image completely fills w x h."""
    scale = max(w / img.width, h / img.height)
    tmp = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
    left = (tmp.width - w) // 2
    top = (tmp.height - h) // 2
    return tmp.crop((left, top, left + w, top + h))


def contain(img: Image.Image, w: int, h: int) -> Image.Image:
    """Scale so the whole image fits inside w x h. Nothing is cut off."""
    scale = min(w / img.width, h / img.height)
    return img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)


def reframe(src: Path, w: int, h: int) -> Image.Image:
    img = Image.open(src).convert("RGB")
    img = img.crop((0, 0, img.width, int(img.height * (1 - TRIM_BOTTOM))))

    bg = cover(img, w, h).filter(ImageFilter.GaussianBlur(60))
    bg = ImageEnhance.Brightness(bg).enhance(0.62)

    fg = contain(img, w, h)
    bg.paste(fg, ((w - fg.width) // 2, (h - fg.height) // 2))
    return bg


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sources = sorted(SRC.glob("*.png")) + sorted(SRC.glob("*.jpg"))
    if not sources:
        print(f"No screenshots found in {SRC}")
        return 1

    made = 0
    for src in sources:
        for tag, (w, h) in SHAPES.items():
            dst = OUT / f"{src.stem}__{tag}.jpg"
            reframe(src, w, h).save(dst, "JPEG", quality=88, optimize=True)
            made += 1
            print(f"  {dst.relative_to(ROOT)}  {w}x{h}  {dst.stat().st_size // 1024} KB")
    print(f"\n{made} images written to {OUT.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
