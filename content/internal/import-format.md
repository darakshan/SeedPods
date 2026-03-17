# Format of Importable Seed Nugget Files

Use this when creating or editing **import source files** — Markdown files that become multiple proto nuggets via `just import`. Examples: `content/more/primordia.md`, `content/more/seed-speculations.md`. The build does not read these files; the import script does. The output is `.txt` nuggets in `content/nuggets/`, which then follow the grammar in @link(grammar.md, grammar).

---

## Purpose and workflow

1. **Write** a single `.md` file with multiple “protonuggets” (blocks separated by `---`).
2. **Preview**: `just import content/more/yourfile.md` — lists what would be created; does not write.
3. **Apply**: `just import --apply content/more/yourfile.md` — writes `NNN-shortname.txt` into `content/nuggets/`.
4. **Build**: `just build` — regenerates the site from the new nuggets.

Imported nuggets get `#status proto`, today’s date, and a single body (no layer headers). Number and shortname are derived from the output filename only; the written .txt files do not contain `#number` or `#shortname`.

---

## File structure

- **Location**: Typically `content/more/<name>.md`. Any path is valid; the script only needs the file to exist.
- **Encoding**: UTF-8.
- **Blocks**: Split the file with a horizontal rule: a line that is only `---` (or more dashes), with blank lines before/after optional. Everything before the first `---` is **preamble** (title, subtitle, notes); the parser ignores it for nugget extraction.
- **Block first line** (required). Exactly one of:
  - `## N. Title` — numbered section (e.g. `## 1. The Harmonic Bar Chart`). The `N.` and space are stripped; the rest is the nugget title.
  - `### Title` — unnumbered (e.g. `### Consciousness as a Dimension Orthogonal to Spacetime`). The whole line after `### ` is the title.
  - `## Category Name` — category heading with no number. **Skipped**: no nugget is created; use these to group blocks in the source.
- **Block body**: All following lines until the next `---` or end of file. Blank lines are kept. Certain lines are special (see below); the rest become the nugget body.

---

## Required in every block that becomes a nugget: #shortname

Each block that should produce a nugget **must** contain a line:

- `#shortname <slug>`

Example: `#shortname harmonic-chart` or `#shortname orthogonal`.

- **If missing**: the import script reports “shortname missing for: &lt;title&gt;” and **skips** that block; no file is written.
- **Slug**: One word or hyphenated (e.g. `farey`, `born-harmonic`). Lowercase is conventional. No spaces. If the slug is already used by an existing nugget or by another block in the same import run, the script appends `-2`, `-3`, etc. to make it unique.
- **Placement**: Anywhere in the block body; typically right after the title or at the start of the body.

---

## Special lines in the body

These are recognized and removed from the body (or collected) before the rest is written as the nugget’s single body.

| Line | Effect |
|------|--------|
| `#shortname slug` | Sets the output filename slug for this block. Required for the block to be emitted. |
| `#ref Full citation text` | **File-level.** The ref is collected and appended to **every** nugget generated from this file. Use for shared bibliography. |
| `#term Term: Definition` | **File-level.** The term is collected and appended to **every** nugget. Same format as in @link(grammar.md, grammar): term, colon, space, definition. |
| `#term Term` | Allowed; definition is empty. |
| `#links` or `#links ...` | **Stripped.** Not written to the nugget. Use if you want to reserve a line for future links. |

All other lines (including normal `##`/`###` in the middle of prose) go into the body. The parser only treats the **first line** of the block as the title/category; after that, `#` starts special lines only when they match the patterns above.

---

## What the import script writes

For each block that has a `#shortname`:

- **Filename**: `NNN-shortname.txt` in `content/nuggets/`, where `NNN` is the next free 3-digit number and `shortname` is the slug (uniquified if needed). The nugget’s number and shortname are taken from this filename only; the .txt file does not contain `#number` or `#shortname` lines.
- **Content**: A single nugget .txt with:
  - `#title` — from the block’s first line (after `## N. ` or `### `).
  - `#status proto`
  - `#date` — import date (e.g. 2026-03-16).
  - Optional `#subtitle`, `#tags`, `#related` — **not** parsed from the import file today; you can add them by editing the .txt after import.
  - One blank line, then the **body** (all non-special lines from the block, joined). Proto nuggets have no primary section headers (`#brief`, `#surface`, `#depth`, `#script`, `#images`); the body is unheaded. You may add `#provenance` and `#term` / `#ref` by editing the .txt after import.
  - Then all **file-level** `#term` lines (from any block in the file).
  - Then all **file-level** `#ref` lines.

So: `#ref` and `#term` in the import file are **global to the file** and get added to every generated nugget. To have refs/terms only on one nugget, add them by hand to that nugget’s .txt after import, or split into separate import files.

---

## Minimal example

```markdown
# My Import File
Optional preamble. Ignored.

---

### First idea
#shortname first-idea

A few sentences of body. No layer headers.

---

### Second idea
#shortname second-idea

Another block. #ref Author, Book, Year.
#term Idea: A notion worth defining.
```

Two blocks with shortnames → two nuggets. The `#ref` and `#term` will appear on both. Category-only blocks (`## Some Category`) can sit between `---` and the next `###`/`## N.` block and are skipped.

---

## Checklist for an AI (or human) creating an import file

1. **One file** in e.g. `content/more/<name>.md`, UTF-8.
2. **Blocks** separated by `---`.
3. **Each block** that should become a nugget: first line `## N. Title` or `### Title`; somewhere in the block, `#shortname slug`.
4. **Slugs**: lowercase, hyphenated, no spaces; unique per run (script will uniquify).
5. **Body**: normal prose; `#ref` / `#term` are file-level and go on every nugget; `#links` is stripped.
6. **After writing**: run `just import content/more/<name>.md` to preview, then `just import --apply content/more/<name>.md` to write; then `just build`.

For the exact grammar of the **output** .txt files (metadata, layers, #ref/#term in nuggets), see @link(grammar.md, grammar). For the import command and build order, see @link(build.md, build).
