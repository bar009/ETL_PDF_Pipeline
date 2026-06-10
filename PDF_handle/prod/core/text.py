from __future__ import annotations

import hashlib
import re
import unicodedata


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def normalize_newlines(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.strip()


# ---------------------------------------------------------------------------
# Canonical title normalization
# Used by new-source E1/E2 pipeline only.
# Do NOT apply retroactively to existing site data or stored slugs.
# ---------------------------------------------------------------------------

# Dashes/hyphens/en-dash/em-dash → ASCII hyphen
_DASH_RE = re.compile(r"[\u2010-\u2015\u2212\uFE58\uFE63\uFF0D]")

# Typographic quotes → straight apostrophe/quote
_QUOTE_MAP = str.maketrans({
    "\u2018": "'", "\u2019": "'",   # ' '
    "\u201C": '"', "\u201D": '"',   # " "
    "\u2032": "'", "\u2033": '"',   # prime / double-prime
})

# Collapse runs of whitespace
_SPACE_RE = re.compile(r"\s+")

# Used for slug generation: anything that is not a-z, 0-9
_SLUG_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")

# Used for match key: collapse hyphens, spaces, and punctuation together
_MATCH_COLLAPSE_RE = re.compile(r"[\s\-]+")
# Strip residual non-alphanumeric, non-space chars from match key (apostrophes, dots, commas, etc.)
_MATCH_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def canonical_normalize(title: str) -> str:
    """Return an ASCII-safe canonical form of a raw candidate title.

    Steps:
    1. Strip leading/trailing whitespace.
    2. Normalize typographic dashes to ASCII hyphen.
    3. Normalize typographic quotes to ASCII equivalents.
    4. Strip Unicode diacritics (é → e, à → a, ñ → n, etc.).
    5. Collapse internal whitespace runs to a single space.

    The result is a clean mixed-case string suitable for display.
    It preserves original casing — use .lower() for matching.

    Examples:
        "RÉUNION"                          → "REUNION"
        "Hiram–Abiff"                      → "Hiram-Abiff"
        "Trestle\u2010Board"               → "Trestle-Board"
        "L\u2019Équerre"                   → "L'Equerre"
        "  multiple   spaces  "            → "multiple spaces"
    """
    s = str(title or "").strip()
    # Typographic dashes → hyphen
    s = _DASH_RE.sub("-", s)
    # Typographic quotes → ASCII
    s = s.translate(_QUOTE_MAP)
    # Decompose Unicode, remove combining diacritics (category Mn)
    nfd = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    # Recompose (NFC) so remaining chars are canonical
    s = unicodedata.normalize("NFC", s)
    # Collapse whitespace
    s = _SPACE_RE.sub(" ", s).strip()
    return s


def canonical_match_key(title: str) -> str:
    """Lowercase + collapse hyphens/spaces for duplicate detection.

    "Cable-Tow" == "cable tow" == "CABLE TOW" all map to "cable tow".
    "RÉUNION" → canonical_normalize first → "REUNION" → "reunion".

    Always call canonical_normalize before this for cross-script safety.
    """
    normed = canonical_normalize(title)
    key = normed.lower()
    # Strip residual punctuation (apostrophes, dots, commas, etc.) before collapsing
    key = _MATCH_PUNCT_RE.sub(" ", key)
    key = _MATCH_COLLAPSE_RE.sub(" ", key).strip()
    return key


def canonical_slug(title: str) -> str:
    """Generate a URL-safe slug from a canonical title.

    canonical_normalize is applied first, so diacritics and typographic
    dashes are handled before slug generation.

    "The Molten Sea"        → "the-molten-sea"
    "Lion of the Tribe"     → "lion-of-the-tribe"
    "A.A.S. Rite"           → "aas-rite"
    "RÉUNION"               → "reunion"
    """
    normed = canonical_normalize(title)
    lowered = normed.lower()
    return _SLUG_NON_ALNUM_RE.sub("-", lowered).strip("-")


def enc_canonical_slug(title: str) -> str:
    """Encyclopedia entry slug: enc-{canonical_slug(title)}."""
    return "enc-" + canonical_slug(title)
