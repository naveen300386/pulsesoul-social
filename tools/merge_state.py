"""
Merges the remote content/state.json into the local one, taking the UNION.

This exists because of a nasty failure mode. state.json is the only record of
"this slot already fired", and it only becomes durable when the workflow
pushes it back to the repo. If that push hits a conflict, the old code let git
halt the step -- and because GitHub Actions runs steps under `bash -e`, the
push never happened and the runner was destroyed with the record inside it.
The next hourly run then read stale state and posted the same thing again.

A union merge makes that conflict impossible to lose data to: a slot that
fired on either side has fired, and a post sent on either side was sent. The
worst case is a post that gets skipped, never one that repeats.

Used by the workflow. You should never need to run it by hand.

    python tools/merge_state.py <git-ref>      e.g. origin/main
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import queue  # noqa: E402

REMOTE_PATH = "content/state.json"


def remote_state(ref: str) -> dict | None:
    try:
        raw = subprocess.run(
            ["git", "show", f"{ref}:{REMOTE_PATH}"],
            capture_output=True, text=True, check=True, timeout=60,
        ).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def merge(local: dict, remote: dict) -> tuple[dict, int]:
    added = 0

    for platform, ids in (remote.get("posted") or {}).items():
        mine = local.setdefault("posted", {}).setdefault(platform, [])
        for post_id in ids:
            if post_id not in mine:
                mine.append(post_id)
                added += 1

    for platform, days in (remote.get("fired") or {}).items():
        mine = local.setdefault("fired", {}).setdefault(platform, {})
        for day, slots in (days or {}).items():
            bucket = mine.setdefault(day, [])
            for slot in slots:
                if slot not in bucket:
                    bucket.append(slot)
                    added += 1

    return local, added


def main() -> int:
    ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"

    remote = remote_state(ref)
    if remote is None:
        print(f"no readable {REMOTE_PATH} at {ref} - keeping local state as is")
        return 0

    merged, added = merge(queue.load_state(), remote)
    queue.save_state(merged)
    print(f"merged {ref}: pulled in {added} record(s) this runner did not have")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
