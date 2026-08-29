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
autopost.py           wakes, posts whoever is due, then keeps watching
      ↓
content/state.json    what has been posted, so nothing repeats
content/history.jsonl what went out when, so tools/learn.py can improve it
```

## Staying alive

`cron:` on GitHub's free tier is a hint, not a promise. In August 2026 delivery
on this repo fell from ~17 runs a day to 2, without a single red run, and
posting dropped by 92% for three days before anyone noticed. Four independent
things now have to fail before that can happen again:

1. **The watchdog loop.** A run stays alive 5.5 hours re-checking the schedule
   every 5 minutes and pushing state after each cycle, so one delivered cron
   covers a block of the day rather than one instant of it.
2. **Two cron entries** at different minutes — GitHub drops each separately.
3. **The self-chain.** Each run asks for its successor before exiting, so the
   cron only has to restart a chain that has broken. Needs the `DISPATCH_TOKEN`
   secret; without it the workflow says so in a warning every run.
4. **`repository_dispatch`.** Any external pinger can wake it with one POST.

And when all four fail, the health job scores the last 48 hours of slots and
turns the run red, so you get an email instead of silence. Set the
`AUTOPOST_PAUSE` repository variable to `1` to stop the whole thing.

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
python tools/health.py                   is it actually still posting? (red = no)
python tools/simulate.py --chaos         proves the schedule under a bad runner
python tools/simulate.py --wakes-per-day 2 --watch 330 --chain --faults
                                         proves it survives GitHub throttling the cron
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

## Festival greetings

On Diwali, Holi, Raksha Bandhan, Independence Day and fifteen other occasions,
Facebook and Instagram post a greeting instead of the marketing post that was
due. One post that day, at the first slot, then silence until tomorrow. The
marketing post is not consumed -- the queue does not advance -- so it goes out
at the next slot instead.

    content/festivals.json      the greetings and the dated calendar
    tools/make_greeting.py      rebuilds the cards
    core/festivals.py           the date lookup and the once-a-day guard

Only Facebook and Instagram take part. LinkedIn, Bluesky and Mastodon are left
out on purpose: a Diwali greeting reads warmly to family-app followers in India
and as noise to a global feed.

**The calendar is hand-dated and it will run out.** Hindu festivals follow a
lunar calendar, so no code can compute them -- every date in the file was
checked against a published panchang for that specific year. `tools/check.py`
warns when fewer than 90 days remain and fails outright when the list is empty.
When that happens, look the dates up. Do not estimate them: a Diwali greeting
posted a day late is worse than none at all.

The cards are typographic -- the brand gradient, Poppins, and nothing drawn.
They are built 1080x1350 rather than 1080x1920, because with no phone in the
frame the taller shape left a third of the card empty.
