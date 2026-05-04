"""
Sync sibling project files into the unified tool's deploy folder.

Run this BEFORE `vercel deploy`:
    python scripts/sync.py

Locally the unified Flask app imports core tool modules directly from sibling
project folders via sys.path injection — siblings are the source of truth.
On Vercel siblings aren't part of the deploy bundle, so we copy:

  - tools/_synced/<module>.py    — Python fallback (used by api/index.py)
  - api/letter_generate.js       — Node Vercel handler for the Letter tab

Both targets are gitignored — they are build artifacts, refreshed each deploy.
"""
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SIBLINGS_ROOT = PROJECT_ROOT.parent

COPIES = [
    # (sibling-relative source, unified-tool-relative destination)
    ("Checklist extractor/tools/checklist_extract.py",     "tools/_synced/checklist_extract.py"),
    ("Risk library export/tools/risk_library_export.py",   "tools/_synced/risk_library_export.py"),
    ("Note visibility/tools/note_visibility_report.py",    "tools/_synced/note_visibility_report.py"),
    ("Letter export/tools/letter_extract.py",              "tools/_synced/letter_extract.py"),
    ("Letter export/tools/generate_docx.js",               "tools/_synced/generate_docx.js"),
    ("Letter export/api/generate.js",                      "api/letter_generate.js"),
]


def main() -> int:
    missing = []
    copied = []
    for src_rel, dst_rel in COPIES:
        src = SIBLINGS_ROOT / src_rel
        dst = PROJECT_ROOT / dst_rel
        if not src.exists():
            missing.append(src_rel)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append((src_rel, dst_rel))

    for src_rel, dst_rel in copied:
        print(f"  copied  {src_rel}")
        print(f"       -> {dst_rel}")

    if missing:
        print("\nERROR: missing sibling files:")
        for m in missing:
            print(f"  - {m}")
        return 1

    print(f"\nSynced {len(copied)} file(s). Ready for `vercel deploy`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
