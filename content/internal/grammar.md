## Grammar of a Seed Nugget

The build script parses nugget files strictly. Follow this grammar so new or revised nuggets work without manual processing.

###File

- Location: `nuggets/` directory.
- Name: `NNN-shortname.txt` where NNN is the 3-digit zero-padded number (e.g. 001, 020) and shortname is a one-word or hyphenated slug. Lowercase, no spaces. The number and shortname are derived from the filename only; do not put them in the file.
- Encoding: UTF-8.

###Structure (order is fixed)

1. Metadata block: single-line fields, one per line.
2. Layer block: exactly five sections, in this order — surface, depth, provenance, script, images. Each section is a line `#layername` (no value) followed by the section body until the next line that starts with `#`.

###Metadata (single-line fields)

- Each line: `#fieldname value` (one space after the hash, field name, space, rest of line is value).
- Field names are case-insensitive; the parser lowercases them.
- Required fields and format:
  - `#title` — full title; may contain spaces and punctuation.
  - `#subtitle` — one sentence; may contain spaces and punctuation.
  - `#status` — exactly one of: empty | partial | prelim | rough | draft1 | final
  - `#date` — date string (e.g. 2026-03-11).
  - `#tags` — comma-separated list. Each tag: lowercase, multi-word tags hyphenated (e.g. history-of-science, AI). No spaces after commas required but allowed.
  - `#related` — comma-separated list of other nugget numbers. The NNN from each target's filename (e.g. 002, 011, 018). Max 5. Links resolve by string equality, so "1" will not match a nugget whose filename starts with "001".

###References (#ref)

- **Only inside `#provenance`.** Each line: `#ref` followed by a space and the full citation text (e.g. author, title, year, notes). One reference per line. If `#ref` appears in any other section it is an error (the build warns and ignores it).
- The build does two things with `#ref` lines: (1) At the end of the References layer on each nugget page it generates a **Further reading** subsection listing all refs from that nugget. (2) It collects refs from **all** nuggets and generates the Bibliography page, sorted by exact ref text (so author order if you cite as "Author, Title..."), with which nuggets cite each.

###Key terms (#term)

- **Anywhere in a nugget.** Each line: `#term` followed by a space and the term, then a colon (`:`), then the definition (e.g. `#term Paradigm: Thomas Kuhn's term for the framework...`). One term per line.
- The build collects terms from **all** nuggets and generates the Glossary page: terms sorted alphabetically, grouped so the same term from multiple nuggets appears once with each definition indented; each entry lists which nuggets define it (In: …).

###Editorial notes (#note)

- `#note` — any line `#note ...` is an editorial comment. It is not included in any layer and is omitted from page generation. The check tool reports all `#note` lines; use `just check -v` or `just check -v 001 002` to list them.

###Layers (multi-line sections)

- Section start: a line that is exactly `#surface`, `#depth`, `#provenance`, `#script`, or `#images` (no text after the name). Parser treats these as layer names, not metadata.
- Section body: all following lines that do not start with `#`. Blank lines are kept. Body ends at the next line starting with `#` or end of file.
- All five layer headers must appear in this order: `#surface`, `#depth`, `#provenance`, `#script`, `#images`. If a layer has no content yet, write the header and put `TBD` (or a single line of placeholder text) as the body so the section exists.
- Layer content is free-form text. No special syntax required. Use `TBD` for placeholder sections. In any prose layer you may use **@exercise(Try this: ...)** — the text inside the parentheses (typically starting with “Try this: ”) is rendered as a call-to-action block at that position. Use balanced parentheses if the text contains `)`.

###Parsing rules (what the build does)

- Lines starting with `#`: after the `#`, the first token is the key; the rest of the line (after the first run of whitespace) is the value. Keys in the metadata set (title, subtitle, status, date, tags, related) are stored as meta; value is trimmed. Number and shortname are derived from the filename (NNN-shortname) and are not read from the file. Any other key starts a layer and subsequent non-`#` lines are appended to that layer's body.
- Tags: meta["tags"] is split on commas, each item stripped.
- Related: meta["related"] is split on commas, each item stripped. Matching to other nuggets is by exact string equality of the nugget number (the NNN from the filename).

###Minimal valid nugget (template)

The following lines need "#" before each one. It is not included here because it has a different meaning for MarkDown, even inside triple quotes.

```
title: Example Title
subtitle: One sentence subtitle.
status: empty
date: 2026-03-11
tags: tag-one, tag-two
related: 001, 002
surface: TBD
depth: TBD
provenance: TBD
script: TBD
images: TBD
```

Save as `nuggets/999-example.txt`. The number (999) and shortname (example) come from the filename only.
