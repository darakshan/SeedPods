# Finding a nugget page on the website

The list of all nuggets and their revision numbers is available at **./list.html** (relative to the site root).

The build gets the site root URL and output path from **config/settings.txt** (`site_base` and `site_dir`). Given the site root URL, a nugget number, and its shortname, you can form the canonical URL for that nugget’s page.

**Rule:** the page filename is `{number}-{shortname}.html`, where the number is **zero-padded to 3 digits**.

**URL:** `{root}/{number}-{shortname}.html`

- **root** — base URL of the site from `config/settings.txt` key **site_base** (no trailing slash when forming URLs). In .md you can insert it with `@setting(site_base)`.
- **number** — the nugget’s numeric id, zero-padded to 3 digits (e.g. `001`, `072`).
- **shortname** — the slug after the number in the nugget filename (e.g. `caloric`, `temperature`).

**Examples (root comes from settings at build time):**

| Root | Number | Shortname | Page URL |
|------|--------|-----------|----------|
| @setting(site_base) | 1 | caloric | @setting(site_base)/001-caloric.html |
| @setting(site_base) | 72 | temperature | @setting(site_base)/072-temperature.html |
| @setting(site_base) | 33 | edge | @setting(site_base)/033-edge.html |

In code: zero-pad the number to 3 digits, then concatenate `root` (with no trailing slash), `/`, `number`, `-`, `shortname`, and `.html`.

### Note
Claude is known to have a very slow cache, so fetching a page this way may not give the most recent version. 

