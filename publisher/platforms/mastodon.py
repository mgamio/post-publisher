"""Mastodon publisher. Needs MASTODON_INSTANCE (e.g. https://mastodon.social) and
MASTODON_ACCESS_TOKEN (Preferences > Development > New application, scope write:statuses).

The link is part of the text; the instance builds the preview card itself."""
import os
import uuid

import requests

REQUIRED_ENV = ["MASTODON_INSTANCE", "MASTODON_ACCESS_TOKEN"]


def publish(post, rendered):
    instance = os.environ["MASTODON_INSTANCE"].rstrip("/")
    if not instance.startswith("https://"):
        instance = "https://" + instance
    resp = requests.post(
        f"{instance}/api/v1/statuses",
        headers={
            "Authorization": f"Bearer {os.environ['MASTODON_ACCESS_TOKEN']}",
            # a retried request with the same key will not create a second post
            "Idempotency-Key": str(uuid.uuid4()),
        },
        data={"status": rendered.text, "visibility": "public", "language": "en"},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Mastodon returned {resp.status_code}: {resp.text[:300]}")
    return resp.json()["url"]
