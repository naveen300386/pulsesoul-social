#!/usr/bin/env python3
"""
PulseSoul AutoPostAI -- posts to every connected social account, on a schedule,
with no one watching.

  python autopost.py --dry-run          see exactly what would go out, post nothing
  python autopost.py                    post one item to every connected platform
  python autopost.py --only telegram    post to a single platform (good for testing)
  python autopost.py --status           what is connected, what is not, how far the queue is

A platform with no tokens is skipped, not failed. A platform that errors does
not stop the others. Nothing is ever posted twice.
"""
import argparse
import os
import sys
import traceback
from pathlib import Path

import yaml

from core import history, log, queue, schedule
from platforms import ALL, BY_NAME

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.yaml"
PREVIEW = ROOT / "preview.md"


def load_env_file() -> None:
    """Local runs read .env . GitHub Actions injects real environment vars."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


def load_config() -> dict:
    with open(CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)


# Paragraphs containing any of these are legal/safety qualifiers. They are
# never dropped to make a post fit -- a shortened post that keeps the claim
# but loses the qualifier is exactly the thing that gets an app pulled.
PROTECTED = [
    "not an emergency service",
    "emergency services",
    "never an alarm",
    "not a medical",
    "not a health device",
    "optional",
    "encrypted",
]


def is_protected(paragraph: str) -> bool:
    low = paragraph.lower()
    return any(phrase in low for phrase in PROTECTED)


def compose(post: dict, platform, cfg: dict) -> str:
    """
    Build the final text for one platform.

    Short platforms (Bluesky is 300 characters) must never chop a sentence in
    half. So when it does not fit we shed things in order of what matters
    least: hashtags first, then the middle paragraphs, keeping the opening
    hook, the closing call to action, and any paragraph carrying a safety
    qualifier. Truncation is the last resort and should never actually happen
    with the current bank -- tools/check.py fails the build if it does.
    """
    body = (post.get(platform.voice) or post.get("english") or "").strip()
    paras = [p.strip() for p in body.split("\n\n") if p.strip()]

    tail = ""
    if platform.link_style == "inline":
        tail = cfg["link"]
    elif platform.link_style == "bio":
        tail = cfg.get("bio_cta", "").strip()

    tag_line = " ".join(cfg.get("hashtags", {}).get(platform.name, [])).strip()

    def assemble(body_paras: list, with_tags: bool) -> str:
        parts = ["\n\n".join(body_paras)]
        if tail:
            parts.append(tail)
        if with_tags and tag_line:
            parts.append(tag_line)
        return "\n\n".join(p for p in parts if p)

    def fits(text: str) -> bool:
        return platform.limit is None or len(text) <= platform.limit

    candidate = assemble(paras, True)
    if fits(candidate):
        return candidate

    candidate = assemble(paras, False)
    if fits(candidate):
        return candidate

    # Drop from the middle outwards, keeping the hook, the ask, and every
    # safety qualifier. If the only paragraphs left are protected ones, we
    # stop shrinking and let tools/check.py fail rather than ship a post that
    # states a capability without its caveat.
    kept = list(paras)
    while len(kept) > 2:
        droppable = [i for i in range(1, len(kept) - 1) if not is_protected(kept[i])]
        if not droppable:
            break
        middle = len(kept) // 2
        kept.pop(min(droppable, key=lambda i: (abs(i - middle), i)))
        candidate = assemble(kept, False)
        if fits(candidate):
            return candidate

    if not any(is_protected(p) for p in paras):
        for fallback in ([paras[0], paras[-1]], [paras[0]]):
            candidate = assemble(fallback, False)
            if fits(candidate):
                return candidate

    return candidate


def run(args) -> int:
    load_env_file()
    cfg = load_config()
    posts = queue.load_posts()
    state = queue.load_state()
    phase = args.phase or cfg.get("phase")

    # A typo here would silently fall back to the whole bank -- which on
    # launch day means posting tester-recruitment copy to eight live accounts.
    known = sorted({p.get("phase") for p in posts})
    if phase not in known:
        log.fail(f"config.yaml has phase '{phase}', which is not in posts.json. Valid phases: {', '.join(known)}")
        return 1

    targets = [BY_NAME[args.only]] if args.only else ALL
    when = schedule.now_local(cfg, args.now)

    if args.status:
        log.header(f"Accounts  |  {when:%a %d %b %H:%M} IST")
        for p in ALL:
            done = len(state["posted"].get(p.name, []))
            total = len([x for x in posts if not phase or x.get("phase") == phase])
            if p.available():
                log.ok(
                    f"{p.name:<10} ready       {done}/{total} sent  |  today: "
                    f"{schedule.describe(p.name, when, cfg)}  |  next: {schedule.next_slot_after(p.name, when, cfg)}"
                )
            else:
                log.skip(f"{p.name:<10} not set up  needs: {', '.join(p.missing())}")
        return 0

    mode = "DRY RUN - nothing will be posted" if args.dry_run else "LIVE"
    if args.force:
        mode += "  (--force: ignoring the schedule)"
    log.header(f"AutoPostAI  |  phase '{phase}'  |  {when:%a %d %b %H:%M} IST  |  {mode}")

    preview_lines = [f"# What would be posted (phase: {phase})\n"]
    sent = 0
    failed = 0
    skipped = 0

    for platform in targets:
        if not platform.available():
            log.skip(f"{platform.name}: not connected yet ({', '.join(platform.missing())})")
            skipped += 1
            continue

        # --force is a manual override; the hourly runner uses the schedule and
        # stays quiet the ~22 hours a day nobody is due.
        slot = slot_day = None
        owed = schedule.due_slot(platform.name, when, state, cfg)
        if owed:
            slot, slot_day = owed
        elif not args.force:
            log.skip(f"{platform.name}: not due (next {schedule.next_slot_after(platform.name, when, cfg)})")
            skipped += 1
            continue

        post = queue.next_for(platform.name, posts, state, phase)
        if not post:
            log.skip(f"{platform.name}: queue is empty for this phase")
            skipped += 1
            continue

        text = compose(post, platform, cfg)
        image = platform.image_path(post.get("image", ""))

        preview_lines.append(
            f"\n## {platform.name}  (post {post['id']})\n\n"
            f"image: `{image.name if image else 'none'}`\n\n"
            f"```\n{text}\n```\n"
        )

        label = f"slot {slot}" if slot else "forced"

        if args.dry_run:
            log.step(f"{platform.name}: would send post {post['id']} at {label} ({len(text)} chars, "
                     f"{'image ' + image.name if image else 'no image'})")
            continue

        # WRITE AHEAD. The slot and the post id are burned to disk BEFORE the
        # API call, not after.
        #
        # The window between "bytes reached Instagram" and "we recorded it" is
        # not small -- Threads sleeps 30s then publishes with a 60s timeout. A
        # dropped response, a timeout, or the runner dying in that window is
        # indistinguishable from a genuine failure. Recording afterwards means
        # every one of those posts twice.
        #
        # The trade is deliberate: a lost post is recoverable and nobody
        # notices, a duplicate is public and permanent.
        if slot:
            schedule.record_fire(platform.name, slot_day, slot, state)
        queue.mark_posted(platform.name, post["id"], state)
        queue.save_state(state)

        try:
            log.step(f"{platform.name}: sending post {post['id']} ({label})...")
            where = platform.post(text, post.get("image", ""), cfg["link"])
            log.ok(f"{platform.name}: posted -> {where}")
            sent += 1
        except Exception as exc:  # one platform must never take down the rest
            failed += 1
            where = f"FAILED: {exc}"
            log.fail(f"{platform.name}: {exc}")
            if args.verbose:
                traceback.print_exc()

        # Outside the try on purpose: a history write that fails must never be
        # reported as a posting failure, which would send you hunting a token
        # that is working perfectly.
        try:
            history.record(platform.name, post["id"], slot, when, where)
        except Exception as exc:
            log.info(f"{platform.name}: posted fine, but the history log failed ({exc})")

    PREVIEW.write_text("\n".join(preview_lines), encoding="utf-8")

    # An account that used to post and has now gone quiet is the failure mode
    # nobody notices for weeks. A deleted or renamed secret does not throw --
    # the platform just reports "not connected" forever, with a green tick.
    # So: if a platform has EVER posted successfully and is now unreachable
    # with slots going by, say so loudly. Platforms that have never been set
    # up stay quiet, or every run would be red during setup.
    gone_quiet = []
    if not args.dry_run and not args.only:
        try:
            established = history.platforms_seen()
        except Exception:
            established = set()
        for p in ALL:
            if p.name in established and not p.available():
                if schedule.missed_today(p.name, when, state, cfg):
                    gone_quiet.append(p.name)

    log.header(f"done in {log.elapsed()}  |  posted {sent}  |  failed {failed}  |  skipped {skipped}")
    if args.dry_run:
        log.info(f"full preview written to {PREVIEW.name}")

    for name in gone_quiet:
        log.fail(f"{name}: was posting before, now has no credentials - a secret was deleted or renamed")

    # A red X in the Actions tab is the only way you find out an account has
    # gone quiet. A false alarm is much cheaper than silence: an expired token
    # fails identically to a working one that posted nothing.
    if failed or gone_quiet:
        log.fail(f"{failed + len(gone_quiet)} account(s) need attention - open this run's log")
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Post PulseSoul content to every connected social account.")
    ap.add_argument("--dry-run", action="store_true", help="show what would be posted, send nothing")
    ap.add_argument("--only", choices=sorted(BY_NAME), help="post to one platform only")
    ap.add_argument("--phase", help="override the content phase set in config.yaml")
    ap.add_argument("--status", action="store_true", help="show what is connected and when it posts next")
    ap.add_argument("--force", action="store_true", help="post now, ignoring the peak-time schedule")
    ap.add_argument("--now", metavar="'YYYY-MM-DD HH:MM'", help="pretend it is this time (for testing the schedule)")
    ap.add_argument("--verbose", action="store_true", help="print full errors and why platforms were skipped")
    return run(ap.parse_args())


if __name__ == "__main__":
    sys.exit(main())
