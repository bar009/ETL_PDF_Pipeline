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
        # Mixed-case words and short acronyms (VIII, MM) are already deliberate.
        bare = w.rstrip(":.,;")
        if any(c.islower() for c in w) or (bare.isupper() and len(bare) <= 4 and i > 0):
            out.append(w)
            continue
        lw = w.lower()
        if 0 < i < len(words) - 1 and lw in SMALL_WORDS:
            out.append(lw)
        else:
            out.append(lw[:1].upper() + lw[1:])
    return " ".join(out)


EXISTING_HEADING_RE = re.compile(r"^#{2,6}\s+(.*\S)\s*$")


def restructure(
    text: str,
    *,
    min_words: int,
    max_words: int,
    drop_patterns: list[re.Pattern[str]] | None = None,
    body_patterns: list[re.Pattern[str]] | None = None,
) -> list[tuple[str, list[str]]]:
    drop_patterns = drop_patterns or []
    body_patterns = body_patterns or []
    sections: list[tuple[str, list[str]]] = [("Front Matter", [])]
    for raw in text.splitlines():
        if PAGE_HEADING_RE.match(raw) or PAGE_NUMBER_LINE_RE.match(raw):
            continue
        stripped = raw.strip()
        existing = EXISTING_HEADING_RE.match(stripped)
        candidate = existing.group(1).strip() if existing else stripped
        if any(p.search(candidate) for p in drop_patterns):
            continue
        if any(p.search(candidate) for p in body_patterns):
            sections[-1][1].append(raw)
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


# Tolerates list prefixes ('1.  '), bold markers, and heading hashes:
# '1.  **1st Pause:** desc' / '**9th Pause:** desc' / '### 9th Pause'
PAUSE_RE = re.compile(
    r"^(?:\d+\.\s+)?(?:#+\s*)?\*{0,2}(\d+)(?:st|nd|rd|th)\s+Pause:?\*{0,2}\s*(.*)$",
    re.IGNORECASE,
)
COMMENTARY_RE = re.compile(r"^\*{0,2}Commentary:?\*{0,2}\s*(.*)$", re.IGNORECASE)


def convert_pause_commentary(text: str) -> str:
    """Convert 'Nth Pause: <when>' / 'Commentary: <text>' lecture format into
    semantic sections: the pause description becomes the section heading,
    the commentary becomes the body. Lines outside pause blocks pass through."""
    out: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        pause = PAUSE_RE.match(stripped)
        if pause:
            desc = pause.group(2).strip().rstrip(".")
            title = f"Pause {pause.group(1)}: {desc}" if desc else f"Pause {pause.group(1)}"
            out.append(f"## {title}")
            out.append("")
            continue
        commentary = COMMENTARY_RE.match(stripped)
        if commentary:
            out.append(commentary.group(1))
            continue
        out.append(raw)
    return "\n".join(out)


def dedup_repeated_paragraphs(sections: list[tuple[str, list[str]]]) -> list[tuple[str, list[str]]]:
    """Drop paragraphs already seen earlier in the document (normalized
    whitespace) — double-OCR sources repeat whole page spans verbatim.
    Also drops repeated sections wholesale when every paragraph is a repeat."""
    seen: set[str] = set()
    result: list[tuple[str, list[str]]] = []
    for title, lines in sections:
        kept: list[str] = []
        for para in "\n".join(lines).split("\n\n"):
            key = re.sub(r"\s+", " ", para).strip().lower()
            if not key:
                continue
            if key in seen:
                continue
            seen.add(key)
            kept.append(para)
        if kept:
            result.append((title, "\n\n".join(kept).splitlines()))
    return result


def split_oversized(
    sections: list[tuple[str, list[str]]], *, max_section_chars: int
) -> list[tuple[str, list[str]]]:
    """Split sections larger than max_section_chars at paragraph boundaries,
    titling continuations '<title> (Part N)'."""
    result: list[tuple[str, list[str]]] = []
    for title, lines in sections:
        body = "\n".join(lines)
        if len(body) <= max_section_chars:
            result.append((title, lines))
            continue
        paragraphs = body.split("\n\n")
        # OCR text sometimes lacks blank lines entirely — fall back to
        # line-level chunks so a single huge "paragraph" can still split.
        if any(len(p) > max_section_chars for p in paragraphs):
            paragraphs = [p2 for p in paragraphs for p2 in p.split("\n")]
        # Last resort: run-on OCR lines with no newlines split at sentence ends.
        if any(len(p) > max_section_chars for p in paragraphs):
            paragraphs = [s for p in paragraphs for s in re.split(r"(?<=\.) (?=[A-Z\"'])", p)]
        # Absolute fallback for sentence-less OCR garbage: hard fixed-width slices.
        if any(len(p) > max_section_chars for p in paragraphs):
            paragraphs = [
                p[i : i + max_section_chars]
                for p in paragraphs
                for i in range(0, len(p), max_section_chars)
            ]
        chunk: list[str] = []
        size = 0
        part = 1
        for para in paragraphs:
            if chunk and size + len(para) > max_section_chars:
                name = title if part == 1 else f"{title} (Part {part})"
                result.append((name, "\n\n".join(chunk).splitlines()))
                part += 1
                chunk, size = [], 0
            chunk.append(para)
            size += len(para) + 2
        if chunk:
            name = title if part == 1 else f"{title} (Part {part})"
            result.append((name, "\n\n".join(chunk).splitlines()))
    return result


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
        "--body-pattern",
        action="append",
        default=[],
        help="Regex for lines that must stay body text and never become headings (e.g. figure captions). Repeatable.",
    )
    parser.add_argument(
        "--min-section-chars",
        type=int,
        default=0,
        help="Sections with a body smaller than this fold back into the previous section.",
    )
    parser.add_argument(
        "--max-section-chars",
        type=int,
        default=0,
        help="Split sections larger than this at paragraph boundaries into '(Part N)' continuations. 0 disables.",
    )
    parser.add_argument(
        "--pause-commentary",
        action="store_true",
        help="Pre-pass for 'Nth Pause: / Commentary:' lecture sources: pause text becomes the heading, commentary the body.",
    )
    parser.add_argument(
        "--dedup-paragraphs",
        action="store_true",
        help="Drop paragraphs repeated verbatim earlier in the document (double-OCR cleanup).",
    )
    args = parser.parse_args()

    text = args.input.read_text(encoding="utf-8")
    if args.pause_commentary:
        text = convert_pause_commentary(text)
    sections = restructure(
        text,
        min_words=args.min_words,
        max_words=args.max_words,
        drop_patterns=[re.compile(p) for p in args.drop_pattern],
        body_patterns=[re.compile(p) for p in args.body_pattern],
    )
    if args.dedup_paragraphs:
        sections = dedup_repeated_paragraphs(sections)
    if args.max_section_chars:
        sections = split_oversized(sections, max_section_chars=args.max_section_chars)
    result = render(sections, min_section_chars=args.min_section_chars)
    args.output.write_text(result, encoding="utf-8")
    headings = result.count("\n## ") + (1 if result.startswith("## ") else 0)
    print(f"[done] {args.output} sections={headings}")


if __name__ == "__main__":
    main()
