"""
Builds the festival creative as a product advertisement.

    python tools/make_festival_ad.py            # every festival with a chat
    python tools/make_festival_ad.py diwali     # one

The brief was Apple / Samsung. What that means in practice, and what this file
does, is a short list of disciplines rather than effects:

    a near-black ground with ONE pool of festival-coloured light
    the greeting in a light weight, large, with room around it
    the device rendered as an object: bezel, rim light, contact shadow,
    a faint reflection on the floor
    a footer that whispers -- small icon, the name, a hairline, the store

What is NOT here is as deliberate as what is. No diyas, no rangoli, no
fireworks, no flags, no gradient washes over the whole frame, no bold
headlines. Restraint is the premium signal. Ornament drawn in code is what
made earlier attempts look cheap, and it has been rejected here before.

Per-festival colour lives in content/festivals.json under "palette":
[ground, light]. Everything else is shared, so the set reads as one campaign.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GEN = ROOT / "assets" / "generated"
OUT_DIR = ROOT / "assets" / "screenshots"
FESTIVALS = ROOT / "content" / "festivals.json"
ICON = ROOT / "assets" / "brand" / "icon.png"

FONTS = Path("/usr/share/fonts/truetype/google-fonts")
LIGHT = FONTS / "Poppins-Light.ttf"
REGULAR = FONTS / "Poppins-Regular.ttf"

W, H = 1080, 1350

# The device. Sizes are the screen; the bezel is drawn around it.
SCREEN_W = 560
SCREEN_ROWS = 1250           # how many rows of the 2264-tall render to show
SCREEN_TOP = 420
BEZEL = 14
DEVICE_RADIUS = 78
SCREEN_RADIUS = DEVICE_RADIUS - BEZEL

DEFAULT_PALETTE = ["#0A0A0C", "#E0A63A"]

INK = (246, 244, 240)
INK_SOFT = (168, 163, 156)
INK_FAINT = (110, 106, 100)


def hex_rgb(h: str) -> np.ndarray:
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


def ground(base_hex: str, light_hex: str) -> Image.Image:
    """Near-black, with one soft pool of light behind where the device sits,
    and a fainter echo low on the frame so the foot is not dead."""
    base, light = hex_rgb(base_hex), hex_rgb(light_hex)
    y, x = np.mgrid[0:H, 0:W].astype(float)

    def pool(cx, cy, rx, ry, power, strength):
        d = np.sqrt(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2)
        return np.clip(1 - d, 0, 1) ** power * strength

    m = pool(W / 2, SCREEN_TOP + 300, 820, 760, 1.7, 0.72)
    m += pool(W / 2, H + 40, 900, 420, 2.0, 0.22)
    m = np.clip(m, 0, 1)[..., None]

    img = base[None, None, :] * (1 - m) + light[None, None, :] * m
    # Very fine grain, so large flat areas do not band on a phone screen.
    rng = np.random.default_rng(7)
    img = img + rng.normal(0, 1.1, img.shape)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius, fill=255)
    return m


def wrap(text: str, path: Path, size: int, max_width: int) -> list[str]:
    font = ImageFont.truetype(str(path), size)
    words, lines, line = text.split(), [], ""
    for word in words:
        trial = f"{line} {word}".strip()
        if font.getlength(trial) <= max_width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def text_centred(draw: ImageDraw.ImageDraw, text: str, font, top: int, fill, tracking: float = 0.0) -> None:
    """Draw centred, by the top of the ink, with optional letter-spacing."""
    if tracking:
        widths = [font.getlength(ch) for ch in text]
        total = sum(widths) + tracking * (len(text) - 1)
        x = (W - total) / 2
        for ch, w in zip(text, widths):
            draw.text((x, top), ch, font=font, fill=fill)
            x += w + tracking
        return
    box = font.getbbox(text)
    draw.text(((W - (box[2] - box[0])) / 2 - box[0], top - box[1]), text, font=font, fill=fill)


def device(screen: Image.Image, light_hex: str) -> Image.Image:
    """The phone as an object: bezel, a hairline rim that catches the light,
    a soft inner edge on the glass. Returns RGBA at device size."""
    dw = SCREEN_W + 2 * BEZEL
    dh = screen.height + 2 * BEZEL
    dev = Image.new("RGBA", (dw, dh), (0, 0, 0, 0))

    # Body: graphite, very slightly lighter at the top-left where the light is.
    body_px = np.full((dh, dw, 3), (22, 22, 25), dtype=float)
    yy, xx = np.mgrid[0:dh, 0:dw].astype(float)
    sheen = np.clip(1 - np.sqrt(((xx - dw * 0.2) / dw) ** 2 + ((yy - dh * 0.1) / dh) ** 2) / 0.9, 0, 1) ** 2
    body_px += sheen[..., None] * 18
    body = Image.fromarray(np.clip(body_px, 0, 255).astype(np.uint8), "RGB")
    dev.paste(body, (0, 0), rounded_mask((dw, dh), DEVICE_RADIUS))

    dev.paste(screen, (BEZEL, BEZEL), rounded_mask(screen.size, SCREEN_RADIUS))

    d = ImageDraw.Draw(dev)
    light = tuple(int(v) for v in hex_rgb(light_hex))
    # Rim: one pixel of the festival light so the edge reads as metal catching
    # a lamp rather than a stroke, then a fainter white line inside it.
    d.rounded_rectangle([0, 0, dw - 1, dh - 1], DEVICE_RADIUS, outline=(*light, 110), width=1)
    d.rounded_rectangle([1, 1, dw - 2, dh - 2], DEVICE_RADIUS - 1, outline=(255, 255, 255, 34), width=1)
    d.rounded_rectangle([BEZEL, BEZEL, BEZEL + SCREEN_W - 1, BEZEL + screen.height - 1],
                        SCREEN_RADIUS, outline=(255, 255, 255, 22), width=1)
    return dev


def build(key: str, greeting: dict) -> Image.Image:
    palette = greeting.get("palette") or DEFAULT_PALETTE
    base_hex, light_hex = palette[0], palette[-1]
    card = ground(base_hex, light_hex).convert("RGBA")

    # ---- the greeting: light weight, big, and left to breathe -----------------
    draw = ImageDraw.Draw(card)
    title = greeting["card_title"]
    size = 92
    lines = wrap(title, LIGHT, size, 900)
    if len(lines) > 1:
        size = 78
        lines = wrap(title, LIGHT, size, 900)
    y = 132
    for line in lines:
        text_centred(draw, line, ImageFont.truetype(str(LIGHT), size), y, INK)
        y += size + 8
    y += 22
    for line in wrap(greeting["card_line"], LIGHT, 34, 800):
        text_centred(draw, line, ImageFont.truetype(str(LIGHT), 34), y, INK_SOFT)
        y += 46

    # ---- the device ---------------------------------------------------------
    screen_path = GEN / f"festival_{key}.png"
    if not screen_path.exists():
        raise SystemExit(f"{screen_path} missing - run: python tools/make_festival_chat.py {key}")
    screen = Image.open(screen_path).convert("RGB")
    screen = screen.crop((0, 0, screen.width, min(SCREEN_ROWS, screen.height)))
    screen = screen.resize((SCREEN_W, round(screen.height * SCREEN_W / screen.width)), Image.LANCZOS)
    dev = device(screen, light_hex)
    dx = (W - dev.width) // 2
    dy = SCREEN_TOP - BEZEL

    # Shadow: a wide soft one, then a tight dark one right under the body.
    for inset, dyoff, alpha, blur in ((6, 34, 200, 46), (2, 8, 170, 14)):
        shadow = Image.new("RGBA", card.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(
            [dx + inset, dy + dyoff, dx + dev.width - inset, dy + dev.height + dyoff],
            DEVICE_RADIUS, fill=(0, 0, 0, alpha))
        card = Image.alpha_composite(card, shadow.filter(ImageFilter.GaussianBlur(blur)))

    # Floor reflection: the bottom of the device, flipped, faded out fast.
    refl_h = 120
    strip = dev.crop((0, dev.height - refl_h, dev.width, dev.height)).transpose(Image.FLIP_TOP_BOTTOM)
    fade = np.linspace(0.16, 0.0, refl_h)[:, None] * 255
    fade = np.repeat(fade, dev.width, axis=1)
    alpha = np.minimum(np.array(strip.getchannel("A"), dtype=float), fade).astype(np.uint8)
    strip.putalpha(Image.fromarray(alpha, "L"))
    card.paste(strip, (dx, dy + dev.height + 6), strip)

    card.paste(dev, (dx, dy), dev)

    # ---- the footer: whisper, not shout ---------------------------------------
    draw = ImageDraw.Draw(card)
    name_font = ImageFont.truetype(str(REGULAR), 40)
    store_font = ImageFont.truetype(str(LIGHT), 24)
    foot = H - 128
    icon_sz, gap = 64, 20
    block = icon_sz + gap + name_font.getlength("PulseSoul")
    x = (W - block) / 2
    if ICON.exists():
        icon = Image.open(ICON).convert("RGB").resize((icon_sz, icon_sz), Image.LANCZOS)
        card.paste(icon, (round(x), foot - icon_sz // 2), rounded_mask((icon_sz, icon_sz), 18))
    draw.text((x + icon_sz + gap, foot - 26), "PulseSoul", font=name_font, fill=INK)
    draw.line([(W // 2 - 60, foot + 44), (W // 2 + 60, foot + 44)], fill=(*INK_FAINT, 255), width=1)
    text_centred(draw, "FREE ON GOOGLE PLAY", store_font, foot + 62, INK_SOFT, tracking=4.5)
    return card.convert("RGB")


def main() -> int:
    data = json.loads(FESTIVALS.read_text(encoding="utf-8"))
    greetings = data["greetings"]
    wanted = sys.argv[1:] or [k for k, g in greetings.items() if g.get("chat")]
    unknown = [k for k in wanted if k not in greetings]
    if unknown:
        print(f"unknown festival(s): {', '.join(unknown)}")
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for key in wanted:
        card = build(key, greetings[key])
        path = OUT_DIR / f"{greetings[key]['image']}.png"
        card.save(path)
        print(f"  {key:14} -> {path.relative_to(ROOT)}")
    print(f"\n{len(wanted)} ad(s). next: python tools/render_images.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
