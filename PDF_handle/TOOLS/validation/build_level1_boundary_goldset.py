from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import argparse
from pathlib import Path
from typing import Any

from common import CODE_ROOT
from pipeline_utils import read_json, write_json


DEFAULT_SOURCE_RUN_DIR = (
    CODE_ROOT
    / "PDF_handle"
    / "TOOLS"
    / "reports"
    / "phase_h_post_gating_live_smoke"
    / "2026-03-19T22-51-17+00-00"
)
DEFAULT_OUTPUT_PATH = CODE_ROOT / "PDF_handle" / "TOOLS" / "data" / "level1_boundary_goldset.json"


TARGETS: list[tuple[str, str, str | None, str, str]] = [
    ("degree-1-entered-apprentice::reading_layers.basic::p1", "keep", None, "strict_level1_core", "Explicit Degree 1 orientation content with no later-degree contamination."),
    ("degree-1-entered-apprentice::reading_layers.symbolic::p1", "keep", None, "strict_level1_symbolic", "Degree 1 symbolic explanation remains core instructional material."),
    ("degree-1-entered-apprentice::full_summary::p2", "keep", None, "strict_level1_summary", "Summarizes Entered Apprentice scope without later-degree drift."),
    ("l1-gate-what-is-degree::candidate_lesson::p2", "keep", None, "gate_orientation", "Gate/orientation framing belongs in level1 core."),
    ("ritual-flow::symbolic_meaning::p17", "keep", None, "strict_level1_symbolic", "Symbolic explanation stays inside level1 ritual framing."),
    ("allegory-shloshet-hadarim::symbolic_meaning::p1", "keep", None, "boundary_core_keep", "Borderline but still framed as core level1 allegorical explanation."),
    ("ritual-flow::candidate_lesson::p16", "keep", None, "boundary_core_keep", "Borderline candidate lesson still serves direct level1 instruction."),
    ("ritual-flow::candidate_lesson::p26", "move_to_library", "higher_degree_material", "advanced_blue_lodge_out_of_core", "Explicit advanced Blue Lodge anchor should be preserved outside strict core."),
    ("ritual-flow::candidate_lesson::p28", "move_to_library", "higher_degree_material", "advanced_blue_lodge_out_of_core", "Advanced Blue Lodge material is useful but out of core scope."),
    ("ritual-flow::full_summary::p52", "move_to_library", "higher_degree_material", "advanced_blue_lodge_out_of_core", "Summary row contains later-degree contamination and should not remain core."),
    ("ritual-flow::full_summary::p67", "move_to_library", "higher_degree_material", "advanced_blue_lodge_out_of_core", "Degree 2/3 anchored Blue Lodge material must leave strict keep."),
    ("obligation-and-law::candidate_lesson::p35", "move_to_library", "higher_degree_material", "advanced_blue_lodge_out_of_core", "Advanced obligation material is valid but should be preserved outside core."),
    ("obligation-and-law::candidate_lesson::p37", "move_to_library", "higher_degree_material", "advanced_blue_lodge_out_of_core", "Explicit advanced Blue Lodge row belongs in higher-degree preservation."),
    ("obligation-and-law::full_summary::p63", "move_to_library", "higher_degree_material", "advanced_blue_lodge_out_of_core", "Summary contains higher-degree contamination and should move to library."),
    ("obligation-and-law::full_summary::p76", "move_to_library", "higher_degree_material", "advanced_blue_lodge_out_of_core", "Degree contamination disqualifies this row from strict keep."),
    ("l1-ritual-habakasha-lehikanes::reading_layers.advanced::p1", "keep_here_framed", None, "framed_blue_lodge_context", "Short explanatory advanced framing is allowed in Hybrid Core+Frame."),
    ("l1-ritual-hahovala-harishona-bemerkhav-halishka::reading_layers.advanced::p1", "keep_here_framed", None, "framed_blue_lodge_context", "Advanced framing supports level1 understanding without transferring later-degree procedure."),
    ("l1-obligation-mashmaut-hahitchayvut::reading_layers.advanced::p1", "keep_here_framed", None, "framed_blue_lodge_context", "Framed obligation context remains acceptable as explanatory support."),
    ("l1-obligation-chovot-haach-badraga-harishona::symbolic_meaning::p2", "keep_here_framed", None, "framed_blue_lodge_context", "Symbolic overlay remains safe only as framed support, not strict core."),
    ("l1-obligation-mishmaat-taksit-mul-mishmaat-pnimit::reading_layers.advanced::p1", "keep_here_framed", None, "framed_blue_lodge_context", "Blue Lodge comparison is short and explanatory rather than procedural."),
    ("l1-obligation-chok-matzpun-veachva::reading_layers.advanced::p1", "keep_here_framed", None, "framed_blue_lodge_context", "Advanced obligation framing stays as contextual support only."),
    ("l1-obligation-chok-matzpun-veachva::symbolic_meaning::p2", "keep_here_framed", None, "framed_blue_lodge_context", "Symbolic explanation is acceptable as framed material."),
    ("l1-inner-work-hamaavar-meeven-gvila-leeven-mesutetet::reading_layers.advanced::p1", "keep_here_framed", None, "framed_blue_lodge_context", "Short framed inner-work explanation supports level1 interpretation."),
    ("hasarat-matachot::reading_layers.advanced::p1", "keep_here_framed", None, "framed_blue_lodge_context", "Advanced context is explanatory and non-procedural."),
    ("cable-tow::reading_layers.advanced::p1", "keep_here_framed", None, "framed_blue_lodge_context", "Borderline advanced framing remains allowed only in keep_here_framed."),
    ("cable-tow::candidate_lesson::p2", "move_to_library", "historical_research", "library_historical", "Historical preservation is useful but not core level1 content."),
    ("obligation-and-law::candidate_lesson::p78", "move_to_library", "historical_research", "library_historical", "Historically oriented material belongs in research/library."),
    ("obligation-and-law::symbolic_meaning::p74", "move_to_library", "historical_research", "library_historical", "Historically explanatory row is valuable outside core."),
    ("l1-gate-purpose::candidate_lesson::p2", "move_to_library", "comparative_rituals", "library_comparative", "Comparative ritual analysis should stay in library."),
    ("l1-gate-purpose::full_summary::p1", "move_to_library", "comparative_rituals", "library_comparative", "Comparative framing is useful reference material, not core content."),
    ("l1-obligation-mashmaut-hahitchayvut::candidate_lesson::p2", "move_to_library", "comparative_rituals", "library_comparative", "Comparative synthesis belongs in library context."),
    ("l1-ritual-rega-kabalat-haor::symbolic_meaning::p2", "move_to_library", "comparative_rituals", "library_comparative", "Comparative symbolic material should be preserved outside core."),
    ("cable-tow::symbolic_meaning::p3", "move_to_library", "biblical_symbolic_expansion", "library_biblical", "Biblical-symbolic expansion is valuable but not core level1."),
    ("obligation-and-law::symbolic_meaning::p81", "move_to_library", "biblical_symbolic_expansion", "library_biblical", "Biblical expansion belongs in library unless a stronger later-degree thread dominates."),
    ("ritual-flow::symbolic_meaning::p70", "move_to_library", "biblical_symbolic_expansion", "library_biblical", "Extended biblical-symbolic material should be preserved in library."),
    ("cable-tow::candidate_lesson::p5", "create_future_entry_candidate", "royal_arch_names_and_word", "future_entry_royal_arch", "Coherent Royal Arch thread deserves its own downstream entry."),
    ("cable-tow::symbolic_meaning::p2", "create_future_entry_candidate", "royal_arch_names_and_word", "future_entry_royal_arch", "Later-degree names/word theme is entry-worthy rather than core/library-only."),
    ("cable-tow::symbolic_meaning::p6", "create_future_entry_candidate", "royal_arch_names_and_word", "future_entry_royal_arch", "Same coherent Royal Arch theme should consolidate into a future entry."),
    ("candidate-preparation::candidate_lesson::p15", "create_future_entry_candidate", "royal_arch_names_and_word", "future_entry_royal_arch", "This later-degree thematic thread warrants its own entry."),
    ("cable-tow::candidate_lesson::p6", "create_future_entry_candidate", "royal_arch_hidden_vault_motifs", "future_entry_royal_arch", "Hidden-vault motif is a coherent downstream topic."),
    ("cable-tow::symbolic_meaning::p4", "create_future_entry_candidate", "royal_arch_hidden_vault_motifs", "future_entry_royal_arch", "Royal Arch hidden-vault theme should preserve as a future entry."),
    ("candidate-preparation::candidate_lesson::p14", "create_future_entry_candidate", "royal_arch_return_from_babylon", "future_entry_royal_arch", "Return-from-Babylon motif is a coherent future-entry theme."),
    ("ritual-flow::candidate_lesson::p55", "create_future_entry_candidate", "royal_arch_return_from_babylon", "future_entry_royal_arch", "Later-degree restoration narrative belongs in future-entry queue."),
    ("ritual-flow::full_summary::p112", "create_future_entry_candidate", "biblical_symbolic_names_and_signs", "future_entry_biblical_symbols", "Coherent external symbolic theme deserves a dedicated entry."),
    ("obligation-and-law::full_summary::p130", "create_future_entry_candidate", "biblical_symbolic_names_and_signs", "future_entry_biblical_symbols", "This names/signs theme is entry-worthy rather than core material."),
    ("ritual-flow::symbolic_meaning::p64", "create_future_entry_candidate", "royal_arch_names_and_word", "conflict_resolution_future_entry", "When Royal Arch thread is coherent, future_entry should beat biblical library routing."),
    ("obligation-and-law::symbolic_meaning::p75", "create_future_entry_candidate", "royal_arch_names_and_word", "conflict_resolution_future_entry", "Repeated Royal Arch vs biblical conflict should resolve deterministically to future entry."),
    ("ritual-flow::candidate_lesson::p10", "move_to_library", "historical_research", "manual_review_library_fallback", "Known manual-review cluster should deterministically preserve to library."),
    ("obligation-and-law::candidate_lesson::p27", "move_to_library", "historical_research", "manual_review_library_fallback", "Known manual-review cluster should route to library without provider."),
    ("l1-gate-category-landing::full_summary::p1", "move_to_library", "historical_research", "manual_review_library_fallback", "Landing-page synthesis should preserve to library instead of lingering in provider review."),
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the level1 boundary goldset from the accepted source run.")
    parser.add_argument("--source-run-dir", type=Path, default=DEFAULT_SOURCE_RUN_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser


def flatten_rows(entries: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for row in entry.get(key, []):
            if isinstance(row, dict):
                review_unit_id = str(row.get("review_unit_id") or "").strip()
                if review_unit_id:
                    rows[review_unit_id] = row
    return rows


def main() -> None:
    args = build_parser().parse_args()
    source_run_dir = args.source_run_dir.resolve()
    output_path = args.output.resolve()

    f2_entries = read_json(source_run_dir / "f2" / "semantic_purity_entries.json")
    f3_entries = read_json(source_run_dir / "f3" / "content_routing_entries.json")
    f2_rows = flatten_rows(f2_entries, "paragraph_reviews")
    f3_rows = flatten_rows(f3_entries, "routing_reviews")

    entries: list[dict[str, Any]] = []
    for review_unit_id, target_outcome, target_bucket_or_label, scope_class, rationale in TARGETS:
        f2_row = f2_rows.get(review_unit_id)
        f3_row = f3_rows.get(review_unit_id)
        entries.append(
            {
                "review_unit_id": review_unit_id,
                "excerpt": (f2_row or f3_row or {}).get("text_excerpt"),
                "current_f2_outcome": {
                    "final_verdict": (f2_row or {}).get("final_verdict"),
                    "recommended_preservation_action": (f2_row or {}).get("recommended_preservation_action"),
                    "recommended_destination": (f2_row or {}).get("recommended_destination"),
                },
                "current_f3_outcome": {
                    "routing_decision": (f3_row or {}).get("routing_decision"),
                    "library_bucket": (f3_row or {}).get("library_bucket"),
                    "future_entry_label": (f3_row or {}).get("future_entry_label"),
                },
                "target_outcome": target_outcome,
                "target_bucket_or_label": target_bucket_or_label,
                "scope_class": scope_class,
                "rationale": rationale,
            }
        )

    payload = {
        "schema_version": "1.0.0",
        "source_run_id": source_run_dir.name,
        "source_report_dir": str(source_run_dir),
        "entry_count": len(entries),
        "entries": entries,
    }
    write_json(output_path, payload)


if __name__ == "__main__":
    main()

