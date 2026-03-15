"""
Output path convention: no directories under site_dir; path segments become a single filename with "-".
Used for content .md → .html and for "more" section built pages (e.g. more-bibliography.html).
"""

from pathlib import Path


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


def more_page_output_name(key):
    """Output filename for a built page in the logical 'more' section. E.g. bibliography → more-bibliography.html."""
    return f"more-{key}.html"


def get_more_pages(index_copy):
    """Parse more_pages from config index (comma-separated). Returns list of keys, e.g. ['bibliography', 'glossary', 'tags', 'map-graph']."""
    raw = (index_copy or {}).get("more_pages", "bibliography, glossary, tags, map-graph")
    return [t.strip() for t in raw.split(",") if t.strip()]
