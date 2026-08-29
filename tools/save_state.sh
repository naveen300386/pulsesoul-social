#!/usr/bin/env bash
#
# Makes "already posted" durable.
#
# The runner is destroyed when the job ends, so a post that is not pushed back
# to the branch has, as far as the next run is concerned, never happened -- and
# it will be sent again. This script is the only thing standing between a
# delayed push and a duplicate on eight live accounts.
#
# It used to be an inline step that ran once, at the end of the job. It is a
# file now because the job no longer ends after one pass: the watchdog loop in
# autopost.yml posts and saves every few minutes for hours, so this has to be
# callable dozens of times and be a no-op on the many cycles that post nothing.
#
# Never rebase here. A conflict would halt the step and strand the record
# inside a runner that is about to vanish. Union-merge and move on: a slot that
# fired on either side has fired. Worst case a post is skipped, never repeated.
set -u

BRANCH="${1:-main}"
cd "$(dirname "$0")/.."

git config user.name  "autopost-bot"
git config user.email "autopost-bot@users.noreply.github.com"
touch content/history.jsonl

# Keep this cycle's results somewhere git cannot touch them.
mkdir -p /tmp/ap
cp content/state.json    /tmp/ap/state.json
cp content/history.jsonl /tmp/ap/history.jsonl
# feed.xml too. It is written during the Post step, and the reset below would
# otherwise throw the new LinkedIn item away -- which it silently did once, so
# the Page went quiet while the log cheerfully said "queued".
cp content/feed.xml      /tmp/ap/feed.xml 2>/dev/null || true

for attempt in 1 2 3 4 5; do
  git fetch --quiet origin "$BRANCH"

  # Start from exactly what the remote has, then lay our results back on top.
  # This also refreshes the runner between watchdog cycles, so a long-lived
  # run keeps reading current state instead of the state it booted with.
  git reset --hard --quiet "origin/$BRANCH"
  cp /tmp/ap/state.json content/state.json
  cp /tmp/ap/feed.xml   content/feed.xml 2>/dev/null || true

  # history is append-only lines, so union = concatenate and dedupe.
  cat content/history.jsonl /tmp/ap/history.jsonl 2>/dev/null \
    | awk 'NF && !seen[$0]++' > /tmp/ap/merged.jsonl
  cp /tmp/ap/merged.jsonl content/history.jsonl

  python tools/merge_state.py "origin/$BRANCH"

  git add content/state.json content/history.jsonl content/feed.xml
  if git diff --staged --quiet; then
    echo "nothing new to record"
    exit 0
  fi

  git commit --quiet -m "posted $(date -u '+%Y-%m-%d %H:%M') UTC"
  if git push --quiet origin "HEAD:$BRANCH"; then
    echo "state saved on attempt $attempt"
    exit 0
  fi
  echo "push failed, retrying (attempt $attempt)"
  sleep $((attempt * 5))
done

echo "::error::Could not save posting state after 5 attempts."
echo "::error::The next run may repeat these posts. Check branch protection on $BRANCH."
exit 1
