"""
Shared @-directive helpers: unknown-directive warnings and @note stripping.
Used by nugget_parser and md_pages. Parse @ commands independently, then look up for processing.
"""

import re

KNOWN_AT_DIRECTIVES = {
    "include", "samples", "nuggets", "glossary", "bibliography", "index", "map",
    "timestamp", "link", "note", "exercise", "nugget",
}


def warn_unknown_at_directives(text, filepath, warn):
    """Warn for any @foo (alphabetic) not in KNOWN_AT_DIRECTIVES. filepath used in message."""
    if not text or not callable(warn):
        return
    for m in re.finditer(r"@([a-zA-Z]+)(?=[\s\(\)]|$)", text):
        name = m.group(1).lower()
        if name not in KNOWN_AT_DIRECTIVES:
            warn(f"Warning: {filepath}: unknown @ directive @{m.group(1)} (possible misspelling?)")


def strip_at_notes(text):
    """Remove every @note(...) (balanced parens) from text. Return (cleaned_text, [note_contents])."""
    if not text:
        return "", []
    notes = []
    out = []
    i = 0
    while i < len(text):
        match = re.search(r"@note\s*\(", text[i:])
        if not match:
            out.append(text[i:])
            break
        start = i + match.start()
        out.append(text[i:start])
        paren_start = i + match.end() - 1
        depth = 1
        j = paren_start + 1
        while j < len(text) and depth:
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
            j += 1
        if depth == 0:
            notes.append(text[paren_start + 1 : j - 1].strip())
            i = j
        else:
            out.append(text[start:paren_start + 1])
            i = paren_start + 1
    return "".join(out), notes
