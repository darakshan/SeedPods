# config/settings.txt

The build requires `config/settings.txt`. It is a **key–value config file**: one `key: value` per line. Empty lines and lines whose first non-space character is `#` are skipped. Trailing comments are supported: anything after ` #` on a line is ignored (the space before `#` matters).

## Required key

- **site_dir** — Directory under the repo root where the site is written (e.g. `docs`). Must be set; the build exits if it is missing. The build reads this from `config/settings.txt`; that directory is the web root when served; all generated HTML and copied assets live there.

## Nav and page discovery

- **nav** — Comma-separated list of tokens that become the top navigation. Each token is resolved to either a **file** or a **directory** under `content/`:
  - **File**: if `content/<token>.md` exists, that file is the page; it is built and emitted as `<token>.html`.
  - **Directory**: if `content/<token>/` is a directory and `content/<token>/page.md` exists, that directory is the page; the content is taken from `content/<token>/page.md` and emitted as `<token>.html`.

  The link label in the nav is the token with hyphens replaced by spaces and title-cased (e.g. `about` → "About", `more-is-different` → "More Is Different"). If neither the file nor the directory exists, the build warns and the item is still listed but the target is missing.

- **list_menu** — Optional. When the nav includes `list`, this key controls the **Lists** pulldown. If `list_menu` is missing or empty, the Lists nav item is a single link to `list.html` (no dropdown). If set, it defines the dropdown entries: comma-separated items, each of the form `Label | target`. **Target** is always a **content path**: a token that resolves like nav (e.g. `list` → `content/list.md` → `list.html`, `glossary` → `content/glossary.md` → `glossary.html`). Each target must have either `content/<token>.md` or `content/<token>/page.md`. Pages for list_menu targets are built if not already built from nav.

  Example: `list_menu: Pods | list, Index | tags, Bibliography | bibliography, Glossary | glossary, Map | map`

## Other keys (used by the build or MD pipeline)

- **site_base** — Base URL for the site (e.g. for canonical or absolute links). The build and MD pipeline read `site_base` and `site_dir` from `config/settings.txt`. In .md you can inject any setting value with `@setting(key)` (e.g. `@setting(site_base)`, `@setting(site_dir)`); see @link(directives.md, directives).
- **section_head**, **repo_link**, **view_all** — Copy for list/home sections; `view_all` can use `{n}` for the total pod count.
- **surface_min_words**, **surface_max_words**, **depth_min_words**, **depth_max_words** — Guidance for layer word counts.
- **min_related_in_degree** — Used for map/graph logic.

---

# Directory content: &lt;dir&gt;/page.md

For any nav token that is implemented as a **directory** (e.g. `about`, `internal`), the page content comes from that directory’s **page.md**:

- Path: `content/<token>/page.md`
- The build uses this file as the single Markdown source for that section.
- Output: `<token>.html` in the site directory (e.g. `about.html`, `internal.html`).

So for a section named `about`, you must have either:

- `content/about.md` (single file), or  
- `content/about/page.md` (directory with a `page.md`).

The same applies to `internal`: `content/internal/page.md` is the main Internal doc page. Other `.md` files under that directory (e.g. `content/internal/structure.md`, `content/internal/grammar.md`) are not nav targets by themselves; they are only used if something **includes** or **links** to them (see directives).
