"""
Sync content/ with iCloud Drive SeedPods folder (mirrors full directory tree).

State is tracked in .syncstate (JSON: relative-path → sha256 hash at last sync).
On first run (no .syncstate), files present in both with identical content are
recorded as already in sync; differing content is flagged as a conflict.

  --local-wins   On conflict, overwrite iCloud with local and record as synced.
                 Use this on first run when local is known to be authoritative.
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

CONTENT_DIR = Path(__file__).parent.parent / "content"
ICLOUD_DIR = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "com~apple~CloudDocs"
    / "SeedPods"
)
STATE_FILE = Path(__file__).parent.parent / ".syncstate"

SKIP = {".DS_Store"}


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def collect_files(base: Path) -> set[str]:
    return {
        str(f.relative_to(base))
        for f in base.rglob("*")
        if f.is_file() and f.name not in SKIP
    }


def main() -> None:
    local_wins = "--local-wins" in sys.argv

    if not ICLOUD_DIR.exists():
        print(f"iCloud folder not found: {ICLOUD_DIR}")
        return

    state = load_state()

    local_files = collect_files(CONTENT_DIR)
    icloud_files = collect_files(ICLOUD_DIR)
    all_files = local_files | icloud_files

    imported: list[str] = []
    exported: list[str] = []
    conflicts: list[str] = []
    new_state = dict(state)

    for rel in sorted(all_files):
        local_path = CONTENT_DIR / rel
        icloud_path = ICLOUD_DIR / rel
        saved_hash = state.get(rel)

        local_hash = file_hash(local_path) if local_path.exists() else None
        icloud_hash = file_hash(icloud_path) if icloud_path.exists() else None

        if local_hash is None and icloud_hash is None:
            new_state.pop(rel, None)

        elif local_hash is None:
            if saved_hash is None:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(icloud_path, local_path)
                new_state[rel] = icloud_hash
                imported.append(rel)
            elif icloud_hash != saved_hash:
                conflicts.append(rel)

        elif icloud_hash is None:
            if saved_hash is None:
                icloud_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(local_path, icloud_path)
                new_state[rel] = local_hash
                exported.append(rel)
            elif local_hash != saved_hash:
                conflicts.append(rel)

        else:
            local_changed = local_hash != saved_hash
            icloud_changed = icloud_hash != saved_hash

            if local_hash == icloud_hash:
                new_state[rel] = local_hash
            elif local_changed and not icloud_changed:
                icloud_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(local_path, icloud_path)
                new_state[rel] = local_hash
                exported.append(rel)
            elif icloud_changed and not local_changed:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(icloud_path, local_path)
                new_state[rel] = icloud_hash
                imported.append(rel)
            else:
                if local_wins:
                    icloud_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(local_path, icloud_path)
                    new_state[rel] = local_hash
                    exported.append(rel)
                else:
                    conflicts.append(rel)

    save_state(new_state)

    def fmt(items: list[str]) -> str:
        return ", ".join(items) if items else "(none)"

    print(f"Imported:  {fmt(imported)}")
    print(f"Exported:  {fmt(exported)}")
    print(f"Conflicts: {fmt(conflicts)}")


if __name__ == "__main__":
    main()
