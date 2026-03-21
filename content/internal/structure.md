## Structure of a SeedPod

Every seedpod has the same five layers. This consistency makes the archive navigable and the template maintainable. A reader who knows the structure can find what they need at whatever depth they want.

### Proto body (no primary sections)

SeedPods with status **proto** have an unheaded body (the proto text) and no primary section headers. Do **not** use `#brief`, `#surface`, `#depth`, `#script`, or `#images` in proto seedpods; the build derives the “brief” content from the first block of text after the metadata. Proto seedpods may optionally include **#provenance** (with prose, `#term`, and `#ref`). These are created by the import command from prototype .md files (e.g. in `content/more/`). Each proto-seedpod in the **import source** (.md) must include a `#shortname` line so the importer can assign the output filename; import skips any block that lacks it. The resulting seedpod `.md` file does not contain `#number` or `#shortname` — those are derived from the filename only. Proto seedpods may later be promoted to full seedpods by adding the five layers and changing status.

### Layer 1: Surface

The accessible version. Written for a curious high schooler or a first-time encounter with the idea. Concrete language, relatable examples, no jargon. Goal: recognition — oh, I've felt that, I just didn't have words for it. Ends with a call to action: "try this" or "look for this." Length: 400–700 words. Test with real young readers.

### Layer 2: Depth

The intellectual version. Connects to philosophy, science, history of ideas. Where Whitehead, Gödel, autopoiesis, and the rest live. Does not dumb down — assumes a reader who wants to go further. Can include technical detail. References other seedpods by number. Length: 300–600 words.

### Layer 3: Provenance

The roots. Glossary of key terms with definitions. Bibliography with full citations. Intellectual lineage — whose ideas these are, where they came from, what to read next. Intellectual honesty baked into the structure. Not a footnote — a genuine resource for the curious reader.

### Layer 4: Script

The three-minute video version. Written as a shooting script with direction lines (in caps or italic) and spoken text. Designed for compression and emotional landing — the seedpod as a short piece of entertainment that arrives before it explains. Inspired by Jason Silva's style: rapid, evocative, philosophically serious. Ends with a single sharp question or image.

### Layer 5: Images

The visual language. Describes (and eventually will contain) illustrations, animation concepts, shareable graphics. Each seedpod should have: a primary illustration, a shareable one-line graphic for social media, and a video thumbnail concept. The images should be able to stand alone and still transmit something of the seedpod's essence.

### Additional fields

Each seedpod also carries:

- number and short name (from filename: NNN-shortname.md; do not put `#number` or `#shortname` in the seedpod file)
- title, subtitle (one sentence)
- status (see below)
- date added
- category (`#category`): exactly one primary category — one of consciousness, sensation, physics, mathematics, biology, AI-minds, knowledge; see grammar for full list and usage
- related seedpods (up to five, by number), and
- references (#ref): optional lines inside **#provenance** only; each line is full citation text. The build generates a “Further reading” subsection on the seedpod page and a shared Bibliography page (sorted by ref text).
- key terms (#term): optional lines anywhere in a seedpod; each line is `#term Term: Definition`. Use for any concept the seedpod introduces or relies on — this is how all non-category subject matter is tracked. The build generates the shared Glossary page (terms grouped, definitions indented; lists which seedpods define each).

These are stored in the source `.md` file and used to build the repository, navigation, and bibliography automatically. See the grammar file for details on how all of these are represented. 

### Status

Status reflects how many of the four main layers (Surface, Depth, Script, Images) have real content. Provenance is ignored for this count. A layer counts as having content only if it is not empty, and not a single line that is or starts with "TBD".

| Status   | Meaning | Sections with content |
|----------|---------|------------------------|
| **empty**  | Nothing written yet | 0 |
| **prelim** | First layer in progress | 1 |
| **partial** | Two or three layers done | 2 or 3 |
| **rough** | All four layers present but need a lot of work | 4 |
| **draft1** or **final** | Complete; all four layers have content | 4 |
| **proto** | Imported or drafted as a single unheaded body; no primary sections | 1 (unheaded body only) |

Use **rough** when the seedpod has all sections but they need substantial revision. Use **draft1** when the seedpod is complete but still open to revision, **final** when it is locked. The check tool reports a mismatch if status does not match the section count.

SeedPods with status **proto** have an unheaded body (rendered as “Brief”) and optionally **#provenance**; they do not use the standard five primary layers. The site does not show the full layer-tabs nav for proto seedpods.