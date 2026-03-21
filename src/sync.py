"""
Sync content/pods/*.txt with iCloud Drive SeedPods folder.

State is tracked in .syncstate (JSON: filename → sha256 hash at last sync).
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

PODS_DIR = Path(__file__).parent.parent / "content" / "pods"
ICLOUD_DIR = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "com~apple~CloudDocs"
    / "SeedPods"
)
STATE_FILE = Path(__file__).parent.parent / ".syncstate"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def stem(filename: str) -> str:
    return filename.removesuffix(".txt")


def main() -> None:
    local_wins = "--local-wins" in sys.argv

    if not ICLOUD_DIR.exists():
        print(f"iCloud folder not found: {ICLOUD_DIR}")
        return

    state = load_state()

    local_files = {f.name for f in PODS_DIR.glob("*.txt")}
    icloud_files = {f.name for f in ICLOUD_DIR.glob("*.txt")}
    all_files = local_files | icloud_files

    imported: list[str] = []
    exported: list[str] = []
    conflicts: list[str] = []
    new_state = dict(state)

    for fname in sorted(all_files):
        local_path = PODS_DIR / fname
        icloud_path = ICLOUD_DIR / fname
        saved_hash = state.get(fname)

        local_hash = file_hash(local_path) if local_path.exists() else None
        icloud_hash = file_hash(icloud_path) if icloud_path.exists() else None

        if local_hash is None and icloud_hash is None:
            new_state.pop(fname, None)

        elif local_hash is None:
            if saved_hash is None:
                shutil.copy2(icloud_path, local_path)
                new_state[fname] = icloud_hash
                imported.append(stem(fname))
            elif icloud_hash != saved_hash:
                conflicts.append(stem(fname))

        elif icloud_hash is None:
            if saved_hash is None:
                shutil.copy2(local_path, icloud_path)
                new_state[fname] = local_hash
                exported.append(stem(fname))
            elif local_hash != saved_hash:
                conflicts.append(stem(fname))

        else:
            local_changed = local_hash != saved_hash
            icloud_changed = icloud_hash != saved_hash

            if local_hash == icloud_hash:
                new_state[fname] = local_hash
            elif local_changed and not icloud_changed:
                shutil.copy2(local_path, icloud_path)
                new_state[fname] = local_hash
                exported.append(stem(fname))
            elif icloud_changed and not local_changed:
                shutil.copy2(icloud_path, local_path)
                new_state[fname] = icloud_hash
                imported.append(stem(fname))
            else:
                if local_wins:
                    shutil.copy2(local_path, icloud_path)
                    new_state[fname] = local_hash
                    exported.append(stem(fname))
                else:
                    conflicts.append(stem(fname))

    save_state(new_state)

    def fmt(items: list[str]) -> str:
        return ", ".join(items) if items else "(none)"

    print(f"Imported:  {fmt(imported)}")
    print(f"Exported:  {fmt(exported)}")
    print(f"Conflicts: {fmt(conflicts)}")


if __name__ == "__main__":
    main()
