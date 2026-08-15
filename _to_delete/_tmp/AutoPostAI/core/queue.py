"""
Decides what to post next.

Every platform keeps its own place in the queue, so a platform you switch on
in October still starts at post #1 and works through the whole bank. When a
platform reaches the end it wraps around to the start (the oldest post is the
one people are least likely to have seen).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "content" / "posts.json"
STATE = ROOT / "content" / "state.json"


def load_posts() -> list:
    with open(POSTS, encoding="utf-8") as f:
        data = json.load(f)
    posts = data["posts"] if isinstance(data, dict) else data
    seen = set()
    for p in posts:
        if p["id"] in seen:
            raise ValueError(f"duplicate post id in posts.json: {p['id']}")
        seen.add(p["id"])
    return posts


def load_state() -> dict:
    if not STATE.exists():
        return {"posted": {}}
    with open(STATE, encoding="utf-8") as f:
        state = json.load(f)
    state.setdefault("posted", {})
    return state


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")


def next_for(platform: str, posts: list, state: dict, phase: str | None = None) -> dict | None:
    """The oldest post this platform has not sent yet."""
    pool = [p for p in posts if not phase or p.get("phase") == phase]
    if not pool:
        pool = posts
    done = set(state["posted"].get(platform, []))

    for p in pool:
        if p["id"] not in done:
            return p

    # every post in this phase has run at least once -> start the cycle again
    state["posted"][platform] = [i for i in state["posted"].get(platform, []) if i not in {p["id"] for p in pool}]
    return pool[0] if pool else None


def mark_posted(platform: str, post_id: str, state: dict) -> None:
    state["posted"].setdefault(platform, [])
    if post_id not in state["posted"][platform]:
        state["posted"][platform].append(post_id)
