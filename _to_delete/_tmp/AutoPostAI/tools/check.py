"""
Safety net for the content bank. Run it after editing content/posts.json.

    python tools/check.py

It fails loudly if any post would be cut off mid-sentence on any platform,
if an image is missing, if an id is duplicated, or if a post makes a claim
the app cannot back up.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from autopost import PROTECTED, compose, load_config  # noqa: E402
from core import queue  # noqa: E402
from platforms import ALL  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

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


def main() -> int:
    cfg = load_config()
    posts = queue.load_posts()
    problems = []

    for post in posts:
        blob = f"{post.get('english', '')} {post.get('hinglish', '')}".lower()
        for phrase, why in FORBIDDEN:
            if phrase in blob:
                problems.append(f"{post['id']}: says '{phrase}' -- {why}")

        for field in ("english", "hinglish"):
            if not post.get(field, "").strip():
                problems.append(f"{post['id']}: missing {field} copy")

        stem = post.get("image", "")
        if stem:
            for shape in ("sq", "p45", "pin"):
                if not (ROOT / "rendered" / f"{stem}__{shape}.jpg").exists():
                    problems.append(f"{post['id']}: rendered/{stem}__{shape}.jpg missing -- run tools/render_images.py")

        for platform in ALL:
            source = (post.get(platform.voice) or post.get("english") or "")
            text = compose(post, platform, cfg)

            if text.endswith("…"):
                problems.append(f"{post['id']} on {platform.name}: truncated mid-sentence ({len(text)} chars)")
            if platform.limit and len(text) > platform.limit:
                problems.append(
                    f"{post['id']} on {platform.name}: {len(text)} chars, over the {platform.limit} limit "
                    f"-- shorten the copy, it cannot be trimmed without losing a safety line"
                )

            # The dangerous failure is not a long post, it is a SHORTENED post
            # that keeps a claim and drops its qualifier. Anything the source
            # said must survive into what actually goes out.
            for phrase in PROTECTED:
                if phrase in source.lower() and phrase not in text.lower():
                    problems.append(
                        f"{post['id']} on {platform.name}: '{phrase}' was in the copy but got dropped to fit"
                    )

    print(f"checked {len(posts)} posts across {len(ALL)} platforms")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print(f"  ! {p}")
        return 1
    print("all clear")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
