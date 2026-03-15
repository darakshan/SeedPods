# Explainers for glossary terms

**Goal:** Point readers from glossary terms to external explainer videos (e.g. YouTube) where helpful. Nuggets are observations and don’t get explainers; scripts serve that role. Terms are different — they’re definitions that collect in the index (Glossary / tags), and many have good third‑party explainers.

**Where links live:** In the nugget where the term is introduced. Same place as the `#term` line (terms may appear anywhere in a nugget). So the canonical store is the nugget file.

**How (when we implement):** Add an optional explainer URL per term (and duration for display). For example a directive immediately after `#term`, e.g. `#explainer https://... (13 min)`, applying to the preceding term. Parser would expose terms as (term, definition, url_or_empty, duration_or_empty). Glossary page (and any other place we present terms) shows the link when present, with the duration next to it — e.g. "Explain (13 min)" or "Explain (45 min)". No need to label long ones "deep dive"; the length is enough.

**List:** Keep the list we’ve in `notes/explainers-for-terms.md`. Format: one line per video, `- https://... (X min, Title)` or `- https://... (Title)`; use title/source only, no "check duration" in the parenthetical. No parenthetical → link shows as "Watch".

**Curation:** Goal is a short one and the best one. Prefer under 10 minutes; ideally around 5. Always record duration with each link so we can show it in the UI. When choosing: length, ratings (if you check), and source reputation (e.g. Numberphile, Veritasium, PBS Space Time, Computerphile, Fermilab, TED, Serious Science — known-good explainer channels). Source is for our curation only; we don't show it to the user.

No urgency; the list can grow gradually.
