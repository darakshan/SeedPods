# &#64; directives (Markdown pages)

In `.md` files under `content/` (home, nav file/dir pages, internal, and any referenced docs), the pipeline is: **&#64;include**, then **&#64;samples** / **&#64;nuggets** / **&#64;timestamp** / **&#64;link** / **&#64;image**, then Markdown → HTML. The order is fixed: &#64;include runs first so included content is processed; then other directives; then Markdown runs on the result.

The &#64; directives are:

1. **&#64;bibliography**  
2. **&#64;glossary**  
3. **&#64;image(file, caption, credit)**  
4. **&#64;include(path)**  
5. **&#64;index**  
6. **&#64;link(locator, text)**  
7. **&#64;map**  
8. **&#64;nuggets**  
9. **&#64;samples** or **&#64;samples(n)**  
10. **&#64;setting(key)**  
11. **&#64;timestamp**

## &#64;include(path)

- **Syntax**: `@include(filename)` — path relative to the current file's directory. Parentheses required.
- **Effect**: The directive is replaced by the full contents of that file. If the resolved path leaves that directory or the file is missing, a warning is emitted and the directive is left unchanged.
- **Example**: From `content/internal/page.md`, `@include(structure.md)` pulls in `content/internal/structure.md`.

## &#64;samples and &#64;samples(n)

- **Syntax**: `@samples` or `@samples(n)` — optional number (default 5, capped at 50).
- **Effect**: The line is replaced by a block of seed rows (links to nugget pages). The number is how many to show (default 5, capped at 50). Order and styling use `config/status.txt` and index copy (e.g. view-all link on home). On the home page this is rendered as the full "seed list" section; on other pages it is just the requested number of rows.

## &#64;nuggets

- **Syntax**: `@nuggets` (no arguments).
- **Effect**: Replaced by the full list of all nugget rows (same block as the list page), with sort UI. No "view all" link is added (the page is the full list).

## &#64;glossary

- **Syntax**: `@glossary` (no arguments).
- **Effect**: Replaced by the glossary table (terms and definitions from all nuggets, grouped by term). Use in any `.md` file (e.g. `content/glossary.md`) to build a glossary page.

## &#64;bibliography

- **Syntax**: `@bibliography` (no arguments).
- **Effect**: Replaced by the bibliography (references from `#ref` in `#provenance`, grouped by keyword). Use in any `.md` file (e.g. `content/bibliography.md`) to build a bibliography page.

## &#64;index

- **Syntax**: `@index` (no arguments).
- **Effect**: Replaced by the index (nuggets by tag and by status). Use in any `.md` file (e.g. `content/tags.md`) to build an index page.

## &#64;map

- **Syntax**: `@map` (no arguments).
- **Effect**: Replaced by the map (graph of nuggets with category/status filters). Use in any `.md` file (e.g. `content/map.md`) to build a map page.

## &#64;setting(key)

- **Syntax**: `@setting(key)` — key is a single word (e.g. `site_base`, `site_dir`).
- **Effect**: Replaced by the value of that key from `config/settings.txt`. Used so the builder can insert settings into HTML. For `site_base`, the value is returned with no trailing slash so you can concatenate with `/{path}`.
- **Example**: `@setting(site_base)` expands to the site base URL (e.g. `https://example.com/SeedNuggets`).

## &#64;timestamp

- **Syntax**: `@timestamp` (no arguments). May appear anywhere inline.
- **Effect**: Replaced by the build timestamp (e.g. `YYYY-MM-DD HH:MM Pacific`). If build time is not available, the token may be left unchanged.

## &#64;link(locator, text)

- **Syntax**: `@link(locator, text)` — locator and text can be separated by commas; parentheses must match.
- **Effect**: Replaced by an HTML link `<a href="...">text</a>`.
- **Locator** can be:
  - A **nugget number** (e.g. `002`): link to that nugget's page (e.g. `002-somename.html`).
  - A **path to a .md file** under `content/` (e.g. `internal/inside.md`): the build registers that file to be built, and the href becomes the corresponding output name (path with `/` replaced by `-`, `.md` by `.html`, e.g. `internal-inside.html`).
  - Anything else (e.g. `about.html`): used as the href as-is; no automatic output path.
- If `text` is empty, the locator is used as the link text. Referenced `.md` paths are collected and built so that &#64;link targets exist.

## &#64;image(file, caption, credit)

- **Syntax**: `@image(file, caption, credit)` — arguments are comma-separated. Only the first (file) is required; caption and credit are optional.
- **Effect**: The directive is replaced by a figure: the image is copied from `content/images/` to the site output (e.g. `docs/images/`). The image is shown at 50% column width, floated left, with text wrapping. If caption or credit are given, a `<figcaption>` is added (credit in `<cite>`).
- **File**: Basename only (no path). The build looks for `content/images/file` with extension `.jpg`, `.jpeg`, `.png`, `.webp`, or `.gif` and copies it to the site’s `images/` directory. If no file is found, a warning is emitted and the directive is left unchanged.
- **Example**: `@image(harmonic-clock)` or `@image(mandelbrot-boundary, Mandelbrot Set, Wikipedia)`.
- **Where**: Available in both `.md` pages and nugget layer text (Surface, Depth, Brief, etc.).

---

# &#64; directive in nugget .txt files

Inside nugget source files (`content/nuggets/*.txt`), these directives are used (they are expanded when building nugget HTML, not in the Markdown pipeline):

- **&#64;nugget(NNN)** — In layer text (e.g. Surface, Depth, Provenance), replaced by an italicized link to that nugget: `<em><a href="NNN-name.html">Title</a></em>`. If no nugget matches the number, the directive is left as-is.
- **&#64;image(file, caption, credit)** — In any prose layer, replaced by a figure (image from `content/images/` copied to the site, 50% width, left-aligned, optional figcaption). Only the file argument is required; see the &#64;image section above.
- **&#64;exercise(Try this: ...)** — In any prose layer (surface, depth, provenance, images), the text inside the parentheses is rendered as a call-to-action block (`<div class="cta">...</div>`) at that position. Parentheses must balance if the text contains `)`. The inner text may contain &#64;nugget(NNN).
- **&#64;warn(message)** — In any prose layer, the text inside the parentheses is rendered as a notice block with a vertical bar to the left (`<div class="warn-notice">...</div>`), same style as the proto and rough notices. Use for editorial caveats such as flagging speculative content.

(This is an inconsistency that might be rectified.)
