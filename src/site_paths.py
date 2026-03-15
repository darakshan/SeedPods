"""
Output path convention: no directories under site_dir; path segments become a single filename with "-".
Used for content .md → .html.
"""

from pathlib import Path


def parse_list_menu(raw):
    """Parse list_menu value: comma-separated items, each 'Label | target'. Target is a content path (e.g. list, glossary). Returns [(label, target), ...]."""
    if not raw or not raw.strip():
        return []
    out = []
    for part in (p.strip() for p in raw.split(",") if p.strip()):
        if "|" not in part:
            continue
        label, _, target = part.partition("|")
        label, target = label.strip(), target.strip()
        if label and target:
            out.append((label, target))
    return out


def content_path_to_output_name(md_path, content_root):
    """Return the site_dir filename for a .md file under content_root.
    Path relative to content_root with / → -, .md → .html. E.g. about/reviews.md → about-reviews.html."""
    root = Path(content_root).resolve()
    try:
        rel = Path(md_path).resolve().relative_to(root)
    except ValueError:
        return None
    parts = list(rel.parts)
    if not parts or not str(rel).endswith(".md"):
        return None
    parts[-1] = Path(parts[-1]).stem + ".html"
    return "-".join(parts)


