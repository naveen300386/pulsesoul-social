"""
An RSS feed of posts, for platforms this project cannot reach directly.

LinkedIn only lets a registered legal organization post to a company Page
through its API. It does, however, let approved partners do it -- and Zapier
is one. So instead of calling LinkedIn, the runner writes the post here, the
file is pushed to the repo like everything else, and a Zap reads the feed and
publishes to the PulseSoul Page.

The feed is a queue with a memory: it keeps the most recent MAX_ITEMS entries
so a reader that was offline for a day still finds what it missed, and each
item carries a stable guid so a retry of the same send is not published twice.

THE GUID IS THE WHOLE GAME HERE, and it was wrong until 30 Aug 2026. It used
to be a hash of the post text alone, which sounds right -- same words, same
id -- and quietly killed the LinkedIn Page.

The content bank cycles. Twelve tester posts, one LinkedIn slot a weekday, so
on 26 Aug the queue came back around to the post it had already sent on 15
Aug. Identical text, therefore identical guid. Zapier's RSS trigger dedupes on
guid, decided it had seen that item eleven days ago, and skipped it. Not an
error, not a retry, nothing in any log: the Zap simply had nothing new to do.
Every post after that was also a repeat, so the Page would have stayed silent
for good while this project cheerfully recorded "queued in feed.xml" each day.

So the guid now identifies ONE SEND: post, text, and the date it went out.
Same slot retried an hour later -> same guid -> still deduped, which is the
property worth keeping. Same post coming round again next cycle -> new date ->
new guid -> published. LinkedIn posts at most once a day and catch_up_minutes
cannot push a slot past midnight, so the date can never split one send in two.

NEVER regenerate the guids of items already in the feed. A reader that has
seen them would treat every one as new and publish the lot in a burst.
"""
import hashlib
import html
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "content" / "feed.xml"
MAX_ITEMS = 30

HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>PulseSoul</title>
<link>https://pulsesoul.app</link>
<description>Posts queued for the PulseSoul LinkedIn Page</description>
"""
FOOTER = "</channel></rss>\n"


RAW = re.compile(r"^https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)$")


def cdn_url(url: str | None) -> str | None:
    """Serve the feed's image from GitHub Pages, not raw.githubusercontent.

    raw.githubusercontent.com rate-limits by IP, and Zapier goes out through
    shared egress addresses already near that ceiling. The LinkedIn step
    fetches the enclosure, gets GitHub's HTTP 429 "Too Many Requests" page
    instead of a JPEG, and the Zap fails with an error that reads like
    LinkedIn's fault. It is not.

    Pages serves the same files from the same repo over Fastly, with no such
    limit, and it is first-party -- no third-party mirror to go down.

    jsDelivr was the obvious answer and does not work here: it clones the
    whole repository to mirror it, and at ~430 MB this one is past what it
    will take. It answers "Failed to fetch ... from GitHub". Do not switch
    back to it without checking that first.

    REQUIRES Pages to be switched on: Settings -> Pages -> Deploy from a
    branch -> main / root. Without it these URLs 404.

    Only the feed uses this. Instagram and Threads keep fetching from GitHub
    directly, because they work and one fetch an hour is nowhere near a limit.
    """
    if not url:
        return url
    m = RAW.match(url)
    if not m:
        return url
    owner, repo, _ref, path = m.groups()
    return f"https://{owner.lower()}.github.io/{repo}/{path}"


def _existing_items(text: str) -> list[str]:
    return re.findall(r"<item>.*?</item>", text, re.S)


def _first_line(text: str) -> str:
    line = next((p.strip() for p in text.split("\n") if p.strip()), "PulseSoul")
    return line[:110]


def append(post_id: str, text: str, image_url: str | None, when: datetime | None = None) -> Path:
    """Add one post to the feed and drop the oldest beyond MAX_ITEMS."""
    when = when or datetime.now(timezone.utc)
    image_url = cdn_url(image_url)
    digest = hashlib.md5(text.encode()).hexdigest()[:8]
    # The date is what stops a cycling bank looking like a repeat. See above.
    guid = f"pulsesoul-{post_id}-{digest}-{when:%Y%m%d}"

    parts = [
        "<item>",
        f"<title>{html.escape(_first_line(text))}</title>",
        f"<guid isPermaLink=\"false\">{guid}</guid>",
        f"<pubDate>{when:%a, %d %b %Y %H:%M:%S +0000}</pubDate>",
        f"<link>https://pulsesoul.app</link>",
        f"<description>{html.escape(text)}</description>",
    ]
    if image_url:
        # Two spellings of the same thing: readers differ on which they map.
        parts.append(f"<enclosure url=\"{html.escape(image_url)}\" type=\"image/jpeg\" length=\"0\"/>")
        parts.append(f"<image>{html.escape(image_url)}</image>")
    parts.append("</item>")
    item = "\n".join(parts)

    old = _existing_items(FEED.read_text(encoding="utf-8")) if FEED.exists() else []

    # A retry of a send already in the feed changes nothing. Appending a second
    # copy under the same guid would leave the feed self-contradicting, and a
    # reader that maps on something other than guid could publish it twice.
    if any(f"<guid isPermaLink=\"false\">{guid}</guid>" in existing for existing in old):
        return FEED

    # Drop anything older that shares a guid with something newer -- including
    # the collisions the old content-only guid left behind. Newest wins,
    # because that is the one a reader has not published yet.
    seen, kept = set(), []
    for existing in old:
        found = re.search(r"<guid[^>]*>(.*?)</guid>", existing, re.S)
        key = found.group(1) if found else existing
        if key in seen or key == guid:
            continue
        seen.add(key)
        kept.append(existing)

    items = [item] + kept[: MAX_ITEMS - 1]

    FEED.parent.mkdir(parents=True, exist_ok=True)
    FEED.write_text(HEADER + "\n".join(items) + "\n" + FOOTER, encoding="utf-8")
    return FEED
