"""Title-page sections must not become content candidates.

In the Color-Symbolism pilot a semantic heading whose body was only author,
date, and lodge metadata passed Step 5 as kind=topic and became a level2
candidate. The sparse-metadata-body filter classifies such sections as
front_matter regardless of how clean the heading looks.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.steps.stage_support import (
    ExtractedSection,
    is_sparse_publication_metadata_body,
    normalize_extracted_sections,
)

TITLE_PAGE_BODY = (
    "Transactions of A. Douglas Smith, Jr. Lodge of Research #1949 Volume 4 (1998 — 2001)\n"
    "Color Symbolism And Freemasonry, by John Shroeder, PM, Presented August 29, 1998\n"
    "By\n"
    "John Shroeder, PM\n"
    "Presented to A. Douglas Smith, Jr. Lodge of Research, #1949\n"
    "On\n"
    "August 29, 1998\n"
)

SHORT_PROSE_BODY = (
    "The trowel spreads the cement of brotherly love among the brethren, "
    "binding the members of the lodge into one sacred band of friends."
)


def _section(text: str, *, title: str = "Color Symbolism And Freemasonry") -> ExtractedSection:
    return ExtractedSection(
        section_id="section-0001",
        title=title,
        marker_type="heading-2",
        text=text,
        source_anchor="color-symbolism-and-freemasonry",
        source_order=1,
    )


class TestSparseMetadataBodyHelper(unittest.TestCase):
    def test_title_page_body_is_sparse_metadata(self) -> None:
        self.assertTrue(is_sparse_publication_metadata_body(TITLE_PAGE_BODY))

    def test_short_prose_without_metadata_is_not(self) -> None:
        self.assertFalse(is_sparse_publication_metadata_body(SHORT_PROSE_BODY))

    def test_empty_body_is_not(self) -> None:
        self.assertFalse(is_sparse_publication_metadata_body(""))

    def test_residual_token_boundary(self) -> None:
        # 39 residual prose tokens with mostly-metadata lines -> sparse;
        # 40 residual tokens -> not sparse.
        prose_39 = " ".join(["symbol"] * 39)
        prose_40 = " ".join(["symbol"] * 40)
        metadata = "Presented to the Lodge of Research, August 29, 1998\nCopyright 2004 All Rights Reserved\n"
        self.assertTrue(is_sparse_publication_metadata_body(metadata + prose_39))
        self.assertFalse(is_sparse_publication_metadata_body(metadata + prose_40))

    def test_metadata_ratio_boundary(self) -> None:
        metadata_line = "Presented to the Lodge of Research, August 29, 1998"
        prose_line = "A short reflection on the symbol"
        # 1 metadata line of 3 (ratio 0.33) -> not sparse even with few tokens
        body_low_ratio = "\n".join([metadata_line, prose_line, prose_line])
        self.assertFalse(is_sparse_publication_metadata_body(body_low_ratio))
        # 2 metadata lines of 3 (ratio 0.66) with sparse residual -> sparse
        body_high_ratio = "\n".join([metadata_line, metadata_line, prose_line])
        self.assertTrue(is_sparse_publication_metadata_body(body_high_ratio))


class TestSectionClassification(unittest.TestCase):
    def test_semantic_heading_with_author_metadata_body_is_front_matter(self) -> None:
        normalized = normalize_extracted_sections([_section(TITLE_PAGE_BODY)])[0]
        self.assertEqual(normalized.unit_kind, "front_matter")
        self.assertIn("TITLE_PAGE_AUTHOR_METADATA", normalized.normalization_flags)
        self.assertTrue(normalized.is_noise_candidate)

    def test_short_real_section_without_metadata_stays_topic(self) -> None:
        normalized = normalize_extracted_sections(
            [_section(SHORT_PROSE_BODY, title="The Trowel")]
        )[0]
        self.assertEqual(normalized.unit_kind, "topic")
        self.assertFalse(normalized.is_noise_candidate)

    def test_rich_section_with_one_metadata_line_stays_topic(self) -> None:
        rich_body = (
            "Presented to A. Douglas Smith, Jr. Lodge of Research, #1949\n"
            + "Blue symbolism connects moral aspiration, fidelity, friendship, and instruction. " * 20
        )
        normalized = normalize_extracted_sections(
            [_section(rich_body, title="Blue: The Color of the Symbolic Lodge")]
        )[0]
        self.assertEqual(normalized.unit_kind, "topic")
        self.assertNotIn("TITLE_PAGE_AUTHOR_METADATA", normalized.normalization_flags)

    def test_page_level_rich_content_fallback_still_works(self) -> None:
        section = ExtractedSection(
            section_id="section-0005",
            title="Page 5",
            marker_type="heading-2",
            text=(
                "## Page 5\n\n"
                "Transactions of A. Douglas Smith, Jr. Lodge of Research #1949 Volume 4\n"
                "Page 15\n"
                + "Blue symbolism connects moral aspiration, fidelity, friendship, and instruction. " * 20
            ),
            source_anchor="page-5",
            source_order=5,
        )
        normalized = normalize_extracted_sections([section])[0]
        self.assertEqual(normalized.unit_kind, "topic")
        self.assertIn("PAGE_RICH_CONTENT_FALLBACK", normalized.normalization_flags)


if __name__ == "__main__":
    unittest.main()
