from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from publisher import __main__ as cli
from publisher.rotation import empty_state, record, save_state
from publisher.content import Post
from publisher.schedule import is_due, latest_slot

BERLIN = ZoneInfo("Europe/Berlin")
TWICE = {"post_at": ["09:40", "18:40"]}
WEEKDAYS = {"post_at": ["09:10"], "days": ["mon", "tue", "wed", "thu", "fri"]}


def berlin(*args):
    return datetime(*args, tzinfo=BERLIN)


def test_latest_slot_same_day_and_previous_day():
    assert latest_slot(berlin(2026, 10, 20, 12, 0), ["09:40", "18:40"], None, BERLIN) == berlin(2026, 10, 20, 9, 40)
    assert latest_slot(berlin(2026, 10, 20, 8, 0), ["09:40", "18:40"], None, BERLIN) == berlin(2026, 10, 19, 18, 40)


def test_latest_slot_skips_excluded_days():
    monday = berlin(2026, 10, 19, 8, 0)  # before Monday's slot -> Friday's
    assert latest_slot(monday, ["09:10"], ["mon", "fri"], BERLIN) == berlin(2026, 10, 16, 9, 10)


def test_due_when_slot_passed_since_last_post():
    now = berlin(2026, 10, 20, 11, 0)
    assert is_due(TWICE, berlin(2026, 10, 19, 19, 0), now, "Europe/Berlin")
    assert not is_due(TWICE, berlin(2026, 10, 20, 9, 45), now, "Europe/Berlin")
    assert is_due(TWICE, None, now, "Europe/Berlin")


def test_late_run_still_posts_once():
    # the 09:40 run was skipped; the 14:13 run makes up for it, the 14:43 run does not repeat it
    last = berlin(2026, 10, 19, 18, 50)
    assert is_due(TWICE, last, berlin(2026, 10, 20, 14, 13), "Europe/Berlin")
    assert not is_due(TWICE, berlin(2026, 10, 20, 14, 13), berlin(2026, 10, 20, 14, 43), "Europe/Berlin")


def test_not_due_on_weekend_or_without_post_at():
    saturday = berlin(2026, 10, 24, 12, 0)
    assert not is_due(WEEKDAYS, berlin(2026, 10, 23, 9, 15), saturday, "Europe/Berlin")
    assert not is_due({}, None, saturday, "Europe/Berlin")


def test_utc_input_and_dst_change():
    # 26 Oct 2026 is winter time (UTC+1): 09:10 Berlin = 08:10 UTC
    assert latest_slot(datetime(2026, 10, 26, 8, 15, tzinfo=timezone.utc), ["09:10"], None, BERLIN) == \
        berlin(2026, 10, 26, 9, 10)
    assert latest_slot(datetime(2026, 10, 26, 8, 5, tzinfo=timezone.utc), ["09:10"], None, BERLIN) == \
        berlin(2026, 10, 25, 9, 10)


def test_due_runs_only_due_platforms_with_credentials(tmp_path, monkeypatch, capsys):
    now = datetime(2026, 10, 20, 9, 0, tzinfo=timezone.utc)  # 11:00 Berlin
    # mastodon posted after today's 09:40 slot -> not due; bluesky last posted yesterday -> due
    for platform, last in [("mastodon", berlin(2026, 10, 20, 9, 50)), ("bluesky", berlin(2026, 10, 19, 23, 0))]:
        state = empty_state()
        record(state, Post(id="x", type="quote", text="x"), now=last)
        save_state(tmp_path / f"{platform}.json", state)

    published = []

    class Fake:
        REQUIRED_ENV = ["FAKE_TOKEN"]

        @staticmethod
        def publish(post, rendered):
            published.append(post.id)
            return "https://example/post"

    monkeypatch.setattr(cli, "get_module", lambda platform: Fake)
    monkeypatch.setenv("FAKE_TOKEN", "t")
    assert cli.main(["--due", "--state-dir", str(tmp_path)], now=now) == 0
    out = capsys.readouterr().out
    assert "due: bluesky, linkedin, facebook" in out  # no state yet for linkedin, facebook
    assert len(published) == 3

    # second run in the same half hour: nothing is due anymore
    assert cli.main(["--due", "--state-dir", str(tmp_path)], now=now) == 0
    assert "due: nothing" in capsys.readouterr().out


def test_due_skips_platform_without_credentials(tmp_path, monkeypatch, capsys):
    class Fake:
        REQUIRED_ENV = ["MISSING_TOKEN"]

    monkeypatch.setattr(cli, "get_module", lambda platform: Fake)
    monkeypatch.delenv("MISSING_TOKEN", raising=False)
    now = datetime(2026, 10, 20, 9, 0, tzinfo=timezone.utc)
    assert cli.main(["--due", "--state-dir", str(tmp_path)], now=now) == 0
    out = capsys.readouterr().out
    assert "MISSING_TOKEN not set" in out
    assert "due: nothing" in out
