# Setting up AutoPostAI

Work top to bottom. Each block is self-contained — after **Step 1 + Step 2**
you are already posting twice a day, and you can add the rest whenever.

Nothing here costs money. Time estimates are honest.

| Step | Platform | Your time | Waiting on someone? |
|------|----------|-----------|---------------------|
| 1 | GitHub (the engine) | 15 min | no |
| 2 | Telegram | 5 min | no |
| 3 | Bluesky | 5 min | no |
| 4 | Mastodon | 10 min | no |
| 5 | Facebook Page + Instagram | 60 min | no |
| 6 | Threads | 30 min | no |
| 7 | LinkedIn company page | 30 min | yes — 1 to 4 weeks, and there is an eligibility gate |
| 8 | Pinterest | 30 min | yes — two separate reviews |

---

## Step 1 — Put the project on GitHub

**Make the repository public.** Two reasons, both practical:

- GitHub Actions is **unlimited and free on public repos**. On private repos
  you get 2,000 minutes a month and this would eat into them.
- Instagram and Threads do not accept uploaded image bytes. They fetch the
  picture from a public URL. A public repo gives you that URL for free.
  *(Facebook, Telegram, Bluesky, Mastodon, LinkedIn and Pinterest all take the
  bytes directly, so they do not care either way.)*

Your tokens are **not** in the repo. They go into GitHub Secrets, which are
encrypted before they ever reach GitHub, cannot be read back after saving, are
auto-redacted from logs, and — importantly for a public repo — **are not
passed to workflows triggered from a forked repository**. Nobody can fork this
and print your tokens. What is public is your marketing copy and your store
screenshots, both of which are going on the internet anyway.

1. Go to <https://github.com/new>
2. Repository name: `pulsesoul-social`
3. Choose **Public**. Do not tick "Add a README".
4. Click **Create repository**.
5. Open PowerShell and paste this whole block:

```powershell
cd "D:\AI_Projects\Anthropic\AutoPostAI"

git init
git add .
git commit -m "AutoPostAI: PulseSoul social autoposter"
git branch -M main
git remote add origin https://github.com/naveen300386/pulsesoul-social.git
git push -u origin main

Write-Host ""
Write-Host "Now open:  https://github.com/naveen300386/pulsesoul-social/settings/secrets/actions" -ForegroundColor Cyan
Write-Host "That is where every token below goes." -ForegroundColor Cyan
```

> If `git push` asks for a password, use a GitHub Personal Access Token, not
> your account password. GitHub stopped accepting passwords for git in 2021.

**Where every token goes from here on:** repository → **Settings** →
**Secrets and variables** → **Actions** → **New repository secret**. Name it
exactly as written below, paste the value, save.

---

## Step 2 — Telegram (5 minutes, easiest one)

1. In Telegram, create a channel: **New Channel** → name it `PulseSoul`.
   Make it **Public** and pick a link like `t.me/pulsesoul`.
   *(It must be public. A private channel needs a numeric `-100…` id instead.)*
2. Search for **@BotFather**, open it, send `/newbot`.
3. Give it a name (`PulseSoul Poster`) and a username ending in `bot`
   (`pulsesoul_poster_bot`).
4. BotFather replies with a long token like `8123456789:AAF...`. Copy it.
5. Open your channel → tap the channel name → **Edit** (pencil) →
   **Administrators** → **Add Admin** → search your bot → give it
   **Post Messages** → save. That is the only right it needs.

| Secret name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | the token from BotFather |
| `TELEGRAM_CHAT_ID` | `@pulsesoul` (your channel's public link name, with the @) |

---

## Step 3 — Bluesky (5 minutes)

1. Sign up at <https://bsky.app> as `pulsesoul.bsky.social`.
2. **Settings** → **Privacy and security** → **App passwords** → **Add App
   Password**. Name it `autopost`.
3. Copy the password it shows — you cannot see it again.

| Secret name | Value |
|---|---|
| `BLUESKY_HANDLE` | `pulsesoul.bsky.social` |
| `BLUESKY_APP_PASSWORD` | the app password (format `xxxx-xxxx-xxxx-xxxx`) |

> An app password can be revoked on its own. Your real password never touches
> this project.

---

## Step 4 — Mastodon (10 minutes)

1. Sign up at <https://mastodon.social>. Signups there are sometimes held for
   manual approval — if so, wait for the email before continuing.
2. In your profile settings, tick **"This is an automated account"**.
   Mastodon's rules require bots to be flagged, and unflagged automation gets
   suspended.
3. **Preferences** → **Development** → **New application**
   (direct link: `mastodon.social/settings/applications/new`).
4. Name: `AutoPostAI`. Tick scopes **`write:statuses`** and **`write:media`**.
   Untick everything else. Submit.
5. Open the application you just made and copy **Your access token**.

| Secret name | Value |
|---|---|
| `MASTODON_INSTANCE` | `https://mastodon.social` |
| `MASTODON_TOKEN` | the access token |

---

## Step 5 — Facebook Page + Instagram (60 minutes)

**The good news, and it is a big one:** you do **not** need Meta App Review,
and you do **not** need Business Verification. Meta's rule is that review is
required when an app touches data you do not own or manage. You are posting to
your own Page from your own admin account, so every permission below is
granted at **Standard Access**, which is automatic. This is what turns a
"2 to 7 day wait" into an afternoon.

**But you do have to flip the app to Live.** Meta's App Modes page is explicit:
*data generated while an app is in Development mode can only be seen by people
with a role on the app.* Leave it in Development and your posts will publish
successfully and be invisible to everyone but you. Going Live is a toggle, not
a review — but Meta will not let you flip it until **Settings → Basic** has a
**Privacy Policy URL** and an **App category**.

**Before you start, get these ready:**

- A Meta developer account: <https://developers.facebook.com> → **Get Started**.
- **2FA switched on** for that Facebook account, or it cannot hold app roles.
- Your privacy policy URL: **`https://pulsesoul.app/privacy/`** — already live,
  so this costs you nothing.

### 5a. The accounts

1. Create a Facebook **Page** for PulseSoul (facebook.com → Pages → Create).
2. On Instagram, create `@pulsesoul` if it does not exist.
3. In the Instagram app: menu → **For professionals** → **Account type and
   tools** → **Switch to professional account** → **Business**.
   *(Instagram will not publish through the API from a personal account. This
   step is not optional.)*
4. Link Instagram to the Page from **Instagram → Edit Profile → Page**, or
   from **Facebook Page → Settings → Linked accounts**.
   **Do not use Settings → Accounts Center.** That is a different, personal
   level of linking, and the API cannot see it — you will get an empty
   response at step 15 with nothing explaining why.

### 5b. The Meta app

5. Go to <https://developers.facebook.com/apps> → **Create app**.
6. Use case: **Other** → type: **Business** → name it `PulseSoul Poster`.
7. Left menu → **Add product** → add **Instagram** and **Facebook Login for
   Business**.
8. **Settings → Basic**: set **Privacy Policy URL** to
   `https://pulsesoul.app/privacy/` and pick an **App category**. Save.
   *(Do this now — you will need it in step 16.)*

### 5c. The tokens

9. Open the **Graph API Explorer**:
   <https://developers.facebook.com/tools/explorer/>
10. Top right: pick your app `PulseSoul Poster`.
11. Click **Add a permission** and tick exactly these five:
    - `pages_show_list`
    - `pages_read_engagement`
    - `pages_manage_posts`
    - `instagram_basic`
    - `instagram_content_publish`
12. Click **Generate Access Token** and approve the popup. You now have a
    **short-lived user token** (about 2 hours).
13. Make it long-lived. Paste this in the Explorer's URL bar and press Submit
    (as a **GET**), replacing the three capitalised parts:

    ```
    /oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=THE_TOKEN_FROM_STEP_12
    ```

    *(App ID and App Secret are in your app's **Settings → Basic**.)*
    Copy the `access_token` it returns — this one lasts about 60 days.

14. **Paste that long-lived token into the Explorer's token box** — this part
    matters — then run:

    ```
    /me/accounts
    ```

    Find your PulseSoul Page in the response. Copy its `id` and its
    `access_token`. **This Page token does not expire**, but only because you
    pasted the long-lived token in first. Skip step 13 and the Page token you
    get here dies in about two hours.

15. Get the Instagram account id — run this with your Page id:

    ```
    /YOUR_PAGE_ID?fields=instagram_business_account
    ```

    Copy the `id` inside `instagram_business_account`. **If this comes back
    empty, step 4 did not take.** Redo the linking, do not continue.

16. Go to your app dashboard and flip the toggle at the top from
    **Development** to **Live**. Without this your posts are invisible to
    everyone except you.

| Secret name | Value |
|---|---|
| `FB_PAGE_ID` | the Page `id` from step 14 |
| `FB_PAGE_TOKEN` | the Page `access_token` from step 14 |
| `IG_USER_ID` | the `instagram_business_account.id` from step 15 |

> Instagram accepts **JPEG only** and fetches the file from a public server.
> The renderer already outputs JPEG into a public repo, so this is handled —
> it only matters if you start pointing at your own images.

---

## Step 6 — Threads (30 minutes)

Threads has its own token, its own domain, and one trap that will waste your
evening if you miss it: **the token the dashboard hands you lasts one hour.**
You must trade it for a 60-day one before it goes into the secret.

No App Review needed here either — a Threads Tester can grant these
permissions directly.

1. Threads is a **use case**, not a product, so "Add product" will not show
   it. Open your app's **Use cases** and look for **Access the Threads API**.
   If it is not offered on this app, create a second app at
   <https://developers.facebook.com/apps> → **Create app** → use case
   **Access the Threads API**.
2. **App roles → Roles → Add People → Threads Tester**, enter your Threads
   username. Then accept it in the Threads app under **Settings → Account →
   Website permissions → Invites**.
3. **Use cases → Customize** (on Access the Threads API) → scroll to **User
   token generator** → **Generate access token**. Tick `threads_basic` and
   `threads_content_publish`.
4. **That token dies in one hour.** Immediately open this in a browser to
   trade it for a 60-day one:

   ```
   https://graph.threads.net/access_token?grant_type=th_exchange_token&client_secret=YOUR_APP_SECRET&access_token=THE_ONE_HOUR_TOKEN
   ```

   The `access_token` in the response is the one that goes in the secret.

5. Get your Threads user id — open this with the 60-day token:

   ```
   https://graph.threads.net/v1.0/me?fields=id,username&access_token=YOUR_60_DAY_TOKEN
   ```

| Secret name | Value |
|---|---|
| `THREADS_USER_ID` | the `id` from step 5 |
| `THREADS_TOKEN` | the 60-day token from step 4 |

> ⚠️ **This is the only token in the project that expires.** Every 60 days,
> run `python tools/refresh_threads.py` and paste the new value over the
> `THREADS_TOKEN` secret. Two rules: the token must be **at least 24 hours
> old** for the refresh to work, and if you let all 60 days lapse the token is
> dead permanently and you have to redo steps 3 and 4. Put a reminder in your
> calendar for day 50.

---

## Step 7 — LinkedIn company page (1 to 4 weeks, with a real gate)

Read this before spending time. LinkedIn grants the Community Management API
only to **registered legal organizations for commercial use**. A solo
developer with no registered entity gets rejected — and **you cannot re-apply
with the same app**, so it is one shot per app.

If you apply through **Vibrant Automations Pvt. Ltd.**, you have the entity.
If PulseSoul is a personal project with no company behind it, skip this step
entirely; nothing else in the project depends on it.

You will need: a business email LinkedIn can verify, the legal name and
registered address, a live website on your own domain (`pulsesoul.app` works),
a privacy policy URL, and **a super admin of the Page to verify the app**.

1. Create a LinkedIn **Company Page** for PulseSoul if you have not.
2. Go to <https://www.linkedin.com/developers/apps> → **Create app**, and
   associate it with that Page.
3. **Products** tab → request **Community Management API**. Use case, plainly:
   *"Publishing our own product updates to our own company page on a schedule."*
4. Have a Page super admin verify the app when LinkedIn prompts.
5. Wait 1–4 weeks.
6. Once approved: **Auth** tab → generate a token with the
   `w_organization_social` scope.
7. Your organisation id is the number in your page admin URL:
   `linkedin.com/company/`**`12345678`**`/admin/`

| Secret name | Value |
|---|---|
| `LINKEDIN_TOKEN` | the access token |
| `LINKEDIN_ORG_ID` | the numeric id, e.g. `12345678` |

> There is also a 12-month clock: Development tier access is revoked if you do
> not reach Standard tier within a year.

---

## Step 8 — Pinterest (do this last)

Two things worth knowing before you spend an evening here:

- **Trial access is itself a review**, not an instant switch. People report
  waiting a week or more.
- On Trial access, every Pin you create is a sandbox object **visible only to
  you**. Pinterest only becomes a real traffic source after **Standard
  access**, which is a second review requiring a screen recording of the
  integration working.

So the sequence is: get Trial → let the poster run → record the video Trial
lets you make → submit for Standard.

1. Convert your Pinterest account to a **Business** account.
2. <https://developers.pinterest.com/apps/> → create an app → apply for Trial
   access. If it stalls, chase it through Pinterest's app-approval help portal.
3. Create a board called `PulseSoul`.
4. Generate a token with `boards:read` and `pins:write`.
5. Get the board id from <https://api.pinterest.com/v5/boards> or the board URL.
6. Once posting works, apply for **Standard access** with a screen recording.

| Secret name | Value |
|---|---|
| `PINTEREST_TOKEN` | the access token |
| `PINTEREST_BOARD_ID` | the board id |

---

## Turning it on

1. Go to your repo → **Actions** tab → **AutoPost** → **Run workflow**.
2. Leave **Preview only** ticked → **Run workflow**.
3. Open the run and read the log. Every connected account should say
   `would send post t01`. Every account you have not set up yet says
   `not connected yet` — that is correct, not an error.
4. Happy? Run it again with **Preview only** unticked **and Force ticked** —
   force skips the schedule so you get a post immediately instead of waiting
   for the next peak slot. Check your accounts.
5. From then on it runs by itself. The workflow wakes every hour; each
   platform posts at its own peak times, set in `config.yaml`.

**To see the schedule** without waiting for it:

```powershell
python autopost.py --status
python tools/simulate.py          # a fortnight of posting, hour by hour
```

**To change the times,** edit `schedule.platforms` in `config.yaml` — not the
workflow. Times are IST, whole hours only.

**About GitHub's timing:** the free scheduler is shared. Runs land 5–30
minutes late routinely and occasionally one is dropped — GitHub never retries
a missed run. That is why each slot stays live for 2 hours rather than needing
an exact hit. If a slot is missed anyway, nothing is lost: the queue only
advances on a successful post, so that post goes out at the next slot instead.

> GitHub disables scheduled workflows on public repos after 60 days of no
> activity. This workflow commits `content/state.json` back after every real
> post, so that timer resets twice a day and will never fire while it is
> actually posting.

## Running it from your own PC instead

```powershell
cd "D:\AI_Projects\Anthropic\AutoPostAI"
python -m pip install -r requirements.txt
Copy-Item .env.example .env      # then open .env and paste your tokens in
python autopost.py --status      # what is connected
python autopost.py --dry-run     # writes preview.md, posts nothing
python autopost.py               # posts for real
```

> In `.env`, remember to change `YOURNAME` in `IMAGE_BASE_URL` to your GitHub
> username, or Instagram and Threads will fail with a confusing image error.

## When something breaks

| What you see | What it means |
|---|---|
| `not connected yet (FB_PAGE_ID, ...)` | that secret is missing or misspelt |
| `HTTP 400` from Facebook mentioning `code 190` | the token expired, the password changed, or permissions were revoked — redo step 5c |
| Posts publish but nobody else can see them | the Meta app is still in Development mode — step 5b/16 |
| `instagram_business_account` comes back empty | Instagram was linked via Accounts Center — redo step 5a.4 |
| `instagram could not fetch the image` | the repo is private, `IMAGE_BASE_URL` is wrong, or the file is not a JPEG |
| Threads worked for an hour then stopped | you saved the one-hour token — redo step 6.4 |
| `HTTP 426` from LinkedIn | the API version in `platforms/linkedin.py` has been sunset — bump `VERSION` |
| `HTTP 400` from Bluesky | the post was over 300 characters — run `python tools/check.py` |
| The whole run is red but some accounts posted | correct behaviour. The ones that worked are recorded and will not repeat; fix the failing one and the next run catches up |
