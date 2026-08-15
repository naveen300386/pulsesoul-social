# AutoPostAI — PulseSoul social autoposter

Posts PulseSoul content to Facebook, Instagram, Threads, Telegram, Bluesky,
Mastodon, LinkedIn and Pinterest — twice a day, on GitHub's servers, for free,
with your PC switched off.

**Start here: [SETUP.md](SETUP.md).** After the first two steps (about 20
minutes) it is already posting.

---

## How it works

```
content/posts.json    60 posts, each with English + Hinglish copy
      +
assets/screenshots/   your real Play Store art
      ↓
rendered/             the same art reframed for each platform's shape
      ↓
config.yaml           who posts, and at what time, per platform
      ↓
autopost.py           wakes hourly, posts whoever is due
      ↓
content/state.json    what has been posted, so nothing repeats
content/history.jsonl what went out when, so tools/learn.py can improve it
```

## Posting times

The workflow wakes **every hour** and asks `config.yaml` who is due. Most runs
post nothing and finish in seconds.

Times are per platform, in IST, because the platforms disagree with each other
more than you would expect:

| Platform | When it posts | Why |
|---|---|---|
| Instagram | 12:00 + 20:00 weekdays | India peaks 7–9pm; Wed 8pm is the single best slot |
| Facebook | 09:00 + 21:00 | offset from Instagram so one follower isn't hit twice at once |
| Threads | 07:00 + 10:00 | mornings win, evenings are its *worst* window |
| Bluesky | 18:00 + 20:00, weekends 16:00 | chronological feed — ~2x between best and worst slot |
| Mastodon | 12:00 + 19:00 | chronological, same evening shape as Bluesky |
| LinkedIn | 16:00, once a day | 3–8pm now beats office hours; Wednesday is strongest |
| Telegram | 10:00 + 20:00 | subscribers get a notification, so never late at night |
| Pinterest | 21:00, plus weekend mornings | a search engine with a slow burn; timing matters least |

Edit `schedule.platforms` in `config.yaml` to change any of it. A specific day
(`wed:`) beats `weekday:`/`weekend:`, which beats `default:`. An empty list
means "don't post that day". **Use whole hours** — the runner only wakes once
an hour, and `tools/check.py` warns if you don't.

### Not posting the same thing twice

Posting twice to a real audience is embarrassing and permanent; a missed post
is invisible and self-healing. Every trade-off below is made in that direction.

- **The record is written before the API call, not after.** Threads sleeps 30
  seconds and then publishes with a 60-second timeout — a dropped response in
  that window is indistinguishable from a failure. Recording afterwards means
  every one of those posts twice. So the slot is burned to disk first, and a
  genuinely failed send is simply accepted as a lost post.
- **A slot is keyed to its own date, not the run's.** A 23:00 slot caught at
  00:20 belongs to yesterday. Keying it on the run date would both lose the
  record and let it fire again.
- **One slot's catch-up can't swallow the next.** Several platforms have slots
  exactly 120 minutes apart; without clamping, a late run fires the first and
  the next run fires the second forty minutes later.
- **The state push is retried five times and union-merged, never rebased.**
  This push is the *only* thing that makes "already posted" durable — the
  runner is destroyed straight afterwards. A rebase conflict used to halt the
  step under `bash -e`, so the push never happened and the next run reposted
  everything. A union merge cannot conflict: a slot that fired on either side
  has fired.
- **Re-running a failed job doesn't repost.** A re-run checks out the original
  commit, which predates that run's own state push, so the workflow re-fetches
  current state before posting.

**The one residual risk:** if GitHub refuses the push five times running
(branch protection on `main` is the realistic cause), the next run wakes with
stale state and can repost. The workflow emits a loud `::error::` when that
happens, so it is visible rather than silent.

```
python tools/simulate.py            # a fortnight, hour by hour
python tools/simulate.py --chaos    # GitHub dropping and delaying runs
python tools/simulate.py --faults   # + lost responses and lost state pushes
python tools/simulate.py --brutal   # absurd rates, to show where it breaks
```

The simulation drives `autopost.run()` itself — the real queue, the real state
file, the real ordering. An earlier version only poked the scheduler with an
in-memory dict and reported "no double posts" while three separate fault paths
were posting twice.

## Making it use your real audience instead of studies

Those times come from published studies of other people's posts. Your own
audience beats all of it.

Every post is logged to `content/history.jsonl` with the slot it went out in.
After a few weeks:

```
python tools/learn.py --refresh
```

It pulls the real engagement each post got (Bluesky and Mastodon, where
metrics are free to read) and reports which slots earn their place. It refuses
to draw conclusions from fewer than 10 posts in a slot, because one post that
happens to do well would otherwise rewrite your whole schedule.

**Every platform keeps its own place in the queue.** Connect LinkedIn six
weeks from now and it starts at post 1 and works through the whole bank —
it does not skip to whatever the others are on today.

**A platform with no tokens is skipped, never failed.** That is how you turn
accounts on one at a time: add the secret, it starts posting on the next run.
A platform that errors never stops the others.

## The three phases

`config.yaml` decides which set of posts is live:

| phase | what it is | when |
|---|---|---|
| `testers` | recruiting the 12 closed testers Google requires before PulseSoul can go to production | **now** |
| `launch` | PulseSoul is live on Play | switch on launch day |
| `evergreen` | 40 feature and story posts that keep cycling | after launch |

Change one word in `config.yaml`, commit, done.

## Commands

```
python autopost.py --status              what is connected, and when each posts next
python autopost.py --dry-run             writes preview.md, posts nothing
python autopost.py                       posts anything that is due right now
python autopost.py --force               post now, ignoring the schedule
python autopost.py --only telegram --force
python autopost.py --dry-run --now "2026-08-19 20:17"   test any moment in time
python tools/check.py                    validates content and schedule
python tools/simulate.py --chaos         proves the schedule under a bad runner
python tools/learn.py --refresh          what your real audience responded to
python tools/render_images.py            rebuild rendered/ after adding screenshots
```

## Editing the content

Open `content/posts.json`. Each entry:

```json
{ "id": "e41", "phase": "evergreen", "image": "pulsesoul_05",
  "english": "...", "hinglish": "..." }
```

- `image` is a filename in `assets/screenshots/` without the extension.
  Leave it `""` for text-only.
- Facebook and Instagram use `hinglish`. Everything else uses `english`.
- Run `python tools/check.py` afterwards. The workflow runs it too, before
  anything is sent, so a bad edit stops there instead of going out to eight
  live accounts.

The checker fails if a post would be cut off mid-sentence on a short platform,
if an image is missing, if a post makes a claim the app cannot back up, or —
the subtle one — if shortening a post for Bluesky would **drop a safety
qualifier while keeping the claim it qualifies**. Bluesky's 300-character
limit means long posts get trimmed, and "an SOS that reaches your family
loudly" minus "it is not an emergency service" is exactly the sentence that
gets an app pulled.

## Claims this project will not make

`tools/check.py` blocks these, deliberately:

- **end-to-end encryption** — messages are encrypted in transit and at rest,
  but the server holds the keys. Saying otherwise would be false advertising.
- **SOS contacting emergency services** — SOS alerts confirmed family members
  and nothing else.
- **anything medical about CareShield** — it is not a health device, it does
  not detect falls, and it reads nothing.

These are the same three lines that get apps rejected from the Play Store, so
they are enforced in code rather than left to memory.

## Adding new artwork

1. Drop new store screenshots into `assets/screenshots/` (any size).
2. `python tools/render_images.py`
3. Reference the filename stem in `content/posts.json`.

The renderer scales your art to fit and fills the leftover space with a
blurred copy of the same image, so the background gradient just continues. It
draws nothing.
