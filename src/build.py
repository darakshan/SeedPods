#!/usr/bin/env python3
"""
build.py — SeedPods site generator
Reads from content/ and config/; writes to site_dir (e.g. docs/).
Run with --help to see all flags.
"""

import argparse
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
from md_pages import process_md_to_html, expand_includes
from site_paths import content_path_to_output_name

from reporter import error as reporter_error, has_errors, note as reporter_note, note_count as reporter_note_count, print_all, reset as reporter_reset, warning as reporter_warning
from category_colors import build_category_css, load_category_colors
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
BUILD_STATE_DIR = _ROOT / ".buildstate"
STATE_FILE = BUILD_STATE_DIR / "state.json"
HISTORY_CSV = BUILD_STATE_DIR / "history.csv"
RELEASE_VERSION = 0

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
        j = i + 9
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
        for m in re.finditer(r"@link\s*\(\s*([^,)]+)\s*[,)]", text):
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


def _hash_paths(paths):
    """SHA-256 of sorted path strings and their file contents. Paths are Path objects; missing files are skipped."""
    h = hashlib.sha256()
    for p in sorted(paths, key=lambda x: str(x)):
        if p.is_file():
            h.update(str(p).encode("utf-8"))
            h.update(p.read_bytes())
    return h.hexdigest()


def _shared_md_inputs(index_copy, status_order, explainer_terms):
    """Inputs shared by index and all MD pages that use placeholders: settings, status, explainers, all nugget .txt."""
    out = set()
    out.add(CONFIG_DIR / "settings.txt")
    if (CONFIG_DIR / "status.txt").exists():
        out.add(CONFIG_DIR / "status.txt")
    if EXPLAINERS_CSV.exists():
        out.add(EXPLAINERS_CSV)
    cats_json = CONFIG_DIR / "categories.json"
    if cats_json.exists():
        out.add(cats_json)
    out.update((_ROOT / "src").glob("*.py"))
    return out


def _get_all_page_ids(nuggets, index_copy, collected_md_refs):
    """All HTML page IDs (output filenames) that the build produces."""
    ids = ["index.html"]
    for n in nuggets:
        ids.append(nugget_tag(n) + ".html")
    nav_hrefs = {href for href, _, _, _ in get_nav_items(index_copy)}
    nav_built_paths = set()
    for _href, _label, kind, path in get_nav_items(index_copy):
        if kind == "file" and path:
            nav_built_paths.add(path.resolve())
        elif kind == "dir" and path:
            nav_built_paths.add((path / "page.md").resolve())
    for _label, list_href, list_path in get_list_menu_items(index_copy):
        if list_path and list_path.resolve() not in nav_built_paths:
            nav_hrefs.add(list_href)
        elif list_path:
            nav_hrefs.add(list_href)
    ids.extend(sorted(nav_hrefs))
    ids.append("internal.html")
    for md_path in sorted(collected_md_refs, key=lambda p: str(p)):
        out_name = content_path_to_output_name(md_path, CONTENT_DIR)
        if out_name and out_name not in ids:
            ids.append(out_name)
    return ids


def _get_inputs_for_page(page_id, nuggets, index_copy, status_order, explainer_terms, collected_md_refs):
    """Set of input Paths whose content affects this page. Used for input-based hashing."""
    out = set()
    if page_id == "index.html":
        home = CONTENT_DIR / "home.md"
        out.update(_input_files_for_page(home))
        for n in nuggets:
            out.add(NUGGETS_DIR / (n.get("filename", "") + ".txt"))
        out.update(_shared_md_inputs(index_copy, status_order, explainer_terms))
        return out
    if page_id.endswith(".html") and page_id != "internal.html" and page_id != "index.html":
        slug = page_id[:-5]
        nugget_file = None
        for n in nuggets:
            if nugget_tag(n) == slug:
                nugget_file = NUGGETS_DIR / (n.get("filename", "") + ".txt")
                break
        if nugget_file and nugget_file.exists():
            out.add(nugget_file)
            raw = nugget_file.read_text(encoding="utf-8")
            for name in _image_refs_in_text(raw):
                if name and ".." not in name and "/" not in name and "\\" not in name:
                    images_dir = CONTENT_DIR / "images"
                    for ext in _IMAGE_EXTS:
                        p = images_dir / (name + ext)
                        if p.is_file():
                            out.add(p)
                            break
            cats_json = CONFIG_DIR / "categories.json"
            if cats_json.exists():
                out.add(cats_json)
            sorted_nuggets = sorted(nuggets, key=lambda x: x.get("number", ""))
            idx = next((i for i, x in enumerate(sorted_nuggets) if nugget_tag(x) == slug), -1)
            if idx > 0:
                prev_f = NUGGETS_DIR / (sorted_nuggets[idx - 1].get("filename", "") + ".txt")
                out.add(prev_f)
            if 0 <= idx < len(sorted_nuggets) - 1:
                next_f = NUGGETS_DIR / (sorted_nuggets[idx + 1].get("filename", "") + ".txt")
                out.add(next_f)
            return out
    if page_id == "internal.html":
        internal_md = INTERNAL_DIR / "page.md"
        out.update(_input_files_for_page(internal_md))
        base_dir = internal_md.parent.resolve()
        text = expand_includes(internal_md.read_text(encoding="utf-8"), base_dir, filepath=internal_md)
        for m in re.finditer(r"@link\s*\(\s*([^,)]+)\s*[,)]", text):
            loc = m.group(1).strip()
            if not re.match(r"^\d+$", loc) and ".md" in loc:
                p = (base_dir / loc).resolve()
                try:
                    p.relative_to(CONTENT_DIR.resolve())
                except ValueError:
                    pass
                if p.exists():
                    out.add(p)
        for n in nuggets:
            out.add(NUGGETS_DIR / (n.get("filename", "") + ".txt"))
        out.update(_shared_md_inputs(index_copy, status_order, explainer_terms))
        return out
    md_path = None
    for _href, _label, kind, path in get_nav_items(index_copy):
        if (kind == "file" and path and _href == page_id) or (kind == "dir" and path and _href == page_id):
            md_path = path if kind == "file" else path / "page.md"
            break
    if md_path is None:
        for _label, list_href, list_path in get_list_menu_items(index_copy):
            if list_href == page_id and list_path:
                md_path = list_path
                break
    if md_path is not None:
        md_path = Path(md_path).resolve()
        if md_path.suffix != ".md":
            md_path = md_path / "page.md"
        out.update(_input_files_for_page(md_path))
        refs = set()
        to_scan = [md_path]
        while to_scan:
            p = to_scan.pop(0)
            if not p.exists():
                continue
            text = expand_includes(p.read_text(encoding="utf-8"), p.parent, filepath=p) if p.suffix == ".md" else ""
            base_dir = p.parent.resolve()
            for m in re.finditer(r"@link\s*\(\s*([^,)]+)\s*[,)]", text):
                loc = m.group(1).strip()
                if not re.match(r"^\d+$", loc) and ".md" in loc:
                    link_path = (base_dir / loc).resolve()
                    try:
                        link_path.relative_to(CONTENT_DIR.resolve())
                    except ValueError:
                        continue
                    if link_path.exists() and link_path not in refs:
                        refs.add(link_path)
                        to_scan.append(link_path)
        out.update(refs)
        for n in nuggets:
            out.add(NUGGETS_DIR / (n.get("filename", "") + ".txt"))
        out.update(_shared_md_inputs(index_copy, status_order, explainer_terms))
        return out
    for md_path in collected_md_refs:
        md_path = Path(md_path).resolve()
        out_name = content_path_to_output_name(md_path, CONTENT_DIR)
        if out_name == page_id:
            out.update(_input_files_for_page(md_path))
            refs = set()
            to_scan = [md_path]
            while to_scan:
                p = to_scan.pop(0)
                if not p.exists():
                    continue
                text = expand_includes(p.read_text(encoding="utf-8"), p.parent, filepath=p) if p.suffix == ".md" else ""
                base_dir = p.parent.resolve()
                for m in re.finditer(r"@link\s*\(\s*([^,)]+)\s*[,)]", text):
                    loc = m.group(1).strip()
                    if not re.match(r"^\d+$", loc) and ".md" in loc:
                        link_path = (base_dir / loc).resolve()
                        try:
                            link_path.relative_to(CONTENT_DIR.resolve())
                        except ValueError:
                            continue
                        if link_path.exists() and link_path not in refs:
                            refs.add(link_path)
                            to_scan.append(link_path)
            out.update(refs)
            for n in nuggets:
                out.add(NUGGETS_DIR / (n.get("filename", "") + ".txt"))
            out.update(_shared_md_inputs(index_copy, status_order, explainer_terms))
            break
    return out


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

_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def _image_refs_in_text(text):
    """Return set of @image(file, ...) file names (first comma-separated arg) found in text."""
    out = set()
    for m in re.finditer(r"@image\s*\(\s*([^)]+)\s*\)", text):
        args = [s.strip() for s in m.group(1).split(",")]
        if args:
            out.add(args[0])
    return out


def _content_files_used_in_build(nuggets, index_copy, collected_md_refs):
    """Set of content paths that contribute to the built site (nugget .txt, main MD pages, nav/list MD, linked MD)."""
    used = set()
    for main in _get_md_page_paths():
        if main.exists():
            used.add(main.resolve())
    for n in nuggets:
        used.add((NUGGETS_DIR / (n.get("filename", "") + ".txt")).resolve())
    for _href, _label, kind, path in get_nav_items(index_copy):
        if path:
            if kind == "file":
                used.add(path.resolve())
            elif kind == "dir":
                used.add((path / "page.md").resolve())
    for _label, _list_href, list_path in get_list_menu_items(index_copy):
        if list_path:
            used.add(list_path.resolve())
    for p in collected_md_refs:
        used.add(Path(p).resolve())
    image_names = set()
    for n in nuggets:
        raw = (NUGGETS_DIR / (n.get("filename", "") + ".txt")).read_text(encoding="utf-8")
        image_names |= _image_refs_in_text(raw)
    for md_path in _get_md_page_paths():
        if md_path.exists():
            image_names |= _image_refs_in_text(md_path.read_text(encoding="utf-8"))
    images_dir = CONTENT_DIR / "images"
    for name in image_names:
        if not name or ".." in name or "/" in name or "\\" in name:
            continue
        for ext in _IMAGE_EXTS:
            p = images_dir / (name + ext)
            if p.is_file():
                used.add(p.resolve())
                break
    return used


def _warn_content_not_in_docs(nuggets, index_copy, collected_md_refs):
    """If any file under content/ is not used in the build, record a warning. Does not affect exit code."""
    all_content = {p.resolve() for p in CONTENT_DIR.rglob("*") if p.is_file() and p.name != ".DS_Store"}
    used = _content_files_used_in_build(nuggets, index_copy, collected_md_refs)
    missed = sorted(all_content - used, key=lambda p: str(p))
    for p in missed:
        try:
            rel = p.relative_to(CONTENT_DIR)
        except ValueError:
            rel = p
        reporter_warning("content file not used in build", path=p)

def _require_status_order():
    order = load_status_order()
    if not order:
        reporter_error("Required file missing: config/status.txt")
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


def _nugget_summary_text(n):
    """Essential plain text for one nugget: title, subtitle, and main prose without HTML or #-directives."""
    num = display_number(n.get("number", "?"))
    title = n.get("title", "") or "Untitled"
    subtitle = n.get("subtitle", "") or ""
    layers = n.get("layers") or {}
    prose = layers.get("surface") or layers.get("brief") or ""
    if prose and not section_is_tbd(prose):
        lines = []
        for line in prose.splitlines():
            s = line.strip()
            if s.startswith("#"):
                continue
            lines.append(re.sub(r"@nugget\((\d+)\)", lambda m: "Pod " + display_number(m.group(1)), s))
        prose = "\n".join(lines).strip()
    else:
        prose = ""
    block = f"Seed {num}. {title}\n{subtitle}".strip()
    if prose:
        block += "\n\n" + prose
    return block


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
    """Write 4u-ai.txt into site_dir from internal docs and a summary of all nuggets (essential text, no HTML)."""
    parts = [internal_str, "=== Pod summaries ===\n"]
    for n in sorted(nuggets, key=lambda x: (x.get("number", "").zfill(3), x.get("number", ""))):
        slug = nugget_tag(n)
        parts.append(f"--- {slug} ---\n\n{_nugget_summary_text(n)}")
    (SITE_DIR / "4u-ai.txt").write_text("\n\n".join(parts), encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────

def _append_history(page_name, build_version, page_version, release_version=0, changed_in_build=None):
    BUILD_STATE_DIR.mkdir(parents=True, exist_ok=True)
    need_header = not HISTORY_CSV.exists()
    with open(HISTORY_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if need_header:
            w.writerow(["date", "build_version", "page_version", "page_name", "release_version", "changed_in_build"])
        w.writerow([datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(), build_version, page_version, page_name, release_version, changed_in_build if changed_in_build is not None else build_version])


def main():
    global BUILD_TIME, SITE_DIR
    parser = argparse.ArgumentParser(description="SeedPods site generator")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print each built file")
    parser.add_argument("--force", action="store_true", help="Rebuild all pages even when unchanged")
    parser.add_argument("-n", "--notes", action="store_true", help="Show @note contents")
    args = parser.parse_args()
    verbose = args.verbose
    force = args.force
    show_notes = args.notes

    reporter_reset()
    index_copy = load_index_copy()
    site_dir = (index_copy.get("site_dir") or "").strip()
    if not site_dir:
        reporter_error("config/settings.txt must set site_dir")
        print_all()
        sys.exit(1)
    SITE_DIR = _ROOT / site_dir

    state = {"build_version": 0, "pages": {}, "last_build_time": None}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, TypeError):
            pass

    def _warn_cb(msg, filepath=None):
        reporter_warning(msg, path=filepath)
    nuggets = load_all_nuggets(warn=_warn_cb)
    status_order = _require_status_order()
    explainer_terms = load_explainers_csv(EXPLAINERS_CSV) if EXPLAINERS_CSV.exists() else []
    collected_md_refs = _referenced_md_from_md_pages()
    all_page_ids = _get_all_page_ids(nuggets, index_copy, collected_md_refs)

    page_hashes = {}
    page_versions = {}
    for page_id in all_page_ids:
        inputs = _get_inputs_for_page(page_id, nuggets, index_copy, status_order, explainer_terms, collected_md_refs)
        new_hash = _hash_paths(inputs)
        page_hashes[page_id] = new_hash
        old = state.get("pages", {}).get(page_id, {})
        old_ver = old.get("page_version", 0)
        changed = new_hash != old.get("hash") or page_id not in state.get("pages", {})
        page_versions[page_id] = old_ver + 1 if changed else old_ver

    changed_set = {pid for pid in all_page_ids if page_hashes[pid] != state.get("pages", {}).get(pid, {}).get("hash") or pid not in state.get("pages", {})}
    if force:
        changed_set = set(all_page_ids)
    if changed_set:
        build_version = state.get("build_version", 0) + 1
        last_build_time = datetime.now(ZoneInfo("America/Los_Angeles"))
    else:
        build_version = state.get("build_version", 0)
        try:
            last_build_time = datetime.fromisoformat(state["last_build_time"]) if state.get("last_build_time") else None
        except (ValueError, TypeError):
            last_build_time = None
        last_build_time = last_build_time or datetime.now(ZoneInfo("America/Los_Angeles"))
    BUILD_TIME = last_build_time

    page_changed_in_builds = {}
    page_changed_times = {}
    for page_id in all_page_ids:
        old = state.get("pages", {}).get(page_id, {})
        if page_id in changed_set:
            page_changed_in_builds[page_id] = build_version
            page_changed_times[page_id] = BUILD_TIME
        else:
            page_changed_in_builds[page_id] = old.get("changed_in_build", build_version)
            try:
                t = datetime.fromisoformat(old["changed_time"]) if old.get("changed_time") else None
            except (ValueError, TypeError):
                t = None
            page_changed_times[page_id] = t or BUILD_TIME

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    if BUILD_STATE_DIR.exists() and BUILD_STATE_DIR.is_file():
        BUILD_STATE_DIR.unlink()
    BUILD_STATE_DIR.mkdir(parents=True, exist_ok=True)
    nugget_revisions = {nugget_tag(n): page_versions.get(nugget_tag(n) + ".html", 0) for n in nuggets}
    set_build_context(warn=_warn_cb, build_time_=BUILD_TIME, build_version_=build_version, nugget_revisions_=nugget_revisions)
    print(f"Loaded {len(nuggets)} pods")

    for n in nuggets:
        fn = n.get("filename", "?")
        shortname = fn.split("-", 1)[-1] if "-" in fn else None
        for note in n.get("notes", []):
            reporter_note(note, nugget_num=n.get("number"), shortname=shortname)
    seen_num = {}
    duplicate_nums = []
    for n in nuggets:
        num = n.get("number")
        if num:
            if num in seen_num:
                duplicate_nums.append((num, seen_num[num], n.get("filename")))
            else:
                seen_num[num] = n.get("filename")
    for num, a, b in duplicate_nums:
        reporter_error("Duplicate pod number {}: {}.txt and {}.txt".format(num, a, b))

    for md_path in _get_md_page_paths():
        if not md_path.exists():
            reporter_error("Required file missing", path=md_path)
    for n in nuggets:
        s = n.get("status", "empty")
        if s not in status_order:
            fn = n.get("filename") or ""
            shortname = fn.split("-", 1)[-1] if "-" in fn else None
            reporter_error("status {!r} not in config/status.txt".format(s), nugget_num=n.get("number"), shortname=shortname)

    link_errors = []
    built_count = 0
    for n in nuggets:
        fname = nugget_tag(n) + ".html"
        if fname in changed_set:
            set_build_context(page_version_=page_versions[fname], changed_in_build_=page_changed_in_builds[fname], changed_time_=page_changed_times[fname])
            (SITE_DIR / fname).write_text(build_nugget(n, nuggets, link_errors, site_dir=SITE_DIR), encoding="utf-8")
            built_count += 1
            if verbose:
                print(f"  Built {fname}")
            _append_history(fname, build_version, page_versions[fname], RELEASE_VERSION, changed_in_build=page_changed_in_builds[fname])

    internal_str, nugget_raw_by_slug = _collect_4u_ai_content(nuggets)
    if changed_set or not (SITE_DIR / "nugget-index.json").exists():
        (SITE_DIR / "nugget-index.json").write_text(build_nugget_index_json(nuggets), encoding="utf-8")
        (SITE_DIR / "search-index.json").write_text(build_search_index_json(nuggets, nugget_raw_by_slug), encoding="utf-8")
        (SITE_DIR / "seed-nav.js").write_text(nav_seed_script_content(), encoding="utf-8")
        built_count += 3
        if verbose:
            print("  Built nugget-index.json, search-index.json, seed-nav.js")

    if changed_set or not (SITE_DIR / "site.css").exists():
        css_text = (CONFIG_DIR / "site.css").read_text(encoding="utf-8")
        extra_css = build_category_css(load_category_colors())
        if extra_css:
            css_text += "\n" + extra_css
        (SITE_DIR / "site.css").write_text(css_text, encoding="utf-8")
        built_count += 1
        if verbose:
            print("  Built site.css")
    if (CONFIG_DIR / "logo.svg").exists() and (changed_set or not (SITE_DIR / "logo.svg").exists()):
        shutil.copy(CONFIG_DIR / "logo.svg", SITE_DIR / "logo.svg")
        built_count += 1
        if verbose:
            print("  Built logo.svg")

    nav_items = get_nav_items(index_copy)
    nav_built_paths = set()
    for href, label, kind, path in nav_items:
        if kind == "file":
            nav_built_paths.add(path.resolve())
            if href in changed_set:
                set_build_context(page_version_=page_versions[href], changed_in_build_=page_changed_in_builds[href], changed_time_=page_changed_times[href])
                (SITE_DIR / href).write_text(
                    build_md_file_page(path, nuggets, collected_md_refs, status_order, index_copy, explainer_terms, link_errors, wrap_class="wrap--full" if href == "map.html" else ""),
                    encoding="utf-8",
                )
                built_count += 1
                if verbose:
                    print(f"  Built {href}")
                _append_history(href, build_version, page_versions[href], RELEASE_VERSION, changed_in_build=page_changed_in_builds[href])
        elif kind == "dir":
            nav_built_paths.add((path / "page.md").resolve())
            if href in changed_set:
                set_build_context(page_version_=page_versions[href], changed_in_build_=page_changed_in_builds[href], changed_time_=page_changed_times[href])
                (SITE_DIR / href).write_text(build_md_dir_page(path, nuggets, collected_md_refs, status_order, explainer_terms, link_errors), encoding="utf-8")
                built_count += 1
                if verbose:
                    print(f"  Built {href}")
                _append_history(href, build_version, page_versions[href], RELEASE_VERSION, changed_in_build=page_changed_in_builds[href])

    for _label, list_href, list_path in get_list_menu_items(index_copy):
        if list_path and list_path.resolve() not in nav_built_paths and list_href in changed_set:
            set_build_context(page_version_=page_versions[list_href], changed_in_build_=page_changed_in_builds[list_href], changed_time_=page_changed_times[list_href])
            (SITE_DIR / list_href).write_text(
                build_md_file_page(list_path, nuggets, collected_md_refs, status_order, index_copy, explainer_terms, link_errors, wrap_class="wrap--full" if list_href == "map.html" else ""),
                encoding="utf-8",
            )
            built_count += 1
            if verbose:
                print(f"  Built {list_href}")
            _append_history(list_href, build_version, page_versions[list_href], RELEASE_VERSION, changed_in_build=page_changed_in_builds[list_href])

    if "internal.html" in changed_set:
        set_build_context(page_version_=page_versions["internal.html"], changed_in_build_=page_changed_in_builds["internal.html"], changed_time_=page_changed_times["internal.html"])
        (SITE_DIR / "internal.html").write_text(build_internal_page(nuggets, collected_md_refs, link_errors), encoding="utf-8")
        built_count += 1
        if verbose:
            print("  Built internal.html")
        _append_history("internal.html", build_version, page_versions["internal.html"], RELEASE_VERSION, changed_in_build=page_changed_in_builds["internal.html"])

    built_md_refs = set()
    to_build = list(collected_md_refs)
    while to_build:
        md_path = to_build.pop(0)
        if md_path in built_md_refs:
            continue
        built_md_refs.add(md_path)
        out_name = content_path_to_output_name(md_path, CONTENT_DIR)
        if out_name and out_name in changed_set:
            set_build_context(page_version_=page_versions[out_name], changed_in_build_=page_changed_in_builds[out_name], changed_time_=page_changed_times[out_name])
            body_html = process_md_to_html(md_path, _md_context_with_special(nuggets, status_order, explainer_terms, link_errors=link_errors), collected_md_refs)
            title = md_path.stem.replace("nugget", "pod").replace("-", " ").title()
            (SITE_DIR / out_name).write_text(build_static_page(title, body_html), encoding="utf-8")
            built_count += 1
            if verbose:
                print(f"  Built {out_name}")
            _append_history(out_name, build_version, page_versions[out_name], RELEASE_VERSION, changed_in_build=page_changed_in_builds[out_name])
        for p in collected_md_refs - built_md_refs:
            if p not in to_build:
                to_build.append(p)

    for stale in ["index.html", "favicon.svg"]:
        p = _ROOT / stale
        if p.exists():
            p.unlink()
    if "index.html" in changed_set:
        set_build_context(page_version_=page_versions["index.html"], changed_in_build_=page_changed_in_builds["index.html"], changed_time_=page_changed_times["index.html"])
        (SITE_DIR / "index.html").write_text(build_index(nuggets, index_copy, status_order, collected_md_refs, link_errors), encoding="utf-8")
        built_count += 1
        if verbose:
            print("  Built index.html")
        _append_history("index.html", build_version, page_versions["index.html"], RELEASE_VERSION, changed_in_build=page_changed_in_builds["index.html"])
    if (CONFIG_DIR / "logo.svg").exists() and (changed_set or not (SITE_DIR / "favicon.svg").exists()):
        shutil.copy(CONFIG_DIR / "logo.svg", SITE_DIR / "favicon.svg")
        built_count += 1
        if verbose:
            print("  Built favicon.svg")

    if changed_set or not (SITE_DIR / "map.svg").exists():
        (SITE_DIR / "map.svg").write_text(build_graph_svg(nuggets, show_title=False, link_nuggets=True, node_radius=40), encoding="utf-8")
        built_count += 1
        if verbose:
            print("  Built map.svg")

    if changed_set or not (SITE_DIR / "4u-ai.txt").exists():
        build_4u_ai_txt(internal_str, nuggets, nugget_raw_by_slug)
        built_count += 1
        if verbose:
            print("  Built 4u-ai.txt")

    state["build_version"] = build_version
    state["last_build_time"] = BUILD_TIME.isoformat()
    state["pages"] = {pid: {"hash": page_hashes[pid], "page_version": page_versions[pid], "changed_in_build": page_changed_in_builds[pid], "changed_time": page_changed_times[pid].isoformat()} for pid in all_page_ids}
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

    _warn_content_not_in_docs(nuggets, index_copy, collected_md_refs)

    if not changed_set:
        print("Nothing changed.")
    else:
        if not verbose:
            print(f"Built {built_count} files\n")
    for msg in link_errors:
        reporter_error(msg)
    sys.stdout.flush()
    print_all(show_notes=show_notes)
    n = reporter_note_count()
    if n:
        note_word = "note" if n == 1 else "notes"
        suffix = "" if show_notes else " (use -n to show)"
        print(f"{n} {note_word}{suffix}", file=sys.stderr)
    print(f"\nDone. Site written to {SITE_DIR.relative_to(_ROOT)}/ (web root)")
    if has_errors():
        sys.exit(1)

if __name__ == "__main__":
    main()
