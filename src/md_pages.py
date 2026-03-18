"""
Markdown page processor: single pipeline for all .md pages.
Load file → @include → @directives → @link → markdown → HTML.
Used by build.py for home, about, resources, internal pages.
"""

import html as _html
import re
import sys
from pathlib import Path

from directive import first_image_href_from_nugget, image_directive_handler, process_directives

from nugget_parser import display_number, load_index_copy, nugget_tag
from site_paths import content_path_to_output_name

try:
    import markdown
    from markdown.extensions.toc import TocExtension, slugify as _heading_slug
except ImportError:
    markdown = None
    _heading_slug = None

_ROOT = Path(__file__).resolve().parent.parent


def _resolve_content_md_path(content_root, locator):
    """Resolve path-only locator (e.g. 'about', 'about/authors') to a .md path under content_root.
    Tries locator + '.md' first, then locator + '/page.md'. Returns None if not found."""
    content_root = Path(content_root).resolve()
    locator = locator.strip().strip("/")
    if not locator or ".." in locator:
        return None
    path = Path(locator)
    as_file = (content_root / path).with_suffix(".md")
    if as_file.is_file():
        return as_file
    as_page = content_root / path / "page.md"
    if as_page.is_file():
        return as_page
    return None


def _title_from_md(md_path):
    """Return title from .md file: first # heading, or first non-empty line."""
    try:
        raw = md_path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            return line.lstrip("#").strip()
        return line
    return None


def resolve_link(locator, explicit_text, context, base_dir, collected_md_refs=None):
    """Resolve @link(locator, text) to (href, link_text). Single abstraction for .md and nuggets.
    locator: nugget number (e.g. 002), .md path (relative to base_dir), path-only (e.g. about, about/authors), or raw href.
    Returns (href, link_text) or (None, None) on error (caller may keep original text)."""
    if collected_md_refs is None:
        collected_md_refs = set()
    from nugget_parser import nugget_by_number_flex

    content_root = Path(context.get("content_dir") or _ROOT).resolve()
    base_dir = Path(base_dir).resolve()
    warn = context.get("warn", lambda msg, filepath=None: None)
    link_errors = context.get("link_errors")

    def record_error(msg):
        if link_errors is not None:
            link_errors.append(msg)
        else:
            warn(msg)

    link_text = (explicit_text or "").strip() or locator

    if re.match(r"^\d+$", locator):
        nuggets = context.get("nuggets") or []
        n = nugget_by_number_flex(nuggets, locator)
        if not n:
            record_error(f"@link: nugget {locator!r} not found")
            return None, None
        href = nugget_tag(n) + ".html"
        if not (explicit_text or "").strip():
            link_text = n.get("title", "Untitled")
        return href, link_text

    if locator.endswith(".md"):
        md_path = (base_dir / locator).resolve()
        if not md_path.exists():
            record_error(f"@link: file not found {locator!r}")
            return None, None
        try:
            md_path.relative_to(content_root)
        except ValueError:
            record_error(f"@link: path {locator!r} resolves outside content dir")
            return None, None
        collected_md_refs.add(md_path)
        out_name = content_path_to_output_name(md_path, content_root)
        if not out_name:
            record_error(f"@link: invalid path {locator!r}")
            return None, None
        return out_name, link_text

    content_md = _resolve_content_md_path(content_root, locator)
    if content_md is not None:
        collected_md_refs.add(content_md)
        try:
            rel = content_md.relative_to(content_root)
        except ValueError:
            out_name = None
        else:
            parts = rel.parts
            if len(parts) >= 2 and parts[-1] == "page.md":
                out_name = parts[-2] + ".html"
            else:
                out_name = content_path_to_output_name(content_md, content_root)
        if not out_name:
            record_error(f"@link: invalid path {locator!r}")
            return None, None
        if not (explicit_text or "").strip():
            link_text = _title_from_md(content_md) or content_md.stem
        return out_name, link_text

    if "/" in locator and _heading_slug is not None:
        last_slash = locator.rfind("/")
        path_part = locator[:last_slash].strip()
        section_part = locator[last_slash + 1 :].strip()
        if path_part and section_part:
            content_md = _resolve_content_md_path(content_root, path_part)
            if content_md is not None:
                collected_md_refs.add(content_md)
                try:
                    rel = content_md.relative_to(content_root)
                except ValueError:
                    out_name = None
                else:
                    parts = rel.parts
                    if len(parts) >= 2 and parts[-1] == "page.md":
                        out_name = parts[-2] + ".html"
                    else:
                        out_name = content_path_to_output_name(content_md, content_root)
                if not out_name:
                    record_error(f"@link: invalid path {locator!r}")
                    return None, None
                fragment = _heading_slug(section_part, "-")
                href = out_name + "#" + fragment
                if not (explicit_text or "").strip():
                    link_text = section_part
                return href, link_text

    return locator, link_text


def expand_links(text, context, base_dir, collected_md_refs=None):
    """Replace @link(locator, text) with <a href="...">text</a>. Runs before markdown. Used when directive.process_directives is not used (e.g. nugget layer prose)."""
    if collected_md_refs is None:
        collected_md_refs = set()

    def repl(m):
        locator = m.group(1).strip()
        explicit_text = (m.group(2) or "").strip()
        href, link_text = resolve_link(locator, explicit_text, context, base_dir, collected_md_refs)
        if href is None:
            return m.group(0)
        return f'<a href="{_html.escape(href)}">{_html.escape(link_text)}</a>'

    return re.sub(r"@link\s*\(\s*([^,)]+)\s*(?:,\s*([^)]*))?\s*\)", repl, text)


def _md_link_handler(_verb, content, context):
    parts = content.split(",", 1)
    locator = parts[0].strip()
    explicit_text = parts[1].strip() if len(parts) > 1 else ""
    href, link_text = resolve_link(
        locator, explicit_text, context,
        context["base_dir"],
        context.get("collected_md_refs"),
    )
    if href is None:
        return None
    return f'<a href="{_html.escape(href)}">{_html.escape(link_text)}</a>'


def _md_setting_handler(_verb, content, context):
    """Replace @setting(key) with the value from config/settings.txt (e.g. site_base, site_dir). site_base is returned with no trailing slash for URL concatenation."""
    key = (content or "").strip()
    if not key:
        return ""
    copy = context.get("copy")
    if copy is None:
        copy = load_index_copy()
    value = (copy.get(key) or "").strip()
    if key == "site_base" and value:
        value = value.rstrip("/")
    return value


def expand_includes(text, base_dir, warn=None, filepath=None):
    """Expand @include directives in text. Paths resolved under base_dir. filepath used in warnings."""
    if warn is None:
        warn = lambda msg, filepath=None: None
    fp = filepath if filepath is not None else Path(base_dir).resolve()
    ctx = {"base_dir": Path(base_dir).resolve(), "warn": warn, "notes": [], "handlers": {}}
    return process_directives(text, fp, ctx)[0]


CATEGORY_ORDER = (
    "consciousness", "sensation", "physics", "mathematics", "biology", "AI-minds", "knowledge",
)


def _seed_row_html(n, base_href, status_order, stub_only=False, first_image_href=None, rev=None):
    """One seed-row div for a nugget. stub_only=True omits data attrs for sortable lists. rev=page version for this nugget (shown after status)."""
    fname = nugget_tag(n) + ".html"
    num = n.get("number", "")
    title = n.get("title", "")
    subtitle = n.get("subtitle", "")
    status = n.get("status", "empty")
    stub = " stub" if status == "empty" else ""
    num_display = display_number(num)
    title_line = f"{num_display}. {title}" if num_display else title
    status_span = f'<span class="seed-status">{_html.escape(status)}</span>'
    rev_span = f'<span class="seed-status">rev {rev}</span>' if rev is not None else ""
    byline_parts = [status_span]
    if rev_span:
        byline_parts.append(rev_span)
    byline_inner = " · ".join(byline_parts)
    byline = f"{_html.escape(subtitle)} · {byline_inner}" if subtitle else byline_inner
    data_attrs = ""
    if not stub_only:
        status_rank = {s: i for i, s in enumerate(status_order or [])}
        num_val = int(num) if (num or "").isdigit() else 0
        date_val = (n.get("date") or "").strip() or "0000-00-00"
        rank = status_rank.get(status, len(status_rank))
        data_attrs = f' data-num="{num_val}" data-date="{_html.escape(date_val)}" data-status-rank="{rank}" data-title="{_html.escape(title)}"'
    thumb = ""
    if first_image_href:
        thumb = f'<div class="seed-row-thumb"><img src="{_html.escape(first_image_href)}" alt="" class="seed-thumb"></div>'
    return f"""
    <div class="seed-row{stub}"{data_attrs}>
      {thumb}<div class="seed-row-body">
        <div class="seed-title"><a href="{base_href}{fname}">{_html.escape(title_line)}</a></div>
        <div class="seed-sub">{byline}</div>
      </div>
    </div>"""


def _index_entry_html(n, base_href, first_image_href=None):
    """One index-entry div for a nugget (same format as tags.html). Optionally show thumb to the left."""
    fname = nugget_tag(n) + ".html"
    num = n.get("number", "")
    title = n.get("title", "")
    subtitle = n.get("subtitle", "")
    num_display = display_number(num)
    title_display = f"{num_display}. {title}" if num_display else title
    thumb = ""
    if first_image_href:
        thumb = f'<div class="seed-row-thumb"><img src="{_html.escape(first_image_href)}" alt="" class="seed-thumb"></div>'
    body = f'<a href="{base_href}{fname}">{_html.escape(title_display)}</a><br><span class="repo-subtitle">{_html.escape(subtitle)}</span>'
    return f'<div class="index-entry">{thumb}<div class="index-entry-body">{body}</div></div>'


def _render_categories_html(nuggets, status_order, copy, base_href="", content_dir=None):
    """Render categories as a two-level tree: category name (open/close) and nuggets per category. Same style as tags.html. If content_dir is set, each entry shows its first @image thumb to the left."""
    status_rank = {s: i for i, s in enumerate(status_order)}
    key_status = lambda n: status_rank.get(n.get("status", "empty"), len(status_order))
    key_num = lambda n: int(n.get("number", "0")) if (n.get("number") or "").isdigit() else 0
    by_category = {}
    for n in nuggets:
        cat = n.get("category", "")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(n)
    for cat in by_category:
        by_category[cat] = sorted(by_category[cat], key=lambda n: (key_status(n), key_num(n)))

    def details_block(entries, label):
        inner = "\n    ".join(
            _index_entry_html(n, base_href, first_image_href=first_image_href_from_nugget(n, content_dir) if content_dir else None)
            for n in entries
        )
        return f"""  <details class="category-group">
    <summary class="index-tag-name">{_html.escape(label)}</summary>
    {inner}
  </details>"""

    parts = []
    for cat in sorted(by_category):
        label = cat.replace("-", " ")
        parts.append(details_block(by_category[cat], label))
    total = len(nuggets)
    view_all_text = (copy.get("view_all") or "View all {n} seeds →").replace("{n}", str(total))
    more_wrap = f"""
  <div class="seed-list-more-wrap">
    <a href="{base_href}list.html" class="link-mono-accent">{view_all_text}</a>
  </div>"""
    return f"""<div class="index-by-tag seed-categories">
{chr(10).join(parts)}
{more_wrap}
</div>"""


def _render_samples_html(
    nuggets,
    status_order,
    copy,
    count=5,
    full_section=False,
    include_view_all=True,
    include_repo_link=True,
    base_href="",
    content_dir=None,
    nugget_revisions=None,
):
    """Render sample seed rows (or full seed-list-section when full_section=True). copy = settings.txt dict.
    count=None means all nuggets. base_href is prefix for links (e.g. '' when site is served from output dir as root)."""
    status_rank = {s: i for i, s in enumerate(status_order)}
    key_status = lambda n: status_rank.get(n.get("status", "empty"), len(status_order))
    key_num = lambda n: int(n.get("number", "0")) if (n.get("number") or "").isdigit() else 0
    by_ready = sorted(nuggets, key=lambda n: (key_status(n), key_num(n)))
    recent = by_ready if count is None else by_ready[:count]
    sortable = full_section and count is None
    rev_map = nugget_revisions or {}
    rows_html = "".join(
        _seed_row_html(
            n,
            base_href,
            status_order if sortable else None,
            stub_only=not sortable,
            first_image_href=first_image_href_from_nugget(n, content_dir) if content_dir else None,
            rev=rev_map.get(nugget_tag(n)),
        )
        for n in recent
    )
    if not full_section:
        return rows_html.strip()
    more_wrap = ""
    if include_view_all:
        total = len(nuggets)
        view_all_text = (copy.get("view_all") or "View all {n} seeds →").replace("{n}", str(total))
        more_wrap = f"""
    <div class="seed-list-more-wrap">
      <a href="{base_href}list.html" class="link-mono-accent">{view_all_text}</a>
    </div>"""
    sort_ui = ""
    sort_script = ""
    if sortable:
        sort_ui = """
    <p class="repo-sort-wrap"><label for="repo-sort">Sort: </label><select id="repo-sort" class="repo-sort" aria-label="Sort list">
      <option value="status">By status</option>
      <option value="number" selected>By number</option>
      <option value="alpha">By name</option>
      <option value="recent">By most recent</option>
    </select></p>
    <div id="seed-list-rows">"""
        sort_script = """
    </div>
    <script>
    (function(){
      var STORAGE_KEY = "seednuggets-sort";
      var container = document.getElementById("seed-list-rows");
      var sel = document.getElementById("repo-sort");
      if (!container || !sel) return;
      function sortKey(s){ var t = (s || "").toLowerCase(); return t.indexOf("the ") === 0 ? t.slice(4) : t; }
      function sortRows(by){
        var rows = [].slice.call(container.querySelectorAll(".seed-row"));
        rows.sort(function(a,b){
          if (by === "alpha") return sortKey(a.dataset.title).localeCompare(sortKey(b.dataset.title));
          if (by === "recent") return (b.dataset.date || "").localeCompare(a.dataset.date || "");
          if (by === "number") return (+a.dataset.num) - (+b.dataset.num);
          return (+a.dataset.statusRank) - (+b.dataset.statusRank) || (+a.dataset.num) - (+b.dataset.num);
        });
        rows.forEach(function(r){ container.appendChild(r); });
      }
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved && ["status","number","alpha","recent"].indexOf(saved) >= 0) sel.value = saved;
      sel.addEventListener("change", function(){ var v = this.value; localStorage.setItem(STORAGE_KEY, v); sortRows(v); });
      sortRows(sel.value);
    })();
    </script>"""
    return f"""
  <div class="seed-list-section">
    {sort_ui}
    {rows_html}
    {more_wrap}
    {sort_script}
  </div>"""


def _md_samples_handler(_verb, content, context):
    nuggets = context.get("nuggets") or []
    status_order = context.get("status_order") or []
    if not nuggets or not status_order:
        return ""
    copy = context.get("copy") or {}
    page = context.get("page")
    count = 5
    if content.strip().isdigit():
        count = min(int(content.strip()), 50)
    full = page == "home"
    base_href = "" if page == "list" or context.get("site_dir") else (context["site_dir"].rstrip("/") + "/")
    block = _render_samples_html(
        nuggets, status_order, copy,
        count=count, full_section=full, include_view_all=full, include_repo_link=False, base_href=base_href,
        content_dir=context.get("content_dir"),
        nugget_revisions=context.get("nugget_revisions"),
    )
    placeholder = "{{SAMPLES}}"
    context.setdefault("replacements", {})[placeholder] = block
    return placeholder


def _md_categories_handler(_verb, content, context):
    nuggets = context.get("nuggets") or []
    status_order = context.get("status_order") or []
    if not nuggets or not status_order:
        return ""
    copy = context.get("copy") or {}
    page = context.get("page")
    base_href = "" if page == "list" or context.get("site_dir") else (context["site_dir"].rstrip("/") + "/")
    block = _render_categories_html(nuggets, status_order, copy, base_href=base_href, content_dir=context.get("content_dir"))
    placeholder = "{{CATEGORIES}}"
    context.setdefault("replacements", {})[placeholder] = block
    return placeholder


def _md_nuggets_handler(_verb, content, context):
    nuggets = context.get("nuggets") or []
    status_order = context.get("status_order") or []
    if not nuggets or not status_order:
        return ""
    copy = context.get("copy") or {}
    page = context.get("page")
    base_href = "" if page == "list" or context.get("site_dir") else (context["site_dir"].rstrip("/") + "/")
    block = _render_samples_html(
        nuggets, status_order, copy,
        count=None, full_section=True, include_view_all=False, include_repo_link=False, base_href=base_href,
        content_dir=context.get("content_dir"),
        nugget_revisions=context.get("nugget_revisions"),
    )
    placeholder = "{{NUGGETS}}"
    context.setdefault("replacements", {})[placeholder] = block
    return placeholder


def _md_placeholder_handler(placeholder, key):
    def handler(_verb, _content, context):
        val = context.get(key)
        if val is not None:
            context.setdefault("replacements", {})[placeholder] = val
            return placeholder
        return ""
    return handler


def _md_timestamp_handler(_verb, _content, context):
    build_time = context.get("build_time")
    if build_time is not None:
        return build_time.strftime("%Y-%m-%d %H:%M Pacific")
    return ""


def process_md_to_html(md_path, context=None, collected_md_refs=None):
    """Single pipeline for .md → HTML: load file, process_directives (@include, @note, @link, @samples, …), markdown. Returns body HTML."""
    if context is None:
        context = {}
    if collected_md_refs is None:
        collected_md_refs = set()
    if not md_path.exists():
        raise SystemExit(f"Missing markdown file: {md_path}")
    if markdown is None:
        raise SystemExit(
            "Markdown pages require the markdown package.\n"
            "  pip install markdown\n"
            "Or in a venv: pip install -r requirements.txt"
        )
    raw = md_path.read_text(encoding="utf-8")
    base_dir = md_path.parent.resolve()
    warn = context.get("warn", lambda msg, filepath=None: None)
    ctx = {
        "base_dir": base_dir,
        "warn": warn,
        "notes": [],
        "replacements": {},
        "collected_md_refs": collected_md_refs,
        "handlers": {
            "link": _md_link_handler,
            "samples": _md_samples_handler,
            "categories": _md_categories_handler,
            "nuggets": _md_nuggets_handler,
            "glossary": _md_placeholder_handler("{{GLOSSARY}}", "glossary_html"),
            "bibliography": _md_placeholder_handler("{{BIBLIOGRAPHY}}", "bibliography_html"),
            "index": _md_placeholder_handler("{{INDEX}}", "index_html"),
            "map": _md_placeholder_handler("{{MAP}}", "map_html"),
            "timestamp": _md_timestamp_handler,
            "setting": _md_setting_handler,
            "image": image_directive_handler,
        },
    }
    for k, v in context.items():
        if k not in ctx:
            ctx[k] = v
    expanded, note_list = process_directives(raw, md_path, ctx)
    note_cb = context.get("note") or (lambda msg, filepath=None: warn("@note " + msg, filepath=filepath))
    for note in note_list:
        note_cb(note, filepath=md_path)
    if not expanded.strip():
        return ""
    extensions = ["fenced_code", "tables"]
    extension_configs = {"fenced_code": {}}
    if markdown is not None:
        extensions.append(TocExtension(marker=""))
    html = markdown.markdown(
        expanded,
        extensions=extensions,
        extension_configs=extension_configs,
    )
    for placeholder, block in ctx["replacements"].items():
        escaped = re.escape(placeholder)
        html = re.sub(r"<p>\s*" + escaped + r"\s*</p>", block, html)
        html = html.replace(placeholder, block)
    html = re.sub(
        r'<p>(TBD|No reviews completed yet\.)</p>',
        r'<p class="dim placeholder">\1</p>',
        html,
    )
    return html
