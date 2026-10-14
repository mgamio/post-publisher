import tomllib
from pathlib import Path

from publisher.content import load_posts
from tools.migrate_txt import parse_line

ROOT = Path(__file__).resolve().parent.parent


def test_parse_line_keeps_semicolons_in_text_and_cleans_link():
    text, link, tags = parse_line("a; b;https://codersi te.dev/x/;#java  #code")
    assert (text, link, tags) == ("a; b", "https://codersite.dev/x/", "#java #code")


def test_real_content_is_valid():
    posts = load_posts(ROOT / "content" / "posts.csv")
    weights = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))["weights"]
    assert posts
    for post in posts:
        assert post.text, post.id
        assert post.type in weights, f"{post.id}: type {post.type} has no weight in config.toml"
        assert not post.link or post.link.startswith("https://"), post.id
