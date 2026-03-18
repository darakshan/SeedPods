"""
Page builders: build_nugget, build_*_page / build_*_body, and MD context.
Composes site_chrome, nugget_layers, explainers_glossary, graph_svg.
"""

import html as _html

from explainers_glossary import build_explainers_page, build_glossary_body, build_glossary_page, load_explainers_csv, tag_slug
from graph_svg import map_directive_html
from md_pages import process_md_to_html, expand_links
from nugget_layers import (
    _assemble_layer_html,
    _layer_prose_to_html,
    expand_layer_directives,
    script_to_html,
)
from nugget_parser import (
    CONTENT_DIR,
    NUGGETS_DIR,
    display_number,
    expand_nugget_directives,
    load_index_copy,
    nugget_by_number,
    nugget_tag,
    section_is_tbd,
)
from reporter import error as reporter_error, note as reporter_note
import site_chrome
from site_chrome import close, foot, get_list_menu_items, get_nav_items, head, nav, nav_seed_script_content, set_build_context, _first_h1, _warn

INTERNAL_DIR = CONTENT_DIR / "internal"

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

PROTO_NOTICE_HTML = '''<div class="proto-notice"><p class="dim">Beware! This nugget might be a crazy idea. It will one day be fleshed out, merged with another nugget, or even removed. Caveat lector.</p></div>'''

ROUGH_NOTICE_HTML = '''<div class="rough-notice"><p class="dim">This nugget is a rough draft, far from polished. Caveat lector.</p></div>'''


def build_nugget(n, all_nuggets, link_errors=None, site_dir=None):
    num = n.get("number", "?")
    title = n.get("title", "Untitled")
    subtitle = n.get("subtitle", "")
    status = n.get("status", "empty")
    date = n.get("date", "")
    tags = n.get("tags", [])
    related_nums = n.get("related", [])
    layers = n.get("layers", {})

    link_context = {"nuggets": all_nuggets, "content_dir": CONTENT_DIR, "warn": _warn, "link_errors": link_errors}
    if site_dir is not None:
        link_context["site_dir"] = site_dir
    link_base_dir = NUGGETS_DIR

    tags_href = "tags.html"
    tag_html = " ".join(f'<a href="{tags_href}#{tag_slug(t)}" class="tag">{t}</a>' for t in tags)

    rel_nuggets = [nugget_by_number(all_nuggets, r) for r in related_nums]
    fn = n.get("filename") or ""
    shortname = fn.split("-", 1)[-1] if "-" in fn else None
    for r in related_nums:
        if not nugget_by_number(all_nuggets, r):
            reporter_error("related {} does not match any nugget".format(r), nugget_num=num, shortname=shortname)
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
        for n in matching:
            num = n.get("number", "")
            title = n.get("title", "")
            subtitle = n.get("subtitle", "")
            fname = nugget_tag(n) + ".html"
            title_display = f"{display_number(num)}. {title}" if num else title
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
    """Default context for process_md_to_html: warn, build_time, content_dir, site_dir, note. Merge with overrides."""
    copy = overrides.get("copy", load_index_copy())
    def _note(msg, filepath=None):
        reporter_note(msg, path=filepath)
    return {"warn": _warn, "build_time": site_chrome.build_time, "content_dir": CONTENT_DIR, "site_dir": (copy.get("site_dir") or "").strip(), "note": _note, **overrides}


def _md_context_with_special(nuggets, status_order, explainer_terms=None, **overrides):
    """Context for process_md_to_html including @glossary, @bibliography, @index, @map placeholder HTML."""
    ctx = _md_context(nuggets=nuggets, status_order=status_order, **overrides)
    ctx["glossary_html"] = build_glossary_body(nuggets, explainer_terms)
    ctx["bibliography_html"] = build_bibliography_body(nuggets)
    ctx["index_html"] = build_tags_body(nuggets, status_order)
    ctx["map_html"] = map_directive_html(nuggets, status_order)
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


def build_map_graph_page(nuggets, status_order):
    return build_static_page("Map", map_directive_html(nuggets, status_order), wrap_class="wrap--full")


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
