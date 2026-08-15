"""
Runs the REAL posting path against a fake clock and fake platforms, so you can
watch a fortnight of posting without posting anything.

    python tools/simulate.py            # 14 days, perfect hourly runner
    python tools/simulate.py --chaos    # GitHub drops and delays runs
    python tools/simulate.py --faults   # ...and the network eats responses,
                                        #    and state pushes get lost

The faults mode is the one that matters. It reproduces the three ways this can
post the same thing twice in production:

  * the post lands but the response never comes back
  * the runner dies after posting, before recording
  * the state push fails, so the next run reads stale state

This drives autopost.run() itself -- the same queue, state file, write-ahead
ordering and dedupe logic that runs for real. An earlier version of this file
only called the scheduler with an in-memory dict, and it cheerfully reported
"no double posts" while all three faults above posted twice.
"""
import argparse
import shutil
import sys
import tempfile
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import autopost  # noqa: E402
from core import history, queue, schedule  # noqa: E402
import platforms as platforms_pkg  # noqa: E402

# What SHOULD happen, written out by hand rather than derived from the code
# under test. If config.yaml and this table disagree, one of them is wrong and
# the simulation says so instead of quietly agreeing with itself.
EXPECTED_PER_WEEK = {
    "instagram": 14, "facebook": 14, "threads": 12, "bluesky": 14,
    "mastodon": 12, "linkedin": 6, "telegram": 14, "pinterest": 9,
}

# A bank that runs out legitimately cycles back to the start, so the same text
# WILL appear again days later -- that is by design. A genuine double post is
# the same text twice in quick succession. 36 hours is comfortably longer than
# any gap between slots and far shorter than any real cycle.
REPEAT_WINDOW_HOURS = 36


class Rng:
    """Reproducible, and each draw is independent of the last."""

    def __init__(self, seed: int = 20260817):
        self.s = seed

    def next(self) -> int:
        self.s = (self.s * 1103515245 + 12345) % (2 ** 31)
        return (self.s >> 8) % 100


class FakePlatform:
    """Stands in for a real account. Records calls, can fail like a real one."""

    def __init__(self, real):
        self.name = real.name
        self.voice = real.voice
        self.limit = real.limit
        self.link_style = real.link_style
        self.shape = real.shape
        self.calls = []
        self.fail_next_response = False

    def available(self):
        return True

    def missing(self):
        return []

    def image_path(self, stem):
        return None

    def image_url(self, stem):
        return None

    def post(self, text, image_stem, link):
        # The call is recorded BEFORE any failure is decided -- that is the
        # whole point. A lost response is not an unsent post.
        self.calls.append(text)
        if self.fail_next_response:
            self.fail_next_response = False
            raise RuntimeError("HTTP 504 reading the response (the post already landed)")
        return f"https://example/{self.name}/{len(self.calls)}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--chaos", action="store_true", help="drop and delay runs")
    ap.add_argument("--faults", action="store_true", help="chaos, plus lost responses and lost state pushes")
    ap.add_argument("--brutal", action="store_true",
                    help="faults at absurd rates, to show where the design finally breaks")
    args = ap.parse_args()
    if args.brutal:
        args.faults = True
    if args.faults:
        args.chaos = True

    # A lost response means the post landed but we could not confirm it. The
    # write-ahead ordering in autopost.py makes this safe, so the rate is only
    # about how often we NEEDLESSLY lose a post.
    response_loss = 20 if args.brutal else 4

    # A lost state push is the one genuinely dangerous fault: the next run
    # wakes with stale state and reposts. The workflow retries the push five
    # times with backoff and union-merges rather than rebasing, so reaching
    # this state means five consecutive failures. 8% models a repo where
    # something is structurally broken (branch protection, say); 1% is
    # already pessimistic for normal operation.
    push_loss = 8 if args.brutal else 1

    work = Path(tempfile.mkdtemp(prefix="autopost-sim-"))
    try:
        shutil.copy(ROOT / "content" / "posts.json", work / "posts.json")
        (work / "state.json").write_text('{"posted": {}, "fired": {}}')
        (work / "history.jsonl").write_text("")

        queue.POSTS = work / "posts.json"
        queue.STATE = work / "state.json"
        history.HISTORY = work / "history.jsonl"
        autopost.PREVIEW = work / "preview.md"

        fakes = [FakePlatform(p) for p in platforms_pkg.ALL]
        autopost.ALL = fakes
        autopost.BY_NAME = {f.name: f for f in fakes}

        cfg = autopost.load_config()
        start = schedule.now_local(cfg, "2026-08-17 00:00")  # a Monday
        rng = Rng()

        dropped = lost_pushes = 0
        per_platform_calls = defaultdict(list)

        for hour in range(args.days * 24):
            wake = start + timedelta(hours=hour, minutes=17)  # GitHub fires at :17

            if args.chaos:
                if rng.next() < 12:                          # ~12% of runs never happen
                    dropped += 1
                    continue
                wake += timedelta(minutes=rng.next() // 3)   # 0-33 minutes late

            if args.faults:
                for f in fakes:
                    if rng.next() < response_loss:
                        f.fail_next_response = True

            before = {f.name: len(f.calls) for f in fakes}
            snapshot = (work / "state.json").read_text()

            autopost.run(SimpleNamespace(
                dry_run=False, only=None, phase=None, status=False,
                force=False, now=wake.strftime("%Y-%m-%d %H:%M"), verbose=False,
            ))

            for f in fakes:
                for text in f.calls[before[f.name]:]:
                    per_platform_calls[f.name].append((wake, text))
                f.fail_next_response = False

            # The state push is what makes "already posted" durable. When it
            # fails, the next run wakes up with the old file.
            if args.faults and rng.next() < push_loss:
                (work / "state.json").write_text(snapshot)
                lost_pushes += 1

        # ---- the checks that matter ---------------------------------------
        problems = []
        for name, calls in per_platform_calls.items():
            last_seen = {}
            for at, text in calls:
                if text in last_seen:
                    gap = (at - last_seen[text]).total_seconds() / 3600
                    if gap < REPEAT_WINDOW_HOURS:
                        problems.append(
                            f"DOUBLE POST: {name} sent the same text twice {gap:.1f}h apart"
                        )
                last_seen[text] = at

        by_minute = defaultdict(list)
        for entry in history.load():
            by_minute[entry["posted_at"]].append((entry["platform"], entry["post_id"]))
        clashes = sum(
            1
            for items in by_minute.values()
            for pid, plats in _group(items).items()
            if len(plats) > 1
        )

        weeks = args.days / 7
        mode = "faults" if args.faults else ("chaos" if args.chaos else "clean")
        print(f"\n{args.days} days, mode={mode}"
              f"{f', {dropped} runs dropped, {lost_pushes} state pushes lost' if args.chaos else ''}\n")
        print(f"{'platform':<11} {'sent':>6} {'expected':>9} {'delivered':>10}   result")
        print("-" * 62)

        total_sent = total_expected = 0
        for f in fakes:
            sent = len(per_platform_calls[f.name])
            want = round(EXPECTED_PER_WEEK.get(f.name, 0) * weeks)
            total_sent += sent
            total_expected += want
            pct = (100 * sent / want) if want else 0

            if want and sent == 0:
                verdict = "SILENT - posted nothing at all"
                problems.append(f"{f.name} posted nothing across {args.days} days")
            elif sent > want:
                verdict = f"OVER by {sent - want}"
                problems.append(f"{f.name} sent {sent - want} more than scheduled")
            elif not args.chaos and sent < want:
                verdict = f"MISSED {want - sent}"
                problems.append(f"{f.name} missed {want - sent} slots with a perfect runner")
            elif pct < 80:
                verdict = f"only {pct:.0f}% delivered"
                problems.append(f"{f.name} delivered only {pct:.0f}% even allowing for chaos")
            else:
                verdict = "healthy"
            print(f"{f.name:<11} {sent:>6} {want:>9} {pct:>9.0f}%   {verdict}")

        overall = 100 * total_sent / total_expected if total_expected else 0
        print(f"\ndelivered {total_sent}/{total_expected} = {overall:.1f}%")
        # Two accounts carrying the same text in the same minute is untidy but
        # not harmful -- the audiences barely overlap. The per-platform queue
        # rotation keeps it rare; it only matters if it becomes the norm.
        clash_rate = (100 * clashes / total_sent) if total_sent else 0
        print(f"same post to 2+ accounts in the same minute: {clashes} ({clash_rate:.1f}% of posts)")
        if clash_rate > 3:
            problems.append(
                f"{clashes} posts ({clash_rate:.0f}%) went to several accounts at once - "
                f"the queue rotation in core/queue.py is not spreading them out"
            )

        if problems:
            print(f"\n{len(problems)} PROBLEM(S):")
            for p in sorted(set(problems)):
                print(f"  ! {p}")
            return 1

        print("\nno double posts, no silent platforms, no duplicate blasts")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _group(items):
    out = defaultdict(list)
    for platform, post_id in items:
        out[post_id].append(platform)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
