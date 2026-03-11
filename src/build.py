#!/usr/bin/env python3
"""
build.py — Seed Nuggets site generator
Reads nugget .txt files from ./nuggets/, writes HTML to ./docs/
Also generates repository.html from collected metadata.

Usage:
    python build.py
    python build.py --nugget 001   # rebuild single nugget
"""

import os
import shutil
import sys
import re
from pathlib import Path
from datetime import datetime

NUGGETS_DIR = Path("nuggets")
ABOUT_DIR = Path("about")
CONTENT_DIR = Path("content")
SITE_DIR = Path("docs")

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
                meta[key] = value.strip()
            else:
                flush()
                current_layer = key
                buffer = []
        else:
            if current_layer and current_layer not in SINGLE_LINE:
                buffer.append(line)

    flush()

    # Parse list fields
    meta["tags"] = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
    meta["related"] = [r.strip() for r in meta.get("related", "").split(",") if r.strip()]

    meta["layers"] = {
        "surface": layers.get("surface", "TBD"),
        "depth": layers.get("depth", "TBD"),
        "provenance": layers.get("provenance", "TBD"),
        "script": layers.get("script", "TBD"),
        "images": layers.get("images", "TBD"),
    }

    return meta


def load_all_nuggets():
    nuggets = []
    for f in sorted(NUGGETS_DIR.glob("*.txt")):
        try:
            n = parse_nugget(f)
            n["filename"] = f.stem  # e.g. 001-caloric
            nuggets.append(n)
        except Exception as e:
            print(f"Warning: could not parse {f}: {e}")
    return nuggets


def nugget_by_number(nuggets, num):
    for n in nuggets:
        if n.get("number") == num:
            return n
    return None


def about_body_to_html(body):
    """Convert about-page body text (## headings, - lists, paragraphs) to HTML."""
    out = []
    blocks = re.split(r"\n\n+", body.strip())
    for block in blocks:
        lines = [L for L in block.splitlines() if L.strip()]
        if not lines:
            continue
        if lines[0].startswith("## "):
            out.append(f"<h2>{lines[0][3:].strip()}</h2>")
            rest = "\n".join(lines[1:]).strip()
            if rest:
                for p in re.split(r"\n\n+", rest):
                    t = p.strip().replace(chr(10), " ")
                    if t:
                        cls = " class=\"dim placeholder\"" if t in ("TBD", "No reviews completed yet.") else ""
                        out.append(f"<p{cls}>{t}</p>")
        elif all(L.strip().startswith("- ") for L in lines):
            items = [f"<li>{L.strip()[2:].replace(chr(10), ' ')}</li>" for L in lines]
            out.append(f"<ul>\n" + "\n".join(items) + "\n</ul>")
        else:
            for line in lines:
                t = line.strip().replace(chr(10), " ")
                cls = " class=\"dim placeholder\"" if t in ("TBD", "No reviews completed yet.") else ""
                out.append(f"<p{cls}>{t}</p>")
    return "\n".join(out)


def parse_about_file(filepath):
    """Parse an about .txt file: first line = title, rest = body. Returns (title, body_html)."""
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines:
        return ("Untitled", "")
    title = lines[0].strip()
    body = "\n".join(lines[1:]).strip()
    body_html = about_body_to_html(body) if body else ""
    return (title, body_html)


def load_about_pages():
    """Load all about/*.txt. Returns list of (stem, title, body_html) sorted by stem."""
    pages = []
    for f in sorted(ABOUT_DIR.glob("*.txt")):
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

CSS_CONTENT = """*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--ink:#1a1814;--paper:#f5f0e8;--warm:#c8a96e;--dim:#8a7f6e;--accent:#2d4a3e;--line:#e0d8c8}
html{font-size:18px}
body{background:var(--paper);color:var(--ink);font-family:'Cormorant Garamond',Georgia,serif;min-height:100vh}
body::before{content:'';position:fixed;inset:0;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");pointer-events:none;z-index:1000;opacity:.6}
nav{display:flex;justify-content:space-between;align-items:center;padding:1.4rem 3rem;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--paper);z-index:100}
.nav-logo{font-family:'DM Mono',monospace;font-size:.7rem;letter-spacing:.15em;text-transform:uppercase;color:var(--dim);text-decoration:none}
.nav-links{display:flex;gap:2rem;list-style:none;align-items:center}
.nav-links a{font-family:'DM Mono',monospace;font-size:.65rem;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);text-decoration:none;transition:color .2s}
.nav-links a:hover{color:var(--ink)}
.nav-item-dropdown{position:relative}
.nav-item-dropdown summary{font-family:'DM Mono',monospace;font-size:.65rem;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);cursor:pointer;list-style:none}
.nav-item-dropdown summary::-webkit-details-marker{display:none}
.nav-item-dropdown summary:hover{color:var(--ink)}
.nav-dropdown{position:absolute;top:100%;left:0;margin:0;padding:.5rem 0;min-width:10rem;background:var(--paper);border:1px solid var(--line);box-shadow:0 .25rem 1rem rgba(0,0,0,.08);list-style:none}
.nav-dropdown a{display:block;padding:.4rem 1rem;white-space:nowrap}
.wrap{max-width:860px;margin:0 auto;padding:0 3rem}
h1{font-size:clamp(2rem,5vw,3.5rem);font-weight:300;line-height:1.1}
h1 em,h2 em{font-style:italic;color:var(--accent)}
h2{font-size:1.6rem;font-weight:300;margin-bottom:1rem}
.mono{font-family:'DM Mono',monospace}
.small{font-size:.65rem;letter-spacing:.15em;text-transform:uppercase}
.warm{color:var(--warm)}
.dim{color:var(--dim)}
.prose{font-size:1.1rem;line-height:1.85;color:#2a2520}
.prose p+p{margin-top:1.3rem}
.prose hr{border:none;border-top:1px solid var(--line);margin:2rem 0}
.prose em{font-style:italic}
.tag{font-family:'DM Mono',monospace;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;color:var(--dim);border:1px solid var(--line);padding:.18rem .45rem;border-radius:2px;text-decoration:none;display:inline-block}
.tag:hover{color:var(--accent);border-color:var(--accent)}
footer{padding:3rem;border-top:1px solid var(--line);margin-top:4rem;display:flex;justify-content:space-between}
footer span{font-family:'DM Mono',monospace;font-size:.58rem;letter-spacing:.12em;text-transform:uppercase;color:var(--dim)}
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
.fade{animation:fadeUp .5s ease both}
@media(max-width:640px){nav,.wrap,footer{padding-left:1.5rem;padding-right:1.5rem}.layer-tabs-inner{padding-left:1.5rem;padding-right:1.5rem}}
/* Repo table */
table{width:100%;border-collapse:collapse;font-size:.95rem;margin-top:1.5rem}
th{font-family:'DM Mono',monospace;font-size:.58rem;letter-spacing:.15em;text-transform:uppercase;color:var(--warm);padding:.8rem 1rem .8rem 0;border-bottom:1px solid var(--line);text-align:left}
td{padding:.9rem 1rem .9rem 0;border-bottom:1px solid var(--line);vertical-align:top}
td a{color:var(--ink);text-decoration:none}
td a:hover{color:var(--accent)}
.status-draft1{color:var(--accent);font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:.08em}
.status-prelim{color:var(--warm);font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:.08em}
.status-partial{color:var(--warm);font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:.08em}
.status-empty{color:var(--line);font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:.08em}
/* Nugget page */
.nugget-header{padding:4rem 0 2.5rem}
.meta-row{display:flex;gap:1.2rem;align-items:center;margin-bottom:1.5rem;flex-wrap:wrap}
.premise{font-size:1.15rem;font-style:italic;color:var(--dim);border-left:2px solid var(--warm);padding-left:1.2rem;margin-top:1.2rem;line-height:1.5}
.nugget-tags{margin-top:1.5rem}
.layer-tabs{position:sticky;top:57px;background:var(--paper);border-bottom:1px solid var(--line);z-index:90}
.layer-tabs-inner{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;padding:.4rem 3rem;gap:0;row-gap:0}
.layer-tabs-prev,.layer-tabs-next{flex-shrink:0;padding:.5rem .25rem;font-size:1rem;line-height:1}
.layer-tabs-prev a,.layer-tabs-next a{color:var(--dim);text-decoration:none}
.layer-tabs-prev a:hover,.layer-tabs-next a:hover{color:var(--accent)}
.layer-tabs-center{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;flex:1;min-width:0}
.layer-tab{font-family:'DM Mono',monospace;font-size:.65rem;letter-spacing:.08em;text-transform:uppercase;color:var(--dim);padding:.5rem .4rem;text-decoration:none;border-bottom:2px solid transparent;background:none;transition:all .2s;white-space:nowrap;display:inline-block}
.layer-tab:hover{color:var(--accent)}
.layer-tab-disabled{color:var(--line);cursor:default;pointer-events:none}
.layer-tab-disabled:hover{color:var(--line)}
.layer-section{scroll-margin-top:5rem;padding:3rem 0;border-top:1px solid var(--line)}
.layer-section:first-of-type{border-top:none}
.layer-heading{font-size:1.1rem;font-weight:400;font-family:'DM Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--warm);margin-bottom:1.5rem}
.map-matrix{display:inline-block;border-collapse:collapse;margin:2rem 0;font-size:.7rem}
.map-matrix th,.map-matrix td{border:1px solid var(--line);width:1.4rem;height:1.4rem;text-align:center;vertical-align:middle}
.map-matrix th{font-family:'DM Mono',monospace;color:var(--dim);font-weight:400}
.map-matrix .map-cell-linked{background:var(--accent);color:var(--paper)}
.map-matrix .map-cell-empty{background:var(--paper)}
.map-matrix .map-row-label,.map-matrix .map-col-label{font-family:'DM Mono',monospace;color:var(--dim)}
.cta{background:var(--accent);color:var(--paper);padding:1.4rem 1.8rem;margin-top:2rem;font-size:1rem;line-height:1.7;font-style:italic}
.related-section{margin-top:3rem;padding-top:2rem;border-top:1px solid var(--line)}
.related-label{margin-bottom:.5rem}
.related-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1rem;margin-top:1rem}
.related-card{border:1px solid var(--line);padding:1rem;text-decoration:none;color:inherit;transition:border-color .2s}
.related-card:hover{border-color:var(--accent)}
.related-num{font-family:'DM Mono',monospace;font-size:.58rem;color:var(--warm);margin-bottom:.3rem}
.related-title{font-size:1rem;font-weight:300}
.placeholder{font-style:italic}
.script-direction{font-family:'DM Mono',monospace;font-size:.62rem;letter-spacing:.15em;text-transform:uppercase;color:var(--ink);margin-top:1.5rem}
.script-punch{font-size:1.3rem;font-style:italic;color:var(--accent);margin-top:1.5rem}
.script-line{margin-bottom:.6rem}
/* Group page */
.group-block{margin-bottom:3rem}
.group-label{font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:.2em;text-transform:uppercase;color:var(--warm);padding:2rem 0 .8rem;border-top:1px solid var(--line)}
.seed-row{display:grid;grid-template-columns:56px 1fr 80px;gap:1.2rem;padding:1.2rem 0;border-bottom:1px solid var(--line);text-decoration:none;color:inherit;align-items:baseline}
.seed-row:hover .seed-title{color:var(--accent)}
.seed-row.stub{opacity:.4;pointer-events:none}
.seed-num{font-family:'DM Mono',monospace;font-size:.6rem;color:var(--warm)}
.seed-title{font-size:1.2rem;font-weight:300;margin-bottom:.2rem}
.seed-sub{font-size:.85rem;color:var(--dim);line-height:1.4}
.seed-status-col{font-family:'DM Mono',monospace;font-size:.55rem;letter-spacing:.08em;text-transform:uppercase;color:var(--dim);text-align:right}
/* About pages */
.page-body{padding:4rem 0}
.page-body p{font-size:1.1rem;line-height:1.8;color:#2a2520;margin-bottom:1.2rem}
.page-body h2{font-size:1.4rem;font-weight:400;color:var(--accent);margin:2.5rem 0 .8rem}
.page-body ul{margin-left:1.5rem;margin-bottom:1.2rem}
.page-body li{font-size:1.05rem;line-height:1.7;color:#2a2520;margin-bottom:.4rem}
/* Index */
.hero{padding:5rem 0 2rem}
.hero-notice{display:block;margin-bottom:1.5rem}
.hero-tagline{font-size:1.2rem;color:var(--dim);margin-top:1rem;max-width:520px;line-height:1.6}
.hero-stats{display:flex;gap:3rem;margin-top:3rem;padding-top:2rem;border-top:1px solid var(--line)}
.hero-stat-label{font-size:.85rem;color:var(--dim);margin-top:.2rem}
.seed-list-section{padding:2rem 0 4rem}
.section-head{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid var(--line);padding-bottom:.8rem;margin-bottom:.5rem}
.link-mono-small{font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);text-decoration:none}
.link-mono-small:hover{color:var(--ink)}
.seed-list-more-wrap{padding:1.5rem 0}
.link-mono-accent{font-family:'DM Mono',monospace;font-size:.62rem;letter-spacing:.15em;text-transform:uppercase;color:var(--accent);text-decoration:none}
.link-mono-accent:hover{color:var(--ink)}
.about-block{padding:2.5rem 0;border-top:1px solid var(--line)}
.about-block-label{margin-bottom:1.2rem}
.about-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:.8rem}
.about-card{color:var(--ink);text-decoration:none;padding:.8rem;border:1px solid var(--line);font-size:.95rem;display:block}
.about-card:hover{color:var(--accent);border-color:var(--accent)}
/* Repository */
.repo-intro{margin-top:.8rem;font-size:.95rem}
.repo-cell-mono{font-size:.8rem}
.repo-subtitle{font-size:.82rem;color:var(--dim)}
.repo-date{font-size:.75rem}
.repo-tags{font-size:.8rem;color:var(--dim)}
/* Tags page */
.index-section-head{font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:.2em;text-transform:uppercase;color:var(--warm);padding:2rem 0 .8rem;border-top:1px solid var(--line);margin-top:2rem}
.tags-table th:first-child,.tags-table td:first-child{min-width:8rem}
.tags-table .repo-tag-label{font-size:1rem;font-weight:400;font-family:'DM Mono',monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--warm);scroll-margin-top:5rem;vertical-align:top;padding-top:.9rem}
.tags-table .repo-tag-label-empty{vertical-align:top}
/* Groups */
.groups-intro{color:var(--dim);margin-top:.5rem;font-size:.95rem}
.group-label-sub{font-style:italic;font-weight:300}
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
    return """
<footer>
  <span>Seed Nuggets — archive in progress</span>
  <span>Not yet for public consumption</span>
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

def text_to_html(text):
    """Convert plain text with --- dividers and paragraphs to HTML."""
    if text.strip() == "TBD":
        return '<p class="dim placeholder">This layer is not yet written.</p>'
    parts = text.split("\n---\n")
    html_parts = []
    for part in parts:
        paras = [p.strip() for p in part.strip().split("\n\n") if p.strip()]
        html = "\n".join(f"<p>{p.replace(chr(10), ' ')}</p>" for p in paras)
        html_parts.append(html)
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
    ("provenance", "Reference"),
    ("script", "Script"),
    ("images", "Images"),
    ("related", "Related"),
]


def build_nugget(n, all_nuggets, about_pages):
    num = n.get("number", "?")
    title = n.get("title", "Untitled")
    subtitle = n.get("subtitle", "")
    status = n.get("status", "empty")
    date = n.get("date", "")
    tags = n.get("tags", [])
    related_nums = n.get("related", [])
    layers = n.get("layers", {})
    shortname = n.get("shortname", "")

    tag_html = " ".join(f'<a href="tags.html#{tag_slug(t)}" class="tag">{t}</a>' for t in tags)

    rel_nuggets = [nugget_by_number(all_nuggets, r) for r in related_nums]
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
        if layer_id == "related":
            return bool(rel_nuggets)
        raw = (layers.get(layer_id) or "TBD").strip()
        return raw != "TBD"

    def layer_body(layer_id):
        if layer_id == "related":
            return related_cards_html
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
        if layer_id == "related":
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

    status_order = ("draft1", "partial", "prelim", "empty")
    all_statuses = set(n.get("status", "empty") for n in nuggets)
    sorted_statuses = sorted(all_statuses, key=lambda s: (status_order.index(s) if s in status_order else 99, s))

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
    <table class="tags-table">
      <thead>
        <tr>
          <th>Tag</th>
          <th>Title / Subtitle</th>
        </tr>
      </thead>
      <tbody>{tag_rows}
      </tbody>
    </table>
    <h2 class="index-section-head">Statuses</h2>
    <table class="tags-table">
      <thead>
        <tr>
          <th>Tag</th>
          <th>Title / Subtitle</th>
        </tr>
      </thead>
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
    <h1>Seed<br><em>Nuggets</em></h1>
    <p class="hero-tagline">{c.get("tagline", "")}</p>

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
        (SITE_DIR / "site.css").write_text(CSS_CONTENT, encoding="utf-8")
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

if __name__ == "__main__":
    main()
