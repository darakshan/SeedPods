#!/usr/bin/env python3
"""
check.py — Review nuggets for structure guidelines.
- Surface/depth word counts vs config/index.txt limits
- Every nugget pointed to by at least min_related_in_degree others (#related)
- Underlinked: nuggets with 0 #related
- #related max 5
- Report #note directives (editorial comments; ignored in page generation)
- Status vs sections (surface, depth, script, images; provenance ignored): section counts and valid statuses from config/status.txt; word count for statuses from top of config up through last draft*

Usage:
  python src/check.py              # summary + detailed findings (all nuggets)
  python src/check.py -q            # summary only
  python src/check.py -v            # summary + details + notes (interleaved by nugget)
  python src/check.py 3             # check only 003, show notes (implies -v)
  python src/check.py 3 4 19 99     # check 003, 004, 019; warn 99 missing
"""

import sys

from nugget_parser import (
    load_all_nuggets,
    load_index_copy,
    load_status_order,
    section_is_tbd,
)


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

    params = load_index_params()
    nuggets = load_all_nuggets(warn=lambda _: None)
    status_order = load_status_order()
    all_numbers = set(n.get("number", "") for n in nuggets if n.get("number"))
    if nugget_filter:
        for a in args:
            n = a.zfill(3)
            if n not in all_numbers:
                print(f"{a}: no such nugget", file=sys.stderr)
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

        if run_word_count and not section_is_tbd(surface):
            lo, hi = params["surface_min_words"], params["surface_max_words"]
            if s_words < lo:
                errors.append(("length", f"{fn}: surface has {s_words} words (min {lo})"))
            elif s_words > hi:
                errors.append(("length", f"{fn}: surface has {s_words} words (max {hi})"))

        if run_word_count and not section_is_tbd(depth):
            lo, hi = params["depth_min_words"], params["depth_max_words"]
            if d_words < lo:
                errors.append(("length", f"{fn}: depth has {d_words} words (min {lo})"))
            elif d_words > hi:
                errors.append(("length", f"{fn}: depth has {d_words} words (max {hi})"))

        if run_limits:
            degree = in_degree.get(num, 0)
            min_deg = params["min_related_in_degree"]
            if degree < min_deg:
                errors.append(("in_degree", f"{fn}: in-degree {degree} (min {min_deg} via #related)"))

        related = n.get("related", [])
        if run_limits and len(related) == 0:
            errors.append(("underlinked", f"{fn}: 0 #related"))
        elif run_limits and len(related) > 5:
            errors.append(("over_related", f"{fn}: #related has {len(related)} entries (max 5)"))

        section_names = ("surface", "depth", "script", "images")
        n_sections = sum(1 for name in section_names if not section_is_tbd(layers.get(name)))
        if not status_order:
            expected_status = "empty"
        elif n_sections == 0:
            expected_status = status_order[-1]
        elif n_sections == 1:
            expected_status = status_order[-3] if len(status_order) >= 3 else status_order[-1]
        elif n_sections <= 3:
            expected_status = status_order[-2] if len(status_order) >= 2 else status_order[-1]
        else:
            expected_status = "complete"
        complete_statuses = _complete_statuses(status_order)
        if expected_status == "complete":
            if status not in complete_statuses:
                expected_str = ", ".join(sorted(complete_statuses))
                errors.append(("status", f"{fn}: has all 4 sections but status is {status!r} (expected one of: {expected_str})"))
        elif status != expected_status:
            errors.append(("status", f"{fn}: has {n_sections} section(s) but status is {status!r} (expected {expected_status})"))

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

    unified = []
    for _, msg in errors:
        fn = msg.split(": ", 1)[0] if ": " in msg else "?"
        unified.append((fn, msg))
    if verbose:
        for n in nuggets_to_check:
            if n.get("notes"):
                fn = n.get("filename", "?")
                for note in n.get("notes", []):
                    unified.append((fn, f"{fn} {note}"))
    unified.sort(key=lambda x: x[0])

    if not quiet:
        for _, line in unified:
            print(line, file=sys.stderr)

    if errors:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
