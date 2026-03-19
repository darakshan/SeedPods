# Pod Images

Images are placed in `content/images/` and referenced in pod files with the `@image` directive.

## Naming

Files are named `{NNN}-{slug}.jpg`, matching the pod number and slug. Example: `073-moral-caution.jpg`.

## Specs

- **Format**: `.jpg` only
- **Dimensions**: 800 × 800 pixels (square)
- **Source**: Wikimedia Commons (public domain or compatible license)

## Adding an image

1. Find a suitable image on [Wikimedia Commons](https://commons.wikimedia.org).
2. Download the original file.
3. Crop to a square, then resize to 800 × 800 at quality 88:
   ```
   magick original.jpg -crop SxS+X+Y +repage -resize 800x800 -quality 88 NNN-slug.jpg
   ```
4. Place the result in `content/images/`.
5. Add the directive to the pod file:
   ```
   &#64;image(NNN-slug, Caption text, Credit / Wikimedia Commons)
   ```

## Directive syntax

`&#64;image(file, caption, credit)` — only the filename (no extension, no path) is required. Caption and credit are optional but expected for all pods. The build copies the image to `docs/images/` and wraps it in a `<figure>` floated left at 50% column width.
