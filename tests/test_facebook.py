import pytest

from publisher.content import Post
from publisher.formatter import Rendered
from publisher.platforms import facebook


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.ok = status_code < 400
        self.body = body
        self.text = str(body)
        self.headers = {"content-type": "application/json; charset=UTF-8"}

    def json(self):
        return self.body


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("FACEBOOK_PAGE_ID", "123")
    monkeypatch.setenv("FACEBOOK_PAGE_TOKEN", "secret")


def test_posts_message_and_link_to_page_feed(env, monkeypatch):
    calls = []
    monkeypatch.setattr(facebook.requests, "post",
                        lambda url, **kw: calls.append((url, kw)) or FakeResponse(200, {"id": "123_456"}))

    url = facebook.publish(Post(id="1", type="article", text="t"),
                           Rendered(text="hello\n\n#java", link="https://codersite.dev/a", tags=("#java",)))

    assert url == "https://www.facebook.com/123_456"
    called_url, kw = calls[0]
    assert called_url == f"https://graph.facebook.com/{facebook.api_version()}/123/feed"
    assert kw["data"] == {"message": "hello\n\n#java", "link": "https://codersite.dev/a", "access_token": "secret"}


def test_no_link_param_without_link(env, monkeypatch):
    calls = []
    monkeypatch.setattr(facebook.requests, "post",
                        lambda url, **kw: calls.append(kw) or FakeResponse(200, {"id": "123_1"}))
    facebook.publish(Post(id="1", type="quote", text="q"), Rendered(text="q", link="", tags=()))
    assert "link" not in calls[0]["data"]


def test_expired_token_gives_clear_message(env, monkeypatch):
    error = {"error": {"message": "Session has expired", "code": 190}}
    monkeypatch.setattr(facebook.requests, "post", lambda url, **kw: FakeResponse(400, error))
    with pytest.raises(RuntimeError, match="facebook_auth.py"):
        facebook.publish(Post(id="1", type="quote", text="q"), Rendered(text="q", link="", tags=()))
