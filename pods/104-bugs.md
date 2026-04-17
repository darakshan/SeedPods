@title Bugs
@subtitle Known issues and quirks tracked during development.
@status proto
@date 2026-04-16
@category zzz-debug
@related 102

## Open

1. **Keyboard retraction layout bug** — When the keyboard retracts, the windows above it sometimes don't expand to fill the vacated space.
2. **Glossary backlink scroll position** — Clicking a backlink from the glossary to a pod positions the anchor under the sticky nav/section tabs. Need scroll-margin-top on ref anchor elements.
3. **Glossary should merge same-term definitions** — Multiple pods defining the same @term should appear under a single heading in the glossary, with each definition listed beneath it (similar to how the bibliography groups refs by keyword).
4. **@term should accept name without definition** — `@term Panpsychism` (no colon, no definition) should be valid, treated as an assertion that the term is defined elsewhere. The glossary should link it to the pod but not display a blank definition.
5. **Check button in Settings doesn't work** — The check/validate button in the Settings screen appears non-functional.

## Fixed

(none yet)
