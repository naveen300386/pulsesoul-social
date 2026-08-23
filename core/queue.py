"""
Decides what to post next.

Every platform keeps its own place in the queue, so a platform you switch on
in October still starts at post #1 and works through the whole bank. When a
platform reaches the end it wraps around to the start (the oldest post is the
one people are least likely to have seen).
"""
import json
import os
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
        return {"posted": {}, "fired": {}, "cycle": {}}
    with open(STATE, encoding="utf-8") as f:
        state = json.load(f)
    state.setdefault("posted", {})
    state.setdefault("fired", {})
    state.setdefault("cycle", {})
    return state


def save_state(state: dict) -> None:
    """Atomic. A half-written state.json would crash every future run, and
    this file is the only thing standing between you and a double post."""
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, STATE)


def _rotation(platform: str, size: int) -> int:
    """
    Where in the bank this platform starts.

    Without this, platforms that post at the same frequency stay locked to the
    same queue position forever -- so whenever two of them share a time slot,
    the identical post goes out to both accounts in the same minute. A fixed
    per-platform offset keeps them permanently out of step. Deterministic, so
    it does not drift between runs.
    """
    if size <= 0:
        return 0
    return sum(ord(c) for c in platform) % size


def next_for(platform: str, posts: list, state: dict, phase: str | None = None) -> dict | None:
    """The oldest post this platform has not sent yet."""
    pool = [p for p in posts if not phase or p.get("phase") == phase]
    if not pool:
        pool = posts
    if not pool:
        return None

    offset = _rotation(platform, len(pool))
    ordered = pool[offset:] + pool[:offset]
    done = set(state["posted"].get(platform, []))

    for p in ordered:
        if p["id"] not in done:
            return p

    # Every post in this phase has run at least once -> start the cycle again.
    # Clearing only this pool's ids means switching phase and switching back
    # does not lose your place in the other phase.
    #
    # The cycle counter is what makes that reset survive the push. state.json
    # is union-merged with the remote copy on the way back to the repo, and a
    # plain union cannot tell "this id belongs to the cycle I just finished"
    # from "a parallel runner sent this id" -- so it put all twelve ids back
    # and every platform re-sent ordered[0] forever. Bumping the cycle here
    # gives the merge the one fact it was missing.
    pool_ids = {p["id"] for p in pool}
    state["posted"][platform] = [i for i in state["posted"].get(platform, []) if i not in pool_ids]
    cycles = state.get("cycle") or {}
    state["cycle"] = cycles
    try:
        current = int(cycles.get(platform, 0))
    except (TypeError, ValueError):
        current = 0          # a hand-edited state must never crash the run
    cycles[platform] = current + 1
    return ordered[0]


def mark_posted(platform: str, post_id: str, state: dict) -> None:
    state["posted"].setdefault(platform, [])
    if post_id not in state["posted"][platform]:
        state["posted"][platform].append(post_id)
