"""
Assembles the 90-second CareShield film from stills, type, and the real UI.

    python tools/make_film.py 16x9      # 1920x1080 master
    python tools/make_film.py 9x16      # 1080x1920 cutdown
    python tools/make_film.py frames    # QC: writes 14 spread frames as JPGs

This is a real edit, not a slideshow: every photo moves (slow eased push-ins
and drifts), every shot is graded (warmth, exposure, vignette), live 35mm-ish
grain sits over the whole frame, and the words fade in and out on the
voiceover's own timecodes. The form is the photo-essay commercial -- stills
presented editorially on a near-black ground -- because that is what the
material honestly is. Nothing pretends to be footage.

Product honesty, same rules as everywhere else in this repo:
  * The app UI shown is the real CareShield render (assets/generated/
    careshield_liquid.png), never a mock. Its own words tell the mechanism:
    "Phone answered on its own - nobody was nudged" / "Family nudged once".
  * No crisis is depicted or implied. Nothing red, nothing flashing.
  * The photos are the AI set the owner generated for the ad campaign
    (assets/photos/ai_*.png); the closing caption says so.

Renders frames in Python and pipes them straight to ffmpeg/libx264. ~4 min
per ratio on this container.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PHOTOS = ROOT / "assets" / "photos"
GEN = ROOT / "assets" / "generated"
FILM = ROOT / "assets" / "film"

FONTS = Path("/usr/share/fonts/truetype/google-fonts")
LIGHT = str(FONTS / "Poppins-Light.ttf")
REGULAR = str(FONTS / "Poppins-Regular.ttf")
MEDIUM = str(FONTS / "Poppins-Medium.ttf")

FPS = 24
DUR = 90.0

GOLD = (224, 166, 58)
INK = (238, 235, 229)
SOFT = (166, 162, 155)
FAINT = (118, 114, 108)


# ---------------------------------------------------------------- helpers --
def ease(t: float) -> float:
    """Smoothstep: gentle in and out, no mechanical linear moves."""
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def load(path: Path, box=None) -> np.ndarray:
    im = Image.open(path).convert("RGB")
    if box:
        im = im.crop(box)
    return np.asarray(im, dtype=np.float32)


def ground(w: int, h: int) -> np.ndarray:
    """The film's stage: near-black with one faint warm pool, fine grain-free
    (live grain is added per frame). Matches the end card's world."""
    base = np.array([12, 12, 15], dtype=np.float32)
    warm = np.array([46, 36, 20], dtype=np.float32)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((x - w * 0.38) / (w * 0.75)) ** 2 + ((y - h * 0.42) / (h * 0.75)) ** 2)
    m = np.clip(1 - d, 0, 1)[..., None] ** 2
    return base[None, None, :] * (1 - m) + (base + warm)[None, None, :] * m


def grade(px: np.ndarray, warmth: float = 0.0, exposure: float = 1.0,
          contrast: float = 1.0, desat: float = 0.0) -> np.ndarray:
    """warmth >0 golden, <0 blue. Applied in float, clipped once."""
    out = px * exposure
    if warmth:
        out = out * np.array([1 + 0.16 * warmth, 1 + 0.03 * warmth, 1 - 0.16 * warmth],
                             dtype=np.float32)[None, None, :]
    if contrast != 1.0:
        out = (out - 118.0) * contrast + 118.0
    if desat:
        g = out.mean(axis=2, keepdims=True)
        out = out * (1 - desat) + g * desat
    return out


def vignette(shape, strength=0.35) -> np.ndarray:
    h, w = shape[:2]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((x / w) - 0.5) ** 2 + ((y / h) - 0.5) ** 2) / 0.72
    return (1 - np.clip(d, 0, 1) ** 2.2 * strength)[..., None]


class Type:
    """A timed line of text, rendered once, faded per frame."""

    def __init__(self, text, t0, t1, size=54, font=LIGHT, colour=INK,
                 pos=(0.5, 0.5), align="center", tracking=0, max_w=0.8):
        self.text, self.t0, self.t1 = text, t0, t1
        self.size, self.font, self.colour = size, font, colour
        self.pos, self.align, self.tracking, self.max_w = pos, align, tracking, max_w
        self._layer = None

    def layer(self, W, H):
        if self._layer is not None:
            return self._layer
        font = ImageFont.truetype(self.font, self.size)
        lines = []
        for para in self.text.split("\n"):
            words, line = para.split(), ""
            for w in words:
                trial = f"{line} {w}".strip()
                if font.getlength(trial) + self.tracking * len(trial) <= W * self.max_w or not line:
                    line = trial
                else:
                    lines.append(line)
                    line = w
            lines.append(line)
        lh = int(self.size * 1.42)
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        total_h = lh * len(lines)
        y = int(self.pos[1] * H - total_h / 2)
        for ln in lines:
            if self.tracking:
                tw = sum(font.getlength(c) for c in ln) + self.tracking * (len(ln) - 1)
            else:
                tw = font.getlength(ln)
            if self.align == "center":
                x = self.pos[0] * W - tw / 2
            elif self.align == "left":
                x = self.pos[0] * W
            else:
                x = self.pos[0] * W - tw
            if self.tracking:
                cx = x
                for c in ln:
                    d.text((cx, y), c, font=font, fill=(*self.colour, 255))
                    cx += font.getlength(c) + self.tracking
            else:
                d.text((x, y), ln, font=font, fill=(*self.colour, 255))
            y += lh
        self._layer = np.asarray(img, dtype=np.float32)
        return self._layer

    def alpha(self, t):
        if t < self.t0 or t > self.t1:
            return 0.0
        fin = min(1.0, (t - self.t0) / 0.7)
        fout = min(1.0, (self.t1 - t) / 0.7)
        return ease(min(fin, fout))


class PhotoShot:
    """A still presented editorially: inset on the ground, slowly moving.

    move: (cx0, cy0, z0) -> (cx1, cy1, z1), centres in source fractions,
    zoom z = how much of the *fitting* crop is shown (1 = all, .9 = push-in).
    """

    def __init__(self, t0, t1, src, box, side, move, warmth=0.0, exposure=1.0,
                 contrast=1.03, desat=0.0, night=False):
        self.t0, self.t1 = t0, t1
        self.px = load(src, box)
        self.side = side          # "left" | "right" | "centre"
        self.move = move
        self.warmth, self.exposure, self.contrast, self.desat = warmth, exposure, contrast, desat
        self.night = night
        self._vig = None

    def frame(self, t, W, H, stage):
        # -- where the photo sits ------------------------------------------
        if H > W:                                # vertical: width-driven, upper
            pw = W - 2 * int(W * 0.065)
            ph = int(pw / 0.78)
            px0 = (W - pw) // 2
            py0 = int(H * 0.065)
        else:                                    # wide: height-driven, one side
            margin = int(H * 0.085)
            ph = H - 2 * margin
            pw = int(ph * 0.78)
            if self.side == "centre":
                px0 = (W - pw) // 2
            elif self.side == "left":
                px0 = int(W * 0.075)
            else:
                px0 = W - pw - int(W * 0.075)
            py0 = margin

        # -- eased crop of the source --------------------------------------
        k = ease((t - self.t0) / (self.t1 - self.t0))
        cx = self.move[0][0] + (self.move[1][0] - self.move[0][0]) * k
        cy = self.move[0][1] + (self.move[1][1] - self.move[0][1]) * k
        z = self.move[0][2] + (self.move[1][2] - self.move[0][2]) * k

        sh, sw = self.px.shape[:2]
        target = pw / ph
        fit_w, fit_h = (sw, sw / target) if sw / sh <= target else (sh * target, sh)
        cw, ch = fit_w * z, fit_h * z
        x0 = min(max(cx * sw - cw / 2, 0), sw - cw)
        y0 = min(max(cy * sh - ch / 2, 0), sh - ch)
        crop = self.px[int(y0):int(y0 + ch), int(x0):int(x0 + cw)]

        img = Image.fromarray(crop.astype(np.uint8)).resize((pw, ph), Image.LANCZOS)
        px = grade(np.asarray(img, dtype=np.float32), self.warmth, self.exposure,
                   self.contrast, self.desat)
        if self._vig is None or self._vig.shape[:2] != (ph, pw):
            self._vig = vignette((ph, pw), 0.42 if self.night else 0.30)
        px = px * self._vig

        stage[py0:py0 + ph, px0:px0 + pw] = np.clip(px, 0, 255)
        return stage


class FullBleed:
    """The UI macro and the end card: fills the frame, slow move, no inset."""

    def __init__(self, t0, t1, src, move, warmth=0.0, exposure=1.0, source_px=None):
        self.t0, self.t1 = t0, t1
        self.px = source_px if source_px is not None else load(src)
        self.move = move
        self.warmth, self.exposure = warmth, exposure

    def frame(self, t, W, H, stage):
        k = ease((t - self.t0) / (self.t1 - self.t0))
        cx = self.move[0][0] + (self.move[1][0] - self.move[0][0]) * k
        cy = self.move[0][1] + (self.move[1][1] - self.move[0][1]) * k
        z = self.move[0][2] + (self.move[1][2] - self.move[0][2]) * k

        z = min(z, 1.0)
        sh, sw = self.px.shape[:2]
        target = W / H
        fit_w, fit_h = (sw, sw / target) if sw / sh <= target else (sh * target, sh)
        cw, ch = fit_w * z, fit_h * z
        x0 = min(max(cx * sw - cw / 2, 0), sw - cw)
        y0 = min(max(cy * sh - ch / 2, 0), sh - ch)
        crop = self.px[int(y0):int(y0 + ch), int(x0):int(x0 + cw)]
        img = Image.fromarray(crop.astype(np.uint8)).resize((W, H), Image.LANCZOS)
        px = grade(np.asarray(img, dtype=np.float32), self.warmth, self.exposure)
        return np.clip(px, 0, 255)


class ScreenScroll:
    """The real CareShield screen, readable, inside a rounded panel that
    slowly scrolls from the status card down to the recent check-ins.

    This replaces any temptation to macro-pan the raw PNG: a full-bleed crop
    of a 1080x2280 screen puts one cut-off word on screen at a time and reads
    as a glitch. A panel at readable scale is how app UI appears in real
    device ads.
    """

    def __init__(self, t0, t1, src):
        self.t0, self.t1 = t0, t1
        self.px = load(src)                      # 1080 x 2280
        self._cache = {}

    def frame(self, t, W, H, stage):
        if not self._cache:
            if H > W:
                pw = int(W * 0.68)
                ph = int(H * 0.62)
                py0 = int(H * 0.155)
            else:
                ph = int(H * getattr(self, "ph_frac", 0.68))
                pw = int(ph * 0.62)
                py0 = int(H * getattr(self, "py_frac", 0.245))
            px0 = (W - pw) // 2
            scale = pw / self.px.shape[1]
            win = int(ph / scale)
            mask = Image.new("L", (pw, ph), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1], int(pw * 0.055), fill=255)
            self._cache = dict(pw=pw, ph=ph, px0=px0, py0=py0, win=win,
                               mask=np.asarray(mask, dtype=np.float32)[..., None] / 255.0)
        c = self._cache
        k = ease((t - self.t0) / (self.t1 - self.t0))
        sh = self.px.shape[0]
        span = getattr(self, "span", None)   # (start_row, end_row) override
        if span:
            y0 = span[0] + (min(span[1], sh - c["win"]) - span[0]) * k
        else:
            y0 = 40 + (sh - c["win"] - 120 - 40) * k
        crop = self.px[int(y0):int(y0 + c["win"])]
        img = Image.fromarray(crop.astype(np.uint8)).resize((c["pw"], c["ph"]), Image.LANCZOS)
        panel = np.asarray(img, dtype=np.float32)

        # soft shadow, then the panel through its rounded mask, then edges
        x0, y0f = c["px0"], c["py0"]
        sh_pad = 26
        region = stage[max(0, y0f - sh_pad):y0f + c["ph"] + sh_pad,
                       max(0, x0 - sh_pad):x0 + c["pw"] + sh_pad]
        region *= 0.72                                   # cheap contact shadow
        stage[max(0, y0f - sh_pad):y0f + c["ph"] + sh_pad,
              max(0, x0 - sh_pad):x0 + c["pw"] + sh_pad] = region

        m = c["mask"]
        base = stage[y0f:y0f + c["ph"], x0:x0 + c["pw"]]
        stage[y0f:y0f + c["ph"], x0:x0 + c["pw"]] = base * (1 - m) + panel * m

        edge = Image.new("RGBA", (c["pw"], c["ph"]), (0, 0, 0, 0))
        d = ImageDraw.Draw(edge)
        d.rounded_rectangle([0, 0, c["pw"] - 1, c["ph"] - 1], int(c["pw"] * 0.055),
                            outline=(224, 166, 58, 105), width=1)
        d.rounded_rectangle([1, 1, c["pw"] - 2, c["ph"] - 2], int(c["pw"] * 0.055) - 1,
                            outline=(255, 255, 255, 30), width=1)
        e = np.asarray(edge, dtype=np.float32)
        ea = e[..., 3:4] / 255.0
        base = stage[y0f:y0f + c["ph"], x0:x0 + c["pw"]]
        stage[y0f:y0f + c["ph"], x0:x0 + c["pw"]] = base * (1 - ea) + e[..., :3] * ea
        return stage


class Black:
    """Not void: a cool, very dim pool, so the pause still feels lit."""

    def __init__(self, t0, t1, cool=True):
        self.t0, self.t1 = t0, t1
        self.cool = cool
        self._bg = None

    def frame(self, t, W, H, stage):
        if self._bg is None:
            base = np.array([7, 8, 12], dtype=np.float32)
            pool = np.array([16, 19, 34], dtype=np.float32) if self.cool else np.array([26, 21, 12], dtype=np.float32)
            y, x = np.mgrid[0:H, 0:W].astype(np.float32)
            d = np.sqrt(((x - W * 0.5) / (W * 0.7)) ** 2 + ((y - H * 0.44) / (H * 0.7)) ** 2)
            m = np.clip(1 - d, 0, 1)[..., None] ** 2
            self._bg = base[None, None, :] * (1 - m) + pool[None, None, :] * m
        return self._bg.copy()


# ---------------------------------------------------------------- timeline --
def build_timeline(W, H, vertical=False):
    side_a = "centre" if vertical else "right"
    side_b = "centre" if vertical else "left"
    tx = 0.5 if vertical else 0.075          # type x when photo sits right
    tx2 = 0.5 if vertical else 0.925         # type x when photo sits left
    al_a = "center" if vertical else "left"
    al_b = "center" if vertical else "right"
    ty = 0.82 if vertical else 0.5           # vertical: words under the photo
    big, small, tiny = (54, 30, 22) if not vertical else (48, 30, 22)

    ui = GEN / "careshield_liquid.png"       # 1080x2280 real screen
    endcard = FILM / ("endcard_9x16.png" if vertical else "endcard_16x9.png")

    shots = [
        Black(0.0, 4.0),
        # ACT 1 - her day
        PhotoShot(3.2, 12.0, PHOTOS / "ai_parents_waiting.png", (0, 60, 928, 1050),
                  side_a, ((0.46, 0.52, 1.0), (0.52, 0.46, 0.90)), warmth=0.5, exposure=1.04),
        # detail insert of the same morning: the chai table, hands, brass bowl.
        # (the kitchen photo held a blank phone to camera -- promo pose, cut.)
        PhotoShot(11.2, 20.5, PHOTOS / "ai_parents_waiting.png", (140, 620, 860, 1152),
                  side_b, ((0.42, 0.5, 0.98), (0.58, 0.52, 0.90)), warmth=0.45, exposure=1.05),
        PhotoShot(19.7, 28.5, PHOTOS / "ai_mother_alone_home.png", None,
                  side_a, ((0.5, 0.42, 0.96), (0.44, 0.38, 0.86)), warmth=0.4, exposure=1.03),
        # ACT 2 - the daughter
        PhotoShot(27.7, 40.0, PHOTOS / "ai_lady_cafe.png", (0, 60, 560, 900),
                  side_b, ((0.5, 0.42, 1.0), (0.55, 0.38, 0.88)), warmth=-0.8, exposure=0.93,
                  desat=0.15),
        # ACT 3 - the quiet: the same window, the light gone
        PhotoShot(39.2, 50.0, PHOTOS / "ai_mother_alone_home.png", None,
                  side_a, ((0.44, 0.38, 0.86), (0.5, 0.45, 0.99)), warmth=-1.1,
                  exposure=0.50, contrast=1.08, desat=0.30, night=True),
        Black(49.2, 58.0),
        # ACT 4 - the ask, told by the real screen at readable scale
        ScreenScroll(57.2, 71.5, ui),
        # ACT 5 - relief
        PhotoShot(70.7, 81.5, PHOTOS / "ai_grandmother_grandchild.png", (60, 160, 928, 1152),
                  side_b, ((0.5, 0.5, 1.0), (0.44, 0.42, 0.87)), warmth=0.5, exposure=1.05),
        # END
        FullBleed(80.7, 90.0, endcard, ((0.5, 0.5, 1.0), (0.5, 0.5, 0.965)), exposure=1.0),
    ]

    Y = ty
    cues = [
        Type("PulseSoul presents", 0.8, 3.4, size=tiny + 4, font=MEDIUM, colour=SOFT,
             pos=(0.5, 0.47), tracking=6),
        Type("Twelve Hours Quiet", 1.6, 3.8, size=big - 6, colour=INK, pos=(0.5, 0.55)),

        Type("Jaipur, 6:14 am", 4.4, 8.0, size=tiny, font=MEDIUM, colour=GOLD,
             pos=(tx if not vertical else 0.5, (Y - 0.12) if vertical else 0.36),
             align=al_a, tracking=4),
        Type("She has her own rhythm.", 5.2, 11.5, size=big, pos=(tx, Y if vertical else 0.46), align=al_a),
        Type("Her own way of doing everything.", 13.0, 19.5, size=big,
             pos=(tx2, Y if vertical else 0.46), align=al_b),
        Type("She doesn't need looking after.\nShe's said so. Often.", 21.0, 27.5, size=big,
             pos=(tx, Y if vertical else 0.44), align=al_a),

        Type("Bengaluru, 900 km away", 29.0, 33.0, size=tiny, font=MEDIUM, colour=GOLD,
             pos=(tx2 if not vertical else 0.5, (Y - 0.12) if vertical else 0.36),
             align=al_b, tracking=4),
        Type("Her daughter is busy.", 30.0, 35.0, size=big, pos=(tx2, Y if vertical else 0.46), align=al_b),
        Type("Busy isn't the same as far away.\nSome evenings it feels the same.", 35.2, 39.6,
             size=small + 6, colour=SOFT, pos=(tx2, (Y + 0.09) if vertical else 0.58), align=al_b),

        Type("That night, her phone goes quiet.", 41.0, 48.5, size=big,
             pos=(tx, Y if vertical else 0.46), align=al_a),

        Type("Evening.", 50.2, 52.6, size=big - 8, colour=SOFT, pos=(0.5, 0.47)),
        Type("Midnight.", 52.9, 55.3, size=big - 8, colour=SOFT, pos=(0.5, 0.47)),
        Type("Dawn.", 55.6, 58.4, size=big - 8, colour=GOLD, pos=(0.5, 0.47)),
        Type("Twelve hours. Not a touch.", 56.2, 60.8, size=small + 4, colour=SOFT, pos=(0.5, 0.57)),

        Type("So CareShield asks her phone first.", 61.0, 66.0, size=big - 8,
             pos=(0.5, 0.10 if not vertical else 0.08)),
        Type("And only if the quiet continues,\nit nudges the family she chose.", 66.5, 71.2,
             size=big - 8, pos=(0.5, 0.10 if not vertical else 0.08)),

        Type("Nothing was wrong.", 72.5, 77.0, size=big, pos=(tx2, Y if vertical else 0.44), align=al_b),
        Type("She was asleep with her book.\nHer daughter simply knew.", 77.2, 81.2,
             size=small + 6, colour=SOFT, pos=(tx2, (Y + 0.09) if vertical else 0.56), align=al_b),

        Type("Characters portrayed with AI-generated imagery.", 82.0, 89.5, size=16,
             font=REGULAR, colour=(96, 93, 88), pos=(0.5, 0.965)),
    ]
    return shots, cues


# ------------------------------------------------------------------ render --
def render(W, H, out_path, qc_only=False, builder=None, dur=None, qc_times=None, qc_prefix="qc"):
    """builder/dur let other films (the SOS spot) reuse this whole engine."""
    builder = builder or build_timeline
    dur = dur or DUR
    shots, cues = builder(W, H, vertical=(H > W))
    stage0 = ground(W, H)
    total = int(dur * FPS)
    rng = np.random.default_rng(3)
    noise = rng.normal(0, 1, (H + 64, W + 64, 1)).astype(np.float32)

    proc = None
    if not qc_only:
        proc = subprocess.Popen(
            ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
             "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium",
             "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    qc_frames = {int(s * FPS) for s in (qc_times or (2, 7, 15, 24, 33, 44, 52, 57, 62, 69, 75, 79, 85, 89))}
    qc_dir = FILM / "qc"
    if qc_only:
        qc_dir.mkdir(parents=True, exist_ok=True)

    for f in range(total):
        t = f / FPS
        if qc_only and f not in qc_frames:
            continue

        active = [s for s in shots if s.t0 <= t < s.t1]
        frame = None
        for s in active:
            candidate = s.frame(t, W, H, stage0.copy())
            if frame is None:
                frame = candidate
            else:
                # dissolve: weight by how far into the NEWER shot we are
                w = ease((t - s.t0) / 0.8) if t - s.t0 < 0.8 else 1.0
                frame = frame * (1 - w) + candidate * w
        if frame is None:
            frame = stage0.copy()

        # words
        for c in cues:
            a = c.alpha(t)
            if a <= 0:
                continue
            layer = c.layer(W, H)
            al = layer[..., 3:4] / 255.0 * a
            frame = frame * (1 - al) + layer[..., :3] * al

        # live grain: one field, new offset each frame
        ox, oy = rng.integers(0, 64), rng.integers(0, 64)
        frame = frame + noise[oy:oy + H, ox:ox + W] * 2.2

        # master fades
        if t < 1.0:
            frame = frame * ease(t / 1.0)
        if t > dur - 1.2:
            frame = frame * ease((dur - t) / 1.2)

        out = np.clip(frame, 0, 255).astype(np.uint8)
        if qc_only:
            Image.fromarray(out).save(qc_dir / f"{qc_prefix}_{W}x{H}_{t:05.1f}s.jpg", quality=86)
        else:
            proc.stdin.write(out.tobytes())
        if not qc_only and f % 240 == 0:
            print(f"  {t:5.1f}s / {dur:.0f}s", flush=True)

    if proc:
        proc.stdin.close()
        proc.wait()
        print(f"  wrote {out_path}")


def main() -> int:
    FILM.mkdir(parents=True, exist_ok=True)
    which = sys.argv[1] if len(sys.argv) > 1 else "16x9"
    if which == "frames":
        render(1920, 1080, None, qc_only=True)
        render(1080, 1920, None, qc_only=True)
    elif which == "16x9":
        render(1920, 1080, FILM / "careshield_16x9_silent.mp4")
    elif which == "9x16":
        render(1080, 1920, FILM / "careshield_9x16_silent.mp4")
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
