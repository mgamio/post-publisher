import pytest

from publisher.content import Post
from publisher.formatter import Rendered
from publisher.platforms import x


class FakeResponse:
    ok = True
    status_code = 201

    def json(self):
        return {"data": {"id": "123", "text": "hello"}}


def test_signature_matches_the_x_documentation_example():
    # https://developer.x.com/en/docs/authentication/oauth-1-0a/creating-a-signature
    header = x.oauth1_header(
        "POST", "https://api.twitter.com/1.1/statuses/update.json",
        {"status": "Hello Ladies + Gentlemen, a signed OAuth request!", "include_entities": "true"},
        "xvz1evFS4wEEPTGEFPHBog", "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw",
        "370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb", "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE",
        nonce="kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg", timestamp=1318622958)
    assert 'oauth_signature="hCtSmYh%2BiHYCEqBWrE7C7hYmtUk%3D"' in header


def test_posts_text_as_json(monkeypatch):
    calls = []
    for name in x.REQUIRED_ENV:
        monkeypatch.setenv(name, "secret")
    monkeypatch.setattr(x.requests, "post", lambda url, **kw: calls.append((url, kw)) or FakeResponse())

    url = x.publish(Post(id="1", type="quote", text="q"), Rendered(text="hello\n\n#java", link="", tags=("#java",)))

    assert url == "https://x.com/i/web/status/123"
    called_url, kw = calls[0]
    assert called_url == "https://api.x.com/2/tweets"
    assert kw["json"] == {"text": "hello\n\n#java"}
    assert kw["headers"]["Authorization"].startswith("OAuth ")


@pytest.mark.parametrize("text", ["see codersite.dev", "a CLAUDE.md file", "https://example.com", "www.example"])
def test_refuses_text_with_a_link(monkeypatch, text):
    monkeypatch.setattr(x.requests, "post", lambda *a, **kw: pytest.fail("must not post"))
    with pytest.raises(RuntimeError, match="link"):
        x.publish(Post(id="1", type="quote", text=text), Rendered(text=text, link="", tags=()))
