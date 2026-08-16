"""
Builds the "influencer" creative: a person holding a phone, our app on the
phone, painted headline over the photo.

    python tools/make_selfie_ad.py              # every ad in ads.json with layout "selfie"
    python tools/make_selfie_ad.py sanity       # one

How the phone gets our screen: the photo has a blank white phone screen. We
find that white quadrilateral automatically (largest near-white blob inside
the search box given in the spec), warp a real rendered app screen onto those
four corners with a perspective transform, and lay it under a soft edge so it
sits in the glass rather than on top of it. Nothing about the person is
drawn; the only thing added to the photo is the app.

The photo is AI-generated (Gemini) at the owner's request, and captions for
these posts should say so -- Instagram labels the reference posts the same
way, and honesty here costs nothing.

Then the type: a big hand-painted-looking headline in Poppins ExtraBold-ish
(Bold + stroke), one or two words on a brush-stroke highlight, a scribble
underline, and the brand sticker bottom-left. Same shape as the reference.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ADS = ROOT / "content" / "ads.json"
GEN = ROOT / "assets" / "generated"
PHOTOS = ROOT / "assets" / "photos"
BRAND = ROOT / "assets" / "brand"
OUT_DIR = ROOT / "assets" / "screenshots"

FONTS = Path("/usr/share/fonts/truetype/google-fonts")
BOLD = FONTS / "Poppins-Bold.ttf"
MEDIUM = FONTS / "Poppins-Medium.ttf"
REGULAR = FONTS / "Poppins-Regular.ttf"

W, H = 1080, 1350


# ---------------------------------------------------------------- the phone --
def find_screen(img: Image.Image, box: tuple[int, int, int, int]) -> np.ndarray:
    """Corners (TL, TR, BR, BL) of the largest near-white blob inside box."""
    a = np.array(img.convert("RGB")).astype(int)
    white = (a[..., 0] > 225) & (a[..., 1] > 225) & (a[..., 2] > 225)
    m = np.zeros_like(white)
    x0, y0, x1, y1 = box
    m[y0:y1, x0:x1] = True
    white &= m
    lab, n = ndimage.label(white)
    if n == 0:
        raise SystemExit("no white screen found inside the search box -- adjust 'phone_box' in ads.json")
    sizes = ndimage.sum(white, lab, range(1, n + 1))
    big = lab == (np.argmax(sizes) + 1)
    ys, xs = np.nonzero(big)
    pts = np.stack([xs, ys], 1).astype(float)
    s, d = pts.sum(1), pts[:, 0] - pts[:, 1]
    return np.array([pts[s.argmin()], pts[d.argmax()], pts[s.argmax()], pts[d.argmin()]])


def perspective_coeffs(src, dst):
    """PIL wants the inverse mapping: for each output pixel, where in the source."""
    A = []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    A = np.array(A, dtype=float)
    b = np.array(src, dtype=float).reshape(8)
    return np.linalg.solve(A, b)


def put_screen_on_phone(photo: Image.Image, screen: Image.Image, corners: np.ndarray) -> Image.Image:
    """Warp the screen onto the phone. Slight inset so the glass edge shows,
    a whisper of the photo's own highlights kept on top so it reads as glass."""
    # inset the quad ~2px toward its centre so we do not paint over the bezel
    c = corners.mean(0)
    quad = corners + (c - corners) * 0.012
    tl, tr, br, bl = quad
    # target size ~ the quad's own size, keep the screen's aspect by cropping
    tw = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
    th = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))
    ratio = th / tw
    sw, sh = screen.size
    if sh / sw > ratio:                       # screen too tall: crop bottom
        screen = screen.crop((0, 0, sw, int(sw * ratio)))
    else:                                     # too wide (unlikely): crop sides
        nw = int(sh / ratio)
        screen = screen.crop(((sw - nw) // 2, 0, (sw - nw) // 2 + nw, sh))
    screen = screen.resize((tw, th), Image.LANCZOS).convert("RGBA")

    coeffs = perspective_coeffs([(0, 0), (tw, 0), (tw, th), (0, th)],
                                [tuple(tl), tuple(tr), tuple(br), tuple(bl)])
    warped = screen.transform(photo.size, Image.PERSPECTIVE, coeffs, Image.BICUBIC)

    # mask: the same quad, feathered by a pixel so the edge is not razor-sharp
    mask = Image.new("L", photo.size, 0)
    ImageDraw.Draw(mask).polygon([tuple(p) for p in quad], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(0.8))

    out = photo.convert("RGBA")
    out.paste(warped, (0, 0), mask)
    # keep 8% of the original screen's light on top: glass, not a sticker
    glass = photo.convert("RGBA").copy()
    glass.putalpha(mask.point(lambda v: int(v * 0.08)))
    out = Image.alpha_composite(out, glass)
    return out


# ------------------------------------------------------------------ the type --
def brush(draw: ImageDraw.ImageDraw, box, colour, seed=3):
    """A rough painted rectangle: a rounded box plus jittered edge blobs."""
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = box
    draw.rounded_rectangle([x0, y0, x1, y1], 18, fill=colour)
    for _ in range(14):
        x = rng.uniform(x0 + 10, x1 - 10)
        y = rng.choice([y0, y1]) + rng.uniform(-5, 5)
        r = rng.uniform(5, 10)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=colour)
    # ragged ends, like a brush lifting off
    for yy in np.linspace(y0 + 8, y1 - 8, 5):
        draw.ellipse([x0 - 6, yy - 7, x0 + 8, yy + 7], fill=colour)
        draw.ellipse([x1 - 8, yy - 7, x1 + 6, yy + 7], fill=colour)


def painted_text(canvas: Image.Image, text: str, xy, size: int, fill, stroke=(0, 0, 0), stroke_w=0, tilt=-2.0):
    """Big text on its own layer, rotated slightly, pasted on -- 'stickered on'."""
    font = ImageFont.truetype(str(BOLD), size)
    box = font.getbbox(text, stroke_width=stroke_w)
    tw, th = box[2] - box[0] + 40, box[3] - box[1] + 40
    layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((20 - box[0], 20 - box[1]), text, font=font, fill=fill,
                               stroke_width=stroke_w, stroke_fill=stroke)
    layer = layer.rotate(tilt, resample=Image.BICUBIC, expand=True)
    canvas.paste(layer, (int(xy[0]), int(xy[1])), layer)
    return layer.size


def scribble_underline(draw, x0, x1, y, colour, seed=5):
    rng = np.random.default_rng(seed)
    pts = []
    for i in range(14):
        t = i / 13
        pts.append((x0 + (x1 - x0) * t, y + rng.uniform(-4, 4) + 6 * np.sin(t * 6.3)))
    draw.line(pts, fill=colour, width=10, joint="curve")


def build(key: str, ad: dict) -> Image.Image:
    photo_path = PHOTOS / ad["photo"]
    if not photo_path.exists():
        raise SystemExit(f"{photo_path} missing")
    photo = Image.open(photo_path).convert("RGB")

    # --- the app on the phone --------------------------------------------
    screen = Image.open(GEN / f"{ad['screen']}.png").convert("RGB")
    corners = find_screen(photo, tuple(ad["phone_box"]))
    photo = put_screen_on_phone(photo, screen, corners)

    # --- fit to 4:5, cover ------------------------------------------------
    pw, ph = photo.size
    scale = max(W / pw, H / ph)
    photo = photo.resize((round(pw * scale), round(ph * scale)), Image.LANCZOS)
    fx = ad.get("focus_x", 0.5)
    left = int((photo.width - W) * fx)
    top = int((photo.height - H) * ad.get("focus_y", 0.35))
    canvas = photo.crop((left, top, left + W, top + H)).convert("RGBA")

    # a touch of darkening where the headline sits, so white type reads
    shade = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    sd.rectangle([0, 0, W, 560], fill=(0, 0, 0, 70))
    shade = shade.filter(ImageFilter.GaussianBlur(90))
    canvas = Image.alpha_composite(canvas, shade)

    # --- headline: three painted lines, second on a brush stroke ----------
    accent = tuple(int(ad.get("accent", "#F0578F")[i:i + 2], 16) for i in (1, 3, 5))
    lines = ad["headline_lines"]                       # e.g. ["THIS APP", "SAVED MY", "SANITY"]
    y = ad.get('headline_top', 56)
    sizes = [ad.get('headline_size', 96)] * 3
    for i, (line, size) in enumerate(zip(lines, sizes)):
        if i == 1:
            font = ImageFont.truetype(str(BOLD), size)
            tw = font.getlength(line)
            d = ImageDraw.Draw(canvas)
            brush(d, (48, y + 4, 48 + tw + 56, y + size + 4), accent)
            painted_text(canvas, line, (66, y - 6), size, (255, 255, 255), stroke_w=0, tilt=-2.0)
        else:
            painted_text(canvas, line, (54, y), size, (255, 255, 255), stroke=(20, 20, 20), stroke_w=3, tilt=-2.0)
        y += size + 10

    # --- the highlighter line ----------------------------------------------
    d = ImageDraw.Draw(canvas)
    sub = ad.get("sub", "")
    if sub:
        font = ImageFont.truetype(str(MEDIUM), 46)
        tw = font.getlength(sub)
        sy = 930
        brush(d, (44, sy - 10, 44 + tw + 60, sy + 62), accent, seed=9)
        d.text((72, sy), sub, font=font, fill=(255, 255, 255))
        scribble_underline(d, 72, 72 + tw, sy + 76, (255, 255, 255))

    # --- the brand sticker ---------------------------------------------------
    sx, sy = 44, H - 190
    stick = Image.new("RGBA", (560, 150), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stick)
    brush(sd, (10, 10, 540, 130), (255, 255, 255), seed=11)
    icon = Image.open(BRAND / "icon.png").convert("RGBA").resize((72, 72), Image.LANCZOS)
    m = Image.new("L", icon.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, 71, 71], 20, fill=255)
    stick.paste(icon, (34, 34), m)
    sd.text((122, 26), "PulseSoul", font=ImageFont.truetype(str(BOLD), 44), fill=accent)
    sd.text((124, 82), ad.get("tagline", "Never Miss What Matters."), font=ImageFont.truetype(str(REGULAR), 26), fill=(40, 34, 40))
    stick = stick.rotate(-3, resample=Image.BICUBIC, expand=True)
    canvas.paste(stick, (sx, sy), stick)

    return canvas.convert("RGB")


def main() -> int:
    data = json.loads(ADS.read_text(encoding="utf-8"))
    ads = {k: v for k, v in data["ads"].items() if v.get("layout") == "selfie"}
    wanted = sys.argv[1:] or list(ads)
    for key in wanted:
        if key not in ads:
            print(f"unknown selfie ad: {key}")
            return 1
        img = build(key, ads[key])
        path = OUT_DIR / f"{ads[key]['image']}.png"
        img.save(path)
        print(f"  {key:12} -> {path.relative_to(ROOT)}")
    print("next: python tools/render_images.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
