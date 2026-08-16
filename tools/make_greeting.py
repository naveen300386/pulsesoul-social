"""
Builds a festival greeting card: your gradient, your typeface, no artwork.

    python tools/make_greeting.py            # every greeting in festivals.json
    python tools/make_greeting.py diwali     # just one

The cards are deliberately typographic. Drawn diyas, rangoli, flags and
crackers are exactly the kind of code-generated artwork that has been rejected
before, and a hand-drawn diya next to a real app screenshot looks like a
sticker. Type on the brand background reads as the same family as the other
cards without pretending to be an illustration.

Layout is centred rather than copying the store card's top-aligned headline:
there is no phone in the frame, so anything hugging the top leaves a hole.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.make_card import (  # noqa: E402
    FONTS, LIGHT, SEMIBOLD, TEMPLATE, W, H, fitted, draw_centred,
)

OUT_DIR = ROOT / "assets" / "screenshots"
FESTIVALS = ROOT / "content" / "festivals.json"

BOLD = FONTS / "Poppins-Bold.ttf"

# Greetings are built 4:5, not 9:16 like the store cards. There is no phone in
# the frame, so the tall shape left a third of the card empty and shrank the
# type to nothing once Instagram letterboxed it into a square. 1080x1350 is
# Instagram's largest feed shape and crops well everywhere else.
CARD_H = 1350
GREETING_SIZE = 116          # the festival name itself
GREETING_MAX = 900
LINE_SIZE = 46               # the warm line under it
LINE_MAX = 920
GAP = 54                     # between the two blocks
CENTRE = 690                 # the whole block is centred on this, not top-aligned
MARK_SIZE = 34               # "PulseSoul" at the foot
MARK_TOP = 1190

GREETING_COLOUR = (252, 251, 252)
LINE_COLOUR = (206, 201, 219)
MARK_COLOUR = (168, 160, 188)


def wrap(text: str, font_path: Path, size: int, max_width: int) -> list[str]:
    """Break into as few lines as will fit at this size."""
    font = ImageFont.truetype(str(font_path), size)
    words, lines, line = text.split(), [], ""
    for word in words:
        trial = f"{line} {word}".strip()
        box = font.getbbox(trial)
        if box[2] - box[0] <= max_width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def build(greeting: str, line: str) -> Image.Image:
    if not TEMPLATE.exists():
        raise SystemExit("Background missing - run: python tools/fit_background.py")
    full = Image.open(TEMPLATE).convert("RGB")
    top = (full.height - CARD_H) // 2          # keep the middle of the gradient
    card = full.crop((0, top, full.width, top + CARD_H))
    draw = ImageDraw.Draw(card)

    size = GREETING_SIZE
    g_lines = wrap(greeting, BOLD, size, GREETING_MAX)
    if len(g_lines) > 2:                      # a three-line title looks shouty
        size = 88
        g_lines = wrap(greeting, BOLD, size, GREETING_MAX)
    body = wrap(line, LIGHT, LINE_SIZE, LINE_MAX)

    # Centre the whole block. Top-aligning it left two thirds of the card empty
    # and put the text where a square crop cuts hardest.
    g_step, b_step = size + 18, LINE_SIZE + 16
    block = len(g_lines) * g_step + (GAP if body else 0) + len(body) * b_step
    y = CENTRE - block // 2

    for text in g_lines:
        draw_centred(draw, text, ImageFont.truetype(str(BOLD), size), y, GREETING_COLOUR)
        y += g_step
    y += GAP
    for text in body:
        draw_centred(draw, text, ImageFont.truetype(str(LIGHT), LINE_SIZE), y, LINE_COLOUR)
        y += b_step

    draw_centred(draw, "PulseSoul", fitted(SEMIBOLD, MARK_SIZE, "PulseSoul", 400),
                 MARK_TOP, MARK_COLOUR)
    return card


def main() -> int:
    if not FESTIVALS.exists():
        raise SystemExit(f"{FESTIVALS} is missing")
    data = json.loads(FESTIVALS.read_text(encoding="utf-8"))
    wanted = sys.argv[1:] or list(data["greetings"])

    unknown = [n for n in wanted if n not in data["greetings"]]
    if unknown:
        print(f"unknown greeting(s): {', '.join(unknown)}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name in wanted:
        g = data["greetings"][name]
        card = build(g["card_title"], g["card_line"])
        path = OUT_DIR / f"{g['image']}.png"
        card.save(path)
        print(f"  {g['image']:24} {path.stat().st_size // 1024} KB")
    print(f"\n{len(wanted)} card(s) in {OUT_DIR.relative_to(ROOT)}/")
    print("next: python tools/render_images.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
