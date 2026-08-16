"""
Renders each festival greeting as a chat you have just opened.

    python tools/make_festival_chat.py             # every festival
    python tools/make_festival_chat.py diwali      # one

A poster says "Happy Diwali". A chat screen says somebody in your family
remembered you today -- which is the thing the app is actually for. So the
greeting is delivered the way a real one arrives: a message from a person,
sitting in the app, with a reply underneath.

The cast is invented (Meera, Aarav, Priya, Rohan, Kabir, Ananya) and so are
the words. Nothing here is lifted from a real phone -- do not change that.

Output goes to assets/generated/festival_<key>.png, then straight through
tools/make_card.py into the usual store card, so a festival post sits beside
the feature posts instead of looking like a different brand.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.shoot import shoot  # noqa: E402

OUT = ROOT / "assets" / "generated"
FESTIVALS = ROOT / "content" / "festivals.json"

# 1080x2264 is the phone box's exact aspect, so make_card.py scales it without
# cropping the composer off the bottom.
W, H = 1080, 2264

CSS = """
@font-face{font-family:P;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf')}
@font-face{font-family:P;font-weight:500;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf')}
@font-face{font-family:P;font-weight:700;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf')}
@font-face{font-family:E;src:url('/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf')}
*{margin:0;padding:0;box-sizing:border-box;-webkit-font-smoothing:antialiased}
body{width:1080px;height:2264px;font-family:P,E,sans-serif;background:#0B0B0D;color:#F2EFEA;
     overflow:hidden;position:relative}
.bar{height:150px;background:#131316;display:flex;align-items:center;gap:28px;padding:0 34px;
     border-bottom:1px solid #FFFFFF12}
.bar svg{width:48px;height:48px;stroke:#F2EFEA;fill:none;stroke-width:2.6}
.bar svg[style]{fill:#F2EFEA !important}
.av{width:88px;height:88px;border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-size:36px;font-weight:600;color:#fff;flex:none}
.who{flex:1}.who b{display:block;font-size:40px;font-weight:700}
.who span{font-size:27px;color:#9A948C}
.day{display:flex;justify-content:center;margin:34px 0 10px}
.day span{background:#1C1C20;border:1px solid #FFFFFF14;border-radius:34px;padding:12px 40px;font-size:28px;font-weight:600;color:#C9C3BA}
.wrap{padding:0 34px}
.in,.out{max-width:800px;border-radius:34px;padding:30px 34px;margin-top:26px;
         border:1px solid #FFFFFF14;font-size:38px;line-height:1.42}
.in{background:#1B1B1F;border-top-left-radius:12px}
.out{background:#3A2A12;border-top-right-radius:12px;margin-left:auto;max-width:640px;border-color:#E0A63A33}
.mt{font-size:24px;color:#8F8981;margin-top:14px;display:flex;gap:10px;align-items:center}
.out .mt{justify-content:flex-end}
.mt svg{width:30px;height:20px;stroke:#7FD7F5;fill:none;stroke-width:3}
.em{font-family:P,E,sans-serif}
.pic{max-width:800px;border-radius:34px;border-top-left-radius:12px;margin-top:26px;overflow:hidden;
     background:#1B1B1F;border:1px solid #FFFFFF14;padding:10px}
.pic img{display:block;width:100%;height:520px;object-fit:cover;border-radius:26px}
.pic .cap{padding:22px 24px 10px;font-size:38px;line-height:1.42}
.pic .mt{padding:0 24px 12px}
.composer{position:absolute;left:0;right:0;bottom:0;height:150px;display:flex;align-items:center;
          gap:26px;padding:0 34px}
.field{flex:1;height:100px;border-radius:50px;background:#1B1B1F;border:1px solid #FFFFFF14;
       display:flex;align-items:center;padding:0 36px;font-size:34px;color:#8F8981}
.mic{width:106px;height:106px;border-radius:50%;background:#E0A63A;display:flex;
     align-items:center;justify-content:center;flex:none}
.mic svg{width:50px;height:50px;stroke:#3A2A08;fill:none;stroke-width:2.6}
"""

TICKS = ('<svg viewBox="0 0 26 18"><path d="M2 10l4.5 4.5L14 5M11 12l2 2 8-9"/></svg>')


def page(chat: dict) -> str:
    initial = chat["from"][0]
    # A photo message: the picture, then the words underneath in the same
    # bubble, the way the app shows an image with a caption.
    photo_path = ROOT / "assets" / "photos" / f"{chat['photo']}" if chat.get("photo") else None
    if photo_path and photo_path.exists():
        photo = (f'<div class="pic em"><img src="file://{photo_path}">'
                 f'<div class="cap">{chat["message"]}</div>'
                 f'<div class="mt">{chat.get("time", "08:14")}</div></div>')
    else:
        photo = (f'<div class="in em">{chat["message"]}'
                 f'<div class="mt">{chat.get("time", "08:14")}</div></div>')
    earlier = ""
    if chat.get("earlier") and not (photo_path and photo_path.exists()):
        e = chat["earlier"]
        earlier = f"""<div class="day"><span>Yesterday</span></div>
<div class="wrap">
  <div class="out em">{e['out']}<div class="mt">{e.get('out_time', '21:10')} {TICKS}</div></div>
  <div class="in em">{e['in']}<div class="mt">{e.get('in_time', '21:14')}</div></div>
</div>"""
    return f"""<!DOCTYPE html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class="bar">
  <svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7"/></svg>
  <span class="av" style="background:{chat.get('colour', '#6E76D8')}">{initial}</span>
  <span class="who"><b>{chat['from']}</b><span>online</span></span>
  <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>
  <svg viewBox="0 0 24 24" style="fill:#1E1B16;stroke:none"><path d="M5.2 3.6h3.9l1.9 4.8-2.8 1.9a12.4 12.4 0 005.5 5.5l1.9-2.8 4.8 1.9v3.9a1.8 1.8 0 01-1.8 1.8A16.8 16.8 0 013.4 5.4a1.8 1.8 0 011.8-1.8z"/></svg>
</div>
{earlier}
<div class="day"><span>Today</span></div>
<div class="wrap">
  {photo}
  <div class="out em">{chat['reply']}<div class="mt">{chat.get('reply_time', '08:16')} {TICKS}</div></div>
</div>
<div class="composer">
  <span class="field">Message</span>
  <span class="mic"><svg viewBox="0 0 24 24"><rect x="9" y="2.5" width="6" height="11" rx="3"/>
    <path d="M5.5 11a6.5 6.5 0 0013 0M12 17.5V21"/></svg></span>
</div>
</body></html>"""


def main() -> int:
    data = json.loads(FESTIVALS.read_text(encoding="utf-8"))
    greetings = data["greetings"]
    wanted = sys.argv[1:] or [k for k, g in greetings.items() if g.get("chat")]

    missing = [k for k in wanted if not greetings.get(k, {}).get("chat")]
    if missing:
        print(f"no chat written yet for: {', '.join(missing)}")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    for key in wanted:
        g = greetings[key]
        html = OUT / f"festival_{key}.html"
        html.write_text(page(g["chat"]), encoding="utf-8")
        png = shoot(html, OUT / f"festival_{key}.png", W, H)

        subprocess.run([sys.executable, str(ROOT / "tools" / "make_card.py"), str(png),
                        g["card_title"], g["card_line"], g["image"]],
                       check=True, capture_output=True)
        print(f"  {key:14} -> assets/screenshots/{g['image']}.png")

    print(f"\n{len(wanted)} festival card(s). next: python tools/render_images.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
