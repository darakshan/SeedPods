"""
Parse nugget .txt files and provide load/lookup/expand helpers.
"""

import html as _html
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
NUGGETS_DIR = _ROOT / "nuggets"


def _noop_warn(msg):
    pass


def parse_nugget(filepath, warn=None):
    """Parse a nugget .txt file into a dict. warn(msg) is called for non-fatal issues."""
    w = warn if warn is not None else _noop_warn
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines()

    meta = {}
    layers = {}
    refs = []
    terms = []
    current_layer = None
    buffer = []

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

            if key == "ref":
                if current_layer == "provenance":
                    refs.append(value.strip())
                else:
                    w(f"Warning: {filepath}: #ref only allowed in #provenance (found in or before {current_layer or 'metadata'})")
                continue
            if key == "term":
                if current_layer == "provenance":
                    raw = value.strip()
                    if " — " in raw:
                        term_part, def_part = raw.split(" — ", 1)
                        terms.append((term_part.strip(), def_part.strip()))
                    else:
                        terms.append((raw, ""))
                else:
                    w(f"Warning: {filepath}: #term only allowed in #provenance (found in or before {current_layer or 'metadata'})")
                continue
            elif key in SINGLE_LINE:
                flush()
                current_layer = None
                if key in meta:
                    w(f"Warning: {filepath}: duplicate #{key}, keeping first value.")
                else:
                    if not value.strip():
                        w(f"Warning: {filepath}: #{key} has no value on same line.")
                    meta[key] = value.strip()
            else:
                flush()
                if key in layers:
                    w(f"Warning: {filepath}: duplicate #{key}, keeping first.")
                    current_layer = None
                    buffer = []
                else:
                    current_layer = key
                    buffer = []
        else:
            if current_layer and current_layer not in SINGLE_LINE:
                buffer.append(line)

    flush()

    meta["tags"] = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
    raw_related = [r.strip() for r in meta.get("related", "").split(",") if r.strip()]
    related_parsed = []
    for r in raw_related:
        if re.match(r"^\d+$", r):
            related_parsed.append(r)
        else:
            w(f"Warning: {filepath}: related entry {r!r} is not a valid nugget number (digits only).")
            m = re.match(r"^(\d+)", r)
            if m:
                related_parsed.append(m.group(1))
    meta["related"] = related_parsed
    meta["refs"] = refs
    meta["terms"] = terms

    meta["layers"] = {
        "surface": layers.get("surface", "TBD"),
        "depth": layers.get("depth", "TBD"),
        "provenance": layers.get("provenance", "TBD"),
        "script": layers.get("script", "TBD"),
        "images": layers.get("images", "TBD"),
    }

    stem = filepath.stem
    prefix = stem.split("-")[0] if "-" in stem else ""
    if prefix.isdigit() and meta.get("number") and meta["number"] != prefix:
        w(f"Warning: {filepath}: filename prefix {prefix} does not match #number {meta['number']}.")

    return meta


def load_all_nuggets(warn=None):
    """Load and parse all nugget .txt files from NUGGETS_DIR. warn(msg) for parse issues."""
    w = warn if warn is not None else (lambda msg: print(msg, file=sys.stderr))
    nuggets = []
    for f in sorted(NUGGETS_DIR.glob("*.txt")):
        try:
            n = parse_nugget(f, warn=w)
            n["filename"] = f.stem
            nuggets.append(n)
        except Exception as e:
            w(f"Warning: could not parse {f}: {e}")
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
        n = nugget_by_number(all_nuggets, num_str)
        if n is None and num_str.isdigit():
            n = nugget_by_number(all_nuggets, num_str.zfill(3))
        if n is None:
            return m.group(0)
        title = n.get("title", "Untitled")
        filename = n.get("filename", "")
        return f'<em><a href="{filename}.html">{_html.escape(title)}</a></em>'
    return re.sub(r"@nugget\((\d+)\)", repl, text)
