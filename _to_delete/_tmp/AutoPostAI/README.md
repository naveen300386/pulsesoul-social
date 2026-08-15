# AutoPostAI — PulseSoul social autoposter

Posts PulseSoul content to Facebook, Instagram, Threads, Telegram, Bluesky,
Mastodon, LinkedIn and Pinterest — twice a day, on GitHub's servers, for free,
with your PC switched off.

**Start here: [SETUP.md](SETUP.md).** After the first two steps (about 20
minutes) it is already posting.

---

## How it works

```
content/posts.json   60 posts, each with English + Hinglish copy
      +
assets/screenshots/  your real Play Store art
      ↓
rendered/            the same art reframed for each platform's shape
      ↓
autopost.py          picks the next unsent post, posts it everywhere
      ↓
content/state.json   remembers what went where, so nothing repeats
```

Run twice a day by `.github/workflows/autopost.yml` at 09:00 and 20:00 IST.

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
python autopost.py --status      what is connected, how far the queue is
python autopost.py --dry-run     writes preview.md, posts nothing
python autopost.py               posts one item to every connected account
python autopost.py --only telegram
python tools/check.py            validates the content bank
python tools/render_images.py    rebuild rendered/ after adding screenshots
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
