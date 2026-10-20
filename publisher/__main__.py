"""Publish posts.

    python -m publisher --due                          # post to every platform that is due (used by the workflow)
    python -m publisher --platform bluesky             # post one now, regardless of the schedule
    python -m publisher --platform bluesky --dry-run   # preview, posts and saves nothing
    python -m publisher --platform x --dry-run -n 10   # preview the next 10 picks
"""
import argparse
import os
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from .content import eligible_posts, load_posts
from .formatter import render
from .platforms import IMPLEMENTED, get_module
from .rotation import load_state, pick, record, save_state
from .schedule import is_due, last_posted_at

ROOT = Path(__file__).resolve().parent.parent

try:
    # use the OS certificate store, so HTTPS works behind antivirus/corporate TLS inspection
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass


def run_platform(platform, config, args, now):
    """Post (or preview) the next post(s) for one platform. Returns False on failure."""
    platform_cfg = config["platforms"][platform]
    posts = eligible_posts(load_posts(args.content), platform, platform_cfg)
    state_path = args.state_dir / f"{platform}.json"
    state = load_state(state_path)

    for i in range(args.count):
        post = pick(posts, config["weights"], state)
        if post is None:
            print(f"nothing eligible to post on {platform}", file=sys.stderr)
            return False
        rendered = render(post, platform, platform_cfg, config.get("utm", {}))
        if args.dry_run:
            print(f"--- [{platform} {i + 1}] {post.id} ({post.type}), {len(rendered.text)} chars"
                  + (f", link card: {rendered.link}" if rendered.link and rendered.link not in rendered.text else ""))
            print(rendered.text)
            record(state, post, now=now)  # in memory only, so -n previews follow the real rotation
            continue
        url = get_module(platform).publish(post, rendered)
        record(state, post, url, now=now)
        save_state(state_path, state)
        print(f"posted {post.id} to {platform}: {url}")
    return True


def due_platforms(config, state_dir, now, check_env=True):
    tz = config["schedule"]["timezone"]
    due = []
    for platform in IMPLEMENTED:
        platform_cfg = config["platforms"].get(platform, {})
        last = last_posted_at(load_state(state_dir / f"{platform}.json"))
        if not is_due(platform_cfg, last, now, tz):
            continue
        missing = [v for v in get_module(platform).REQUIRED_ENV if not os.environ.get(v)]
        if missing and check_env:
            print(f"::warning::{platform} is due but {', '.join(missing)} not set, skipping")
            continue
        due.append(platform)
    return due


def main(argv=None, now=None):
    parser = argparse.ArgumentParser(prog="publisher", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--platform")
    target.add_argument("--due", action="store_true", help="every platform whose posting time has come")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-n", "--count", type=int, default=1, help="posts to preview (dry run only)")
    parser.add_argument("--config", default=ROOT / "config.toml", type=Path)
    parser.add_argument("--content", default=ROOT / "content" / "posts.csv", type=Path)
    parser.add_argument("--state-dir", default=ROOT / "state", type=Path)
    args = parser.parse_args(argv)

    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    if args.count > 1 and not args.dry_run:
        parser.error("--count is only allowed with --dry-run")
    now = now or datetime.now(timezone.utc)

    if args.due:
        platforms = due_platforms(config, args.state_dir, now, check_env=not args.dry_run)
        print(f"due: {', '.join(platforms) or 'nothing'}")
    else:
        if args.platform not in config["platforms"]:
            parser.error(f"unknown platform '{args.platform}', see [platforms.*] in {args.config}")
        if args.platform not in IMPLEMENTED:
            parser.error(f"no publisher for '{args.platform}' yet (implemented: {', '.join(IMPLEMENTED)})")
        platforms = [args.platform]

    failed = []
    for platform in platforms:
        try:
            if not run_platform(platform, config, args, now):
                failed.append(platform)
        except Exception as e:  # one platform failing must not stop the others
            print(f"::error::{platform} failed: {e}")
            failed.append(platform)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
