"""X (Twitter) publisher. Needs the app's X_API_KEY and X_API_SECRET, plus the account's
X_ACCESS_TOKEN and X_ACCESS_TOKEN_SECRET (developer portal > your app > Keys and tokens;
set the app permissions to "Read and write" before generating the access token).

OAuth 1.0a user tokens do not expire, so nothing has to be renewed. Only text-only posts
are sent (text_only in config.toml): the API bills a post with a URL much higher than a
plain one, so a text in which X would detect a link is refused instead of posted."""
import base64
import hashlib
import hmac
import os
import re
import secrets
import time
from urllib.parse import quote

import requests

REQUIRED_ENV = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]

API_URL = "https://api.x.com/2/tweets"

# what X turns into a link: a URL, or a bare domain such as codersite.dev or CLAUDE.md
LINK_LIKE = re.compile(r"https?://|www\.|\b[\w-]+\.[A-Za-z]{2,}\b")


def _enc(s):
    return quote(str(s), safe="~-._")


def oauth1_header(method, url, params, consumer_key, consumer_secret, token, token_secret,
                  nonce=None, timestamp=None):
    """Authorization header for an OAuth 1.0a request. params: query/form parameters
    (a JSON body is not part of the signature)."""
    oauth = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": nonce or secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(timestamp or int(time.time())),
        "oauth_token": token,
        "oauth_version": "1.0",
    }
    pairs = sorted((_enc(k), _enc(v)) for k, v in {**params, **oauth}.items())
    base = "&".join([method.upper(), _enc(url), _enc("&".join(f"{k}={v}" for k, v in pairs))])
    key = f"{_enc(consumer_secret)}&{_enc(token_secret)}"
    oauth["oauth_signature"] = base64.b64encode(
        hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    return "OAuth " + ", ".join(f'{_enc(k)}="{_enc(v)}"' for k, v in sorted(oauth.items()))


def publish(post, rendered):
    if rendered.link or LINK_LIKE.search(rendered.text):
        raise RuntimeError(f"{post.id} contains a link, which X bills as a link post; not posted")
    auth = oauth1_header("POST", API_URL, {}, os.environ["X_API_KEY"], os.environ["X_API_SECRET"],
                         os.environ["X_ACCESS_TOKEN"], os.environ["X_ACCESS_TOKEN_SECRET"])
    resp = requests.post(API_URL, headers={"Authorization": auth}, json={"text": rendered.text}, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"X returned {resp.status_code}: {resp.text[:300]}")
    return f"https://x.com/i/web/status/{resp.json()['data']['id']}"
