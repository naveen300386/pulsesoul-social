"""
Answers the only question that matters: is it still posting?

This exists because of a three-day outage in Aug 2026 that every other signal
in the system reported as fine. GitHub stopped delivering the hourly cron, so
the runner woke twice a day instead of seventeen times, found nothing inside
the catch-up window, and exited 0. Posting fell from 12 a day to 1 a day. Every
run in the Actions tab was green the whole time, because a run that wakes,
finds nothing due and leaves IS a success.

So health is not measured on runs, or on exit codes, or on tokens. It is
measured on slots that came and went: for every account with credentials, how
many of the slots config.yaml promised in the last two days actually fired.

Run by the health job after every posting run. Its exit code is the alert --
GitHub emails the repo owner when a scheduled workflow goes red, and that
email is the only thing here that reaches you without you going to look.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import autopost  # noqa: E402
from core import history, queue, schedule  # noqa: E402
from platforms import ALL  # noqa: E402

# How far back to score. Two days is long enough to survive one bad night and
# short enough that a real outage shows up the same day it starts.
WINDOW_HOURS = 48

# Below this share of promised slots, something is wrong. Not 100%: a festival
# day replaces several slots with one greeting, a single slot can legitimately
# be missed, and an alert that cries wolf gets ignored, which is worse than no
# alert at all.
MIN_DELIVERY = 0.60

# A slot is not late until its catch-up window has closed -- before that it is
# still perfectly likely to fire.
GRACE_MINUTES = 30

# How far back an account has to have posted for its silence to count as a
# fault rather than as "not set up yet".
ESTABLISHED_DAYS = 21


def established(now):
    """Accounts that have actually posted recently, from the history log.

    Deliberately NOT platform.available(). This runs in its own job, which has
    no secrets -- and it should not have them, since reading a token is not the
    point. An account that has been posting for a fortnight and has now gone
    quiet is a fault whether its token is present or not, and an account that
    was never set up should never raise an alarm.
    """
    cutoff = (now - timedelta(days=ESTABLISHED_DAYS)).isoformat(timespec="minutes")
    seen = set()
    for entry in history.load():
        at = str(entry.get("posted_at", ""))
        if at >= cutoff and str(entry.get("ref", "")).lower().find("failed") != 0:
            seen.add(entry.get("platform"))
    return seen


def scored_slots(name, now, cfg):
    """Every slot promised to this account inside the window that is now past saving."""
    deadline = now - timedelta(minutes=schedule.catch_up_of(cfg) + GRACE_MINUTES)
    out = []
    for offset in range(-(WINDOW_HOURS // 24) - 1, 1):
        day = now + timedelta(days=offset)
        for slot in schedule.slots_for(name, day, cfg):
            parsed = schedule.parse_slot(slot)
            if not parsed:
                continue
            when = day.replace(hour=parsed[0], minute=parsed[1], second=0, microsecond=0)
            if now - timedelta(hours=WINDOW_HOURS) <= when <= deadline:
                out.append((day, slot))
    return out


def delivery_report(now, cfg, state):
    live = established(now)
    rows, promised, fired = [], 0, 0
    for platform in ALL:
        if platform.name not in live:
            rows.append((platform.name, None, None, "never posted / not set up"))
            continue
        slots = scored_slots(platform.name, now, cfg)
        hit = sum(1 for day, slot in slots
                  if schedule.already_fired(platform.name, day, slot, state))
        promised += len(slots)
        fired += hit
        if not slots:
            verdict = "nothing scheduled"
        elif hit == 0:
            verdict = "SILENT"
        elif hit < len(slots) * MIN_DELIVERY:
            verdict = "BEHIND"
        else:
            verdict = "ok"
        rows.append((platform.name, hit, len(slots), verdict))
    return rows, fired, promised


def wake_report():
    """How often GitHub actually woke us, and whether the self-chain is alive.

    Reported, never fatal. With the chain running, cron delivery does not
    matter; it is here because a collapse in this number is the early warning
    that the chain has stopped and only the cron is left.
    """
    token, repo = os.environ.get("GH_TOKEN"), os.environ.get("REPO")
    if not (token and repo):
        return None
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/actions/runs?per_page=100",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            runs = json.load(resp).get("workflow_runs", [])
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
        print(f"  (could not read run history: {exc})")
        return None

    from datetime import datetime, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    counts = {}
    for run in runs:
        try:
            at = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        except (ValueError, KeyError):
            continue
        if at >= cutoff:
            counts[run.get("event", "?")] = counts.get(run.get("event", "?"), 0) + 1
    return counts


def main() -> int:
    autopost.load_env_file()
    cfg = autopost.load_config()
    state = queue.load_state()
    now = schedule.now_local(cfg)

    print(f"Health at {now:%a %d %b %H:%M} IST -- last {WINDOW_HOURS}h\n")
    rows, fired, promised = delivery_report(now, cfg, state)

    print(f"{'account':<11} {'fired':>6} {'due':>5}   status")
    print("-" * 44)
    for name, hit, total, verdict in rows:
        got = "-" if hit is None else str(hit)
        want = "-" if total is None else str(total)
        print(f"{name:<11} {got:>6} {want:>5}   {verdict}")

    share = (fired / promised) if promised else 1.0
    print(f"\ndelivered {fired}/{promised} slots = {share * 100:.0f}%")

    counts = wake_report()
    if counts is not None:
        summary = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "none"
        print(f"runs in the last 24h -- {summary}")
        if counts.get("schedule", 0) < 6:
            print("::warning::GitHub delivered the cron fewer than 6 times in 24h. "
                  "The watchdog loop and the self-chain are carrying this now; "
                  "if DISPATCH_TOKEN is unset, fix that before it bites.")
        if counts.get("repository_dispatch", 0) == 0:
            print("::warning::No repository_dispatch runs in 24h -- the self-chain is not "
                  "running. Check the DISPATCH_TOKEN secret has not expired.")

    problems = [name for name, hit, total, verdict in rows if verdict in ("SILENT", "BEHIND")]
    if promised and share < MIN_DELIVERY:
        print(f"::error::Only {share * 100:.0f}% of scheduled slots posted in the last "
              f"{WINDOW_HOURS}h. The autoposter is not working.")
        return 1
    if problems:
        print(f"::error::{', '.join(problems)} missed most of their slots in the last "
              f"{WINDOW_HOURS}h while other accounts posted normally -- "
              f"that points at those accounts' tokens, not the scheduler.")
        return 1

    print("\nposting normally")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
