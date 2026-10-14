"""One-off migration of the legacy posts-scheduler text files into content/posts.csv.

Usage: python tools/migrate_txt.py <legacy resources dir> <output csv>

Legacy line format: text;link;hashtags (text itself may contain ';').
"""
import csv
import sys
from pathlib import Path

# legacy file -> (type, id prefix)
SOURCES = [
    ("codersite.txt", "article", "art"),
    ("medium.txt", "medium", "med"),
    ("myBooks.txt", "book", "book"),
    ("quotes.txt", "quote", "quote"),
    ("ads.txt", "ad", "ad"),
    ("global.txt", "external", "ext"),
]

FIELDS = ["id", "type", "text", "link", "tags", "platforms", "priority", "image"]


def parse_line(line):
    parts = line.split(";")
    if len(parts) < 3:
        raise ValueError(f"expected text;link;tags, got: {line!r}")
    text = ";".join(parts[:-2]).strip()
    link = "".join(parts[-2].split())  # URLs never contain whitespace
    tags = " ".join(parts[-1].split())
    return text, link, tags


def migrate(src_dir, out_csv):
    rows, seen, codersite_texts = [], set(), set()
    report = []
    for filename, post_type, prefix in SOURCES:
        lines = (Path(src_dir) / filename).read_text(encoding="utf-8").splitlines()
        n = 0
        for lineno, line in enumerate(lines, 1):
            if not line.strip():
                continue
            text, link, tags = parse_line(line)
            if (text, link) in seen:
                report.append(f"dropped exact duplicate {filename}:{lineno}: {text[:60]}")
                continue
            seen.add((text, link))
            platforms = "all"
            if post_type == "article":
                codersite_texts.add(text)
            elif post_type == "medium" and text in codersite_texts:
                # same teaser already points to codersite.dev; prefer own site
                platforms = "none"
                report.append(f"disabled medium duplicate of codersite article {filename}:{lineno}: {text[:60]}")
            n += 1
            rows.append({
                "id": f"{prefix}-{n:03d}", "type": post_type, "text": text, "link": link,
                "tags": tags, "platforms": platforms, "priority": "", "image": "",
            })

    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return rows, report


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    rows, report = migrate(sys.argv[1], sys.argv[2])
    print("\n".join(report))
    print(f"wrote {len(rows)} posts to {sys.argv[2]}")
