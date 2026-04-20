@title Gossamer App Test
@subtitle A framework for collections of linked ideas
@status proto
@version 14
@date 2026-03-27
@category zzz-debug
@tags meta, framework, software, collections

Gossamer is an iOS/macOS app for building and exploring collections of linked ideas, with an AI collaborator to help think things through. SeedPods is one such collection. Yours might be something else entirely.

## What a Collection Is

A collection is a directory of markdown files:
- `content/pods/` — the pods themselves
- `content/config/` — settings, categories, styling
- `content/about/`, `content/more/`, etc. — supporting pages
- `content/internal/` — documentation

Each pod has metadata fields (#title, #subtitle, #status, #date, #category, #tags), up to six content layers (surface, depth, provenance, script, images, brief), and links to other pods via @link(NNN) syntax.

## The AI Collaborator

Claude has access to the full archive index, can read any file on request, and can propose edits via structured edit blocks. Edits are applied silently — Claude proposes, the user accepts, the file is written. Claude receives no confirmation; it learns the edit succeeded when the user sends their next message.

## To-Do

- [ ] **Bug: `field` + `mode: set` replaces entire file**: When Claude uses the edit protocol with `field: title` and `mode: set`, the app appears to replace the entire file with just the block content, rather than surgically replacing only that metadata line. Workaround: use `mode: patch` with find/replace for metadata changes. The system prompt or edit protocol documentation should clarify this — or the app behavior should be fixed.
- [ ] **UI: nav bar should be sticky**: The page navigation bar scrolls away with content. It should remain fixed at the top.
- [ ] **UI: translucent blur behind top panels**: Both the chat pane and browse pane should have a translucent panel with blur effect behind the top info area, so scrolling content is visible but muted beneath it.
- [x] **BROWSE directive working**: Opens as a bottom sheet that can be dismissed by swiping down. Clean interaction.
- [ ] **Bug: build cache not always invalidating**: After an edit is accepted, the built HTML sometimes doesn't update until app restart. "Force rebuild" in settings gives no feedback. The build should either auto-trigger reliably when switching to browse, or force rebuild should confirm it ran.
- [ ] **Bug: scroll position after accepting edit**: Conversation view scrolls away after accepting. Should maintain position.
- [ ] Define generic vocabulary (what to call a pod in other collections)
- [ ] Create minimal starter template for new collections
- [ ] Document onboarding flow for new users
- [ ] Write the "first run" greeting prompt
- [ ] Specify what's SeedPods-specific vs. framework-generic
- [ ] Design collection switching UX
- [ ] Document the edit protocol for AI collaborators
- [ ] Create example collections (recipe collection? research notes? worldbuilding?)

Gossamer emerged from the SeedPods project in March 2026. Christopher Alexander's "A Pattern Language" is the structural ancestor.
