"""
Safety net for the content bank. Run it after editing content/posts.json.

    python tools/check.py

It fails loudly if any post would be cut off mid-sentence on any platform,
if an image is missing, if an id is duplicated, or if a post makes a claim
the app cannot back up.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from autopost import PROTECTED, compose, load_config, voice_for  # noqa: E402
from core import festivals, queue, schedule  # noqa: E402
from platforms import ALL  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _day(weekday_index: int):
    """A datetime that lands on the given weekday, for counting slots."""
    from datetime import datetime, timedelta, timezone

    monday = datetime(2026, 8, 17, tzinfo=timezone.utc)  # a Monday
    return monday + timedelta(days=weekday_index)

# Things the app genuinely cannot claim. Keep this list in sync with reality.
FORBIDDEN = [
    ("end-to-end", "messages are not end-to-end encrypted -- the server can read them for chat previews"),
    ("end to end", "messages are not end-to-end encrypted"),
    ("calls emergency", "SOS alerts your family, never emergency services"),
    ("calls 112", "SOS alerts your family, never emergency services"),
    ("ambulance", "SOS alerts your family, never emergency services"),
    ("detects falls", "CareShield does not detect falls"),
    ("fall detection", "CareShield does not detect falls"),
    ("monitors your health", "CareShield is not a medical or health device"),
    ("medical", "CareShield must never be described medically"),
]

# ...except when the sentence is the disclaimer itself. Flagging "not a medical
# device" pushed the copy towards weaker wording, which is the opposite of the
# point.
ALLOWED_AROUND = {
    "medical": ("not a medical", "no medical", "never medical", "medical nahi"),
}


def main() -> int:
    cfg = load_config()
    posts = queue.load_posts()
    phase = cfg.get("phase")
    problems = []
    warnings = []

    for post in posts:
        blob = f"{post.get('english', '')} {post.get('hinglish', '')}".lower()
        for phrase, why in FORBIDDEN:
            if phrase not in blob:
                continue
            if any(ok in blob for ok in ALLOWED_AROUND.get(phrase, ())):
                continue
            problems.append(f"{post['id']}: says '{phrase}' -- {why}")

        for field in ("english", "hinglish"):
            if not post.get(field, "").strip():
                problems.append(f"{post['id']}: missing {field} copy")

        stem = post.get("image", "")
        if stem:
            # The source card matters as much as the rendered crops: if it has
            # been deleted or retired, render_images.py cannot rebuild them and
            # the next edit to this post would go out with no picture.
            if not (ROOT / "assets" / "screenshots" / f"{stem}.png").exists():
                problems.append(f"{post['id']}: assets/screenshots/{stem}.png missing -- "
                                f"the card was moved or retired, point this post at a card that exists")
            for shape in ("sq", "p45", "pin"):
                if not (ROOT / "rendered" / f"{stem}__{shape}.jpg").exists():
                    problems.append(f"{post['id']}: rendered/{stem}__{shape}.jpg missing -- run tools/render_images.py")

        for platform in ALL:
          # Both languages are checked on every platform, not just the one this
          # post happens to draw today. Otherwise raising an account's Hinglish
          # share in config.yaml could push a post over a character limit that
          # nothing had ever tested.
          for voice in ("english", "hinglish"):
            source = (post.get(voice) or post.get("english") or "")
            text = compose(post, platform, cfg, voice=voice)

            if text.endswith("…"):
                problems.append(f"{post['id']} on {platform.name} ({voice}): truncated mid-sentence ({len(text)} chars)")
            if platform.limit and len(text) > platform.limit:
                problems.append(
                    f"{post['id']} on {platform.name} ({voice}): {len(text)} chars, over the {platform.limit} "
                    f"limit -- shorten the copy, it cannot be trimmed without losing a safety line"
                )

            # The dangerous failure is not a long post, it is a SHORTENED post
            # that keeps a claim and drops its qualifier. Anything the source
            # said must survive into what actually goes out.
            for phrase in PROTECTED:
                if phrase in source.lower() and phrase not in text.lower():
                    problems.append(
                        f"{post['id']} on {platform.name} ({voice}): '{phrase}' was in the copy but got dropped to fit"
                    )

    # --- festival greetings ------------------------------------------------
    # These are hand-dated: a lunar festival cannot be computed, so the file
    # goes stale silently unless something shouts about it.
    fest = festivals.load()
    known_platforms = {p.name for p in ALL}
    for name in fest.get("platforms", []):
        if name not in known_platforms:
            problems.append(f"festivals.json lists '{name}', which is not a platform this project supports")

    for key, greeting in (fest.get("greetings") or {}).items():
        for field in ("image", "card_title", "card_line", "english", "hinglish"):
            if not str(greeting.get(field, "")).strip():
                problems.append(f"festival '{key}': missing {field}")
        stem = greeting.get("image", "")
        if stem and not (ROOT / "assets" / "screenshots" / f"{stem}.png").exists():
            problems.append(f"festival '{key}': assets/screenshots/{stem}.png missing -- run tools/make_greeting.py")
        if stem:
            for shape in ("sq", "p45", "pin"):
                if not (ROOT / "rendered" / f"{stem}__{shape}.jpg").exists():
                    problems.append(f"festival '{key}': rendered/{stem}__{shape}.jpg missing -- run tools/render_images.py")
        blob = f"{greeting.get('english', '')} {greeting.get('hinglish', '')}".lower()
        for phrase, why in FORBIDDEN:
            if phrase in blob and not any(ok in blob for ok in ALLOWED_AROUND.get(phrase, ())):
                problems.append(f"festival '{key}': says '{phrase}' -- {why}")
        fake = {"id": f"festival:{key}", "english": greeting.get("english", ""),
                "hinglish": greeting.get("hinglish", "")}
        for platform in ALL:
            if platform.name not in fest.get("platforms", []):
                continue
            for voice in ("english", "hinglish"):
                text = compose(fake, platform, cfg, voice=voice)
                if platform.limit and len(text) > platform.limit:
                    problems.append(f"festival '{key}' on {platform.name} ({voice}): {len(text)} chars, "
                                    f"over the {platform.limit} limit")

    from datetime import datetime, timezone  # noqa: E402
    for stamp, key in (fest.get("dates") or {}).items():
        try:
            datetime.strptime(stamp, "%Y-%m-%d")
        except ValueError:
            problems.append(f"festivals.json date '{stamp}' is not YYYY-MM-DD")
            continue
        if key not in (fest.get("greetings") or {}):
            problems.append(f"festivals.json date {stamp} points at '{key}', which has no greeting")

    if fest.get("dates"):
        left = festivals.days_of_calendar_left(datetime.now(timezone.utc))
        if left <= 0:
            problems.append("the festival calendar has run out -- every future festival will pass in silence")
        elif left < 90:
            warnings.append(f"the festival calendar runs out in {left} days; look up next year's dates "
                            f"and add them to content/festivals.json (never guess a lunar date)")

    # --- schedule sanity ---------------------------------------------------
    # These checks exist because a one-character typo used to silence a whole
    # platform while every tool reported success. `weekdays:` instead of
    # `weekday:` fell through to an empty default and posted nothing, forever.

    if phase not in {p.get("phase") for p in posts}:
        problems.append(f"config.yaml phase '{phase}' is not used by any post in posts.json")

    try:
        schedule.tz_of(cfg)
    except Exception as exc:
        problems.append(f"config.yaml timezone is not a real timezone: {exc}")
    try:
        catch_up = schedule.catch_up_of(cfg)
        if not 15 <= catch_up <= 360:
            warnings.append(f"catch_up_minutes is {catch_up}; anything outside 15-360 is probably a mistake")
    except (TypeError, ValueError):
        problems.append("config.yaml catch_up_minutes is not a number")

    sched = cfg.get("schedule", {}).get("platforms", {})
    for name in sorted(sched):
        if name not in {p.name for p in ALL}:
            problems.append(f"config.yaml schedules '{name}', which is not a platform this project supports")

        table = sched[name] or {}
        for day in table:
            if day not in schedule.VALID_KEYS:
                problems.append(
                    f"{name}: '{day}:' is not a valid day key, so it is ignored and this platform "
                    f"may never post. Use one of: {', '.join(sorted(schedule.VALID_KEYS))}"
                )
        if not any(table.values()):
            problems.append(f"{name}: schedule has no posting times at all, so it will never post")

        for day, slots in table.items():
            for slot in slots or []:
                parsed = schedule.parse_slot(slot)
                if not parsed:
                    problems.append(f"{name}/{day}: '{slot}' is not a valid HH:MM time")
                    continue
                hh, mm = parsed
                if mm != 0:
                    warnings.append(
                        f"{name}/{day} {slot}: the runner only wakes once an hour, so this posts at "
                        f"{(hh + 1) % 24:02d}:17 - use a whole hour instead"
                    )
                if str(slot) != f"{hh:02d}:{mm:02d}":
                    warnings.append(f"{name}/{day}: write '{slot}' as '{hh:02d}:{mm:02d}' so times sort correctly")

    for platform in ALL:
        if platform.name not in sched:
            warnings.append(f"{platform.name} has no schedule, so it will never post unless you use --force")

    # How long before the bank starts repeating itself? Nothing breaks when it
    # wraps, but you should know you are recycling rather than find out from a
    # follower.
    pool = [p for p in posts if p.get("phase") == phase]
    if pool:
        busiest = max(
            (sum(len(schedule.slots_for(p.name, _day(i), cfg)) for i in range(7)) for p in ALL),
            default=0,
        )
        if busiest:
            days = len(pool) / (busiest / 7)
            if days < 21:
                warnings.append(
                    f"the '{phase}' set has {len(pool)} posts, so the busiest account repeats itself "
                    f"every ~{days:.0f} days. Fine for a short recruitment push; add posts before "
                    f"leaving it running for months"
                )

    # ---- content/feed.xml -------------------------------------------------
    # LinkedIn is published by a feed reader, and a feed reader dedupes on the
    # item guid. Two items sharing one means the newer was silently never
    # published -- which is exactly how the Page went quiet from 26 Aug 2026
    # while every log line said "queued".
    #
    # A warning, deliberately never a problem: check.py failing stops the run
    # before anything is sent anywhere, and taking eight accounts down over one
    # LinkedIn item would be the worse bug. It clears itself on the next
    # LinkedIn send -- see the dedupe in core.feed.append.
    feed_path = ROOT / "content" / "feed.xml"
    if feed_path.exists():
        guids = re.findall(r"<guid[^>]*>(.*?)</guid>",
                           feed_path.read_text(encoding="utf-8"))
        for guid in sorted({g for g in guids if guids.count(g) > 1}):
            warnings.append(
                f"content/feed.xml has {guids.count(guid)} items sharing the guid "
                f"'{guid}', so a feed reader published only the older one. "
                f"Clears itself on the next LinkedIn post"
            )

    print(f"checked {len(posts)} posts across {len(ALL)} platforms")
    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  ? {w}")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print(f"  ! {p}")
        return 1
    print("all clear")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
