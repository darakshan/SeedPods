"""
Page chrome: head, nav, foot, close, nav config, and inline scripts.
Call set_build_context(warn=..., build_time_=...) from build.main() before using.
"""

import html as _html
import re
import sys

from nugget_parser import CONTENT_DIR, load_index_copy
from site_paths import parse_list_menu

_warn_callback = lambda msg, filepath=None: print(msg, file=sys.stderr)
build_time = None
build_version = 0
page_version = 0
changed_in_build = 0
changed_time = None
nugget_revisions = {}


def set_build_context(*, warn=None, build_time_=None, build_version_=None, page_version_=None, changed_in_build_=None, changed_time_=None, nugget_revisions_=None):
    global _warn_callback, build_time, build_version, page_version, changed_in_build, changed_time, nugget_revisions
    if warn is not None:
        _warn_callback = warn
    if build_time_ is not None:
        build_time = build_time_
    if build_version_ is not None:
        build_version = build_version_
    if page_version_ is not None:
        page_version = page_version_
    if changed_in_build_ is not None:
        changed_in_build = changed_in_build_
    if changed_time_ is not None:
        changed_time = changed_time_
    if nugget_revisions_ is not None:
        nugget_revisions = nugget_revisions_


def _warn(msg, filepath=None):
    _warn_callback(msg, filepath=filepath)


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


_NAV_ITEMS = None


def _nav_items():
    global _NAV_ITEMS
    if _NAV_ITEMS is None:
        _NAV_ITEMS = get_nav_items(load_index_copy())
    return _NAV_ITEMS


def _head_links(css_href="site.css", icon_href="logo.svg"):
    return f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=Inter:wght@300;400;600&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">
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
                    f'<a href="{prefix}list.html" class="nav-btn">Lists</a>'
                    '<button type="button" class="nav-dropdown-trigger" aria-expanded="false" aria-haspopup="true" aria-label="Lists menu"></button>'
                    '<ul class="nav-dropdown">'
                    + "".join(dropdown_items) +
                    '</ul></li>'
                )
            else:
                nav_item_parts.append(f'<li class="nav-link-item"><a href="{prefix}list.html" class="nav-btn">{_html.escape(label)}</a></li>')
        else:
            nav_item_parts.append(f'<li class="nav-link-item"><a href="{prefix}{href}" class="nav-btn">{_html.escape(label)}</a></li>')
    search_li = '<li><button type="button" class="nav-search-btn nav-btn" aria-label="Search pods" onclick="seedNavOpenSearch();return false">Search</button></li>'
    goto_li = (
        '<li class="nav-goto-wrap">'
        '<label for="nav-goto-num" class="sr-only">Goto pod</label>'
        '<input type="text" id="nav-goto-num" class="nav-goto-input" inputmode="numeric" pattern="[0-9]*" maxlength="4" onkeydown="if(event.key===\'Enter\'){event.preventDefault();seedNavGoFromInput(this);}">'
        '<button type="button" class="nav-goto-btn nav-btn" aria-label="Go to pod" onclick="seedNavGo(this);return false">Go</button>'
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
  <div class="nav-brand"><a href="{index_href}" class="nav-logo"><img src="{logo_src}" alt="" class="nav-logo-icon"><span class="nav-logo-text"><span class="nav-logo-word1">Seed</span><span class="nav-logo-word2">Pods</span></span></a></div>
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
<div id="search-dialog" class="search-dialog" role="dialog" aria-modal="true" aria-label="Search pods" hidden>
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


def foot(logo_href="logo.svg", page_timestamp=None):
    home_href = "index.html"
    chg_time = changed_time or build_time
    chg_ts = chg_time.strftime("%Y-%m-%d %H:%M Pacific") if chg_time else ""
    chg_hm = chg_time.strftime("%H:%M Pacific") if chg_time else ""
    cur_ts = build_time.strftime("%Y-%m-%d %H:%M Pacific") if build_time else ""
    display_ts = f"{page_timestamp} {chg_hm}".strip() if page_timestamp else chg_ts
    version_attr = f' data-build-version="{build_version}" data-changed-in-build="{changed_in_build}" data-page-version="{page_version}" data-build-timestamp="{_html.escape(cur_ts)}"'
    logo_block = f'''
<div class="page-end" id="page-end-version"{version_attr}>
  <button class="page-end-logo" aria-label="Show build info" onmouseenter="typeof seedNavShowVersion==='function'&&seedNavShowVersion(true)" onmouseleave="typeof seedNavShowVersion==='function'&&seedNavShowVersion(false)" ontouchend="typeof seedNavToggleVersion==='function'&&(seedNavToggleVersion(),event.preventDefault())">
    <img src="{logo_href}" alt="" width="32" height="32">
  </button>
  <span class="page-end-version" aria-hidden="true">Build {changed_in_build} · Rev {page_version} · {display_ts}</span>
</div>
'''
    return logo_block + "\n" + NAV_SCROLL_SCRIPT + "\n" + NAV_LISTS_DROPDOWN_SCRIPT + "\n" + SEARCH_DIALOG_HTML


def nav_seed_script_content():
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
  if(!h&&q)h='<p class="search-no-results">No pods match.</p>';
  el.innerHTML=h;
};
window.seedNavShowVersion=function(show){var el=document.querySelector(".page-end-version");if(el)el.classList.toggle("page-end-version-visible",!!show);};
window.seedNavToggleVersion=function(){var el=document.querySelector(".page-end-version");if(el)el.classList.toggle("page-end-version-visible");};
document.addEventListener("keydown",function(e){if(e.key==="Escape"){var n=document.querySelector("nav");if(n&&n.classList.contains("nav-hamburger-open"))window.seedNavToggleMenu();else window.seedNavCloseSearch();}});
document.addEventListener("DOMContentLoaded",function(){var h=window.location.hash;if(!h)return;var el=document.querySelector("details"+h);if(!el)return;el.open=true;setTimeout(function(){el.scrollIntoView({behavior:"auto",block:"start"});},80);});
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
<script>if(new URLSearchParams(location.search).has('mobile'))document.documentElement.classList.add('mobile-sim');</script>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — SeedPods</title>
{links}
{extra}
<script src="seed-nav.js"></script>
</head>
<body>"""


def close():
    return "\n</body>\n</html>"
