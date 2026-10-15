from datetime import date

from publisher.formatter import Rendered
from publisher.platforms import linkedin


def test_commentary_escapes_reserved_chars_and_templates_hashtags():
    rendered = Rendered(text="Use List<T> (generics) & #1 tip\n\n#java #code", link="", tags=("#java", "#code"))
    assert linkedin.build_commentary(rendered) == \
        "Use List\<T\> \(generics\) & \#1 tip\n\n{hashtag|\#|java} {hashtag|\#|code}"


def test_commentary_without_tags():
    assert linkedin.build_commentary(Rendered(text="a_b", link="", tags=())) == "a\_b"


def test_expiry_warning(monkeypatch, capsys):
    monkeypatch.setenv("LINKEDIN_TOKEN_EXPIRES", "2026-10-20")
    linkedin.warn_if_expiring(today=date(2026, 10, 15))
    assert "expires in 5 days" in capsys.readouterr().err
    linkedin.warn_if_expiring(today=date(2026, 9, 1))
    assert capsys.readouterr().err == ""


def test_api_version_configured():
    assert len(linkedin.api_version()) == 6
