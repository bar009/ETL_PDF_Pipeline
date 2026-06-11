"""Convert a page-based consolidated markdown into semantic-heading sections.

Page-OCR consolidated books arrive as `## Page N` blocks. Step 5 needs
semantic `##` headings, one per knowledge unit. This tool:

1. Drops `## Page N` lines and bare page-number artifact lines.
2. Promotes in-text ALL-CAPS title lines to `## Heading` (title-cased).
3. Merges body text under the most recent heading; text before the first
   heading goes into a front-matter section the noise filter will reject.

Deterministic, no LLM. Review the output before staging — OCR noise in
heading detection is possible.

Usage:
    python restructure_page_md_to_semantic.py INPUT.md OUTPUT.md [--min-words 1] [--max-words 10]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PAGE_HEADING_RE = re.compile(r"^##\s+Page\s+\d+\s*$")
PAGE_NUMBER_LINE_RE = re.compile(r"^\s*\d{1,3}\s*$")

# An ALL-CAPS line is a heading candidate when it has no lowercase letters,
# at least one A-Z, and is short enough to be a title rather than shouted prose.
CAPS_LINE_RE = re.compile(r"^[^a-z]*[A-Z][^a-z]*$")

SMALL_WORDS = {"a", "an", "and", "at", "by", "for", "in", "of", "on", "or", "the", "to", "with"}


def looks_like_heading(line: str, *, min_words: int, max_words: int) -> bool:
    stripped = line.strip()
    if not stripped or not CAPS_LINE_RE.match(stripped):
        return False
    words = [w for w in re.split(r"\s+", stripped) if any(c.isalpha() for c in w)]
    if not (min_words <= len(words) <= max_words):
        return False
    # Reject lines that are mostly digits/punctuation (TOC rows, dates).
    alpha = sum(c.isalpha() for c in stripped)
    return alpha >= max(4, len(stripped) // 3)


def title_case(heading: str) -> str:
    words = heading.strip().split()
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if 0 < i < len(words) - 1 and lw in SMALL_WORDS:
            out.append(lw)
        else:
            out.append(lw[:1].upper() + lw[1:])
    return " ".join(out)


EXISTING_HEADING_RE = re.compile(r"^#{2,6}\s+(.*\S)\s*$")


def restructure(
    text: str, *, min_words: int, max_words: int, drop_patterns: list[re.Pattern[str]] | None = None
) -> str:
    drop_patterns = drop_patterns or []
    sections: list[tuple[str, list[str]]] = [("Front Matter", [])]
    for raw in text.splitlines():
        if PAGE_HEADING_RE.match(raw) or PAGE_NUMBER_LINE_RE.match(raw):
            continue
        stripped = raw.strip()
        existing = EXISTING_HEADING_RE.match(stripped)
        candidate = existing.group(1).strip() if existing else stripped
        if any(p.search(candidate) for p in drop_patterns):
            continue
        is_heading = bool(existing) or (
            not stripped.startswith(("*", "-", ">"))
            and looks_like_heading(raw, min_words=min_words, max_words=max_words)
        )
        if is_heading:
            title = title_case(candidate)
            # Page boundaries repeat the section title — merge, don't split.
            if title != sections[-1][0]:
                sections.append((title, []))
            continue
        sections[-1][1].append(raw)

    return sections


def render(sections: list[tuple[str, list[str]]], *, min_section_chars: int = 0) -> str:
    # Fold too-small sections back into the previous one as plain text:
    # a caps line with a tiny body is usually shouted dialogue or an OCR
    # artifact, not a real knowledge unit.
    folded: list[tuple[str, list[str]]] = []
    for title, lines in sections:
        body = "\n".join(lines).strip()
        if folded and len(body) < min_section_chars:
            folded[-1][1].extend(["", title, ""] + lines)
            continue
        folded.append((title, list(lines)))

    parts: list[str] = []
    for title, lines in folded:
        body = "\n".join(lines).strip()
        if not body and title == "Front Matter":
            continue
        parts.append(f"## {title}\n\n{body}\n")
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--min-words", type=int, default=1)
    parser.add_argument("--max-words", type=int, default=10)
    parser.add_argument(
        "--drop-pattern",
        action="append",
        default=[],
        help="Regex for running-header/artifact lines to drop entirely. Repeatable.",
    )
    parser.add_argument(
        "--min-section-chars",
        type=int,
        default=0,
        help="Sections with a body smaller than this fold back into the previous section.",
    )
    args = parser.parse_args()

    text = args.input.read_text(encoding="utf-8")
    sections = restructure(
        text,
        min_words=args.min_words,
        max_words=args.max_words,
        drop_patterns=[re.compile(p) for p in args.drop_pattern],
    )
    result = render(sections, min_section_chars=args.min_section_chars)
    args.output.write_text(result, encoding="utf-8")
    headings = result.count("\n## ") + (1 if result.startswith("## ") else 0)
    print(f"[done] {args.output} sections={headings}")


if __name__ == "__main__":
    main()
