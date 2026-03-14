#!/usr/bin/env python3
"""
build.py — Seed Nuggets site generator
Reads from content/ and config/; writes to d/ (and index.html at root).
Website root = project root: / serves index.html, /d/ has built HTML, /content/ has source.
Generates: nugget pages, list.html, tags.html (Index),
index.html, about pages, resources (with map), site.css.

Usage:
    python src/build.py   (from repo root)
    python build.py --nugget 001   # rebuild single nugget
"""

import csv
import hashlib
import html as _html
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_ROOT = Path(__file__).resolve().parent.parent
from graph_svg import build_graph_svg
from nugget_parser import (
    CONFIG_DIR,
    CONTENT_DIR,
    NUGGETS_DIR,
    display_number,
    expand_nugget_directives,
    load_all_nuggets,
    load_index_copy,
    load_status_order,
    nugget_by_number,
    section_is_tbd,
)
from md_pages import process_md_to_html, expand_includes, _md_link_output_name

ABOUT_DIR = CONTENT_DIR / "about"
INTERNAL_DIR = CONTENT_DIR / "internal"
EXPLAINERS_CSV = CONFIG_DIR / "explainers.csv"
SITE_DIR = _ROOT / "d"

def _get_md_page_paths():
    """Main MD pages for @link scanning and required-file check: home, internal, plus nav file/dir pages."""
    index_copy = load_index_copy()
    paths = [CONTENT_DIR / "home.md", INTERNAL_DIR / "page.md"]
    for _href, _label, kind, path in get_nav_items(index_copy):
        if kind == "file" and path:
            paths.append(path)
        elif kind == "dir" and path:
            paths.append(path / "page.md")
    return paths

BUILD_TIME = None
_warn_count = 0
BUILD_STATE_FILE = _ROOT / ".buildstate"

def _input_files_for_page(main_path):
    base_dir = main_path.parent.resolve()
    out = {main_path}
    if not main_path.exists():
        return out
    for line in main_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("@include "):
            name = stripped[8:].strip()
            inc_path = (base_dir / name).resolve()
            if str(inc_path).startswith(str(base_dir)) and inc_path.exists():
                out.add(inc_path)
    return out


def _referenced_md_from_md_pages():
    """Set of .md paths referenced via @link(locator, text) from main MD pages (transitive)."""
    refs = set()
    to_scan = list(_get_md_page_paths())
    while to_scan:
        path = to_scan.pop(0)
        if not path.exists():
            continue
        text = expand_includes(path.read_text(encoding="utf-8"), path.parent) if path.suffix == ".md" else ""
        for m in re.finditer(r"@link\s*\(\s*([^,)]+)\s*,", text):
            loc = m.group(1).strip()
            if not re.match(r"^\d+$", loc) and ".md" in loc:
                p = (CONTENT_DIR / loc).resolve()
                if p not in refs and p.exists():
                    refs.add(p)
                    to_scan.append(p)
    return refs

def get_build_input_files():
    files = set()
    for p in NUGGETS_DIR.glob("*.txt"):
        files.add(p)
    for name in ["index.txt", "status.txt", "site.css", "logo.svg"]:
        p = CONFIG_DIR / name
        if p.exists():
            files.add(p)
    for name in ["home.md"]:
        p = CONTENT_DIR / name
        if p.exists():
            files.add(p)
    if EXPLAINERS_CSV.exists():
        files.add(EXPLAINERS_CSV)
    for main in _get_md_page_paths():
        if main.exists():
            files.update(_input_files_for_page(main))
    files.update(_referenced_md_from_md_pages())
    return sorted(files, key=lambda p: str(p))

def get_build_input_hash():
    h = hashlib.sha256()
    for path in get_build_input_files():
        h.update(path.read_bytes())
    return h.hexdigest()

def _warn(msg):
    global _warn_count
    print(msg, file=sys.stderr)
    _warn_count += 1

_NAV_ITEMS = None


def _first_h1(path):
    """First # heading line text from a .md file, or None."""
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#\s+(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    return None


def get_nav_items(index_copy=None):
    """Resolve nav key from config index to list of (href, label, kind, path).
    nav value is comma-separated tokens. Label = token title-cased. Paths under content/."""
    raw = (index_copy or load_index_copy()).get("nav", "about, list, more")
    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    out = []
    for token in tokens:
        label = token.replace("-", " ").title()
        md_file = CONTENT_DIR / f"{token}.md"
        if md_file.exists():
            out.append((f"{token}.html", label, "file", md_file))
            continue
        dir_path = CONTENT_DIR / token
        if dir_path.is_dir() and (dir_path / "page.md").exists():
            out.append((f"{token}.html", label, "dir", dir_path))
            continue
        _warn(f"nav item {token!r} not found: no content/{token}.md nor content/{token}/page.md")
    return out


def _nav_items():
    global _NAV_ITEMS
    if _NAV_ITEMS is None:
        _NAV_ITEMS = get_nav_items(load_index_copy())
    return _NAV_ITEMS


def _require_status_order():
    order = load_status_order()
    if not order:
        raise SystemExit("Required file missing: config/status.txt")
    return order


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _head_links(css_href="site.css", icon_href="d/logo.svg"):
    return f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{css_href}">
<link rel="icon" type="image/svg+xml" href="{icon_href}">
"""

def nav(from_d=False, from_nuggets=False, layer_tabs_html=None):
    """Top nav: logo left; menu items from config index (nav key). All output is under SITE_DIR, which is the web root (same-dir links)."""
    prefix, index_href, logo_src = "", "index.html", "logo.svg"
    links = "".join(
        f'<li><a href="{prefix}{href}">{_html.escape(label)}</a></li>'
        for href, label, _, _ in _nav_items()
    )
    row = f"""  <div class="nav-row">
  <a href="{index_href}" class="nav-logo"><img src="{logo_src}" alt="" class="nav-logo-icon">Seed Nuggets</a>
  <ul class="nav-links">
    {links}
  </ul>
</div>"""
    extra = f"\n{layer_tabs_html}" if layer_tabs_html else ""
    return f"""
<nav>
{row}{extra}
</nav>"""

NAV_SCROLL_SCRIPT = """
<script>
(function(){
  var t = 0;
  function update(){
    var y = window.scrollY || window.pageYOffset;
    var on = y > 80;
    if (on === (document.body.classList.contains("nav-scrolled"))) return;
    document.body.classList.toggle("nav-scrolled", on);
  }
  window.addEventListener("scroll", function(){ if (t) cancelAnimationFrame(t); t = requestAnimationFrame(update); }, { passive: true });
  window.addEventListener("load", update);
  update();
})();
</script>
"""

def foot(logo_href="logo.svg"):
    home_href = "index.html"
    logo_block = f'''
<div class="page-end">
  <a href="{home_href}" class="page-end-logo" aria-label="Seed Nuggets home">
    <img src="{logo_href}" alt="" width="32" height="32">
  </a>
</div>
'''
    return logo_block + "\n" + NAV_SCROLL_SCRIPT

def head(title, extra="", at_root=False, css_href=None, icon_href=None):
    if css_href is None:
        css_href = "site.css"
    if icon_href is None:
        icon_href = "logo.svg"
    links = _head_links(css_href=css_href, icon_href=icon_href)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Seed Nuggets</title>
{links}
{extra}
</head>
<body>"""

def close():
    return "\n</body>\n</html>"

_LIST_MARKERS = ("- ", "* ")


def _block_to_html(block):
    """Convert a single block (paragraph or list) to HTML."""
    lines = [ln.strip() for ln in block.strip().splitlines() if ln.strip()]
    if not lines:
        return ""
    if any(ln.startswith(_LIST_MARKERS) for ln in lines):
        items = []
        for ln in lines:
            for m in _LIST_MARKERS:
                if ln.startswith(m):
                    items.append(f"<li>{ln[len(m):].strip()}</li>")
                    break
            else:
                items.append(f"<li>{ln}</li>")
        return f"<ul>\n" + "\n".join(items) + "\n</ul>"
    return f"<p>{' '.join(lines)}</p>"

def text_to_html(text):
    """Convert plain text with --- dividers, paragraphs, and - / * lists to HTML."""
    if section_is_tbd(text):
        return '<p class="dim placeholder">This layer is not yet written.</p>'
    parts = text.split("\n---\n")
    html_parts = []
    for part in parts:
        blocks = []
        current = []
        in_list = None
        for line in part.splitlines():
            is_list_line = any(line.strip().startswith(m) for m in _LIST_MARKERS)
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
    if section_is_tbd(text):
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

def build_nugget(n, all_nuggets):
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
            rstatus = r.get("status", "empty")
            card_class = "related-card related-card-prelim" if rstatus in ("empty", "prelim") else "related-card"
            cards += f"""
      <a href="{rfile}" class="{card_class}">
        <div class="related-num">{display_number(rnum)}</div>
        <div class="related-title">{rtitle}</div>
      </a>"""
        related_cards_html = f'<div class="related-grid">{cards}\n      </div>'

    surface_raw = layers.get("surface", "TBD")
    surface_expanded = expand_nugget_directives(surface_raw, all_nuggets) if surface_raw else surface_raw
    surface_html = "" if section_is_tbd(surface_expanded) else text_to_html(surface_expanded)
    if surface_html and "Try this:" in surface_expanded:
        parts = surface_expanded.split("Try this:")
        before = text_to_html("Try this:".join(parts[:-1]))
        cta_text = "Try this: " + parts[-1].strip()
        surface_html = before + f'<div class="cta">{cta_text}</div>'

    def layer_has_content(layer_id):
        if layer_id == "references":
            prov_raw = layers.get("provenance", "TBD")
            prov_expanded = expand_nugget_directives(prov_raw, all_nuggets) if prov_raw else prov_raw
            return not section_is_tbd(prov_expanded) or bool(n.get("refs"))
        return not section_is_tbd(layers.get(layer_id))

    def layer_body(layer_id):
        if layer_id == "references":
            prov_raw = layers.get("provenance", "TBD")
            prov_expanded = expand_nugget_directives(prov_raw, all_nuggets) if prov_raw else prov_raw
            prov_html = text_to_html(prov_expanded) if not section_is_tbd(prov_expanded) else ""
            parts = []
            if prov_html:
                parts.append(f'<div class="prose">{prov_html}</div>')
            refs_list = n.get("refs", [])
            if refs_list:
                parts.append('<h3 class="layer-heading ref-heading">Further reading</h3>')
                parts.append('<div class="prose ref-list">')
                for ref_text in refs_list:
                    if ref_text:
                        parts.append(f'<p class="ref-entry">{_html.escape(ref_text)}</p>')
                parts.append("</div>")
            if rel_nuggets:
                parts.append('<div class="related-section">')
                if prov_html or refs_list:
                    parts.append('<h3 class="layer-heading related-label">Related seeds</h3>')
                parts.append(related_cards_html)
                parts.append("</div>")
            return "\n    ".join(parts)
        if layer_id == "surface":
            return surface_html
        raw = layers.get(layer_id, "TBD")
        expanded = expand_nugget_directives(raw, all_nuggets) if raw else raw
        if layer_id == "script":
            return script_to_html(expanded)
        return text_to_html(expanded)

    tabs_parts = []
    for layer_id, label in LAYER_ORDER:
        if layer_has_content(layer_id):
            tabs_parts.append(f'<a href="#{layer_id}" class="layer-tab">{label}</a>')
        else:
            tabs_parts.append(f'<span class="layer-tab layer-tab-disabled">{label}</span>')

    sections_parts = []
    refs_section_shown = layer_has_content("references")
    for layer_id, label in LAYER_ORDER:
        if not layer_has_content(layer_id):
            continue
        body = layer_body(layer_id)
        if layer_id == "references":
            section_content = f'<h2 class="layer-heading">{label}</h2>\n    {body}'
        else:
            section_content = f'<h2 class="layer-heading">{label}</h2>\n    <div class="prose">{body}</div>'
        if layer_id == "surface" and rel_nuggets and not refs_section_shown:
            section_content += f'\n    <div class="related-section"><h3 class="layer-heading related-label">Related seeds</h3>\n      {related_cards_html}\n    </div>'
        sections_parts.append(f'  <section id="{layer_id}" class="layer-section">\n    {section_content}\n  </section>')

    tabs_html = "\n      ".join(tabs_parts)
    sections_html = "\n\n".join(sections_parts)

    sorted_nuggets = sorted(all_nuggets, key=lambda x: x.get("number", ""))
    idx = next((i for i, x in enumerate(sorted_nuggets) if x.get("filename") == n.get("filename")), -1)
    prev_n = sorted_nuggets[idx - 1] if idx > 0 else None
    next_n = sorted_nuggets[idx + 1] if 0 <= idx < len(sorted_nuggets) - 1 else None

    prev_html = f'<a href="{prev_n.get("filename", "")}.html">&lt;&lt;</a>' if prev_n else ''
    next_html = f'<a href="{next_n.get("filename", "")}.html">&gt;&gt;</a>' if next_n else ''

    layer_tabs_html = f"""  <div class="layer-tabs">
    <div class="layer-tabs-inner">
      <span class="layer-tabs-prev">{prev_html}</span>
      <div class="layer-tabs-center">
        {tabs_html}
      </div>
      <span class="layer-tabs-next">{next_html}</span>
    </div>
  </div>"""

    html = head(f"{display_number(num)} — {title}")
    html += nav(from_d=True, layer_tabs_html=layer_tabs_html)
    html += f"""
<div class="wrap">
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


def tag_slug(tag):
    return tag.replace(" ", "-")


def term_slug(term):
    """Slug for explainer term anchors: lowercase, spaces to hyphens, parentheticals become -inner-."""
    s = re.sub(r"\s*\(([^)]*)\)\s*", r"-\1-", term)
    s = s.strip().lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9-]", "", s).strip("-")
    return s or "term"


def load_explainers_csv(path):
    """Load content/explainers.csv. Returns list of dicts: term, slug, links [{url, duration, title}], notes [str]."""
    if not path.exists():
        return []
    by_term = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 4 or (row[0].lower() == "term" and row[1].lower() == "url"):
                continue
            term, url, duration, title = (row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip())
            if not term:
                continue
            if term not in by_term:
                by_term[term] = {"links": [], "notes": []}
            if url.lower() == "comment":
                by_term[term]["notes"].append(title)
            else:
                by_term[term]["links"].append({"url": url, "duration": duration or "?:??", "title": title or "Watch"})
    return [
        {"term": term, "slug": term_slug(term), "links": data["links"], "notes": data["notes"]}
        for term, data in by_term.items()
    ]


def get_glossary_terms(nuggets):
    """Set of term strings from #term in all nuggets."""
    out = set()
    for n in nuggets:
        for term, _ in n.get("terms", []):
            out.add(term)
    return out


def ensure_explainers_has_glossary_terms(csv_path, glossary_terms):
    """Append any glossary term missing from the CSV as a comment row (No explainers found yet.). Returns list of added terms."""
    existing_terms = set()
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header and len(header) >= 4:
            rows.append(header)
        for row in reader:
            if len(row) >= 4 and row[0].strip():
                existing_terms.add(row[0].strip())
                rows.append(row)
    added = []
    for t in sorted(glossary_terms):
        if t not in existing_terms:
            rows.append([t, "comment", "", "(No explainers found yet.)"])
            added.append(t)
    if added:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
    return added


def _parse_explainer_link_text(text):
    """Parse link text into (duration_display, title). Duration is 'M:SS' or ''; title is cleaned or 'Watch'."""
    for prefix in ("check duration; ", "check duration, "):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    if not text or text in ("(", ")", "()"):
        return ("", "Watch")
    m = re.match(r"^(\d+):(\d+)[;,]?\s*(.*)$", text)
    if m:
        mins, secs = int(m.group(1)), int(m.group(2))
        total_secs = mins * 60 + secs
        display_m, display_s = total_secs // 60, total_secs % 60
        title = m.group(3).strip()
        return (f"{display_m}:{display_s:02d}", title if title else "Watch")
    m = re.match(r"^(\d+)\s*min(?:\s+(\d+)\s*secs?)?[;,]?\s*(.*)$", text, re.IGNORECASE)
    if m:
        mins = int(m.group(1))
        secs = int(m.group(2)) if m.group(2) else 0
        total_secs = mins * 60 + secs
        display_m, display_s = total_secs // 60, total_secs % 60
        title = m.group(3).strip()
        return (f"{display_m}:{display_s:02d}", title if title else "Watch")
    return ("", text.strip() or "Watch")


def _title_case(s):
    """Return string in Title Case (major words capitalized, small words lowercase unless first/last)."""
    if not s:
        return s
    small = frozenset(
        "a an the and but or for nor on at to by of in with as is it".split()
    )
    words = s.split()
    result = []
    for i, w in enumerate(words):
        if not w:
            result.append(w)
            continue
        lower = w.lower()
        if lower in small and i != 0 and i != len(words) - 1:
            result.append(lower)
        else:
            result.append(w[0].upper() + w[1:].lower() if len(w) > 1 else w.upper())
    return " ".join(result)


def _explainer_sort_key(term):
    """Sort key for terms: strip leading 'The ' for alphabetical order."""
    t = term.strip().lower()
    if t.startswith("the "):
        t = t[4:].strip()
    return t


def _explainer_block_html(entry):
    """HTML for one term's explainer content: notes + link lines. Used in glossary."""
    real_notes = [n for n in entry.get("notes", []) if n != "(No explainers found yet.)"]
    if not entry["links"]:
        real_notes = ["(No explainers found yet.)"]
    notes_html = "".join(
        '<p class="dim explainer-notes">' + _html.escape(n) + "</p>" for n in real_notes
    )
    link_lines = []
    for link in entry["links"]:
        url_esc = _html.escape(link["url"])
        dur_display = link["duration"] or "?:??"
        title_esc = _html.escape(_title_case(link["title"]))
        link_lines.append(
            f'<div class="explainer-link-line">'
            f'<span class="explainer-dur">{dur_display}</span> '
            f'<a class="explainer-link" href="{url_esc}" target="_blank" rel="noopener">{title_esc}</a>'
            f'</div>'
        )
    return notes_html + "".join(link_lines)


def build_explainers_page(nuggets, explainer_terms):
    """Build explainers.html from explainers data. Terms sorted alphabetically (strip 'The ' for sort); uses glossary styles."""
    if not explainer_terms:
        body = '<p class="dim">No explainers list. Add <code>content/explainers.csv</code>.</p>'
    else:
        sorted_terms = sorted(explainer_terms, key=lambda t: _explainer_sort_key(t["term"]))
        parts = []
        for entry in sorted_terms:
            term = entry["term"]
            slug = entry["slug"]
            term_esc = _html.escape(term)
            real_notes = [n for n in entry.get("notes", []) if n != "(No explainers found yet.)"]
            if not entry["links"]:
                real_notes = ["(No explainers found yet.)"]
            notes_html = "".join(
                '<p class="dim explainer-notes">' + _html.escape(n) + "</p>" for n in real_notes
            )
            link_lines = []
            for link in entry["links"]:
                url_esc = _html.escape(link["url"])
                dur_display = link["duration"] or "?:??"
                title_esc = _html.escape(_title_case(link["title"]))
                link_lines.append(
                    f'<div class="explainer-link-line">'
                    f'<span class="explainer-dur">{dur_display}</span> '
                    f'<a class="explainer-link" href="{url_esc}" target="_blank" rel="noopener">{title_esc}</a>'
                    f'</div>'
                )
            links_html = "".join(link_lines)
            block_content = notes_html + links_html
            links_block = f'<div class="gloss-defs"><div class="gloss-def-block">{block_content}</div></div>'
            parts.append(
                f'<div id="{_html.escape(slug)}" class="gloss-entry">'
                f'<div class="gloss-term-line"><strong class="gloss-term">{term_esc}</strong></div>'
                f'{links_block}'
                f"</div>"
            )
        body = "\n".join(parts)
    html = head("Explainers")
    html += nav(from_d=True)
    html += f'<div class="wrap"><div class="page-body fade"><h1>Explainers</h1><p class="dim repo-intro">Video explainers for glossary terms. (Relevance not verified)</p>{body}</div></div>'
    html += foot()
    html += close()
    return html


def build_tags_page(nuggets, status_order, explainer_terms=None):
    all_tags = set()
    for n in nuggets:
        all_tags.update(n.get("tags", []))
    sorted_tags = sorted(all_tags)

    all_statuses = set(n.get("status", "empty") for n in nuggets)
    sorted_statuses = [s for s in status_order if s in all_statuses]

    def block_for_tag(label, slug, matching):
        parts = [f'<hr class="index-tag-rule"><div id="{slug}" class="index-tag-name">{_html.escape(label)}</div>']
        for i, n in enumerate(matching):
            num = n.get("number", "")
            title = n.get("title", "")
            subtitle = n.get("subtitle", "")
            fname = n.get("filename", "") + ".html"
            title_display = f"{display_number(num)}. {title}" if num else title
            if i > 0:
                parts.append('<hr class="index-entry-rule">')
            parts.append(
                f'<div class="index-entry"><a href="{fname}">{_html.escape(title_display)}</a>'
                f'<br><span class="repo-subtitle">{_html.escape(subtitle)}</span></div>'
            )
        return "\n    ".join(parts)

    tag_blocks = ""
    for tag in sorted_tags:
        tag_blocks += block_for_tag(tag, tag_slug(tag), [n for n in nuggets if tag in n.get("tags", [])])
    status_blocks = ""
    for status in sorted_statuses:
        status_blocks += block_for_tag(status, f"status-{status}", [n for n in nuggets if n.get("status", "empty") == status])

    terms_block = ""
    if explainer_terms:
        sorted_explainer = sorted(explainer_terms, key=lambda t: _explainer_sort_key(t["term"]))
        term_parts = []
        for entry in sorted_explainer:
            term_esc = _html.escape(entry["term"])
            slug = entry["slug"]
            term_parts.append(f'<div class="index-entry"><a href="glossary.html#{_html.escape(slug)}">{term_esc}</a> 📺</div>')
        terms_block = "\n    ".join(term_parts)

    terms_section = ""
    if terms_block:
        terms_section = f"""
    <h2 class="index-section-head">Terms</h2>
    <div class="index-by-tag">
    {terms_block}
    </div>"""

    html = head("Index")
    html += nav(from_d=True)
    html += f"""
<div class="wrap">
  <div class="page-body fade">
    <h1>Index</h1>
    <div class="index-by-tag">
    {tag_blocks}
    </div>
    <h2 class="index-section-head">Statuses</h2>
    <div class="index-by-tag">
    {status_blocks}
    </div>{terms_section}
  </div>
</div>"""
    html += foot()
    html += close()
    return html


def _md_context(**overrides):
    """Default context for process_md_to_html: warn, build_time, content_dir, site_dir. Merge with overrides."""
    copy = overrides.get("copy", load_index_copy())
    return {"warn": _warn, "build_time": BUILD_TIME, "content_dir": CONTENT_DIR, "site_dir": (copy.get("site_dir") or "").strip(), **overrides}


def build_index(nuggets, index_copy, status_order, collected_md_refs=None):
    context = _md_context(nuggets=nuggets, status_order=status_order, copy=index_copy, page="home")
    body_html = process_md_to_html(CONTENT_DIR / "home.md", context, collected_md_refs=collected_md_refs)

    html = head("Seed Nuggets")
    html += nav()
    html += f'<div class="wrap"><div class="page-body home-page fade">{body_html}</div></div>'
    html += foot()
    html += close()
    return html


def build_static_page(title, body_html, wrap_class=""):
    html = head(title)
    html += nav(from_d=True)
    wrap_attr = f' class="wrap {wrap_class}"' if wrap_class else ' class="wrap"'
    html += f'<div{wrap_attr}><div class="page-body fade">{body_html}</div></div>'
    html += foot()
    html += close()
    return html


def build_map_graph_page(nuggets):
    """Full page with standard nav and background that embeds the map graph SVG."""
    svg = build_graph_svg(nuggets, show_title=False, link_nuggets=True)
    body_html = '<h1>Map</h1>\n<p class="dim">How the Seed Nuggets are related.</p>\n<div class="map-graph-wrap">' + svg + '</div>'
    return build_static_page("Map graph", body_html, wrap_class="wrap--full")


def build_md_file_page(md_path, nuggets=None, collected_md_refs=None, status_order=None, index_copy=None):
    context = _md_context(
        nuggets=nuggets or [],
        status_order=status_order,
        copy=index_copy,
        page=md_path.stem,
    )
    body_html = process_md_to_html(md_path, context, collected_md_refs=collected_md_refs)
    title = _first_h1(md_path) or md_path.stem.replace("-", " ").title()
    html = head(title)
    html += nav(from_d=True)
    html += f'<div class="wrap"><div class="page-body fade">{body_html}</div></div>'
    html += foot()
    html += close()
    return html


def build_md_dir_page(dir_path, nuggets=None, collected_md_refs=None):
    page_md = dir_path / "page.md"
    context = _md_context(nuggets=nuggets or [])
    body_html = process_md_to_html(page_md, context, collected_md_refs=collected_md_refs)
    title = _first_h1(page_md) or dir_path.name.replace("-", " ").title()
    html = head(title)
    html += nav(from_d=True)
    html += f'<div class="wrap"><div class="page-body fade">{body_html}</div></div>'
    html += foot()
    html += close()
    return html


def build_internal_page(nuggets=None, collected_md_refs=None):
    context = _md_context(nuggets=nuggets or [])
    body_html = process_md_to_html(INTERNAL_DIR / "page.md", context, collected_md_refs=collected_md_refs)
    html = head("Internal")
    html += nav(from_d=True)
    html += f'<div class="wrap"><div class="page-body fade">{body_html}</div></div>'
    html += foot()
    html += close()
    return html


def build_bibliography_page(nuggets):
    """Build Bibliography from #ref (full text) in #provenance of all nuggets. Sorted by exact ref text; lists which nuggets cite each."""
    by_text = {}
    for n in nuggets:
        num = n.get("number", "")
        fname = n.get("filename", "") + ".html"
        title_display = display_number(num)
        for ref_text in n.get("refs", []):
            ref_text = (ref_text or "").strip()
            if not ref_text:
                continue
            if ref_text not in by_text:
                by_text[ref_text] = []
            by_text[ref_text].append((title_display, fname))
    entries = sorted(by_text.items(), key=lambda x: x[0].lower())
    parts = []
    for ref_text, nugget_list in entries:
        sorted_nugs = sorted(nugget_list, key=lambda x: (int(x[0]) if x[0].isdigit() else 999, x[0]))
        nugget_links = " ".join(f'<a href="{fname}">{disp}</a>' for disp, fname in sorted_nugs)
        ref_esc = _html.escape(ref_text)
        parts.append(
            f'<div class="bib-entry"><span class="bib-text">{ref_esc}</span> '
            f'<span class="bib-in">In:</span> {nugget_links}</div>'
        )
    body = "\n".join(parts) if parts else "<p class=\"dim\">No references yet. Add <code>#ref</code> lines (full citation text) inside <code>#provenance</code> in any nugget.</p>"
    html = head("Bibliography")
    html += nav(from_d=True)
    html += f'<div class="wrap"><div class="page-body fade"><h1>Bibliography</h1><p class="dim repo-intro">References from all nuggets.  Duplicates will be merged later.</p>{body}</div></div>'
    html += foot()
    html += close()
    return html


def build_glossary_page(nuggets, explainer_terms=None):
    """Build Glossary from #term (Term — Definition) in #provenance of all nuggets. Grouped by term; term in bold, definitions indented. Explainers merged below each term's definition."""
    explainer_by_slug = {e["slug"]: e for e in (explainer_terms or [])}
    by_entry = {}
    for n in nuggets:
        num = n.get("number", "")
        fname = n.get("filename", "") + ".html"
        title_display = display_number(num)
        for term, definition in n.get("terms", []):
            entry_key = (term, definition)
            if entry_key not in by_entry:
                by_entry[entry_key] = []
            by_entry[entry_key].append((title_display, fname))
    by_term = {}
    for (term, definition), nugget_list in by_entry.items():
        if term not in by_term:
            by_term[term] = []
        sorted_nugs = sorted(nugget_list, key=lambda x: (int(x[0]) if x[0].isdigit() else 999, x[0]))
        by_term[term].append((definition, sorted_nugs))
    parts = []
    for term in sorted(by_term.keys(), key=lambda t: t.lower()):
        term_esc = _html.escape(term)
        slug = term_slug(term)
        all_nuggets = []
        seen = set()
        for definition, nugget_list in by_term[term]:
            for disp, fname in nugget_list:
                if (disp, fname) not in seen:
                    seen.add((disp, fname))
                    all_nuggets.append((disp, fname))
        all_nuggets.sort(key=lambda x: (int(x[0]) if x[0].isdigit() else 999, x[0]))
        nugget_links = ", ".join(f'<a href="{fname}">{disp}</a>' for disp, fname in all_nuggets)
        in_part = f' ({nugget_links})' if nugget_links else ""
        term_line = f'<div class="gloss-term-line"><strong class="gloss-term">{term_esc}</strong>{in_part}</div>'
        def_blocks = []
        for definition, nugget_list in by_term[term]:
            def_esc = _html.escape(definition)
            if definition:
                def_blocks.append(f'<div class="gloss-def-block"><span class="gloss-def">{def_esc}</span></div>')
        if slug in explainer_by_slug:
            def_blocks.append(
                '<div class="gloss-def-block">' + _explainer_block_html(explainer_by_slug[slug]) + '</div>'
            )
        entry_id = f' id="{_html.escape(slug)}"' if slug in explainer_by_slug else ""
        parts.append(
            f'<div class="gloss-entry"{entry_id}>'
            f'{term_line}'
            f'<div class="gloss-defs">' + "\n".join(def_blocks) + '</div>'
            f'</div>'
        )
    body = "\n".join(parts) if parts else "<p class=\"dim\">No terms yet. Add <code>#term Term — Definition</code> lines inside <code>#provenance</code> in any nugget.</p>"
    html = head("Glossary")
    html += nav(from_d=True)
    html += f'<div class="wrap"><div class="page-body fade"><h1>Glossary</h1><p class="dim repo-intro">Key terms from all nuggets.</p>{body}</div></div>'
    html += foot()
    html += close()
    return html


def build_4u_ai_txt():
    """Write d/4u-ai.txt: concatenation of raw content/internal/*.md and content/nuggets/*.txt."""
    parts = []
    for p in sorted(INTERNAL_DIR.glob("*.md")):
        parts.append(f"=== content/internal/{p.name} ===\n\n{p.read_text(encoding='utf-8')}")
    for p in sorted(NUGGETS_DIR.glob("*.txt")):
        parts.append(f"=== content/nuggets/{p.name} ===\n\n{p.read_text(encoding='utf-8')}")
    (SITE_DIR / "4u-ai.txt").write_text("\n\n".join(parts), encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global BUILD_TIME, SITE_DIR
    index_copy = load_index_copy()
    site_dir = (index_copy.get("site_dir") or "").strip()
    if not site_dir:
        raise SystemExit("config/index.txt must set site_dir")
    SITE_DIR = _ROOT / site_dir
    filter_num = None
    if "--nugget" in sys.argv:
        idx = sys.argv.index("--nugget")
        filter_num = sys.argv[idx + 1]

    nothing_changed = False
    state_lines = BUILD_STATE_FILE.read_text(encoding="utf-8").splitlines() if BUILD_STATE_FILE.exists() else []
    if len(state_lines) >= 2:
        try:
            BUILD_TIME = datetime.fromisoformat(state_lines[1].strip())
        except ValueError:
            BUILD_TIME = datetime.now(ZoneInfo("America/Los_Angeles"))
    else:
        BUILD_TIME = datetime.now(ZoneInfo("America/Los_Angeles"))
    if not filter_num:
        current_hash = get_build_input_hash()
        if len(state_lines) >= 2 and state_lines[0].strip() == current_hash:
            nothing_changed = True
        else:
            BUILD_TIME = datetime.now(ZoneInfo("America/Los_Angeles"))

    if filter_num:
        SITE_DIR.mkdir(exist_ok=True)
    else:
        if SITE_DIR.exists():
            shutil.rmtree(SITE_DIR)
        SITE_DIR.mkdir(parents=True)

    nuggets = load_all_nuggets(warn=_warn)
    print(f"Loaded {len(nuggets)} nuggets")
    seen_num = {}
    for n in nuggets:
        num = n.get("number")
        if num:
            if num in seen_num:
                _warn(f"Warning: duplicate #number {num} (in {seen_num[num]}.txt and {n.get('filename')}.txt).")
            else:
                seen_num[num] = n.get("filename")

    for md_path in _get_md_page_paths():
        if not md_path.exists():
            raise SystemExit(f"Required file missing: {md_path}")
    status_order = _require_status_order()

    for n in nuggets:
        s = n.get("status", "empty")
        if s not in status_order:
            _warn(f"Error: nugget {n.get('filename', '?')}: status {s!r} not in config/status.txt")

    for n in nuggets:
        if filter_num and n.get("number") != filter_num:
            continue
        fname = n.get("filename", "") + ".html"
        out = SITE_DIR / fname
        out.write_text(build_nugget(n, nuggets), encoding="utf-8")
        print(f"  Built {fname}")

    if not filter_num:
        shutil.copy(CONFIG_DIR / "site.css", SITE_DIR / "site.css")
        print("  Built site.css")
        if (CONFIG_DIR / "logo.svg").exists():
            shutil.copy(CONFIG_DIR / "logo.svg", SITE_DIR / "logo.svg")
            print("  Built logo.svg")

        if EXPLAINERS_CSV.exists():
            added = ensure_explainers_has_glossary_terms(EXPLAINERS_CSV, get_glossary_terms(nuggets))
            for t in added:
                print("  Added explainer term:", t)
        explainer_terms = load_explainers_csv(EXPLAINERS_CSV)

        (SITE_DIR / "tags.html").write_text(build_tags_page(nuggets, status_order, explainer_terms), encoding="utf-8")
        print("  Built tags.html")

        collected_md_refs = set()
        nav_items = get_nav_items(index_copy)
        for href, label, kind, path in nav_items:
            if kind == "file":
                (SITE_DIR / href).write_text(
                    build_md_file_page(path, nuggets, collected_md_refs, status_order, index_copy),
                    encoding="utf-8",
                )
                print(f"  Built {href}")
            elif kind == "dir":
                (SITE_DIR / href).write_text(build_md_dir_page(path, nuggets, collected_md_refs), encoding="utf-8")
                print(f"  Built {href}")

        (SITE_DIR / "internal.html").write_text(build_internal_page(nuggets, collected_md_refs), encoding="utf-8")
        print("  Built internal.html")

        built_md_refs = set()
        to_build = list(collected_md_refs)
        while to_build:
            md_path = to_build.pop(0)
            if md_path in built_md_refs:
                continue
            built_md_refs.add(md_path)
            body_html = process_md_to_html(md_path, _md_context(nuggets=nuggets), collected_md_refs)
            title = md_path.stem.replace("-", " ").title()
            out_name = _md_link_output_name(md_path, CONTENT_DIR)
            if out_name:
                (SITE_DIR / out_name).write_text(build_static_page(title, body_html), encoding="utf-8")
                print(f"  Built {out_name}")
            for p in collected_md_refs - built_md_refs:
                if p not in to_build:
                    to_build.append(p)

        (SITE_DIR / "bibliography.html").write_text(build_bibliography_page(nuggets), encoding="utf-8")
        print("  Built bibliography.html")

        (SITE_DIR / "glossary.html").write_text(build_glossary_page(nuggets, explainer_terms), encoding="utf-8")
        print("  Built glossary.html")

        for stale in ["index.html", "favicon.svg"]:
            p = _ROOT / stale
            if p.exists():
                p.unlink()
        index_html = build_index(nuggets, index_copy, status_order, collected_md_refs)
        (SITE_DIR / "index.html").write_text(index_html, encoding="utf-8")
        if (CONFIG_DIR / "logo.svg").exists():
            shutil.copy(CONFIG_DIR / "logo.svg", SITE_DIR / "favicon.svg")
            print("  Built favicon.svg")
        print("  Built index.html")

        (SITE_DIR / "map.svg").write_text(build_graph_svg(nuggets, show_title=False, link_nuggets=True), encoding="utf-8")
        print("  Built map.svg")
        (SITE_DIR / "map-graph.html").write_text(build_map_graph_page(nuggets), encoding="utf-8")
        print("  Built map-graph.html")

        build_4u_ai_txt()
        print("  Built 4u-ai.txt")

        BUILD_STATE_FILE.write_text(
            current_hash + "\n" + BUILD_TIME.isoformat(),
            encoding="utf-8",
        )

    print(f"\nDone. Site written to {SITE_DIR.relative_to(_ROOT)}/ (web root)")
    if nothing_changed:
        print("Nothing changed; timestamp unchanged.")
    if _warn_count:
        sys.exit(1)

if __name__ == "__main__":
    main()
