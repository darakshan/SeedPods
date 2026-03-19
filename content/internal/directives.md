# &#64; directives

&#64; directives work in two contexts:

- **`.md` files** under `content/` (home, nav file/dir pages, internal, and any referenced docs). Pipeline: **&#64;include** first, then other directives, then Markdown → HTML.
- **Pod layer text** (Surface, Depth, Provenance, etc. in `content/pods/*.txt`). Directives are expanded when building pod HTML.

All directives work in both contexts unless marked **`.md` only**. The table below lists all directives:

1. **&#64;bibliography** — `.md` only
2. **&#64;exercise(text)**  
3. **&#64;glossary** — `.md` only  
4. **&#64;image(file, caption, credit)**  
5. **&#64;include(path)** — `.md` only  
6. **&#64;index** — `.md` only  
7. **&#64;link(locator)** or **&#64;link(locator, text)**  
8. **&#64;map** — `.md` only  
9. **&#64;pods** — `.md` only  
10. **&#64;samples** or **&#64;samples(n)** — `.md` only  
11. **&#64;setting(key)**  
12. **&#64;timestamp**  
13. **&#64;warn(message)**

---

## &#64;include(path)

- **Syntax**: `@include(filename)` — path relative to the current file's directory. Parentheses required.
- **Effect**: The directive is replaced by the full contents of that file. If the resolved path leaves that directory or the file is missing, a warning is emitted and the directive is left unchanged.
- **Example**: From `content/internal/page.md`, `@include(structure.md)` pulls in `content/internal/structure.md`.
- **Where**: `.md` files only.

## &#64;samples and &#64;samples(n)

- **Syntax**: `@samples` or `@samples(n)` — optional number (default 5, capped at 50).
- **Effect**: The line is replaced by a block of seed rows (links to pod pages). The number is how many to show (default 5, capped at 50). Order and styling use `config/status.txt` and index copy (e.g. view-all link on home). On the home page this is rendered as the full "seed list" section; on other pages it is just the requested number of rows.
- **Where**: `.md` files only.

## &#64;pods

- **Syntax**: `@pods` (no arguments).
- **Effect**: Replaced by the full list of all pod rows (same block as the list page), with sort UI. No "view all" link is added (the page is the full list).
- **Where**: `.md` files only.

## &#64;glossary

- **Syntax**: `@glossary` (no arguments).
- **Effect**: Replaced by the glossary table (terms and definitions from all pods, grouped by term). Use in any `.md` file (e.g. `content/glossary.md`) to build a glossary page.
- **Where**: `.md` files only.

## &#64;bibliography

- **Syntax**: `@bibliography` (no arguments).
- **Effect**: Replaced by the bibliography (references from `#ref` in `#provenance`, grouped by keyword). Use in any `.md` file (e.g. `content/bibliography.md`) to build a bibliography page.
- **Where**: `.md` files only.

## &#64;index

- **Syntax**: `@index` (no arguments).
- **Effect**: Replaced by the index (pods by tag and by status). Use in any `.md` file (e.g. `content/tags.md`) to build an index page.
- **Where**: `.md` files only.

## &#64;map

- **Syntax**: `@map` (no arguments).
- **Effect**: Replaced by the map (graph of pods with category/status filters). Use in any `.md` file (e.g. `content/map.md`) to build a map page.
- **Where**: `.md` files only.

## &#64;setting(key)

- **Syntax**: `@setting(key)` — key is a single word (e.g. `site_base`, `site_dir`).
- **Effect**: Replaced by the value of that key from `config/settings.txt`. Used so the builder can insert settings into HTML. For `site_base`, the value is returned with no trailing slash so you can concatenate with `/{path}`.
- **Example**: `@setting(site_base)` expands to the site base URL (e.g. `https://example.com/SeedPods`).

## &#64;timestamp

- **Syntax**: `@timestamp` (no arguments). May appear anywhere inline.
- **Effect**: Replaced by the build timestamp (e.g. `YYYY-MM-DD HH:MM Pacific`). If build time is not available, the token may be left unchanged.

## &#64;link(locator) or &#64;link(locator, text)

- **Syntax**: `@link(locator)` or `@link(locator, text)`. Text is optional; if omitted it defaults to the pod title (for pod number locators) or the locator itself (for other types).
- **Effect**: Replaced by `<a href="...">text</a>`. Missing pods or unresolvable `.md` files are build errors.
- **Locator** can be:
  - A **pod number** (e.g. `002`): links to that pod's page. If no pod matches, it is a build error.
  - A **path to a `.md` file** (e.g. `internal/inside.md`): resolved relative to the current file's directory. The build registers that file to be built, and the href becomes the output name (e.g. `internal-inside.html`).
  - A **path-only name** (e.g. `about`, `about/authors`): looks for `content/{name}.md` or `content/{name}/page.md`.
  - Anything else (e.g. `about.html`): used as the href as-is.

## &#64;image(file, caption, credit)

- **Syntax**: `@image(file, caption, credit)` — arguments are comma-separated. Only the first (file) is required; caption and credit are optional.
- **Effect**: The directive is replaced by a figure: the image is copied from `content/images/` to the site output (e.g. `docs/images/`). The image is shown at 50% column width, floated left, with text wrapping. If caption or credit are given, a `<figcaption>` is added (credit in `<cite>`).
- **File**: Basename only (no path). The build looks for `content/images/file` with extension `.jpg`, `.jpeg`, `.png`, `.webp`, or `.gif` and copies it to the site's `images/` directory. If no file is found, a warning is emitted and the directive is left unchanged.
- **Example**: `@image(harmonic-clock)` or `@image(mandelbrot-boundary, Mandelbrot Set, Wikipedia)`.

## &#64;exercise(text)

- **Syntax**: `@exercise(Try this: ...)` — parentheses must balance if the text contains `)`.
- **Effect**: The text inside the parentheses is rendered as a call-to-action block (`<div class="cta">...</div>`). The inner text may contain `@link(NNN)`.
- **Where**: Pod layer text only (Surface, Depth, Provenance, Images).

## &#64;warn(message)

- **Syntax**: `@warn(message)`.
- **Effect**: The text is rendered as a notice block with a vertical bar to the left (`<div class="warn-notice">...</div>`), same style as the proto and rough notices. Use for editorial caveats such as flagging speculative content.
- **Where**: Pod layer text only.
