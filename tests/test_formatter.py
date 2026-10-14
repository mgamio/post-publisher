from publisher.content import Post, eligible_posts
from publisher.formatter import add_utm, render

UTM = {"domains": ["codersite.dev"], "medium": "social", "campaign": "test"}
LINK_CARD = {"max_len": 300, "link_in_text": False, "max_tags": 2}
INLINE = {"max_len": 100, "link_in_text": True, "url_len": 23, "max_tags": 3}


def test_utm_only_on_configured_domains():
    assert add_utm("https://codersite.dev/a/", "bluesky", UTM) == \
        "https://codersite.dev/a/?utm_source=bluesky&utm_medium=social&utm_campaign=test"
    assert add_utm("https://amzn.to/3LuO5X8", "bluesky", UTM) == "https://amzn.to/3LuO5X8"
    assert add_utm("", "bluesky", UTM) == ""


def test_link_card_platform_keeps_link_out_of_text():
    post = Post(id="1", type="article", text="Hello", link="https://codersite.dev/a/", tags="#a #b #c")
    r = render(post, "bluesky", LINK_CARD, UTM)
    assert r.text == "Hello\n\n#a #b"
    assert r.link.startswith("https://codersite.dev/a/?utm_source=bluesky")


def test_inline_link_counts_as_url_len():
    long_url = "https://example.com/" + "x" * 200
    post = Post(id="1", type="article", text="Hi", link=long_url, tags="#a")
    r = render(post, "mastodon", INLINE, UTM)
    assert r.text == f"Hi\n{long_url}\n\n#a"


def test_tags_dropped_before_text_is_shortened():
    post = Post(id="1", type="quote", text="x" * 90, tags="#one #two")
    r = render(post, "x", {"max_len": 100, "max_tags": 2}, UTM)
    assert r.text == "x" * 90 + "\n\n#one"


def test_text_shortened_with_ellipsis_when_needed():
    post = Post(id="1", type="quote", text="word " * 50, tags="#t")
    r = render(post, "x", {"max_len": 50, "max_tags": 1}, UTM)
    assert len(r.text) <= 50
    assert r.text.endswith("…")


def test_text_only_platform_excludes_posts_with_links():
    posts = [Post(id="1", type="quote", text="q"),
             Post(id="2", type="book", text="b", link="https://amzn.to/x"),
             Post(id="3", type="quote", text="q", platforms="bluesky,mastodon")]
    assert [p.id for p in eligible_posts(posts, "x", {"text_only": True})] == ["1"]
    assert [p.id for p in eligible_posts(posts, "mastodon", {})] == ["1", "2", "3"]
