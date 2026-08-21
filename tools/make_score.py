"""
The film's audio bed, synthesized from scratch: a sparse felt-piano figure,
low room tone, and one soft two-note chime where CareShield asks her phone.

    python tools/make_score.py          # writes assets/film/score.wav (90s, stereo)

Honesty about what this is: no recorded instruments, no licensed track --
every sound is additive synthesis rendered here. A felt piano is the most
forgiving instrument to synthesize (soft attack, dark spectrum, drowned in
reverb), which is exactly why it was chosen. If the owner prefers a licensed
track later, replacing the audio is one ffmpeg command; the video is rendered
silent and muxed afterwards, so the picture never has to be touched.

Design rules from the film doc: ~62bpm, no percussion, the score thins
through the night, drops out entirely while the UI speaks (1:02-1:11), and
resolves DOWN at the end, not up. The chime must sound like a question.
"""
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "film" / "score.wav"

SR = 44100
DUR = 90.0
N = int(SR * DUR)

rng = np.random.default_rng(17)


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# ------------------------------------------------------------------- piano --
def piano_note(f0, dur, vel=0.5, felt=1800.0):
    """One soft piano strike: inharmonic partials, felt-dark rolloff."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    out = np.zeros(n)
    B = 0.0004                                    # string inharmonicity
    for p in range(1, 9):
        fp = f0 * p * np.sqrt(1 + B * p * p)
        if fp > SR / 2 - 200:
            break
        amp = (1 / p ** 1.7) * np.exp(-(fp / felt) ** 1.6)
        tau = (3.4 / p) * (1.0 if f0 < 240 else 0.75)
        out += amp * np.exp(-t / tau) * np.sin(2 * np.pi * fp * t + rng.uniform(0, 2 * np.pi) * 0.05)
    # soft hammer: raised-cosine attack, tiny filtered noise thump
    atk = int(SR * 0.018)
    env = np.ones(n)
    env[:atk] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, atk))
    thump_n = int(SR * 0.008)
    thump = rng.normal(0, 1, thump_n) * np.exp(-np.linspace(0, 6, thump_n))
    sos = signal.butter(2, [80, 400], "bandpass", fs=SR, output="sos")
    out[:thump_n] += signal.sosfilt(sos, thump) * 0.05
    return out * env * vel


NOTES = [
    # (time, [midi...], velocity, dur) -- the whole 90 seconds
    (10.0, [45, 52], 0.40, 8.0),        # A2+E3       her rhythm
    (13.9, [60], 0.34, 6.0),            # C4
    (17.8, [64], 0.32, 6.0),            # E4
    (21.7, [57], 0.36, 7.0),            # A3
    (25.6, [55], 0.30, 6.0),            # G3
    (29.4, [53, 60], 0.34, 7.0),        # F3+C4      the daughter
    (33.3, [64], 0.28, 6.0),            # E4
    (37.1, [62], 0.26, 6.0),            # D4
    (41.0, [45], 0.30, 9.0),            # A2         night falls
    (45.0, [52], 0.22, 8.0),            # E3
    (49.0, [48], 0.16, 9.0),            # C3         into the quiet
    (56.5, [69], 0.14, 6.0),            # A4         first grey light
    # 58.6  the chime lives here (separate voice)
    # 62-71 tacet: the screen speaks alone
    (71.5, [60, 64], 0.30, 7.0),        # C4+E4      relief
    (75.4, [67], 0.26, 6.0),            # G4
    (79.3, [57], 0.24, 5.0),            # A3 \
    (79.42, [60], 0.22, 5.0),           # C4  broken chord
    (79.55, [64], 0.20, 5.0),           # E4 /
    (84.0, [33, 45, 52], 0.34, 6.0),    # A1+A2+E3   resolve, downwards
]


def chime():
    """Two soft sine notes, falling: a question, not an alert."""
    out = np.zeros(N)
    for t0, f, dur, amp in ((58.6, midi_hz(76), 0.9, 0.10),    # E5
                            (58.95, midi_hz(72), 1.5, 0.085)):  # C5
        n = int(SR * dur)
        t = np.arange(n) / SR
        atk = int(SR * 0.03)
        env = np.exp(-t / (dur * 0.45))
        env[:atk] *= np.linspace(0, 1, atk)
        i = int(t0 * SR)
        out[i:i + n] += amp * env * np.sin(2 * np.pi * f * t)
    return out


# -------------------------------------------------------------------- verb --
def reverb(x, wet=0.55, secs=2.6, damp_hz=3000, decay=0.85):
    ir_n = int(SR * secs)
    t = np.arange(ir_n) / SR
    outs = []
    sos = signal.butter(2, damp_hz, "lowpass", fs=SR, output="sos")
    pre = int(SR * 0.02)
    for seed in (5, 9):
        r = np.random.default_rng(seed)
        ir = r.normal(0, 1, ir_n) * np.exp(-t / decay)
        ir = signal.sosfilt(sos, ir)
        ir[:pre] = 0
        ir /= np.sqrt((ir ** 2).sum() + 1e-9)
        outs.append(signal.fftconvolve(x, ir)[:len(x)])
    dry = np.stack([x, x], 1)
    wetx = np.stack([outs[0], outs[1]], 1) * 2.2
    return dry * (1 - wet) + wetx * wet


# --------------------------------------------------------------- room tone --
def room_tone():
    """A low, breathing bed. Warmer while her day runs, thinner at night,
    almost nothing in the tacet, back gently for the relief."""
    lows = signal.sosfilt(signal.butter(4, 320, "lowpass", fs=SR, output="sos"),
                          rng.normal(0, 1, N))
    air = signal.sosfilt(signal.butter(2, [2000, 7000], "bandpass", fs=SR, output="sos"),
                         rng.normal(0, 1, N)) * 0.05
    tone = lows + air
    t = np.arange(N) / SR
    env = np.interp(t, [0, 2, 39, 45, 50, 58, 62, 71, 73, 86, 90],
                       [0, 1.0, 1.0, 0.75, 0.5, 0.42, 0.30, 0.30, 0.8, 0.8, 0])
    breathe = 1 + 0.12 * np.sin(2 * np.pi * t / 11.0)
    tone = tone * env * breathe
    L = tone
    R = np.roll(tone, int(SR * 0.011))
    return np.stack([L, R], 1) * 0.055


def main() -> int:
    piano = np.zeros(N)
    for t0, chord, vel, dur in NOTES:
        for j, m in enumerate(chord):
            for detune, w in ((-0.0015, 0.5), (0.0015, 0.5)):
                note = piano_note(midi_hz(m) * (1 + detune), dur, vel * w)
                i = int(t0 * SR)
                piano[i:i + len(note)] += note[:max(0, N - i)]
    piano += chime()
    mix = reverb(piano, wet=0.55) * 0.5 + room_tone()

    # master: gentle soft-knee, then place the level low -- this is a bed
    mix = np.tanh(mix * 1.4) / 1.4
    peak = np.abs(mix).max()
    mix = mix / peak * 10 ** (-3.0 / 20) * 0.85
    # ~ -21 dB RMS overall: quiet on purpose; platforms only turn audio DOWN
    fade = np.ones(N)
    fade[: int(SR * 0.8)] = np.linspace(0, 1, int(SR * 0.8))
    fade[-int(SR * 1.5):] = np.linspace(1, 0, int(SR * 1.5))
    mix *= fade[:, None]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(OUT, SR, (mix * 32767).astype(np.int16))
    rms = 20 * np.log10(np.sqrt((mix ** 2).mean()) + 1e-12)
    print(f"  {OUT.name}: 90s stereo, peak {20*np.log10(np.abs(mix).max()):.1f} dBFS, rms {rms:.1f} dBFS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
