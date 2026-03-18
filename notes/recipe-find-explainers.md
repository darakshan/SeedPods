# Recipe: Find new explainers

Use this to launch a background agent that finds explainer videos for glossary terms, then runs the site build so the explainers page and Index are updated.

## Steps

1. Run `just find-explainers` to print the agent prompt (or open this file).
2. In Cursor, ask the agent to run a background task with that prompt.
3. When the agent completes, it will run `just build` (or you can run it). Then:
   - `notes/explainers-for-terms.md` is turned into `explainers.html` in site_dir (terms sorted, pod numbers as links, video URLs as links with descriptive text).
   - `tags.html` is rebuilt with a Terms section linking each term to the explainers page.

If the agent does not run the build, run `just build` yourself.

## Agent prompt

Copy and adapt this prompt when asking for a background agent:

---

You are in the SeedPods repo. Read `notes/explainers-design.md` and `notes/explainers-for-terms.md`.

Task: Find YouTube (or similar) explainer videos for glossary terms that still have no link or could use a better one. Focus on terms in the "Still to search" section first; then any term that only has "(check duration)" links or long videos. Follow the guidelines: under 10 min ideally ~5, reputable sources, note duration for every link.

Update `notes/explainers-for-terms.md`: add new links as bullet lines under the right term with format `- https://... (X min, optional title/source)`. If you cannot confirm duration, use "(check duration)". Update or remove the "Still to search" section as needed.

When you have finished updating the file, run the build so the site reflects your changes. From the repo root, run: `just build`

---
