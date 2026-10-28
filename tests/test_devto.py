from datetime import datetime, timezone

from publisher import devto
from publisher.rotation import load_state

UTM = {"domains": ["codersite.dev"], "medium": "social", "campaign": "post-publisher"}

POST = """---
layout: post
title:  "Merge Two Sorted Lists in Java"
description: "Two pointers, O(n + m)."
image: /assets/images/merge.jpg
---

Intro with a [link](/big-o/){:target="_blank"} and an image:

![diagram](/assets/images/d.png "diagram"){:class="img-responsive"}

As [Effective Java](https://amzn.to/1) says, and as my book [**Top Java Challenges**](https://link.amazon/2) shows.

<div>
{%- include inArticleAds.html -%}
</div>

For the theory, this is the classic reference:

<div>
{%- include effectiveJava.html -%}
</div>

Practice with real interview questions:

<div>
{%- include jediJavaInterviewAds.html -%}
</div>

<div>
{% include buymeacoffee.html %}
</div>

<br/>
"""


def make_blog(tmp_path):
    (tmp_path / "_posts").mkdir(parents=True)
    (tmp_path / "_includes").mkdir()
    (tmp_path / "_posts" / "2021-08-04-merge-two-sorted-lists.md").write_text(POST, encoding="utf-8")
    (tmp_path / "_includes" / "jediJavaInterviewAds.html").write_text(
        '<center><a href="https://link.amazon/x" target="_blank"><img alt="codersite" '
        'src="{{ site.baseurl }}/assets/images/book.jpg" ></a></center>', encoding="utf-8")
    (tmp_path / "_includes" / "effectiveJava.html").write_text(
        '<center><a href="https://amzn.to/3" target="_blank"><img alt="codersite" '
        'src="{{ site.baseurl }}/recommended/images/effectiveJava.jpg" ></a></center>', encoding="utf-8")
    (tmp_path / "_includes" / "inArticleAds.html").write_text('<ins class="adsbygoogle"></ins>', encoding="utf-8")
    return tmp_path


def test_canonical_url_follows_jekyll_permalinks():
    assert devto.slug_of("_posts/2022-04-26-spring boot oauth2.md") == "spring-boot-oauth2"
    assert devto.slug_of("_posts/2022-11-12-assemble-parts-in-minimum.time.md") == "assemble-parts-in-minimum.time"
    assert devto.canonical_url("_posts/2022-11-04-x..md", {"permalink": "/how-503/"}) == "https://codersite.dev/how-503/"


def test_article_has_no_jekyll_markup_and_absolute_urls(tmp_path):
    blog = make_blog(tmp_path)
    article = devto.build_article(blog / "_posts" / "2021-08-04-merge-two-sorted-lists.md", ["java"], UTM, False)
    body = article["body_markdown"]

    assert article["canonical_url"] == "https://codersite.dev/merge-two-sorted-lists/"
    assert article["main_image"] == "https://codersite.dev/assets/images/merge.jpg"
    assert article["published"] is False
    for leftover in ["{%", "{{", "{:", "adsbygoogle", "buymeacoffee", "<div>"]:
        assert leftover not in body
    assert "[link](https://codersite.dev/big-o/)" in body
    assert "![diagram](https://codersite.dev/assets/images/d.png" in body
    # the author's own book links to its landing page, so the footer doesn't repeat the books
    assert "[![The Code Interview, book cover](https://codersite.dev/assets/images/book.jpg)]" \
           "(https://codersite.dev/book/theCodeInterview.html?utm_source=devto" in body
    assert "Originally published at [codersite.dev](https://codersite.dev/merge-two-sorted-lists/?utm_source=devto" in body
    assert "Software That Can Change" not in body
    # other authors' books: the cover and its lead-in are dropped, an inline link keeps only its text
    assert "effectiveJava.jpg" not in body and "classic reference" not in body
    assert "As Effective Java says" in body
    assert "[**Top Java Challenges**](https://codersite.dev/book/theCodeInterview.html?utm_source=devto" in body
    assert "amzn.to" not in body and "link.amazon" not in body


def test_publishes_next_in_queue_once_per_slot_drafts_first(tmp_path, monkeypatch):
    blog = make_blog(tmp_path / "blog")
    queue = tmp_path / "devto.csv"
    queue.write_text("slug,tags\nmerge-two-sorted-lists,java algorithms\n", encoding="utf-8")
    config = tmp_path / "config.toml"
    config.write_text('[schedule]\ntimezone = "Europe/Berlin"\n[devto]\npost_at = ["10:10"]\ndays = ["thu"]\n'
                      'drafts = 1\n', encoding="utf-8")
    state = tmp_path / "devto.json"
    sent = []
    monkeypatch.setenv("DEVTO_API_KEY", "k")
    monkeypatch.setattr(devto, "publish", lambda article: sent.append(article) or "https://dev.to/me/merge")
    args = ["--blog-dir", str(blog), "--due", "--queue", str(queue), "--state", str(state), "--config", str(config)]

    thursday = datetime(2026, 10, 29, 10, 0, tzinfo=timezone.utc)  # 11:00 Berlin
    assert devto.main(args, now=thursday) == 0
    assert len(sent) == 1 and sent[0]["published"] is False and sent[0]["tags"] == ["java", "algorithms"]
    assert load_state(state)["history"][0]["id"] == "merge-two-sorted-lists"

    # same slot again, and the next Thursday with nothing left: nothing more is sent
    assert devto.main(args, now=thursday) == 0
    assert devto.main(args, now=datetime(2026, 11, 5, 10, 0, tzinfo=timezone.utc)) == 0
    assert len(sent) == 1
