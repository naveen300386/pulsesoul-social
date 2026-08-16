"""
Festival greetings: which day, which greeting, and has it gone out yet.

Hindu festival dates follow a lunar calendar, so nothing here is computed --
content/festivals.json holds a hand-checked date for each specific year. That
is a maintenance cost with a payoff: a wrong Diwali greeting posted a day late
is worse than no greeting at all.

Only the accounts listed in the file's "platforms" take part. LinkedIn and the
global platforms are deliberately left out: a festival greeting reads warmly to
family-app followers in India and as noise to everyone else.
"""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "content" / "festivals.json"


def load() -> dict:
    if not FILE.exists():
        return {"platforms": [], "greetings": {}, "dates": {}}
    return json.loads(FILE.read_text(encoding="utf-8"))


def for_date(when: datetime, platform_name: str, data: dict | None = None) -> dict | None:
    """The greeting due on this date for this account, or None."""
    data = data if data is not None else load()
    if platform_name not in (data.get("platforms") or []):
        return None
    key = data.get("dates", {}).get(when.strftime("%Y-%m-%d"))
    if not key:
        return None
    greeting = (data.get("greetings") or {}).get(key)
    if not greeting:
        return None
    # Shaped like a post from posts.json so the rest of the pipeline -- compose,
    # image lookup, history -- needs no special case.
    return {
        "id": f"festival:{key}",
        "phase": "festival",
        "image": greeting["image"],
        "english": greeting["english"],
        "hinglish": greeting["hinglish"],
    }


def already_sent(platform_name: str, when: datetime, state: dict) -> bool:
    stamp = when.strftime("%Y-%m-%d")
    return stamp in (state.get("festivals", {}).get(platform_name) or [])


def record(platform_name: str, when: datetime, state: dict) -> None:
    stamp = when.strftime("%Y-%m-%d")
    bucket = state.setdefault("festivals", {}).setdefault(platform_name, [])
    if stamp not in bucket:
        bucket.append(stamp)
    # A year of stamps is plenty; this file is pushed on every run.
    del bucket[:-40]


def days_of_calendar_left(today: datetime, data: dict | None = None) -> int:
    """How far ahead the hand-checked dates run. Zero means the next festival
    will pass in silence."""
    data = data if data is not None else load()
    future = [d for d in (data.get("dates") or {}) if d >= today.strftime("%Y-%m-%d")]
    if not future:
        return 0
    last = max(future)
    return (datetime.strptime(last, "%Y-%m-%d").date() - today.date()).days
