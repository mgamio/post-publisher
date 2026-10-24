import importlib

# platforms with a working publisher; the others in config.toml are planned
IMPLEMENTED = ["bluesky", "mastodon", "linkedin", "facebook", "x"]


def get_module(platform):
    """The publisher module: publish(post, rendered) -> url, and REQUIRED_ENV."""
    return importlib.import_module(f"{__name__}.{platform}")
