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
from directive import process_directives
from md_pages import process_md_to_html, expand_includes, expand_links
from site_paths import content_path_to_output_name

from builders import (
    build_bibliography_body,
    build_bibliography_page,
    build_explainers_page,
    build_glossary_body,
    build_glossary_page,
    build_index,
    build_internal_page,
    build_md_dir_page,
    build_md_file_page,
    build_map_graph_page,
    build_nugget,
    build_static_page,
    build_tags_body,
    build_tags_page,
    get_list_menu_items,
    get_nav_items,
    load_explainers_csv,
    nav_seed_script_content,
    set_build_context,
    _md_context_with_special,
)

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
    text = main_path.read_text(encoding="utf-8")
    i = 0
    while True:
        i = text.find("@include(", i)
        if i < 0:
            break
        depth = 1
        j = i + 8
        while j < len(text) and depth:
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
            j += 1
        if depth == 0:
            name = text[i + 9 : j - 1].strip()
            if name:
                inc_path = (base_dir / name).resolve()
                if str(inc_path).startswith(str(base_dir)) and inc_path.exists():
                    out.add(inc_path)
        i = j
    return out


def _referenced_md_from_md_pages():
    """Set of .md paths referenced via @link(locator, text) from main MD pages (transitive). Paths resolved relative to the file containing the link."""
    refs = set()
    to_scan = list(_get_md_page_paths())
    while to_scan:
        path = to_scan.pop(0)
        if not path.exists():
            continue
        text = expand_includes(path.read_text(encoding="utf-8"), path.parent, filepath=path) if path.suffix == ".md" else ""
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
    set_build_context(warn=_warn, build_time_=BUILD_TIME)
    print(f"Loaded {len(nuggets)} nuggets")
    for n in nuggets:
        for note in n.get("notes", []):
            rel = NUGGETS_DIR / (n.get("filename", "?") + ".txt")
            try:
                rel = rel.resolve().relative_to(_ROOT)
            except ValueError:
                pass
            print(f"\n{rel}: @note {note}")
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
    (SITE_DIR / "seed-nav.js").write_text(nav_seed_script_content(), encoding="utf-8")
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
