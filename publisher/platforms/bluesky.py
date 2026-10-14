"""Bluesky publisher. Needs BLUESKY_HANDLE and BLUESKY_APP_PASSWORD
(create an app password at bsky.app > Settings > Privacy and security > App passwords)."""
import os
from pathlib import Path
from urllib.parse import urlsplit

from atproto import Client, client_utils, models

from .linkcard import fetch_image, fetch_og

ROOT = Path(__file__).resolve().parents[2]
MAX_THUMB_BYTES = 950_000  # Bluesky rejects blobs over ~1 MB


def build_text(rendered):
    """Plain text plus clickable hashtag facets."""
    builder = client_utils.TextBuilder()
    tag_line = " ".join(rendered.tags)
    body = rendered.text[: len(rendered.text) - len(tag_line)] if tag_line else rendered.text
    builder.text(body)
    for i, tag in enumerate(rendered.tags):
        if i:
            builder.text(" ")
        builder.tag(tag, tag.lstrip("#"))
    return builder


def build_card(client, link, fallback_title, local_image=""):
    """Link preview card. Pages that block bots (e.g. Amazon) give no metadata,
    so the post text and the post's own image column are used as fallbacks."""
    og = fetch_og(link)
    image = fetch_image(og["image"], MAX_THUMB_BYTES) if og.get("image") else None
    if image is None and local_image:
        path = ROOT / local_image
        if path.is_file() and path.stat().st_size <= MAX_THUMB_BYTES:
            image = path.read_bytes()
    thumb = client.upload_blob(image).blob if image else None
    return models.AppBskyEmbedExternal.Main(
        external=models.AppBskyEmbedExternal.External(
            uri=link,
            title=og.get("title") or fallback_title,
            description=og.get("description") or urlsplit(link).hostname or "",
            thumb=thumb,
        )
    )


def publish(post, rendered):
    handle = os.environ["BLUESKY_HANDLE"]
    client = Client()
    client.login(handle, os.environ["BLUESKY_APP_PASSWORD"])
    embed = build_card(client, rendered.link, post.text[:100], post.image) if rendered.link else None
    resp = client.send_post(build_text(rendered), embed=embed, langs=["en"])
    rkey = resp.uri.rsplit("/", 1)[-1]
    return f"https://bsky.app/profile/{handle}/post/{rkey}"
