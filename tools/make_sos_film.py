"""
The 20-second SOS spot, v2: literal shot list, built on the CareShield film
engine.

    python tools/make_sos_film.py            # renders 16:9 + 9:16, muxes, encodes
    python tools/make_sos_film.py frames     # QC stills only

This replaces the first cut (which told the SOS story through a muted group
chat). The brief this time is explicit and prioritises clarity over mood:
button -> instant family alert -> location share must be UNMISTAKABLE, so
every UI beat is a macro shot on real, newly-rendered screens rather than an
inference the viewer has to make.

Honesty note on those screens: PulseSoul's shipped SOS mechanic is a chat-list
banner ("Live location sharing is ON" / "I'm safe") -- there was no rendered
screen for a standalone SOS button, an alert notification, or a location map.
Rather than fake those against a screen that doesn't exist, three new real
screens were designed in the app's own HTML/CSS design system and shot
through tools/shoot.py exactly like every other "real UI" asset in this repo
(assets/generated/sos_press.html, sos_notify.html, sos_map.html). They depict
nothing beyond what the product already claims in README.md / content/ads.json:
SOS alerts confirmed family and shares location -- never emergency services.
That line is kept ON SCREEN in the UI itself, not just as a caption.

No TTS/voice synthesis is reachable from this sandbox (egress is allow-listed
and speech APIs are not on it -- confirmed by a live connection test, not
assumed). The brief's VO script is carried as on-screen type instead, timed
like a voiceover would be, exactly as the first SOS film and the CareShield
film both had to do.

Cast: ai_mother_alone_home.png (the person, alone, needing help) and
ai_mother_daughter.png (the family who receives it) -- cropped left of the
promo blank-phone pose, same rule as everywhere else in this repo.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.make_film import (FILM, GEN, PHOTOS, FPS, REGULAR,                  # noqa: E402
                             Black, PhotoShot, FullBleed, Type, render)
from tools import make_endcard as ec                                            # noqa: E402
from tools.make_score import piano_note, reverb, midi_hz, SR                    # noqa: E402
from scipy import signal                                                        # noqa: E402
from scipy.io import wavfile                                                    # noqa: E402

DUR = 20.0
PRESS = GEN / "sos_press.png"
NOTIFY = GEN / "sos_notify.png"
MAPSCREEN = GEN / "sos_map.png"
TAGLINE = "When you need help, your family knows."


# ---------------------------------------------------------------- end card --
def sos_lockup(card, y, centre):
    """Same lockup grammar as the CareShield card, this film's words."""
    d = ImageDraw.Draw(card)
    name_f = ImageFont.truetype(str(ec.REGULAR), 58)
    feat_f = ImageFont.truetype(str(ec.MEDIUM), 24)
    tag_f = ImageFont.truetype(str(ec.LIGHT), 40)
    store_f = ImageFont.truetype(str(ec.LIGHT), 22)

    icon_sz, gap = 72, 22
    block_w = icon_sz + gap + name_f.getlength("PulseSoul")
    bx = centre - block_w / 2
    icon = Image.open(ec.ICON).convert("RGB").resize((icon_sz, icon_sz), Image.LANCZOS)
    card.paste(icon, (int(bx), y), ec.rounded((icon_sz, icon_sz), 20))
    d.text((bx + icon_sz + gap, y + 6), "PulseSoul", font=name_f, fill=ec.INK)
    y += icon_sz + 34

    glow = tuple(int(v) for v in ec.hex_rgb(ec.GLOW))
    fw = ec.tracked_width("SOS ALERT", feat_f, 6)
    ec.tracked(d, "SOS ALERT", feat_f, centre - fw / 2, y, glow, 6)
    y += 52
    d.line([(centre - 45, y), (centre + 45, y)], fill=(*ec.INK_FAINT, 255), width=1)
    y += 40
    for ln in ec.wrap(TAGLINE, tag_f, 780):
        d.text((centre - tag_f.getlength(ln) / 2, y), ln, font=tag_f, fill=ec.INK_SOFT)
        y += 58
    y += 24
    sub_f = ImageFont.truetype(str(ec.LIGHT), 26)
    sub = "Family only - never emergency services."
    d.text((centre - sub_f.getlength(sub) / 2, y), sub, font=sub_f, fill=ec.INK_FAINT)
    y += 52
    sw = ec.tracked_width("FREE ON GOOGLE PLAY", store_f, 4)
    ec.tracked(d, "FREE ON GOOGLE PLAY", store_f, centre - sw / 2, y, ec.INK_FAINT, 4)
    return card


def build_endcards():
    ec.SCREEN = PRESS                        # the real SOS screen, not a mock
    for name, W, H in (("sos_endcard_16x9", 1920, 1080), ("sos_endcard_9x16", 1080, 1920)):
        if W > H:
            card = ec.ground(W, H, W * 0.30, H * 0.52, 1150, 980)
            dev = ec.device(screen_w=372, rows=1150)
            card = ec.place_device(card, dev, int(W * 0.155), (H - dev.height) // 2)
            card = sos_lockup(card, int(H * 0.24), centre=W * 0.655)
        else:
            card = ec.ground(W, H, W * 0.5, H * 0.31, 940, 1080)
            dev = ec.device(screen_w=600, rows=1150)
            card = ec.place_device(card, dev, (W - dev.width) // 2, int(H * 0.075))
            card = sos_lockup(card, int(H * 0.565), centre=W / 2)
        card.convert("RGB").save(FILM / f"{name}.png")
        print(f"  {name}.png")


# ---------------------------------------------------------------- timeline --
def build_timeline(W, H, vertical=False):
    side_a = "centre" if vertical else "right"
    tx = 0.5 if vertical else 0.075
    al_a = "center" if vertical else "left"
    ty = 0.84 if vertical else 0.5
    big = 46 if vertical else 52

    endcard = FILM / ("sos_endcard_9x16.png" if vertical else "sos_endcard_16x9.png")

    shots = [
        Black(0.0, 1.4),
        # (a) emergency at home -- alone, needing help
        PhotoShot(0.9, 4.6, PHOTOS / "ai_mother_alone_home.png", None,
                  side_a, ((0.5, 0.42, 0.98), (0.46, 0.40, 0.85)), warmth=-1.0,
                  exposure=0.55, contrast=1.06, desat=0.25, night=True),
        # (b) close-up: the SOS button, held
        FullBleed(4.1, 8.0, PRESS, ((0.5, 0.27, 0.62), (0.5, 0.27, 0.30))),
        # (c) family's phone: the alert, name + location line
        FullBleed(7.5, 11.6, NOTIFY, ((0.5, 0.13, 0.55), (0.5, 0.11, 0.38))),
        # (d) family sees the location on the map, then the call card
        FullBleed(11.1, 15.6, MAPSCREEN, ((0.5, 0.40, 0.92), (0.5, 0.70, 0.60))),
        # (e) the family, together -- help is already on its way
        PhotoShot(15.1, 17.9, PHOTOS / "ai_mother_daughter.png", (0, 60, 620, 1152),
                  "centre" if vertical else "left", ((0.5, 0.45, 1.0), (0.52, 0.4, 0.88)),
                  warmth=0.55, exposure=1.05),
        FullBleed(17.5, 20.0, endcard, ((0.5, 0.5, 1.0), (0.5, 0.5, 0.965))),
    ]

    cues = [
        Type("Sometimes, you need help\nin just one tap.", 0.7, 4.3, size=big,
             pos=(tx, ty if vertical else 0.46), align=al_a),

        # (b)(c)(d) carry no overlay captions -- the real screens already say
        # "Hold for 3 seconds... alerts Priya, Rohan +2", "SOS from Priya...
        # live location shared", "Priya's location... Live... Call Priya".
        # Layering paraphrased captions on top of that real product copy
        # competed with it instead of reinforcing it.

        Type("Because when every second matters,\nyour family should know.", 15.4, 17.3,
             size=big - 6, pos=(tx if not vertical else 0.5,
                                 ty if vertical else 0.46),
             align=al_a if not vertical else "center"),

        Type("Characters portrayed with AI-generated imagery.", 17.8, 19.7, size=15,
             font=REGULAR, colour=(96, 93, 88), pos=(0.5, 0.968)),
    ]
    return shots, cues


# ------------------------------------------------------------------- score --
def score():
    N = int(SR * DUR)
    piano = np.zeros(N)
    notes = [
        (1.0, [52], 0.28, 3.5),              # E3      quiet open
        (2.6, [57, 64], 0.30, 3.0),          # A3+E4   the need
        (4.3, [60], 0.34, 4.5),              # C4      the press
        (7.6, [64, 67], 0.32, 4.5),          # E4+G4   the alert lands
        (11.3, [55, 62], 0.30, 4.5),         # G3+D4   the map
        (15.3, [57, 60, 64], 0.34, 4.5),     # A3+C4+E4  the family, resolve
    ]
    for t0, chord, vel, dur in notes:
        for m in chord:
            for detune, w in ((-0.0015, 0.5), (0.0015, 0.5)):
                note = piano_note(midi_hz(m) * (1 + detune), dur, vel * w)
                i = int(t0 * SR)
                seg = note[: N - i]
                piano[i:i + len(seg)] += seg
    # the ring-through: two RISING notes right on the button press -- firm,
    # not alarming
    for t0, f, dur, amp in ((4.35, midi_hz(72), 0.7, 0.13),     # C5
                            (4.65, midi_hz(76), 1.3, 0.11)):    # E5
        n = int(SR * dur)
        t = np.arange(n) / SR
        env = np.exp(-t / (dur * 0.45))
        atk = int(SR * 0.02)
        env[:atk] *= np.linspace(0, 1, atk)
        i = int(t0 * SR)
        piano[i:i + n] += amp * env * np.sin(2 * np.pi * f * t)

    mix = reverb(piano, wet=0.5) * 0.5

    rng = np.random.default_rng(29)
    lows = signal.sosfilt(signal.butter(4, 320, "lowpass", fs=SR, output="sos"),
                          rng.normal(0, 1, N))
    t = np.arange(N) / SR
    env = np.interp(t, [0, 1.2, 17, 20], [0, 1, 1, 0])
    mix += np.stack([lows, np.roll(lows, int(SR * 0.011))], 1) * env[:, None] * 0.05

    mix = np.tanh(mix * 1.4) / 1.4
    mix = mix / np.abs(mix).max() * 10 ** (-3.0 / 20) * 0.85
    fade = np.ones(N)
    fade[:int(SR * 0.5)] = np.linspace(0, 1, int(SR * 0.5))
    fade[-int(SR * 1.2):] = np.linspace(1, 0, int(SR * 1.2))
    mix *= fade[:, None]
    out = FILM / "sos_score.wav"
    wavfile.write(out, SR, (mix * 32767).astype(np.int16))
    print(f"  {out.name}")
    return out


# -------------------------------------------------------------------- main --
def main() -> int:
    FILM.mkdir(parents=True, exist_ok=True)
    build_endcards()

    if len(sys.argv) > 1 and sys.argv[1] == "frames":
        qc = (0.5, 2.5, 4.5, 6, 8.5, 10, 12.5, 14.5, 16.5, 19)
        render(1920, 1080, None, qc_only=True, builder=build_timeline, dur=DUR,
               qc_times=qc, qc_prefix="sos2")
        render(1080, 1920, None, qc_only=True, builder=build_timeline, dur=DUR,
               qc_times=qc, qc_prefix="sos2")
        return 0

    wav = score()
    for W, H, tag in ((1920, 1080, "16x9"), (1080, 1920, "9x16")):
        silent = FILM / f"sos_{tag}_silent.mp4"
        render(W, H, silent, builder=build_timeline, dur=DUR)
        final = FILM / f"sos_{tag}.mp4"
        subprocess.run(["ffmpeg", "-y", "-i", str(silent), "-i", str(wav),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
                        str(final)], check=True, capture_output=True)
        print(f"  {final.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
