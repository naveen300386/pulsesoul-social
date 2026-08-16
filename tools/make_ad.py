"""
Builds a daily advertisement poster -- the kind of creative a marketing team
would put out, not a screenshot in a frame.

    python tools/make_ad.py                 # every ad in content/ads.json
    python tools/make_ad.py launch          # one

The layout is a proper ad: brand block, a big headline, a short list of
benefits with icons, the app on a device, a photo of real people, and a clear
call to action with a QR code and the store badge. It is rendered from HTML
so the type, icons and layout behave like a design tool's output, then shot
with headless Chromium at 1080x1350.

Rules this file keeps:
  * Photos come from assets/photos/ -- licensed stock or the owner's own.
    Nothing here draws a person, a scene or an ornament in code.
  * The device shows a REAL rendered app screen from assets/generated/.
  * The store badge is Google's own artwork (assets/brand/google-play.png).
    If it is missing the layout falls back to a plain text button rather than
    a hand-drawn imitation, which Google's brand rules forbid anyway.
  * Icons are the same line icons the app screens use.

Each ad in content/ads.json is a small spec:
    headline, sub, features[], screen, photo, cta, theme
"""
import base64
import io
import json
import sys
from pathlib import Path

import qrcode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.shoot import shoot  # noqa: E402

ADS = ROOT / "content" / "ads.json"
GEN = ROOT / "assets" / "generated"
OUT_DIR = ROOT / "assets" / "screenshots"
PHOTOS = ROOT / "assets" / "photos"
BRAND = ROOT / "assets" / "brand"

W, H = 1080, 1350

ICONS = {
    "chat": '<rect x="2.5" y="4" width="19" height="14" rx="3"/><path d="M7 21.2l1.2-3.2h3.4z"/>',
    "call": '<path d="M5.2 3.6h3.9l1.9 4.8-2.8 1.9a12.4 12.4 0 005.5 5.5l1.9-2.8 4.8 1.9v3.9a1.8 1.8 0 01-1.8 1.8A16.8 16.8 0 013.4 5.4a1.8 1.8 0 011.8-1.8z"/>',
    "shield": '<path d="M12 2.5l8 3.2v6.1c0 5.3-3.4 8.6-8 9.7-4.6-1.1-8-4.4-8-9.7V5.7z"/>',
    "heart": '<path d="M12 20.5S3.5 15 3.5 9.4A4.4 4.4 0 0112 7.6a4.4 4.4 0 018.5 1.8c0 5.6-8.5 11.1-8.5 11.1z"/>',
    "photo": '<rect x="3" y="5" width="18" height="14" rx="3"/><circle cx="9" cy="10" r="1.6"/><path d="M3 16l5-4 4 3 3-2 6 4"/>',
    "calendar": '<rect x="3" y="5" width="18" height="17" rx="3"/><path d="M8 2.5v5M16 2.5v5M3 11h18"/>',
    "pin": '<path d="M12 21s-6.5-6.2-6.5-11a6.5 6.5 0 0113 0c0 4.8-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/>',
    "mic": '<rect x="9" y="2.5" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0013 0M12 17.5V21"/>',
    "cloud": '<path d="M6 18a4 4 0 010-8 6 6 0 0111.5-1.5A3.5 3.5 0 0119 18z"/>',
    "sound": '<path d="M9 18V6l11-2v12"/><circle cx="6.5" cy="18" r="3"/><circle cx="17.5" cy="16" r="3"/>',
    "check": '<path d="M5 13l4.5 4.5L19 7"/>',
    "lock": '<rect x="4" y="10" width="16" height="11" rx="3"/><path d="M8 10V7a4 4 0 018 0v3"/>',
    "free": '<circle cx="12" cy="12" r="9"/><path d="M8 12h8M12 8v8"/>',
}

THEMES = {
    # light poster, brand gradient accents -- the Familiqo reference
    "light": {"bg": "#FBF8F3", "ink": "#1B1723", "muted": "#5E5769", "card": "#FFFFFF",
              "a": "#EC4899", "b": "#F97316", "c": "#8B5CF6", "chip": "#F3EAF7"},
    # dark poster, same accents
    "dark": {"bg": "#0E0C12", "ink": "#F6F3EE", "muted": "#B7B0C0", "card": "#17141D",
             "a": "#EC4899", "b": "#F97316", "c": "#8B5CF6", "chip": "#221C2A"},
}


def data_url(path: Path, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def qr_data_url(text: str, dark: str, light: str) -> str:
    q = qrcode.QRCode(box_size=10, border=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
    q.add_data(text)
    q.make(fit=True)
    img = q.make_image(fill_color=dark, back_color=light).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def icon_svg(name: str, colour: str) -> str:
    return (f'<svg viewBox="0 0 24 24" fill="none" stroke="{colour}" stroke-width="2.2" '
            f'stroke-linecap="round" stroke-linejoin="round">{ICONS.get(name, ICONS["check"])}</svg>')


def page(ad: dict) -> str:
    t = THEMES[ad.get("theme", "light")]
    icon = data_url(BRAND / "icon.png", "image/png")
    screen = data_url(GEN / f"{ad['screen']}.png", "image/png")
    photo_path = PHOTOS / ad["photo"] if ad.get("photo") else None
    photo = data_url(photo_path, "image/jpeg") if photo_path and photo_path.exists() else ""
    badge_path = BRAND / "google-play.png"
    badge = data_url(badge_path, "image/png") if badge_path.exists() else ""
    qr = qr_data_url(ad.get("link", "https://pulsesoul.app"), t["ink"], t["card"])

    feats = "".join(
        f'<li><span class="ic">{icon_svg(f["icon"], t["a"])}</span>'
        f'<span><b>{f["title"]}</b><small>{f["sub"]}</small></span></li>'
        for f in ad["features"][:4])

    badge_html = (f'<img class="badge" src="{badge}">' if badge else
                  f'<span class="badge-txt">GET IT ON<br><b>Google Play</b></span>')

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:P;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf')}}
@font-face{{font-family:P;font-weight:500;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf')}}
@font-face{{font-family:P;font-weight:600;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-SemiBold.ttf')}}
@font-face{{font-family:P;font-weight:700;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf')}}
@font-face{{font-family:P;font-weight:800;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-ExtraBold.ttf')}}
*{{margin:0;padding:0;box-sizing:border-box;-webkit-font-smoothing:antialiased}}
body{{width:{W}px;height:{H}px;overflow:hidden;position:relative;font-family:P,sans-serif;
     background:{t['bg']};color:{t['ink']}}}
/* soft brand wash top-right, behind the photo */
.wash{{position:absolute;right:-220px;top:-260px;width:820px;height:820px;border-radius:50%;
      background:radial-gradient(closest-side,{t['a']}22,{t['b']}14 55%,transparent 72%)}}
.wash2{{position:absolute;left:-260px;bottom:-300px;width:760px;height:760px;border-radius:50%;
      background:radial-gradient(closest-side,{t['c']}1E,transparent 70%)}}

.brand{{position:absolute;left:64px;top:60px;display:flex;align-items:center;gap:20px}}
.brand img{{width:76px;height:76px;border-radius:22px;box-shadow:0 8px 24px #0000001f}}
.brand .w{{font-size:50px;font-weight:700;letter-spacing:-.5px;
          background:linear-gradient(95deg,{t['a']},{t['b']});-webkit-background-clip:text;
          -webkit-text-fill-color:transparent}}
.brand .tg{{display:block;font-size:22px;color:{t['muted']};font-weight:500;letter-spacing:.2px;margin-top:-4px}}

.photo{{position:absolute;right:0;top:0;width:520px;height:560px;overflow:hidden;
       border-bottom-left-radius:260px;box-shadow:0 30px 70px #00000026}}
.photo img{{width:100%;height:100%;object-fit:cover;display:block}}
.photo::after{{content:'';position:absolute;inset:0;
              background:linear-gradient(200deg,transparent 55%,{t['bg']} 100%)}}

.head{{position:absolute;left:64px;top:220px;width:520px}}
.head h1{{font-size:78px;line-height:1.02;font-weight:800;letter-spacing:-1.5px}}
.head h1 em{{font-style:normal;background:linear-gradient(95deg,{t['a']},{t['b']});
            -webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.head p{{margin-top:20px;font-size:27px;line-height:1.38;color:{t['muted']};font-weight:500;max-width:470px}}

ul{{position:absolute;left:64px;top:660px;width:500px;list-style:none;display:flex;flex-direction:column;gap:24px}}
li{{display:flex;align-items:center;gap:22px}}
.ic{{width:66px;height:66px;border-radius:20px;background:{t['chip']};display:flex;align-items:center;
    justify-content:center;flex:none}}
.ic svg{{width:34px;height:34px}}
li b{{display:block;font-size:29px;font-weight:600}}
li small{{display:block;font-size:22px;color:{t['muted']};margin-top:2px}}

.device{{position:absolute;right:88px;top:486px;width:392px;height:640px;padding:14px;border-radius:64px 64px 0 0;
        background:linear-gradient(160deg,#2a2a30,#0d0d10);box-shadow:0 40px 90px #00000045,0 0 0 1.5px #ffffff22;
        overflow:hidden}}
.device img{{display:block;width:100%;border-radius:50px 50px 0 0}}
.cta{{z-index:2}}

.cta{{position:absolute;left:64px;bottom:64px;right:64px;height:170px;border-radius:40px;
     background:linear-gradient(95deg,{t['a']},{t['b']});display:flex;align-items:center;
     gap:34px;padding:0 40px;box-shadow:0 24px 60px {t['a']}44}}
.cta .qr{{width:126px;height:126px;border-radius:22px;background:{t['card']};padding:10px;flex:none}}
.cta .qr img{{width:100%;height:100%;display:block;image-rendering:pixelated}}
.cta .t{{flex:1;color:#fff}}
.cta .t b{{display:block;font-size:40px;font-weight:700;letter-spacing:-.3px}}
.cta .t span{{display:block;font-size:22px;opacity:.92;margin-top:4px}}
.badge{{height:78px;display:block;flex:none;border-radius:12px}}
.badge-txt{{flex:none;background:#000;color:#fff;border-radius:16px;padding:14px 26px;font-size:16px;
           line-height:1.15;letter-spacing:.5px}}
.badge-txt b{{font-size:30px;font-weight:600;letter-spacing:0}}
.free{{position:absolute;right:88px;top:430px;background:{t['card']};color:{t['ink']};font-size:22px;
      font-weight:600;padding:12px 24px;border-radius:30px;box-shadow:0 10px 30px #00000022;
      display:flex;align-items:center;gap:10px}}
.free i{{width:12px;height:12px;border-radius:50%;background:#22C55E;display:inline-block}}
</style></head><body>
<div class="wash"></div><div class="wash2"></div>
{f'<div class="photo"><img src="{photo}"></div>' if photo else ''}
<div class="brand"><img src="{icon}"><span><span class="w">PulseSoul</span><span class="tg">Never Miss What Matters.</span></span></div>
<div class="head"><h1>{ad['headline']}</h1><p>{ad['sub']}</p></div>
<ul>{feats}</ul>
<div class="free"><i></i>{ad.get('pill', 'Free · No ads · No subscriptions')}</div>
<div class="device"><img src="{screen}"></div>
<div class="cta"><span class="qr"><img src="{qr}"></span>
  <span class="t"><b>{ad.get('cta', 'Download PulseSoul')}</b><span>{ad.get('cta_sub', 'Scan or search “PulseSoul” on Google Play')}</span></span>
  {badge_html}</div>
</body></html>"""


def page_premium(ad: dict) -> str:
    icon = data_url(BRAND / "icon.png", "image/png")
    screen = data_url(GEN / f"{ad['screen']}.png", "image/png")
    photo_path = PHOTOS / ad["photo"] if ad.get("photo") else None
    photo = data_url(photo_path, "image/jpeg") if photo_path and photo_path.exists() else ""
    glow = ad.get("glow", "#E0A63A")
    words = ad.get("words") or []
    words_html = " <i>·</i> ".join(words[:3])
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:P;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf')}}
@font-face{{font-family:P;font-weight:300;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-Light.ttf')}}
@font-face{{font-family:P;font-weight:500;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf')}}
*{{margin:0;padding:0;box-sizing:border-box;-webkit-font-smoothing:antialiased}}
body{{width:{W}px;height:{H}px;overflow:hidden;position:relative;font-family:P,sans-serif;background:#050506;color:#F4F1EC}}
/* the photo, if any, lives in the dark: desaturated, low, fading to black */
.photo{{position:absolute;inset:0;overflow:hidden}}
.photo img{{width:100%;height:100%;object-fit:cover;display:block;filter:saturate(.55) brightness(.42)}}
.photo::after{{content:'';position:absolute;inset:0;
  background:linear-gradient(180deg,#050506 0%,#05050688 30%,#05050666 55%,#050506 88%),
             radial-gradient(60% 50% at 62% 58%,transparent 0%,#050506 100%)}}
/* one light, behind the device */
.light{{position:absolute;left:50%;top:700px;width:1500px;height:1250px;transform:translate(-50%,-50%);
  background:radial-gradient(closest-side,{glow}8a,{glow}2a 45%,transparent 72%)}}
.head{{position:absolute;left:0;right:0;top:118px;text-align:center;padding:0 70px}}
.head h1{{font-size:104px;line-height:1.02;font-weight:300;letter-spacing:-2px}}
.head h1 b{{font-weight:500}}
.head p{{margin-top:26px;font-size:32px;font-weight:300;color:#B9B3AC;letter-spacing:.2px}}
.device{{position:absolute;left:50%;top:436px;width:544px;transform:translateX(-50%);padding:14px;
  border-radius:82px;background:linear-gradient(160deg,#26262b,#0b0b0d);height:620px;overflow:hidden;
  box-shadow:0 0 0 1px {glow}55,0 0 0 2px #ffffff14,0 60px 120px #000000c0,0 20px 40px #000000a0}}
.device img{{display:block;width:100%;border-radius:68px}}
.floor{{position:absolute;left:50%;top:1046px;width:620px;height:70px;transform:translateX(-50%);border-radius:50%;
  background:radial-gradient(closest-side,{glow}55,transparent 70%);filter:blur(10px)}}
.words{{position:absolute;left:0;right:0;top:1092px;text-align:center;font-size:26px;font-weight:300;
  color:#CFC9C1;letter-spacing:.6px}}
.words i{{font-style:normal;color:{glow};padding:0 10px}}
.foot{{position:absolute;left:0;right:0;bottom:50px;display:flex;flex-direction:column;align-items:center;gap:10px}}
.foot .b{{display:flex;align-items:center;gap:14px;font-size:30px;font-weight:400}}
.foot .b img{{width:46px;height:46px;border-radius:14px}}
.foot .s{{font-size:17px;letter-spacing:4.5px;color:#9A948C;font-weight:300}}
.foot .rule{{width:110px;height:1px;background:#3a3733}}
</style></head><body>
{f'<div class="photo"><img src="{photo}"></div>' if photo else ''}
<div class="light"></div>
<div class="head"><h1>{ad['headline']}</h1><p>{ad['sub']}</p></div>
<div class="device"><img src="{screen}"></div>
<div class="floor"></div>
{f'<div class="words">{words_html}</div>' if words else ''}
<div class="foot"><span class="b"><img src="{icon}">PulseSoul</span><span class="rule"></span>
  <span class="s">FREE ON GOOGLE PLAY</span></div>
</body></html>"""


def page_lifestyle(ad: dict) -> str:
    """Photo-first. A real family moment fills the frame; the words sit on it.
    The app appears only as a small floating card, if at all -- the post is
    about the people, and the product is the thing that got them there."""
    icon = data_url(BRAND / "icon.png", "image/png")
    photo_path = PHOTOS / ad["photo"]
    if not photo_path.exists():
        raise SystemExit(f"{photo_path} missing -- download it into assets/photos/ first")
    photo = data_url(photo_path, "image/jpeg")
    screen = data_url(GEN / f"{ad['screen']}.png", "image/png") if ad.get("screen") else ""
    accent = ad.get("accent", "#F0A63A")
    align = ad.get("align", "left")            # left | centre
    focus = ad.get("focus", "50% 40%")         # object-position of the photo
    lines = "".join(f"<span>{l}</span>" for l in ad["headline_lines"])
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:P;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf')}}
@font-face{{font-family:P;font-weight:300;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-Light.ttf')}}
@font-face{{font-family:P;font-weight:500;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf')}}
@font-face{{font-family:P;font-weight:700;src:url('/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf')}}
*{{margin:0;padding:0;box-sizing:border-box;-webkit-font-smoothing:antialiased}}
body{{width:{W}px;height:{H}px;overflow:hidden;position:relative;font-family:P,sans-serif;background:#000;color:#fff}}
.photo{{position:absolute;inset:0}}
.photo img{{width:100%;height:100%;object-fit:cover;object-position:{focus};display:block;
  filter:saturate(1.05) contrast(1.03)}}
/* the words need a floor: darken the bottom, kiss the top so the chip reads */
.photo::after{{content:'';position:absolute;inset:0;
  background:linear-gradient(180deg,#00000066 0%,transparent 22%,transparent 46%,#000000cc 78%,#000000f0 100%)}}
.chip{{position:absolute;left:56px;top:52px;display:flex;align-items:center;gap:14px;
  background:#00000055;border:1px solid #ffffff2e;backdrop-filter:blur(14px);border-radius:40px;padding:10px 24px 10px 12px}}
.chip img{{width:44px;height:44px;border-radius:13px}}
.chip b{{font-size:26px;font-weight:500;letter-spacing:.2px}}
.copy{{position:absolute;left:56px;right:56px;bottom:150px;text-align:{'center' if align=='centre' else 'left'}}}
.copy h1{{font-size:96px;line-height:.98;font-weight:700;letter-spacing:-2.5px;text-shadow:0 6px 30px #00000088}}
.copy h1 span{{display:block}}
.copy h1 span:last-child{{color:{accent}}}
.copy p{{margin-top:26px;font-size:32px;line-height:1.36;font-weight:300;color:#EDE8E1;max-width:{'100%' if align=='centre' else '760px'};
  text-shadow:0 3px 18px #00000088;{'margin-left:auto;margin-right:auto' if align=='centre' else ''}}}
.foot{{position:absolute;left:56px;right:56px;bottom:56px;display:flex;align-items:center;justify-content:space-between}}
.store{{font-size:19px;letter-spacing:4px;color:#CFC9C1;font-weight:300}}
.pill{{background:{accent};color:#141008;font-size:24px;font-weight:600;border-radius:32px;padding:14px 30px;
  box-shadow:0 12px 34px {accent}66}}
.card{{position:absolute;right:56px;top:52px;width:250px;border-radius:30px;overflow:hidden;
  box-shadow:0 30px 70px #000000aa,0 0 0 1px #ffffff2a;transform:rotate(4deg)}}
.card img{{display:block;width:100%}}
</style></head><body>
<div class="photo"><img src="{photo}"></div>
<div class="chip"><img src="{icon}"><b>PulseSoul</b></div>
{f'<div class="card"><img src="{screen}"></div>' if screen and ad.get("card", True) else ''}
<div class="copy"><h1>{lines}</h1><p>{ad['copy']}</p></div>
<div class="foot"><span class="store">FREE ON GOOGLE PLAY</span><span class="pill">{ad.get('cta', 'Download PulseSoul')}</span></div>
</body></html>"""


def main() -> int:
    data = json.loads(ADS.read_text(encoding="utf-8"))
    ads = data["ads"]
    wanted = sys.argv[1:] or list(ads)
    unknown = [k for k in wanted if k not in ads]
    if unknown:
        print(f"unknown ad(s): {', '.join(unknown)}")
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    GEN.mkdir(parents=True, exist_ok=True)
    for key in wanted:
        ad = ads[key]
        html = GEN / f"ad_{key}.html"
        builder = {"premium": page_premium, "lifestyle": page_lifestyle}.get(ad.get("layout"), page)
        html.write_text(builder(ad), encoding="utf-8")
        png = shoot(html, OUT_DIR / f"{ad['image']}.png", W, H)
        print(f"  {key:14} -> {png.relative_to(ROOT)}")
    print(f"\n{len(wanted)} ad(s). next: python tools/render_images.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
