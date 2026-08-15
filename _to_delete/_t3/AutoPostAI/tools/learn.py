"""
Replaces guesses with evidence.

The times in config.yaml came from published studies of millions of posts by
other people. This reads the engagement YOUR posts actually got, groups it by
the slot they went out in, and tells you which slots to keep and which to move.

    python tools/learn.py              # report
    python tools/learn.py --refresh    # fetch fresh numbers first, then report

Works on Bluesky and Mastodon, where post metrics are free to read with the
token you already have. Facebook and Instagram need an extra `read_insights`
permission; if you add it, this is where that would slot in.

Be patient with it. Ten posts per slot is the point where the numbers start
meaning something -- below that you are reading noise, and it will say so.
"""
import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from autopost import load_env_file  # noqa: E402
from core import history  # noqa: E402

MIN_SAMPLE = 10
TIMEOUT = 60


def fetch_bluesky(entries: list) -> int:
    handle = os.environ.get("BLUESKY_HANDLE", "").strip()
    password = os.environ.get("BLUESKY_APP_PASSWORD", "").strip()
    todo = [e for e in entries if e["platform"] == "bluesky" and e.get("ref", "").startswith("https://bsky.app")]
    if not (handle and password and todo):
        return 0

    session = requests.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        json={"identifier": handle, "password": password},
        timeout=TIMEOUT,
    )
    if session.status_code >= 400:
        print(f"  bluesky: could not log in ({session.status_code})")
        return 0
    jwt = session.json()["accessJwt"]
    did = session.json()["did"]

    updated = 0
    for entry in todo:
        rkey = entry["ref"].rsplit("/", 1)[-1]
        uri = f"at://{did}/app.bsky.feed.post/{rkey}"
        resp = requests.get(
            "https://bsky.social/xrpc/app.bsky.feed.getPosts",
            params={"uris": uri},
            headers={"Authorization": f"Bearer {jwt}"},
            timeout=TIMEOUT,
        )
        if resp.status_code >= 400:
            continue
        posts = resp.json().get("posts", [])
        if not posts:
            continue
        p = posts[0]
        entry["engagement"] = p.get("likeCount", 0) + p.get("repostCount", 0) + p.get("replyCount", 0)
        updated += 1
    return updated


def fetch_mastodon(entries: list) -> int:
    base = os.environ.get("MASTODON_INSTANCE", "").strip().rstrip("/")
    token = os.environ.get("MASTODON_TOKEN", "").strip()
    todo = [e for e in entries if e["platform"] == "mastodon" and e.get("ref", "").startswith("http")]
    if not (base and token and todo):
        return 0

    updated = 0
    for entry in todo:
        status_id = entry["ref"].rsplit("/", 1)[-1]
        resp = requests.get(
            f"{base}/api/v1/statuses/{status_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
        )
        if resp.status_code >= 400:
            continue
        d = resp.json()
        entry["engagement"] = d.get("favourites_count", 0) + d.get("reblogs_count", 0) + d.get("replies_count", 0)
        updated += 1
    return updated


def report(entries: list) -> None:
    scored = [e for e in entries if isinstance(e.get("engagement"), int)]
    if not scored:
        print("\nNo engagement numbers yet.")
        print("Run this again after a couple of weeks of posting, with --refresh.")
        return

    by_platform = defaultdict(lambda: defaultdict(list))
    for e in scored:
        by_platform[e["platform"]][e["slot"]].append(e["engagement"])

    for platform in sorted(by_platform):
        slots = by_platform[platform]
        print(f"\n{platform}")
        print(f"  {'slot':<8} {'posts':>6} {'avg engagement':>16}   verdict")
        print(f"  {'-' * 54}")

        averages = {s: sum(v) / len(v) for s, v in slots.items() if v}
        best = max(averages.values()) if averages else 0

        for slot in sorted(slots, key=lambda s: -averages.get(s, 0)):
            values = slots[slot]
            avg = averages[slot]
            if len(values) < MIN_SAMPLE:
                verdict = f"only {len(values)} posts - too early to say"
            elif best and avg >= best * 0.85:
                verdict = "strong, keep it"
            elif best and avg < best * 0.5:
                verdict = "weak - try moving this one"
            else:
                verdict = "middling"
            print(f"  {slot:<8} {len(values):>6} {avg:>16.1f}   {verdict}")

        thin = [s for s, v in slots.items() if len(v) < MIN_SAMPLE]
        if thin:
            print(f"  note: {len(thin)} slot(s) still under {MIN_SAMPLE} posts. "
                  f"Do not move a slot on thin data - one viral post distorts everything.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="fetch current engagement from the platforms first")
    args = ap.parse_args()

    load_env_file()
    entries = history.load()
    if not entries:
        print("content/history.json is empty - nothing has been posted yet.")
        return 0

    print(f"{len(entries)} posts on record")

    if args.refresh:
        print("\nfetching engagement...")
        got = fetch_bluesky(entries) + fetch_mastodon(entries)
        history.save(entries)
        print(f"  updated {got} posts")

    report(entries)

    print("\nHow to act on this: change the times in config.yaml under")
    print("schedule.platforms, commit, and the next run uses them. Move one")
    print("slot at a time so you can tell what caused any change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
