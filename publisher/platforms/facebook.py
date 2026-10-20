"""Facebook Page publisher (Graph API). Needs FACEBOOK_PAGE_ID and FACEBOOK_PAGE_TOKEN,
both printed by tools/facebook_auth.py (the page token does not expire).

The link is sent separately; Facebook builds the preview card from the page itself."""
import os
import tomllib
from pathlib import Path

import requests

REQUIRED_ENV = ["FACEBOOK_PAGE_ID", "FACEBOOK_PAGE_TOKEN"]
ROOT = Path(__file__).resolve().parents[2]
# Graph API error codes meaning the token is invalid, expired or lacks permission
_AUTH_ERRORS = {102, 190, 200, 10}


def api_version():
    config = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
    return config["platforms"]["facebook"]["api_version"]


def publish(post, rendered):
    page_id = os.environ["FACEBOOK_PAGE_ID"]
    data = {"message": rendered.text, "access_token": os.environ["FACEBOOK_PAGE_TOKEN"]}
    if rendered.link:
        data["link"] = rendered.link
    resp = requests.post(f"https://graph.facebook.com/{api_version()}/{page_id}/feed", data=data, timeout=30)
    if not resp.ok:
        error = resp.json().get("error", {}) if resp.headers.get("content-type", "").startswith(
            ("application/json", "text/javascript")) else {}
        if error.get("code") in _AUTH_ERRORS:
            raise RuntimeError(f"Facebook token rejected ({error.get('message')}): "
                               "run tools/facebook_auth.py and update the secrets")
        raise RuntimeError(f"Facebook returned {resp.status_code}: {resp.text[:300]}")
    # the id is "<page id>_<post id>"
    return f"https://www.facebook.com/{resp.json()['id']}"
