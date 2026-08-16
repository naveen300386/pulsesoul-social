"""
A log of every post that actually went out, with the slot it went out in.

This exists so that `tools/learn.py` can eventually answer the only question
that really matters: *which of these times worked for YOUR audience?*
Published "best time to post" studies are a starting guess. This file is
evidence.

Stored as JSON Lines (one JSON object per line) rather than one big array,
for three reasons: appending a post does not rewrite the whole file, a
corrupt line loses one entry instead of the file, and two runs appending
different lines produce a git conflict git can actually resolve.
"""
import json
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "content" / "history.jsonl"


def load() -> list:
    if not HISTORY.exists():
        return []
    entries = []
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            # one bad line must not cost you the whole history
            continue
    return entries


def save(entries: list) -> None:
    """Full rewrite. Only tools/learn.py needs this, to fill in engagement."""
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    tmp = HISTORY.with_suffix(".jsonl.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, HISTORY)  # atomic: never leaves a half-written file


def record(platform: str, post_id: str, slot: str | None, when: datetime, where: str) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "platform": platform,
        "post_id": post_id,
        "slot": slot or "forced",
        "weekday": when.strftime("%a"),
        "posted_at": when.isoformat(timespec="minutes"),
        "ref": where,
        "engagement": None,  # filled in later by tools/learn.py
    }
    with open(HISTORY, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def platforms_seen() -> set:
    """Platforms that have successfully posted at least once, ever.

    Used to tell 'not set up yet' apart from 'was working, now silent'.

    SANDBOX counts as not-seen on purpose. A Pinterest app on Trial access can
    only make private sandbox pins; treating those as a working account would
    mean the day it silently stops, nothing complains.
    """
    return {
        e["platform"]
        for e in load()
        if e.get("platform") and not str(e.get("ref", "")).startswith(("FAILED", "SANDBOX"))
    }
