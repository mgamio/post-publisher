"""Republish codersite.dev articles on DEV (dev.to), one per scheduled slot.

    python -m publisher.devto --blog-dir blog --due       # publish the next article if [devto] is due
    python -m publisher.devto --blog-dir blog --dry-run   # preview the next article, posts and saves nothing

The articles are the Jekyll markdown files in the blog repository (_posts/). The order
is content/devto.csv (slug, DEV tags); each slug is published once. canonical_url
points to codersite.dev, so search engines keep crediting the original. The first
`drafts` articles are created as unpublished drafts to review on dev.to.
Needs DEVTO_API_KEY (dev.to > Settings > Extensions > DEV Community API Keys).
"""
import argparse
import csv
import os
import re
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import requests

from .content import Post
from .formatter import add_utm
from .rotation import load_state, record, save_state
from .schedule import is_due, last_posted_at

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://codersite.dev"
API_URL = "https://dev.to/api/articles"
REQUIRED_ENV = ["DEVTO_API_KEY"]

INTERVIEW_BOOK = f"{SITE}/book/theCodeInterview.html"
DESIGN_BOOK = f"{SITE}/book/softwareDesignPrinciplesV2.html"
# the blog's includes for the author's own books link to Amazon; on DEV they link to the landing
# pages. Includes for other authors' books, ads and the coffee button are left out.
OWN_BOOKS = {
    "jediJavaInterviewAds": (INTERVIEW_BOOK, "The Code Interview"),
    "algorithmsBook": (INTERVIEW_BOOK, "The Code Interview"),
    "softwareDesign": (DESIGN_BOOK, "Software That Can Change"),
    "softwareDesignAd1": (DESIGN_BOOK, "Software That Can Change"),
}
DROPPED_BOOK = "<<dropped book>>"
# inline Amazon links in the text: the author's books (any edition's title) go to their landing
# page, other books keep their title as plain text
AMAZON_LINK = r"\[([^\]]+)\]\(https?://(?:amzn\.to|link\.amazon|(?:www\.)?amazon\.[a-z.]+)/[^)\s]*\)"
OWN_TITLES = [("software design", DESIGN_BOOK), ("code interview", INTERVIEW_BOOK),
              ("java challenges", INTERVIEW_BOOK), ("java coding interview", INTERVIEW_BOOK)]

FOOTER = "\n---\n\n*Originally published at [codersite.dev]({link}).*\n"
BOOKS = ("\nPreparing for a Java interview? [The Code Interview]({interview}) solves 48 real questions step by step, "
         "with the clarifying questions to ask and tested code. Want code that stays easy to change? "
         "[Software That Can Change]({design}) shows how, with a real billing system in plain Java.\n")


def split_front_matter(text):
    m = re.match(r"---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}, text
    front = {}
    for line in m.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and not line.startswith((" ", "\t")):
            front[key.strip()] = value.strip().strip("\"'")
    return front, text[m.end():]


def slug_of(path):
    """Jekyll's :title for a post file: the name without date and extension, spaces as hyphens."""
    name = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", Path(path).stem)
    return name.rstrip(".").replace(" ", "-")


def canonical_url(path, front):
    permalink = front.get("permalink") or f"/{slug_of(path)}/"
    return SITE + permalink


def include_as_markdown(name, includes_dir, utm_cfg):
    """One of the author's books as a linked cover image; any other include is dropped."""
    path = Path(includes_dir) / f"{name}.html"
    html = path.read_text(encoding="utf-8") if path.is_file() else ""
    img = re.search(r'<a href="https://[^"]+"[^>]*>\s*<img [^>]*src="([^"]+)"', html)
    if name not in OWN_BOOKS:
        return DROPPED_BOOK if img else ""
    href, title = OWN_BOOKS[name]
    src = img.group(1).replace("{{ site.baseurl }}", SITE)
    return f"\n[![{title}, book cover]({src})]({add_utm(href, 'devto', utm_cfg)})\n\n"


def amazon_link(text, utm_cfg):
    for words, page in OWN_TITLES:
        if words in text.lower():
            return f"[{text}]({add_utm(page, 'devto', utm_cfg)})"
    return text


def to_devto_markdown(body, includes_dir, utm_cfg):
    """Jekyll/kramdown markdown -> DEV markdown: no Liquid, no kramdown attributes, absolute URLs."""
    body = re.sub(r"(?:<div>\s*)?\{%-?\s*include\s+(\w+)\.html\s*-?%\}(?:\s*</div>)?\s*",
                  lambda m: include_as_markdown(m.group(1), includes_dir, utm_cfg), body)
    # a paragraph that introduces a dropped book ("... this is the reference:") goes with it
    body = re.sub(r"(?m)^[^\n]*:[ \t]*\n+(?=" + re.escape(DROPPED_BOOK) + ")", "", body)
    body = body.replace(DROPPED_BOOK, "\n\n")
    body = re.sub(AMAZON_LINK, lambda m: amazon_link(m.group(1), utm_cfg), body)
    body = re.sub(r"\{%-?.*?-?%\}", "", body)  # any other Liquid tag (DEV would try to run it)
    body = body.replace("{{ site.baseurl }}", "")
    body = re.sub(r"\{:[^}]*\}", "", body)  # kramdown attributes like {:target="_blank"}
    body = re.sub(r"<style.*?</style>", "", body, flags=re.S)
    body = re.sub(r'(\]\(|src=")/(?!/)', rf"\g<1>{SITE}/", body)  # site-relative links and images
    body = re.sub(r"(?:\s*<br\s*/?>)+\s*$", "", body.rstrip())  # trailing spacers
    return re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"


def build_article(path, tags, utm_cfg, published):
    """path: a post in <blog>/_posts; its includes are read from <blog>/_includes."""
    path = Path(path)
    front, body = split_front_matter(path.read_text(encoding="utf-8"))
    link = canonical_url(path, front)
    body = to_devto_markdown(body, path.parent.parent / "_includes", utm_cfg)
    footer = FOOTER.format(link=add_utm(link, "devto", utm_cfg))
    if INTERVIEW_BOOK not in body and DESIGN_BOOK not in body:
        footer += BOOKS.format(interview=add_utm(INTERVIEW_BOOK, "devto", utm_cfg),
                               design=add_utm(DESIGN_BOOK, "devto", utm_cfg))
    article = {
        "title": front["title"],
        "body_markdown": body + footer,
        "published": published,
        "canonical_url": link,
        "description": front.get("description", ""),
        "tags": tags[:4],
    }
    if front.get("image"):
        article["main_image"] = SITE + front["image"] if front["image"].startswith("/") else front["image"]
    return article


def load_queue(path):
    with open(path, encoding="utf-8", newline="") as f:
        return [(r["slug"], r["tags"].split()) for r in csv.DictReader(f)]


def find_post(blog_dir, slug):
    for path in sorted((Path(blog_dir) / "_posts").iterdir()):
        if path.is_file() and slug_of(path) == slug:
            return path
    raise FileNotFoundError(f"no post for slug '{slug}' in {blog_dir}/_posts")


def publish(article):
    resp = requests.post(
        API_URL,
        headers={"api-key": os.environ["DEVTO_API_KEY"], "Accept": "application/vnd.forem.api-v1+json",
                 "User-Agent": "post-publisher (+https://codersite.dev)"},
        json={"article": article},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"DEV returned {resp.status_code}: {resp.text[:300]}")
    return resp.json()["url"]


def main(argv=None, now=None):
    parser = argparse.ArgumentParser(prog="publisher.devto", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--blog-dir", required=True, type=Path, help="checkout of the blog repository")
    parser.add_argument("--due", action="store_true", help="only publish if a [devto] posting time has come")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--config", default=ROOT / "config.toml", type=Path)
    parser.add_argument("--queue", default=ROOT / "content" / "devto.csv", type=Path)
    parser.add_argument("--state", default=ROOT / "state" / "devto.json", type=Path)
    args = parser.parse_args(argv)

    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    cfg = config["devto"]
    now = now or datetime.now(timezone.utc)
    state = load_state(args.state)

    if args.due and not is_due(cfg, last_posted_at(state), now, config["schedule"]["timezone"]):
        print("devto: not due")
        return 0
    if not args.dry_run and not os.environ.get("DEVTO_API_KEY"):
        print("::warning::devto is due but DEVTO_API_KEY not set, skipping")
        return 0

    done = {h["id"] for h in state["history"]}
    queue = [(slug, tags) for slug, tags in load_queue(args.queue) if slug not in done]
    if not queue:
        print("devto: every article in the queue is published")
        return 0
    slug, tags = queue[0]
    published = len(done) >= cfg.get("drafts", 0)
    article = build_article(find_post(args.blog_dir, slug), tags, config.get("utm", {}), published)

    if args.dry_run:
        print(f"--- [devto] {slug} ({'published' if published else 'draft'}), tags {article['tags']}")
        print(f"title: {article['title']}\ncanonical: {article['canonical_url']}\n")
        print(article["body_markdown"])
        return 0
    url = publish(article)
    record(state, Post(id=slug, type="article", text=article["title"]), url, now=now)
    save_state(args.state, state)
    print(f"{'published' if published else 'draft created'} {slug} on devto: {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
