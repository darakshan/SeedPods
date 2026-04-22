# SeedPods iOS App

This document describes the architecture, scope, and design decisions for a new SeedPods iOS app.
It is intended as a briefing document for AI-assisted development sessions (Cursor/Claude).
Read this first, then consult the linked internal docs for format and grammar details.

Darakshan has added several NOTEs which are intended as amendments to this specification.

---

## Purpose

The iOS app is a native mobile environment for creating, editing, browsing, and publishing SeedPods.
It replaces the current workflow — which requires a Mac, a terminal, and manual file handling — with a fluid, conversation-driven experience on iPhone and iPad.

The app is designed for two kinds of users:

- **Darakshan** (primary author): full access to authoring, Claude conversations, build, and GitHub sync.
- **Future users**: a self-contained tool for building their own pod archive, with optional GitHub integration.

---

## Core Design Principles

- **iCloud as the working filesystem.** The `content/` directory lives in iCloud Drive. The app reads and writes directly to it. No intermediate sync layer.
- **Claude as collaborator, not tool.** The Claude conversation is the primary creative surface. The app gives Claude full awareness of the existing archive so conversations are contextually rich.
- **Plain text source files are the ground truth.** The `.txt` pod format is unchanged from the Python system. The iOS app reads and writes the same files. The Python build system remains valid and usable in parallel.
- **Protocol-based version management.** A `VersionStore` protocol abstracts version history. A simple built-in store ships by default; GitHub is an optional backend the user can enable in settings.
- **MVP scope is narrow.** Build the core well. Defer the graph, bibliography, glossary, and map pages.

---

## Internal Documentation to Read First

Before writing any code, read these internal docs (available at the published site or in `content/internal/`):

- **Structure**: `internal-structure.html` — the five layers, status values, proto pods
- **Grammar**: `internal-grammar.html` — exact file format, metadata fields, section syntax
- **Directives**: `internal-directives.html` — the `@verb(content)` system; note which directives are pod-layer only vs. `.md` only
- **Build**: `internal-build.html` — what the Python builder produces; the iOS builder is a subset of this

The Python source files are also available in `src/` and serve as the reference implementation:

- `src/seedpod_parser.py` — pod file parser; port this faithfully to Swift
- `src/directive.py` — directive scanner and processor; port to Swift
- `src/build.py` — site builder; port the pod-page portion for MVP

---

## Technology Stack

- **Language**: Swift
- **UI**: SwiftUI
- **Filesystem**: `FileManager` with iCloud ubiquity container (`FileManager.default.url(forUbiquityContainerIdentifier:)`)
- **Markdown → HTML**: Apple's `swift-markdown` package (Swift Package Manager), or `cmark` via SPM
- **In-app browser**: `WKWebView` pointed at locally-built HTML in a temp directory
- **Claude API**: Anthropic REST API (`/v1/messages`), API key stored in iOS Keychain
- **GitHub API**: GitHub REST API over HTTPS (no local git binary needed); personal access token stored in Keychain
- **Swift based.** All logic is native Swift.

---

## Data Model

Port `seedpod_parser.py` directly to Swift.
The core struct:

```swift
struct SeedPod: Identifiable, Codable {
    // Derived from filename: NNN-shortname.txt
    let number: String        // e.g. "042"
    let shortname: String     // e.g. "caloric"
    var filename: String      // e.g. "042-caloric"

    // Metadata fields (#title, #subtitle, etc.)
    var title: String
    var subtitle: String
    var status: PodStatus
    var date: String
    var category: PodCategory
    var tags: [String]
    var related: [String]     // pod numbers as strings

    // Structured data
    var refs: [(keyword: String, text: String)]
    var terms: [(term: String, definition: String)]

    // Layer content (raw text, directives unexpanded)
    var layers: PodLayers
}

struct PodLayers: Codable {
    var surface: String
    var depth: String
    var brief: String
    var provenance: String
    var script: String
    var images: String
}


NOTE: PodStatus and PodCategory are configurable in the python code, so the following enum declarations are incorrect

enum PodStatus: String, Codable, CaseIterable {
    case empty, prelim, partial, rough, draft1, final, proto
}

enum PodCategory: String, Codable, CaseIterable {
    case consciousness, sensation, physics, mathematics, biology
    case aiMinds = "AI-minds"
    case knowledge
}
```

**Key rule**: number and shortname come from the filename only.
Never read `#number` or `#shortname` from the file body.

---

## Swift Module Architecture

Build in three layers, in this order.

### Layer 1: Core (no UI)

`SeedPodParser` — reads a `.txt` file and returns a `SeedPod`.
Port of `seedpod_parser.py`.
Handles both full pods (five layers) and proto pods (unheaded body).

`DirectiveProcessor` — scans text for `@verb(content)` patterns and either strips, expands, or renders them.
Port of `directive.py`.
The scanner handles nested parentheses and backtick escaping.

`SeedPodStore` — loads all pods from the iCloud `content/pods/` directory.
Provides lookup by number, by slug, by category.
Handles file writes and new file creation.

`VersionStore` (protocol) — defines: `save(pod:note:)`, `listVersions(for:)`, `revert(pod:to:)`.
Two implementations:

- `LocalVersionStore`: keeps the last 20 snapshots per pod in `content/.versions/NNN-shortname/`. Each snapshot is a timestamped copy of the `.txt` file plus an optional `note.txt` (which may contain the Claude conversation summary that produced this version).
- `GitHubVersionStore`: commits changed files via the GitHub REST API. Requires a personal access token in the Keychain.

### Layer 2: Build Engine

`SiteBuilder` — takes `[SeedPod]` and writes HTML files to a local temp directory (not iCloud).
For MVP, builds only individual pod pages.
Deferred: index, bibliography, glossary, map.

`DirectiveRenderer` — expands pod-layer directives at render time: `@exercise`, `@image`, `@link`, `@warn`, `@timestamp`.
Strips `@note`.
The `.md`-only directives (`@bibliography`, `@glossary`, `@index`, `@map`, `@pods`, `@samples`, `@include`) are not needed for pod pages.

`MarkdownRenderer` — wraps `swift-markdown` or `cmark`.
Converts layer text (after directive expansion) to HTML.

`SearchIndex` — builds a simple in-memory index from all pod titles, subtitles, and surface text.
Used for the pod browser search bar.

### Layer 3: iOS UI (SwiftUI)

`PodListView` — browsable, searchable list of all pods.
Grouped by category or status.
Tap to open a pod.

`PodDetailView` — shows a pod's layers as tabs (Surface, Depth, Provenance, Script, Images).
Each tab shows the rendered HTML in a `WKWebView` (built on demand from the pod's source).
A raw-text escape hatch opens the pod file in an external editor (Files app or any text editor via `UIDocumentInteractionController`) for power editing, but this is not the primary editing path.

`PodBrowserView` — a `WKWebView` pointed at the locally-built site temp directory.
Allows navigating the built site as it would appear on the web.
Rebuilt on demand.

`ClaudeConversationView` — a full chat interface.
At session start, the app injects archive context into the system prompt (see Claude Integration below).
Editing is collaborative and inline: the user asks Claude to make a specific change ("revise the opening paragraph of surface"), Claude proposes the new text in the conversation, and the user accepts or pushes back.
No external editor is needed for the main authoring workflow — this is pair programming, not a handoff.
At session end, offers "Save to version history" and optionally "Write pod file(s)" for any pods Claude has drafted or revised.

`ContextualDiffSheet` — shown before any file write.
Rather than previewing the entire pod, this displays the specific changed passage centered within its layer text in a scrollable window.
The user can scroll up or down to see as much surrounding context as needed.
Changed text is highlighted (additions in green, removals in red).
The user confirms or cancels.
This design supports the pair-programming editing model: changes are small and targeted, and the preview reflects that granularity.

`SettingsView` — GitHub token entry and connection toggle.
Version store selector.
API key management.

`ExportView` — builds a zip of the `content/` directory (or a subset) for sharing or backup.
Uses `UIActivityViewController`.

NOTE we will also want to be able to export the full HTML of a site so it can be installed on a web server.

---

## Claude Integration

### Context injection

At the start of every Claude conversation, the app sends a system prompt containing:

1. A brief role description: "You are a collaborator on the SeedPods project. You have full knowledge of the existing pod archive."
2. The contents of `internal-structure.html`, `internal-grammar.html`, and `internal-directives.html` (or their source `.md` equivalents), so Claude knows the format.
3. A summary of the current archive.

### Archive context format

Rather than sending every pod in full (which becomes expensive as the archive grows), the app sends a two-level summary:

**Category summaries** (always included): one paragraph per category describing the pods it contains — their numbers, titles, and one-line subtitles.
This lets Claude notice overlap and make connections without consuming the full text of every pod.

**Full pod text** (included on demand): when the conversation references a specific pod by number or title, the app automatically appends that pod's full `.txt` source to the next message.
This keeps context lean while ensuring Claude can quote and edit actual prose when needed.

The `4u-ai.txt` file that the Python builder already generates is a good starting point for the category summary format — the iOS app generates an equivalent in memory at conversation start.

### Write-back flow

The primary editing model is collaborative and incremental — Claude proposes a specific change to a specific layer passage, not a full pod rewrite.
When Claude produces a change:

1. Claude outputs the proposed text in the conversation (a revised paragraph, a new section, a corrected sentence).
2. The app detects that the proposal applies to a known pod and layer (by context or by explicit Claude markup).
3. A `ContextualDiffSheet` appears showing the changed passage centered in a scrollable window, with surrounding context visible above and below, and changes highlighted.
4. If the user confirms, `SeedPodStore` applies the change surgically to the pod file in iCloud, and `VersionStore` records a snapshot with a note: "Revised [layer] of pod NNN in Claude conversation on [date]."
5. If GitHub sync is enabled, a commit is offered (not automatic).

For new pods (full file creation), the same flow applies but the diff sheet shows the complete new file against an empty baseline.

---

## Multi-Device Awareness

The app is designed to run on multiple devices simultaneously (iPhone and iPad, or two iPads). iCloud handles file sync but has no locking mechanism — two devices editing the same pod file concurrently will produce an iCloud conflict version.

### Presence indicators

When a user opens a pod layer for active editing on one device, the app writes a lightweight coordination record to iCloud:

```
content/.editing/NNN-shortname-surface.lock
```

The file contains a device identifier and timestamp.
Other devices opening the same pod check for this file and display a non-blocking warning: "Surface layer is being edited on your iPhone."
The lock is released when editing stops and expires automatically after a configurable timeout (default: 15 minutes) to handle crashes or lost connectivity.

This does not prevent simultaneous editing — it makes concurrent access visible.
For a single author across personal devices this is sufficient.

### Conflict resolution

If iCloud detects a conflict (two devices wrote different versions of the same file), the app surfaces this clearly in the pod list and detail view.
The user is offered a side-by-side diff and can choose which version to keep, or can ask Claude to help merge the two versions.

---

## HTML Rendering and Future Native UI

The primary rendering approach uses `WKWebView` — a full Safari engine embedded in the app.
It renders the existing HTML and CSS output from the site builder without modification, and is well-supported on all iOS versions.

A future direction is to render pod layers using native SwiftUI components rather than HTML — native text, native typography, native scroll behavior.
This would make the app feel more fully iOS-native and would open up features like inline editing within the rendered view.
This is a significant additional effort and is deferred post-MVP.
The `WKWebView` approach is the correct choice for MVP and will remain available as an option even if native rendering is added later.

---

### LocalVersionStore (default)

Snapshots are stored in `content/.versions/NNN-shortname/YYYYMMDD-HHMMSS.txt`.
A companion file `YYYYMMDD-HHMMSS.note` may contain the session summary.

The UI shows a version timeline per pod.
Reverting replaces the current file with the snapshot content (after confirmation) and writes a new snapshot marking the revert.

The store keeps the 20 most recent snapshots per pod.
Older ones are pruned automatically.

### GitHubVersionStore (optional)

Uses the GitHub REST API:

- `GET /repos/{owner}/{repo}/contents/{path}` — read current file and get its SHA
- `PUT /repos/{owner}/{repo}/contents/{path}` — write file with commit message and SHA

Commit messages are short and descriptive.
Claude can generate them from the conversation: "Added surface and depth layers for pod 043 (harmony)."

The GitHub token is stored in the iOS Keychain.
The user enters it once in Settings.
No local git binary, no SSH keys.

---

## iCloud File Layout

The app's iCloud container mirrors the existing repo structure:

```
content/
  pods/           ← pod .txt source files (NNN-shortname.txt)
  images/         ← image assets
  internal/       ← internal documentation .md files
  .versions/      ← local version snapshots (hidden from Files app)
config/
  settings.txt
  status.txt
  categories.json
  site.css
  logo.svg
```

The built site (HTML output) lives in a local temp directory, not in iCloud.
It is rebuilt on demand and not persisted between app launches.

---

## MVP Scope

**In scope for MVP:**

- Read all pod files from iCloud `content/pods/`
- Parse pods (full and proto)
- Pod list view with search and category grouping
- Pod detail view with layer tabs (rendered HTML via WKWebView)
- Claude conversation with archive context injection and write-back flow
- Local version store (snapshots)
- Build pod pages to temp directory; view in in-app browser
- Export zip of content directory
- GitHub commit (optional, settings-controlled)

**Deferred (post-MVP):**

- Index page, bibliography page, glossary page, map/graph page
- Full text search across all layer content
- Image import from camera roll
- Multi-user / sharing
- DAG visualization
- App Store distribution

---

## Key Constraints and Decisions

- **Do not change the `.txt` file format.** The Python build system must remain able to read any file the iOS app writes.
- **Directive expansion happens at render time only.** The raw `.txt` files always contain unexpanded directives. The renderer expands them when building HTML.
- **Status is not auto-computed.** The Python `check` tool validates status vs. layer count. The iOS app may warn but does not enforce.
- **Pod numbers are assigned by the user.** The app can suggest the next available number but does not auto-assign. The caching warning in `internal.html` applies: Claude should ask Darakshan for the current next valid pod number.
- **`#number` and `#shortname` are never written to pod files.** They are always derived from the filename.

---

## Reference Links

- Internal docs (published): `https://darakshan.github.io/SeedPods/internal.html`
- GitHub repo: `https://github.com/darakshan/SeedPods`
- Python source: `src/build.py`, `src/seedpod_parser.py`, `src/directive.py`
