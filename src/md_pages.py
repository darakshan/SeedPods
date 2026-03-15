"""
Markdown page processor: single pipeline for all .md pages.
Load file → @include → @directives → @link → markdown → HTML.
Used by build.py for home, about, resources, internal pages.
"""

import html as _html
import re
from pathlib import Path

from nugget_parser import display_number, nugget_tag

try:
    import markdown
except ImportError:
    markdown = None

_ROOT = Path(__file__).resolve().parent.parent


def _md_link_output_name(md_path, content_root=None):
    """Return the d/ filename for a referenced .md file: path relative to content_root (or repo root) with / → -, .md → .html."""
    root = (content_root or _ROOT).resolve()
    try:
        rel = md_path.resolve().relative_to(root)
    except ValueError:
        return None
    parts = list(rel.parts)
    if not parts or not str(rel).endswith(".md"):
        return None
    parts[-1] = Path(parts[-1]).stem + ".html"
    return "-".join(parts)


def expand_links(text, context, base_dir, collected_md_refs=None):
    """Replace @link(locator, text) with <a href="...">text</a>. Runs before markdown.
    locator: nugget number (e.g. 002) or path like internal/inside.md (relative to repo root).
    collected_md_refs: optional set to add referenced .md paths to (for build to emit)."""
    if collected_md_refs is None:
        collected_md_refs = set()
    from nugget_parser import nugget_by_number_flex

    def repl(m):
        locator = m.group(1).strip()
        link_text = m.group(2).strip()
        if not link_text:
            link_text = locator
        if re.match(r"^\d+$", locator):
            nuggets = context.get("nuggets") or []
            n = nugget_by_number_flex(nuggets, locator)
            if not n:
                context.get("warn", lambda msg: None)(f"@link: nugget {locator!r} not found")
                return m.group(0)
            href = nugget_tag(n) + ".html"
            return f'<a href="{href}">{_html.escape(link_text)}</a>'
        if locator.endswith(".md"):
            content_root = context.get("content_dir") or _ROOT
            md_path = (content_root / locator).resolve()
            if not md_path.exists():
                context.get("warn", lambda msg: None)(f"@link: file not found {locator!r}")
                return m.group(0)
            collected_md_refs.add(md_path)
            out_name = _md_link_output_name(md_path, content_root)
            if not out_name:
                context.get("warn", lambda msg: None)(f"@link: invalid path {locator!r}")
                return m.group(0)
            return f'<a href="{out_name}">{_html.escape(link_text)}</a>'
        return f'<a href="{_html.escape(locator)}">{_html.escape(link_text)}</a>'

    return re.sub(r"@link\s*\(\s*([^,)]+)\s*,\s*([^)]*)\s*\)", repl, text)


def expand_includes(text, base_dir, warn=None):
    """Replace lines @include filename with file contents from base_dir. Paths resolved under base_dir."""
    if warn is None:
        warn = lambda msg: None
    base_dir = Path(base_dir).resolve()
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("@include "):
            name = stripped[8:].strip()
            inc_path = (base_dir / name).resolve()
            if not str(inc_path).startswith(str(base_dir)):
                warn(f"Warning: @include {name!r} resolves outside {base_dir}")
                continue
            if not inc_path.exists():
                warn(f"Warning: @include {name!r} not found")
                continue
            out.append(inc_path.read_text(encoding="utf-8"))
        else:
            out.append(line)
    return "\n".join(out)


def _render_samples_html(
    nuggets,
    status_order,
    copy,
    count=5,
    full_section=False,
    include_view_all=True,
    include_repo_link=True,
    base_href="d/",
):
    """Render sample seed rows (or full seed-list-section when full_section=True). copy = index.txt dict.
    count=None means all nuggets. base_href is prefix for links (e.g. '' for list page, 'd/' for index)."""
    status_rank = {s: i for i, s in enumerate(status_order)}
    key_status = lambda n: status_rank.get(n.get("status", "empty"), len(status_order))
    key_num = lambda n: int(n.get("number", "0")) if (n.get("number") or "").isdigit() else 0
    by_ready = sorted(nuggets, key=lambda n: (key_status(n), key_num(n)))
    recent = by_ready if count is None else by_ready[:count]
    rows_html = ""
    sortable = full_section and count is None
    for n in recent:
        fname = nugget_tag(n) + ".html"
        num = n.get("number", "")
        title = n.get("title", "")
        subtitle = n.get("subtitle", "")
        status = n.get("status", "empty")
        stub = " stub" if status == "empty" else ""
        num_display = display_number(num)
        title_line = f"{num_display}. {title}" if num_display else title
        status_span = f'<span class="seed-status">{_html.escape(status)}</span>'
        byline = f"{_html.escape(subtitle)} · {status_span}" if subtitle else status_span
        num_val = int(num) if (num or "").isdigit() else 0
        date_val = (n.get("date") or "").strip() or "0000-00-00"
        rank = status_rank.get(status, len(status_order))
        data_attrs = ""
        if sortable:
            data_attrs = f' data-num="{num_val}" data-date="{_html.escape(date_val)}" data-status-rank="{rank}" data-title="{_html.escape(title)}"'
        rows_html += f"""
    <a href="{base_href}{fname}" class="seed-row{stub}"{data_attrs}>
      <div>
        <div class="seed-title">{_html.escape(title_line)}</div>
        <div class="seed-sub">{byline}</div>
      </div>
    </a>"""
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


def expand_page_directives(text, context):
    """Replace @directives in page content. Returns (text_with_placeholders, {placeholder: html}).
    context: nuggets, status_order, copy (from index.txt), build_time, page.
    @timestamp is replaced everywhere it appears (whole line or inline)."""
    if not text:
        return text, {}
    nuggets = context.get("nuggets") or []
    status_order = context.get("status_order") or []
    copy = context.get("copy") or {}
    build_time = context.get("build_time")
    page = context.get("page")
    timestamp_str = build_time.strftime("%Y-%m-%d %H:%M Pacific") if build_time else None
    out = []
    replacements = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("@samples"):
            rest = stripped[7:].strip()
            count = 5
            if rest.isdigit():
                count = min(int(rest), 50)
            if nuggets and status_order:
                full = page == "home"
                base_href = "" if page == "list" or context.get("site_dir") else (context["site_dir"].rstrip("/") + "/")
                block = _render_samples_html(
                    nuggets,
                    status_order,
                    copy,
                    count=count,
                    full_section=full,
                    include_view_all=full,
                    include_repo_link=False,
                    base_href=base_href,
                )
                placeholder = "{{SAMPLES}}"
                replacements[placeholder] = block
                out.append(placeholder)
            continue
        if stripped.startswith("@nuggets"):
            if nuggets and status_order:
                base_href = "" if page == "list" or context.get("site_dir") else (context["site_dir"].rstrip("/") + "/")
                block = _render_samples_html(
                    nuggets,
                    status_order,
                    copy,
                    count=None,
                    full_section=True,
                    include_view_all=False,
                    include_repo_link=False,
                    base_href=base_href,
                )
                placeholder = "{{NUGGETS}}"
                replacements[placeholder] = block
                out.append(placeholder)
            continue
        if stripped == "@timestamp" and timestamp_str:
            out.append(timestamp_str)
            continue
        if timestamp_str and "@timestamp" in line:
            line = line.replace("@timestamp", timestamp_str)
        out.append(line)
    return "\n".join(out), replacements


def process_md_to_html(md_path, context=None, collected_md_refs=None):
    """Single pipeline for .md → HTML: load file, @include, @directives, @link, markdown. Returns body HTML.
    context: copy (index.txt), nuggets, status_order, page, build_time, warn (callable).
    collected_md_refs: optional set; referenced .md paths (for @link) are added for build to emit."""
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
    warn = context.get("warn", lambda msg: None)
    raw = expand_includes(raw, base_dir, warn=warn)
    expanded, replacements = expand_page_directives(raw, context)
    for placeholder, block in replacements.items():
        expanded = expanded.replace(placeholder, block)
    expanded = expand_links(expanded, context, base_dir, collected_md_refs)
    if not expanded.strip():
        return ""
    html = markdown.markdown(
        expanded,
        extensions=["fenced_code", "tables"],
        extension_configs={"fenced_code": {}},
    )
    html = re.sub(
        r'<p>(TBD|No reviews completed yet\.)</p>',
        r'<p class="dim placeholder">\1</p>',
        html,
    )
    return html
