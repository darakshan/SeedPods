#!/usr/bin/env python3
"""
build.py — Seed Nuggets site generator
Reads nugget .txt files from ./nuggets/, writes HTML to ./docs/
Generates: nugget pages, repository.html, tags.html (Index), groups.html,
index.html, about pages (including map.html), site.css.

Usage:
    python build.py
    python build.py --nugget 001   # rebuild single nugget
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import markdown
except ImportError:
    markdown = None

NUGGETS_DIR = Path("nuggets")
ABOUT_DIR = Path("about")
CONTENT_DIR = Path("content")
SITE_DIR = Path("docs")

BUILD_TIME = None
_warn_count = 0

def _warn(msg):
    global _warn_count
    print(msg, file=sys.stderr)
    _warn_count += 1

# ── Parser ────────────────────────────────────────────────────────────────────

def parse_nugget(filepath):
    """Parse a nugget .txt file into a dict."""
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines()

    meta = {}
    layers = {}
    current_layer = None
    buffer = []

    # Single-line meta fields
    SINGLE_LINE = {"number", "shortname", "title", "subtitle", "status",
                   "date", "tags", "related"}

    def flush():
        if current_layer and current_layer not in SINGLE_LINE:
            layers[current_layer] = "\n".join(buffer).strip()
        buffer.clear()

    for line in lines:
        if line.startswith("#"):
            parts = line[1:].split(None, 1)
            if not parts:
                continue
            key = parts[0].lower()
            value = parts[1] if len(parts) > 1 else ""

            if key in SINGLE_LINE:
                flush()
                current_layer = None
                if key in meta:
                    _warn(f"Warning: {filepath}: duplicate #{key}, keeping first value.")
                else:
                    if not value.strip():
                        _warn(f"Warning: {filepath}: #{key} has no value on same line.")
                    meta[key] = value.strip()
            else:
                flush()
                if key in layers:
                    _warn(f"Warning: {filepath}: duplicate #{key}, keeping first.")
                    current_layer = None
                    buffer = []
                else:
                    current_layer = key
                    buffer = []
        else:
            if current_layer and current_layer not in SINGLE_LINE:
                buffer.append(line)

    flush()

    # Parse list fields
    meta["tags"] = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
    raw_related = [r.strip() for r in meta.get("related", "").split(",") if r.strip()]
    related_parsed = []
    for r in raw_related:
        if re.match(r"^\d+$", r):
            related_parsed.append(r)
        else:
            _warn(f"Warning: {filepath}: related entry {r!r} is not a valid nugget number (digits only).")
            m = re.match(r"^(\d+)", r)
            if m:
                related_parsed.append(m.group(1))
    meta["related"] = related_parsed

    meta["layers"] = {
        "surface": layers.get("surface", "TBD"),
        "depth": layers.get("depth", "TBD"),
        "provenance": layers.get("provenance", "TBD"),
        "script": layers.get("script", "TBD"),
        "images": layers.get("images", "TBD"),
    }

    stem = filepath.stem
    prefix = stem.split("-")[0] if "-" in stem else ""
    if prefix.isdigit() and meta.get("number") and meta["number"] != prefix:
        _warn(f"Warning: {filepath}: filename prefix {prefix} does not match #number {meta['number']}.")

    return meta


def load_all_nuggets():
    nuggets = []
    for f in sorted(NUGGETS_DIR.glob("*.txt")):
        try:
            n = parse_nugget(f)
            n["filename"] = f.stem  # e.g. 001-caloric
            nuggets.append(n)
        except Exception as e:
            _warn(f"Warning: could not parse {f}: {e}")
    return nuggets


def nugget_by_number(nuggets, num):
    for n in nuggets:
        if n.get("number") == num:
            return n
    return None


def about_body_to_html(body):
    """Convert about-page body from Markdown to HTML. Requires the markdown package (pip install markdown)."""
    if not body.strip():
        return ""
    if markdown is None:
        raise SystemExit(
            "About pages use Markdown. Install the markdown package:\n"
            "  pip install markdown\n"
            "Or in a venv: pip install -r requirements.txt"
        )
    html = markdown.markdown(
        body,
        extensions=["fenced_code", "tables"],
        extension_configs={"fenced_code": {}},
    )
    html = re.sub(
        r'<p>(TBD|No reviews completed yet\.)</p>',
        r'<p class="dim placeholder">\1</p>',
        html,
    )
    return html


def parse_about_file(filepath):
    """Parse an about .md file: first line = title, rest = body (Markdown). Returns (title, body_html)."""
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines:
        return ("Untitled", "")
    title = lines[0].strip()
    body = "\n".join(lines[1:]).strip()
    body_html = about_body_to_html(body) if body else ""
    return (title, body_html)


def load_about_pages():
    """Load all about/*.md. Returns list of (stem, title, body_html) sorted by stem."""
    pages = []
    for f in sorted(ABOUT_DIR.glob("*.md")):
        title, body_html = parse_about_file(f)
        pages.append((f.stem, title, body_html))
    return pages


def load_index_copy():
    """Load content/index.txt as key: value dict."""
    p = CONTENT_DIR / "index.txt"
    if not p.exists():
        return {}
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def load_groups_data():
    """Load content/groups.txt. Returns list of (title, subtitle, [num, ...])."""
    p = CONTENT_DIR / "groups.txt"
    if not p.exists():
        return []
    text = p.read_text(encoding="utf-8")
    groups = []
    for block in text.strip().split("\n---\n"):
        block = block.strip()
        if not block:
            continue
        title = subtitle = ""
        seeds = []
        for line in block.splitlines():
            line = line.strip()
            if line.startswith("title:"):
                title = line[6:].strip()
            elif line.startswith("subtitle:"):
                subtitle = line[9:].strip()
            elif line.startswith("seeds:"):
                seeds = [s.strip() for s in line[6:].split(",") if s.strip()]
        if title:
            groups.append((title, subtitle, seeds))
    return groups

# ── HTML helpers ──────────────────────────────────────────────────────────────

HEAD_LINKS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="site.css">
"""

def nav(about_pages):
    """about_pages: list of (stem, title) for dropdown."""
    about_items = "".join(
        f'<li><a href="{stem}.html">{title}</a></li>' for stem, title, _ in about_pages
    )
    return f"""
<nav>
  <a href="index.html" class="nav-logo">Seed Nuggets</a>
  <ul class="nav-links">
    <li><a href="repository.html">Repository</a></li>
    <li><a href="tags.html">Index</a></li>
    <li><a href="groups.html">By Group</a></li>
    <li class="nav-item-dropdown">
      <details>
        <summary>About</summary>
        <ul class="nav-dropdown">{about_items}
        </ul>
      </details>
    </li>
  </ul>
</nav>"""

def foot():
    t = (BUILD_TIME or datetime.now(ZoneInfo("America/Los_Angeles"))).strftime("%Y-%m-%d %H:%M Pacific")
    return f"""
<footer>
  <span>Seed Nuggets — archive in progress</span>
  <span>Built {t}</span>
</footer>"""

def head(title, extra=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Seed Nuggets</title>
{HEAD_LINKS}
{extra}
</head>
<body>"""

def close():
    return "\n</body>\n</html>"

def _block_to_html(block):
    """Convert a single block (paragraph or list) to HTML."""
    lines = [ln.strip() for ln in block.strip().splitlines() if ln.strip()]
    if not lines:
        return ""
    list_markers = ("- ", "* ")
    if any(ln.startswith(list_markers) for ln in lines):
        items = []
        for ln in lines:
            for m in list_markers:
                if ln.startswith(m):
                    items.append(f"<li>{ln[len(m):].strip()}</li>")
                    break
            else:
                items.append(f"<li>{ln}</li>")
        return f"<ul>\n" + "\n".join(items) + "\n</ul>"
    return f"<p>{' '.join(lines)}</p>"

def text_to_html(text):
    """Convert plain text with --- dividers, paragraphs, and - / * lists to HTML."""
    if text.strip() == "TBD":
        return '<p class="dim placeholder">This layer is not yet written.</p>'
    parts = text.split("\n---\n")
    html_parts = []
    list_markers = ("- ", "* ")
    for part in parts:
        blocks = []
        current = []
        in_list = None
        for line in part.splitlines():
            is_list_line = any(line.strip().startswith(m) for m in list_markers)
            if is_list_line:
                if in_list is False and current:
                    blocks.append("\n".join(current))
                    current = []
                in_list = True
                current.append(line)
            else:
                if in_list is True and current:
                    blocks.append(("\n".join(current), "list"))
                    current = []
                in_list = False
                current.append(line)
        if current:
            if in_list:
                blocks.append(("\n".join(current), "list"))
            else:
                blocks.append("\n".join(current))
        part_html = []
        for b in blocks:
            if isinstance(b, tuple):
                part_html.append(_block_to_html(b[0]))
            else:
                for para in (p.strip() for p in b.split("\n\n") if p.strip()):
                    part_html.append(_block_to_html(para))
        html_parts.append("\n".join(part_html))
    return "<hr>".join(html_parts)

def script_to_html(text):
    """Format script text with direction lines highlighted."""
    if text.strip() == "TBD":
        return '<p class="dim placeholder">Script not yet written.</p>'
    lines = text.strip().splitlines()
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.isupper() or re.match(r'^(CUT|OPEN|FADE|PAUSE|SLOW|CLOSE|END)', line):
            out.append(f'<p class="script-direction">{line}</p>')
        elif line.startswith("What does") or line.startswith("What if"):
            out.append(f'<p class="script-punch">{line}</p>')
        else:
            out.append(f'<p class="script-line">{line}</p>')
    return "\n".join(out)

# ── Page builders ─────────────────────────────────────────────────────────────

LAYER_ORDER = [
    ("surface", "Surface"),
    ("depth", "Depth"),
    ("script", "Script"),
    ("images", "Images"),
    ("references", "References"),
]

INDEX_TABLE_HEAD = """
      <thead>
        <tr>
          <th>Tag</th>
          <th>Title / Subtitle</th>
        </tr>
      </thead>"""


def build_nugget(n, all_nuggets, about_pages):
    num = n.get("number", "?")
    title = n.get("title", "Untitled")
    subtitle = n.get("subtitle", "")
    status = n.get("status", "empty")
    date = n.get("date", "")
    tags = n.get("tags", [])
    related_nums = n.get("related", [])
    layers = n.get("layers", {})

    tag_html = " ".join(f'<a href="tags.html#{tag_slug(t)}" class="tag">{t}</a>' for t in tags)

    rel_nuggets = [nugget_by_number(all_nuggets, r) for r in related_nums]
    for r in related_nums:
        if not nugget_by_number(all_nuggets, r):
            _warn(f"Warning: nugget {n.get('number')} ({n.get('filename')}): related {r} does not match any nugget.")
    rel_nuggets = [r for r in rel_nuggets if r]
    related_cards_html = ""
    if rel_nuggets:
        cards = ""
        for r in rel_nuggets[:5]:
            rfile = r.get("filename", "") + ".html"
            rnum = r.get("number", "")
            rtitle = r.get("title", "")
            cards += f"""
      <a href="{rfile}" class="related-card">
        <div class="related-num">{display_number(rnum)}</div>
        <div class="related-title">{rtitle}</div>
      </a>"""
        related_cards_html = f'<div class="related-grid">{cards}\n      </div>'

    surface_raw = layers.get("surface", "TBD")
    surface_html = "" if (surface_raw or "TBD").strip() == "TBD" else text_to_html(surface_raw)
    if surface_html and "Try this:" in surface_raw:
        parts = surface_raw.split("Try this:")
        before = text_to_html("Try this:".join(parts[:-1]))
        cta_text = "Try this: " + parts[-1].strip()
        surface_html = before + f'<div class="cta">{cta_text}</div>'

    def layer_has_content(layer_id):
        if layer_id == "references":
            prov_raw = (layers.get("provenance") or "TBD").strip()
            return prov_raw != "TBD" or bool(rel_nuggets)
        raw = (layers.get(layer_id) or "TBD").strip()
        return raw != "TBD"

    def layer_body(layer_id):
        if layer_id == "references":
            prov_raw = layers.get("provenance", "TBD")
            prov_html = text_to_html(prov_raw) if (prov_raw or "TBD").strip() != "TBD" else ""
            parts = []
            if prov_html:
                parts.append(f'<div class="prose">{prov_html}</div>')
            if rel_nuggets:
                parts.append('<div class="related-section">')
                if prov_html:
                    parts.append('<h3 class="layer-heading related-label">Related seeds</h3>')
                parts.append(related_cards_html)
                parts.append("</div>")
            return "\n    ".join(parts)
        if layer_id == "surface":
            return surface_html
        raw = layers.get(layer_id, "TBD")
        if layer_id == "script":
            return script_to_html(raw)
        return text_to_html(raw)

    tabs_parts = []
    for layer_id, label in LAYER_ORDER:
        if layer_has_content(layer_id):
            tabs_parts.append(f'<a href="#{layer_id}" class="layer-tab">{label}</a>')
        else:
            tabs_parts.append(f'<span class="layer-tab layer-tab-disabled">{label}</span>')

    sections_parts = []
    for layer_id, label in LAYER_ORDER:
        if not layer_has_content(layer_id):
            continue
        body = layer_body(layer_id)
        if layer_id == "references":
            section_content = f'<h2 class="layer-heading">{label}</h2>\n    {body}'
        else:
            section_content = f'<h2 class="layer-heading">{label}</h2>\n    <div class="prose">{body}</div>'
        sections_parts.append(f'  <section id="{layer_id}" class="layer-section">\n    {section_content}\n  </section>')

    tabs_html = "\n      ".join(tabs_parts)
    sections_html = "\n\n".join(sections_parts)

    sorted_nuggets = sorted(all_nuggets, key=lambda x: x.get("number", ""))
    idx = next((i for i, x in enumerate(sorted_nuggets) if x.get("filename") == n.get("filename")), -1)
    prev_n = sorted_nuggets[idx - 1] if idx > 0 else None
    next_n = sorted_nuggets[idx + 1] if 0 <= idx < len(sorted_nuggets) - 1 else None

    prev_html = f'<a href="{prev_n.get("filename", "")}.html">&laquo;</a>' if prev_n else ''
    next_html = f'<a href="{next_n.get("filename", "")}.html">&raquo;</a>' if next_n else ''

    html = head(f"{display_number(num)} — {title}")
    html += nav(about_pages)
    html += f"""
<div class="wrap">
  <div class="layer-tabs">
    <div class="layer-tabs-inner">
      <span class="layer-tabs-prev">{prev_html}</span>
      <div class="layer-tabs-center">
        {tabs_html}
      </div>
      <span class="layer-tabs-next">{next_html}</span>
    </div>
  </div>

  <div class="nugget-header fade">
    <div class="meta-row">
      <span class="mono small warm">Seed {display_number(num)}</span>
      <span class="mono small dim"> · {status} · {date}</span>
    </div>
    <h1>{title}</h1>
    <p class="premise">{subtitle}</p>
    <div class="nugget-tags">{tag_html}</div>
  </div>

{sections_html}
</div>
"""
    html += foot()
    html += close()
    return html


def build_repository(nuggets, about_pages):
    rows = ""
    for n in nuggets:
        num = n.get("number", "")
        shortname = n.get("shortname", "")
        title = n.get("title", "")
        subtitle = n.get("subtitle", "")
        status = n.get("status", "empty")
        date = n.get("date", "")
        tag_links = " ".join(f'<a href="tags.html#{tag_slug(t)}" class="tag">{t}</a>' for t in n.get("tags", []))
        fname = n.get("filename", "") + ".html"
        status_class = f"status-{status.replace(' ','')}"
        rows += f"""
    <tr>
      <td class="mono repo-cell-mono">{display_number(num)}</td>
      <td class="mono repo-cell-mono">{shortname}</td>
      <td><a href="{fname}">{title}</a><br><span class="repo-subtitle">{subtitle}</span></td>
      <td class="{status_class}">{status}</td>
      <td class="mono repo-date">{date}</td>
      <td class="repo-tags">{tag_links}</td>
    </tr>"""

    html = head("Repository")
    html += nav(about_pages)
    html += f"""
<div class="wrap">
  <div class="page-body fade">
    <h1>Repository</h1>
    <p class="dim repo-intro">All seed nuggets. The canonical list. Generated from source files.</p>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Name</th>
          <th>Title / Subtitle</th>
          <th>Status</th>
          <th>Date</th>
          <th>Tags</th>
        </tr>
      </thead>
      <tbody>{rows}
      </tbody>
    </table>
  </div>
</div>"""
    html += foot()
    html += close()
    return html


def tag_slug(tag):
    return tag.replace(" ", "-")


def display_number(num):
    """Strip leading zeros for display only; keep filenames/URLs/lookup as-is."""
    if num and num.isdigit():
        return str(int(num))
    return num or "?"


def build_tags_page(nuggets, about_pages):
    all_tags = set()
    for n in nuggets:
        all_tags.update(n.get("tags", []))
    sorted_tags = sorted(all_tags)

    all_statuses = set(n.get("status", "empty") for n in nuggets)
    sorted_statuses = sorted(all_statuses)

    def row_block(label, slug, matching):
        block = ""
        for i, n in enumerate(matching):
            num = n.get("number", "")
            title = n.get("title", "")
            subtitle = n.get("subtitle", "")
            fname = n.get("filename", "") + ".html"
            title_display = f"{display_number(num)}. {title}" if num else title
            if i == 0:
                tag_cell = f'<td id="{slug}" class="repo-tag-label">{label}</td>'
            else:
                tag_cell = '<td class="repo-tag-label-empty"></td>'
            block += f"""
    <tr>
      {tag_cell}
      <td><a href="{fname}">{title_display}</a><br><span class="repo-subtitle">{subtitle}</span></td>
    </tr>"""
        return block

    tag_rows = ""
    for tag in sorted_tags:
        tag_rows += row_block(tag, tag_slug(tag), [n for n in nuggets if tag in n.get("tags", [])])
    status_rows = ""
    for status in sorted_statuses:
        status_rows += row_block(status, f"status-{status}", [n for n in nuggets if n.get("status", "empty") == status])

    html = head("Index")
    html += nav(about_pages)
    html += f"""
<div class="wrap">
  <div class="page-body fade">
    <h1>Index</h1>
    <table class="tags-table">{INDEX_TABLE_HEAD}
      <tbody>{tag_rows}
      </tbody>
    </table>
    <h2 class="index-section-head">Statuses</h2>
    <table class="tags-table">{INDEX_TABLE_HEAD}
      <tbody>{status_rows}
      </tbody>
    </table>
  </div>
</div>"""
    html += foot()
    html += close()
    return html


def build_groups(nuggets, groups_data, about_pages):
    html = head("Seeds by Group")
    html += nav(about_pages)
    html += '<div class="wrap"><div class="page-body fade">'
    html += "<h1>Seeds by group</h1>\n"
    html += '<p class="groups-intro">Thematic clusters. Each seed may appear in more than one group.</p>\n'

    for group_title, group_sub, nums in groups_data:
        html += f'<div class="group-block">'
        html += f'<div class="group-label">{group_title} — <span class="group-label-sub">{group_sub}</span></div>'
        for num in nums:
            n = nugget_by_number(nuggets, num)
            if not n:
                _warn(f"Warning: groups.txt: seed {num!r} in group {group_title!r} does not match any nugget.")
                continue
            fname = n.get("filename", "") + ".html"
            title = n.get("title", "")
            subtitle = n.get("subtitle", "")
            status = n.get("status", "empty")
            stub_class = " stub" if status == "empty" else ""
            html += f"""
      <a href="{fname}" class="seed-row{stub_class}">
        <div class="seed-num">{display_number(n.get("number", ""))}</div>
        <div>
          <div class="seed-title">{title}</div>
          <div class="seed-sub">{subtitle}</div>
        </div>
        <div class="seed-status-col">{status}</div>
      </a>"""
        html += "</div>"

    html += "</div></div>"
    html += foot()
    html += close()
    return html


def build_index(nuggets, index_copy, about_pages):
    c = index_copy
    ready = [n for n in nuggets if n.get("status") not in ("empty",)]
    total = len(nuggets)
    ready_count = len(ready)

    recent = nuggets[:5]
    recent_html = ""
    for n in recent:
        fname = n.get("filename", "") + ".html"
        num = n.get("number", "")
        title = n.get("title", "")
        subtitle = n.get("subtitle", "")
        status = n.get("status", "empty")
        stub = " stub" if status == "empty" else ""
        recent_html += f"""
    <a href="{fname}" class="seed-row{stub}">
      <div class="seed-num">{display_number(num)}</div>
      <div>
        <div class="seed-title">{title}</div>
        <div class="seed-sub">{subtitle}</div>
      </div>
      <div class="seed-status-col">{status}</div>
    </a>"""

    view_all_text = (c.get("view_all") or "View all {n} seeds →").replace("{n}", str(total))
    about_cards = []
    for stem, title, _ in about_pages:
        about_cards.append(f'<a href="{stem}.html" class="about-card">{title}</a>')
    about_cards.append(f'<a href="groups.html" class="about-card">{c.get("groups", "By Group")}</a>')

    html = head("Seed Nuggets")
    html += nav(about_pages)
    html += f"""
<div class="wrap">
  <div class="hero fade">
    <span class="mono small warm hero-notice">{c.get("notice", "")}</span>
    <h1>Seed Nuggets</h1>
    <p class="hero-tagline">{c.get("tagline", "")}</p>
    <p class="hero-purpose">{c.get("purpose", "")}</p>

    <div class="hero-stats">
      <div>
        <div class="mono small warm">{total}</div>
        <div class="hero-stat-label">{c.get("stat_label_1", "seeds defined")}</div>
      </div>
      <div>
        <div class="mono small warm">{ready_count}</div>
        <div class="hero-stat-label">{c.get("stat_label_2", "with content")}</div>
      </div>
    </div>
  </div>

  <div class="seed-list-section">
    <div class="section-head">
      <span class="mono small">{c.get("section_head", "All seeds")}</span>
      <a href="repository.html" class="link-mono-small">{c.get("repo_link", "Full repository →")}</a>
    </div>
    {recent_html}
    <div class="seed-list-more-wrap">
      <a href="repository.html" class="link-mono-accent">{view_all_text}</a>
    </div>
  </div>

  <div class="about-block">
    <div class="mono small warm about-block-label">{c.get("about_heading", "About this project")}</div>
    <div class="about-grid">
      {"".join(about_cards)}
    </div>
  </div>
</div>"""
    html += foot()
    html += close()
    return html


def build_static_page(title, body_html, about_pages):
    html = head(title)
    html += nav(about_pages)
    html += f'<div class="wrap"><div class="page-body fade"><h1>{title}</h1>{body_html}</div></div>'
    html += foot()
    html += close()
    return html


def build_map_body(nuggets):
    """HTML body for the Map about page: N×N matrix of related links (from → to)."""
    sorted_nuggets = sorted(nuggets, key=lambda x: x.get("number", ""))
    nums = [n.get("number", "") for n in sorted_nuggets]
    related_sets = {n.get("number", ""): set(n.get("related", [])) for n in sorted_nuggets}
    rows = []
    header_cells = ["<th></th>"] + [f'<th class="map-col-label">{display_number(num)}</th>' for num in nums]
    rows.append("<tr>" + "".join(header_cells) + "</tr>")
    for from_num, n in zip(nums, sorted_nuggets):
        cells = [f'<th class="map-row-label">{display_number(from_num)}</th>']
        for to_num in nums:
            linked = to_num in related_sets.get(from_num, set())
            cls = "map-cell-linked" if linked else "map-cell-empty"
            cells.append(f'<td class="{cls}">{"·" if linked else ""}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    table = "<table class=\"map-matrix\">\n" + "\n".join(rows) + "\n</table>"
    return f'<p>Rows = from seed, columns = to seed. Marked cell means the row seed links to the column seed in its Related list.</p>\n{table}'


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global BUILD_TIME
    BUILD_TIME = datetime.now(ZoneInfo("America/Los_Angeles"))

    filter_num = None
    if "--nugget" in sys.argv:
        idx = sys.argv.index("--nugget")
        filter_num = sys.argv[idx + 1]

    if filter_num:
        SITE_DIR.mkdir(exist_ok=True)
    else:
        if SITE_DIR.exists():
            shutil.rmtree(SITE_DIR)
        SITE_DIR.mkdir(parents=True)

    nuggets = load_all_nuggets()
    print(f"Loaded {len(nuggets)} nuggets")
    seen_num = {}
    for n in nuggets:
        num = n.get("number")
        if num:
            if num in seen_num:
                _warn(f"Warning: duplicate #number {num} (in {seen_num[num]}.txt and {n.get('filename')}.txt).")
            else:
                seen_num[num] = n.get("filename")

    about_pages = load_about_pages()
    about_pages.append(("map", "Map", build_map_body(nuggets)))
    index_copy = load_index_copy()
    groups_data = load_groups_data()

    for n in nuggets:
        if filter_num and n.get("number") != filter_num:
            continue
        fname = n.get("filename", "") + ".html"
        out = SITE_DIR / fname
        out.write_text(build_nugget(n, nuggets, about_pages), encoding="utf-8")
        print(f"  Built {fname}")

    if not filter_num:
        shutil.copy(CONTENT_DIR / "site.css", SITE_DIR / "site.css")
        print("  Built site.css")

        (SITE_DIR / "repository.html").write_text(build_repository(nuggets, about_pages), encoding="utf-8")
        print("  Built repository.html")

        (SITE_DIR / "tags.html").write_text(build_tags_page(nuggets, about_pages), encoding="utf-8")
        print("  Built tags.html")

        (SITE_DIR / "groups.html").write_text(build_groups(nuggets, groups_data, about_pages), encoding="utf-8")
        print("  Built groups.html")

        (SITE_DIR / "index.html").write_text(build_index(nuggets, index_copy, about_pages), encoding="utf-8")
        print("  Built index.html")

        for stem, title, body_html in about_pages:
            (SITE_DIR / f"{stem}.html").write_text(build_static_page(title, body_html, about_pages), encoding="utf-8")
            print(f"  Built {stem}.html")

    print(f"\nDone. Site written to ./{SITE_DIR}/")
    if _warn_count:
        sys.exit(1)

if __name__ == "__main__":
    main()
