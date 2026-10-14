"""Reads Open Graph metadata (title, description, image) for link previews."""
import html
import re

import requests

USER_AGENT = "Mozilla/5.0 (compatible; post-publisher; +https://codersite.dev)"
_META = re.compile(r"<meta\s+[^>]*>", re.IGNORECASE)
_ATTR = re.compile(r'(\w[\w:-]*)\s*=\s*("([^"]*)"|\'([^\']*)\')')


def fetch_og(url, timeout=10):
    """Return {'title','description','image'} (any may be missing). Never raises."""
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException:
        return {}
    found = {}
    for tag in _META.findall(resp.text):
        attrs = {m.group(1).lower(): m.group(3) if m.group(3) is not None else m.group(4)
                 for m in _ATTR.finditer(tag)}
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key in ("og:title", "og:description", "og:image") and attrs.get("content"):
            found.setdefault(key[3:], html.unescape(attrs["content"]).strip())
    return found


def fetch_image(url, max_bytes, timeout=10):
    """Return image bytes, or None if unavailable or larger than max_bytes."""
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException:
        return None
    if not resp.headers.get("Content-Type", "").startswith("image/") or len(resp.content) > max_bytes:
        return None
    return resp.content
