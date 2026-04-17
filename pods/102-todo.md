@title To-Do List
@subtitle Ideas, questions, and tasks awaiting their pods.
@status proto
@date 2026-04-14
@category zzz-debug
@related 073

- Map of valence & arousal 3.4
- Everything has an inside and outside and a structure. The outside is a surface and a structure and so is the inside. Or maybe this is 2 orthogonal poles: inside–outside and surface–structure.
- AI is a mirror
- Be nice to your AI — extend @link(073). Other reasons.
- This is a memoir.
- Dipping into the river.
- The ratchet effect in evolution, engineering, science
- How does this obscure physics and philosophy stuff change our everyday thinking about our life?
- Science versus speculation versus fantasy. How our interior model of reality affects our behavior and our feelings. Why it's OK to speculate and even good as long as you can be aware of its probability (expectation)… and at the same time keep an open mind!
- **@aside directive** — Inline aside for content that matters but shouldn't interrupt flow. Syntax: `@aside(text)`. Semantically distinct from `@ref` (which points to sources) and `@note` (which is editorial and stripped from output). The aside is reader-facing content whose placement is left to the renderer — margin note, footnote, collapsible inline, etc. First use case: disambiguating "inside" (spatial vs. experiential) without breaking prose. See pod 078.
- **Bibliography backref wrapper** — Wrap backref links in `<span class="bib-backrefs">` so CSS can constrain them to a proper right-hand column. Current HTML puts bare `<a>` elements as siblings of `.bib-cite`, making two-column layout impossible with CSS alone.
- **Pending-changes indicator (short term)** — Show the number of uncommitted changes in the app nav bar, visible across all modes (chat, browse, split, feedback, settings). Tappable to go to the save/commit screen. Invisible at zero. Also set the iOS app icon badge to the same count so it's visible on the home screen without opening the app — a gentle "save your work" nudge that clears on commit.
- **Auto-commit with AI summary (longer term)** — Trigger auto-save at end of session, end of day, or N-change threshold. Server passes the list of changed files to the AI, which generates a one-line commit message. Commit happens silently. User sees the summary in settings and can override or revert. Eliminates the friction of manual commit messages while keeping the git history useful.
