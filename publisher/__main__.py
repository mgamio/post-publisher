"""Publish the next post to one platform.

    python -m publisher --platform bluesky             # publish one post
    python -m publisher --platform bluesky --dry-run   # preview, posts and saves nothing
    python -m publisher --platform x --dry-run -n 10   # preview the next 10 picks
"""
import argparse
import sys
import tomllib
from pathlib import Path

from .content import eligible_posts, load_posts
from .formatter import render
from .platforms import get_publisher
from .rotation import load_state, pick, record, save_state

ROOT = Path(__file__).resolve().parent.parent

try:
    # use the OS certificate store, so HTTPS works behind antivirus/corporate TLS inspection
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass


def main(argv=None):
    parser = argparse.ArgumentParser(prog="publisher", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-n", "--count", type=int, default=1, help="posts to preview (dry run only)")
    parser.add_argument("--config", default=ROOT / "config.toml", type=Path)
    parser.add_argument("--content", default=ROOT / "content" / "posts.csv", type=Path)
    parser.add_argument("--state-dir", default=ROOT / "state", type=Path)
    args = parser.parse_args(argv)

    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    platform_cfg = config["platforms"].get(args.platform)
    if platform_cfg is None:
        parser.error(f"unknown platform '{args.platform}', see [platforms.*] in {args.config}")
    if args.count > 1 and not args.dry_run:
        parser.error("--count is only allowed with --dry-run")

    posts = eligible_posts(load_posts(args.content), args.platform, platform_cfg)
    state_path = args.state_dir / f"{args.platform}.json"
    state = load_state(state_path)
    publish = None if args.dry_run else get_publisher(args.platform)

    for i in range(args.count):
        post = pick(posts, config["weights"], state)
        if post is None:
            print(f"nothing eligible to post on {args.platform}", file=sys.stderr)
            return 1
        rendered = render(post, args.platform, platform_cfg, config.get("utm", {}))
        if args.dry_run:
            print(f"--- [{i + 1}] {post.id} ({post.type}), {len(rendered.text)} chars"
                  + (f", link card: {rendered.link}" if rendered.link and rendered.link not in rendered.text else ""))
            print(rendered.text)
            record(state, post)  # in memory only, so -n previews follow the real rotation
            continue
        url = publish(post, rendered)
        record(state, post, url)
        save_state(state_path, state)
        print(f"posted {post.id} to {args.platform}: {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
