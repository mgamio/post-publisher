# post-publisher

Posts evergreen content (articles, book promotions, quotes) from
[codersite.dev](https://codersite.dev) to social networks on a schedule, using
GitHub Actions. No server needed.

| Platform | Status |
|---|---|
| Bluesky | ✅ 6× a day |
| Mastodon | ✅ 2× a day |
| LinkedIn | ✅ weekdays, articles only |
| Facebook Page | planned |
| X | planned, text-only posts |

## How it works

1. `content/posts.csv` holds every post: `id, type, text, link, tags, platforms, priority, image`.
2. Each run picks the next post for one platform:
   - posts with `priority = new` go first, once per platform;
   - otherwise a content type is drawn using the `[weights]` in `config.toml`, and the
     next post of that type is taken from a shuffled rotation, so every post is used
     before any repeats.
3. The text is adapted to the platform (length limit, number of hashtags, link in the
   text or as a preview card) and links to codersite.dev get UTM tags.
4. The rotation is saved in `state/<platform>.json` and committed back by the workflow.

## Schedule

Posting times are `post_at` (and optional `days`) per platform in `config.toml`, in Berlin
time. GitHub starts scheduled runs late or skips them at busy times, so the workflow runs
every 30 minutes and only posts to a platform when one of its times has passed since its
last post. A skipped run is made up by the next one, and nothing is posted twice: a manual
post also counts for the current time slot. Expect posts up to ~30-60 minutes after the
configured time.

## Editing content

Edit `content/posts.csv` (Excel or any text editor, UTF-8):

- **id**: unique and never reused; the rotation tracks posts by id.
- **type**: `article`, `medium`, `book`, `quote`, `ad`, `external` (any type in `[weights]`).
- **platforms**: `all`, a list like `bluesky,linkedin`, or `none` to disable.
- **priority**: `new` to announce it on every platform before the rotation.
- **image**: optional path in this repo, used as preview image when the page has none
  (e.g. Amazon links).

On X only posts without a link are used; on LinkedIn only `article` posts
(`types` in `config.toml`).

## Running locally

```sh
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # Windows; on Linux/macOS use .venv/bin/
.venv/Scripts/python -m publisher --platform bluesky --dry-run -n 10   # preview
.venv/Scripts/python -m pytest
```

Publishing for real needs the platform's environment variables (below).

## GitHub setup

Add these in **Settings → Secrets and variables → Actions**:

| Secret | Value |
|---|---|
| `BLUESKY_HANDLE` | e.g. `codersite.bsky.social` |
| `BLUESKY_APP_PASSWORD` | bsky.app → Settings → Privacy and security → App passwords |
| `MASTODON_INSTANCE` | your server, e.g. `https://mastodon.social` |
| `MASTODON_ACCESS_TOKEN` | Preferences → Development → New application, scope `write:statuses` only |
| `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_AUTHOR`, `LINKEDIN_TOKEN_EXPIRES` | printed by `python tools/linkedin_auth.py <client id> <client secret>` (renew every 60 days) |

**Actions → post → Run workflow**: `due` with *dry run* checked previews what the schedule
would post now; choosing a platform with *dry run* unchecked posts to it immediately.
