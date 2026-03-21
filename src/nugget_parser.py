"""
Parse nugget .txt files and provide load/lookup/expand helpers.
"""

import html as _html
import re
import sys
from pathlib import Path

from directive import process_directives, split_directive_args

_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = _ROOT / "content"
CONFIG_DIR = _ROOT / "config"
NUGGETS_DIR = CONTENT_DIR / "pods"


def section_is_tbd(text):
    """True if section is empty or counts as TBD (single line TBD or empty)."""
    body = (text or "").strip()
    if not body:
        return True
    if body.upper() == "TBD":
        return True
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    return len(lines) == 1 and lines[0].upper().startswith("TBD")


def display_number(num):
    """Strip leading zeros for display; keep filenames/URLs as-is."""
    if num and num.isdigit():
        return str(int(num))
    return num or "?"


def nugget_tag(n):
    """Return the number + short name tag for a nugget (e.g. 001-caloric, 033-edge)."""
    return n.get("filename", "")


def load_key_value_file(path):
    """Read key: value lines from path. Lines starting with # and trailing # comments are ignored."""
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if " #" in line:
            line = line[: line.index(" #")].strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def load_index_copy():
    """Config settings.txt as key: value dict."""
    return load_key_value_file(CONFIG_DIR / "settings.txt")


def load_status_order(path=None):
    """One status per line from path (default config/status.txt). Returns [] if missing. Inline # comments stripped."""
    p = path if path is not None else CONFIG_DIR / "status.txt"
    if not p.exists():
        return []
    result = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if "#" in line:
            line = line[: line.index("#")].strip()
        else:
            line = line.strip()
        if line:
            result.append(line)
    return result


def nugget_by_number_flex(nuggets, num_str):
    """Look up nugget by number; tries num_str then num_str.zfill(3) if numeric."""
    n = nugget_by_number(nuggets, num_str)
    if n is None and num_str and num_str.isdigit():
        n = nugget_by_number(nuggets, num_str.zfill(3))
    return n


def _noop_warn(msg, filepath=None):
    pass


def parse_nugget(filepath, warn=None):
    """Parse a nugget .txt file into a dict. warn(msg, filepath=...) is called for non-fatal issues."""
    w = warn if warn is not None else _noop_warn
    text = filepath.read_text(encoding="utf-8")
    ctx = {"warn": w, "notes": [], "handlers": {}}
    text, notes = process_directives(text, filepath, ctx)
    lines = text.splitlines()

    meta = {}
    layers = {}
    refs = []
    terms = []
    current_layer = None
    buffer = []

    SINGLE_LINE = {"title", "subtitle", "status", "date", "tags", "category", "related"}

    def _ref_handler(verb, content, context):
        args = split_directive_args(content or "")
        if len(args) >= 2:
            kw, ref_text = args[0].strip(), args[1].strip()
        elif len(args) == 1:
            kw = args[0].strip()
            ref_text = kw
        else:
            return ""
        if kw and ref_text:
            refs.append((kw, ref_text))
        return ""

    def flush():
        if current_layer and current_layer not in SINGLE_LINE:
            full = "\n".join(buffer).strip()
            ctx = {"warn": w, "notes": notes, "handlers": {"ref": _ref_handler}}
            stripped, _ = process_directives(full, filepath, ctx)
            layers[current_layer] = stripped
        buffer.clear()

    for line in lines:
        if line.startswith("#"):
            parts = line[1:].split(None, 1)
            if not parts:
                continue
            key = parts[0].lower()
            value = parts[1] if len(parts) > 1 else ""

            if key == "ref":
                if current_layer in ("provenance", "brief"):
                    raw = value.strip()
                    if not raw:
                        continue
                    parts = raw.split(None, 1)
                    if len(parts) == 2 and parts[0].lower() == parts[0] and parts[0].replace("-", "").replace("_", "").isalnum():
                        keyword, ref_text = parts[0], parts[1]
                    else:
                        first_word = raw.split(None, 1)[0].rstrip(".,;")
                        keyword = re.sub(r"[^a-z0-9\-]", "", first_word.lower()) or first_word.lower()
                        ref_text = raw
                    refs.append((keyword, ref_text))
                else:
                    w("#ref only allowed in #provenance (found in or before {})".format(current_layer or "metadata"), filepath=filepath)
                continue
            if key == "term":
                raw = value.strip()
                if ": " in raw:
                    term_part, def_part = raw.split(": ", 1)
                    terms.append((term_part.strip(), def_part.strip()))
                else:
                    terms.append((raw, ""))
                continue
            elif key in SINGLE_LINE:
                flush()
                current_layer = None
                if key in meta:
                    w("duplicate #{}, keeping first value.".format(key), filepath=filepath)
                else:
                    if not value.strip() and key in ("title", "status", "date"):
                        w("#{} has no value on same line.".format(key), filepath=filepath)
                    meta[key] = value.strip()
            else:
                flush()
                if key in layers:
                    w("duplicate #{}, keeping first.".format(key), filepath=filepath)
                    current_layer = None
                    buffer = []
                else:
                    current_layer = key
                    buffer = []
        else:
            if current_layer is None and line.strip():
                current_layer = "brief"
                buffer = [line]
            elif current_layer not in SINGLE_LINE:
                buffer.append(line)

    flush()

    meta["tags"] = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
    meta["category"] = meta.get("category", "").strip() or (meta["tags"][0] if meta["tags"] else "")
    raw_related = [r.strip() for r in meta.get("related", "").split(",") if r.strip()]
    related_parsed = []
    for r in raw_related:
        if re.match(r"^\d+$", r):
            related_parsed.append(r)
        else:
            w("related entry {!r} is not a valid nugget number (digits only).".format(r), filepath=filepath)
            m = re.match(r"^(\d+)", r)
            if m:
                related_parsed.append(m.group(1))
    meta["related"] = related_parsed
    meta["refs"] = refs
    meta["terms"] = terms
    meta["notes"] = notes

    meta["layers"] = {
        "surface": layers.get("surface", "TBD"),
        "depth": layers.get("depth", "TBD"),
        "provenance": layers.get("provenance", "TBD"),
        "script": layers.get("script", "TBD"),
        "images": layers.get("images", "TBD"),
        "brief": layers.get("brief", "TBD"),
    }

    stem = filepath.stem
    if "-" in stem:
        meta["number"] = stem.split("-", 1)[0]
        meta["shortname"] = stem.split("-", 1)[1]
    else:
        meta["number"] = ""
        meta["shortname"] = ""

    return meta


def load_all_nuggets(warn=None):
    """Load and parse all nugget .txt files from NUGGETS_DIR. warn(msg, filepath=...) for parse issues."""
    def default_warn(msg, filepath=None):
        print(msg, file=sys.stderr)
    w = warn if warn is not None else default_warn
    nuggets = []
    for f in sorted(NUGGETS_DIR.glob("*.txt")):
        try:
            n = parse_nugget(f, warn=w)
            n["filename"] = f.stem
            nuggets.append(n)
        except Exception as e:
            w("could not parse: {}".format(e), filepath=f)
    return nuggets


def nugget_by_number(nuggets, num):
    for n in nuggets:
        if n.get("number") == num:
            return n
    return None


def expand_nugget_directives(text, all_nuggets):
    """Replace @nugget(NNN) with italicized title link to that nugget. Unknown numbers left as-is."""
    def repl(m):
        num_str = m.group(1)
        n = nugget_by_number_flex(all_nuggets, num_str)
        if n is None:
            return m.group(0)
        title = n.get("title", "Untitled")
        filename = n.get("filename", "")
        return f'<em><a href="{filename}.html">{_html.escape(title)}</a></em>'
    return re.sub(r"@(?:nugget|pod|link)\((\d+)\)", repl, text)
