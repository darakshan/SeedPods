# How build.py Creates the Website

`src/build.py` is the site generator for Seed Nuggets. It reads from `content/` and `config/`, and writes HTML (and assets) into a single output directory. That directory is the web root: the build writes `index.html` and all other pages there.

Run the build with:

```bash
just build
```

Do not run `python3 src/build.py` directly; use the justfile so the venv (with the `markdown` package) is used.

**Where to edit styles and assets:** The build **creates the site directory from scratch** and copies two assets from `config/`. Edit **`config/site.css`** (and `config/logo.svg` if needed) — **not** files under the site directory. Files under the site directory are build output and will be overwritten; changes there will be lost on the next build.

---

## Build order and outputs

1. **Config**: `config/settings.txt` is read; `site_dir` must be set.
2. **Nuggets**: All `content/nuggets/*.txt` are parsed; nugget pages are written to `site_dir/<tag>.html`.
3. **Assets**: `config/site.css` and `config/logo.svg` are copied into `site_dir`.
4. **Nav-derived pages**: For each nav item, either `content/<token>.md` or `content/<token>/page.md` is built to `site_dir/<token>.html`.
5. **Internal**: `content/internal/page.md` is always built as `site_dir/internal.html`.
6. **Referenced .md**: Any `.md` file reached by @link from the main MD pages (transitively) is built to `site_dir` with the path-based name (e.g. `internal-inside.html`).
7. **List-menu pages**: For each target in `list_menu` (e.g. glossary, bibliography, tags, map) that is not already built from nav, the corresponding `content/<token>.md` (or `content/<token>/page.md`) is built to `site_dir/<token>.html`. Those `.md` files use @glossary, @bibliography, @index, or @map to inject the built table or graph.
8. **Index and assets**: `site_dir/index.html` (from `content/home.md`), `map.svg`, and `4u-ai.txt` are generated.

Required files for a full build include: `content/home.md`, `content/internal/page.md`, and for each nav token either `content/<token>.md` or `content/<token>/page.md`. `config/status.txt` is also required.

For config and nav: @link(settings.md, settings). For @ directives in Markdown and nugget files: @link(directives.md, directives).
