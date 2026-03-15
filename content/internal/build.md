# How build.py Creates the Website

`src/build.py` is the site generator for Seed Nuggets. It reads from `content/` and `config/`, and writes HTML (and assets) into a single output directory. That directory is the web root: the build writes `index.html` and all other pages there.

Run the build with:

```bash
just build
```

Do not run `python3 src/build.py` directly; use the justfile so the venv (with the `markdown` package) is used.

---

## config/index.txt

The build requires `config/index.txt`. It is a **key–value config file**: one `key: value` per line. Empty lines and lines whose first non-space character is `#` are skipped. Trailing comments are supported: anything after ` #` on a line is ignored (the space before `#` matters).

### Required key

- **site_dir** — Directory under the repo root where the site is written (e.g. `d` or `docs`). Must be set; the build exits if it is missing. This is the web root; all generated HTML and copied assets live here.

### Nav and page discovery

- **nav** — Comma-separated list of tokens that become the top navigation. Each token is resolved to either a **file** or a **directory** under `content/`:
  - **File**: if `content/<token>.md` exists, that file is the page; it is built and emitted as `<token>.html`.
  - **Directory**: if `content/<token>/` is a directory and `content/<token>/page.md` exists, that directory is the page; the content is taken from `content/<token>/page.md` and emitted as `<token>.html`.

  The link label in the nav is the token with hyphens replaced by spaces and title-cased (e.g. `about` → "About", `more-is-different` → "More Is Different"). If neither the file nor the directory exists, the build warns and the item is still listed but the target is missing.

### Other keys (used by the build or MD pipeline)

- **site_base** — Base URL for the site (e.g. for canonical or absolute links).
- **section_head**, **repo_link**, **view_all** — Copy for list/home sections; `view_all` can use `{n}` for the total nugget count.
- **surface_min_words**, **surface_max_words**, **depth_min_words**, **depth_max_words** — Guidance for layer word counts.
- **min_related_in_degree** — Used for map/graph logic.

---

## Directory content: &lt;dir&gt;/page.md

For any nav token that is implemented as a **directory** (e.g. `about`, `internal`), the page content comes from that directory’s **page.md**:

- Path: `content/<token>/page.md`
- The build uses this file as the single Markdown source for that section.
- Output: `<token>.html` in the site directory (e.g. `about.html`, `internal.html`).

So for a section named `about`, you must have either:

- `content/about.md` (single file), or  
- `content/about/page.md` (directory with a `page.md`).

The same applies to `internal`: `content/internal/page.md` is the main Internal doc page. Other `.md` files under that directory (e.g. `content/internal/structure.md`, `content/internal/grammar.md`) are not nav targets by themselves; they are only used if something **includes** or **links** to them (see below).

---

## @ directives (Markdown pages)

In `.md` files under `content/` (home, nav file/dir pages, internal, and any referenced docs), the pipeline is: **@include**, then **@samples** / **@nuggets** / **@timestamp**, then **@link**, then Markdown → HTML. The order is fixed and affects both what is valid and how output is produced: @include must run first so included content is processed by the rest of the pipeline; the line-based directives must run before @link so that link text (e.g. `@link(002, @samples)`) is not interpreted as a directive; then Markdown runs on the result.

The five @ directives are:

1. **@include**  
2. **@samples**  
3. **@nuggets**  
4. **@timestamp**  
5. **@link(locator, text)**

### @include

- **Syntax**: a line that is exactly `@include ` followed by a filename (relative to the current file’s directory).
- **Effect**: The line is replaced by the full contents of that file. Paths are resolved under the directory of the current `.md` file; if the resolved path leaves that directory or the file is missing, a warning is emitted and the line is dropped.
- **Example**: From `content/internal/page.md`, `@include structure.md` pulls in `content/internal/structure.md`.

### @samples [N]

- **Syntax**: A line starting with `@samples`; optionally followed by a number (e.g. `@samples` or `@samples 10`).
- **Effect**: The line is replaced by a block of seed rows (links to nugget pages). The number is how many to show (default 5, capped at 50). Order and styling use `config/status.txt` and index copy (e.g. view-all link on home). On the home page this is rendered as the full “seed list” section; on other pages it is just the requested number of rows.

### @nuggets

- **Syntax**: A line that is exactly `@nuggets` (or starting with `@nuggets`).
- **Effect**: The line is replaced by the full list of all nugget rows (same block as the list page), with sort UI. No “view all” link is added (the page is the full list).

### @timestamp

- **Syntax**: `@timestamp` as a whole line, or anywhere inline in a line.
- **Effect**: Replaced by the build timestamp (e.g. `YYYY-MM-DD HH:MM Pacific`). If build time is not available, the token may be left unchanged.

### @link(locator, text)

- **Syntax**: `@link(locator, text)` — locator and text can be separated by commas; parentheses must match.
- **Effect**: Replaced by an HTML link `<a href="...">text</a>`.
- **Locator** can be:
  - A **nugget number** (e.g. `002`): link to that nugget’s page (e.g. `002-somename.html`).
  - A **path to a .md file** under `content/` (e.g. `internal/inside.md`): the build registers that file to be built, and the href becomes the corresponding output name (path with `/` replaced by `-`, `.md` by `.html`, e.g. `internal-inside.html`).
  - Anything else (e.g. `about.html`): used as the href as-is; no automatic output path.
- If `text` is empty, the locator is used as the link text. Referenced `.md` paths are collected and built so that @link targets exist.

---

## @ directive in nugget .txt files

Inside nugget source files (`content/nuggets/*.txt`), these directives are used (they are expanded when building nugget HTML, not in the Markdown pipeline):

- **@nugget(NNN)** — In layer text (e.g. Surface, Depth, Provenance), replaced by an italicized link to that nugget: `<em><a href="NNN-name.html">Title</a></em>`. If no nugget matches the number, the directive is left as-is.
- **@exercise(Try this: ...)** — In any prose layer (surface, depth, provenance, images), the text inside the parentheses is rendered as a call-to-action block (`<div class="cta">...</div>`) at that position. Parentheses must balance if the text contains `)`. The inner text may contain @nugget(NNN).

(This is an inconsistency that might be rectified.)

---

## Build order and outputs

1. **Config**: `config/index.txt` is read; `site_dir` must be set.
2. **Nuggets**: All `content/nuggets/*.txt` are parsed; nugget pages are written to `site_dir/<tag>.html`.
3. **Assets**: `config/site.css` and `config/logo.svg` are copied into `site_dir`.
4. **Nav-derived pages**: For each nav item, either `content/<token>.md` or `content/<token>/page.md` is built to `site_dir/<token>.html`.
5. **Internal**: `content/internal/page.md` is always built as `site_dir/internal.html`.
6. **Referenced .md**: Any `.md` file reached by @link from the main MD pages (transitively) is built to `site_dir` with the path-based name (e.g. `internal-inside.html`).
7. **Index, list, tags, etc.**: `site_dir/index.html` (from `content/home.md`), `tags.html`, `list.html` (if list is in nav), `bibliography.html`, `glossary.html`, `map.svg`, `map-graph.html`, and `4u-ai.txt` are generated as needed.

Required files for a full build include: `content/home.md`, `content/internal/page.md`, and for each nav token either `content/<token>.md` or `content/<token>/page.md`. `config/status.txt` is also required.
