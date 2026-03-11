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

# ── HTML helpers ──────────────────────────────────────────────────────────────

CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--ink:#1a1814;--paper:#f5f0e8;--warm:#c8a96e;--dim:#8a7f6e;--accent:#2d4a3e;--line:#e0d8c8}
html{font-size:18px}
body{background:var(--paper);color:var(--ink);font-family:'Cormorant Garamond',Georgia,serif;min-height:100vh}
body::before{content:'';position:fixed;inset:0;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");pointer-events:none;z-index:1000;opacity:.6}
nav{display:flex;justify-content:space-between;align-items:center;padding:1.4rem 3rem;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--paper);z-index:100}
.nav-logo{font-family:'DM Mono',monospace;font-size:.7rem;letter-spacing:.15em;text-transform:uppercase;color:var(--dim);text-decoration:none}
.nav-links{display:flex;gap:2rem;list-style:none}
.nav-links a{font-family:'DM Mono',monospace;font-size:.65rem;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);text-decoration:none;transition:color .2s}
.nav-links a:hover{color:var(--ink)}
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
.tag{font-family:'DM Mono',monospace;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;color:var(--dim);border:1px solid var(--line);padding:.18rem .45rem;border-radius:2px}
footer{padding:3rem;border-top:1px solid var(--line);margin-top:4rem;display:flex;justify-content:space-between}
footer span{font-family:'DM Mono',monospace;font-size:.58rem;letter-spacing:.12em;text-transform:uppercase;color:var(--dim)}
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
.fade{animation:fadeUp .5s ease both}
@media(max-width:640px){nav,.wrap,footer{padding-left:1.5rem;padding-right:1.5rem}}
/* Repo table */
table{width:100%;border-collapse:collapse;font-size:.95rem;margin-top:1.5rem}
th{font-family:'DM Mono',monospace;font-size:.58rem;letter-spacing:.15em;text-transform:uppercase;color:var(--warm);padding:.8rem 1rem .8rem 0;border-bottom:1px solid var(--line);text-align:left}
td{padding:.9rem 1rem .9rem 0;border-bottom:1px solid var(--line);vertical-align:top}
td a{color:var(--ink);text-decoration:none}
td a:hover{color:var(--accent)}
.status-draft1{color:var(--accent);font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:.08em}
.status-partial{color:var(--warm);font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:.08em}
.status-empty{color:var(--line);font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:.08em}
/* Nugget page */
.nugget-header{padding:4rem 0 2.5rem}
.meta-row{display:flex;gap:1.2rem;align-items:center;margin-bottom:1.5rem;flex-wrap:wrap}
.premise{font-size:1.15rem;font-style:italic;color:var(--dim);border-left:2px solid var(--warm);padding-left:1.2rem;margin-top:1.2rem;line-height:1.5}
.layer-tabs{position:sticky;top:57px;background:var(--paper);border-bottom:1px solid var(--line);z-index:90;overflow-x:auto}
.layer-tabs-inner{display:flex;padding:0 3rem;gap:0}
.tab{font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:.15em;text-transform:uppercase;color:var(--dim);padding:.9rem 1.1rem;cursor:pointer;border:none;border-bottom:2px solid transparent;background:none;transition:all .2s;white-space:nowrap}
.tab:hover{color:var(--ink)}
.tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.panel{display:none;padding:3rem 0}
.panel.active{display:block;animation:fadeUp .3s ease both}
.cta{background:var(--accent);color:var(--paper);padding:1.4rem 1.8rem;margin-top:2rem;font-size:1rem;line-height:1.7;font-style:italic}
.related-section{margin-top:3rem;padding-top:2rem;border-top:1px solid var(--line)}
.related-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1rem;margin-top:1rem}
.related-card{border:1px solid var(--line);padding:1rem;text-decoration:none;color:inherit;transition:border-color .2s}
.related-card:hover{border-color:var(--accent)}
.related-num{font-family:'DM Mono',monospace;font-size:.58rem;color:var(--warm);margin-bottom:.3rem}
.related-title{font-size:1rem;font-weight:300}
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
</style>
"""

def nav(active=""):
    return f"""
<nav>
  <a href="index.html" class="nav-logo">Seed Nuggets</a>
  <ul class="nav-links">
    <li><a href="repository.html">Repository</a></li>
    <li><a href="groups.html">By Group</a></li>
    <li><a href="goals.html">About</a></li>
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
{CSS}
{extra}
</head>
<body>"""

def close():
    return "\n</body>\n</html>"

def text_to_html(text):
    """Convert plain text with --- dividers and paragraphs to HTML."""
    if text.strip() == "TBD":
        return '<p class="dim" style="font-style:italic">This layer is not yet written.</p>'
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
        return '<p class="dim" style="font-style:italic">Script not yet written.</p>'
    lines = text.strip().splitlines()
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Lines in ALL CAPS or starting with CUT/OPEN/etc. are directions
        if line.isupper() or re.match(r'^(CUT|OPEN|FADE|PAUSE|SLOW|CLOSE|END)', line):
            out.append(f'<p style="font-family:\'DM Mono\',monospace;font-size:.62rem;letter-spacing:.15em;text-transform:uppercase;color:var(--warm);margin-top:1.5rem">{line}</p>')
        elif line.startswith("What does") or line.startswith("What if"):
            out.append(f'<p style="font-size:1.3rem;font-style:italic;color:var(--accent);margin-top:1.5rem">{line}</p>')
        else:
            out.append(f'<p style="margin-bottom:.6rem">{line}</p>')
    return "\n".join(out)

# ── Page builders ─────────────────────────────────────────────────────────────

def build_nugget(n, all_nuggets):
    num = n.get("number", "?")
    title = n.get("title", "Untitled")
    subtitle = n.get("subtitle", "")
    status = n.get("status", "empty")
    date = n.get("date", "")
    tags = n.get("tags", [])
    related_nums = n.get("related", [])
    layers = n.get("layers", {})
    shortname = n.get("shortname", "")

    tag_html = " ".join(f'<span class="tag">{t}</span>' for t in tags)

    # Build related cards
    related_html = ""
    rel_nuggets = [nugget_by_number(all_nuggets, r) for r in related_nums]
    rel_nuggets = [r for r in rel_nuggets if r]
    if rel_nuggets:
        cards = ""
        for r in rel_nuggets[:5]:
            rfile = r.get("filename", "") + ".html"
            rnum = r.get("number", "")
            rtitle = r.get("title", "")
            cards += f"""
      <a href="{rfile}" class="related-card">
        <div class="related-num">{rnum}</div>
        <div class="related-title">{rtitle}</div>
      </a>"""
        related_html = f"""
    <div class="related-section">
      <div class="mono small warm" style="margin-bottom:.5rem">Related seeds</div>
      <div class="related-grid">{cards}
      </div>
    </div>"""

    surface_html = text_to_html(layers.get("surface", "TBD"))
    depth_html = text_to_html(layers.get("depth", "TBD"))
    prov_html = text_to_html(layers.get("provenance", "TBD"))
    script_html = script_to_html(layers.get("script", "TBD"))
    images_html = text_to_html(layers.get("images", "TBD"))

    # Add CTA to surface if it contains "Try this"
    surface_layer = layers.get("surface", "")
    if "Try this:" in surface_layer:
        parts = surface_layer.split("Try this:")
        before = text_to_html("Try this:".join(parts[:-1]))
        cta_text = "Try this: " + parts[-1].strip()
        surface_html = before + f'<div class="cta">{cta_text}</div>'

    html = head(f"{num} — {title}")
    html += nav()
    html += f"""
<div class="layer-tabs">
  <div class="layer-tabs-inner">
    <button class="tab active" onclick="show('surface',this)">Surface</button>
    <button class="tab" onclick="show('depth',this)">Depth</button>
    <button class="tab" onclick="show('provenance',this)">Provenance</button>
    <button class="tab" onclick="show('script',this)">Script</button>
    <button class="tab" onclick="show('images',this)">Images</button>
  </div>
</div>

<div class="wrap">
  <div class="nugget-header fade">
    <div class="meta-row">
      <span class="mono small warm">Seed {num}</span>
      {tag_html}
      <span class="mono small dim">{status} · {date}</span>
    </div>
    <h1>{title}</h1>
    <p class="premise">{subtitle}</p>
  </div>

  <div id="surface" class="panel active">
    <div class="prose">{surface_html}</div>
    {related_html}
  </div>

  <div id="depth" class="panel">
    <div class="prose">{depth_html}</div>
  </div>

  <div id="provenance" class="panel">
    <div class="prose">{prov_html}</div>
  </div>

  <div id="script" class="panel">
    <div class="prose">{script_html}</div>
  </div>

  <div id="images" class="panel">
    <div class="prose">{images_html}</div>
  </div>
</div>
"""
    html += foot()
    html += """
<script>
function show(id,btn){
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
}
</script>"""
    html += close()
    return html


def build_repository(nuggets):
    rows = ""
    for n in nuggets:
        num = n.get("number", "")
        shortname = n.get("shortname", "")
        title = n.get("title", "")
        subtitle = n.get("subtitle", "")
        status = n.get("status", "empty")
        date = n.get("date", "")
        tags = ", ".join(n.get("tags", []))
        fname = n.get("filename", "") + ".html"
        status_class = f"status-{status.replace(' ','')}"
        rows += f"""
    <tr>
      <td class="mono" style="font-size:.8rem">{num}</td>
      <td class="mono" style="font-size:.8rem">{shortname}</td>
      <td><a href="{fname}">{title}</a><br><span style="font-size:.82rem;color:var(--dim)">{subtitle}</span></td>
      <td class="{status_class}">{status}</td>
      <td class="mono" style="font-size:.75rem">{date}</td>
      <td style="font-size:.8rem;color:var(--dim)">{tags}</td>
    </tr>"""

    html = head("Repository")
    html += nav()
    html += f"""
<div class="wrap">
  <div class="page-body fade">
    <h1>Repository</h1>
    <p class="dim" style="margin-top:.8rem;font-size:.95rem">All seed nuggets. The canonical list. Generated from source files.</p>
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


GROUPS = [
    ("The Dissolving Map", "On frameworks and their limits", ["001", "006", "019"]),
    ("The Nature of Events", "Whitehead's radical inversion", ["002", "003", "004", "005"]),
    ("Fields and Physics", "Where science already arrived", ["007", "008", "009"]),
    ("Accumulation and Emergence", "What happens when events nest", ["010", "011", "012", "013"]),
    ("Societies of Events", "From cells to cities to AIs", ["014", "015", "016", "017"]),
    ("How Ideas Move", "The spread and the seed", ["018", "019"]),
]

def build_groups(nuggets):
    html = head("Seeds by Group")
    html += nav()
    html += '<div class="wrap"><div class="page-body fade">'
    html += "<h1>Seeds by group</h1>\n"
    html += '<p style="color:var(--dim);margin-top:.5rem;font-size:.95rem">Thematic clusters. Each seed may appear in more than one group.</p>\n'

    for group_title, group_sub, nums in GROUPS:
        html += f'<div class="group-block">'
        html += f'<div class="group-label">{group_title} — <span style="font-style:italic;font-weight:300">{group_sub}</span></div>'
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
        <div class="seed-num">{num}</div>
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


def build_index(nuggets):
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
      <div class="seed-num">{num}</div>
      <div>
        <div class="seed-title">{title}</div>
        <div class="seed-sub">{subtitle}</div>
      </div>
      <div class="seed-status-col">{status}</div>
    </a>"""

    html = head("Seed Nuggets")
    html += nav()
    html += f"""
<div class="wrap">
  <div style="padding:5rem 0 2rem" class="fade">
    <span class="mono small warm" style="display:block;margin-bottom:1.5rem">Working archive — not for public consumption</span>
    <h1>Seed<br><em>Nuggets</em></h1>
    <p style="font-size:1.2rem;color:var(--dim);margin-top:1rem;max-width:520px;line-height:1.6">Small ideas that change how you see. Start anywhere. Follow what intrigues you.</p>

    <div style="display:flex;gap:3rem;margin-top:3rem;padding-top:2rem;border-top:1px solid var(--line)">
      <div>
        <div class="mono small warm">{total}</div>
        <div style="font-size:.85rem;color:var(--dim);margin-top:.2rem">seeds defined</div>
      </div>
      <div>
        <div class="mono small warm">{ready_count}</div>
        <div style="font-size:.85rem;color:var(--dim);margin-top:.2rem">with content</div>
      </div>
    </div>
  </div>

  <div style="padding:2rem 0 4rem">
    <div style="display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid var(--line);padding-bottom:.8rem;margin-bottom:.5rem">
      <span class="mono small">All seeds</span>
      <a href="repository.html" style="font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);text-decoration:none">Full repository →</a>
    </div>
    {recent_html}
    <div style="padding:1.5rem 0">
      <a href="repository.html" style="font-family:'DM Mono',monospace;font-size:.62rem;letter-spacing:.15em;text-transform:uppercase;color:var(--accent);text-decoration:none">View all {total} seeds →</a>
    </div>
  </div>

  <div style="padding:2.5rem 0;border-top:1px solid var(--line)">
    <div class="mono small warm" style="margin-bottom:1.2rem">About this project</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:.8rem">
      <a href="goals.html" style="color:var(--ink);text-decoration:none;padding:.8rem;border:1px solid var(--line);font-size:.95rem">Goals</a>
      <a href="audiences.html" style="color:var(--ink);text-decoration:none;padding:.8rem;border:1px solid var(--line);font-size:.95rem">Audiences</a>
      <a href="structure.html" style="color:var(--ink);text-decoration:none;padding:.8rem;border:1px solid var(--line);font-size:.95rem">Structure</a>
      <a href="reviews.html" style="color:var(--ink);text-decoration:none;padding:.8rem;border:1px solid var(--line);font-size:.95rem">Reviews</a>
      <a href="authors.html" style="color:var(--ink);text-decoration:none;padding:.8rem;border:1px solid var(--line);font-size:.95rem">Authors</a>
      <a href="groups.html" style="color:var(--ink);text-decoration:none;padding:.8rem;border:1px solid var(--line);font-size:.95rem">By Group</a>
    </div>
  </div>
</div>"""
    html += foot()
    html += close()
    return html


def build_static_page(title, body_html):
    html = head(title)
    html += nav()
    html += f'<div class="wrap"><div class="page-body fade"><h1>{title}</h1>{body_html}</div></div>'
    html += foot()
    html += close()
    return html


# ── Static about pages ────────────────────────────────────────────────────────

GOALS_BODY = """
<p>Seed Nuggets is an attempt to shift how people see the world — not by argument, but by offering small, memorable ideas that reorient perception. Each seed is a lens. You pick it up, look through it, and something looks different.</p>

<h2>The core problem</h2>
<p>We are living through a moment of genuine confusion. Machines talk to us, reason with us, surprise us. Ancient assumptions about mind, matter, and experience are wobbling. And most of the available explanations feel either too technical or too mystical to be any use.</p>
<p>The dominant framework — that matter is fundamentally inert and experience is a late biological anomaly — may be the caloric of our moment. Not wrong in its observations, but wrong in its foundations. The anomalies are accumulating. The patches are getting elaborate.</p>

<h2>The approach</h2>
<p>This is not a course with a fixed sequence. It is a garden — enter anywhere, follow what intrigues you. Each seed stands alone. The connections form over time, building a network of mutually reinforcing ideas.</p>
<p>The bridge this project aims at is between science and spirituality — not by compromising either, but by showing that careful philosophy already connects them. Alfred North Whitehead did this work almost a century ago. This project is one attempt to make it legible.</p>

<h2>The ambition</h2>
<p>To slowly adjust the way a generation sees the world. Not through a movement or an institution, but through ideas that spread because they are true and because they help people make sense of things that otherwise make no sense.</p>
<p>The coming transformation around AI is the most immediate occasion. The stakes of getting the framework wrong are no longer abstract. This project is an investment in a more coherent and less frightened response to what is arriving.</p>
"""

AUDIENCES_BODY = """
<p>Seed Nuggets is designed to reach several distinct audiences. The same core ideas work for all of them, but the emphasis, tone, and most useful components differ.</p>

<h2>Young people (high school and college)</h2>
<p>The primary long-term audience. Young people are more open to new frameworks before old ones calcify into obvious reality. Tone: direct, not condescending, assumes genuine intelligence. Most useful components: Surface layer, Script/video, Images. The Surface layer should be tested with actual high schoolers to calibrate difficulty.</p>

<h2>Science-curious adults</h2>
<p>Readers of Michael Pollan, Annaka Harris, Philip Goff. Already interested in consciousness, AI, philosophy of mind. Willing to read longer pieces. Tone: intellectually serious, not academic. Most useful components: all five layers, especially Depth and Provenance.</p>

<h2>Spiritually oriented adults</h2>
<p>Including Sufi communities, liberal religious groups, contemplative practitioners. Already comfortable with non-materialist views of experience, but may be suspicious of science. Tone: warm, bridging, honoring existing wisdom while showing scientific convergence. Most useful components: Surface, Depth, the connection to mystical traditions.</p>

<h2>AI-concerned general public</h2>
<p>People anxious about AI who lack a framework for thinking about it. The alien/AI seeds are the entry point. Tone: reassuring through understanding, not dismissive of concern. Most useful components: Script/video, Surface, Images.</p>

<h2>Professionals and influencers</h2>
<p>Academics, writers, thinkers who could amplify. Including: David Chalmers, Tam Hunt, Jason Silva, Michael Garfield. Tone: peer-level, rigorous, connecting to their existing work. Most useful components: Depth, Provenance, the essay (separate long-form piece).</p>

<h2>Voice and style across audiences</h2>
<p>The overall voice is: warm, precise, slightly wonder-struck, never preachy. It does not tell people what to conclude. It offers lenses and asks them to look. It honors both scientific rigor and the reality of subjective experience without privileging either. It speaks to the person who is confused and curious, not the person who already knows.</p>
"""

STRUCTURE_BODY = """
<p>Every seed nugget has the same five layers. This consistency makes the archive navigable and the template maintainable. A reader who knows the structure can find what they need at whatever depth they want.</p>

<h2>Layer 1: Surface</h2>
<p>The accessible version. Written for a curious high schooler or a first-time encounter with the idea. Concrete language, relatable examples, no jargon. Goal: recognition — <em>oh, I've felt that, I just didn't have words for it.</em> Ends with a call to action: "try this" or "look for this." Length: 400–700 words. Test with real young readers.</p>

<h2>Layer 2: Depth</h2>
<p>The intellectual version. Connects to philosophy, science, history of ideas. Where Whitehead, Gödel, autopoiesis, and the rest live. Does not dumb down — assumes a reader who wants to go further. Can include technical detail. References other seeds by number. Length: 300–600 words.</p>

<h2>Layer 3: Provenance</h2>
<p>The roots. Glossary of key terms with definitions. Bibliography with full citations. Intellectual lineage — whose ideas these are, where they came from, what to read next. Intellectual honesty baked into the structure. Not a footnote — a genuine resource for the curious reader.</p>

<h2>Layer 4: Script</h2>
<p>The three-minute video version. Written as a shooting script with direction lines (in caps or italic) and spoken text. Designed for compression and emotional landing — the seed as a short piece of entertainment that arrives before it explains. Inspired by Jason Silva's style: rapid, evocative, philosophically serious. Ends with a single sharp question or image.</p>

<h2>Layer 5: Images</h2>
<p>The visual language. Describes (and eventually will contain) illustrations, animation concepts, shareable graphics. Each seed should have: a primary illustration, a shareable one-line graphic for social media, and a video thumbnail concept. The images should be able to stand alone and still transmit something of the seed's essence.</p>

<h2>Additional fields</h2>
<p>Each seed also carries: number (permanent identifier), short name (used in filename and URL), title, subtitle (one sentence), status (empty / partial / draft1 / final), date added, tags, and related seeds (up to five, by number). These are stored in the source .txt file and used to build the repository and navigation automatically.</p>
"""

REVIEWS_BODY = """
<p>This page tracks intended and completed reviews of the Seed Nuggets project. Reviews are of two kinds: reviews of individual seeds, and reviews of the overall project and its goals.</p>

<h2>Intended reviewers — friends and alpha participants</h2>
<ul>
<li>Alia Whitman — potential collaborator, strong AI interest, organizational skills</li>
<li>Rebecca Strong</li>
<li>Deva Temple</li>
<li>Wendy Tremayne</li>
<li>Ryan Lee</li>
<li>Jim Balter</li>
</ul>

<h2>Intended reviewers — professionals</h2>
<ul>
<li>Michael Pollan — author, consciousness and nature</li>
<li>Annaka Harris — author, Conscious</li>
<li>David Chalmers — philosopher, hard problem of consciousness</li>
<li>Jason Silva — filmmaker, ideas and wonder</li>
<li>Michael Garfield — writer, science and culture</li>
<li>Tam Hunt — UCSB, Mind World God (2017)</li>
</ul>

<h2>Intended reviewers — AI systems</h2>
<p>As a meta-experiment consistent with the project's themes, reviews by AI systems are also intended. Candidate systems: Claude (Anthropic), GPT-4 (OpenAI), Gemini (Google). The question of what an AI review means is itself a seed nugget.</p>

<h2>Review log</h2>
<p style="color:var(--dim);font-style:italic">No reviews completed yet.</p>
"""

AUTHORS_BODY = """
<p style="font-style:italic;color:var(--dim)">TBD</p>

<h2>Primary author</h2>
<p>TBD</p>

<h2>Collaborators</h2>
<p>TBD</p>

<h2>A note on AI collaboration</h2>
<p>These seeds were developed in conversation with Claude (Anthropic). The ideas, judgments, and editorial voice are human. The AI contributed drafting, reflection, and the occasional useful phrase. This collaboration is itself an instance of the themes explored in several seeds.</p>
"""

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

    # Build nugget pages
    for n in nuggets:
        if filter_num and n.get("number") != filter_num:
            continue
        fname = n.get("filename", "") + ".html"
        out = SITE_DIR / fname
        out.write_text(build_nugget(n, nuggets), encoding="utf-8")
        print(f"  Built {fname}")

    if not filter_num:
        # Build generated pages
        (SITE_DIR / "repository.html").write_text(build_repository(nuggets), encoding="utf-8")
        print("  Built repository.html")

        (SITE_DIR / "groups.html").write_text(build_groups(nuggets), encoding="utf-8")
        print("  Built groups.html")

        (SITE_DIR / "index.html").write_text(build_index(nuggets), encoding="utf-8")
        print("  Built index.html")

        # Build static pages
        static = {
            "goals.html": ("Goals", GOALS_BODY),
            "audiences.html": ("Audiences", AUDIENCES_BODY),
            "structure.html": ("Structure of a Seed Nugget", STRUCTURE_BODY),
            "reviews.html": ("Reviews", REVIEWS_BODY),
            "authors.html": ("Authors", AUTHORS_BODY),
        }
        for fname, (title, body) in static.items():
            (SITE_DIR / fname).write_text(build_static_page(title, body), encoding="utf-8")
            print(f"  Built {fname}")

    print(f"\nDone. Site written to ./{SITE_DIR}/")

if __name__ == "__main__":
    main()
