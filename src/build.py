#!/usr/bin/env python3
"""
build.py — Seed Nuggets site generator
Reads from content/ and config/; writes to d/ (and index.html at root).
Website root = project root: / serves index.html, /d/ has built HTML, /content/ has source.
Generates: nugget pages, list.html, glossary/bibliography/tags/map from content .md (via @ directives),
index.html, about pages, resources (with map), site.css.

Usage:
    python src/build.py   (from repo root; quiet: nugget count, @notes, file count)
    python src/build.py -v   # verbose: also print every built file
    python src/build.py --nugget 001   # rebuild single nugget
"""

import csv
import hashlib
import html as _html
import json
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
    nugget_tag,
    section_is_tbd,
)
from md_pages import process_md_to_html, expand_includes, expand_links
from site_paths import content_path_to_output_name, parse_list_menu

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
    """Set of .md paths referenced via @link(locator, text) from main MD pages (transitive). Paths resolved relative to the file containing the link."""
    refs = set()
    to_scan = list(_get_md_page_paths())
    while to_scan:
        path = to_scan.pop(0)
        if not path.exists():
            continue
        text = expand_includes(path.read_text(encoding="utf-8"), path.parent) if path.suffix == ".md" else ""
        base_dir = path.parent.resolve()
        for m in re.finditer(r"@link\s*\(\s*([^,)]+)\s*,", text):
            loc = m.group(1).strip()
            if not re.match(r"^\d+$", loc) and ".md" in loc:
                p = (base_dir / loc).resolve()
                try:
                    p.relative_to(CONTENT_DIR.resolve())
                except ValueError:
                    continue
                if p not in refs and p.exists():
                    refs.add(p)
                    to_scan.append(p)
    return refs

def get_build_input_files():
    files = set()
    for p in NUGGETS_DIR.glob("*.txt"):
        files.add(p)
    for name in ["settings.txt", "status.txt", "site.css", "logo.svg"]:
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
    for p in (_ROOT / "src").glob("*.py"):
        files.add(p)
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


def _content_path_for_token(token):
    """Resolve content path token to (href, path). path is the .md file to build, or None."""
    token = token.strip()
    md_file = CONTENT_DIR / f"{token}.md"
    if md_file.exists():
        return (f"{token}.html", md_file)
    dir_path = CONTENT_DIR / token
    if dir_path.is_dir() and (dir_path / "page.md").exists():
        return (f"{token}.html", dir_path / "page.md")
    return (None, None)


def get_list_menu_items(index_copy=None):
    """Resolve list_menu from config to [(label, href, path)]. Target is content path only. Returns [] when list_menu unset. path is source .md for building."""
    copy = index_copy or load_index_copy()
    raw = copy.get("list_menu", "").strip()
    if not raw:
        return []
    entries = parse_list_menu(raw)
    out = []
    for label, target in entries:
        href, path = _content_path_for_token(target)
        if href and path:
            out.append((label, href, path))
        else:
            _warn(f"list_menu target {target!r} not found: no content/{target}.md nor content/{target}/page.md")
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


def build_nugget_index_json(nuggets):
    """Return JSON object: number -> slug for goto. Includes both display num and zero-padded."""
    index = {}
    for n in nuggets:
        num = n.get("number")
        if not num:
            continue
        slug = nugget_tag(n)
        index[num] = slug
        if num.isdigit():
            index[display_number(num)] = slug
    return json.dumps(index)


def build_search_index_json(nuggets, nugget_raw_by_slug=None):
    """Return JSON array of {num, title, slug, content}. If nugget_raw_by_slug given, content = raw file text (same as 4u-ai); else title + subtitle + layers."""
    out = []
    for n in sorted(nuggets, key=lambda x: (x.get("number", "").zfill(3), x.get("number", ""))):
        num = n.get("number", "")
        title = n.get("title", "") or ""
        slug = nugget_tag(n)
        if nugget_raw_by_slug is not None:
            content = (nugget_raw_by_slug.get(slug) or "").replace("\n", " ")
        else:
            parts = [title, n.get("subtitle", "")]
            layers = n.get("layers") or {}
            for key in ("surface", "depth", "brief", "provenance", "script", "images"):
                if key in layers and layers[key]:
                    parts.append(layers[key])
            content = " ".join(parts).replace("\n", " ")
        out.append({"num": display_number(num), "title": title, "slug": slug, "content": content})
    return json.dumps(out)


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _head_links(css_href="site.css", icon_href="d/logo.svg"):
    return f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{css_href}">
<link rel="icon" type="image/svg+xml" href="{icon_href}">
"""

def _more_page_label(key):
    return "Index" if key == "tags" else key.replace("-", " ").title()


def nav(from_d=False, from_nuggets=False, layer_tabs_html=None):
    """Top nav: logo left; then Search, Go+input; then menu items from config (About, Lists, More)."""
    prefix, index_href, logo_src = "", "index.html", "logo.svg"
    list_menu_items = get_list_menu_items(load_index_copy())
    nav_item_parts = []
    for href, label, _, _ in _nav_items():
        if href == "list.html":
            if list_menu_items:
                dropdown_items = [f'<li><a href="{prefix}{item_href}">{_html.escape(item_label)}</a></li>' for item_label, item_href, _ in list_menu_items]
                nav_item_parts.append(
                    '<li class="nav-link-item nav-item-dropdown nav-lists-dropdown">'
                    f'<a href="{prefix}list.html">Lists</a>'
                    '<button type="button" class="nav-dropdown-trigger" aria-expanded="false" aria-haspopup="true" aria-label="Lists menu"></button>'
                    '<ul class="nav-dropdown">'
                    + "".join(dropdown_items) +
                    '</ul></li>'
                )
            else:
                nav_item_parts.append(f'<li class="nav-link-item"><a href="{prefix}list.html">{_html.escape(label)}</a></li>')
        else:
            nav_item_parts.append(f'<li class="nav-link-item"><a href="{prefix}{href}">{_html.escape(label)}</a></li>')
    search_li = '<li><button type="button" class="nav-search-btn" aria-label="Search nuggets" onclick="seedNavOpenSearch();return false">Search</button></li>'
    goto_li = (
        '<li class="nav-goto-wrap">'
        '<label for="nav-goto-num" class="sr-only">Goto nugget</label>'
        '<button type="button" class="nav-goto-btn" aria-label="Go to nugget" onclick="seedNavGo(this);return false">Go</button>'
        '<input type="text" id="nav-goto-num" class="nav-goto-input" inputmode="numeric" pattern="[0-9]*" maxlength="4" onkeydown="if(event.key===\'Enter\'){event.preventDefault();seedNavGoFromInput(this);}">'
        '</li>'
    )
    center_links = search_li + goto_li
    end_links = "".join(nav_item_parts)

    hamburger_nav_parts = []
    for href, label, _, _ in _nav_items():
        if href == "list.html":
            if list_menu_items:
                for item_label, item_href, _ in list_menu_items:
                    hamburger_nav_parts.append(f'<li><a href="{prefix}{item_href}">{_html.escape(item_label)}</a></li>')
            else:
                hamburger_nav_parts.append(f'<li><a href="{prefix}list.html">{_html.escape(label)}</a></li>')
        else:
            hamburger_nav_parts.append(f'<li><a href="{prefix}{href}">{_html.escape(label)}</a></li>')
    hamburger_list = "".join(hamburger_nav_parts)

    row = f"""  <div class="nav-row">
  <div class="nav-brand"><a href="{index_href}" class="nav-logo"><img src="{logo_src}" alt="" class="nav-logo-icon"><span class="nav-logo-text"><span class="nav-logo-word1">Seed</span><span class="nav-logo-word2">Nuggets</span></span></a></div>
  <div class="nav-center"><ul class="nav-links nav-links-center">
    {center_links}
  </ul></div>
  <div class="nav-end"><ul class="nav-links nav-links-end">
    {end_links}
  </ul><button type="button" class="nav-hamburger-btn" aria-label="Menu" aria-expanded="false" aria-controls="nav-hamburger-panel" onclick="seedNavToggleMenu();return false">&#9776;</button></div>
</div>
  <div class="nav-hamburger-panel" id="nav-hamburger-panel" role="menu" aria-hidden="true">
    <div class="nav-hamburger-overlay" onclick="seedNavToggleMenu()"></div>
    <div class="nav-hamburger-inner">
      <ul class="nav-hamburger-list">
{hamburger_list}
      </ul>
    </div>
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

NAV_LISTS_DROPDOWN_SCRIPT = """
<script>
(function(){
  function init(){
    var wrap = document.querySelector(".nav-lists-dropdown");
    if (!wrap) return;
    var trigger = wrap.querySelector(".nav-dropdown-trigger");
    var link = wrap.querySelector('a[href="list.html"]');
    var dropdown = wrap.querySelector(".nav-dropdown");
    function open(){ wrap.classList.add("nav-dropdown-open"); if (trigger) trigger.setAttribute("aria-expanded", "true"); }
    function close(){ wrap.classList.remove("nav-dropdown-open"); if (trigger) trigger.setAttribute("aria-expanded", "false"); }
    function toggle(){ wrap.classList.contains("nav-dropdown-open") ? close() : open(); }
    if (trigger) trigger.addEventListener("click", function(e){ e.preventDefault(); e.stopPropagation(); toggle(); });
    document.addEventListener("click", function(e){ if (wrap && !wrap.contains(e.target)) close(); });
    var longPressTimer;
    if (link) {
      link.addEventListener("touchstart", function(){ longPressTimer = setTimeout(function(){ open(); longPressTimer = null; }, 500); }, { passive: true });
      link.addEventListener("touchend", function(){ if (longPressTimer) clearTimeout(longPressTimer); longPressTimer = null; }, { passive: true });
      link.addEventListener("touchcancel", function(){ if (longPressTimer) clearTimeout(longPressTimer); longPressTimer = null; }, { passive: true });
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
</script>
"""

SEARCH_DIALOG_HTML = """
<div id="search-dialog" class="search-dialog" role="dialog" aria-modal="true" aria-label="Search nuggets" hidden>
  <div class="search-dialog-overlay" onclick="seedNavCloseSearch()"></div>
  <div class="search-dialog-inner">
    <div class="search-dialog-header">
      <input type="search" id="search-dialog-input" class="search-dialog-input" placeholder="Search by name or content…" autocomplete="off" aria-label="Search" oninput="seedNavRunSearch(this.value)">
      <button type="button" class="search-dialog-close" aria-label="Close" onclick="seedNavCloseSearch()">&times;</button>
    </div>
    <div id="search-dialog-count" class="search-dialog-count"></div>
    <div id="search-dialog-results" class="search-dialog-results"></div>
  </div>
</div>
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
    return logo_block + "\n" + NAV_SCROLL_SCRIPT + "\n" + NAV_LISTS_DROPDOWN_SCRIPT + "\n" + SEARCH_DIALOG_HTML

def _nav_seed_script_content():
    """Return the inner JS of the nav/search/goto script (no script tags)."""
    return r"""
window.seedNavToggleMenu=function(){
  var n=document.querySelector("nav");
  var b=document.querySelector(".nav-hamburger-btn");
  var p=document.getElementById("nav-hamburger-panel");
  if(!n||!b)return;
  var open=n.classList.contains("nav-hamburger-open");
  n.classList.toggle("nav-hamburger-open",!open);
  b.setAttribute("aria-expanded",!open?"true":"false");
  if(p)p.style.display=open?"none":"flex";
};
window.seedNavGo=function(btn){var w=btn&&btn.closest?btn.closest(".nav-goto-wrap"):null;var i=w?w.querySelector(".nav-goto-input"):null;window.seedNavGoFromInput(i);};
window.seedNavGoFromInput=function(input){if(!input)return;var v=(input.value||"").trim();if(!v)return;var p=window._seedNavIndexPromise||(window._seedNavIndexPromise=fetch("nugget-index.json").then(function(r){return r.json();}));p.then(function(idx){var s=idx[v]||idx[v.replace(/^0+/,"")]||(v.length<=3?idx[v.padStart(3,"0")]:null);if(s)window.location.href=s+".html";});};
window.seedNavOpenSearch=function(){var n=document.querySelector("nav");if(n&&n.classList.contains("nav-hamburger-open"))window.seedNavToggleMenu();var d=document.getElementById("search-dialog");var i=document.getElementById("search-dialog-input");if(d)d.removeAttribute("hidden");if(i){i.value="";i.focus();}window.seedNavRunSearch("");};
window.seedNavCloseSearch=function(){var d=document.getElementById("search-dialog");if(d)d.setAttribute("hidden","");};
window._seedNavSearchIndex=null;
window._seedNavSnippet=function(content,q){if(!content||!q)return"";var c=content.toLowerCase();var i=c.indexOf(q);if(i<0)return"";var len=100;var start=Math.max(0,i-len);var end=Math.min(content.length,i+q.length+len);var s=content.substring(start,end).replace(/\s+/g," ").trim();if(start>0)s="\u2026 "+s;if(end<content.length)s=s+" \u2026";return s;};
window.seedNavRunSearch=function(q){
  q=(q||"").toLowerCase().trim();
  var el=document.getElementById("search-dialog-results");
  var countEl=document.getElementById("search-dialog-count");
  if(!el)return;
  if(!window._seedNavSearchIndex){fetch("search-index.json").then(function(r){return r.json();}).then(function(data){window._seedNavSearchIndex=data;window.seedNavRunSearch(q);});return;}
  if(!q){el.innerHTML="";if(countEl)countEl.textContent="";return;}
  var nm=[],cm=[];
  for(var j=0;j<window._seedNavSearchIndex.length;j++){var it=window._seedNavSearchIndex[j];if((it.title||"").toLowerCase().indexOf(q)>=0)nm.push(it);else if((it.content||"").toLowerCase().indexOf(q)>=0)cm.push(it);}
  var slugs={};
  nm.forEach(function(it){slugs[it.slug]=1;});cm.forEach(function(it){slugs[it.slug]=1;});
  var n=Object.keys(slugs).length;
  if(countEl)countEl.textContent=n===1?"1 found":n+" found";
  var h="";
  if(nm.length){h+='<div class="search-section"><div class="search-section-title">Name</div><ul class="search-result-list">';nm.forEach(function(it){var d=document.createElement("div");d.textContent=it.num+". "+it.title;h+='<li><a href="'+it.slug+'.html">'+d.innerHTML+'</a></li>';});h+="</ul></div>";}
  if(cm.length){h+='<div class="search-section"><div class="search-section-title">Content</div><ul class="search-result-list">';cm.forEach(function(it){var titleDiv=document.createElement("div");titleDiv.textContent=it.num+". "+it.title;var snip=window._seedNavSnippet(it.content,q);var snipDiv=document.createElement("div");snipDiv.textContent=snip;h+='<li><a href="'+it.slug+'.html">'+titleDiv.innerHTML+'<br><span class="search-result-snippet">'+snipDiv.innerHTML+'</span></a></li>';});h+="</ul></div>";}
  if(!h&&q)h='<p class="search-no-results">No nuggets match.</p>';
  el.innerHTML=h;
};
document.addEventListener("keydown",function(e){if(e.key==="Escape"){var n=document.querySelector("nav");if(n&&n.classList.contains("nav-hamburger-open"))window.seedNavToggleMenu();else window.seedNavCloseSearch();}});
document.addEventListener("DOMContentLoaded",function(){var p=document.getElementById("nav-hamburger-panel");if(p){p.style.display="none";var list=p.querySelector(".nav-hamburger-list");if(list)list.querySelectorAll("a").forEach(function(a){a.addEventListener("click",function(){if(document.querySelector("nav").classList.contains("nav-hamburger-open"))window.seedNavToggleMenu();});});}});
"""

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
<script src="seed-nav.js"></script>
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

def _expand_exercise_directives(text, all_nuggets):
    """Replace each @exercise(...) (balanced parens) with a placeholder; return (segments, cta_htmls). Each directive turns its argument into HTML (expand @nugget, text_to_html, wrap in div.cta) without knowing which layer it's in."""
    segments = []
    cta_htmls = []
    i = 0
    while i < len(text):
        match = re.search(r"@exercise\s*\(", text[i:])
        if not match:
            segments.append(text[i:])
            break
        start = i + match.start()
        segments.append(text[i:start])
        paren_start = i + match.end() - 1
        depth = 1
        j = paren_start + 1
        while j < len(text) and depth:
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
            j += 1
        if depth != 0:
            segments.append(text[start:j])
            i = j
            continue
        inner = text[paren_start + 1 : j - 1].strip()
        expanded = expand_nugget_directives(inner, all_nuggets) if inner else ""
        cta_html = text_to_html(expanded) if expanded else ""
        placeholder = f"{{{{EXERCISE_{len(cta_htmls)}}}}}"
        segments.append(placeholder)
        cta_htmls.append(f'<div class="cta">{cta_html}</div>' if cta_html else "")
        i = j
    return segments, cta_htmls


def expand_layer_directives(raw, all_nuggets):
    """Expand @nugget and @exercise in layer text. Returns (segments, cta_htmls). Same expansion for every layer; caller chooses how to render each text segment (prose vs script)."""
    expanded = expand_nugget_directives(raw, all_nuggets) if raw else raw
    return _expand_exercise_directives(expanded, all_nuggets)


def _assemble_layer_html(segments, cta_htmls, segment_renderer):
    """Turn (segments, cta_htmls) into final HTML. segment_renderer(seg) is used for each text segment; placeholders are replaced by the corresponding cta_htmls entry."""
    parts = []
    for seg in segments:
        if seg.startswith("{{EXERCISE_") and seg.endswith("}}"):
            try:
                i = int(seg[11:-2])
                if i < len(cta_htmls) and cta_htmls[i]:
                    parts.append(cta_htmls[i])
            except ValueError:
                parts.append(segment_renderer(seg))
        else:
            parts.append(segment_renderer(seg))
    return "".join(parts)


def _layer_prose_to_html(raw, all_nuggets, link_context=None, link_base_dir=None):
    """Prose layers: expand directives, then render each segment with text_to_html."""
    if section_is_tbd(raw):
        return '<p class="dim placeholder">This layer is not yet written.</p>'
    segments, cta_htmls = expand_layer_directives(raw, all_nuggets)

    def render_seg(seg):
        if section_is_tbd(seg):
            return ""
        if link_context is not None and link_base_dir is not None:
            seg = expand_links(seg, link_context, link_base_dir)
        return text_to_html(seg)

    return _assemble_layer_html(segments, cta_htmls, render_seg)


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
LAYER_ORDER_PROTO = [
    ("brief", "Brief"),
    ("references", "References"),
]

PROTO_NOTICE_HTML = '''<div class="proto-notice"><p class="dim">This nugget is a crazy idea so far. It might be fleshed out, merged with another nugget, or even removed. Caveat lector.</p></div>'''

ROUGH_NOTICE_HTML = '''<div class="rough-notice"><p class="dim">This nugget is a rough draft, far from polished. Caveat lector.</p></div>'''

def build_nugget(n, all_nuggets, link_errors=None):
    num = n.get("number", "?")
    title = n.get("title", "Untitled")
    subtitle = n.get("subtitle", "")
    status = n.get("status", "empty")
    date = n.get("date", "")
    tags = n.get("tags", [])
    related_nums = n.get("related", [])
    layers = n.get("layers", {})

    link_context = {"nuggets": all_nuggets, "content_dir": CONTENT_DIR, "warn": _warn, "link_errors": link_errors}
    link_base_dir = NUGGETS_DIR

    tags_href = "tags.html"
    tag_html = " ".join(f'<a href="{tags_href}#{tag_slug(t)}" class="tag">{t}</a>' for t in tags)

    rel_nuggets = [nugget_by_number(all_nuggets, r) for r in related_nums]
    for r in related_nums:
        if not nugget_by_number(all_nuggets, r):
            _warn(f"Warning: nugget {n.get('number')} ({n.get('filename')}): related {r} does not match any nugget.")
    rel_nuggets = [r for r in rel_nuggets if r]
    related_cards_html = ""
    if rel_nuggets:
        cards = ""
        for r in rel_nuggets[:5]:
            rfile = nugget_tag(r) + ".html"
            rnum = r.get("number", "")
            rtitle = r.get("title", "")
            rstatus = r.get("status", "empty")
            card_class = "related-card related-card-prelim" if rstatus in ("empty", "prelim", "proto", "rough") else "related-card"
            cards += f"""
      <a href="{rfile}" class="{card_class}">
        <div class="related-title">{display_number(rnum)}. {rtitle}</div>
      </a>"""
        related_cards_html = f'<div class="related-grid">{cards}\n      </div>'

    surface_html = _layer_prose_to_html(layers.get("surface", "TBD"), all_nuggets, link_context, link_base_dir)
    is_proto = status == "proto"
    is_rough = status == "rough"
    layer_order = LAYER_ORDER_PROTO if is_proto else LAYER_ORDER

    def layer_has_content(layer_id):
        if layer_id == "references":
            prov_raw = layers.get("provenance", "TBD")
            prov_expanded = expand_nugget_directives(prov_raw, all_nuggets) if prov_raw else prov_raw
            return not section_is_tbd(prov_expanded) or bool(n.get("refs"))
        return not section_is_tbd(layers.get(layer_id))

    def layer_body(layer_id):
        if layer_id == "brief":
            brief_html = _layer_prose_to_html(layers.get("brief", "TBD"), all_nuggets, link_context, link_base_dir)
            if is_proto:
                return PROTO_NOTICE_HTML + "\n    " + brief_html
            return brief_html
        if layer_id == "references":
            prov_raw = layers.get("provenance", "TBD")
            prov_html = "" if section_is_tbd(prov_raw) else _layer_prose_to_html(prov_raw, all_nuggets, link_context, link_base_dir)
            parts = []
            if prov_html:
                parts.append(f'<div class="prose">{prov_html}</div>')
            refs_list = n.get("refs", [])
            if refs_list:
                parts.append('<h3 class="layer-heading ref-heading">Further reading</h3>')
                parts.append('<div class="prose ref-list">')
                for ref_item in refs_list:
                    ref_text = ref_item[1] if isinstance(ref_item, tuple) else ref_item
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
            if is_rough:
                return ROUGH_NOTICE_HTML + "\n    " + surface_html
            return surface_html
        raw = layers.get(layer_id, "TBD")
        if layer_id == "script":
            segments, cta_htmls = expand_layer_directives(raw, all_nuggets)
            def script_render(seg):
                expanded = expand_links(seg, link_context, link_base_dir) if (link_context and link_base_dir) else seg
                return script_to_html(expanded)
            return _assemble_layer_html(segments, cta_htmls, script_render)
        return _layer_prose_to_html(raw, all_nuggets, link_context, link_base_dir)

    tabs_parts = []
    for layer_id, label in layer_order:
        if layer_has_content(layer_id):
            tabs_parts.append(f'<a href="#{layer_id}" class="layer-tab">{label}</a>')
        else:
            tabs_parts.append(f'<span class="layer-tab layer-tab-disabled">{label}</span>')

    sections_parts = []
    refs_section_shown = layer_has_content("references")
    for layer_id, label in layer_order:
        if not layer_has_content(layer_id):
            continue
        body = layer_body(layer_id)
        if layer_id == "references":
            has_provenance_prose = not section_is_tbd(layers.get("provenance", "TBD"))
            if has_provenance_prose:
                section_content = f'<h2 class="layer-heading">{label}</h2>\n    {body}'
            else:
                section_content = body
        elif layer_id == "brief" and is_proto:
            section_content = f'<div class="prose">{body}</div>'
        else:
            section_content = f'<h2 class="layer-heading">{label}</h2>\n    <div class="prose">{body}</div>'
        if layer_id == "surface" and rel_nuggets and not refs_section_shown:
            section_content += f'\n    <div class="related-section"><h3 class="layer-heading related-label">Related seeds</h3>\n      {related_cards_html}\n    </div>'
        if layer_id == "brief" and is_proto and rel_nuggets and not refs_section_shown:
            section_content += f'\n    <div class="related-section"><h3 class="layer-heading related-label">Related seeds</h3>\n      {related_cards_html}\n    </div>'
        sections_parts.append(f'  <section id="{layer_id}" class="layer-section">\n    {section_content}\n  </section>')

    tabs_html = "\n      ".join(tabs_parts)
    sections_html = "\n\n".join(sections_parts)

    sorted_nuggets = sorted(all_nuggets, key=lambda x: x.get("number", ""))
    idx = next((i for i, x in enumerate(sorted_nuggets) if nugget_tag(x) == nugget_tag(n)), -1)
    prev_n = sorted_nuggets[idx - 1] if idx > 0 else None
    next_n = sorted_nuggets[idx + 1] if 0 <= idx < len(sorted_nuggets) - 1 else None

    prev_html = f'<a href="{nugget_tag(prev_n)}.html">&lt;&lt;</a>' if prev_n else ''
    next_html = f'<a href="{nugget_tag(next_n)}.html">&gt;&gt;</a>' if next_n else ''

    if is_proto:
        layer_tabs_html = f"""  <div class="layer-tabs">
    <div class="layer-tabs-inner">
      <span class="layer-tabs-prev">{prev_html}</span>
      <div class="layer-tabs-center"></div>
      <span class="layer-tabs-next">{next_html}</span>
    </div>
  </div>"""
    else:
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


def build_tags_body(nuggets, status_order):
    """Index-by-tag and by-status HTML. For @index directive."""
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
            fname = nugget_tag(n) + ".html"
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
    return f"""<div class="index-by-tag">
    {tag_blocks}
    </div>
    <h2 class="index-section-head">Statuses</h2>
    <div class="index-by-tag">
    {status_blocks}
    </div>"""


def build_tags_page(nuggets, status_order, explainer_terms=None):
    body = build_tags_body(nuggets, status_order)
    html = head("Index")
    html += nav(from_d=True)
    html += f'<div class="wrap"><div class="page-body fade"><h1>Index</h1>{body}</div></div>'
    html += foot()
    html += close()
    return html


def _md_context(**overrides):
    """Default context for process_md_to_html: warn, build_time, content_dir, site_dir. Merge with overrides."""
    copy = overrides.get("copy", load_index_copy())
    return {"warn": _warn, "build_time": BUILD_TIME, "content_dir": CONTENT_DIR, "site_dir": (copy.get("site_dir") or "").strip(), **overrides}


def _md_context_with_special(nuggets, status_order, explainer_terms=None, **overrides):
    """Context for process_md_to_html including @glossary, @bibliography, @index, @map placeholder HTML."""
    ctx = _md_context(nuggets=nuggets, status_order=status_order, **overrides)
    ctx["glossary_html"] = build_glossary_body(nuggets, explainer_terms)
    ctx["bibliography_html"] = build_bibliography_body(nuggets)
    ctx["index_html"] = build_tags_body(nuggets, status_order)
    ctx["map_html"] = build_map_body(nuggets, status_order)
    return ctx


def build_index(nuggets, index_copy, status_order, collected_md_refs=None, link_errors=None):
    context = _md_context(nuggets=nuggets, status_order=status_order, copy=index_copy, page="home", link_errors=link_errors)
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


MIN_TAG_COUNT_FOR_MAP = 3


def build_map_body(nuggets, status_order):
    """Map graph filters + SVG + filter script. For @map directive."""
    tag_counts = {}
    for n in nuggets:
        for t in n.get("tags", []):
            tag_counts[t] = tag_counts.get(t, 0) + 1
    tags_with_min = sorted([t for t, c in tag_counts.items() if c >= MIN_TAG_COUNT_FOR_MAP])
    category_opts = '<option value="">All</option>' + "".join(
        '<option value="{}">{}</option>'.format(_html.escape(t), _html.escape(t)) for t in tags_with_min
    )
    status_opts = '<option value="">All</option>' + "".join(
        '<option value="{}">{}</option>'.format(_html.escape(s), _html.escape(s)) for s in (status_order or [])
    )
    filters_html = (
        '<div class="map-graph-filters">'
        '<label for="map-filter-tag">Category</label>'
        '<select id="map-filter-tag" aria-label="Filter by tag">' + category_opts + '</select>'
        ' <label for="map-filter-status">Status</label>'
        '<select id="map-filter-status" aria-label="Filter by status">' + status_opts + '</select>'
        "</div>"
    )
    key_html = (
        '<div class="map-graph-key" aria-hidden="true">'
        '<span class="map-graph-key-item"><span class="map-graph-key-dot map-graph-key-from"></span> from</span>'
        ' <span class="map-graph-key-item"><span class="map-graph-key-dot map-graph-key-to"></span> to</span>'
        '</div>'
    )
    script = """
<script>
(function(){
  var tagSel = document.getElementById('map-filter-tag');
  var statusSel = document.getElementById('map-filter-status');
  function apply(){
    var tagVal = tagSel && tagSel.value;
    var statusVal = statusSel && statusSel.value;
    document.querySelectorAll('.map-graph-node-wrap').forEach(function(el){
      var tags = (el.getAttribute('data-tags') || '').split(',').map(function(s){ return s.trim(); });
      var status = el.getAttribute('data-status') || '';
      var tagMatch = !tagVal || tags.indexOf(tagVal) >= 0;
      var statusMatch = !statusVal || status === statusVal;
      el.classList.toggle('unselected', !(tagMatch && statusMatch));
    });
    var selected = new Set();
    document.querySelectorAll('.map-graph-node-wrap:not(.unselected)').forEach(function(el){
      selected.add(el.getAttribute('data-nugget'));
    });
    document.querySelectorAll('.map-graph-edge-wrap').forEach(function(el){
      var fromId = el.getAttribute('data-from');
      var toId = el.getAttribute('data-to');
      var connected = selected.has(fromId) && selected.has(toId);
      el.classList.toggle('unselected', !connected);
    });
  }
  if (tagSel) tagSel.addEventListener('change', apply);
  if (statusSel) statusSel.addEventListener('change', apply);
  apply();
  var wrap = document.querySelector('.map-graph-wrap');
  if (wrap && wrap.scrollWidth > wrap.clientWidth) wrap.scrollLeft = (wrap.scrollWidth - wrap.clientWidth) / 2;
  if (wrap && wrap.scrollHeight > wrap.clientHeight) wrap.scrollTop = (wrap.scrollHeight - wrap.clientHeight) / 2;

  var svgEl = document.querySelector('.map-graph-svg');
  if (svgEl && typeof svgEl.createSVGPoint === 'function') {
    var pt = svgEl.createSVGPoint();
    var dragState = { active: false, wrap: null, g: null, startX: 0, startY: 0, startDx: 0, startDy: 0, didMove: false };
    function clientToSvg(clientX, clientY) {
      pt.x = clientX;
      pt.y = clientY;
      return pt.matrixTransform(svgEl.getScreenCTM().inverse());
    }
    function rectExitT(dx, dy, hw, hh) {
      var candidates = [];
      if (dx > 0) candidates.push(hw / dx);
      else if (dx < 0) candidates.push(-hw / dx);
      if (dy > 0) candidates.push(hh / dy);
      else if (dy < 0) candidates.push(-hh / dy);
      return candidates.length ? Math.min.apply(null, candidates) : 1;
    }
    function getNodePosition(nid) {
      var wraps = document.querySelectorAll('.map-graph-node-wrap');
      var w = null;
      for (var i = 0; i < wraps.length; i++) {
        if (wraps[i].getAttribute('data-nugget') === nid) { w = wraps[i]; break; }
      }
      if (!w) return { x: 0, y: 0 };
      var g = w.querySelector('.map-graph-node-transform');
      if (!g) return { x: 0, y: 0 };
      var x = parseFloat(g.getAttribute('data-x')) || 0;
      var y = parseFloat(g.getAttribute('data-y')) || 0;
      var dx = parseFloat(g.getAttribute('data-dx')) || 0;
      var dy = parseFloat(g.getAttribute('data-dy')) || 0;
      return { x: x + dx, y: y + dy };
    }
    function updateEdgesForNode(nodeId) {
      var rect = document.querySelector('.map-graph-node');
      if (!rect) return;
      var hw = parseFloat(rect.getAttribute('width')) / 2;
      var hh = parseFloat(rect.getAttribute('height')) / 2;
      var edgeWraps = document.querySelectorAll('.map-graph-edge-wrap');
      var seen = {};
      edgeWraps.forEach(function(w) {
        var fromId = w.getAttribute('data-from');
        var toId = w.getAttribute('data-to');
        if (fromId !== nodeId && toId !== nodeId) return;
        var key = fromId + ',' + toId;
        if (seen[key]) return;
        seen[key] = true;
        var fromPos = getNodePosition(fromId);
        var toPos = getNodePosition(toId);
        var dx = toPos.x - fromPos.x;
        var dy = toPos.y - fromPos.y;
        var dist = Math.sqrt(dx * dx + dy * dy) || 1;
        var tFrom = Math.min(rectExitT(dx, dy, hw, hh), 1);
        var tTo = Math.min(rectExitT(-dx, -dy, hw, hh), 1);
        var x1 = fromPos.x + tFrom * dx;
        var y1 = fromPos.y + tFrom * dy;
        var x2 = toPos.x - tTo * dx;
        var y2 = toPos.y - tTo * dy;
        document.querySelectorAll('.map-graph-edge-wrap[data-from="' + fromId + '"][data-to="' + toId + '"]').forEach(function(grp) {
          var line = grp.querySelector('.map-graph-edge');
          if (line) {
            line.setAttribute('x1', x1);
            line.setAttribute('y1', y1);
            line.setAttribute('x2', x2);
            line.setAttribute('y2', y2);
          }
          var exitC = grp.querySelector('.map-graph-bullet-exit');
          if (exitC) { exitC.setAttribute('cx', x1); exitC.setAttribute('cy', y1); }
          var enterC = grp.querySelector('.map-graph-bullet-enter');
          if (enterC) { enterC.setAttribute('cx', x2); enterC.setAttribute('cy', y2); }
        });
      });
    }
    function startDrag(wrap, clientX, clientY) {
      var g = wrap.querySelector('.map-graph-node-transform');
      if (!g) return;
      var origX = parseFloat(g.getAttribute('data-x')) || 0;
      var origY = parseFloat(g.getAttribute('data-y')) || 0;
      var dx = parseFloat(g.getAttribute('data-dx')) || 0;
      var dy = parseFloat(g.getAttribute('data-dy')) || 0;
      var p = clientToSvg(clientX, clientY);
      dragState.didMove = false;
      dragState.active = true;
      dragState.wrap = wrap;
      dragState.g = g;
      dragState.origX = origX;
      dragState.origY = origY;
      dragState.startX = p.x;
      dragState.startY = p.y;
      dragState.startDx = dx;
      dragState.startDy = dy;
    }
    function moveDrag(clientX, clientY) {
      if (!dragState.active || !dragState.g) return;
      var p = clientToSvg(clientX, clientY);
      var dx = dragState.startDx + (p.x - dragState.startX);
      var dy = dragState.startDy + (p.y - dragState.startY);
      dragState.g.setAttribute('transform', 'translate(' + (dragState.origX + dx) + ',' + (dragState.origY + dy) + ')');
      dragState.g.setAttribute('data-dx', dx);
      dragState.g.setAttribute('data-dy', dy);
      dragState.didMove = true;
      var nid = dragState.wrap && dragState.wrap.getAttribute('data-nugget');
      if (nid) updateEdgesForNode(nid);
    }
    function endDrag() {
      dragState.active = false;
      dragState.wrap = null;
      dragState.g = null;
    }
    document.querySelectorAll('.map-graph-node-wrap').forEach(function(wrap) {
      wrap.addEventListener('mousedown', function(e) {
        if (e.button !== 0) return;
        startDrag(wrap, e.clientX, e.clientY);
      });
      wrap.addEventListener('click', function(e) {
        if (dragState.didMove) {
          e.preventDefault();
          e.stopPropagation();
          dragState.didMove = false;
        }
      });
    });
    document.addEventListener('mousemove', function(e) {
      if (dragState.active) {
        e.preventDefault();
        moveDrag(e.clientX, e.clientY);
      }
    });
    document.addEventListener('mouseup', function() { endDrag(); });
    document.addEventListener('mouseleave', function() { endDrag(); });

    var wrapEl = document.querySelector('.map-graph-wrap');
    if (wrapEl) {
      wrapEl.addEventListener('touchstart', function(e) {
        if (e.target.closest('.map-graph-node-wrap')) {
          var wrap = e.target.closest('.map-graph-node-wrap');
          startDrag(wrap, e.touches[0].clientX, e.touches[0].clientY);
        }
      }, { passive: true });
      wrapEl.addEventListener('touchmove', function(e) {
        if (dragState.active && e.touches.length) {
          e.preventDefault();
          moveDrag(e.touches[0].clientX, e.touches[0].clientY);
        }
      }, { passive: false });
      wrapEl.addEventListener('touchend', endDrag);
      wrapEl.addEventListener('touchcancel', endDrag);
    }
  }
})();
</script>"""
    svg = build_graph_svg(nuggets, show_title=False, link_nuggets=True, node_radius=40)
    return filters_html + '\n' + key_html + '\n<div class="map-graph-wrap"><div class="map-graph-inner">' + svg + '</div></div>' + script


def build_map_graph_page(nuggets, status_order):
    return build_static_page("Map", build_map_body(nuggets, status_order), wrap_class="wrap--full")


def build_md_file_page(md_path, nuggets=None, collected_md_refs=None, status_order=None, index_copy=None, explainer_terms=None, link_errors=None, wrap_class=""):
    nuggets = nuggets or []
    status_order = status_order or []
    context = _md_context_with_special(nuggets, status_order, explainer_terms, copy=index_copy, page=md_path.stem, link_errors=link_errors)
    body_html = process_md_to_html(md_path, context, collected_md_refs=collected_md_refs)
    title = _first_h1(md_path) or md_path.stem.replace("-", " ").title()
    html = head(title)
    html += nav(from_d=True)
    wrap_attr = f' class="wrap {wrap_class}"' if wrap_class else ' class="wrap"'
    html += f'<div{wrap_attr}><div class="page-body fade">{body_html}</div></div>'
    html += foot()
    html += close()
    return html


def build_md_dir_page(dir_path, nuggets=None, collected_md_refs=None, status_order=None, explainer_terms=None, link_errors=None):
    page_md = dir_path / "page.md"
    nuggets = nuggets or []
    status_order = status_order or []
    context = _md_context_with_special(nuggets, status_order, explainer_terms, page=dir_path.name, link_errors=link_errors)
    body_html = process_md_to_html(page_md, context, collected_md_refs=collected_md_refs)
    title = _first_h1(page_md) or dir_path.name.replace("-", " ").title()
    html = head(title)
    html += nav(from_d=True)
    html += f'<div class="wrap"><div class="page-body fade">{body_html}</div></div>'
    html += foot()
    html += close()
    return html


def build_internal_page(nuggets=None, collected_md_refs=None, link_errors=None):
    context = _md_context(nuggets=nuggets or [], link_errors=link_errors)
    body_html = process_md_to_html(INTERNAL_DIR / "page.md", context, collected_md_refs=collected_md_refs)
    html = head("Internal")
    html += nav(from_d=True)
    html += f'<div class="wrap"><div class="page-body fade">{body_html}</div></div>'
    html += foot()
    html += close()
    return html


def build_bibliography_body(nuggets):
    """Bibliography table HTML from #ref in #provenance. For @bibliography directive."""
    by_keyword = {}
    for n in nuggets:
        tag = nugget_tag(n)
        fname = tag + ".html"
        for ref_item in n.get("refs", []):
            if isinstance(ref_item, tuple):
                keyword, ref_text = ref_item[0], (ref_item[1] or "").strip()
            else:
                ref_text = (ref_item or "").strip()
                keyword = ref_text.split(None, 1)[0].lower() if ref_text else ""
            if not ref_text:
                continue
            if keyword not in by_keyword:
                by_keyword[keyword] = {}
            if ref_text not in by_keyword[keyword]:
                by_keyword[keyword][ref_text] = []
            by_keyword[keyword][ref_text].append((tag, fname))
    parts = []
    for keyword in sorted(by_keyword.keys(), key=str.lower):
        keyword_esc = _html.escape(keyword)
        count = len(by_keyword[keyword])
        heading = f"{keyword_esc} ({count})" if count > 1 else keyword_esc
        parts.append(f'<hr class="index-tag-rule"><div id="{keyword_esc}" class="index-tag-name">{heading}</div>')
        entries = sorted(by_keyword[keyword].items(), key=lambda x: x[0].lower())
        for ref_text, nugget_list in entries:
            sort_key = lambda x: (int(x[0].split("-")[0]) if x[0].split("-")[0].isdigit() else 999, x[0])
            sorted_nugs = sorted(nugget_list, key=sort_key)
            nugget_links = " ".join(f'<a href="{fname}" class="bib-tag">{_html.escape(disp)}</a>' for disp, fname in sorted_nugs)
            ref_esc = _html.escape(ref_text)
            parts.append(
                f'<div class="bib-entry"><span class="bib-text">{ref_esc}</span> {nugget_links}</div>'
            )
    return "\n".join(parts) if parts else "<p class=\"dim\">No references yet. Add <code>#ref</code> lines (keyword + citation text) inside <code>#provenance</code> in any nugget.</p>"


def build_bibliography_page(nuggets):
    body = build_bibliography_body(nuggets)
    html = head("Bibliography")
    html += nav(from_d=True)
    html += f'<div class="wrap"><div class="page-body fade"><h1>Bibliography</h1><p class="dim repo-intro">References from all nuggets, grouped by keyword.</p>{body}</div></div>'
    html += foot()
    html += close()
    return html


def build_glossary_body(nuggets, explainer_terms=None):
    """Glossary entries HTML from #term in nuggets. For @glossary directive."""
    explainer_by_slug = {e["slug"]: e for e in (explainer_terms or [])}
    by_entry = {}
    for n in nuggets:
        num = n.get("number", "")
        fname = nugget_tag(n) + ".html"
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
            entry = explainer_by_slug[slug]
            if entry["links"] or [n for n in entry.get("notes", []) if n != "(No explainers found yet.)"]:
                def_blocks.append(
                    '<div class="gloss-def-block">' + _explainer_block_html(entry) + '</div>'
                )
        entry_id = f' id="{_html.escape(slug)}"'
        parts.append(
            f'<div class="gloss-entry"{entry_id}>'
            f'{term_line}'
            f'<div class="gloss-defs">' + "\n".join(def_blocks) + '</div>'
            f'</div>'
        )
    return "\n".join(parts) if parts else "<p class=\"dim\">No terms yet. Add <code>#term Term : Definition</code> lines in any nugget.</p>"


def build_glossary_page(nuggets, explainer_terms=None):
    body = build_glossary_body(nuggets, explainer_terms)
    html = head("Glossary")
    html += nav(from_d=True)
    html += f'<div class="wrap"><div class="page-body fade"><h1>Glossary</h1><p class="dim repo-intro">Key terms from all nuggets.</p>{body}</div></div>'
    html += foot()
    html += close()
    return html


def _collect_4u_ai_content(nuggets):
    """Return (internal_docs_str, nugget_raw_by_slug). Internal docs in one string; nugget raw file text keyed by slug."""
    internal_parts = []
    for p in sorted(INTERNAL_DIR.glob("*.md")):
        internal_parts.append(f"=== content/internal/{p.name} ===\n\n{p.read_text(encoding='utf-8')}")
    internal_str = "\n\n".join(internal_parts)
    nugget_raw_by_slug = {}
    for n in sorted(nuggets, key=lambda x: (x.get("number", "").zfill(3), x.get("number", ""))):
        raw = (NUGGETS_DIR / f"{n['filename']}.txt").read_text(encoding="utf-8")
        nugget_raw_by_slug[nugget_tag(n)] = raw
    return internal_str, nugget_raw_by_slug


def build_4u_ai_txt(internal_str, nuggets, nugget_raw_by_slug):
    """Write d/4u-ai.txt from shared internal string and per-nugget raw content."""
    parts = [internal_str]
    for n in sorted(nuggets, key=lambda x: (x.get("number", "").zfill(3), x.get("number", ""))):
        slug = nugget_tag(n)
        raw = nugget_raw_by_slug.get(slug, "")
        parts.append(f"=== content/nuggets/{n['filename']}.txt ===\n\n{raw}")
    (SITE_DIR / "4u-ai.txt").write_text("\n\n".join(parts), encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global BUILD_TIME, SITE_DIR
    index_copy = load_index_copy()
    site_dir = (index_copy.get("site_dir") or "").strip()
    if not site_dir:
        raise SystemExit("config/settings.txt must set site_dir")
    SITE_DIR = _ROOT / site_dir
    filter_num = None
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
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
    for n in nuggets:
        for note in n.get("notes", []):
            rel = NUGGETS_DIR / (n.get("filename", "?") + ".txt")
            try:
                rel = rel.resolve().relative_to(_ROOT)
            except ValueError:
                pass
            print(f"{rel}: @note {note}")
    built_count = 0
    seen_num = {}
    duplicate_nums = []
    for n in nuggets:
        num = n.get("number")
        if num:
            if num in seen_num:
                duplicate_nums.append((num, seen_num[num], n.get("filename")))
            else:
                seen_num[num] = n.get("filename")
    if duplicate_nums:
        lines = [f"Duplicate nugget number {num}: {a}.txt and {b}.txt" for num, a, b in duplicate_nums]
        raise SystemExit("Build failed:\n  " + "\n  ".join(lines))

    for md_path in _get_md_page_paths():
        if not md_path.exists():
            raise SystemExit(f"Required file missing: {md_path}")
    status_order = _require_status_order()

    for n in nuggets:
        s = n.get("status", "empty")
        if s not in status_order:
            _warn(f"Error: nugget {n.get('filename', '?')}: status {s!r} not in config/status.txt")

    link_errors = []
    for n in nuggets:
        if filter_num and n.get("number") != filter_num:
            continue
        fname = nugget_tag(n) + ".html"
        out = SITE_DIR / fname
        out.write_text(build_nugget(n, nuggets, link_errors), encoding="utf-8")
        built_count += 1
        if verbose:
            print(f"  Built {fname}")

    internal_str, nugget_raw_by_slug = _collect_4u_ai_content(nuggets)
    (SITE_DIR / "nugget-index.json").write_text(build_nugget_index_json(nuggets), encoding="utf-8")
    (SITE_DIR / "search-index.json").write_text(build_search_index_json(nuggets, nugget_raw_by_slug), encoding="utf-8")
    (SITE_DIR / "seed-nav.js").write_text(_nav_seed_script_content(), encoding="utf-8")
    if not filter_num:
        built_count += 3
        if verbose:
            print("  Built nugget-index.json, search-index.json, seed-nav.js")

    if not filter_num:
        shutil.copy(CONFIG_DIR / "site.css", SITE_DIR / "site.css")
        built_count += 1
        if verbose:
            print("  Built site.css")
        if (CONFIG_DIR / "logo.svg").exists():
            shutil.copy(CONFIG_DIR / "logo.svg", SITE_DIR / "logo.svg")
            built_count += 1
            if verbose:
                print("  Built logo.svg")

        explainer_terms = load_explainers_csv(EXPLAINERS_CSV) if EXPLAINERS_CSV.exists() else []

        collected_md_refs = set()
        nav_items = get_nav_items(index_copy)
        nav_built_paths = set()
        for href, label, kind, path in nav_items:
            if kind == "file":
                nav_built_paths.add(path)
                wrap_class = "wrap--full" if href == "map.html" else ""
                (SITE_DIR / href).write_text(
                    build_md_file_page(path, nuggets, collected_md_refs, status_order, index_copy, explainer_terms, link_errors, wrap_class=wrap_class),
                    encoding="utf-8",
                )
                built_count += 1
                if verbose:
                    print(f"  Built {href}")
            elif kind == "dir":
                nav_built_paths.add(path / "page.md")
                (SITE_DIR / href).write_text(build_md_dir_page(path, nuggets, collected_md_refs, status_order, explainer_terms, link_errors), encoding="utf-8")
                built_count += 1
                if verbose:
                    print(f"  Built {href}")

        for _label, list_href, list_path in get_list_menu_items(index_copy):
            if list_path and list_path not in nav_built_paths:
                wrap_class = "wrap--full" if list_href == "map.html" else ""
                (SITE_DIR / list_href).write_text(
                    build_md_file_page(list_path, nuggets, collected_md_refs, status_order, index_copy, explainer_terms, link_errors, wrap_class=wrap_class),
                    encoding="utf-8",
                )
                built_count += 1
                if verbose:
                    print(f"  Built {list_href}")

        (SITE_DIR / "internal.html").write_text(build_internal_page(nuggets, collected_md_refs, link_errors), encoding="utf-8")
        built_count += 1
        if verbose:
            print("  Built internal.html")

        built_md_refs = set()
        to_build = list(collected_md_refs)
        while to_build:
            md_path = to_build.pop(0)
            if md_path in built_md_refs:
                continue
            built_md_refs.add(md_path)
            body_html = process_md_to_html(md_path, _md_context_with_special(nuggets, status_order, explainer_terms, link_errors=link_errors), collected_md_refs)
            title = md_path.stem.replace("-", " ").title()
            out_name = content_path_to_output_name(md_path, CONTENT_DIR)
            if out_name:
                (SITE_DIR / out_name).write_text(build_static_page(title, body_html), encoding="utf-8")
                built_count += 1
                if verbose:
                    print(f"  Built {out_name}")
            for p in collected_md_refs - built_md_refs:
                if p not in to_build:
                    to_build.append(p)

        for stale in ["index.html", "favicon.svg"]:
            p = _ROOT / stale
            if p.exists():
                p.unlink()
        index_html = build_index(nuggets, index_copy, status_order, collected_md_refs, link_errors)
        (SITE_DIR / "index.html").write_text(index_html, encoding="utf-8")
        built_count += 1
        if verbose:
            print("  Built index.html")
        if (CONFIG_DIR / "logo.svg").exists():
            shutil.copy(CONFIG_DIR / "logo.svg", SITE_DIR / "favicon.svg")
            built_count += 1
            if verbose:
                print("  Built favicon.svg")

        (SITE_DIR / "map.svg").write_text(build_graph_svg(nuggets, show_title=False, link_nuggets=True, node_radius=40), encoding="utf-8")
        built_count += 1
        if verbose:
            print("  Built map.svg")

        build_4u_ai_txt(internal_str, nuggets, nugget_raw_by_slug)
        built_count += 1
        if verbose:
            print("  Built 4u-ai.txt")

        BUILD_STATE_FILE.write_text(
            current_hash + "\n" + BUILD_TIME.isoformat(),
            encoding="utf-8",
        )

    if not verbose:
        print(f"Built {built_count} files")
    print(f"\nDone. Site written to {SITE_DIR.relative_to(_ROOT)}/ (web root)")
    if nothing_changed:
        print("Nothing changed; timestamp unchanged.")
    if link_errors:
        for msg in link_errors:
            print(msg, file=sys.stderr)
        sys.exit(1)
    if _warn_count:
        sys.exit(1)

if __name__ == "__main__":
    main()
