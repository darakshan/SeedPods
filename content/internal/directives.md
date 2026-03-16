# @ directives (Markdown pages)

In `.md` files under `content/` (home, nav file/dir pages, internal, and any referenced docs), the pipeline is: **@include**, then **@samples** / **@nuggets** / **@timestamp**, then **@link**, then Markdown → HTML. The order is fixed and affects both what is valid and how output is produced: @include must run first so included content is processed by the rest of the pipeline; the line-based directives must run before @link so that link text (e.g. `@link(002, @samples)`) is not interpreted as a directive; then Markdown runs on the result.

The @ directives are:

1. **@include**  
2. **@samples**  
3. **@nuggets**  
4. **@glossary**  
5. **@bibliography**  
6. **@index**  
7. **@map**  
8. **@timestamp**  
9. **@link(locator, text)**

## @include

- **Syntax**: a line that is exactly `@include ` followed by a filename (relative to the current file's directory).
- **Effect**: The line is replaced by the full contents of that file. Paths are resolved under the directory of the current `.md` file; if the resolved path leaves that directory or the file is missing, a warning is emitted and the line is dropped.
- **Example**: From `content/internal/page.md`, `@include structure.md` pulls in `content/internal/structure.md`.

## @samples [N]

- **Syntax**: A line starting with `@samples`; optionally followed by a number (e.g. `@samples` or `@samples 10`).
- **Effect**: The line is replaced by a block of seed rows (links to nugget pages). The number is how many to show (default 5, capped at 50). Order and styling use `config/status.txt` and index copy (e.g. view-all link on home). On the home page this is rendered as the full "seed list" section; on other pages it is just the requested number of rows.

## @nuggets

- **Syntax**: A line that is exactly `@nuggets` (or starting with `@nuggets`).
- **Effect**: The line is replaced by the full list of all nugget rows (same block as the list page), with sort UI. No "view all" link is added (the page is the full list).

## @glossary

- **Syntax**: A line that is exactly `@glossary`.
- **Effect**: The line is replaced by the glossary table (terms and definitions from all nuggets, grouped by term). Use in any `.md` file (e.g. `content/glossary.md`) to build a glossary page.

## @bibliography

- **Syntax**: A line that is exactly `@bibliography`.
- **Effect**: The line is replaced by the bibliography (references from `#ref` in `#provenance`, grouped by keyword). Use in any `.md` file (e.g. `content/bibliography.md`) to build a bibliography page.

## @index

- **Syntax**: A line that is exactly `@index`.
- **Effect**: The line is replaced by the index (nuggets by tag and by status). Use in any `.md` file (e.g. `content/tags.md`) to build an index page.

## @map

- **Syntax**: A line that is exactly `@map`.
- **Effect**: The line is replaced by the map (graph of nuggets with category/status filters). Use in any `.md` file (e.g. `content/map.md`) to build a map page.

## @timestamp

- **Syntax**: `@timestamp` as a whole line, or anywhere inline in a line.
- **Effect**: Replaced by the build timestamp (e.g. `YYYY-MM-DD HH:MM Pacific`). If build time is not available, the token may be left unchanged.

## @link(locator, text)

- **Syntax**: `@link(locator, text)` — locator and text can be separated by commas; parentheses must match.
- **Effect**: Replaced by an HTML link `<a href="...">text</a>`.
- **Locator** can be:
  - A **nugget number** (e.g. `002`): link to that nugget's page (e.g. `002-somename.html`).
  - A **path to a .md file** under `content/` (e.g. `internal/inside.md`): the build registers that file to be built, and the href becomes the corresponding output name (path with `/` replaced by `-`, `.md` by `.html`, e.g. `internal-inside.html`).
  - Anything else (e.g. `about.html`): used as the href as-is; no automatic output path.
- If `text` is empty, the locator is used as the link text. Referenced `.md` paths are collected and built so that @link targets exist.

---

# @ directive in nugget .txt files

Inside nugget source files (`content/nuggets/*.txt`), these directives are used (they are expanded when building nugget HTML, not in the Markdown pipeline):

- **@nugget(NNN)** — In layer text (e.g. Surface, Depth, Provenance), replaced by an italicized link to that nugget: `<em><a href="NNN-name.html">Title</a></em>`. If no nugget matches the number, the directive is left as-is.
- **@exercise(Try this: ...)** — In any prose layer (surface, depth, provenance, images), the text inside the parentheses is rendered as a call-to-action block (`<div class="cta">...</div>`) at that position. Parentheses must balance if the text contains `)`. The inner text may contain @nugget(NNN).

(This is an inconsistency that might be rectified.)
