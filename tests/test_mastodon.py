from publisher.content import Post
from publisher.formatter import Rendered
from publisher.platforms import mastodon


class FakeResponse:
    ok = True
    status_code = 200

    def json(self):
        return {"url": "https://mastodon.example/@me/1"}


def test_posts_text_with_bearer_token(monkeypatch):
    calls = []
    monkeypatch.setenv("MASTODON_INSTANCE", "mastodon.example/")
    monkeypatch.setenv("MASTODON_ACCESS_TOKEN", "secret")
    monkeypatch.setattr(mastodon.requests, "post", lambda url, **kw: calls.append((url, kw)) or FakeResponse())

    url = mastodon.publish(Post(id="1", type="quote", text="q"), Rendered(text="hello\n\n#java", link="", tags=("#java",)))

    assert url == "https://mastodon.example/@me/1"
    called_url, kw = calls[0]
    assert called_url == "https://mastodon.example/api/v1/statuses"
    assert kw["headers"]["Authorization"] == "Bearer secret"
    assert kw["data"]["status"] == "hello\n\n#java"
