"""Turns a Post into the text a given platform will publish."""
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ELLIPSIS = "…"


@dataclass(frozen=True)
class Rendered:
    text: str
    link: str  # empty for text-only posts; for link_in_text platforms it is also inside text
    tags: tuple  # hashtags included in text


def add_utm(link, platform, utm_cfg):
    if not link:
        return link
    parts = urlsplit(link)
    host = parts.hostname or ""
    if not any(host == d or host.endswith("." + d) for d in utm_cfg.get("domains", [])):
        return link
    query = dict(parse_qsl(parts.query))
    query.setdefault("utm_source", platform)
    query.setdefault("utm_medium", utm_cfg.get("medium", "social"))
    query.setdefault("utm_campaign", utm_cfg.get("campaign", "post-publisher"))
    return urlunsplit(parts._replace(query=urlencode(query)))


def render(post, platform, platform_cfg, utm_cfg):
    """Layout: text, then the link (if it goes in the text), then hashtags.

    If too long, hashtags are dropped from the end first, then the text is shortened.
    """
    max_len = platform_cfg["max_len"]
    link = add_utm(post.link, platform, utm_cfg)
    inline_link = link if platform_cfg.get("link_in_text", False) else ""
    tags = post.tag_list[: platform_cfg.get("max_tags", 0)]

    def layout(body, tags):
        head = f"{body}\n{inline_link}" if inline_link else body
        return "\n\n".join([head, " ".join(tags)]) if tags else head

    def measure(text):
        url_len = platform_cfg.get("url_len")
        return len(text) - len(inline_link) + url_len if inline_link and url_len else len(text)

    while tags and measure(layout(post.text, tags)) > max_len:
        tags = tags[:-1]
    body = post.text
    overflow = measure(layout(body, tags)) - max_len
    if overflow > 0:
        body = body[: len(body) - overflow - len(ELLIPSIS)].rstrip() + ELLIPSIS
    return Rendered(text=layout(body, tags), link=link, tags=tuple(tags))
