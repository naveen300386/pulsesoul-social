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

from core import log, queue
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

    if args.status:
        log.header("Connected accounts")
        for p in ALL:
            done = len(state["posted"].get(p.name, []))
            total = len([x for x in posts if not phase or x.get("phase") == phase])
            if p.available():
                log.ok(f"{p.name:<10} ready      {done}/{total} posts sent from the '{phase}' set")
            else:
                log.skip(f"{p.name:<10} not set up  needs: {', '.join(p.missing())}")
        return 0

    log.header(f"AutoPostAI  |  phase '{phase}'  |  {'DRY RUN - nothing will be posted' if args.dry_run else 'LIVE'}")

    preview_lines = [f"# What would be posted (phase: {phase})\n"]
    sent = 0
    failed = 0
    skipped = 0

    for platform in targets:
        if not platform.available():
            log.skip(f"{platform.name}: not connected yet ({', '.join(platform.missing())})")
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

        if args.dry_run:
            log.step(f"{platform.name}: would send post {post['id']} ({len(text)} chars, "
                     f"{'image ' + image.name if image else 'no image'})")
            continue

        try:
            log.step(f"{platform.name}: sending post {post['id']}...")
            where = platform.post(text, post.get("image", ""), cfg["link"])
            queue.mark_posted(platform.name, post["id"], state)
            queue.save_state(state)
            log.ok(f"{platform.name}: posted -> {where}")
            sent += 1
        except Exception as exc:  # one platform must never take down the rest
            failed += 1
            log.fail(f"{platform.name}: {exc}")
            if args.verbose:
                traceback.print_exc()

    PREVIEW.write_text("\n".join(preview_lines), encoding="utf-8")

    log.header(f"done in {log.elapsed()}  |  posted {sent}  |  failed {failed}  |  skipped {skipped}")
    if args.dry_run:
        log.info(f"full preview written to {PREVIEW.name}")

    # A red X in the Actions tab is the only way you find out an account has
    # gone quiet. Silence would be worse than a false alarm here: an expired
    # token fails identically to a working one that posted nothing.
    if failed:
        log.fail(f"{failed} account(s) failed - open this run's log and fix them")
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Post PulseSoul content to every connected social account.")
    ap.add_argument("--dry-run", action="store_true", help="show what would be posted, send nothing")
    ap.add_argument("--only", choices=sorted(BY_NAME), help="post to one platform only")
    ap.add_argument("--phase", help="override the content phase set in config.yaml")
    ap.add_argument("--status", action="store_true", help="show which accounts are connected")
    ap.add_argument("--verbose", action="store_true", help="print full errors")
    return run(ap.parse_args())


if __name__ == "__main__":
    sys.exit(main())
