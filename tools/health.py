"""
Answers the only question that matters: is it still posting?

This exists because of a three-day outage in Aug 2026 that every other signal
in the system reported as fine. GitHub stopped delivering the hourly cron, so
the runner woke twice a day instead of seventeen times, found nothing inside
the catch-up window, and exited 0. Posting fell from 12 a day to 1 a day. Every
run in the Actions tab was green the whole time, because a run that wakes,
finds nothing due and leaves IS a success.

So health is not measured on runs, or on exit codes, or on tokens. It is
measured on the slots that have come and gone unfilled since the last thing
that actually worked -- a streak rather than a window, so it goes quiet the
moment posting resumes instead of staying red for two days after the fix.

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

# How far back to look for slots at all. Only ever used to bound the search.
WINDOW_DAYS = 7

# A slot is not late until its catch-up window has closed -- before that it is
# still perfectly likely to fire.
GRACE_MINUTES = 30

# Missed slots in a row, counted back from now, before this is an outage
# rather than one unlucky slot. Roughly half a day of posting.
STALE_LIMIT = 6

# Same idea for one account while the others are fine, which is a token
# problem rather than a scheduler problem. Lower, because it is a narrower
# claim and a wrong one is cheap to check.
ACCOUNT_STALE_LIMIT = 4

# An account's miss only counts against that account if the system was
# demonstrably alive around then -- i.e. some OTHER account posted within this
# many hours of the slot. Otherwise everything was down, and blaming the
# account sends you hunting a token that is working perfectly.
COMPANY_HOURS = 3

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
        if str(entry.get("posted_at", "")) >= cutoff:
            seen.add(entry.get("platform"))
    return seen


def scored_slots(name, now, cfg, state):
    """Every slot promised to this account that is now past saving, oldest first.

    "Past saving" means its catch-up window has closed. A slot still inside its
    window is not late, it is pending, and counting it as a miss would set this
    alarm off every evening at five past the hour.
    """
    deadline = now - timedelta(minutes=schedule.catch_up_of(cfg) + GRACE_MINUTES)
    out = []
    for offset in range(-WINDOW_DAYS, 1):
        day = now + timedelta(days=offset)
        for slot in schedule.slots_for(name, day, cfg):
            parsed = schedule.parse_slot(slot)
            if not parsed:
                continue
            when = day.replace(hour=parsed[0], minute=parsed[1], second=0, microsecond=0)
            if when <= deadline:
                out.append((when, slot, schedule.already_fired(name, day, slot, state)))
    return sorted(out)


def assess(now, cfg, state):
    """
    The question is "is it posting NOW", not "how were the last two days".

    The first version of this scored a fixed 48-hour window, and it was wrong
    in the way alarms usually are wrong. Once the Aug 2026 outage was fixed and
    every slot was firing again, it stayed red for another two days, because
    the window still contained the outage. An alarm that stays on after the
    fault is cleared is one you learn to ignore, which is worse than no alarm.

    So: measure the streak, not the window. Slots that came and went AFTER the
    last thing that worked. That number is large during an outage and drops to
    zero the moment posting resumes.
    """
    live = established(now)
    slots = {name: scored_slots(name, now, cfg, state)
             for name in (p.name for p in ALL) if name in live}

    successes = sorted(when for rows in slots.values() for when, _, fired in rows if fired)
    last_success = successes[-1] if successes else None

    # Whole system: everything promised since the last thing that worked.
    stale = sorted(when for rows in slots.values() for when, _, fired in rows
                   if not fired and (last_success is None or when > last_success))

    # One account: its own misses, but only the ones where somebody else was
    # visibly posting at the time.
    per_account = {}
    for name, rows in slots.items():
        own = [when for when, _, fired in rows if fired]
        last_own = own[-1] if own else None
        blamed = []
        for when, _, fired in rows:
            if fired or (last_own is not None and when <= last_own):
                continue
            if any(abs((other - when).total_seconds()) <= COMPANY_HOURS * 3600
                   for other in successes if other != when):
                blamed.append(when)
        per_account[name] = (blamed, last_own)

    return live, last_success, stale, per_account


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

    live, last_success, stale, per_account = assess(now, cfg, state)

    print(f"Health at {now:%a %d %b %H:%M} IST\n")
    print(f"{'account':<11} {'last posted':>13} {'missed since':>13}   status")
    print("-" * 60)

    problems = []
    for platform in ALL:
        name = platform.name
        if name not in live:
            print(f"{name:<11} {'-':>13} {'-':>13}   never posted / not set up")
            continue
        blamed, last_own = per_account[name]
        ago = "never"
        if last_own is not None:
            hours = (now - last_own).total_seconds() / 3600
            ago = f"{hours:.0f}h ago" if hours < 48 else f"{hours / 24:.0f}d ago"
        if len(blamed) >= ACCOUNT_STALE_LIMIT:
            verdict = f"CHECK THIS ACCOUNT ({len(blamed)} missed while others posted)"
            problems.append(name)
        elif blamed:
            verdict = "behind, catching up"
        else:
            verdict = "ok"
        print(f"{name:<11} {ago:>13} {len(blamed):>13}   {verdict}")

    if last_success is None:
        print("\nNothing has ever posted.")
    else:
        hours = (now - last_success).total_seconds() / 3600
        print(f"\nlast slot filled: {last_success:%a %d %b %H:%M} IST ({hours:.0f}h ago)")
    print(f"slots come and gone unfilled since then: {len(stale)}")

    counts = wake_report()
    if counts is not None:
        summary = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "none"
        print(f"runs in the last 24h -- {summary}")
        if counts.get("schedule", 0) < 6:
            print("::warning::GitHub delivered the cron fewer than 6 times in 24h. "
                  "The watchdog loop is carrying this; if DISPATCH_TOKEN is unset, "
                  "set it before that stops being enough.")
        if counts.get("repository_dispatch", 0) == 0:
            print("::warning::No repository_dispatch runs in 24h -- the self-chain is not "
                  "running. Either DISPATCH_TOKEN is unset, or it has expired.")

    if len(stale) >= STALE_LIMIT:
        print(f"::error::{len(stale)} scheduled slots have come and gone unfilled since "
              f"anything last posted. The autoposter is not working.")
        return 1
    if problems:
        print(f"::error::{', '.join(problems)} kept missing slots while other accounts "
              f"posted normally -- that points at those accounts' tokens, not the scheduler.")
        return 1

    print("\nposting, with a few slots still to catch up" if stale else "\nposting normally")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
