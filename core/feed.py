"""
An RSS feed of posts, for platforms this project cannot reach directly.

LinkedIn only lets a registered legal organization post to a company Page
through its API. It does, however, let approved partners do it -- and Zapier
is one. So instead of calling LinkedIn, the runner writes the post here, the
file is pushed to the repo like everything else, and a Zap reads the feed and
publishes to the PulseSoul Page.

The feed is a queue with a memory: it keeps the most recent MAX_ITEMS entries
so a reader that was offline for a day still finds what it missed, and each
item carries a stable guid so no reader posts the same item twice.
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


def _existing_items(text: str) -> list[str]:
    return re.findall(r"<item>.*?</item>", text, re.S)


def _first_line(text: str) -> str:
    line = next((p.strip() for p in text.split("\n") if p.strip()), "PulseSoul")
    return line[:110]


def append(post_id: str, text: str, image_url: str | None, when: datetime | None = None) -> Path:
    """Add one post to the feed and drop the oldest beyond MAX_ITEMS."""
    when = when or datetime.now(timezone.utc)
    digest = hashlib.md5(text.encode()).hexdigest()[:8]
    guid = f"pulsesoul-{post_id}-{digest}"

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
    items = [item] + old[: MAX_ITEMS - 1]

    FEED.parent.mkdir(parents=True, exist_ok=True)
    FEED.write_text(HEADER + "\n".join(items) + "\n" + FOOTER, encoding="utf-8")
    return FEED
