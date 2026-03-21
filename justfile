# SeedPods — build
# Requires: python3, just  (brew install just)
# Run `just setup` once to create .venv and install dependencies.

root := justfile_directory()
python := root + "/.venv/bin/python"

# Create venv and install dependencies (run once)
setup:
    python3 -m venv {{root}}/.venv
    {{root}}/.venv/bin/pip install -r {{root}}/requirements.txt

# Rebuild the full site (reads content/ and config/, writes d/ and index.html)
# For another deployment, set base URL: SITE_BASE_URL=https://yoursite.com/path just build
# Default: nugget count, @notes, file count. 
# just build -v to print every built file
build *args:
    {{python}} {{root}}/src/build.py {{args}}

# Serve the built site locally (default port 8000). Site dir must match config/settings.txt site_dir.
serve port="8000":
    @echo "Serving at http://localhost:{{port}}/"
    nohup python3 -m http.server {{port}} --directory {{root}}/docs > /dev/null 2>&1 &

# Find new explainer videos: show the agent prompt (copy into Cursor). When the agent completes, run: just build
find-explainers:
    @cat {{root}}/notes/recipe-find-explainers.md
    @echo ""
    @echo "When the agent completes, run: just build"

# Review nuggets: surface/depth length, in-degree, underlinked, final+TBD, #related max 5, #note. Exit 1 if any fail.
# just check         — summary + detailed findings (all nuggets)
# just check -q       — summary only
# just check -v       — summary + details + notes (interleaved by nugget)
# just check 3        — check only 003, show notes (implies -v)
# just check 3 4 19 99  — check 003, 004, 019; warn if 99 missing
check *ARGS:
    {{python}} {{root}}/src/check.py {{ARGS}}

# Sync content/pods/ with iCloud Drive SeedPods folder. Prints imported, exported, and conflicting files.
sync:
    {{python}} {{root}}/src/sync.py

# Like sync, but local files win all conflicts. Use on first run when local is authoritative.
sync-init:
    {{python}} {{root}}/src/sync.py --local-wins

# Import prototype .md files into content/pods. Prints table (shortname-number, #words, #related, title). Preview only; use --apply to write.
import *ARGS:
    {{python}} {{root}}/src/import_proto.py {{ARGS}}
