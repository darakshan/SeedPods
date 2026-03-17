"""
Single place for @-directive handling when reading .md or nugget/*.txt.
One form: @verb or @verb(content). Parentheses are optional; without them content is empty.
Multi-argument directives use comma-separated content; split with split_directive_args().
Complain on unknown verb or unclosed parentheses; dispatch to handlers; return updated text.
Side effects (e.g. @note contents for printing) are collected in context.
"""

import html as _html
import re
import shutil
from pathlib import Path

KNOWN_VERBS = {
    "include", "samples", "nuggets", "categories", "glossary", "bibliography", "index", "map",
    "timestamp", "link", "note", "exercise", "nugget", "image",
}

_ROOT = Path(__file__).resolve().parent.parent
_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def split_directive_args(content):
    """Split directive content by comma; return list of stripped segments. Use for multi-arg directives."""
    if not (content or "").strip():
        return []
    return [s.strip() for s in content.split(",")]


def image_directive_handler(verb, content, context):
    """Handle @image(file, caption, credit): copy content/images/file to site images/, return figure HTML. Only file required."""
    args = split_directive_args(content or "")
    name = args[0] if args else ""
    caption = args[1] if len(args) > 1 else ""
    credit = args[2] if len(args) > 2 else ""
    if not name or ".." in name or "/" in name or "\\" in name:
        return None
    content_dir = context.get("content_dir")
    site_dir = context.get("site_dir")
    if not content_dir:
        return None
    content_dir = Path(content_dir).resolve()
    if site_dir is not None:
        site_dir = Path(site_dir).resolve() if isinstance(site_dir, Path) else _ROOT / str(site_dir).strip()
    else:
        site_dir = _ROOT / "d"
    images_src = content_dir / "images"
    images_dst = site_dir / "images"
    src_path = None
    ext_used = None
    for ext in _IMAGE_EXTS:
        candidate = images_src / (name + ext)
        if candidate.is_file():
            src_path = candidate
            ext_used = ext
            break
    if not src_path or not src_path.is_file():
        warn = context.get("warn", lambda msg, filepath=None: None)
        warn("@image({!r}): no file in content/images/ (tried {})".format(name, ", ".join(name + e for e in _IMAGE_EXTS)), filepath=context.get("filepath"))
        return None
    images_dst.mkdir(parents=True, exist_ok=True)
    dest_path = images_dst / (name + ext_used)
    shutil.copy2(src_path, dest_path)
    href = "images/" + name + ext_used
    figcaption = ""
    if caption or credit:
        parts = []
        if caption:
            parts.append(_html.escape(caption))
        if credit:
            parts.append("<cite>{}</cite>".format(_html.escape(credit)))
        figcaption = "<figcaption>{}</figcaption>".format(" ".join(parts))
    return '<figure class="directive-image directive-image--left"><img src="{}" alt="">{}</figure>'.format(href, figcaption)


def _parse_directive(text, start, filepath, warn):
    """Find @ at or after start; return (verb, content, end_pos). On bad parens warn and return (None, None, end)."""
    at = text.find("@", start)
    if at < 0:
        return None, None, len(text)
    verb_m = re.match(r"[a-zA-Z]+", text[at + 1 :])
    if not verb_m:
        return None, None, at + 1
    verb = verb_m.group(0).lower()
    pos = at + 1 + verb_m.end()
    while pos < len(text) and text[pos] in " \t":
        pos += 1

    if pos < len(text) and text[pos] == "(":
        depth = 1
        j = pos + 1
        while j < len(text) and depth:
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
            j += 1
        if depth != 0:
            warn("unclosed parentheses in @{}(...)".format(verb), filepath=filepath)
            return None, None, j if j <= len(text) else len(text)
        content = text[pos + 1 : j - 1]
        return verb, content, j
    return verb, "", pos


def process_directives(text, filepath, context):
    """Process all @directives in text. context: warn, base_dir (for @include), notes (list), handlers (verb -> fn(verb, content, context) -> replacement).
    Returns (new_text, notes). notes are appended to context['notes'] and also returned."""
    if not text:
        return "", context.get("notes", [])
    notes = context.get("notes")
    if notes is None:
        notes = []
        context["notes"] = notes
    warn = context.get("warn", lambda msg, filepath=None: None)
    handlers = context.get("handlers", {})
    base_dir = context.get("base_dir")

    out = []
    pos = 0
    while pos < len(text):
        next_at = text.find("@", pos)
        if next_at < 0:
            out.append(text[pos:])
            break
        verb, content, end = _parse_directive(text, next_at, filepath, warn)
        if verb is None:
            out.append(text[pos:next_at + 1])
            pos = next_at + 1
            continue
        out.append(text[pos:next_at])
        span_start = next_at
        replacement = None
        if verb == "note":
            notes.append(content.strip())
            replacement = ""
        elif verb == "include":
            path_arg = content.strip()
            if not path_arg:
                warn("@include() requires a path: @include(filename)", filepath=filepath)
                replacement = text[span_start:end]
            elif base_dir is not None:
                inc_path = (Path(base_dir).resolve() / path_arg).resolve()
                base = Path(base_dir).resolve()
                if not str(inc_path).startswith(str(base)):
                    warn("@include {!r} resolves outside base dir".format(path_arg), filepath=filepath)
                    replacement = text[span_start:end]
                elif not inc_path.exists():
                    warn("@include {!r} not found".format(path_arg), filepath=filepath)
                    replacement = text[span_start:end]
                else:
                    replacement = inc_path.read_text(encoding="utf-8")
                    if replacement and not replacement.endswith("\n"):
                        replacement += "\n"
            else:
                replacement = text[span_start:end]
        elif verb in handlers:
            replacement = handlers[verb](verb, content, context)
            if replacement is None:
                replacement = text[span_start:end]
        else:
            if verb not in KNOWN_VERBS:
                warn("unknown @ directive @{} (possible misspelling?)".format(verb), filepath=filepath)
            replacement = text[span_start:end]
        out.append(replacement)
        pos = end
    return "".join(out), notes
