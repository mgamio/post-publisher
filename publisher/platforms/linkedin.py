"""LinkedIn publisher (personal profile, Posts API). Needs LINKEDIN_ACCESS_TOKEN and
LINKEDIN_AUTHOR (urn:li:person:...), both printed by tools/linkedin_auth.py.
Optional LINKEDIN_TOKEN_EXPIRES (YYYY-MM-DD) gives a warning a week before expiry.

The link becomes an article card; its image is uploaded from the page's og:image."""
import os
import re
import sys
import tomllib
from datetime import date
from pathlib import Path

import requests

from .linkcard import fetch_image, fetch_og

REQUIRED_ENV = ["LINKEDIN_ACCESS_TOKEN", "LINKEDIN_AUTHOR"]
ROOT = Path(__file__).resolve().parents[2]
API = "https://api.linkedin.com/rest"
MAX_IMAGE_BYTES = 5_000_000
# characters with a meaning in LinkedIn's "little text format"; must be escaped in commentary
_RESERVED = re.compile(r"([\\|{}@\[\]()<>#*_~])")


def api_version():
    config = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
    return config["platforms"]["linkedin"]["api_version"]


def build_commentary(rendered):
    """Escaped text, with hashtags as LinkedIn hashtag templates."""
    tag_line = " ".join(rendered.tags)
    body = rendered.text[: len(rendered.text) - len(tag_line)] if tag_line else rendered.text
    tags = " ".join(f"{{hashtag|\\#|{t.lstrip('#')}}}" for t in rendered.tags)
    return _RESERVED.sub(r"\\\1", body) + tags


def warn_if_expiring(today=None):
    expires = os.environ.get("LINKEDIN_TOKEN_EXPIRES")
    if not expires:
        return
    days = (date.fromisoformat(expires) - (today or date.today())).days
    if days <= 7:
        print(f"::warning::LinkedIn token expires in {days} days ({expires}); "
              "run tools/linkedin_auth.py and update the secrets", file=sys.stderr)


def upload_image(session, author, image):
    init = session.post(f"{API}/images?action=initializeUpload",
                        json={"initializeUploadRequest": {"owner": author}}, timeout=30)
    init.raise_for_status()
    value = init.json()["value"]
    put = requests.put(value["uploadUrl"], data=image, timeout=60,
                       headers={"Authorization": session.headers["Authorization"]})
    put.raise_for_status()
    return value["image"]


def build_article(session, author, post, link):
    og = fetch_og(link)
    article = {
        "source": link,
        "title": (og.get("title") or post.text)[:200],
        "description": (og.get("description") or "")[:250],
    }
    image = fetch_image(og["image"], MAX_IMAGE_BYTES) if og.get("image") else None
    if image is None and post.image and (ROOT / post.image).is_file():
        image = (ROOT / post.image).read_bytes()
    if image:
        try:
            article["thumbnail"] = upload_image(session, author, image)
        except requests.RequestException as e:
            print(f"::warning::LinkedIn image upload failed, posting without image: {e}", file=sys.stderr)
    return {"article": article}


def publish(post, rendered):
    warn_if_expiring()
    author = os.environ["LINKEDIN_AUTHOR"]
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {os.environ['LINKEDIN_ACCESS_TOKEN']}",
        "LinkedIn-Version": api_version(),
        "X-Restli-Protocol-Version": "2.0.0",
    })
    body = {
        "author": author,
        "commentary": build_commentary(rendered),
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [],
                         "thirdPartyDistributionChannels": []},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    if rendered.link:
        body["content"] = build_article(session, author, post, rendered.link)

    resp = session.post(f"{API}/posts", json=body, timeout=30)
    if resp.status_code == 401:
        raise RuntimeError("LinkedIn token rejected (expired?): run tools/linkedin_auth.py and update the secrets")
    if not resp.ok:
        raise RuntimeError(f"LinkedIn returned {resp.status_code}: {resp.text[:300]}")
    return f"https://www.linkedin.com/feed/update/{resp.headers['x-restli-id']}/"
