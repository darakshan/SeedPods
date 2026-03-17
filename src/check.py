#!/usr/bin/env python3
"""
check.py — Review nuggets for structure guidelines.
- Surface/depth word counts vs config/settings.txt limits
- Every nugget pointed to by at least min_related_in_degree others (#related)
- Underlinked: nuggets with 0 #related
- #related max 5
- Report @note directives (editorial comments; removed from content, printed at build time)
- Status vs sections (surface, depth, script, images; provenance ignored): section counts and valid statuses from config/status.txt; word count for statuses from top of config up through last draft*

Usage:
  python src/check.py              # summary + detailed findings (all nuggets)
  python src/check.py -q            # summary only
  python src/check.py -v            # summary + details + notes (interleaved by nugget)
  python src/check.py 3             # check only 003, show notes (implies -v)
  python src/check.py 3 4 19 99     # check 003, 004, 019; warn 99 missing
"""

import sys

from reporter import error as reporter_error, has_errors, print_all, reset as reporter_reset, warning as reporter_warning
from nugget_parser import (
    load_all_nuggets,
    load_index_copy,
    load_status_order,
    section_is_tbd,
)

PRIMARY_CATEGORIES = frozenset({
    "consciousness", "sensation", "physics", "mathematics", "biology", "mind-AI", "knowledge",
})


def _word_count(text):
    if not text or section_is_tbd(text):
        return 0
    return len(text.split())


def load_index_params():
    out = {
        "surface_min_words": 400,
        "surface_max_words": 700,
        "depth_min_words": 300,
        "depth_max_words": 600,
        "min_related_in_degree": 2,
    }
    copy = load_index_copy()
    for key in ("surface_min_words", "surface_max_words", "depth_min_words", "depth_max_words", "min_related_in_degree"):
        if key in copy:
            try:
                out[key] = int(copy[key])
            except ValueError:
                pass
    return out


def _complete_statuses(status_order):
    """Statuses that mean 'has all 4 sections': first two in config."""
    if not status_order:
        return set()
    return set(status_order[:2])


def _run_word_count_statuses(status_order):
    """Statuses that get surface/depth word-count checks: from top of config up through last draft*."""
    if not status_order:
        return set()
    last_draft_i = -1
    for i, s in enumerate(status_order):
        if s.startswith("draft"):
            last_draft_i = i
    if last_draft_i < 0:
        return set()
    return set(status_order[: last_draft_i + 1])


def _run_other_limits(status, status_order):
    """True if nugget gets in-degree and #related checks (complete but maybe rough)."""
    complete = _complete_statuses(status_order)
    return status in complete


def main():
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    quiet = "-q" in sys.argv or "--quiet" in sys.argv
    args = [a for a in sys.argv[1:] if a not in ("-v", "--verbose", "-q", "--quiet")]
    nugget_filter = None
    if args and all(a.isdigit() for a in args):
        nugget_filter = set(a.zfill(3) for a in args)
        verbose = True

    reporter_reset()
    params = load_index_params()
    nuggets = load_all_nuggets(warn=lambda msg, filepath=None: None)
    status_order = load_status_order()
    all_numbers = set(n.get("number", "") for n in nuggets if n.get("number"))
    if nugget_filter:
        for a in args:
            n = a.zfill(3)
            if n not in all_numbers:
                reporter_error("no such nugget", nugget_num=n)
        nuggets_to_check = [n for n in nuggets if n.get("number") in nugget_filter]
    else:
        nuggets_to_check = nuggets

    errors = []
    in_degree = {}
    for n in nuggets:
        num = n.get("number", "")
        if num:
            in_degree[num] = in_degree.get(num, 0)
        for r in n.get("related", []):
            in_degree[r] = in_degree.get(r, 0) + 1

    for n in nuggets_to_check:
        num = n.get("number", "?")
        fn = n.get("filename", "?")
        layers = n.get("layers", {})
        status = n.get("status", "")

        surface = layers.get("surface", "TBD")
        depth = layers.get("depth", "TBD")
        s_words = _word_count(surface)
        d_words = _word_count(depth)
        run_word_count = status in _run_word_count_statuses(status_order)
        run_limits = _run_other_limits(status, status_order)
        shortname = fn.split("-", 1)[-1] if "-" in fn else None

        if run_word_count and not section_is_tbd(surface):
            lo, hi = params["surface_min_words"], params["surface_max_words"]
            if s_words < lo:
                msg = "surface has {} words (min {})".format(s_words, lo)
                errors.append(("length", msg))
                reporter_error(msg, nugget_num=num, shortname=shortname)
            elif s_words > hi:
                msg = "surface has {} words (max {})".format(s_words, hi)
                errors.append(("length", msg))
                reporter_error(msg, nugget_num=num, shortname=shortname)

        if run_word_count and not section_is_tbd(depth):
            lo, hi = params["depth_min_words"], params["depth_max_words"]
            if d_words < lo:
                msg = "depth has {} words (min {})".format(d_words, lo)
                errors.append(("length", msg))
                reporter_error(msg, nugget_num=num, shortname=shortname)
            elif d_words > hi:
                msg = "depth has {} words (max {})".format(d_words, hi)
                errors.append(("length", msg))
                reporter_error(msg, nugget_num=num, shortname=shortname)

        if run_limits:
            degree = in_degree.get(num, 0)
            min_deg = params["min_related_in_degree"]
            if degree < min_deg:
                msg = "in-degree {} (min {} via #related)".format(degree, min_deg)
                errors.append(("in_degree", msg))
                reporter_error(msg, nugget_num=num, shortname=shortname)

        related = n.get("related", [])
        if run_limits and len(related) == 0:
            msg = "0 #related"
            errors.append(("underlinked", msg))
            reporter_error(msg, nugget_num=num, shortname=shortname)
        elif run_limits and len(related) > 5:
            msg = "#related has {} entries (max 5)".format(len(related))
            errors.append(("over_related", msg))
            reporter_error(msg, nugget_num=num, shortname=shortname)

        section_names = ("surface", "depth", "script", "images")
        n_sections = sum(1 for name in section_names if not section_is_tbd(layers.get(name)))
        if status == "proto":
            expected_status = "proto"
        elif not status_order:
            expected_status = "empty"
        elif n_sections == 0:
            expected_status = status_order[-1]
        elif n_sections >= 1 and n_sections <= 3:
            expected_status = status_order[-3] if len(status_order) >= 3 else status_order[-1]
        else:
            expected_status = "complete"
        complete_statuses = _complete_statuses(status_order)
        if expected_status == "complete":
            if status not in complete_statuses:
                expected_str = ", ".join(sorted(complete_statuses))
                msg = "has all 4 sections but status is {!r} (expected one of: {})".format(status, expected_str)
                errors.append(("status", msg))
                reporter_error(msg, nugget_num=num, shortname=shortname)
        elif status != expected_status:
            msg = "has {} section(s) but status is {!r} (expected {})".format(n_sections, status, expected_status)
            errors.append(("status", msg))
            reporter_error(msg, nugget_num=num, shortname=shortname)

        tags = n.get("tags", [])
        if not tags:
            msg = "no #tags (first tag must be a primary category)"
            errors.append(("primary_category", msg))
            reporter_error(msg, nugget_num=num, shortname=shortname)
        elif tags[0] not in PRIMARY_CATEGORIES:
            msg = "first tag {!r} is not a primary category (expected one of: {})".format(
                tags[0], ", ".join(sorted(PRIMARY_CATEGORIES))
            )
            errors.append(("primary_category", msg))
            reporter_error(msg, nugget_num=num, shortname=shortname)

    counts = {}
    for kind, _ in errors:
        counts[kind] = counts.get(kind, 0) + 1
    n_nuggets = len(nuggets_to_check)
    n_issues = len(errors)
    n_notes = sum(len(n.get("notes", [])) for n in nuggets_to_check)

    parts = [f"{n_nuggets} nuggets", f"{n_notes} notes"]
    if counts.get("length"):
        parts.append(f"{counts['length']} length")
    if counts.get("in_degree"):
        parts.append(f"{counts['in_degree']} in-degree")
    if counts.get("underlinked"):
        parts.append(f"{counts['underlinked']} underlinked")
    if counts.get("over_related"):
        parts.append(f"{counts['over_related']} over-related")
    if counts.get("status"):
        parts.append(f"{counts['status']} status")
    if counts.get("primary_category"):
        parts.append(f"{counts['primary_category']} primary_category")
    suffix = f" — {n_issues} issues" if n_issues else " — ok"
    summary = ", ".join(parts) + suffix + "."
    print(summary, file=sys.stderr)

    by_status = {}
    for n in nuggets_to_check:
        s = n.get("status", "empty")
        by_status[s] = by_status.get(s, 0) + 1
    ordered = [s for s in status_order if s in by_status]
    ordered += [s for s in sorted(by_status) if s not in status_order]
    status_line = ", ".join(f"{s}: {by_status[s]}" for s in ordered)
    print(status_line, file=sys.stderr)

    if verbose:
        for n in nuggets_to_check:
            if n.get("notes"):
                num = n.get("number", "?")
                fn = n.get("filename", "?")
                shortname = fn.split("-", 1)[-1] if "-" in fn else None
                for note in n.get("notes", []):
                    reporter_warning(note, nugget_num=num, shortname=shortname)

    if not quiet:
        print_all()

    if has_errors():
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
