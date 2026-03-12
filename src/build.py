#!/usr/bin/env python3
"""
build.py — Seed Nuggets site generator
Reads nugget .txt files from repo nuggets/, writes HTML to repo d/.
Generates: nugget pages, list.html, tags.html (Index),
index.html, about pages, resources (with map), site.css.

Usage:
    python src/build.py   (from repo root)
    python build.py --nugget 001   # rebuild single nugget
"""

import html as _html
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

_ROOT = Path(__file__).resolve().parent.parent
from nugget_parser import NUGGETS_DIR, load_all_nuggets, nugget_by_number, expand_nugget_directives

ABOUT_DIR = _ROOT / "about"
INTERNAL_DIR = _ROOT / "internal"
CONTENT_DIR = _ROOT / "content"
SITE_DIR = _ROOT / "d"

BUILD_TIME = None
_warn_count = 0

def _warn(msg):
    global _warn_count
    print(msg, file=sys.stderr)
    _warn_count += 1

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
    t = (BUILD_TIME or datetime.now(ZoneInfo("America/Los_Angeles"))).strftime("%Y-%m-%d %H:%M Pacific")
    html = html.replace("@timestamp", t)
    return html


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


def _expand_includes(text, base_dir):
    """Replace lines @include filename with file contents from base_dir. Paths resolved under base_dir."""
    base_dir = Path(base_dir).resolve()
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("@include "):
            name = stripped[8:].strip()
            inc_path = (base_dir / name).resolve()
            if not str(inc_path).startswith(str(base_dir)):
                _warn(f"Warning: @include {name!r} resolves outside {base_dir}")
                continue
            if not inc_path.exists():
                _warn(f"Warning: @include {name!r} not found")
                continue
            out.append(inc_path.read_text(encoding="utf-8"))
        else:
            out.append(line)
    return "\n".join(out)


def load_page_md(dir_path, main_filename, required=False):
    """Load a directory page: main file with @include, or all .md alphabetically with ## heading. Returns markdown."""
    dir_path = Path(dir_path)
    main_path = dir_path / main_filename
    if main_path.exists():
        return _expand_includes(main_path.read_text(encoding="utf-8"), dir_path)
    if required:
        raise SystemExit(f"Required file missing: {main_path}")
    parts = []
    for f in sorted(dir_path.glob("*.md")):
        parts.append(f"## {f.stem}\n\n{f.read_text(encoding='utf-8')}")
    return "\n\n".join(parts) if parts else ""


def load_resources_content():
    """Load content/resources.md (with @include). Required."""
    if not (CONTENT_DIR / "resources.md").exists():
        raise SystemExit("Required file missing: content/resources.md")
    return load_page_md(CONTENT_DIR, "resources.md")


def load_about_page_content():
    """Load about/page.md (with @include). Required."""
    if not (ABOUT_DIR / "page.md").exists():
        raise SystemExit("Required file missing: about/page.md")
    return load_page_md(ABOUT_DIR, "page.md", required=True)


def load_internal_page_content():
    """Load internal/page.md (with @include). Required."""
    if not (INTERNAL_DIR / "page.md").exists():
        raise SystemExit("Required file missing: internal/page.md")
    return load_page_md(INTERNAL_DIR, "page.md", required=True)


def load_status_order():
    """Load content/status.txt: one status per line, in sort order (most ready first). Required."""
    p = CONTENT_DIR / "status.txt"
    if not p.exists():
        raise SystemExit("Required file missing: content/status.txt")
    order = [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    return order


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _head_links(css_href="site.css"):
    return f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{css_href}">
"""

def nav(from_d=False):
    """About, List, Resources. from_d=True for pages under d/."""
    prefix = "" if from_d else "d/"
    index_href = "../index.html" if from_d else "index.html"
    return f"""
<nav>
  <a href="{index_href}" class="nav-logo">Seed Nuggets</a>
  <ul class="nav-links">
    <li><a href="{prefix}about.html">About</a></li>
    <li><a href="{prefix}list.html">List</a></li>
    <li><a href="{prefix}resources.html">Resources</a></li>
  </ul>
</nav>"""

def foot():
    return """
<footer>
  <span>Seed Nuggets</span>
</footer>"""

def head(title, extra="", at_root=False):
    links = _head_links("d/site.css" if at_root else "site.css")
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
    surface_html = "" if (surface_expanded or "TBD").strip() == "TBD" else text_to_html(surface_expanded)
    if surface_html and "Try this:" in surface_expanded:
        parts = surface_expanded.split("Try this:")
        before = text_to_html("Try this:".join(parts[:-1]))
        cta_text = "Try this: " + parts[-1].strip()
        surface_html = before + f'<div class="cta">{cta_text}</div>'

    def layer_has_content(layer_id):
        if layer_id == "references":
            prov_raw = (layers.get("provenance") or "TBD").strip()
            return prov_raw != "TBD" or bool(rel_nuggets) or bool(n.get("refs"))
        raw = (layers.get(layer_id) or "TBD").strip()
        return raw != "TBD"

    def layer_body(layer_id):
        if layer_id == "references":
            prov_raw = layers.get("provenance", "TBD")
            prov_expanded = expand_nugget_directives(prov_raw, all_nuggets) if prov_raw else prov_raw
            prov_html = text_to_html(prov_expanded) if (prov_expanded or "TBD").strip() != "TBD" else ""
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
    html += nav(from_d=True)
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


def build_list(nuggets, status_order):
    status_rank = {s: i for i, s in enumerate(status_order)}
    key_status = lambda n: status_rank.get(n.get("status", "empty"), len(status_order))
    key_num = lambda n: int(n.get("number", "0")) if (n.get("number") or "").isdigit() else 0
    sorted_nuggets = sorted(nuggets, key=lambda n: (key_status(n), key_num(n)))
    rows = ""
    for n in sorted_nuggets:
        num = n.get("number", "")
        shortname = n.get("shortname", "")
        title = n.get("title", "")
        subtitle = n.get("subtitle", "")
        status = n.get("status", "empty")
        date = n.get("date", "")
        tag_links = " ".join(f'<a href="tags.html#{tag_slug(t)}" class="tag">{t}</a>' for t in n.get("tags", []))
        fname = n.get("filename", "") + ".html"
        status_class = f"status-{status.replace(' ','')}"
        rank = status_rank.get(status, len(status_order))
        num_val = key_num(n)
        date_val = date.strip() or "0000-00-00"
        title_attr = _html.escape(title, quote=True)
        rows += f"""
    <tr data-num="{num_val}" data-date="{date_val}" data-status-rank="{rank}" data-title="{title_attr}">
      <td class="mono repo-cell-mono">{display_number(num)}</td>
      <td class="mono repo-cell-mono">{shortname}</td>
      <td><a href="{fname}">{title}</a><br><span class="repo-subtitle">{subtitle}</span></td>
      <td class="{status_class}">{status}</td>
      <td class="mono repo-date">{date}</td>
      <td class="repo-tags">{tag_links}</td>
    </tr>"""

    sort_script = """
<script>
(function(){
  var tbody = document.querySelector('.repo-table tbody');
  var sel = document.getElementById('repo-sort');
  if (!tbody || !sel) return;
  function sortTable(by){
    var rows = [].slice.call(tbody.querySelectorAll('tr'));
    rows.sort(function(a,b){
      if (by === 'alpha') return (a.dataset.title || '').toLowerCase().localeCompare((b.dataset.title || '').toLowerCase());
      if (by === 'recent') return (b.dataset.date || '').localeCompare(a.dataset.date || '');
      if (by === 'number') return (+a.dataset.num) - (+b.dataset.num);
      return (+a.dataset.statusRank) - (+b.dataset.statusRank) || (+a.dataset.num) - (+b.dataset.num);
    });
    rows.forEach(function(r){ tbody.appendChild(r); });
  }
  sel.addEventListener('change', function(){ sortTable(this.value); });
  sortTable(sel.value);
})();
</script>"""
    html = head("List")
    html += nav(from_d=True)
    html += f"""
<div class="wrap">
  <div class="page-body fade">
    <h1>List</h1>
    <p class="dim repo-intro">All seed nuggets. The canonical list. Generated from source files.</p>
    <p class="repo-sort-wrap"><label for="repo-sort">Sort: </label><select id="repo-sort" class="repo-sort" aria-label="Sort table">
      <option value="status">By status</option>
      <option value="number">By number</option>
      <option value="alpha">Alphabetical</option>
      <option value="recent">By most recent</option>
    </select></p>
    <table class="repo-table">
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
</div>{sort_script}"""
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


def display_number_map(num):
    """Two-digit label for map row/column headers (no spaces)."""
    if num and num.isdigit():
        return str(int(num)).zfill(2)
    return num or "??"


def build_tags_page(nuggets, status_order):
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
    </div>
  </div>
</div>"""
    html += foot()
    html += close()
    return html


def build_index(nuggets, index_copy, status_order):
    c = index_copy
    status_rank = {s: i for i, s in enumerate(status_order)}
    key_status = lambda n: status_rank.get(n.get("status", "empty"), len(status_order))
    key_num = lambda n: int(n.get("number", "0")) if (n.get("number") or "").isdigit() else 0
    by_ready = sorted(nuggets, key=lambda n: (key_status(n), key_num(n)))
    ready = [n for n in nuggets if n.get("status") not in ("empty",)]
    total = len(nuggets)
    ready_count = len(ready)
    d = "d/"

    recent = by_ready[:5]
    recent_html = ""
    for n in recent:
        fname = n.get("filename", "") + ".html"
        num = n.get("number", "")
        title = n.get("title", "")
        subtitle = n.get("subtitle", "")
        status = n.get("status", "empty")
        stub = " stub" if status == "empty" else ""
        recent_html += f"""
    <a href="{d}{fname}" class="seed-row{stub}">
      <div class="seed-num">{display_number(num)}</div>
      <div>
        <div class="seed-title">{title}</div>
        <div class="seed-sub">{subtitle}</div>
      </div>
      <div class="seed-status-col">{status}</div>
    </a>"""

    view_all_text = (c.get("view_all") or "View all {n} seeds →").replace("{n}", str(total))
    about_cards = [
        f'<a href="{d}about.html" class="about-card">About</a>',
    ]

    html = head("Seed Nuggets", at_root=True)
    html += nav()
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
      <a href="{d}list.html" class="link-mono-small">{c.get("repo_link", "Full repository →")}</a>
    </div>
    {recent_html}
    <div class="seed-list-more-wrap">
      <a href="{d}list.html" class="link-mono-accent">{view_all_text}</a>
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


def build_static_page(title, body_html):
    html = head(title)
    html += nav(from_d=True)
    html += f'<div class="wrap"><div class="page-body fade"><h1>{title}</h1>{body_html}</div></div>'
    html += foot()
    html += close()
    return html


def build_resources_page():
    """Build Resources page from content/resources.md (with @include). Body contains its own heading."""
    raw = load_resources_content()
    body_html = about_body_to_html(raw) if raw.strip() else ""
    html = head("Resources")
    html += nav(from_d=True)
    html += f'<div class="wrap"><div class="page-body fade">{body_html}</div></div>'
    html += foot()
    html += close()
    return html


def build_about_page():
    """Build About page from about/page.md (with @include)."""
    raw = load_about_page_content()
    body_html = about_body_to_html(raw) if raw.strip() else ""
    html = head("About")
    html += nav(from_d=True)
    html += f'<div class="wrap"><div class="page-body fade">{body_html}</div></div>'
    html += foot()
    html += close()
    return html


def build_internal_page():
    """Build Internal page from internal/page.md (with @include)."""
    raw = load_internal_page_content()
    body_html = about_body_to_html(raw) if raw.strip() else ""
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


def build_glossary_page(nuggets):
    """Build Glossary from #term (Term — Definition) in #provenance of all nuggets. Grouped by term; term in bold, definitions indented."""
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
        def_blocks = []
        for definition, nugget_list in by_term[term]:
            nugget_links = " ".join(f'<a href="{fname}">{disp}</a>' for disp, fname in nugget_list)
            def_esc = _html.escape(definition)
            if definition:
                def_blocks.append(
                    f'<div class="gloss-def-block"><span class="gloss-def">{def_esc}</span> '
                    f'<span class="gloss-in">In:</span> {nugget_links}</div>'
                )
            else:
                def_blocks.append(
                    f'<div class="gloss-def-block"><span class="gloss-in">In:</span> {nugget_links}</div>'
                )
        parts.append(
            f'<div class="gloss-entry">'
            f'<div class="gloss-term-line"><strong class="gloss-term">{term_esc}</strong></div>'
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


def build_map_body(nuggets):
    """HTML body for the Map about page: N×N matrix of related links (from → to)."""
    sorted_nuggets = sorted(nuggets, key=lambda x: x.get("number", ""))
    nums = [n.get("number", "") for n in sorted_nuggets]
    related_sets = {n.get("number", ""): set(n.get("related", [])) for n in sorted_nuggets}
    rows = []
    pad = [display_number_map(num) for num in nums]
    header_cells = ["<th></th>"] + [f'<th class="map-col-label">{p[0]}<br>{p[1]}</th>' for p in pad]
    rows.append("<tr>" + "".join(header_cells) + "</tr>")
    for from_num, n in zip(nums, sorted_nuggets):
        cells = [f'<th class="map-row-label">{display_number_map(from_num)}</th>']
        for to_num in nums:
            linked = to_num in related_sets.get(from_num, set())
            cls = "map-cell-linked" if linked else "map-cell-empty"
            cells.append(f'<td class="{cls}">{"·" if linked else ""}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    table = "<table class=\"map-matrix\">\n" + "\n".join(rows) + "\n</table>"
    return f'<p>Rows = from seed, columns = to seed. Marked cell means the row seed links to the column seed in its Related list.</p>\n{table}'


def build_nuggets_index():
    """Write nuggets/index.html so that ../nuggets/ resolves on static hosts (e.g. GitHub Pages) that require an index."""
    txt_files = sorted(NUGGETS_DIR.glob("*.txt"))
    lines = [
        "<!DOCTYPE html>",
        "<html lang=\"en\">",
        "<head><meta charset=\"utf-8\"><title>Source nuggets</title></head>",
        "<body>",
        "<h1>Source nuggets</h1>",
        "<p>Raw nugget files. See the <a href=\"../d/\">site</a> for the built pages.</p>",
        "<ul>",
    ]
    for p in txt_files:
        name = p.name
        lines.append(f'  <li><a href="{_html.escape(name)}">{_html.escape(name)}</a></li>')
    lines.append("</ul>")
    lines.append("</body>")
    lines.append("</html>")
    (NUGGETS_DIR / "index.html").write_text("\n".join(lines), encoding="utf-8")


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

    load_about_page_content()
    load_internal_page_content()
    status_order = load_status_order()
    index_copy = load_index_copy()

    for n in nuggets:
        s = n.get("status", "empty")
        if s not in status_order:
            _warn(f"Error: nugget {n.get('filename', '?')}: status {s!r} not in content/status.txt")

    for n in nuggets:
        if filter_num and n.get("number") != filter_num:
            continue
        fname = n.get("filename", "") + ".html"
        out = SITE_DIR / fname
        out.write_text(build_nugget(n, nuggets), encoding="utf-8")
        print(f"  Built {fname}")

    if not filter_num:
        shutil.copy(CONTENT_DIR / "site.css", SITE_DIR / "site.css")
        print("  Built site.css")

        (SITE_DIR / "list.html").write_text(build_list(nuggets, status_order), encoding="utf-8")
        print("  Built list.html")

        (SITE_DIR / "tags.html").write_text(build_tags_page(nuggets, status_order), encoding="utf-8")
        print("  Built tags.html")

        (SITE_DIR / "resources.html").write_text(build_resources_page(), encoding="utf-8")
        print("  Built resources.html")

        (SITE_DIR / "about.html").write_text(build_about_page(), encoding="utf-8")
        print("  Built about.html")

        (SITE_DIR / "internal.html").write_text(build_internal_page(), encoding="utf-8")
        print("  Built internal.html")

        (SITE_DIR / "bibliography.html").write_text(build_bibliography_page(nuggets), encoding="utf-8")
        print("  Built bibliography.html")

        (SITE_DIR / "glossary.html").write_text(build_glossary_page(nuggets), encoding="utf-8")
        print("  Built glossary.html")

        (_ROOT / "index.html").write_text(build_index(nuggets, index_copy, status_order), encoding="utf-8")
        print("  Built index.html")

        (SITE_DIR / "map.html").write_text(build_static_page("Map", build_map_body(nuggets)), encoding="utf-8")
        print("  Built map.html")

        build_nuggets_index()
        print("  Built nuggets/index.html")

    print(f"\nDone. Site written to repo root (index.html) and {SITE_DIR.relative_to(_ROOT)}/ (docs)")
    if _warn_count:
        sys.exit(1)

if __name__ == "__main__":
    main()
