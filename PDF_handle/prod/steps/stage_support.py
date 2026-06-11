from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from PDF_handle.prod.core.text import normalize_newlines
from PDF_handle.prod.schema import normalize_nullable_string, normalize_string_array, normalize_text, unique_strings


IMAGE_ONLY_LINE_RE = re.compile(r"^!\[[^\]]*\]\([^)]+\)\s*$", re.MULTILINE)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
PAUSE_RE = re.compile(
    r"^(?:\*\*)?(?P<title>\d+(?:st|nd|rd|th)\s+Pause):?(?:\*\*)?\s*:?\s*(?P<tail>.*)$",
    re.MULTILINE,
)
GENERIC_MARKER_RE = re.compile(
    r"^(?P<title>(?:Part|Chapter|Lecture|Section|First Section|Second Section|Third Section)[^\n]*)$",
    re.IGNORECASE | re.MULTILINE,
)
SECTION_BREAK_RE = re.compile(r"\n{2,}")
PAGE_TITLE_RE = re.compile(r"^page\s+\d+[a-z]?$", re.IGNORECASE)
LEADING_PAGE_HEADER_RE = re.compile(r"^\d+\s+[A-Z][A-Z0-9\s,'’&.-]{4,100}$")
TRAILING_PAGE_HEADER_RE = re.compile(r"^[A-Z][A-Z0-9\s,'’&.-]{4,100}\s+\d+$")
RUNNING_HEADER_RE = re.compile(
    r"\b(?:BLUE LODGE RITUAL REFERENCE GUIDE|RITUAL REFERENCE GUIDE|TEXT BOOK)\b",
    re.IGNORECASE,
)
TABLE_OF_CONTENTS_RE = re.compile(r"\b(?:table of contents|contents)\b", re.IGNORECASE)
APPARATUS_TITLE_RE = re.compile(
    r"^(?:footnotes?|endnotes?|index|bibliography|references|appendix|introduction|extracts?\s+from|masonic\s+calendar|pronunciation\s+guide|suggested\s+fellow\s+craft\s+roll)\.?$",
    re.IGNORECASE,
)
FRONT_MATTER_HINT_RE = re.compile(
    r"\b(?:copyright|all rights reserved|published by|printed by|isbn|library of congress|edition)\b",
    re.IGNORECASE,
)
TITLE_PAGE_FRAGMENT_RE = re.compile(
    r"^(?:title page|click to enlarge|duncan'?s|exposition of the mysteries\.?\s*an?)$",
    re.IGNORECASE,
)
OFFICER_LIST_HINT_RE = re.compile(
    r"\b(?:officers|grand officers|past masters|grand lodge officers|roll of officers)\b",
    re.IGNORECASE,
)
HONORIFIC_PERSON_TITLE_RE = re.compile(
    r"^(?:dr|mr|mrs|ms|bro|w\.?\s*bro|r\.?\s*w\.?|rev)\.?\s+[a-z][a-z\s.'-]+(?:,\s*(?:pgm|gm|pm|ddgm))?$",
    re.IGNORECASE,
)
TITLE_LINE_RE = re.compile(r"^\s{0,3}(?:#{1,6}\s+)?(?P<title>[^\n]{3,120})\s*$", re.MULTILINE)
PROCEDURAL_LEAD_RE = re.compile(
    r"^(?:after|at the end|at the close|before|when|where|while|once|upon|during|as soon as|as the|if the|if he|if she|any brother|no brother|every brother|each brother)\b",
    re.IGNORECASE,
)
PROCEDURAL_TOPIC_TITLE_RE = re.compile(
    r"^(?:preparing the candidate|preparation of the candidate|preparing candidate)\.?,?$",
    re.IGNORECASE,
)
SHORT_PROCEDURAL_TITLE_RE = re.compile(
    r"^(?:again|and again|another says|another answers|one says|one answers)\.?,?$",
    re.IGNORECASE,
)
STRUCTURAL_SECTION_TITLE_RE = re.compile(
    r"^(?:first|second|third|fourth|fifth|sixth|seventh)\s+section\.?,?$",
    re.IGNORECASE,
)
STRUCTURAL_CEREMONY_STAGE_TITLE_RE = re.compile(
    r"^(?:first|second|third|fourth|fifth|sixth|seventh)\s+circuit\.?,?$",
    re.IGNORECASE,
)
PROCEDURAL_RITUAL_TITLE_RE = re.compile(
    r"^(?:ritual\s+for\s+a\s+lodge\s+of\s+sorrow|burial\s+service|ceremonies\s+at\s+the\s+grave|foundation\s+stone\s+ceremony|dedication\s+of\s+masonic\s+halls|installation\s+of\s+lodge\s+officers)\.?,?$",
    re.IGNORECASE,
)
ROLE_CHARGE_TITLE_RE = re.compile(
    r"^charge\s+to\s+the\s+(?:grand\s+)?(?:master|deputy\s+grand\s+master|senior\s+grand\s+warden|junior\s+grand\s+warden|"
    r"grand\s+treasurer|grand\s+secretary|grand\s+chaplain|grand\s+marshal|grand\s+deacon|grand\s+steward|"
    r"grand\s+sword\s+bearer|grand\s+standard\s+bearer|grand\s+pursuivant|grand\s+tiler|sword\s+bearer|"
    r"tiler|tyler|warden|deacon|steward|marshal|secretary|treasurer|chaplain|candidate)\.?,?$",
    re.IGNORECASE,
)
BARE_DEGREE_TITLE_RE = re.compile(
    r"^(?:entered\s+apprentice(?:\s+degree)?|fellow\s+craft(?:\s+degree)?|master\s+mason(?:\s+degree)?|mark\s+master|past\s+master|most\s+excellent(?:\s+master)?|royal\s+arch(?:\s+mason)?)\.?,?$",
    re.IGNORECASE,
)
LOW_INFO_ROLE_TITLE_RE = re.compile(
    r"^(?:(?:right|most|very)\s+)?(?:worshipful\s+master|senior\s+warden|junior\s+warden|senior\s+deacon|junior\s+deacon|inner\s+guard|outer\s+guard|tyler|treasurer|secretary|chaplain|marshal|conductor|candidate)\.?,?$",
    re.IGNORECASE,
)
DIALOGUE_DASH_RE = re.compile(r"^[A-Z][A-Za-z.\s]{1,30}\s*[-–—]{2}")
SOURCE_TITLE_RE = re.compile(r"^[A-Z][A-Za-z']+'s\s+(?:ritual|monitor|lexicon)\.?$", re.IGNORECASE)
SOURCE_WORK_TITLE_RE = re.compile(
    r"^(?:blue\s+lodge|blue\s+lodge\s+text\s+book|blue\s+lodge\s+ritual\s+reference\s+guide)\.?$",
    re.IGNORECASE,
)
SONG_TITLE_RE = re.compile(r"\b(?:song|hymn|ode)\.?$", re.IGNORECASE)
MUSIC_CUE_TITLE_RE = re.compile(r"^music\s*[-:]", re.IGNORECASE)
OCR_GLUE_RE = re.compile(r"\b[A-Za-z]{24,}\b")
ROMAN_TAXONOMY_HEADING_RE = re.compile(
    r"^[IVXLCDM]+\.\s+[A-Z][A-Z\s'’.-]{2,80}(?:[—-][A-Z][A-Z\s'’.-]{2,80})?$"
)
OCR_COMMON_TYPES_RE = re.compile(r"^I[A-Z]+[—-][A-Z\s]*(?:COMMON|COMMONT)\s*(?:TYPES?|TPES|PES)$", re.IGNORECASE)
EDITION_FRONT_MATTER_TITLE_RE = re.compile(r"^the\s+twentieth\s+century\s+edition\s+de\s+luxe\.?$", re.IGNORECASE)
PROCEDURAL_ROLE_RE = re.compile(
    r"\b(?:candidate|brother|worshipful master|inner guard|junior warden|senior warden|tyler|deacon)\b",
    re.IGNORECASE,
)
DIALOGUE_CONTINUATION_RE = re.compile(
    r"\b(?:dialogue with|words to|reported to|has said|latter says|latter has said|for which ceremony)\b",
    re.IGNORECASE,
)
DIALOGUE_LINE_RE = re.compile(
    r"^(?:ans|answer|all|architect|chaplain|secretary|treasurer|marshal|master|warden|installing officer|"
    r"worshipful master|senior warden|junior warden|senior grand warden|junior grand warden|grand master|"
    r"grand chaplain|grand secretary|grand treasurer|grand marshal|grand tiler|grand tyler|deacon|tyler)\s*:",
    re.IGNORECASE,
)
FIGURE_LABEL_RE = re.compile(r"^(?:fig|figure)\.?\s*\d+", re.IGNORECASE)
SENTENCE_LIKE_START_RE = re.compile(
    r"^(?:a|an|the|this|these|those|how|what|why|in|at|to|for|degree|any|no|each|every|you|your|let|charge)\b",
    re.IGNORECASE,
)
SENTENCE_LIKE_VERB_RE = re.compile(
    r"\b(?:is|are|be|was|were|has|have|had|may|can|shall|should|would|will|desiring|relates|called|reported|risen|made|make|know|says|said|saying|ending|begins|keeps|speak|practice|presented|presents|taught|alluding|committed|confined|concluded|introduced|warrant|preferred|done|give|goes|offers|orders|takes|pours|uncovers|resigns|addresses)\b",
    re.IGNORECASE,
)
TRAILING_FRAGMENT_RE = re.compile(
    r"\b(?:and|or|to|of|the|a|an|in|on|for|with|than|after|before|when|where|which|that|if|as|your|personal|never|give)\s*\.?$",
    re.IGNORECASE,
)
LOW_INFO_SINGLE_WORD_TITLES = {
    "brother",
    "candidate",
    "conductor",
    "craft",
    "deacon",
    "here",
    "know your",
    "master",
    "masonry",
    "freemasonry",
    "amon",
    "ruffian",
    "ruffians",
    "warden",
}

LOOKUP_STOP_TERMS = {
    "degree",
    "level1",
    "level2",
    "level3",
    "library",
    "masonry",
    "freemasonry",
    "lodge",
    "book",
    "chapter",
    "section",
    "guide",
    "reference",
    "introduction",
    "system",
    "process",
    "structure",
    "relationship",
    "analysis",
    "symbolic",
    "meaning",
    "learning",
    "inner",
    "formation",
    "transition",
}
LOOKUP_CONNECTOR_TERMS = {
    "and",
    "of",
    "the",
    "as",
    "to",
    "from",
    "in",
    "on",
    "for",
    "with",
    "by",
    "or",
}
HEURISTIC_SYNONYM_HINTS: dict[str, list[str]] = {
    "candidate-preparation": [
        "candidate preparation",
        "properly prepared",
        "preparation of the candidate",
        "prepared candidate",
        "preparation",
    ],
    "ritual-flow": [
        "ritual flow",
        "ceremony",
        "ceremonial flow",
        "opening the lodge",
        "closing the lodge",
        "perambulation",
        "passing",
    ],
    "tracing-board-symbols": [
        "tracing board",
        "board lecture",
        "winding staircase",
        "middle chamber",
        "g",
        "pillars",
    ],
    "obligation-and-law": [
        "obligation",
        "penalty",
        "secrecy",
        "oath",
        "law",
        "charges",
    ],
}


@dataclass(slots=True)
class MappingUnit:
    unit_id: str
    text: str
    char_length: int


@dataclass(slots=True)
class ExtractedSection:
    section_id: str
    title: str
    marker_type: str
    text: str
    source_anchor: str
    source_order: int
    chapter_toc: list[str] = field(default_factory=list)
    mapping_units: list[MappingUnit] = field(default_factory=list)
    normalized_title: str = ""
    unit_kind: str = "topic"
    normalization_flags: list[str] = field(default_factory=list)
    is_noise_candidate: bool = False

    def as_manifest_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "normalized_title": self.normalized_title or self.title,
            "marker_type": self.marker_type,
            "unit_kind": self.unit_kind,
            "normalization_flags": list(self.normalization_flags),
            "is_noise_candidate": self.is_noise_candidate,
            "text_char_length": len(self.text),
            "source_anchor": self.source_anchor,
            "source_order": self.source_order,
            "chapter_toc": list(self.chapter_toc),
            "mapping_units": [
                {
                    "unit_id": unit.unit_id,
                    "char_length": unit.char_length,
                }
                for unit in self.mapping_units
            ],
        }


def deep_copy_degree(data: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(data)


def clean_markdown_for_preservation(text: str) -> str:
    cleaned = normalize_newlines(text)
    cleaned = IMAGE_ONLY_LINE_RE.sub("", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def clean_heading_text(text: str) -> str:
    cleaned = normalize_text(text)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"[*_`#>\[\]()]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip(" :-")
    return cleaned.strip() or "Untitled Section"


def is_page_level_title(text: str) -> bool:
    return bool(PAGE_TITLE_RE.fullmatch(clean_heading_text(text)))


def is_page_header_fragment_title(text: str) -> bool:
    normalized = clean_heading_text(text)
    if not normalized:
        return False
    if RUNNING_HEADER_RE.search(normalized) and (
        LEADING_PAGE_HEADER_RE.fullmatch(normalized.upper())
        or TRAILING_PAGE_HEADER_RE.fullmatch(normalized.upper())
    ):
        return True
    if LEADING_PAGE_HEADER_RE.fullmatch(normalized.upper()):
        return True
    if TRAILING_PAGE_HEADER_RE.fullmatch(normalized.upper()):
        return True
    return False


def title_word_tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", normalize_text(text))


def slugify(text: str, *, prefix: str = "section") -> str:
    lowered = text.lower()
    lowered = re.sub(r"<[^>]+>", " ", lowered)
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = re.sub(r"-{2,}", "-", lowered).strip("-")
    return lowered or prefix


def split_paragraphs(text: str) -> list[str]:
    normalized = normalize_newlines(text)
    if not normalized:
        return []
    return [part.strip() for part in SECTION_BREAK_RE.split(normalized) if part.strip()]


def slice_text_hard(text: str, max_chars: int) -> list[str]:
    slices: list[str] = []
    remaining = text.strip()
    while remaining:
        if len(remaining) <= max_chars:
            slices.append(remaining)
            break
        cut = remaining.rfind(" ", 0, max_chars)
        if cut < max_chars // 2:
            cut = max_chars
        slices.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    return [item for item in slices if item]


def split_mapping_units(text: str, max_chars: int, section_id: str) -> list[MappingUnit]:
    paragraphs = split_paragraphs(text)
    if not paragraphs:
        return [MappingUnit(unit_id=f"{section_id}-unit-0001", text="", char_length=0)]

    units: list[MappingUnit] = []
    current_parts: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph_length = len(paragraph) + (2 if current_parts else 0)
        if current_parts and current_length + paragraph_length > max_chars:
            unit_text = "\n\n".join(current_parts).strip()
            units.append(
                MappingUnit(
                    unit_id=f"{section_id}-unit-{len(units) + 1:04d}",
                    text=unit_text,
                    char_length=len(unit_text),
                )
            )
            current_parts = []
            current_length = 0

        if len(paragraph) > max_chars:
            for item in slice_text_hard(paragraph, max_chars):
                units.append(
                    MappingUnit(
                        unit_id=f"{section_id}-unit-{len(units) + 1:04d}",
                        text=item,
                        char_length=len(item),
                    )
                )
            continue

        current_parts.append(paragraph)
        current_length += paragraph_length

    if current_parts:
        unit_text = "\n\n".join(current_parts).strip()
        units.append(
            MappingUnit(
                unit_id=f"{section_id}-unit-{len(units) + 1:04d}",
                text=unit_text,
                char_length=len(unit_text),
            )
        )

    return units


def find_subheadings(text: str, *, root_title: str | None = None) -> list[str]:
    toc: list[str] = []
    for match in HEADING_RE.finditer(text):
        title = clean_heading_text(match.group(2))
        if root_title and title == root_title:
            continue
        toc.append(title)
    return unique_strings(toc)


def build_sections_from_matches(
    text: str,
    matches: list[re.Match[str]],
    *,
    marker_type: str,
    max_mapping_chars: int,
) -> list[ExtractedSection]:
    sections: list[ExtractedSection] = []
    if not matches:
        return sections

    if matches[0].start() > 0:
        leading_text = text[: matches[0].start()].strip()
        if leading_text:
            title = "Preface"
            section_id = f"section-{len(sections) + 1:04d}"
            sections.append(
                ExtractedSection(
                    section_id=section_id,
                    title=title,
                    marker_type=f"{marker_type}-preface",
                    text=leading_text,
                    source_anchor=slugify(title, prefix=section_id),
                    source_order=len(sections) + 1,
                    chapter_toc=find_subheadings(leading_text),
                    mapping_units=split_mapping_units(leading_text, max_mapping_chars, section_id),
                )
            )

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        match_groups = match.groupdict()
        if marker_type == "pause":
            title = clean_heading_text(match_groups.get("tail") or match_groups.get("title") or match.group(0))
        else:
            title = clean_heading_text(match_groups.get("title") or match.group(0))
        section_id = f"section-{len(sections) + 1:04d}"
        sections.append(
            ExtractedSection(
                section_id=section_id,
                title=title,
                marker_type=marker_type,
                text=body,
                source_anchor=slugify(title, prefix=section_id),
                source_order=len(sections) + 1,
                chapter_toc=find_subheadings(body, root_title=title),
                mapping_units=split_mapping_units(body, max_mapping_chars, section_id),
            )
        )

    return sections


def extract_sections(markdown_text: str, *, max_mapping_chars: int = 7000) -> list[ExtractedSection]:
    text = clean_markdown_for_preservation(markdown_text)
    pause_matches = list(PAUSE_RE.finditer(text))
    heading_matches = [match for match in HEADING_RE.finditer(text) if len(match.group(1)) <= 3]
    generic_matches = list(GENERIC_MARKER_RE.finditer(text))
    page_heading_count = sum(
        1
        for match in heading_matches
        if is_page_level_title(clean_heading_text(match.groupdict().get("title") or match.group(2)))
    )

    if len(pause_matches) >= 3 and (
        len(heading_matches) <= 8 or (heading_matches and page_heading_count * 2 >= len(heading_matches))
    ):
        return build_sections_from_matches(text, pause_matches, marker_type="pause", max_mapping_chars=max_mapping_chars)
    if len(heading_matches) >= 2:
        return build_sections_from_matches(text, heading_matches, marker_type="heading", max_mapping_chars=max_mapping_chars)
    if len(generic_matches) >= 2:
        return build_sections_from_matches(text, generic_matches, marker_type="marker", max_mapping_chars=max_mapping_chars)

    section_id = "section-0001"
    return [
        ExtractedSection(
            section_id=section_id,
            title="Full Text",
            marker_type="full-text",
            text=text,
            source_anchor="full-text",
            source_order=1,
            chapter_toc=find_subheadings(text),
            mapping_units=split_mapping_units(text, max_mapping_chars, section_id),
        )
    ]


def pick_normalized_section_title(section: ExtractedSection) -> tuple[str, list[str]]:
    raw_title = clean_heading_text(section.title)
    flags: list[str] = []
    candidates: list[str] = []

    if not is_page_level_title(raw_title):
        candidates.append(raw_title)
    else:
        flags.append("PAGE_LEVEL_TITLE")

    candidates.extend(section.chapter_toc[:5])

    for match in TITLE_LINE_RE.finditer(section.text):
        title = clean_heading_text(match.group("title"))
        if title and title != raw_title:
            candidates.append(title)

    for paragraph in split_paragraphs(section.text)[:3]:
        first_line = clean_heading_text(paragraph.splitlines()[0] if paragraph.splitlines() else paragraph)
        if first_line:
            candidates.append(first_line)

    for candidate in unique_strings(candidates):
        lowered = candidate.lower()
        if is_page_level_title(candidate):
            continue
        if is_page_header_fragment_title(candidate):
            flags.append("PAGE_HEADER_FRAGMENT")
            continue
        if lowered in {"preface", "full text", "untitled section"}:
            continue
        if TABLE_OF_CONTENTS_RE.search(candidate):
            continue
        if candidate[:1].islower():
            continue
        if len(candidate) < 4:
            continue
        if candidate != raw_title:
            flags.append("TITLE_NORMALIZED")
        return candidate, unique_strings(flags)

    flags.append("LOW_INFORMATION_TITLE")
    return raw_title, unique_strings(flags)


def detect_procedural_fragment(title: str) -> list[str]:
    normalized = clean_heading_text(title)
    flags: list[str] = []
    if DIALOGUE_LINE_RE.match(normalized):
        flags.append("DIALOGUE_LINE")
        return unique_strings(flags)

    tokens = title_word_tokens(normalized)
    if not normalized or len(tokens) < 4:
        return []

    if PROCEDURAL_LEAD_RE.match(normalized):
        flags.append("PROCEDURAL_LEAD")
    if PROCEDURAL_ROLE_RE.search(normalized):
        flags.append("RITUAL_ROLE_REFERENCE")
    if DIALOGUE_CONTINUATION_RE.search(normalized):
        flags.append("DIALOGUE_CONTINUATION")
    if len(tokens) >= 4 and TRAILING_FRAGMENT_RE.search(normalized):
        flags.append("TRUNCATED_TITLE")
    if "DIALOGUE_LINE" in flags:
        return unique_strings(flags)
    if "PROCEDURAL_LEAD" in flags and ("RITUAL_ROLE_REFERENCE" in flags or "DIALOGUE_CONTINUATION" in flags):
        return unique_strings(flags)
    return []


def detect_fragmentary_title(title: str) -> list[str]:
    normalized = clean_heading_text(title)
    tokens = title_word_tokens(normalized)
    if not normalized or len(tokens) < 4:
        return []

    flags: list[str] = []
    if SENTENCE_LIKE_START_RE.match(normalized) and SENTENCE_LIKE_VERB_RE.search(normalized):
        flags.append("SENTENCE_FRAGMENT")
    if re.match(r"^(?:a|an|the)\b", normalized, re.IGNORECASE) and len(tokens) >= 8:
        flags.append("SENTENCE_FRAGMENT")
    if normalized.endswith(".") and len(tokens) >= 4:
        flags.append("SENTENCE_FRAGMENT")
    if DIALOGUE_LINE_RE.match(normalized):
        flags.append("DIALOGUE_LINE")
    if len(tokens) >= 4 and TRAILING_FRAGMENT_RE.search(normalized):
        flags.append("TRUNCATED_TITLE")
    if "," in normalized and SENTENCE_LIKE_VERB_RE.search(normalized):
        flags.append("INLINE_CLAUSE_TITLE")
    return unique_strings(flags)


def is_page_derived_prose_fragment(title: str) -> bool:
    normalized = clean_heading_text(title)
    tokens = title_word_tokens(normalized)
    if re.fullmatch(r"\d+[.:]?", normalized):
        return True
    if tokens and all(len(token) <= 1 for token in tokens):
        return True
    if len(tokens) == 1 and tokens[0].lower().strip(".,;:") in LOW_INFO_SINGLE_WORD_TITLES:
        return True
    if len(tokens) <= 3 and normalized.rstrip().endswith(","):
        return True
    if normalized[:1] in {"•", "·", ".", ";", ":"}:
        return True
    collapsed = re.sub(r"\s+", "", normalized).lower()
    if "earlybritishfreemasonry" in collapsed or "earlvbritishfreemasonry" in collapsed:
        return True
    if len(tokens) <= 2 and len(normalized) > 20 and " " not in normalized and re.search(r"[a-z]", normalized) and re.search(r"[A-Z]", normalized):
        return True
    if OCR_GLUE_RE.search(normalized):
        return True
    letters = [char for char in normalized if char.isalpha()]
    if (
        re.search(r"\.?\s*\d{1,4}\.?$", normalized)
        and len(letters) >= 8
        and (sum(1 for char in letters if char.isupper()) / len(letters)) >= 0.75
    ):
        return True
    if EDITION_FRONT_MATTER_TITLE_RE.fullmatch(normalized):
        return True
    if ROMAN_TAXONOMY_HEADING_RE.fullmatch(normalized) or OCR_COMMON_TYPES_RE.fullmatch(normalized):
        return True
    if normalized.lower().strip(".") in {"accepted", "apprentice"}:
        return True
    if normalized.lower().strip("., ") in {"yours fraternally", "wherever assembled"}:
        return True
    if normalized.lower().strip("., ") in {"know your"}:
        return True
    if normalized.lower().strip("\"'“”‘’. ") in {"follow me"}:
        return True
    if re.search(r"[-–—]{2}\s*[A-Za-z][A-Za-z.'\s-]{2,40}\.$", normalized):
        return True
    if DIALOGUE_DASH_RE.match(normalized):
        return True
    if SOURCE_TITLE_RE.fullmatch(normalized):
        return True
    if (
        PROCEDURAL_TOPIC_TITLE_RE.fullmatch(normalized)
        or SHORT_PROCEDURAL_TITLE_RE.fullmatch(normalized)
        or STRUCTURAL_SECTION_TITLE_RE.fullmatch(normalized)
        or STRUCTURAL_CEREMONY_STAGE_TITLE_RE.fullmatch(normalized)
        or PROCEDURAL_RITUAL_TITLE_RE.fullmatch(normalized)
        or ROLE_CHARGE_TITLE_RE.fullmatch(normalized)
        or BARE_DEGREE_TITLE_RE.fullmatch(normalized)
        or LOW_INFO_ROLE_TITLE_RE.fullmatch(normalized)
        or SONG_TITLE_RE.search(normalized)
        or MUSIC_CUE_TITLE_RE.match(normalized)
    ):
        return True
    if (
        len(tokens) <= 5
        and normalized.startswith(('"', "'", "“", "‘"))
        and normalized.rstrip().endswith(('"', "'", "”", "’", '".', "'.", "”.", "’."))
    ):
        return True
    if normalized.endswith("?") and len(tokens) <= 3:
        return True
    if len(tokens) < 3:
        return False
    if FIGURE_LABEL_RE.match(normalized):
        return True
    if PROCEDURAL_LEAD_RE.match(normalized):
        return True
    if DIALOGUE_LINE_RE.match(normalized):
        return True
    if normalized.endswith("."):
        return True
    if "," in normalized and SENTENCE_LIKE_VERB_RE.search(normalized):
        return True
    if ". " in normalized and re.search(r"[a-z]", normalized):
        return True
    if sum(1 for token in tokens if len(token) == 1) >= 2:
        return True

    connector_terms = {"a", "an", "and", "as", "by", "for", "in", "of", "on", "or", "the", "to", "with"}
    prose_leads = {"a", "an", "the", "it", "this", "these", "those", "if", "on", "when", "where", "while", "you", "your", "let", "charge"}
    non_connector = [token for token in tokens if token.lower() not in connector_terms]
    lowercase_content = [
        token
        for token in non_connector
        if token[:1].islower() and not token.isupper()
    ]
    if len(lowercase_content) >= 2:
        return True
    if len(tokens) >= 5 and tokens[0].lower() in prose_leads and lowercase_content:
        return True
    if normalized.lower().startswith("general grand "):
        return True
    return False


def classify_section_kind(section: ExtractedSection, *, normalized_title: str, flags: list[str]) -> tuple[str, list[str], bool]:
    text_excerpt = normalize_text(section.text[:1600])
    next_flags = list(flags)
    unit_kind = "topic"
    title_normalized = "TITLE_NORMALIZED" in next_flags

    if section.marker_type.endswith("-preface"):
        unit_kind = "front_matter"
        next_flags.append("PREFACE_SECTION")
    elif "PAGE_LEVEL_TITLE" in next_flags and (
        TITLE_PAGE_FRAGMENT_RE.match(normalized_title)
        or "exposition of the mysteries" in normalized_title.lower()
    ):
        unit_kind = "front_matter"
        next_flags.append("TITLE_PAGE_FRAGMENT")
    elif TABLE_OF_CONTENTS_RE.search(normalized_title) or TABLE_OF_CONTENTS_RE.search(text_excerpt):
        unit_kind = "toc"
        next_flags.append("TABLE_OF_CONTENTS")
    elif APPARATUS_TITLE_RE.fullmatch(normalized_title):
        unit_kind = "front_matter"
        next_flags.append("BIBLIOGRAPHIC_APPARATUS")
    elif FRONT_MATTER_HINT_RE.search(text_excerpt) and not title_normalized:
        unit_kind = "front_matter"
        next_flags.append("FRONT_MATTER")
    elif (OFFICER_LIST_HINT_RE.search(normalized_title) or OFFICER_LIST_HINT_RE.search(text_excerpt)) and not title_normalized:
        unit_kind = "officer_list"
        next_flags.append("OFFICER_LIST")
    elif "PAGE_LEVEL_TITLE" in next_flags and HONORIFIC_PERSON_TITLE_RE.match(normalized_title):
        unit_kind = "front_matter"
        next_flags.append("HONORIFIC_PERSON_TITLE")
    elif SOURCE_WORK_TITLE_RE.fullmatch(normalized_title) and (
        "PAGE_LEVEL_TITLE" in next_flags or len(text_excerpt) < 1200
    ):
        unit_kind = "front_matter"
        next_flags.append("SOURCE_WORK_TITLE")
    elif is_page_level_title(normalized_title):
        unit_kind = "page_fragment"
        next_flags.append("PAGE_LEVEL_FRAGMENT")
    elif is_page_header_fragment_title(normalized_title):
        unit_kind = "page_fragment"
        next_flags.append("PAGE_HEADER_FRAGMENT")
    elif section.marker_type == "full-text":
        unit_kind = "full_text_fallback"
        next_flags.append("FULL_TEXT_FALLBACK")
    else:
        procedural_flags = detect_procedural_fragment(normalized_title)
        fragmentary_flags = detect_fragmentary_title(normalized_title)
        if procedural_flags:
            unit_kind = "procedural_fragment"
            next_flags.extend(procedural_flags)
        elif fragmentary_flags:
            unit_kind = "fragmentary_topic"
            next_flags.extend(fragmentary_flags)
        elif "PAGE_LEVEL_TITLE" in next_flags and is_page_derived_prose_fragment(normalized_title):
            unit_kind = "fragmentary_topic"
            next_flags.append("PAGE_DERIVED_PROSE_FRAGMENT")

    is_noise = unit_kind in {"toc", "front_matter", "officer_list", "page_fragment"}
    return unit_kind, unique_strings(next_flags), is_noise


def normalize_extracted_sections(sections: list[ExtractedSection]) -> list[ExtractedSection]:
    normalized_sections: list[ExtractedSection] = []
    for section in sections:
        normalized_title, flags = pick_normalized_section_title(section)
        unit_kind, next_flags, is_noise = classify_section_kind(
            section,
            normalized_title=normalized_title,
            flags=flags,
        )
        normalized_sections.append(
            ExtractedSection(
                section_id=section.section_id,
                title=section.title,
                marker_type=section.marker_type,
                text=section.text,
                source_anchor=section.source_anchor,
                source_order=section.source_order,
                chapter_toc=list(section.chapter_toc),
                mapping_units=list(section.mapping_units),
                normalized_title=normalized_title,
                unit_kind=unit_kind,
                normalization_flags=next_flags,
                is_noise_candidate=is_noise,
            )
        )
    return normalized_sections


def normalize_lookup_text(text: str) -> str:
    normalized = normalize_text(text).lower()
    normalized = re.sub(r"<[^>]+>", " ", normalized)
    normalized = re.sub(r"[_/]", " ", normalized)
    normalized = re.sub(r"[^0-9a-z\u0590-\u05ff\s-]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def normalize_lookup_term(text: str) -> str:
    return normalize_lookup_text(text).replace("-", " ")


def is_useful_lookup_term(term: str) -> bool:
    if not term:
        return False
    if term in LOOKUP_STOP_TERMS:
        return False
    if len(term) < 4:
        return False
    if " " not in term and len(term) < 7:
        return False
    return True


def expand_lookup_variants(raw_term: Any) -> set[str]:
    base = normalize_lookup_term(raw_term)
    if not base:
        return set()

    variants = {base}
    tokens = [token for token in base.split() if token]
    filtered_tokens = [
        token for token in tokens if token not in LOOKUP_STOP_TERMS and token not in LOOKUP_CONNECTOR_TERMS
    ]

    if filtered_tokens and filtered_tokens != tokens:
        variants.add(" ".join(filtered_tokens))

    for token in filtered_tokens:
        if is_useful_lookup_term(token):
            variants.add(token)

    max_span = min(4, len(filtered_tokens))
    for span in range(2, max_span + 1):
        for index in range(0, len(filtered_tokens) - span + 1):
            phrase = " ".join(filtered_tokens[index : index + span])
            if is_useful_lookup_term(phrase):
                variants.add(phrase)

    return {variant for variant in variants if is_useful_lookup_term(variant)}


def contains_lookup_term(text: str, term: str) -> bool:
    haystack = f" {text} "
    needle = f" {term} "
    return needle in haystack


def claim_unique_slug(base_slug: str, existing_slugs: set[str]) -> str:
    candidate = base_slug
    suffix = 2
    while candidate in existing_slugs:
        candidate = f"{base_slug}-{suffix}"
        suffix += 1
    existing_slugs.add(candidate)
    return candidate


def render_short_summary(text: str, *, fallback: str, max_chars: int = 280) -> str:
    paragraphs = split_paragraphs(text)
    base = paragraphs[0] if paragraphs else fallback
    if len(base) <= max_chars:
        return base
    cut = base.rfind(" ", 0, max_chars)
    if cut < max_chars // 2:
        cut = max_chars
    return base[:cut].rstrip(" ,.;:") + "..."


def render_library_book_summary(work_title: str, sections: list[ExtractedSection]) -> str:
    lines = [
        f"Imported source work preserved from the PDF ETL lane: **{work_title}**.",
        "",
        "Sections staged in this draft:",
    ]
    for section in sections[:20]:
        lines.append(f"- {section.title}")
    if len(sections) > 20:
        lines.append(f"- ...and {len(sections) - 20} more sections")
    return "\n".join(lines).strip()


def build_entry_catalog(*datasets: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    by_degree: dict[str, dict[str, dict[str, Any]]] = {}

    for dataset in datasets:
        degree_id = dataset["meta"]["degree"]
        by_degree.setdefault(degree_id, {})
        for entry in dataset["entries"]:
            terms = set()
            raw_terms = [
                entry["title"],
                entry["slug"].replace("-", " "),
                *entry.get("aliases", []),
                *entry.get("keywords", []),
                *HEURISTIC_SYNONYM_HINTS.get(entry["slug"], []),
            ]
            for raw_term in raw_terms:
                terms.update(expand_lookup_variants(raw_term))

            item = {
                "degree": degree_id,
                "slug": entry["slug"],
                "title": entry["title"],
                "category": entry["category"],
                "parent_topic": entry["parent_topic"],
                "aliases": list(entry.get("aliases", [])),
                "keywords": list(entry.get("keywords", [])),
                "lookup_terms": sorted(terms),
            }
            items.append(item)
            by_key[(degree_id, entry["slug"])] = item
            by_degree[degree_id][entry["slug"]] = item

    return {"items": items, "by_key": by_key, "by_degree": by_degree}


def find_catalog_matches(
    section_title: str,
    section_text: str,
    catalog: dict[str, Any],
    *,
    allowed_degrees: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    title_text = normalize_lookup_text(section_title)
    body_text = normalize_lookup_text(section_text)
    allowed = set(allowed_degrees or [])
    matches: list[dict[str, Any]] = []

    for item in catalog["items"]:
        if allowed and item["degree"] not in allowed:
            continue
        title_terms: list[str] = []
        body_terms: list[str] = []
        for term in item["lookup_terms"]:
            if contains_lookup_term(title_text, term):
                title_terms.append(term)
            elif contains_lookup_term(body_text, term):
                body_terms.append(term)

        evidence = unique_strings(title_terms + body_terms)
        if not evidence:
            continue

        matches.append(
            {
                "degree": item["degree"],
                "slug": item["slug"],
                "title": item["title"],
                "category": item["category"],
                "heading_hit": bool(title_terms),
                "title_terms": unique_strings(title_terms),
                "body_terms": unique_strings(body_terms),
                "supporting_terms": evidence,
                "score": len(title_terms) * 4 + len(body_terms) * 2,
            }
        )

    matches.sort(key=lambda item: (-item["score"], item["degree"], item["slug"]))
    return matches


def heuristic_extract_mapping(
    section_title: str,
    section_text: str,
    catalog: dict[str, Any],
    *,
    allowed_degrees: Iterable[str] | None = None,
) -> dict[str, Any]:
    matches = find_catalog_matches(section_title, section_text, catalog, allowed_degrees=allowed_degrees)
    title = clean_heading_text(section_title)
    non_library_allowed = [
        str(degree).strip()
        for degree in (allowed_degrees or [])
        if str(degree).strip() and str(degree).strip() != "library"
    ]
    heuristic_new_topics: list[dict[str, str]] = []
    if not matches and title and not is_page_level_title(title) and title.lower() not in {"preface", "full text", "untitled section"}:
        heuristic_new_topics.append(
            {
                "title": title,
                "degree": non_library_allowed[0] if non_library_allowed else "unknown",
                "reason": "Heuristic topic unit without a strong local match.",
            }
        )
    keywords = unique_strings(
        [
            title,
            *[term for match in matches[:8] for term in match["supporting_terms"][:2]],
        ]
    )
    return {
        "section_summary": "",
        "practical_elements": [],
        "symbolic_meaning": "",
        "candidate_lesson": "",
        "keywords": keywords[:12],
        "caution_notes": [],
        "tradition_notes": [],
        "target_entry_candidates": [
            {
                "slug": match["slug"],
                "degree": match["degree"],
                "reason": f"Lexical evidence: {', '.join(match['supporting_terms'][:4])}",
            }
            for match in matches[:12]
        ],
        "knowledge_link_candidates": [
            {"slug": match["slug"], "degree": match["degree"]}
            for match in matches[:12]
        ],
        "new_topic_candidates": heuristic_new_topics,
        "_lexical_matches": matches,
    }


def join_nonempty_strings(values: Iterable[str]) -> str:
    normalized = unique_strings(value.strip() for value in values if normalize_text(value))
    return "\n\n".join(normalized)


def mapping_text(item: dict[str, Any], canonical_key: str, legacy_key: str) -> str:
    return normalize_text(item.get(canonical_key)) or normalize_text(item.get(legacy_key))


def mapping_list(item: dict[str, Any], canonical_key: str, legacy_key: str) -> list[str]:
    values = item.get(canonical_key)
    if values is None:
        values = item.get(legacy_key)
    return normalize_string_array(values)


def combine_mapping_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    combined = {
        "section_summary": join_nonempty_strings(mapping_text(item, "section_summary", "section_summary_he") for item in results),
        "practical_elements": unique_strings(
            value for item in results for value in mapping_list(item, "practical_elements", "practical_elements_he")
        ),
        "symbolic_meaning": join_nonempty_strings(mapping_text(item, "symbolic_meaning", "symbolic_meaning_he") for item in results),
        "candidate_lesson": join_nonempty_strings(mapping_text(item, "candidate_lesson", "candidate_lesson_he") for item in results),
        "keywords": unique_strings(value for item in results for value in item.get("keywords", [])),
        "caution_notes": unique_strings(
            value for item in results for value in mapping_list(item, "caution_notes", "caution_notes_he")
        ),
        "tradition_notes": unique_strings(
            value for item in results for value in mapping_list(item, "tradition_notes", "tradition_notes_he")
        ),
        "target_entry_candidates": [],
        "knowledge_link_candidates": [],
        "new_topic_candidates": [],
        "_lexical_matches": [],
    }
    for item in results:
        combined["target_entry_candidates"].extend(item.get("target_entry_candidates", []))
        combined["knowledge_link_candidates"].extend(item.get("knowledge_link_candidates", []))
        combined["new_topic_candidates"].extend(item.get("new_topic_candidates", []))
        combined["_lexical_matches"].extend(item.get("_lexical_matches", []))
    return combined


def resolve_target_matches(
    combined_result: dict[str, Any],
    lexical_matches: list[dict[str, Any]],
    catalog: dict[str, Any],
    *,
    allowed_degrees: Iterable[str],
) -> dict[str, list[dict[str, Any]]]:
    allowed = set(allowed_degrees)
    match_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    rejected: list[dict[str, Any]] = []

    for match in lexical_matches:
        if match["degree"] not in allowed:
            continue
        match_by_key[(match["degree"], match["slug"])] = dict(match, provider_suggested=False)

    for candidate in combined_result.get("target_entry_candidates", []):
        degree = normalize_nullable_string(candidate.get("degree"))
        slug = normalize_nullable_string(candidate.get("slug"))
        if not degree or not slug:
            continue
        if degree not in allowed:
            rejected.append({"degree": degree, "slug": slug, "reason": "Suggested degree is outside the allowed routing lane."})
            continue
        catalog_item = catalog["by_key"].get((degree, slug))
        if not catalog_item:
            rejected.append({"degree": degree, "slug": slug, "reason": "Suggested slug does not exist in the current degree index."})
            continue
        existing = match_by_key.get((degree, slug), {})
        match_by_key[(degree, slug)] = {
            "degree": degree,
            "slug": slug,
            "title": existing.get("title") or catalog_item["title"],
            "category": existing.get("category") or catalog_item["category"],
            "heading_hit": bool(existing.get("heading_hit")),
            "title_terms": unique_strings(existing.get("title_terms", [])),
            "body_terms": unique_strings(existing.get("body_terms", [])),
            "supporting_terms": unique_strings(existing.get("supporting_terms", [])),
            "score": existing.get("score", 0),
            "provider_suggested": True,
            "provider_reason": normalize_text(candidate.get("reason")),
        }

    strong: list[dict[str, Any]] = []
    medium: list[dict[str, Any]] = []
    for match in match_by_key.values():
        evidence_count = len(match.get("supporting_terms", []))
        if match.get("heading_hit") or evidence_count >= 2 or (match.get("provider_suggested") and evidence_count >= 1):
            strong.append(dict(match, confidence="strong"))
        elif evidence_count == 1 or match.get("provider_suggested"):
            medium.append(dict(match, confidence="medium"))

    strong.sort(key=lambda item: (-item.get("score", 0), item["degree"], item["slug"]))
    medium.sort(key=lambda item: (-item.get("score", 0), item["degree"], item["slug"]))
    return {"strong": strong, "medium": medium, "rejected": rejected}


def select_content_match_targets(strong_matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Choose which strong matches receive the section's appended content.

    Routing must not fan a section's content out to *every* strong match.
    Lexical score does not track topical relevance: a generic high-overlap entry
    can outrank the genuinely-correct one (observed empirically - a working-tools
    section scored "seven liberal arts" above "plumb, level and square"). Fanning
    content to all strong matches therefore produces duplicate and off-topic
    enrichment.

    We trust only the targets the provider (LLM) explicitly named
    (``provider_suggested``). When the provider named none, this returns an empty
    list so the caller can withhold content for human review rather than guessing
    a subject from lexical overlap alone.
    """
    return [match for match in strong_matches if match.get("provider_suggested")]


def preservation_report(source_text: str, stored_text: str) -> dict[str, Any]:
    left = normalize_lookup_text(source_text)
    right = normalize_lookup_text(stored_text)
    return {
        "source_char_count": len(source_text),
        "stored_char_count": len(stored_text),
        "normalized_equal": left == right,
        "source_token_count": len(left.split()),
        "stored_token_count": len(right.split()),
    }


DEGREE_ORDER = {"library": 0, "level1": 1, "level2": 2, "level3": 3}

# Encyclopedia-first vocabulary: titles that should route to encyclopedia_candidate
# rather than being proposed as degree_root entries.  Keys are normalize_lookup_term()
# values; values are the target encyclopedia lane.
ENCYCLOPEDIA_TOPIC_SIGNALS: dict[str, str] = {
    # encyclopedia_foundational: Masonic moral virtues and founding principles
    "brotherly love": "encyclopedia_foundational",
    "relief": "encyclopedia_foundational",
    "truth": "encyclopedia_foundational",
    "temperance": "encyclopedia_foundational",
    "justice": "encyclopedia_foundational",
    "fortitude": "encyclopedia_foundational",
    "charity": "encyclopedia_foundational",
    "faith": "encyclopedia_foundational",
    "hope": "encyclopedia_foundational",
    "lesson of charity": "encyclopedia_foundational",
    "brotherly love relief and truth": "encyclopedia_foundational",
    "faith hope and charity": "encyclopedia_foundational",
    # encyclopedia_glossary: structural and definitional concepts
    "a lodge": "encyclopedia_glossary",
    "the lodge": "encyclopedia_glossary",
    # encyclopedia_officers_governance: roles and governance procedures
    "the treasurer": "encyclopedia_officers_governance",
    "the secretary": "encyclopedia_officers_governance",
    "senior and junior deacons": "encyclopedia_officers_governance",
    "brothers senior and junior wardens": "encyclopedia_officers_governance",
    "the senior warden": "encyclopedia_officers_governance",
    "the junior warden": "encyclopedia_officers_governance",
    "the worshipful master": "encyclopedia_officers_governance",
    "no vote": "encyclopedia_officers_governance",
    "quorum": "encyclopedia_officers_governance",
    "rules for masonic dates": "encyclopedia_officers_governance",
    "unanimous ballot": "encyclopedia_officers_governance",
    "digest and judicial decisions": "encyclopedia_officers_governance",
    "williams digest of laws excerpts": "encyclopedia_officers_governance",
    # encyclopedia_ritual_reference: ceremony and ritual elements
    "prayer": "encyclopedia_ritual_reference",
    "benediction": "encyclopedia_ritual_reference",
    "examination before passing": "encyclopedia_ritual_reference",
    # encyclopedia_higher_degrees_reference
    "mark master": "encyclopedia_higher_degrees_reference",
    "mark master and higher degrees": "encyclopedia_higher_degrees_reference",
    "mark master degree": "encyclopedia_higher_degrees_reference",
    "mark master mason": "encyclopedia_higher_degrees_reference",
    "most excellent master": "encyclopedia_higher_degrees_reference",
    "past master degree": "encyclopedia_higher_degrees_reference",
    "royal arch": "encyclopedia_higher_degrees_reference",
    "royal arch chapter": "encyclopedia_higher_degrees_reference",
    "royal arch degree": "encyclopedia_higher_degrees_reference",
    "royal arch mason": "encyclopedia_higher_degrees_reference",
    "royal master": "encyclopedia_higher_degrees_reference",
    "select master": "encyclopedia_higher_degrees_reference",
    # encyclopedia_pending: real content, classification deferred
    "the secrets": "encyclopedia_pending",
}

LATER_DEGREE_TITLE_SIGNALS = {
    # Master Mason / level3 signals
    "all seeing eye": "level3",
    "all-seeing eye": "level3",
    "anchor and ark": "level3",
    "bee hive": "level3",
    "beehive": "level3",
    "forty seventh": "level3",
    "grand hailing sign five points of fellowship": "level3",
    "hiram abiff legend murder burial and discovery": "level3",
    "hour glass": "level3",
    "masonic glossary master mason": "level3",
    "master mason": "level3",
    "master mason degree": "level3",
    "master mason opening obligation overview": "level3",
    "mm monitor emblems three steps beehive anchor ark": "level3",
    "monument and weeping virgin historical account": "level3",
    "scythe": "level3",
    "setting maul": "level3",
    "the all seeing eye": "level3",
    "the all-seeing eye": "level3",
    "the anchor and ark": "level3",
    "the bee hive": "level3",
    "the beehive": "level3",
    "the forty seventh": "level3",
    "the hour glass": "level3",
    "the lion of the tribe of judah": "level3",
    "the master mason": "level3",
    "the master mason degree": "level3",
    "the scythe": "level3",
    "the three steps": "level3",
    "three steps": "level3",
    "trowel": "level3",
    # Fellow Craft / Passing signals → level2
    "astronomy": "level2",
    "degree of fellow craft": "level2",
    "fellow craft": "level2",
    "fellow craft degree": "level2",
    "five orders in architecture": "level2",
    "five senses": "level2",
    "geometry": "level2",
    "middle chamber": "level2",
    "passing degree": "level2",
    "peace unity and plenty": "level2",
    "shibboleth": "level2",
    "the fellow craft": "level2",
    "the five orders in architecture": "level2",
    "the five senses": "level2",
    "the middle chamber": "level2",
    "the passing": "level2",
    "the winding stair": "level2",
    "the winding stairs": "level2",
    "the winding staircase": "level2",
    "winding stair": "level2",
    "winding staircase": "level2",
    "winding stairs": "level2",
}


def discovery_baseline_degree(primary_degree: str | None) -> str | None:
    normalized = normalize_nullable_string(primary_degree)
    if normalized == "multi":
        return "level1"
    return normalized


def select_candidate_degree(
    *,
    primary_degree: str | None,
    medium_matches: list[dict[str, Any]],
    new_topic_candidates: list[dict[str, Any]] | None = None,
    available_degrees: set[str],
) -> str:
    hinted_candidates = [
        normalize_nullable_string(item.get("degree"))
        for item in (new_topic_candidates or [])
        if isinstance(item, dict)
    ]
    hinted_counts: dict[str, int] = {}
    for degree in hinted_candidates:
        if degree and degree in available_degrees:
            hinted_counts[degree] = hinted_counts.get(degree, 0) + 1
    if hinted_counts:
        return sorted(hinted_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    if medium_matches:
        counts: dict[str, int] = {}
        for match in medium_matches:
            degree = str(match.get("degree") or "").strip()
            if not degree:
                continue
            counts[degree] = counts.get(degree, 0) + 1
        if counts:
            return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    baseline_degree = discovery_baseline_degree(primary_degree)
    if baseline_degree in available_degrees:
        return str(baseline_degree)
    if "level1" in available_degrees:
        return "level1"
    return sorted(available_degrees)[0] if available_degrees else "unknown"


def infer_later_degree_from_title(title: str, *, available_degrees: set[str]) -> str | None:
    key = normalize_lookup_term(title)
    # Exact match first (fastest path, handles canonical compound titles).
    degree = LATER_DEGREE_TITLE_SIGNALS.get(key)
    if degree and degree in available_degrees:
        return degree
    # Substring scan: return the highest-degree signal whose key appears as a
    # word sequence anywhere in the normalized title.  Needed for compound
    # headings like "Fellow Craft: Winding Stairs, Middle Chamber, Shibboleth"
    # where no single key matches the full string.
    best_degree: str | None = None
    best_rank = -1
    for signal_key, signal_degree in LATER_DEGREE_TITLE_SIGNALS.items():
        if signal_degree not in available_degrees:
            continue
        if not contains_lookup_term(key, signal_key):
            continue
        rank = DEGREE_ORDER.get(signal_degree, -1)
        if rank > best_rank:
            best_rank = rank
            best_degree = signal_degree
    return best_degree


def infer_encyclopedia_lane_from_title(title: str) -> str | None:
    """Return the target encyclopedia lane if *title* matches ENCYCLOPEDIA_TOPIC_SIGNALS.

    Uses exact key match only (no substring scan) so the signal is tight
    and does not accidentally absorb degree-root topics whose titles happen to
    contain a virtue word as a substring.
    """
    key = normalize_lookup_term(title)
    return ENCYCLOPEDIA_TOPIC_SIGNALS.get(key)


def build_discovery_record(
    *,
    section: ExtractedSection,
    route_primary_degree: str | None,
    combined_result: dict[str, Any],
    resolution: dict[str, list[dict[str, Any]]],
    allowed_degrees: Iterable[str],
    apply_allowed_degrees: Iterable[str],
) -> dict[str, Any]:
    strong_matches = list(resolution.get("strong", []))
    medium_matches = list(resolution.get("medium", []))
    rejected_matches = list(resolution.get("rejected", []))
    new_topic_candidates = [
        {
            "title": normalize_text(item.get("title")),
            "degree": normalize_nullable_string(item.get("degree")),
        }
        for item in combined_result.get("new_topic_candidates", [])
        if isinstance(item, dict) and normalize_text(item.get("title"))
    ]
    if (
        not strong_matches
        and not medium_matches
        and not new_topic_candidates
        and not section.is_noise_candidate
        and section.unit_kind == "topic"
        and section.marker_type == "pause"
        and normalize_text(section.normalized_title or section.title)
    ):
        new_topic_candidates = [
            {
                "title": normalize_text(section.normalized_title or section.title),
                "degree": discovery_baseline_degree(route_primary_degree) or "unknown",
            }
        ]
    reason_codes = list(section.normalization_flags)
    available_degrees = set(allowed_degrees)
    apply_allowed = set(apply_allowed_degrees)
    baseline_degree = discovery_baseline_degree(route_primary_degree)

    decision = "reject_or_noise"
    candidate_degree = "unknown"
    degree_confidence = "low"
    confidence = "low"

    if strong_matches:
        top_match = strong_matches[0]
        candidate_degree = str(top_match.get("degree") or "unknown")
        if candidate_degree not in apply_allowed and candidate_degree != "unknown":
            # Fragmentary/procedural sections must not be promoted into a
            # discovery-only degree even when there is a strong lexical match.
            # They cannot produce a reliable companion candidate and the match
            # is almost always a false positive driven by shared vocabulary.
            if section.unit_kind in {"fragmentary_topic", "procedural_fragment"}:
                decision = "reject_or_noise"
                candidate_degree = "unknown"
                degree_confidence = "low"
                confidence = "medium"
                reason_codes.append("FRAGMENTARY_CANONICAL_BLOCK")
            else:
                decision = "later_degree_candidate"
                degree_confidence = "high"
                confidence = "high"
                reason_codes.extend(["DISCOVERY_ONLY_DEGREE", "LATER_DEGREE_SIGNAL"])
        else:
            decision = "existing_match"
            degree_confidence = "high"
            confidence = "high"
        if top_match.get("heading_hit"):
            reason_codes.append("HEADING_MATCH")
        if len(top_match.get("supporting_terms", [])) >= 2:
            reason_codes.append("MULTI_TERM_OVERLAP")
        if top_match.get("provider_suggested"):
            reason_codes.append("PROVIDER_TARGET_HINT")
    elif medium_matches or new_topic_candidates:
        candidate_degree = select_candidate_degree(
            primary_degree=route_primary_degree,
            medium_matches=medium_matches,
            new_topic_candidates=new_topic_candidates,
            available_degrees=available_degrees,
        )
        promotion_blocked = section.unit_kind in {"procedural_fragment", "fragmentary_topic"}
        # Harden PRIMARY_DEGREE_FALLBACK: if select_candidate_degree fell back to the
        # baseline degree but an explicit non-baseline title signal exists, block the
        # fallback and prefer the signalled degree (which will become later_degree_candidate
        # through the normal ranking logic below).
        if not promotion_blocked and candidate_degree == (baseline_degree or "level1"):
            _blocking_title_signal = infer_later_degree_from_title(
                section.normalized_title or section.title,
                available_degrees=available_degrees,
            )
            if _blocking_title_signal and _blocking_title_signal != candidate_degree:
                candidate_degree = _blocking_title_signal
                reason_codes.append("PRIMARY_DEGREE_FALLBACK_BLOCKED")
        if promotion_blocked:
            decision = "reject_or_noise"
            candidate_degree = "unknown"
            degree_confidence = "low"
            confidence = "medium"
            if section.unit_kind == "procedural_fragment":
                reason_codes.append("PROCEDURAL_CANONICAL_BLOCK")
            else:
                reason_codes.append("FRAGMENTARY_CANONICAL_BLOCK")
            reason_codes.append("REJECTED_AS_FRAGMENTARY")
        else:
            candidate_rank = DEGREE_ORDER.get(candidate_degree, -1)
            primary_rank = DEGREE_ORDER.get(str(baseline_degree), -1)
            if candidate_degree not in apply_allowed and candidate_degree != "unknown":
                decision = "later_degree_candidate"
                reason_codes.extend(["DISCOVERY_ONLY_DEGREE", "LATER_DEGREE_SIGNAL"])
            elif candidate_degree == "level3" or (candidate_rank >= 0 and primary_rank >= 0 and candidate_rank > primary_rank):
                decision = "later_degree_candidate"
                reason_codes.append("LATER_DEGREE_SIGNAL")
            else:
                decision = "new_canonical_topic"
            degree_confidence = "medium" if medium_matches else "low"
            confidence = degree_confidence
        if medium_matches:
            reason_codes.append("WEAK_EXISTING_OVERLAP")
        if new_topic_candidates:
            reason_codes.append("NEW_TOPIC_HINT")
        if candidate_degree == baseline_degree:
            reason_codes.append("PRIMARY_DEGREE_FALLBACK")
    else:
        decision = "reject_or_noise"
        candidate_degree = "unknown"
        if section.is_noise_candidate:
            confidence = "high"
        reason_codes.append("NO_MATCH_FOUND")

    title_degree_signal = infer_later_degree_from_title(
        section.normalized_title or section.title,
        available_degrees=available_degrees,
    )
    out_of_route_title_signal = infer_later_degree_from_title(
        section.normalized_title or section.title,
        available_degrees={"level1", "level2", "level3"},
    )
    if (
        out_of_route_title_signal
        and out_of_route_title_signal not in apply_allowed
        and section.unit_kind == "topic"
        and not section.is_noise_candidate
        and decision in {"new_canonical_topic", "later_degree_candidate"}
    ):
        decision = "reject_or_noise"
        candidate_degree = "unknown"
        degree_confidence = "low"
        confidence = "high"
        reason_codes.extend(["TITLE_DEGREE_SIGNAL", "EXPLICIT_ROUTING_REQUIRED", "TITLE_DEGREE_OUT_OF_ROUTE"])
    # The title signal override applies to new/candidate decisions AND to
    # existing_match when the signal degree is strictly higher than the matched
    # degree.  This prevents a strong lower-degree catalog hit from silencing a
    # clear higher-degree title (e.g. "Master Mason: …" matching a level1 entry).
    _existing_match_overrideable = (
        decision == "existing_match"
        and DEGREE_ORDER.get(title_degree_signal or "", -1) > DEGREE_ORDER.get(candidate_degree, -1)
    )
    if (
        title_degree_signal
        and section.unit_kind == "topic"
        and not section.is_noise_candidate
        and (decision in {"new_canonical_topic", "later_degree_candidate"} or _existing_match_overrideable)
    ):
        candidate_degree = title_degree_signal
        candidate_rank = DEGREE_ORDER.get(candidate_degree, -1)
        primary_rank = DEGREE_ORDER.get(str(baseline_degree), -1)
        if candidate_degree not in apply_allowed or (
            candidate_rank >= 0 and primary_rank >= 0 and candidate_rank > primary_rank
        ):
            decision = "later_degree_candidate"
        degree_confidence = "high"
        confidence = "high"
        reason_codes.extend(["TITLE_DEGREE_SIGNAL", "LATER_DEGREE_SIGNAL"])

    if section.marker_type == "pause":
        reason_codes.append("PAUSE_UNIT")

    # E1-A: Encyclopedia-first routing.
    # Before the noise-candidate override, check whether the normalized title
    # matches ENCYCLOPEDIA_TOPIC_SIGNALS.  Only applies to true topic sections
    # (not noise candidates, not is_noise_candidate structural noise) where the
    # current decision is a non-existing-match outcome — i.e., the section is
    # NOT already matched to an existing degree entry.  This re-routes known
    # Masonic vocabulary entries away from new_canonical_topic / later_degree_candidate
    # (where human reviewers must manually defer them) and into encyclopedia_candidate
    # so they reach the encyclopedia lane automatically.
    encyclopedia_lane: str | None = None
    if (
        not section.is_noise_candidate
        and section.unit_kind == "topic"
        and decision in {"new_canonical_topic", "later_degree_candidate", "reject_or_noise"}
        and decision != "existing_match"
    ):
        encyclopedia_lane = infer_encyclopedia_lane_from_title(
            section.normalized_title or section.title
        )
        if encyclopedia_lane:
            decision = "encyclopedia_candidate"
            candidate_degree = "encyclopedia"
            degree_confidence = "high"
            confidence = "high"
            reason_codes.append("ENCYCLOPEDIA_VOCABULARY_MATCH")

    if section.is_noise_candidate and decision != "existing_match":
        decision = "reject_or_noise"
        candidate_degree = "unknown"
        degree_confidence = "low"
        confidence = "high"

    return {
        "section_id": section.section_id,
        "source_title": section.title,
        "normalized_title": section.normalized_title or section.title,
        "unit_kind": section.unit_kind,
        "is_noise_candidate": section.is_noise_candidate,
        "decision": decision,
        "candidate_degree": candidate_degree,
        "degree_confidence": degree_confidence,
        "confidence": confidence,
        "encyclopedia_lane": encyclopedia_lane,
        "reason_codes": unique_strings(reason_codes),
        "strong_match_count": len(strong_matches),
        "medium_match_count": len(medium_matches),
        "rejected_match_count": len(rejected_matches),
        "top_strong_matches": [
            {"degree": item.get("degree"), "slug": item.get("slug"), "title": item.get("title")}
            for item in strong_matches[:5]
        ],
        "top_medium_matches": [
            {"degree": item.get("degree"), "slug": item.get("slug"), "title": item.get("title")}
            for item in medium_matches[:5]
        ],
        "new_topic_hints": unique_strings(item["title"] for item in new_topic_candidates if item.get("title"))[:8],
    }
