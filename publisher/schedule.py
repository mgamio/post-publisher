"""Decides whether a platform is due for a post.

GitHub Actions cron runs are often late or skipped, so the workflow runs every
30 minutes and asks: has a posting time (post_at, local time) passed since the
platform's last post? A skipped run is then made up by the next one, and a
manual run counts as the post for the current slot, so nothing is posted twice.
"""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def latest_slot(now, post_at, days, tz):
    """Most recent scheduled time <= now (aware datetime), or None."""
    local = now.astimezone(tz)
    times = sorted((time.fromisoformat(t) for t in post_at), reverse=True)
    for back in range(8):
        day = local.date() - timedelta(days=back)
        if days and DAYS[day.weekday()] not in days:
            continue
        for t in times:
            slot = datetime.combine(day, t, tzinfo=tz)
            if slot <= local:
                return slot
    return None


def is_due(platform_cfg, last_posted_at, now, timezone):
    post_at = platform_cfg.get("post_at")
    if not post_at:
        return False
    slot = latest_slot(now, post_at, platform_cfg.get("days"), ZoneInfo(timezone))
    return slot is not None and (last_posted_at is None or last_posted_at < slot)


def last_posted_at(state):
    if not state["history"]:
        return None
    return datetime.fromisoformat(state["history"][-1]["at"])
