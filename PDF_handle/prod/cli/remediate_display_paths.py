"""
Remediate Display Paths — strip absolute local paths from reader-facing text.

The display-text hygiene gate (validate_runtime check 6) rejects absolute
local paths in reader-facing fields. Data staged before display_source_path()
existed (2026-06-12) carries them in source_path / source_notes / work-title
provenance. This tool rewrites every absolute path substring in the display
fields of the live datasets to its display form (repo anchor or file name),
in place, with backups.

Dry-run by default:
    python PDF_handle/prod/cli/remediate_display_paths.py --site-root <ROOT>
    python PDF_handle/prod/cli/remediate_display_paths.py --site-root <ROOT> --apply
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for _candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

from PDF_handle.prod.schema.patches import display_source_path

# Mirror the gate's field lists (validate_runtime.py); a field the gate checks
# is a field we must clean.
DISPLAY_STRING_FIELDS = (
    "title",
    "short_summary",
    "full_summary",
    "symbolic_meaning",
    "candidate_lesson",
    "work_title",
    "source_heading",
    "source_path",
)
DISPLAY_LIST_FIELDS = ("source_notes", "tags")

# An absolute path substring: drive letter, UNC, or POSIX home path, up to
# whitespace/quote/closing punctuation.
PATH_SUBSTRING = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\|/(?:home|Users)/)[^\s'\"()\[\]]*")

DATA_FILES = ("library.json", "level1.json", "level2.json", "level3.json")


def clean_text(text: str) -> str:
    return PATH_SUBSTRING.sub(lambda m: display_source_path(m.group(0)), text)


def remediate_dataset(data: dict) -> int:
    changed = 0
    for entry in data.get("entries", []):
        for field in DISPLAY_STRING_FIELDS:
            value = entry.get(field)
            if isinstance(value, str) and value:
                cleaned = clean_text(value)
                if cleaned != value:
                    entry[field] = cleaned
                    changed += 1
        for field in DISPLAY_LIST_FIELDS:
            value = entry.get(field)
            if isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, str) and item:
                        cleaned = clean_text(item)
                        if cleaned != item:
                            value[i] = cleaned
                            changed += 1
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--site-root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run).")
    args = parser.parse_args()

    data_dir = args.site_root / "data"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S+00-00")
    backup_dir = data_dir / "remediation_backups" / stamp

    total = 0
    for name in DATA_FILES:
        path = data_dir / name
        if not path.exists():
            print(f"[skip] {name} not found")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        changed = remediate_dataset(data)
        total += changed
        print(f"[{'write' if args.apply else 'dry-run'}] {name}: {changed} field(s) cleaned")
        if args.apply and changed:
            backup_dir.mkdir(parents=True, exist_ok=True)
            (backup_dir / name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.apply and total:
        print(f"[backup] originals in {backup_dir}")
    print(f"[done] mode={'live-write' if args.apply else 'preview-only'} total_cleaned={total}")


if __name__ == "__main__":
    main()
