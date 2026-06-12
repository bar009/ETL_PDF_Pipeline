"""
Intake New Source — the day-one command for a new PDF.

Wraps the mechanical part of INGEST_PLAYBOOK.md steps 1-2 so a new file
cannot skip the routing decision:

1. (optional) copy the PDF into the pdf dir and run preprocess Steps 1-4
   (extract, chunk, AI transform, consolidate) for that book only.
2. Scaffold a routing entry in work_routing.json with an EMPTY
   `applies_to_degrees`. Staging stays blocked until the operator fills it —
   this turns the "degree hidden behind the title" trap into a hard stop
   instead of silent misrouting (it bit three sources before this existed).
3. Diagnose the consolidated markdown shape and print which
   SOURCE_PREP_RUNBOOK.md case applies.

Usage:
    python PDF_handle/prod/cli/intake_new_source.py --pdf "C:/path/New Book.pdf"
    python PDF_handle/prod/cli/intake_new_source.py --book "New Book" --skip-preprocess
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for _candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

DEFAULT_PDF_DIR = PDF_HANDLE_ROOT / "PDF_books"
DEFAULT_CONSOLIDATED_DIR = PDF_HANDLE_ROOT / "consolidated_books"
DEFAULT_ROUTING = PDF_HANDLE_ROOT / "work_routing.json"
PREPROCESS_CLI = PDF_HANDLE_ROOT / "prod" / "cli" / "preprocess.py"


def slugify(stem: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def build_routing_scaffold(stem: str) -> dict:
    work_id = slugify(stem)
    return {
        "source_book_name": stem,
        "work_id": work_id,
        "staging_dir": work_id[:24].rstrip("-"),
        "work_title": stem,
        "primary_degree": "TODO",
        "source_kind": "TODO",
        "language": "en",
        # Empty on purpose: staging must stay blocked until the operator has
        # actually looked at the content and decided which degrees it touches.
        "applies_to_degrees": [],
        "default_visibility_level": "internal",
        "default_sensitivity_level": "guarded",
        "default_tradition_scope": "TODO",
        "library_category": "etl_imports",
    }


def ensure_routing_entry(routing_path: Path, stem: str) -> tuple[dict, bool]:
    """Return (entry, created). Never overwrites an existing entry."""
    routing = json.loads(routing_path.read_text(encoding="utf-8"))
    work_id = slugify(stem)
    for work in routing.get("works", []):
        if work.get("work_id") == work_id or work.get("source_book_name") == stem:
            return work, False
    entry = build_routing_scaffold(stem)
    routing.setdefault("works", []).append(entry)
    routing_path.write_text(json.dumps(routing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return entry, True


def diagnose_markdown(md_path: Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    headings = [l for l in lines if l.startswith("## ")]
    page_headings = [h for h in headings if re.match(r"^## Page \d+\s*$", h)]
    semantic_headings = len(headings) - len(page_headings)
    chapter_lines = sum(1 for l in lines if re.match(r"^CHAPTER [IVXLC]+\.", l.strip()))
    pause_lines = sum(
        1 for l in lines if re.search(r"\d+(?:st|nd|rd|th)\s+Pause:?", l, re.IGNORECASE)
    )
    longest_line = max((len(l) for l in lines), default=0)

    if pause_lines >= 3:
        case = "B (pause/commentary lecture): --pause-commentary --dedup-paragraphs"
    elif chapter_lines >= 2:
        case = "C (chapter book): chapter pre-pass, then --max-section-chars 12000"
    elif page_headings and semantic_headings < 5:
        case = "A (page-based OCR): drop page/running-header patterns, --min-section-chars 600"
    elif semantic_headings >= 5 and not page_headings:
        case = "already semantic — verify section stats, may need no prep"
    else:
        case = "mixed — read SOURCE_PREP_RUNBOOK.md and decide"

    return {
        "lines": len(lines),
        "headings": len(headings),
        "page_headings": len(page_headings),
        "semantic_headings": semantic_headings,
        "chapter_lines": chapter_lines,
        "pause_lines": pause_lines,
        "longest_line_chars": longest_line,
        "runbook_case": case,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--pdf", type=Path, help="Path to the new PDF (copied into --pdf-dir).")
    parser.add_argument("--book", help="Book stem if the PDF is already in place (or with --skip-preprocess).")
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    parser.add_argument("--consolidated-dir", type=Path, default=DEFAULT_CONSOLIDATED_DIR)
    parser.add_argument("--routing-config", type=Path, default=DEFAULT_ROUTING)
    parser.add_argument("--skip-preprocess", action="store_true", help="Consolidated markdown already exists.")
    parser.add_argument("--provider", default="gemini", choices=["gemini", "dry-run"])
    args = parser.parse_args()

    if not args.pdf and not args.book:
        raise SystemExit("Provide --pdf <path> or --book <stem>.")

    stem = args.book or args.pdf.stem
    print(f"[intake] source: {stem!r}")

    if args.pdf:
        args.pdf_dir.mkdir(parents=True, exist_ok=True)
        target = args.pdf_dir / args.pdf.name
        if not target.exists():
            shutil.copy2(args.pdf, target)
            print(f"[intake] copied PDF -> {target}")
        else:
            print(f"[intake] PDF already present: {target}")

    if not args.skip_preprocess:
        cmd = [
            sys.executable, str(PREPROCESS_CLI),
            "--book", stem,
            "--pdf-dir", str(args.pdf_dir),
            "--consolidated-dir", str(args.consolidated_dir),
            "--provider", args.provider,
        ]
        print(f"[intake] running preprocess Steps 1-4 ({args.provider}) ...")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            raise SystemExit(f"preprocess failed with exit code {result.returncode}")

    md_path = args.consolidated_dir / f"{stem}.md"
    if not md_path.exists():
        raise SystemExit(f"Consolidated markdown not found: {md_path}")

    entry, created = ensure_routing_entry(args.routing_config, stem)
    if created:
        print(f"[routing] scaffolded entry work_id={entry['work_id']} (applies_to_degrees EMPTY)")
    else:
        print(f"[routing] entry exists: work_id={entry['work_id']}")

    diagnosis = diagnose_markdown(md_path)
    print("[diagnosis]", json.dumps(diagnosis, indent=2))

    print()
    print("=" * 64)
    if not entry.get("applies_to_degrees"):
        print("BLOCKED — operator decisions required before staging:")
        print(f"  1. Open {args.routing_config}")
        print(f"     and fill applies_to_degrees for work_id={entry['work_id']}.")
        print("     Cover every degree whose content appears in the book,")
        print("     not just the degree in the title.")
        print("     Also replace the TODO fields (primary_degree, source_kind,")
        print("     default_tradition_scope) and review sensitivity.")
    print(f"  2. Prep the markdown per runbook case: {diagnosis['runbook_case']}")
    print("  3. Then follow INGEST_PLAYBOOK.md from step 3 (prep) onward.")
    print("=" * 64)
    if not entry.get("applies_to_degrees"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
