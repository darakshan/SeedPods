#!/usr/bin/env python3
"""
Import prototype nugget files into content/nuggets.
Reads .md files (e.g. content/more/primordia.md), splits into protonuggets.
Each protonugget must have #shortname in the source; if missing, report and skip (never write).
Writes .txt with #status proto; no #brief (proto implies single body).
Preview by default; use --apply to write files.
"""

import re
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = _ROOT / "content"
NUGGETS_DIR = CONTENT_DIR / "nuggets"

# Import after path is set
from nugget_parser import load_all_nuggets


def _next_number(existing_nums, used_in_run):
    all_used = set(existing_nums) | set(used_in_run)
    if not all_used:
        return "001"
    max_n = max(int(n) for n in all_used if n.isdigit())
    return str(max_n + 1).zfill(3)


def _unique_shortname(shortname, existing_shortnames, used_in_run):
    used = existing_shortnames | used_in_run
    cand = shortname
    i = 1
    while cand in used:
        cand = f"{shortname}-{i}"
        i += 1
    return cand


def parse_proto_file(path):
    """
    Split a proto .md file into protonuggets.
    Returns (file_level_refs, file_level_terms, list of {name, body, shortname}).
    shortname is from #shortname line in the block, or None if missing.
    - Ignores leading title/metadata before first ---
    - Splits on ---; each block: optional ## Category (skip), or ## N. Title / ### Title then body
    - Collects #ref and #term from anywhere (file-level) and returns separately
    """
    text = path.read_text(encoding="utf-8")
    refs = []
    terms = []
    blocks = re.split(r"\n---+\s*\n", text)
    nuggets = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        if not lines:
            continue
        first = lines[0].strip()
        numbered = re.match(r"^##\s+(\d+\.)\s*(.+)$", first)
        category = re.match(r"^##\s+([^#].*)$", first) and not numbered
        h3 = re.match(r"^###\s+(.+)$", first)
        if numbered:
            name = numbered.group(2).strip()
            body_lines = lines[1:]
        elif h3:
            name = h3.group(1).strip()
            body_lines = lines[1:]
        elif category:
            continue
        else:
            continue
        shortname = None
        body_parts = []
        for line in body_lines:
            stripped = line.strip()
            if stripped.startswith("#shortname "):
                shortname = stripped[10:].strip()
            elif stripped.startswith("#ref "):
                refs.append(stripped[4:].strip())
            elif stripped.startswith("#term "):
                raw = stripped[6:].strip()
                if ": " in raw:
                    term_part, def_part = raw.split(": ", 1)
                    terms.append((term_part.strip(), def_part.strip()))
                else:
                    terms.append((raw, ""))
            elif not (stripped.startswith("#links ") or stripped == "#links"):
                body_parts.append(line)
        body_clean = "\n".join(body_parts).strip()
        nuggets.append({"name": name, "body": body_clean, "shortname": shortname})
    return refs, terms, nuggets


def build_nugget_txt(number, shortname, name, body, refs, terms, date, subtitle="", tags="", related=""):
    parts = [f"#title {name}", "#status proto", f"#date {date}"]
    if subtitle:
        parts.append(f"#subtitle {subtitle}")
    if tags:
        parts.append(f"#tags {tags}")
    if related:
        parts.append(f"#related {related}")
    parts.extend(["", body.strip()])
    for t in terms:
        if t[1]:
            parts.append(f"#term {t[0]}: {t[1]}")
        else:
            parts.append(f"#term {t[0]}")
    for r in refs:
        parts.append(f"#ref {r}")
    return "\n".join(parts) + "\n"


def run(files, apply=False):
    existing = load_all_nuggets(warn=lambda msg, filepath=None: None)
    existing_nums = {n.get("number") for n in existing if n.get("number")}
    existing_shortnames = {n.get("shortname", "") for n in existing if n.get("shortname")}
    used_shortnames_in_run = set()
    used_nums_in_run = []
    rows = []

    for path in files:
        path = Path(path).resolve()
        if not path.exists():
            print(f"Skip (not found): {path}", file=sys.stderr)
            continue
        refs, terms, nuggets = parse_proto_file(path)
        if not nuggets:
            print(f"Skip (no protonuggets): {path}", file=sys.stderr)
            continue
        for n in nuggets:
            if n.get("shortname") is None or not n["shortname"].strip():
                print(f"shortname missing for: {n['name']}", file=sys.stderr)
                continue
            shortname = n["shortname"].strip()
            shortname = _unique_shortname(shortname, existing_shortnames, used_shortnames_in_run)
            used_shortnames_in_run.add(shortname)
            num = _next_number(existing_nums, used_nums_in_run)
            used_nums_in_run.append(num)
            date = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")
            ntags = 0
            nrelated = 0
            nwords = len(n["body"].split()) if n["body"] else 0
            content = build_nugget_txt(num, shortname, n["name"], n["body"], refs, terms, date)
            filename = f"{num}-{shortname}.txt"
            out_path = NUGGETS_DIR / filename
            rows.append((f"{num}-{shortname}", nwords, ntags, nrelated, n["name"]))
            if apply:
                NUGGETS_DIR.mkdir(parents=True, exist_ok=True)
                out_path.write_text(content, encoding="utf-8")
            existing_nums.add(num)
            existing_shortnames.add(shortname)

    if rows:
        col0 = max(len(r[0]) for r in rows)
        col1 = max(len(str(r[1])) for r in rows)
        col2 = max(len(str(r[2])) for r in rows)
        col3 = max(len(str(r[3])) for r in rows)
        col0 = max(col0, len("shortname-number"))
        col1 = max(col1, len("#words"))
        col2 = max(col2, len("#tags"))
        col3 = max(col3, len("#related"))
        fmt = f"{{:<{col0}}}  {{:>{col1}}}  {{:>{col2}}}  {{:>{col3}}}  {{}}"
        print(fmt.format("shortname-number", "#words", "#tags", "#related", "title"))
        print(fmt.format("-" * col0, "-" * col1, "-" * col2, "-" * col3, "-" * 40))
        for r in rows:
            print(fmt.format(r[0], r[1], r[2], r[3], r[4]))


def main():
    args = list(sys.argv[1:])
    apply = "--apply" in args
    if apply:
        args.remove("--apply")
    if not args:
        print("Usage: import_proto.py [--apply] <file.md> ...", file=sys.stderr)
        sys.exit(1)
    run(args, apply=apply)


if __name__ == "__main__":
    main()
