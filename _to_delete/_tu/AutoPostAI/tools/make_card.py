"""
Turns a raw phone screenshot into a PulseSoul store card matching the eight
you already published.

    python tools/make_card.py raw.png "Headline here" "Subhead here" pulsesoul_20

It composites three things and invents none of them:
  * the background is the real gradient, learned from your own cards by
    tools/fit_background.py
  * the phone is your actual screenshot, scaled and corner-rounded
  * the type is Poppins at the sizes measured off your existing cards

Every number below was measured from assets/screenshots/pulsesoul_06.png
rather than chosen, so new cards line up with the old ones exactly. Verify
any change with tools/verify_card.py, which rebuilds an existing card from
its own phone crop and reports the pixel difference.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "assets" / "template" / "background.png"
OUT_DIR = ROOT / "assets" / "screenshots"

W, H = 1080, 1920

# --- measured from the existing cards, do not guess these -------------------
PHONE_BOX = (168, 300, 912, 1860)      # left, top, right, bottom
PHONE_RADIUS = 32

# Phone screenshots arrive with the OS status bar on top (clock, battery -- a
# 15% battery in a marketing image is not a good look) and the Android
# navigation bar at the bottom. Neither is your app, so both are trimmed.
# Expressed as a fraction of the source height so it works for a full-res
# 1080x2340 grab and a WhatsApp-shrunk 722x1600 alike.
CROP_TOP = 0.034
CROP_BOTTOM = 0.034

HEADLINE_TOP = 125                      # top of the ink, not the baseline
# Your headlines are set in a SemiBold weight, which is not on this system.
# Poppins Bold is too heavy and Medium too light -- side by side both are
# obvious. Medium with a 1px stroke lands between them and matches: 531px
# wide against your original's 533. Do not "simplify" this to Bold.
HEADLINE_SIZE = 60
HEADLINE_STROKE = 1
HEADLINE_COLOUR = (252, 251, 252)
HEADLINE_MAX_WIDTH = 940

SUBHEAD_TOP = 203
SUBHEAD_SIZE = 30
SUBHEAD_COLOUR = (187, 193, 212)
SUBHEAD_MAX_WIDTH = 900

FONTS = Path("/usr/share/fonts/truetype/google-fonts")
SEMIBOLD = FONTS / "Poppins-Medium.ttf"   # + HEADLINE_STROKE, see above
LIGHT = FONTS / "Poppins-Light.ttf"


def fitted(font_path: Path, size: int, text: str, max_width: int, stroke: int = 0):
    """Shrink until it fits, so a long headline never runs off the card."""
    while size > 12:
        font = ImageFont.truetype(str(font_path), size)
        box = font.getbbox(text)
        if box[2] - box[0] + 2 * stroke <= max_width:
            return font
        size -= 1
    return ImageFont.truetype(str(font_path), 12)


def draw_centred(draw: ImageDraw.ImageDraw, text: str, font, top: int, colour, stroke: int = 0) -> None:
    """Place text by the TOP OF ITS INK, which is what the measurements are."""
    box = font.getbbox(text)
    width = box[2] - box[0] + 2 * stroke
    x = (W - width) // 2 - box[0] + stroke
    draw.text((x, top - box[1]), text, font=font, fill=colour,
              stroke_width=stroke, stroke_fill=colour)


def rounded(img: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius, fill=255)
    img.putalpha(mask)
    return img


def build(shot_path: Path, headline: str, subhead: str,
          crop_top: float = CROP_TOP, crop_bottom: float = CROP_BOTTOM) -> Image.Image:
    if not TEMPLATE.exists():
        raise SystemExit("Background missing - run: python tools/fit_background.py")

    card = Image.open(TEMPLATE).convert("RGB")
    left, top, right, bottom = PHONE_BOX
    box_w, box_h = right - left, bottom - top

    shot = Image.open(shot_path).convert("RGB")

    top_px = round(shot.height * crop_top)
    bot_px = round(shot.height * crop_bottom)
    if top_px + bot_px < shot.height - 50:
        shot = shot.crop((0, top_px, shot.width, shot.height - bot_px))

    # Scale to the box width. A taller screenshot loses its bottom edge rather
    # than being squashed - never distort the UI.
    scale = box_w / shot.width
    shot = shot.resize((box_w, max(1, round(shot.height * scale))), Image.LANCZOS)
    if shot.height > box_h:
        shot = shot.crop((0, 0, box_w, box_h))

    card.paste(rounded(shot, PHONE_RADIUS), (left, top), rounded(shot.copy(), PHONE_RADIUS))

    draw = ImageDraw.Draw(card)
    if headline:
        draw_centred(draw, headline,
                     fitted(SEMIBOLD, HEADLINE_SIZE, headline, HEADLINE_MAX_WIDTH, HEADLINE_STROKE),
                     HEADLINE_TOP, HEADLINE_COLOUR, HEADLINE_STROKE)
    if subhead:
        draw_centred(draw, subhead, fitted(LIGHT, SUBHEAD_SIZE, subhead, SUBHEAD_MAX_WIDTH),
                     SUBHEAD_TOP, SUBHEAD_COLOUR)
    return card


def main() -> int:
    ap = argparse.ArgumentParser(description="Build a PulseSoul store card from a phone screenshot.")
    ap.add_argument("screenshot")
    ap.add_argument("headline")
    ap.add_argument("subhead")
    ap.add_argument("name", help="output stem, e.g. pulsesoul_20")
    ap.add_argument("--out", default=None, help="output directory (default assets/screenshots)")
    ap.add_argument("--crop-top", type=float, default=CROP_TOP,
                    help="fraction of height to trim off the top (status bar)")
    ap.add_argument("--crop-bottom", type=float, default=CROP_BOTTOM,
                    help="fraction of height to trim off the bottom (nav bar)")
    args = ap.parse_args()

    out_dir = Path(args.out) if args.out else OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"{args.name}.png"
    build(Path(args.screenshot), args.headline, args.subhead,
          args.crop_top, args.crop_bottom).save(dst)
    print(f"wrote {dst}")
    print("now run: python tools/render_images.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
