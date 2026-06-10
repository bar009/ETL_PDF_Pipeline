"""
Duncan MM Section Map — Apply
==============================
Rewrites `consolidated_books/Duncan's Masonic Ritual and Monitor of Freemasonry complete 1866 3rd ed.md`
so that the Step 5 section extractor sees meaningful section boundaries instead of 536 individual
page-level headings.

Problem:
  The pypdf-fallback OCR engine produces `## Page N` headings for every scan page.
  extract_sections() picks those up as 536 structural headings and creates 557 micro-sections,
  almost all classified as `fragmentary_topic` or `page_fragment` and skipped by discovery.
  The MM narrative cluster (Hiram, Five Points, Monument, etc.) is spread across ~40 pages
  of ceremony dialogue — no heading survives to label the section, so it never surfaces.

Fix:
  1. Demote ALL `## Page N` headings to `#### Page N` (depth > 3, excluded from heading_matches).
  2. Inject synthetic `## <section_title>` headings at the correct page boundaries.
  Result: extract_sections() finds 5–8 meaningful h2 sections covering the MM chapter,
  plus the existing h3 sub-sections (### THE HOUR-GLASS, ### THE SCYTHE, etc.) within them.

Run once before a clean rerun:
  python3 PDF_handle/prod/cli/duncan_section_map_apply.py [--dry-run] [--verify]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for _candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

from PDF_handle.prod.core.io import read_text, write_text
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
CONSOLIDATED_DIR = PDF_HANDLE_ROOT / "consolidated_books"
BOOK_NAME = "Duncan's Masonic Ritual and Monitor of Freemasonry complete 1866 3rd ed"
TARGET_MD = CONSOLIDATED_DIR / f"{BOOK_NAME}.md"

# ---------------------------------------------------------------------------
# Section map: (start_scan_page_inclusive, synthetic_title, degree_hint)
# Each entry inserts a ## heading BEFORE that scan page's content.
# Pages before the first entry and between entries are merged into the preceding section.
# ---------------------------------------------------------------------------
SECTION_MAP: list[tuple[int, str, str]] = [
    # Entered Apprentice chapter
    (9,   "Entered Apprentice: Ceremony, Symbols, Working Tools", "level1"),
    # Fellow Craft chapter
    (75,  "Fellow Craft: Winding Stairs, Middle Chamber, Shibboleth", "level2"),
    # Master Mason opening & obligation (pre-narrative)
    (155, "Master Mason: Opening, Obligation, Overview", "level3"),
    # Hiram narrative begins at scan p.165 (book p.93)
    # Title avoids "The..." + 8-token pattern that triggers fragmentary_topic classifier.
    (165, "Hiram Abiff: Legend, Murder, Burial, and Discovery", "level3"),
    # Raising, Grand Hailing Sign, Five Points of Fellowship
    (210, "Grand Hailing Sign: Five Points of Fellowship", "level3"),
    # Historical account: Monument, Weeping Virgin, Lost Word
    (213, "Monument and Weeping Virgin: Historical Account", "level3"),
    # Monitor Emblems — h3 sub-sections (THE HOUR-GLASS etc.) handle individual topics
    (219, "MM Monitor Emblems: Three Steps, Beehive, Anchor, Ark", "level3"),
    # Mark Master and higher degrees (beyond scope of v2.0 target)
    (267, "Mark Master and Higher Degrees", "level3"),
]

PAGE_HEADING_RE = re.compile(r"^## (Page \d+)$", re.MULTILINE)


def build_section_lookup(section_map: list[tuple[int, str, str]]) -> dict[int, tuple[str, str]]:
    """Return {scan_page_number: (title, degree_hint)}."""
    return {page: (title, degree) for page, title, degree in section_map}


def apply_section_map(text: str, section_lookup: dict[int, tuple[str, str]]) -> str:
    """
    1. Replace every `## Page N` with `#### Page N` (demote to h4).
    2. Before the demoted heading for the FIRST occurrence of each section-start page,
       inject `## <title>`.  Subsequent occurrences of the same page number (duplicate
       OCR passes present in some pypdf outputs) are demoted without re-injection.
    """
    injected: set[int] = set()

    def replace_page_heading(m: re.Match) -> str:
        page_label = m.group(1)  # e.g. "Page 165"
        page_num_str = page_label.split()[-1]
        try:
            page_num = int(page_num_str)
        except ValueError:
            return f"#### {page_label}"

        demoted = f"#### {page_label}"
        if page_num in section_lookup and page_num not in injected:
            injected.add(page_num)
            title, _ = section_lookup[page_num]
            return f"## {title}\n\n{demoted}"
        return demoted

    return PAGE_HEADING_RE.sub(replace_page_heading, text)


def verify_result(original: str, rewritten: str) -> list[str]:
    """Return a list of issues found in the rewritten text."""
    issues: list[str] = []

    # No ## Page N headings should remain (they should all be ####)
    remaining_page_h2 = PAGE_HEADING_RE.findall(rewritten)
    if remaining_page_h2:
        issues.append(f"Still has {len(remaining_page_h2)} ## Page N headings after rewrite")

    # Count injected ## section headings
    h2_headings = re.findall(r"^## .+", rewritten, re.MULTILINE)
    if len(h2_headings) < len(SECTION_MAP):
        issues.append(f"Expected >= {len(SECTION_MAP)} h2 headings, got {len(h2_headings)}")

    # Text content should be preserved (length within 5%)
    ratio = len(rewritten) / max(len(original), 1)
    if not (0.95 <= ratio <= 1.10):
        issues.append(f"Rewritten text length ratio {ratio:.3f} outside expected 0.95–1.10")

    # Each section title from the map should appear in the rewritten text
    for _, (title, _) in build_section_lookup(SECTION_MAP).items():
        if f"## {title}" not in rewritten:
            issues.append(f"Missing injected section heading: {title!r}")

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Print what would change without writing")
    parser.add_argument("--verify", action="store_true", help="Verify the output and exit 1 if issues found")
    parser.add_argument("--input", type=Path, default=TARGET_MD, help="Input markdown path")
    parser.add_argument("--output", type=Path, default=None, help="Output path (default: overwrite input)")
    args = parser.parse_args()

    input_path = args.input.resolve()
    output_path = (args.output or args.input).resolve()

    if not input_path.exists():
        print(f"[error] Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    original = read_text(input_path)
    section_lookup = build_section_lookup(SECTION_MAP)

    print(f"[info] Input: {input_path}")
    print(f"[info] Section map: {len(SECTION_MAP)} synthetic sections defined")

    # Count before
    before_h2 = len(re.findall(r"^## .+", original, re.MULTILINE))
    before_page_h2 = len(PAGE_HEADING_RE.findall(original))
    print(f"[before] h2 headings total: {before_h2}  (## Page N: {before_page_h2})")

    rewritten = apply_section_map(original, section_lookup)

    # Count after
    after_h2 = len(re.findall(r"^## .+", rewritten, re.MULTILINE))
    after_page_h4 = len(re.findall(r"^#### Page \d+", rewritten, re.MULTILINE))
    print(f"[after]  h2 headings total: {after_h2}  (#### Page N demoted: {after_page_h4})")

    issues = verify_result(original, rewritten)
    if issues:
        print(f"\n[warn] {len(issues)} issue(s) found:", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        if args.verify:
            sys.exit(1)
    else:
        print("[verify] OK — all checks passed")

    if args.dry_run:
        print("[dry-run] No file written.")
        # Print a summary of what sections would be injected
        print("\nSections that would be injected:")
        for page_num, (title, degree) in sorted(section_lookup.items()):
            print(f"  Before ## Page {page_num}: ## {title}  [{degree}]")
        return

    write_text(output_path, rewritten)
    print(f"[done] Written to {output_path}")


if __name__ == "__main__":
    main()
