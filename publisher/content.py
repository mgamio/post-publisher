import csv
from dataclasses import dataclass


@dataclass(frozen=True)
class Post:
    id: str
    type: str
    text: str
    link: str = ""
    tags: str = ""
    platforms: str = "all"
    priority: str = ""
    image: str = ""

    def enabled_on(self, platform):
        names = {p.strip() for p in self.platforms.split(",")}
        return "all" in names or platform in names

    @property
    def tag_list(self):
        return [t for t in self.tags.split() if t.startswith("#") and len(t) > 1]


def load_posts(path):
    with open(path, encoding="utf-8", newline="") as f:
        posts = [Post(**{k: (v or "").strip() for k, v in row.items()}) for row in csv.DictReader(f)]
    ids = [p.id for p in posts]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate post ids in {path}: {sorted(dupes)}")
    return posts


def eligible_posts(posts, platform, platform_cfg):
    types = platform_cfg.get("types")
    return [
        p for p in posts
        if p.enabled_on(platform)
        and not (platform_cfg.get("text_only") and p.link)
        and (types is None or p.type in types)
    ]
