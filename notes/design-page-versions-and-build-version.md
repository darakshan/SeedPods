# Design: Page-level hashing, version numbers, and build history

## Goals

1. **Page-level change detection** — Hash each page’s **inputs** (content), not the whole site. Know exactly which pages changed.
2. **Version numbers** — Each page has a version; the whole build has a build version. Version reflects **content**, not appearance (so CSS-only changes don’t change page versions).
3. **Local history** — `.buildstate/history.csv` records date, build version, page version, and page name when a page is rebuilt (updated only when you run the build locally; not used on GitHub Pages).
4. **Footer: version + timestamp on every page** — Show build version, page version, and build timestamp in the footer (revealed on hover/touch). Since the site is static (e.g. GitHub Pages), the timestamp on the page is the only “log” visible to viewers.
5. **Build version for generated content** — Same build version for every generated table (index, tags, glossary, bibliography, map).
6. **Skip writing unchanged files** — Only write a page when its input hash has changed.

---

## 1. Input-based hashing

**Choice: hash each page’s inputs.** Version is tied to **content** (source files), not **appearance** (output or CSS). If only CSS or layout changes, a page’s version does not change unless that page’s input files changed.

- **Page identity:** Output path relative to site root (e.g. `index.html`, `037-assembly.html`, `about.html`, `tags.html`, …).
- **Per page:** Define `get_inputs_for_page(page_id)` returning the set of file paths whose contents affect that page. Hash the contents of those files (in a stable order); that is the page’s content hash. Compare to stored hash; if different or missing, the page changed.

**Scope of “page”:** Every HTML page. All HTML output is built via the same pipeline (head → body → foot → close), so every page uses `foot()`. Scope is simply “every HTML page we build.” Non-HTML (JSON, CSS, SVG, 4u-ai.txt) remain “always write” for now.

**Defining inputs per page type (outline):**

- **Pod page** `NNN-slug.html`: That pod’s `.txt` file; plus any image files referenced in it via `
@image(...)` (from content/images/). Optionally omit shared config if we never want config-only changes to bump pod versions.
- **index.html**: `home.md` + its includes; all pod `.txt` files (index lists them); config that affects index (e.g. index_copy, status_order for ordering). Or: home.md + includes + pods dir contents + relevant config paths.
- **Nav/list MD page** (e.g. `about.html`, `list.html`): That MD file + `_input_files_for_page(md_path)` (includes + linked MDs); for pages that embed @glossary / @bibliography / @index / @map, the pod set and config that feed those placeholders. So: main MD + includes + transitive @link refs + pods + status_order + explainers + index_copy for nav.
- **Static MD-ref page** (e.g. `about-authors.html`): That MD path + its includes + transitive @link refs; if it has placeholders, add pods + config that feed them.
- **internal.html**: `content/internal/page.md` + includes + refs; same placeholder inputs if any.
- **tags.html, glossary.html, bibliography.html, map.html**: Their MD (if any) or the builder’s logical “main” file; plus all pods + status_order + explainers (for glossary). So for tags: list path MD + pods + status_order; glossary: glossary builder inputs (pods, explainers); etc.

Implement by having a small registry: for each output path, a function or recipe that returns the set of input Paths. Hash those files in sorted path order.

---

## 2. Version numbers

- **Build version (global):** Integer; increments when at least one page’s input hash changed. Used in footer and for “same build” for all generated tables.
- **Page version (per page):** Integer; increments only when that page’s input hash changed. Stored in state; shown in footer.
- **When nothing changed:** No increment; no page writes; state unchanged. Assets (CSS, JS, JSON, etc.) can still be written every time or skipped by separate logic later.

---

## 3. State and history

**State:** `.buildstate/state.json`

- `build_version`: int  
- `pages`: `{ "index.html": { "hash": "...", "page_version": n }, ... }`  
- Optionally `last_build_time`: ISO timestamp of last build where something changed (for embedding in pages).

**History:** `.buildstate/history.csv` (easy to view in a spreadsheet or editor)

- CSV with header: `date,build_version,page_version,page_name,release_version`
- `release_version` is always `0` for now; release numbering will be handled later.
- Append one row when a page is rebuilt (input hash changed). No row when nothing changed. Date can be ISO or local format.
- This file lives in the repo and is updated only when you run the build locally; GitHub Pages only serves the built site, so the “log” viewers see is the timestamp (and version) on each page.

---

## 4. Build flow (full build only)

**No single-pod build.** Remove the `--pod N` option; build is always full and fast enough.

1. Load `.buildstate/state.json` (or create with build_version=0, pages={}).
2. Load pods, config, etc. (as now).
3. **Compute which pages changed:** For each HTML page id, call `get_inputs_for_page(page_id)`, hash those file contents, compare to `state["pages"].get(page_id, {}).get("hash")`. If missing or different, mark page as changed and set new page_version = old + 1 (or 1).
4. If any page changed: set `build_version = state["build_version"] + 1` and set build timestamp (e.g. now). Else: keep build_version and timestamp; skip all page writes; write state only if needed (e.g. no-op); exit or continue to asset writes.
5. **Write phase:** For each page that changed: generate HTML (with build_version, page_version, and build timestamp in footer); write file; append one row to `history.csv` (with release_version=0); update `state["pages"][page_id]` with new hash and page_version. For unchanged pages: **do not write**.
6. Write assets (CSS, JS, JSON, SVG, 4u-ai.txt) as now (always or optionally skip unchanged via separate hashing later).
7. Save `state.json` (build_version, pages, last_build_time).

---

## 5. Footer: version + timestamp on every page

- **Content:** Show **build version**, **page version**, and **build timestamp** (e.g. “Build 42 · Page 3 · 2025-03-17 14:30 Pacific”). So the page itself carries the “when” and “which version” without needing a server-side log.
- **Placement:** In `site_chrome.foot()`, inside or next to `.page-end` (e.g. with or near the logo). Hidden by default; revealed on hover or touch via a shared JS function.
- **Implementation:** One common JS (e.g. in `seed-nav.js`): e.g. `seedNavShowVersion(show)`. Footer markup includes the version and timestamp (e.g. in a `data-*` or a span). Same for all pages; only the values differ.

---

## 6. Build version for generated tables

All index/tags/glossary/bibliography/map pages get the same `build_version` in the footer. Optionally add `data-build-version` on the container of each generated table for scripting/debugging.

---

## 7. Timestamp and @timestamp

- **Footer:** Every page shows build version, page version, and **timestamp** (build time when something last changed, or that page’s last rebuild time—design choice: use one “build timestamp” for the whole build when any page changed).
- **`@timestamp` in MD:** Can remain as “last build time” (e.g. from `last_build_time` in state or current run). So `@timestamp` and the footer timestamp stay in sync conceptually.

---

## 8. Code touch points

| Area | Change |
|------|--------|
| `build.py` | Remove `--pod`; use input-based per-page hashing; load/save `.buildstate/state.json`; append to `.buildstate/history.csv` only for changed pages; **skip writing** unchanged HTML pages; pass build_version, page_version, build_timestamp into context. |
| New (e.g. in build.py or a small module) | `get_inputs_for_page(page_id)` (or similar) returning set of input Paths per page type; hash those files for comparison. |
| `site_chrome.py` | `set_build_context(build_version_=..., build_time_=...)`. `foot(build_version=..., page_version=..., build_timestamp=...)` with version+timestamp reveal on hover/touch. |
| `builders.py` | All callers of `foot()` pass build_version, page_version, build_timestamp from context. |
| `seed-nav.js` | Add version/timestamp reveal (e.g. `seedNavShowVersion`) for footer. |
| `config/site.css` | Style for footer version/timestamp (hidden by default, visible when active). |
| `md_pages.py` | `@timestamp` can use `last_build_time` from context. |

---

## 9. history.csv format

```csv
date,build_version,page_version,page_name,release_version
2025-03-17T14:30:00-07:00,42,1,index.html,0
2025-03-17T14:30:00-07:00,42,2,037-assembly.html,0
```

- Header on first write; append rows when a page is rebuilt. Same build_version can appear many times (one per changed page). `release_version` is always 0 for now.

---

## 10. Migration

First run with new code: no state → treat all pages as changed; set build_version = 1; set each page_version = 1 for written pages; write all pages; create history.csv with one row per page (or skip backfill and only log going forward). Create `.buildstate/state.json` with build_version and pages.
