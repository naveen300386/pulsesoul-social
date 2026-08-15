"""
Generates PulseSoul app screens as PNGs, ready for tools/make_card.py.

    python tools/build_screens.py            # all screens
    python tools/build_screens.py safety     # just one

Each screen is HTML rendered by headless Chromium. Colours and layout come
from real screenshots of the app; the CAST is invented -- Meera, Aarav, Priya,
Rohan, Kabir, Ananya -- so nothing here echoes a name, face or number from a
real phone. Never put a real contact in this file.

These are RENDERINGS of the app, not screenshots of it. Good enough for a
social card at posting size; do not use them for the Play Store listing,
where the images must be the shipped app.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "assets" / "generated"

from tools.shoot import shoot  # noqa: E402

W, H = 1080, 2280

# --- invented cast. Do not replace these with real contacts. ----------------
CAST = ["Meera", "Aarav", "Priya", "Rohan", "Kabir", "Ananya", "Ishaan", "Diya"]

# --- Minimal (ivory & gold): the theme the published eight cards use --------
BASE = """
@font-face{font-family:P;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf')}
@font-face{font-family:P;font-weight:500;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf')}
@font-face{font-family:P;font-weight:700;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf')}
@font-face{font-family:E;src:url('/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf')}
*{margin:0;padding:0;box-sizing:border-box;-webkit-font-smoothing:antialiased}
body{width:1080px;height:2280px;font-family:P,sans-serif;overflow:hidden;position:relative;
     background:#EDE6DB;color:#1E1B16}
.hdr{height:150px;background:#E3D8C2;display:flex;align-items:center;justify-content:space-between;padding:0 34px}
.brand{display:flex;align-items:center;gap:16px}
.mark{width:66px;height:60px}
.word{font-size:46px;font-weight:700;background:linear-gradient(95deg,#D9822B,#C9A227);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hi{display:flex;gap:38px;align-items:center}
.hi svg{width:46px;height:46px}
.dot{position:relative}
.dot::after{content:'';position:absolute;right:-3px;top:-3px;width:18px;height:18px;border-radius:50%;background:#E0322F}
.me{width:72px;height:72px;border-radius:50%;background:#6E76D8;display:flex;align-items:center;
    justify-content:center;font-size:32px;font-weight:600;color:#fff;box-shadow:0 0 0 5px #E3D8C2,0 0 0 8px #C9A227}
.title{height:150px;display:flex;align-items:center;gap:34px;padding:0 40px;background:#E3D8C2}
.title svg{width:50px;height:50px;stroke:#1E1B16;fill:none;stroke-width:2.6}
.title h1{font-size:50px;font-weight:700}
.card{background:#F3EDE4;border:1.5px solid #00000010;border-radius:28px}
.dock{position:absolute;left:26px;right:26px;bottom:34px;height:150px;border-radius:75px;
      background:#EBE3D6;display:flex;align-items:center;justify-content:space-around}
.tab{display:flex;flex-direction:column;align-items:center;gap:8px;color:#6B6459;font-size:27px;font-weight:500}
.tab svg{width:44px;height:44px;fill:currentColor}
.tab.on{color:#1E1B16}
.tab.on .box{background:#E0A63A;border-radius:38px;padding:12px 48px;margin-bottom:4px;display:inline-block;color:#3A2A08}
.fab{position:absolute;right:46px;bottom:230px;width:126px;height:126px;border-radius:38px;
     background:#E0A63A;display:flex;align-items:center;justify-content:center}
.fab svg{width:58px;height:58px;stroke:#fff;fill:none;stroke-width:2.4}
"""

MARK = """<svg class="mark" viewBox="0 0 48 44">
 <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="#8B5CF6"/><stop offset=".55" stop-color="#EC4899"/><stop offset="1" stop-color="#F97316"/></linearGradient></defs>
 <path d="M24 3.5C12.6 3.5 3.5 11 3.5 20.2c0 5.3 3 10 7.8 13l-1.6 7.3 8-4.3c2 .5 4.1.7 6.3.7 11.4 0 20.5-7.5 20.5-16.7S35.4 3.5 24 3.5z" fill="none" stroke="url(#g)" stroke-width="3.4"/>
 <path d="M11.5 20.5h5l2.8-6.2 3.8 12.4 3.2-7.6 2.5 3.8h2.8" fill="none" stroke="#EF4444" stroke-width="3.1" stroke-linecap="round" stroke-linejoin="round"/>
 <path d="M33.4 17c1.5-1.6 4.1-1.4 5.3.4 1 1.4.7 3.3-.6 4.5l-4.4 4-4.4-4c-1.3-1.2-1.6-3.1-.6-4.5 1.2-1.8 3.8-2 5.3-.4z" fill="#EF4444"/></svg>"""

ICONS = """
 <span class="dot"><svg viewBox="0 0 24 24" fill="none" stroke="#1E1B16" stroke-width="2"><rect x="3" y="5" width="18" height="17" rx="3"/><path d="M8 2.5v5M16 2.5v5M3 11h18"/></svg></span>
 <svg viewBox="0 0 24 24" fill="#1E1B16"><path d="M12 2.5l8 3.2v6.1c0 5.3-3.4 8.6-8 9.7-4.6-1.1-8-4.4-8-9.7V5.7z"/><path d="M11 8.2h2v3h3v2h-3v3h-2v-3H8v-2h3z" fill="#E3D8C2"/></svg>
 <svg viewBox="0 0 24 24" fill="#1E1B16"><circle cx="8" cy="4.6" r="2.3"/><path d="M6.2 8h3.6l1.3 6.2H9.9V21H6.1v-6.8H4.9z"/><circle cx="16.8" cy="4.6" r="2.3"/><path d="M14.5 8.4h4.6l1 5.8h-1.5V21h-1.4v-6.8h-.7V21h-1.4v-6.8h-1.6z"/></svg>
 <span class="me">M</span>"""

DOCK = """<div class="dock">
 <div class="tab {chats}"><span class="box"><svg viewBox="0 0 24 24"><rect x="2.5" y="4" width="19" height="14" rx="3"/><path d="M7 21.2l1.2-3.2h3.4z"/></svg></span>Chats</div>
 <div class="tab {calls}"><svg viewBox="0 0 24 24"><path d="M5.2 3.6h3.9l1.9 4.8-2.8 1.9a12.4 12.4 0 005.5 5.5l1.9-2.8 4.8 1.9v3.9a1.8 1.8 0 01-1.8 1.8A16.8 16.8 0 013.4 5.4a1.8 1.8 0 011.8-1.8z"/></svg>Calls</div>
 <div class="tab"><svg viewBox="0 0 24 24"><circle cx="8.6" cy="8.2" r="3.1"/><circle cx="16.4" cy="9.4" r="2.5"/><path d="M2.6 19.4c0-3.3 2.7-5.2 6-5.2s6 1.9 6 5.2zM15.4 19.4c0-2 .5-3.4 1.5-4.2 2.6-.3 4.5 1.3 4.5 4.2z"/></svg>Groups</div>
 <div class="tab {mom}"><svg viewBox="0 0 24 24" style="fill:none;stroke:currentColor;stroke-width:2.4;stroke-linecap:round;stroke-dasharray:9 5.5"><circle cx="12" cy="12" r="8.4"/></svg>Moments</div>
</div>"""


def page(body: str, extra: str = "") -> str:
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{BASE}{extra}</style></head><body>{body}</body></html>"


# ---------------------------------------------------------------- screens --
def screen_safety() -> str:
    """Chat list with the live-location banner and the I'm safe button."""
    rows = [("M", "#6E76D8", "Meera", "You: ✅ I'm safe. Just letting you know.", "8:09 pm", True),
            ("A", "#E0788A", "Aarav", "You: 🎤 Voice message", "7:48 pm", False),
            ("P", "#E0894F", "Priya", "You: 📹 Missed video call", "5:40 pm", True),
            ("R", "#6BBE8E", "Rohan", "Ghar pahunch gaya", "4 Aug", False),
            ("K", "#8B8FE3", "Kabir", "Voice note · 0:31", "2 Aug", False)]
    items = "".join(
        f"""<div class="row card"><span class="av" style="background:{c}">{i}</span>
        <div class="mid"><div class="nm">{n}{' <span class="fl">🔥 1</span>' if f else ''}</div>
        <div class="pv">{p}</div></div><div class="tm">{t}</div></div>""" for i, c, n, p, t, f in rows)
    extra = """
    .banner{background:#D32F2F;color:#fff;display:flex;align-items:center;gap:26px;padding:26px 34px}
    .banner svg{width:52px;height:52px;stroke:#fff;fill:none;stroke-width:2.6;flex:none}
    .banner .t{flex:1}.banner b{display:block;font-size:38px;font-weight:700}
    .banner span{font-size:29px;opacity:.92}
    .safe{background:#fff;color:#D32F2F;font-size:33px;font-weight:700;border-radius:20px;padding:20px 34px}
    .search{margin:24px 30px 0;height:106px;background:#F3EDE4;border-radius:53px;display:flex;
            align-items:center;gap:26px;padding:0 36px}
    .search svg{width:40px;height:40px;stroke:#8A8378;fill:none;stroke-width:2.5}
    .search span{flex:1;color:#8A8378;font-size:34px}
    .segwrap{margin:22px 30px 0;height:108px;background:#F0EAE1;border-radius:54px;display:flex;align-items:center;padding:0 8px}
    .seg{flex:1;height:90px;display:flex;align-items:center;justify-content:center;font-size:33px;color:#5C554A}
    .seg.on{background:#E0A63A;border-radius:45px;color:#3A2A08;font-weight:700}
    .list{margin-top:34px;padding:0 30px;display:flex;flex-direction:column;gap:20px}
    .row{height:150px;display:flex;align-items:center;padding:0 28px;gap:26px}
    .av{width:94px;height:94px;border-radius:50%;display:flex;align-items:center;justify-content:center;
        font-size:36px;font-weight:600;color:#fff;flex:none}
    .mid{flex:1;min-width:0}.nm{display:flex;align-items:center;gap:16px;font-size:37px;font-weight:700}
    .pv{font-size:30px;color:#6B6459;margin-top:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .fl{font-size:25px;font-weight:700;color:#B4700A;background:#F2DFB4;border-radius:20px;padding:4px 16px}
    .tm{font-size:27px;color:#6B6459;align-self:flex-start;margin-top:30px}"""
    return page(f"""
    <div class="hdr"><div class="brand">{MARK}<span class="word">PulseSoul</span></div><div class="hi">{ICONS}</div></div>
    <div class="banner">
      <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3.4"/><circle cx="12" cy="12" r="8.4"/><path d="M12 1v3M12 20v3M1 12h3M20 12h3"/></svg>
      <div class="t"><b>Live location sharing is ON</b><span>Your family can see you · stops in 29m</span></div>
      <span class="safe">I'm safe</span>
    </div>
    <div class="search"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7.2"/><path d="M20 20l-4.2-4.2"/></svg>
      <span>Search family, messages…</span></div>
    <div class="segwrap"><div class="seg on">All</div><div class="seg">Family</div><div class="seg">Unread</div><div class="seg">Starred</div></div>
    <div class="list">{items}</div>
    {DOCK.format(chats='on', calls='', mom='')}""", extra)


def screen_calls() -> str:
    rows = [("M", "#6E76D8", "Meera", "↗ 5:40 pm · Cancelled", False),
            ("A", "#E0788A", "Aarav", "↗ 5:40 pm · Cancelled", False),
            ("P", "#E0894F", "Priya", "↙ 10:12 am · Missed", True),
            ("R", "#6BBE8E", "Rohan", "↗ 8:57 am · Cancelled", False),
            ("K", "#8B8FE3", "Kabir", "↙ 8:35 am · Missed", True),
            ("A", "#C173C9", "Ananya", "↗ Wed, 5:41 pm", False)]
    items = "".join(
        f"""<div class="row card"><span class="av" style="background:{c}">{i}</span>
        <div class="mid"><div class="nm" style="{'color:#C62828' if m else ''}">{n}</div>
        <div class="pv" style="{'color:#C62828' if m else ''}">{s}</div></div>
        <span class="cb"><svg viewBox="0 0 24 24"><path d="M5.2 3.6h3.9l1.9 4.8-2.8 1.9a12.4 12.4 0 005.5 5.5l1.9-2.8 4.8 1.9v3.9a1.8 1.8 0 01-1.8 1.8A16.8 16.8 0 013.4 5.4a1.8 1.8 0 011.8-1.8z"/></svg></span></div>"""
        for i, c, n, s, m in rows)
    extra = """
    .segwrap{margin:34px 30px 0;height:108px;width:560px;background:#F0EAE1;border-radius:54px;display:flex;align-items:center;padding:0 8px}
    .seg{flex:1;height:90px;display:flex;align-items:center;justify-content:center;font-size:33px;color:#5C554A}
    .seg.on{background:#E0A63A;border-radius:45px;color:#3A2A08;font-weight:700}
    .lbl{padding:38px 34px 8px;font-size:28px;font-weight:700;color:#6B6459;letter-spacing:1.6px}
    .list{padding:0 30px;display:flex;flex-direction:column;gap:20px}
    .row{height:150px;display:flex;align-items:center;padding:0 28px;gap:26px}
    .av{width:94px;height:94px;border-radius:50%;display:flex;align-items:center;justify-content:center;
        font-size:36px;font-weight:600;color:#fff;flex:none}
    .mid{flex:1}.nm{font-size:37px;font-weight:700}
    .pv{font-size:29px;color:#6B6459;margin-top:8px}
    .cb{width:92px;height:92px;border-radius:50%;background:#F2E3C6;display:flex;align-items:center;justify-content:center;flex:none}
    .cb svg{width:44px;height:44px;fill:#C08A1E}"""
    return page(f"""
    <div class="hdr"><div class="brand">{MARK}<span class="word">Calls</span></div><div class="hi">{ICONS}</div></div>
    <div class="segwrap"><div class="seg on">All</div><div class="seg">Missed</div></div>
    <div class="lbl">RECENT</div>
    <div class="list">{items}</div>
    {DOCK.format(chats='', calls='on', mom='')}""", extra)


def screen_pulse() -> str:
    extra = """
    .pulse{margin:34px 34px 0;padding:36px 38px;border-radius:30px;
           background:linear-gradient(160deg,#F4E3C2,#EFE6D6);border:1.5px solid #00000010;
           display:flex;gap:30px;align-items:flex-start}
    .pulse .h{font-family:E;font-size:56px;line-height:1;flex:none}
    .pulse b{display:block;font-size:31px;font-weight:700;color:#B4700A;margin-bottom:14px}
    .pulse p{font-size:34px;line-height:1.45}
    .mem{display:flex;align-items:center;gap:28px;padding:44px 40px 0}
    .mem .av{width:96px;height:96px;border-radius:50%;background:#6E76D8;display:flex;align-items:center;
             justify-content:center;font-size:38px;font-weight:600;color:#fff}
    .mem b{font-size:40px;font-weight:700;display:block}
    .mem span{font-size:30px;color:#6B6459}
    .mem .dots{margin-left:auto;font-size:44px;color:#6B6459;letter-spacing:2px}"""
    members = "".join(f"""<div class="mem"><span class="av" style="background:{c}">{n[0]}</span>
      <span><b>{n}</b><span>my {r}</span></span><span class="dots">⋮</span></div>"""
      for n, r, c in [("Meera", "Sister", "#6E76D8"), ("Aarav", "Father", "#E0894F"),
                      ("Priya", "Mother", "#E0788A"), ("Rohan", "Brother", "#6BBE8E"),
                      ("Kabir", "Brother", "#8B8FE3"), ("Ananya", "Cousin", "#C98BB0"),
                      ("Ishaan", "Uncle", "#7FB0D4"), ("Diya", "Niece", "#D9A15B")])
    return page(f"""
    <div class="title"><svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7"/></svg><h1>My family</h1></div>
    <div class="pulse"><span class="h">❤️</span>
      <div><b>Today's family pulse</b>
      <p>Great to see you staying connected with Aarav today! Keep that momentum going—every day of
      connection strengthens your bond.</p></div></div>
    {members}
    <div class="fab"><svg viewBox="0 0 24 24"><circle cx="10" cy="8" r="3.6"/><path d="M3.5 20c0-3.4 2.9-5.4 6.5-5.4M18 12v7M14.5 15.5h7"/></svg></div>""", extra)


def screen_background() -> str:
    tiles = [("Ocean", "linear-gradient(160deg,#7FD3EA,#3FA9D4)", False),
             ("Romantic", "linear-gradient(160deg,#F6DDE6,#EFC3D5)", False),
             ("Petals", "linear-gradient(160deg,#F3E4DA,#EAD3C4)", True),
             ("Meadow", "linear-gradient(160deg,#E4EBDA,#CBDCC2)", False),
             ("Festival", "linear-gradient(160deg,#F3E9D6,#E7D8BC)", False),
             ("Frost", "linear-gradient(160deg,#EDF3F8,#DCE7F2)", False)]
    grid = "".join(f"""<div class="sw"><div class="th" style="background:{g};{'border:5px solid #7A5410' if s else ''}">
      <span class="sp">✨</span>{'<span class="tick">✓</span>' if s else ''}</div>
      <div class="cap" style="{'font-weight:700' if s else ''}">{n}</div></div>""" for n, g, s in tiles)
    extra = """
    .prev{margin:30px 34px 0;height:390px;border-radius:34px;background:linear-gradient(160deg,#F3E4DA,#EAD3C4);
          position:relative;padding:34px}
    .bub{background:#EFE7DC;border-radius:26px;padding:20px 30px;font-size:33px;display:inline-block}
    .ok{position:absolute;right:34px;bottom:34px;background:#7A5410;color:#fff;font-size:33px;font-weight:700;
        border-radius:38px;padding:22px 44px}
    .sl{display:flex;align-items:center;gap:30px;padding:34px 40px 0}
    .sl svg{width:48px;height:48px;stroke:#5C4A20;fill:none;stroke-width:2.2;flex:none}
    .sl .lbl{font-size:34px;flex:none;width:250px}
    .track{flex:1;height:12px;border-radius:6px;background:#DED5C6;position:relative}
    .fill{position:absolute;left:0;top:0;bottom:0;border-radius:6px;background:#7A5410}
    .knob{position:absolute;top:-16px;width:44px;height:44px;border-radius:50%;background:#7A5410}
    .val{width:150px;text-align:right;font-size:34px;font-weight:700;flex:none}
    .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:28px;padding:40px 34px 0}
    .th{height:290px;border-radius:26px;position:relative}
    .sp{position:absolute;left:18px;top:14px;font-family:E;font-size:44px}
    .tick{position:absolute;right:18px;top:14px;width:56px;height:56px;border-radius:50%;background:#7A5410;
          color:#fff;font-size:34px;display:flex;align-items:center;justify-content:center}
    .cap{text-align:center;font-size:32px;margin-top:16px}
    .btns{position:absolute;left:34px;right:34px;bottom:40px;display:flex;gap:26px}
    .b1{flex:1;height:118px;border:2px solid #7A5410;border-radius:26px;display:flex;align-items:center;
        justify-content:center;font-size:34px;font-weight:700;color:#5C4A20}
    .b2{flex:1.4;height:118px;background:#7A5410;border-radius:26px;display:flex;align-items:center;
        justify-content:center;font-size:34px;font-weight:700;color:#fff}"""
    return page(f"""
    <div class="title"><svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7"/></svg><h1>Chat background</h1></div>
    <div class="prev"><span class="bub">Hi 👋</span><span class="ok">Looks great</span></div>
    <div class="sl"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/></svg>
      <span class="track"><span class="fill" style="width:92%"></span><span class="knob" style="left:88%"></span></span><span class="val">100%</span></div>
    <div class="sl"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 12l5-3"/></svg>
      <span class="track"><span class="fill" style="width:38%"></span><span class="knob" style="left:34%"></span></span><span class="val">1x</span></div>
    <div class="sl"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 010 18z" fill="#5C4A20"/></svg>
      <span class="track"><span class="fill" style="width:58%"></span><span class="knob" style="left:54%"></span></span><span class="val">Auto</span></div>
    <div class="sl"><svg viewBox="0 0 24 24"><path d="M12 3s6 7 6 11a6 6 0 01-12 0c0-4 6-11 6-11z"/></svg>
      <span class="lbl">Transparency</span>
      <span class="track"><span class="fill" style="width:20%"></span><span class="knob" style="left:16%"></span></span><span class="val">20</span></div>
    <div class="grid">{grid}</div>
    <div class="btns"><span class="b1">Set as default</span><span class="b2">Apply to this chat</span></div>""", extra)


def screen_moments() -> str:
    extra = """
    .post{margin:30px 30px 0;border-radius:30px;overflow:hidden;background:#F3EDE4;border:1.5px solid #00000010}
    .who{display:flex;align-items:center;gap:24px;padding:26px 30px}
    .who .av{width:80px;height:80px;border-radius:50%;display:flex;align-items:center;justify-content:center;
             font-size:32px;font-weight:600;color:#fff}
    .who b{font-size:36px;font-weight:700;display:block}
    .who span{font-size:28px;color:#6B6459}
    .ph{height:700px}
    .like{display:flex;align-items:center;gap:20px;padding:24px 30px;font-size:32px;color:#6B6459}
    .like svg{width:44px;height:44px;stroke:#6B6459;fill:none;stroke-width:2.2}
    .note{position:absolute;left:30px;right:30px;bottom:250px;text-align:center;font-size:27px;color:#8A8378}"""
    return page(f"""
    <div class="title"><svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7"/></svg><h1>Family Moments</h1></div>
    <div class="post">
      <div class="who"><span class="av" style="background:#6E76D8">M</span>
        <span><b>Meera</b><span>25 Jul</span></span></div>
      <div class="ph" style="background:linear-gradient(150deg,#E8CFA8,#D9A96F 55%,#C98A54)"></div>
      <div class="like"><svg viewBox="0 0 24 24"><path d="M12 20s-7-4.6-7-9.4A4 4 0 0112 8a4 4 0 017 2.6C19 15.4 12 20 12 20z"/></svg>4</div>
    </div>
    <div class="post">
      <div class="who"><span class="av" style="background:#E0894F">A</span>
        <span><b>Aarav</b><span>25 Jul</span></span></div>
      <div class="ph" style="background:linear-gradient(150deg,#CBD9E6,#9FB6CE 55%,#7E97B4)"></div>
    </div>
    <div class="fab"><svg viewBox="0 0 24 24"><path d="M3 8.6h3.4l1.3-2.1h8.6l1.3 2.1H21a1 1 0 011 1v8.8a1 1 0 01-1 1H3a1 1 0 01-1-1V9.6a1 1 0 011-1z"/><circle cx="12" cy="14" r="3.6"/></svg></div>""", extra)


def screen_drive() -> str:
    """Dark theme: the Google Drive transfer sheet - a real differentiator."""
    extra = """
    body{background:#000;color:#EFEFEA}
    .top{padding:40px 40px 0}
    .top svg{width:52px;height:52px;stroke:#EFEFEA;fill:none;stroke-width:2.6}
    .pf{text-align:center;margin-top:30px}
    .pf .av{width:290px;height:290px;border-radius:50%;margin:0 auto;background:linear-gradient(150deg,#6E76D8,#8E64C8);
            display:flex;align-items:center;justify-content:center;font-size:110px;font-weight:700;color:#fff}
    .pf b{display:block;font-size:56px;font-weight:700;margin-top:34px}
    .pf span{display:block;font-size:32px;color:#9A968E;margin-top:10px}
    .lbl{padding:56px 40px 20px;font-size:29px;font-weight:700;color:#E0A63A;letter-spacing:1.6px}
    .card{margin:0 40px;background:#141416;border:1.5px solid #FFFFFF14;border-radius:28px}
    .it{display:flex;align-items:center;gap:32px;padding:34px 34px}
    .it svg{width:52px;height:52px;stroke:#EFEFEA;fill:none;stroke-width:2.2;flex:none}
    .it b{font-size:38px;font-weight:500;display:block}
    .it span{font-size:29px;color:#9A968E;display:block;margin-top:8px}
    .scrim{position:absolute;inset:0;background:#00000078}
    .sheet{position:absolute;left:0;right:0;bottom:0;background:#141418;border-radius:44px 44px 0 0;padding:0 42px 56px}
    .shead{font-size:44px;font-weight:700;margin-bottom:10px}
    .ssub{font-size:30px;color:#9A968E;margin-bottom:16px}
    .size{display:flex;align-items:baseline;gap:20px;padding:30px 34px 34px;border-top:1.5px solid #FFFFFF12}
    .size b{font-size:52px;font-weight:700;color:#E0A63A}
    .size span{font-size:30px;color:#9A968E}
    .grip{width:96px;height:10px;border-radius:5px;background:#EFE3D0;opacity:.55;margin:30px auto 44px}
    .opt{display:flex;gap:32px;padding:30px 0;align-items:flex-start}
    .opt svg{width:52px;height:52px;stroke:#EFEFEA;fill:none;stroke-width:2.2;flex:none;margin-top:6px}
    .opt b{font-size:38px;font-weight:500;display:block}
    .opt p{font-size:29px;color:#9A968E;line-height:1.42;margin-top:8px}
    .warn b{color:#F08A8A}.warn svg{stroke:#F08A8A}"""
    return page(f"""
    <div class="top"><svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7"/></svg></div>
    <div class="pf"><span class="av">M</span><b>Meera</b><span>last seen recently</span></div>
    <div class="lbl">SHARED</div>
    <div class="card">
      <div class="it"><svg viewBox="0 0 24 24"><rect x="3" y="6" width="18" height="13" rx="3"/><path d="M3 15l5-4 4 3 3-2 6 5"/></svg>
        <span><b>Media, links and docs</b><span>Photos, videos, documents, links</span></span></div>
      <div class="size"><b>1.7 GB</b><span>media saved on this phone from this chat</span></div>
    </div>
    <div class="scrim"></div>
    <div class="sheet">
      <div class="grip"></div>
      <div class="shead">Send media to Google Drive</div>
      <div class="ssub">Uploads to your own Google Drive account</div>
      <div class="opt"><svg viewBox="0 0 24 24"><path d="M6 18a4 4 0 010-8 6 6 0 0111.5-1.5A3.5 3.5 0 0119 18z"/><path d="M12 12v6M9 15l3-3 3 3"/></svg>
        <span><b>Only transfer</b><p>Copies this chat's media to your Drive</p></span></div>
      <div class="opt warn"><svg viewBox="0 0 24 24"><path d="M5 7h14M9 7V4h6v3M7 7l1 13h8l1-13"/></svg>
        <span><b>Transfer &amp; delete from mobile</b><p>After a safe upload, removes the local copies to free
        space - media stays in the chat and re-downloads anytime</p></span></div>
      <div class="opt"><svg viewBox="0 0 24 24"><circle cx="6" cy="12" r="2.6"/><circle cx="18" cy="6" r="2.6"/><circle cx="18" cy="18" r="2.6"/><path d="M8.4 10.8l7.2-3.6M8.4 13.2l7.2 3.6"/></svg>
        <span><b>Backup to other cloud…</b></span></div>
    </div>""", extra)


def screen_events() -> str:
    """The family-dates dialog over My family. Replaces the old card, whose
    dates were a real person's."""
    extra = """
    .scrim{position:absolute;inset:0;background:#0000004D}
    .fab{z-index:3}
    .mem{display:flex;align-items:center;gap:28px;padding:44px 40px 0}
    .mem .av{width:96px;height:96px;border-radius:50%;display:flex;align-items:center;
             justify-content:center;font-size:38px;font-weight:600;color:#fff}
    .mem b{font-size:40px;font-weight:700;display:block}
    .mem span{font-size:30px;color:#6B6459}
    .dlg{position:absolute;left:70px;right:70px;top:640px;background:#F7F2E9;border-radius:36px;
         padding:48px 46px 34px;box-shadow:0 30px 70px #00000045}
    .dlg h2{font-size:52px;font-weight:700;margin-bottom:38px}
    .ev{display:flex;align-items:center;gap:30px;padding:22px 0}
    .ev svg{width:52px;height:52px;stroke:#3B342A;fill:none;stroke-width:2.2;flex:none}
    .ev b{font-size:38px;font-weight:500;display:block}
    .ev span{font-size:30px;color:#6B6459;display:block;margin-top:8px}
    .close{text-align:right;font-size:34px;font-weight:600;color:#8A5A12;padding:26px 6px 0}"""
    members = "".join(f"""<div class="mem"><span class="av" style="background:{c}">{n[0]}</span>
      <span><b>{n}</b><span>my {r}</span></span></div>"""
      for n, r, c in [("Aarav", "Father", "#E0894F"), ("Priya", "Mother", "#E0788A"),
                      ("Meera", "Sister", "#6E76D8"), ("Rohan", "Brother", "#6BBE8E"),
                      ("Kabir", "Brother", "#8B8FE3"), ("Ananya", "Cousin", "#C98BB0"),
                      ("Ishaan", "Uncle", "#7FB0D4"), ("Diya", "Niece", "#D9A15B"),
                      ("Vikram", "Uncle", "#6BBE8E"), ("Sanya", "Cousin", "#A97CD8")])
    return page(f"""
    <div class="title"><svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7"/></svg><h1>My family</h1></div>
    {members}
    <div class="scrim"></div>
    <div class="dlg">
      <h2>Aarav's events</h2>
      <div class="ev"><svg viewBox="0 0 24 24"><path d="M4 20h16M6 20v-6h12v6M8 14V9h8v5M12 9V5M9.5 5.5a2.5 2.5 0 015 0"/></svg>
        <span><b>Birthday</b><span>14 Sep · every year</span></span></div>
      <div class="ev"><svg viewBox="0 0 24 24"><path d="M12 20.5S3.5 15 3.5 9.4A4.4 4.4 0 0112 7.6a4.4 4.4 0 018.5 1.8c0 5.6-8.5 11.1-8.5 11.1z"/></svg>
        <span><b>Anniversary</b><span>22 Nov · every year</span></span></div>
      <div class="close">Close</div>
    </div>
    <div class="fab"><svg viewBox="0 0 24 24"><circle cx="10" cy="8" r="3.6"/><path d="M3.5 20c0-3.4 2.9-5.4 6.5-5.4M18 12v7M14.5 15.5h7"/></svg></div>""", extra)


def screen_streak() -> str:
    """The streak sheet. Counted on the phone, which the sheet says itself."""
    extra = """
    .scrim{position:absolute;inset:0;background:#0000004D}
    .sheet{position:absolute;left:56px;right:56px;top:430px;background:#FBF7F0;border-radius:44px;
           padding:56px 46px 46px;text-align:center;box-shadow:0 30px 70px #00000045}
    .free{display:inline-block;background:#DFF3E3;color:#1F6B36;border-radius:26px;
          padding:12px 30px;font-size:28px;font-weight:700;margin-bottom:44px}
    .pair{display:flex;justify-content:center;gap:-20px;margin-bottom:34px}
    .pair span{width:130px;height:130px;border-radius:50%;display:flex;align-items:center;
               justify-content:center;font-size:52px;font-weight:600;color:#fff;border:6px solid #FBF7F0}
    .pair span+span{margin-left:-34px}
    .fire{font-family:E;font-size:96px;line-height:1}
    .big{font-size:104px;font-weight:700;color:#D9822B;line-height:1.1}
    .cap{font-size:36px;font-weight:500;margin-bottom:46px}
    .stats{display:flex;gap:22px;margin-bottom:44px}
    .st{flex:1;background:#F1EADF;border-radius:26px;padding:26px 10px}
    .st b{display:block;font-size:44px;font-weight:700}
    .st span{font-size:24px;font-weight:700;color:#6B6459;letter-spacing:.8px}
    .cta{background:#E0A63A;border-radius:44px;padding:30px 0;font-size:40px;font-weight:700;color:#3A2A08}
    .fine{font-size:26px;color:#6B6459;margin-top:26px}"""
    return page(f"""
    <div class="hdr"><div class="brand">{MARK}<span class="word">PulseSoul</span></div><div class="hi">{ICONS}</div></div>
    <div class="scrim"></div>
    <div class="sheet">
      <div class="free">✓ Free on PulseSoul</div>
      <div class="pair"><span style="background:#6E76D8">M</span><span style="background:#E0894F">A</span></div>
      <div class="fire">🔥</div>
      <div class="big">4</div>
      <div class="cap">day streak with Meera</div>
      <div class="stats">
        <div class="st"><b>4</b><span>PERSONAL BEST</span></div>
        <div class="st"><b>5d</b><span>FRIENDS SINCE</span></div>
        <div class="st"><b>2h 57m</b><span>ENDS IN</span></div>
      </div>
      <div class="cta">Send something 🔥</div>
      <div class="fine">Counted on your phone. Nothing extra leaves your device.</div>
    </div>""", extra)


def screen_voice() -> str:
    """Voice notes with the filter tags -- the feature the old voice card
    showed over a real family photo."""
    extra = """
    body{background:#F0E9DE}
    .bar{height:150px;display:flex;align-items:center;gap:30px;padding:0 34px;background:#E3D8C2}
    .bar svg{width:48px;height:48px;stroke:#2B2723;fill:none;stroke-width:2.6}
    .pa{width:88px;height:88px;border-radius:50%;background:#6E76D8;display:flex;align-items:center;
        justify-content:center;font-size:36px;font-weight:600;color:#fff;flex:none}
    .who{flex:1}.who b{display:block;font-size:40px;font-weight:700}.who span{font-size:28px;color:#5B534A}
    .day{display:flex;justify-content:center;margin:30px 0}
    .day span{background:#E3D8C2;border-radius:34px;padding:12px 40px;font-size:28px;font-weight:600}
    .wrap{padding:0 34px}
    .vn{max-width:740px;background:#F7F2E9;border:1.5px solid #00000010;border-radius:30px;
        padding:28px 32px;margin:0 0 24px auto}
    .vrow{display:flex;align-items:center;gap:26px}
    .play{width:76px;height:76px;border-radius:50%;background:#E0A63A;display:flex;align-items:center;justify-content:center;flex:none}
    .play svg{width:34px;height:34px;fill:#3A2A08}
    .wave{flex:1;height:8px;border-radius:4px;background:#DCD1C0}
    .sp{font-size:30px;font-weight:600;color:#5B534A}
    .tag{display:inline-flex;align-items:center;gap:12px;background:#EFE3CB;border-radius:16px;
         padding:9px 22px;font-size:26px;font-weight:700;letter-spacing:.6px;margin-top:20px}
    .mt{font-size:25px;color:#6B6459;margin-top:14px;text-align:right}
    .rec{position:absolute;left:34px;right:34px;bottom:180px;background:#F7F2E9;border:1.5px solid #00000010;
         border-radius:36px;padding:34px 34px 30px}
    .rl{font-size:29px;font-weight:700;color:#8A5A12;letter-spacing:1.2px;margin-bottom:24px}
    .chips{display:flex;flex-wrap:wrap;gap:18px}
    .ch{background:#EFE7DA;border-radius:26px;padding:16px 30px;font-size:30px;font-weight:500}
    .ch.on{background:#E0A63A;color:#3A2A08;font-weight:700}
    .composer{position:absolute;left:0;right:0;bottom:0;height:150px;display:flex;align-items:center;
              gap:30px;padding:0 34px}
    .field{flex:1;height:100px;border-radius:50px;background:#F7F2E9;border:1.5px solid #00000010;
           display:flex;align-items:center;padding:0 36px;font-size:34px;color:#8A8378}
    .mic{width:106px;height:106px;border-radius:50%;background:#E0A63A;display:flex;align-items:center;justify-content:center;flex:none}
    .mic svg{width:50px;height:50px;stroke:#3A2A08;fill:none;stroke-width:2.6}"""
    notes = "".join(f"""<div class="vn"><div class="vrow">
      <span class="play"><svg viewBox="0 0 24 24"><path d="M7 4l13 8-13 8z"/></svg></span>
      <span class="wave"></span><span class="sp">{sp}</span></div>
      <span class="tag">{emo} {tag}</span><div class="mt">{tm} ✓✓</div></div>"""
      for emo, tag, sp, tm in [("👽", "ALIEN", "1x", "09:35"), ("🐿️", "CHIPMUNK", "1x", "09:36"),
                               ("🎉", "PARTY", "1.5x", "09:38")])
    return page(f"""
    <div class="bar"><svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7"/></svg>
      <span class="pa">M</span><span class="who"><b>Meera</b><span>last seen recently</span></span>
      <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>
      <svg viewBox="0 0 24 24" style="fill:#2B2723;stroke:none"><path d="M5.2 3.6h3.9l1.9 4.8-2.8 1.9a12.4 12.4 0 005.5 5.5l1.9-2.8 4.8 1.9v3.9a1.8 1.8 0 01-1.8 1.8A16.8 16.8 0 013.4 5.4a1.8 1.8 0 011.8-1.8z"/></svg></div>
    <div class="day"><span>Today</span></div>
    <div class="wrap">{notes}</div>
    <div class="rec">
      <div class="rl">VOICE EFFECT</div>
      <div class="chips"><span class="ch">None</span><span class="ch">Deep</span>
        <span class="ch">Chipmunk</span><span class="ch">Robot</span><span class="ch on">Alien</span>
        <span class="ch">Echo</span><span class="ch">Party</span></div>
    </div>
    <div class="composer"><span class="field">Message</span>
      <span class="mic"><svg viewBox="0 0 24 24"><rect x="9" y="2.5" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0013 0M12 17.5V21"/></svg></span></div>""", extra)


SCREENS = {
    "safety": (screen_safety, "One tap to say you're safe", "Live location that stops on its own"),
    "calls": (screen_calls, "Calls that just work", "Voice and video over the internet"),
    "pulse": (screen_pulse, "A nudge, not a notification", "Today's family pulse"),
    "background": (screen_background, "Every chat, your way", "Backgrounds, blur and brightness per chat"),
    "moments": (screen_moments, "Moments worth keeping", "A shared album for the family"),
    "drive": (screen_drive, "Free your phone's storage", "Send chat media to your Google Drive"),
    "events": (screen_events, "Never miss a birthday", "Family dates everyone gets reminded of"),
    "streak": (screen_streak, "Never miss a day", "Streaks that keep everyone close"),
    "voice": (screen_voice, "Say it any way you like", "Voice notes, six effects, free"),
}


# Four screens were written by hand as HTML and live in assets/generated/
# rather than being built by a function here. They are listed so that one
# command re-shoots everything; the value is the page height each was drawn at.
STATIC = {"chats_liquid": 2340, "chat_liquid": 2264, "careshield_liquid": 2280,
          "sounds_minimal": 2280}


def render(name: str) -> Path:
    if name in STATIC:
        html = OUT / f"{name}.html"
        if not html.exists():
            raise SystemExit(f"{html} is missing -- this screen is hand-written, not generated")
        return shoot(html, OUT / f"{name}.png", W, STATIC[name])
    builder, _, _ = SCREENS[name]
    OUT.mkdir(parents=True, exist_ok=True)
    html = OUT / f"{name}.html"
    png = OUT / f"{name}.png"
    html.write_text(builder(), encoding="utf-8")
    return shoot(html, png, W, H)


def main() -> int:
    wanted = sys.argv[1:] or list(SCREENS) + list(STATIC)
    unknown = [n for n in wanted if n not in SCREENS and n not in STATIC]
    if unknown:
        print(f"unknown screen(s): {', '.join(unknown)}. "
              f"Available: {', '.join(list(SCREENS) + list(STATIC))}")
        return 1
    failed = 0
    for name in wanted:
        try:
            png = render(name)
            size = png.stat().st_size // 1024 if png.exists() else 0
        except SystemExit as exc:            # shoot() refuses bad pages loudly
            print(f"  {name:12} FAILED  {exc}")
            failed += 1
            continue
        failed += 0 if size else 1
        print(f"  {name:12} {'OK' if size else 'FAILED'}  {size} KB")
    if failed:
        print(f"\n{failed} screen(s) FAILED -- do not build cards from this run")
        return 1
    print(f"\nwritten to {OUT.relative_to(ROOT)}/")
    print("next: tools/make_card.py <png> \"Headline\" \"Subhead\" <name>   (no --phone: these are rendered)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
