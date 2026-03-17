"""
Explainers CSV, glossary terms, and build_explainers_page / build_glossary_body / build_glossary_page.
"""

import csv
import html as _html
import re

from nugget_parser import display_number, nugget_tag
from site_chrome import close, foot, head, nav


def tag_slug(tag):
    return tag.replace(" ", "-")


def term_slug(term):
    """Slug for explainer term anchors: lowercase, spaces to hyphens, parentheticals become -inner-."""
    s = re.sub(r"\s*\(([^)]*)\)\s*", r"-\1-", term)
    s = s.strip().lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9-]", "", s).strip("-")
    return s or "term"


def load_explainers_csv(path):
    """Load content/explainers.csv. Returns list of dicts: term, slug, links [{url, duration, title}], notes [str]."""
    if not path.exists():
        return []
    by_term = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 4 or (row[0].lower() == "term" and row[1].lower() == "url"):
                continue
            term, url, duration, title = (row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip())
            if not term:
                continue
            if term not in by_term:
                by_term[term] = {"links": [], "notes": []}
            if url.lower() == "comment":
                by_term[term]["notes"].append(title)
            else:
                by_term[term]["links"].append({"url": url, "duration": duration or "?:??", "title": title or "Watch"})
    return [
        {"term": term, "slug": term_slug(term), "links": data["links"], "notes": data["notes"]}
        for term, data in by_term.items()
    ]


def get_glossary_terms(nuggets):
    """Set of term strings from #term in all nuggets."""
    out = set()
    for n in nuggets:
        for term, _ in n.get("terms", []):
            out.add(term)
    return out


def ensure_explainers_has_glossary_terms(csv_path, glossary_terms):
    """Append any glossary term missing from the CSV as a comment row (No explainers found yet.). Returns list of added terms."""
    existing_terms = set()
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header and len(header) >= 4:
            rows.append(header)
        for row in reader:
            if len(row) >= 4 and row[0].strip():
                existing_terms.add(row[0].strip())
                rows.append(row)
    added = []
    for t in sorted(glossary_terms):
        if t not in existing_terms:
            rows.append([t, "comment", "", "(No explainers found yet.)"])
            added.append(t)
    if added:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
    return added


def _parse_explainer_link_text(text):
    """Parse link text into (duration_display, title). Duration is 'M:SS' or ''; title is cleaned or 'Watch'."""
    for prefix in ("check duration; ", "check duration, "):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    if not text or text in ("(", ")", "()"):
        return ("", "Watch")
    m = re.match(r"^(\d+):(\d+)[;,]?\s*(.*)$", text)
    if m:
        mins, secs = int(m.group(1)), int(m.group(2))
        total_secs = mins * 60 + secs
        display_m, display_s = total_secs // 60, total_secs % 60
        title = m.group(3).strip()
        return (f"{display_m}:{display_s:02d}", title if title else "Watch")
    m = re.match(r"^(\d+)\s*min(?:\s+(\d+)\s*secs?)?[;,]?\s*(.*)$", text, re.IGNORECASE)
    if m:
        mins = int(m.group(1))
        secs = int(m.group(2)) if m.group(2) else 0
        total_secs = mins * 60 + secs
        display_m, display_s = total_secs // 60, total_secs % 60
        title = m.group(3).strip()
        return (f"{display_m}:{display_s:02d}", title if title else "Watch")
    return ("", text.strip() or "Watch")


def _title_case(s):
    """Return string in Title Case (major words capitalized, small words lowercase unless first/last)."""
    if not s:
        return s
    small = frozenset(
        "a an the and but or for nor on at to by of in with as is it".split()
    )
    words = s.split()
    result = []
    for i, w in enumerate(words):
        if not w:
            result.append(w)
            continue
        lower = w.lower()
        if lower in small and i != 0 and i != len(words) - 1:
            result.append(lower)
        else:
            result.append(w[0].upper() + w[1:].lower() if len(w) > 1 else w.upper())
    return " ".join(result)


def _explainer_sort_key(term):
    """Sort key for terms: strip leading 'The ' for alphabetical order."""
    t = term.strip().lower()
    if t.startswith("the "):
        t = t[4:].strip()
    return t


def _explainer_block_html(entry):
    """HTML for one term's explainer content: notes + link lines. Used in glossary."""
    real_notes = [n for n in entry.get("notes", []) if n != "(No explainers found yet.)"]
    if not entry["links"]:
        real_notes = ["(No explainers found yet.)"]
    notes_html = "".join(
        '<p class="dim explainer-notes">' + _html.escape(n) + "</p>" for n in real_notes
    )
    link_lines = []
    for link in entry["links"]:
        url_esc = _html.escape(link["url"])
        dur_display = link["duration"] or "?:??"
        title_esc = _html.escape(_title_case(link["title"]))
        link_lines.append(
            f'<div class="explainer-link-line">'
            f'<span class="explainer-dur">{dur_display}</span> '
            f'<a class="explainer-link" href="{url_esc}" target="_blank" rel="noopener">{title_esc}</a>'
            f'</div>'
        )
    return notes_html + "".join(link_lines)


def build_explainers_page(nuggets, explainer_terms):
    """Build explainers.html from explainers data. Terms sorted alphabetically (strip 'The ' for sort); uses glossary styles."""
    if not explainer_terms:
        body = '<p class="dim">No explainers list. Add <code>content/explainers.csv</code>.</p>'
    else:
        sorted_terms = sorted(explainer_terms, key=lambda t: _explainer_sort_key(t["term"]))
        parts = []
        for entry in sorted_terms:
            term = entry["term"]
            slug = entry["slug"]
            term_esc = _html.escape(term)
            real_notes = [n for n in entry.get("notes", []) if n != "(No explainers found yet.)"]
            if not entry["links"]:
                real_notes = ["(No explainers found yet.)"]
            notes_html = "".join(
                '<p class="dim explainer-notes">' + _html.escape(n) + "</p>" for n in real_notes
            )
            link_lines = []
            for link in entry["links"]:
                url_esc = _html.escape(link["url"])
                dur_display = link["duration"] or "?:??"
                title_esc = _html.escape(_title_case(link["title"]))
                link_lines.append(
                    f'<div class="explainer-link-line">'
                    f'<span class="explainer-dur">{dur_display}</span> '
                    f'<a class="explainer-link" href="{url_esc}" target="_blank" rel="noopener">{title_esc}</a>'
                    f'</div>'
                )
            links_html = "".join(link_lines)
            block_content = notes_html + links_html
            links_block = f'<div class="gloss-defs"><div class="gloss-def-block">{block_content}</div></div>'
            parts.append(
                f'<div id="{_html.escape(slug)}" class="gloss-entry">'
                f'<div class="gloss-term-line"><strong class="gloss-term">{term_esc}</strong></div>'
                f'{links_block}'
                f"</div>"
            )
        body = "\n".join(parts)
    html = head("Explainers")
    html += nav(from_d=True)
    html += f'<div class="wrap"><div class="page-body fade"><h1>Explainers</h1><p class="dim repo-intro">Video explainers for glossary terms. (Relevance not verified)</p>{body}</div></div>'
    html += foot()
    html += close()
    return html


def build_glossary_body(nuggets, explainer_terms=None):
    """Glossary entries HTML from #term in nuggets. For @glossary directive."""
    explainer_by_slug = {e["slug"]: e for e in (explainer_terms or [])}
    by_entry = {}
    for n in nuggets:
        num = n.get("number", "")
        fname = nugget_tag(n) + ".html"
        title_display = display_number(num)
        for term, definition in n.get("terms", []):
            entry_key = (term, definition)
            if entry_key not in by_entry:
                by_entry[entry_key] = []
            by_entry[entry_key].append((title_display, fname))
    by_term = {}
    for (term, definition), nugget_list in by_entry.items():
        if term not in by_term:
            by_term[term] = []
        sorted_nugs = sorted(nugget_list, key=lambda x: (int(x[0]) if x[0].isdigit() else 999, x[0]))
        by_term[term].append((definition, sorted_nugs))
    parts = []
    for term in sorted(by_term.keys(), key=lambda t: t.lower()):
        term_esc = _html.escape(term)
        slug = term_slug(term)
        all_nuggets = []
        seen = set()
        for definition, nugget_list in by_term[term]:
            for disp, fname in nugget_list:
                if (disp, fname) not in seen:
                    seen.add((disp, fname))
                    all_nuggets.append((disp, fname))
        all_nuggets.sort(key=lambda x: (int(x[0]) if x[0].isdigit() else 999, x[0]))
        nugget_links = ", ".join(f'<a href="{fname}">{disp}</a>' for disp, fname in all_nuggets)
        in_part = f' ({nugget_links})' if nugget_links else ""
        term_line = f'<div class="gloss-term-line"><strong class="gloss-term">{term_esc}</strong>{in_part}</div>'
        def_blocks = []
        for definition, nugget_list in by_term[term]:
            def_esc = _html.escape(definition)
            if definition:
                def_blocks.append(f'<div class="gloss-def-block"><span class="gloss-def">{def_esc}</span></div>')
        if slug in explainer_by_slug:
            entry = explainer_by_slug[slug]
            if entry["links"] or [n for n in entry.get("notes", []) if n != "(No explainers found yet.)"]:
                def_blocks.append(
                    '<div class="gloss-def-block">' + _explainer_block_html(entry) + '</div>'
                )
        entry_id = f' id="{_html.escape(slug)}"'
        parts.append(
            f'<div class="gloss-entry"{entry_id}>'
            f'{term_line}'
            f'<div class="gloss-defs">' + "\n".join(def_blocks) + '</div>'
            f'</div>'
        )
    return "\n".join(parts) if parts else "<p class=\"dim\">No terms yet. Add <code>#term Term : Definition</code> lines in any nugget.</p>"


def build_glossary_page(nuggets, explainer_terms=None):
    body = build_glossary_body(nuggets, explainer_terms)
    html = head("Glossary")
    html += nav(from_d=True)
    html += f'<div class="wrap"><div class="page-body fade"><h1>Glossary</h1><p class="dim repo-intro">Key terms from all nuggets.</p>{body}</div></div>'
    html += foot()
    html += close()
    return html
