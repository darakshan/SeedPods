# &#64; directives

&#64; directives work in two contexts:

- **`.md` files** under `content/` (home, nav file/dir pages, internal, and any referenced docs). Pipeline: **&#64;include** first, then other directives, then Markdown → HTML.
- **SeedPod layer text** (Surface, Depth, Provenance, etc. in `content/pods/*.md`). Directives are expanded when building seedpod HTML. Layer text also supports full Markdown styling (bold, italic, headings, lists, code, tables, etc.).

All directives work in both contexts unless marked **`.md` only**.
The table below lists all directives:

1. **&#64;bibliography** — `.md` only
2. **&#64;exercise(text)**  
3. **&#64;footnote(text)**  
4. **&#64;footnotes** — `.md` only  
5. **&#64;glossary** — `.md` only  
6. **&#64;image(file, caption, credit)**  
7. **&#64;include(path)** — `.md` only  
8. **&#64;index** — `.md` only  
9. **&#64;link(locator)** or **&#64;link(locator, text)**  
10. **&#64;map** — `.md` only  
11. **&#64;pods** — `.md` only  
12. **&#64;samples** or **&#64;samples(n)** — `.md` only  
13. **&#64;setting(key)**  
14. **&#64;timestamp**  
15. **&#64;warn(message)**

---

## &#64;include(path)

- **Syntax**: `@include(filename)` — path relative to the current file's directory. Parentheses required.
- **Effect**: The directive is replaced by the full contents of that file. If the resolved path leaves that directory or the file is missing, a warning is emitted and the directive is left unchanged.
- **Example**: From `content/internal/page.md`, `@include(structure.md)` pulls in `content/internal/structure.md`.
- **Where**: `.md` files only.

## &#64;samples and &#64;samples(n)

- **Syntax**: `@samples` or `@samples(n)` — optional number (default 5, capped at 50).
- **Effect**: The line is replaced by a block of seedpod rows (links to seedpod pages). The number is how many to show (default 5, capped at 50). Order and styling use `config/status.txt` and index copy (e.g. view-all link on home). On the home page this is rendered as the full "seedpod list" section; on other pages it is just the requested number of rows.
- **Where**: `.md` files only.

## &#64;pods

- **Syntax**: `@pods` (no arguments).
- **Effect**: Replaced by the full list of all seedpod rows (same block as the list page), with sort UI. No "view all" link is added (the page is the full list).
- **Where**: `.md` files only.

## &#64;glossary

- **Syntax**: `@glossary` (no arguments).
- **Effect**: Replaced by the glossary table (terms and definitions from all seedpods, grouped by term). Use in any `.md` file (e.g. `content/glossary.md`) to build a glossary page.
- **Where**: `.md` files only.

## &#64;bibliography

- **Syntax**: `@bibliography` (no arguments).
- **Effect**: Replaced by the bibliography (references from `#ref` in `#provenance`, grouped by keyword). Use in any `.md` file (e.g. `content/bibliography.md`) to build a bibliography page.
- **Where**: `.md` files only.

## &#64;index

- **Syntax**: `@index` (no arguments).
- **Effect**: Replaced by the index (seedpods by tag and by status). Use in any `.md` file (e.g. `content/tags.md`) to build an index page.
- **Where**: `.md` files only.

## &#64;map

- **Syntax**: `@map` (no arguments).
- **Effect**: Replaced by the map (graph of seedpods with category/status filters). Use in any `.md` file (e.g. `content/map.md`) to build a map page.
- **Where**: `.md` files only.

## &#64;setting(key)

- **Syntax**: `@setting(key)` — key is a single word (e.g. `site_base`, `site_dir`).
- **Effect**: Replaced by the value of that key from `config/settings.txt`. Used so the builder can insert settings into HTML. For `site_base`, the value is returned with no trailing slash so you can concatenate with `/{path}`.
- **Example**: `@setting(site_base)` expands to the site base URL (e.g. `https://example.com/SeedPods`).

## &#64;timestamp

- **Syntax**: `@timestamp` (no arguments). May appear anywhere inline.
- **Effect**: Replaced by the build timestamp (e.g. `YYYY-MM-DD HH:MM Pacific`). If build time is not available, the token may be left unchanged.

## &#64;link(locator) or &#64;link(locator, text)

- **Syntax**: `@link(locator)` or `@link(locator, text)`. Text is optional; if omitted it defaults to the seedpod title (for seedpod number locators) or the locator itself (for other types).
- **Effect**: Replaced by `<a href="...">text</a>`. Missing seedpods or unresolvable `.md` files are build errors.
- **Locator** can be:
  - A **seedpod number** (e.g. `002`): links to that seedpod's page. If no seedpod matches, it is a build error.
  - A **path to a `.md` file** (e.g. `internal/inside.md`): resolved relative to the current file's directory. The build registers that file to be built, and the href becomes the output name (e.g. `internal-inside.html`).
  - A **path-only name** (e.g. `about`, `about/authors`): looks for `content/{name}.md` or `content/{name}/page.md`.
  - Anything else (e.g. `about.html`): used as the href as-is.

## &#64;image(file, caption, credit)

- **Syntax**: `@image(file, caption, credit)` — arguments are comma-separated. Only the first (file) is required; caption and credit are optional.
- **Effect**: The directive is replaced by a figure: the image is copied from `content/images/` to the site output (e.g. `docs/images/`). The image is shown at 50% column width, floated left, with text wrapping. If caption or credit are given, a `<figcaption>` is added (credit in `<cite>`).
- **File**: Basename only (no path). The build looks for `content/images/file` with extension `.jpg`, `.jpeg`, `.png`, `.webp`, or `.gif` and copies it to the site's `images/` directory. If no file is found, a warning is emitted and the directive is left unchanged.
- **Example**: `@image(harmonic-clock)` or `@image(mandelbrot-boundary, Mandelbrot Set, Wikipedia)`.

## &#64;footnote(text)

- **Syntax**: `@footnote(text)` — inline, embedded directly in the source text at the point of relevance. Parentheses in the footnote text must be balanced (same rule as `@note` and `@exercise`).
- **Effect**: The build extracts the footnote from the text flow and replaces it with a superscript number (auto-numbered sequentially by order of appearance within the pod). The footnote text is collected and rendered at the bottom of the pod page in a "Footnotes" section, numbered to match.
- **Marker style**: Footnotes render as superscript **numbers** (1, 2, 3…). Bibliography references (`@ref`) render as superscript **letters** (a, b, c…). The two marker styles are visually distinct so the reader knows at a glance whether a superscript links to the footnotes list at the bottom of the pod or to the bibliography page. This distinction holds during and after the transition period as existing `@ref` superscripts are gradually wrapped in `@footnote` directives.
- **Content**: The footnote text is free-form and supports inline Markdown (`*emphasis*`, `**bold**`, `` `code` ``, `[links](url)`). It may also contain:
  - `@ref(tag)` or `@ref(tag, "citation")` — bibliography references, resolved and linked as usual.
  - `@link(locator)` or `@link(locator, text)` — cross-references to other pods.
  - `@footnote(text)` — a nested footnote. The inner footnote gets its own sequential number and renders as a separate entry in the footnotes list. (Nesting is syntactically legal but should be used sparingly — or reserved for pods about self-reference.)
- **No identifier**: Footnotes have no tag or key. They are positional — each belongs to exactly one location in exactly one pod. They cannot be referenced from elsewhere. This distinguishes them from `@ref`, which uses a shared tag that can appear across many pods.
- **Relationship to `@ref`**: A footnote is *about* a source or an aside; a `@ref` is *the citation itself*. A footnote may contain zero, one, or several `@ref` directives. A `@ref` never contains a footnote.
- **Collection page**: The `@footnotes` directive (`.md` only) generates a collected footnotes page listing all footnotes from all pods, grouped by pod, for cross-archive browsing.
- **Where**: SeedPod section text (Surface, Depth, etc.) and `.md` content files. The `@footnotes` collection directive is `.md` only.

**Example** (inline in pod text):

```
James stated it in 1890@footnote(Chapter 6 of the *Principles*,
'The Mind-Stuff Theory,' where James argues that twelve feelings
don't add up to a thirteenth. He considered this fatal to
panpsychism, though he returned to something close in
@ref(james-2) fourteen years later.) and the problem has
resisted solution ever since.
```

This renders as:

> James stated it in 1890¹ and the problem has resisted solution ever since.

with footnote 1 at the bottom:

> 1. Chapter 6 of the *Principles*, 'The Mind-Stuff Theory,' where James argues that twelve feelings don't add up to a thirteenth. He considered this fatal to panpsychism, though he returned to something close in *The Varieties of Religious Experience* fourteen years later.

## &#64;footnotes

- **Syntax**: `@footnotes` (no arguments).
- **Effect**: Replaced by a collected footnotes page listing all footnotes from all pods, grouped by pod title, with links back to the footnote location in each pod. Analogous to `@glossary` and `@bibliography` for their respective directive types.
- **Where**: `.md` files only.

## &#64;exercise(text)

- **Syntax**: `@exercise(Try this: ...)` — parentheses must balance if the text contains `)`.
- **Effect**: The text inside the parentheses is rendered as a call-to-action block (`<div class="cta">...</div>`). The inner text may contain `@link(NNN)`.
- **Where**: SeedPod layer text only (Surface, Depth, Provenance, Images).

## &#64;warn(message)

- **Syntax**: `@warn(message)`.
- **Effect**: The text is rendered as a notice block with a vertical bar to the left (`<div class="warn-notice">...</div>`), same style as the proto and rough notices. Use for editorial caveats such as flagging speculative content.
- **Where**: SeedPod layer text only.
