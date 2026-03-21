"""
Render nugget layer content (prose, script, @nugget, @exercise) to HTML.
"""

import html as _html
import re
from pathlib import Path

try:
    import markdown as _markdown
except ImportError:
    _markdown = None

from directive import image_directive_handler, process_directives
from md_pages import _md_link_handler, _md_setting_handler, _md_timestamp_handler
from nugget_parser import expand_nugget_directives, section_is_tbd

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
    """Convert text to HTML. Uses Markdown when available; falls back to simple paragraph/list/divider renderer."""
    if section_is_tbd(text):
        return '<p class="dim placeholder">This layer is not yet written.</p>'
    if _markdown is not None:
        return _markdown.markdown(text, extensions=["fenced_code", "tables"])
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


def _layer_nugget_handler(_verb, content, context):
    from nugget_parser import nugget_by_number_flex, nugget_tag
    n = nugget_by_number_flex(context["all_nuggets"], content.strip())
    if n is None:
        num = content.strip()
        link_errors = context.get("link_errors")
        if link_errors is not None:
            link_errors.append(f"@link: nugget {num!r} not found")
        else:
            warn = context.get("warn", lambda msg, filepath=None: None)
            warn(f"@link: nugget {num!r} not found")
        return None
    title = n.get("title", "Untitled")
    filename = n.get("filename", "")
    return f'<em><a href="{filename}.html">{_html.escape(title)}</a></em>'


def _layer_exercise_handler(_verb, content, context):
    inner = content.strip()
    expanded = expand_nugget_directives(inner, context["all_nuggets"]) if inner else ""
    cta_html = text_to_html(expanded) if expanded else ""
    cta_htmls = context["cta_htmls"]
    idx = len(cta_htmls)
    cta_htmls.append(f'<div class="cta">{cta_html}</div>' if cta_html else "")
    return f"{{{{EXERCISE_{idx}}}}}"


def _layer_warn_handler(_verb, content, context):
    inner = content.strip()
    expanded = expand_nugget_directives(inner, context["all_nuggets"]) if inner else ""
    warn_html = text_to_html(expanded) if expanded else ""
    cta_htmls = context["cta_htmls"]
    idx = len(cta_htmls)
    cta_htmls.append(f'<div class="warn-notice">{warn_html}</div>' if warn_html else "")
    return f"{{{{EXERCISE_{idx}}}}}"


def expand_layer_directives(raw, all_nuggets, filepath=None, extra_context=None):
    """Expand directives in layer text via directive.process_directives. Returns (segments, cta_htmls)."""
    if not raw:
        return [], []
    cta_htmls = []
    handlers = {
        "nugget": _layer_nugget_handler,
        "exercise": _layer_exercise_handler,
        "warn": _layer_warn_handler,
        "image": image_directive_handler,
        "link": _md_link_handler,
        "timestamp": _md_timestamp_handler,
        "setting": _md_setting_handler,
        "ref": lambda verb, content, ctx: "",
    }
    ctx = {
        "warn": lambda msg, filepath=None: None,
        "notes": [],
        "cta_htmls": cta_htmls,
        "all_nuggets": all_nuggets,
        "handlers": handlers,
    }
    if extra_context:
        for k, v in extra_context.items():
            if k == "handlers":
                handlers.update(v)
            else:
                ctx[k] = v
    fp = filepath if filepath is not None else Path(".")
    text, _ = process_directives(raw, fp, ctx)
    segments = re.split(r"(\{\{EXERCISE_\d+\}\})", text)
    return segments, cta_htmls


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


def _layer_prose_to_html(raw, all_nuggets, link_context=None):
    """Prose layers: expand directives, then render each segment with text_to_html."""
    if section_is_tbd(raw):
        return '<p class="dim placeholder">This layer is not yet written.</p>'
    segments, cta_htmls = expand_layer_directives(raw, all_nuggets, extra_context=link_context)

    def render_seg(seg):
        if section_is_tbd(seg):
            return ""
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
