"""
The closing frame of the CareShield film, in both deliverable ratios.

    python tools/make_endcard.py

Writes assets/film/endcard_16x9.png (1920x1080) and endcard_9x16.png (1080x1920).

Same discipline as the festival ads: a near-black ground, ONE pool of warm
light, the device rendered as an object, and type that whispers. Nothing is
drawn that pretends to be part of the product -- the phone screen is the real
CareShield render from assets/generated, not an illustration of one.

The tagline is fixed copy and the footer line is deliberately plain. No
health claim, no emergency claim: CareShield notices a quiet phone and nudges
the family you chose, and the film must not imply anything larger.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCREEN = ROOT / "assets" / "generated" / "careshield_liquid.png"
ICON = ROOT / "assets" / "brand" / "icon.png"
OUT = ROOT / "assets" / "film"

FONTS = Path("/usr/share/fonts/truetype/google-fonts")
LIGHT = FONTS / "Poppins-Light.ttf"
REGULAR = FONTS / "Poppins-Regular.ttf"
MEDIUM = FONTS / "Poppins-Medium.ttf"

GROUND = "#08080A"
GLOW = "#E0A63A"

INK = (246, 244, 240)
INK_SOFT = (170, 165, 158)
INK_FAINT = (108, 104, 99)

TAGLINE = "Because being there starts with knowing."
BEZEL = 12
RADIUS = 62


def hex_rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


def ground(w, h, cx, cy, rx, ry):
    """Near-black with one soft pool of warm light behind the device."""
    base, light = hex_rgb(GROUND), hex_rgb(GLOW)
    y, x = np.mgrid[0:h, 0:w].astype(float)
    d = np.sqrt(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2)
    m = (np.clip(1 - d, 0, 1) ** 1.8 * 0.55)[..., None]
    img = base[None, None, :] * (1 - m) + light[None, None, :] * m
    rng = np.random.default_rng(11)                      # grain: stops banding
    img = img + rng.normal(0, 1.1, img.shape)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def rounded(size, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius, fill=255)
    return m


def device(screen_w, rows):
    """The phone as an object: body, rim light, the real screen inside."""
    src = Image.open(SCREEN).convert("RGB")
    src = src.crop((0, 0, src.width, min(rows, src.height)))
    screen = src.resize((screen_w, round(src.height * screen_w / src.width)), Image.LANCZOS)

    dw, dh = screen_w + 2 * BEZEL, screen.height + 2 * BEZEL
    dev = Image.new("RGBA", (dw, dh), (0, 0, 0, 0))

    body = np.full((dh, dw, 3), (23, 23, 26), dtype=float)
    yy, xx = np.mgrid[0:dh, 0:dw].astype(float)
    sheen = np.clip(1 - np.sqrt(((xx - dw * .25) / dw) ** 2 + ((yy - dh * .08) / dh) ** 2) / .9, 0, 1) ** 2
    body += sheen[..., None] * 20
    dev.paste(Image.fromarray(np.clip(body, 0, 255).astype(np.uint8), "RGB"), (0, 0), rounded((dw, dh), RADIUS))
    dev.paste(screen, (BEZEL, BEZEL), rounded(screen.size, RADIUS - BEZEL))

    d = ImageDraw.Draw(dev)
    glow = tuple(int(v) for v in hex_rgb(GLOW))
    d.rounded_rectangle([0, 0, dw - 1, dh - 1], RADIUS, outline=(*glow, 120), width=1)
    d.rounded_rectangle([1, 1, dw - 2, dh - 2], RADIUS - 1, outline=(255, 255, 255, 38), width=1)
    return dev


def place_device(card, dev, x, y):
    """Shadow, floor reflection, then the device itself."""
    for inset, dy, alpha, blur in ((6, 30, 190, 44), (2, 8, 165, 13)):
        sh = Image.new("RGBA", card.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle(
            [x + inset, y + dy, x + dev.width - inset, y + dev.height + dy], RADIUS, fill=(0, 0, 0, alpha))
        card = Image.alpha_composite(card, sh.filter(ImageFilter.GaussianBlur(blur)))

    rh = min(110, dev.height)
    strip = dev.crop((0, dev.height - rh, dev.width, dev.height)).transpose(Image.FLIP_TOP_BOTTOM)
    strip = strip.filter(ImageFilter.GaussianBlur(3.2))
    fade = np.repeat(np.linspace(0.11, 0.0, rh)[:, None] * 255, dev.width, axis=1)
    strip.putalpha(Image.fromarray(np.minimum(np.array(strip.getchannel("A"), float), fade).astype(np.uint8), "L"))
    card.paste(strip, (x, y + dev.height + 5), strip)

    card.paste(dev, (x, y), dev)
    return card


def tracked(draw, text, font, x, y, fill, spacing):
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch) + spacing


def tracked_width(text, font, spacing):
    return sum(font.getlength(c) for c in text) + spacing * (len(text) - 1)


def wrap(text, font, width):
    words, lines, line = text.split(), [], ""
    for w in words:
        t = f"{line} {w}".strip()
        if font.getlength(t) <= width or not line:
            line = t
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def lockup(card, x, y, scale=1.0, centre=None):
    """Icon + PulseSoul + hairline + CARESHIELD + tagline + store line.

    Returns the y below the block. If `centre` is given the block is centred
    on that x instead of left-aligned at x.
    """
    d = ImageDraw.Draw(card)
    s = lambda v: int(v * scale)  # noqa: E731

    name_f = ImageFont.truetype(str(REGULAR), s(58))
    feat_f = ImageFont.truetype(str(MEDIUM), s(24))
    tag_f = ImageFont.truetype(str(LIGHT), s(44))
    store_f = ImageFont.truetype(str(LIGHT), s(22))

    icon_sz, gap = s(72), s(22)
    name_w = name_f.getlength("PulseSoul")
    block_w = icon_sz + gap + name_w
    bx = centre - block_w / 2 if centre is not None else x

    icon = Image.open(ICON).convert("RGB").resize((icon_sz, icon_sz), Image.LANCZOS)
    card.paste(icon, (int(bx), y), rounded((icon_sz, icon_sz), s(20)))
    d.text((bx + icon_sz + gap, y + s(6)), "PulseSoul", font=name_f, fill=INK)
    y += icon_sz + s(34)

    fw = tracked_width("CARESHIELD", feat_f, s(6))
    fx = centre - fw / 2 if centre is not None else x
    tracked(d, "CARESHIELD", feat_f, fx, y, tuple(int(v) for v in hex_rgb(GLOW)), s(6))
    y += s(52)

    line_w = s(90)
    lx = centre - line_w / 2 if centre is not None else x
    d.line([(lx, y), (lx + line_w, y)], fill=(*INK_FAINT, 255), width=1)
    y += s(40)

    for ln in wrap(TAGLINE, tag_f, s(760)):
        tx = centre - tag_f.getlength(ln) / 2 if centre is not None else x
        d.text((tx, y), ln, font=tag_f, fill=INK_SOFT)
        y += s(62)

    y += s(30)
    sw = tracked_width("FREE ON GOOGLE PLAY", store_f, s(4))
    sx = centre - sw / 2 if centre is not None else x
    tracked(d, "FREE ON GOOGLE PLAY", store_f, sx, y, INK_FAINT, s(4))
    return y + s(30)


def build_16x9():
    W, H = 1920, 1080
    card = ground(W, H, W * 0.30, H * 0.52, 1150, 980)
    dev = device(screen_w=372, rows=1600)
    card = place_device(card, dev, int(W * 0.155), (H - dev.height) // 2)
    lockup(card, x=int(W * 0.44), y=int(H * 0.30))
    return card.convert("RGB")


def build_9x16():
    W, H = 1080, 1920
    card = ground(W, H, W * 0.5, H * 0.31, 940, 1080)
    # End the crop BELOW a section, never through a row -- a sliced name
    # ("Priya · Moth") reads as a rendering fault, not a crop.
    dev = device(screen_w=600, rows=1330)
    card = place_device(card, dev, (W - dev.width) // 2, int(H * 0.108))
    lockup(card, x=0, y=int(H * 0.605), centre=W / 2)
    return card.convert("RGB")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, img in (("endcard_16x9", build_16x9()), ("endcard_9x16", build_9x16())):
        p = OUT / f"{name}.png"
        img.save(p)
        print(f"  {name:14} {img.size[0]}x{img.size[1]}  -> {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
