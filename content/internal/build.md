# How build.py Creates the Website

`src/build.py` is the site generator for SeedPods. It reads from `content/` and `config/`, and writes HTML (and assets) into a single output directory. That directory is the web root: the build writes `index.html` and all other pages there.

Run the build with:

```bash
just build
```

Do not run `python3 src/build.py` directly; use the justfile so the venv (with the `markdown` package) is used.

**Where to edit styles and assets:** The build **creates the site directory from scratch** and copies two assets from `config/`. Edit **`config/site.css`** (and `config/logo.svg` if needed) — **not** files under the site directory. Files under the site directory are build output and will be overwritten; changes there will be lost on the next build.

---

## Build order and outputs

1. **Config**: `config/settings.txt` is read; `site_dir` and `site_base` are used (e.g. output path and base URL). MD pages can inject any setting with `@setting(key)` (see @link(directives.md, directives)).
2. **Pods**: All `content/nuggets/*.txt` are parsed; pod pages are written to `site_dir/<tag>.html`.
3. **Assets**: `config/site.css` and `config/logo.svg` are copied into `site_dir`.
4. **Nav-derived pages**: For each nav item, either `content/<token>.md` or `content/<token>/page.md` is built to `site_dir/<token>.html`.
5. **Internal**: `content/internal/page.md` is always built as `site_dir/internal.html`.
6. **Referenced .md**: Any `.md` file reached by &#64;link from the main MD pages (transitively) is built to `site_dir` with the path-based name (e.g. `internal-inside.html`).
7. **List-menu pages**: For each target in `list_menu` (e.g. glossary, bibliography, tags, map) that is not already built from nav, the corresponding `content/<token>.md` (or `content/<token>/page.md`) is built to `site_dir/<token>.html`. Those `.md` files use @glossary, @bibliography, @index, or @map to inject the built table or graph.
8. **Index and assets**: `site_dir/index.html` (from `content/home.md`), `map.svg`, and `4u-ai.txt` are generated.

Required files for a full build include: `content/home.md`, `content/internal/page.md`, and for each nav token either `content/<token>.md` or `content/<token>/page.md`. `config/status.txt` is also required.

For config and nav: @link(settings.md, settings). For @ directives in Markdown and pod files: @link(directives.md, directives).

---

## Importing prototype pods

Prototype .md files (e.g. in `content/more/`) can be turned into pod .txt files with:

```bash
just import content/more/primordia.md content/more/seed-speculations.md
```

By default the command runs in **preview** mode: it parses each file, assigns the next pod number and a shortname (from the title), and prints `number-shortname  Title` for each protopod. It does not write files. Use **`--apply`** to actually write each pod to `content/nuggets/`:

```bash
just import --apply content/more/primordia.md content/more/seed-speculations.md
```

Imported pods have `#status proto` and a single body (no `#brief` directive). Each protopod in the source file must include a `#shortname` line (e.g. `#shortname harmonic-barchart`); if one is missing, import reports it and skips that pod without writing a file. The parser accepts optional numbering (e.g. `## 1. Title`) and category headings (e.g. `## Physics & Mathematics`); categories are skipped. File-level `#ref` and `#term` in the prototype are added to each generated pod. After importing, run `just build` to regenerate the site.

**Full format for import files:** @link(import-format.md, import-format) — use it when creating or editing .md files meant for `just import` (e.g. new files like primordia or seed_speculations).
