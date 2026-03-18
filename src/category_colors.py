"""
Category color palette: load config/categories.json and generate CSS.
"""

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_CATEGORIES_JSON = _ROOT / "config" / "categories.json"


def load_category_colors():
    """Return dict of category -> hex color. Returns {} if file missing."""
    if not _CATEGORIES_JSON.exists():
        return {}
    data = json.loads(_CATEGORIES_JSON.read_text(encoding="utf-8"))
    return {item["category"]: item["hex"] for item in data}


def category_css_slug(category):
    """CSS class name for a category, e.g. 'AI-minds' -> 'cat-ai-minds'."""
    return "cat-" + category.lower().replace(" ", "-")


def build_category_css(category_colors):
    """
    Generate CSS for full-bleed color bands behind category summaries and
    nugget headers.  Uses a ::before pseudo-element so no element dimensions
    change (avoids horizontal-scroll from width:100vw).
    """
    if not category_colors:
        return ""

    base = (
        ".nugget-header.cat-colored,"
        "details.category-group summary.index-tag-name.cat-colored{"
        "position:relative;isolation:isolate}"
        ".nugget-header.cat-colored::before,"
        "details.category-group summary.index-tag-name.cat-colored::before{"
        "content:'';position:absolute;top:0;bottom:0;"
        "left:calc(50% - 50vw);right:calc(50% - 50vw);"
        "background:var(--cat-bg);z-index:-1}"
    )
    color_rules = "".join(
        f".{category_css_slug(cat)}{{--cat-bg:{hex_val}}}"
        for cat, hex_val in sorted(category_colors.items())
    )
    return base + color_rules
