import importlib

# platforms with a working publisher; the others in config.toml are planned
IMPLEMENTED = ["bluesky", "mastodon"]


def get_publisher(platform):
    if platform not in IMPLEMENTED:
        raise SystemExit(f"no publisher for '{platform}' yet (implemented: {', '.join(IMPLEMENTED)})")
    return importlib.import_module(f"{__name__}.{platform}").publish
