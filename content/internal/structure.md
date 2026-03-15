## Structure of a Seed Nugget

Every seed nugget has the same five layers. This consistency makes the archive navigable and the template maintainable. A reader who knows the structure can find what they need at whatever depth they want.

### Layer 1: Surface

The accessible version. Written for a curious high schooler or a first-time encounter with the idea. Concrete language, relatable examples, no jargon. Goal: recognition — oh, I've felt that, I just didn't have words for it. Ends with a call to action: "try this" or "look for this." Length: 400–700 words. Test with real young readers.

### Layer 2: Depth

The intellectual version. Connects to philosophy, science, history of ideas. Where Whitehead, Gödel, autopoiesis, and the rest live. Does not dumb down — assumes a reader who wants to go further. Can include technical detail. References other seeds by number. Length: 300–600 words.

### Layer 3: Provenance

The roots. Glossary of key terms with definitions. Bibliography with full citations. Intellectual lineage — whose ideas these are, where they came from, what to read next. Intellectual honesty baked into the structure. Not a footnote — a genuine resource for the curious reader.

### Layer 4: Script

The three-minute video version. Written as a shooting script with direction lines (in caps or italic) and spoken text. Designed for compression and emotional landing — the seed as a short piece of entertainment that arrives before it explains. Inspired by Jason Silva's style: rapid, evocative, philosophically serious. Ends with a single sharp question or image.

### Layer 5: Images

The visual language. Describes (and eventually will contain) illustrations, animation concepts, shareable graphics. Each seed should have: a primary illustration, a shareable one-line graphic for social media, and a video thumbnail concept. The images should be able to stand alone and still transmit something of the seed's essence.

### Additional fields

Each seed also carries:

- number and short name (from filename: NNN-shortname.txt)
- title, subtitle (one sentence)
- status (see below)
- date added
- tags, and 
- related seeds (up to five, by number), and
- references (#ref): optional lines inside **#provenance** only; each line is full citation text. The build generates a “Further reading” subsection on the nugget page and a shared Bibliography page (sorted by ref text).
- key terms (#term): optional lines anywhere in a nugget; each line is `#term Term — Definition`. The build generates the shared Glossary page (terms grouped, definitions indented; lists which nuggets define each).

These are stored in the source .txt file and used to build the repository, navigation, and bibliography automatically. See the grammar file for details on how all of these are represented. 

### Status

Status reflects how many of the four main layers (Surface, Depth, Script, Images) have real content. Provenance is ignored for this count. A layer counts as having content only if it is not empty, and not a single line that is or starts with "TBD".

| Status   | Meaning | Sections with content |
|----------|---------|------------------------|
| **empty**  | Nothing written yet | 0 |
| **prelim** | First layer in progress | 1 |
| **partial** | Two or three layers done | 2 or 3 |
| **rough** | All four layers present but need a lot of work | 4 |
| **draft1** or **final** | Complete; all four layers have content | 4 |

Use **rough** when the nugget has all sections but they need substantial revision. Use **draft1** when the nugget is complete but still open to revision, **final** when it is locked. The check tool reports a mismatch if status does not match the section count.