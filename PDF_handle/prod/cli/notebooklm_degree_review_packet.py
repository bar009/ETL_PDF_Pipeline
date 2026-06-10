from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.io import ensure_dir, read_json, utc_timestamp, write_json, write_text


DEGREE_RUBRIC = """Degree placement rubric:

Degree 1 / Entered Apprentice:
- Core shape: birth, physical discipline, first moral purification, foundational preparation.
- Native topics: restraint of passions, basic morality, time management, first-degree working tools, lambskin/apron, cardinal virtues, brotherly love/relief/truth when taught as foundations.
- Litmus: does the unit teach bodily restraint, basic virtue, foundational preparation, or first-degree instruction?

Degree 2 / Fellow Craft:
- Core shape: life, mind, intellectual expansion, science, architecture, middle chamber.
- Native topics: five senses, liberal arts and sciences, geometry, architecture, winding stairs, plumb/square/level when used as Fellow Craft teaching.
- Litmus: does the unit expand the intellect through arts, sciences, architecture, or reflective study?

Degree 3 / Master Mason:
- Core shape: death, spirit, fidelity, mortality, immortality, culmination.
- Native topics: Hiram material, five points of fellowship, lost word, acacia, coffin/grave/spade/setting-maul, trowel, mortality emblems.
- Litmus: does the unit confront mortality, spiritual continuity, resurrection/immortality, or fidelity under death/peril?

Level3 category skeleton:
- degree_structure: degree-wide framing, charge/duty, structure-of-degree, board-as-map readings.
- hiram_and_raising: Hiram narrative, loss, fidelity, raising, restoration, fellowship, distress.
- mortality_and_memorial: grave, acacia, burial, monument, mourning, time/death emblems, immortality.
- symbolic_field: native level3 standalone emblems not better framed as structure, Hiram, or memorial material.
- Do not classify Royal Arch, vault, recovery, or appendant-degree material as native level3.

Reject or merge instead of promote when:
- the unit is only ritual flow, dialogue continuation, officer procedure, governance/admin, source residue, or a dependent fragment.
- the topic is real but should merge into a broader existing canonical topic.
- the title is weak, procedural, or not a standalone teaching unit.
"""


OUTPUT_SCHEMA = {
    "candidate_id": "string copied exactly from input",
    "recommended_action": "approve | reject | merge_existing | route_later_degree | defer",
    "recommended_degree": "level1 | level2 | level3 | unknown",
    "recommended_level3_category": "degree_structure | hiram_and_raising | mortality_and_memorial | symbolic_field | empty string when not level3 approval",
    "approved_title": "short standalone English topic title, or empty string if not approved",
    "canonicality": "standalone_topic | alias_or_subtopic | procedural_fragment | source_residue | uncertain",
    "native_vs_mentioned": "native | merely_mentioned | unclear",
    "confidence": "high | medium | low",
    "evidence": "brief source-grounded evidence from the excerpt",
    "reason": "brief explanation using the degree rubric",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate NotebookLM-ready degree review packets from candidate_review_queue.json. "
            "This is report-only and does not call NotebookLM or mutate site data."
        )
    )
    parser.add_argument("--queue-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--max-excerpt-chars", type=int, default=1600)
    parser.add_argument("--rubric-file", type=Path, default=None, help="Optional extra rubric text to append.")
    return parser


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def truncate_text(value: Any, *, max_chars: int) -> str:
    text = " ".join(normalize_text(value).split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "..."


def load_queue(queue_file: Path) -> list[dict[str, Any]]:
    payload = read_json(queue_file.resolve())
    rows = payload.get("review_queue") if isinstance(payload, dict) else []
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def compact_candidate(row: dict[str, Any], *, max_excerpt_chars: int) -> dict[str, Any]:
    source_context = row.get("source_context") if isinstance(row.get("source_context"), dict) else {}
    return {
        "candidate_id": row.get("candidate_id"),
        "current_decision": row.get("decision"),
        "candidate_degree": row.get("candidate_degree"),
        "degree_confidence": row.get("degree_confidence"),
        "confidence": row.get("confidence"),
        "normalized_title": row.get("normalized_title"),
        "work_id": row.get("work_id"),
        "section_id": row.get("section_id"),
        "unit_kind": row.get("unit_kind"),
        "reason_codes": row.get("reason_codes", []),
        "language_warnings": row.get("language_warnings", []),
        "source_chapter_slug": source_context.get("chapter_slug"),
        "source_excerpt": truncate_text(source_context.get("source_excerpt"), max_chars=max_excerpt_chars),
    }


def batch_items(items: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    if batch_size < 1:
        raise SystemExit("--batch-size must be >= 1")
    return [items[index : index + batch_size] for index in range(0, len(items), batch_size)]


def render_batch_markdown(
    *,
    batch_number: int,
    total_batches: int,
    candidates: list[dict[str, Any]],
    extra_rubric: str,
) -> str:
    lines: list[str] = [
        f"# NotebookLM Degree Review Batch {batch_number} of {total_batches}",
        "",
        "Use only the provided source excerpts and the uploaded/source NotebookLM corpus. Do not invent missing facts.",
        "",
        "## Rubric",
        "",
        DEGREE_RUBRIC.strip(),
    ]
    if extra_rubric.strip():
        lines.extend(["", "## Extra Rubric From Operator", "", extra_rubric.strip()])

    lines.extend(
        [
            "",
            "## Required Output",
            "",
            "Return a single JSON array. Do not wrap it in markdown. Every input candidate must have exactly one output object.",
            "",
            "Each object must use this schema:",
            "",
            "```json",
            json.dumps(OUTPUT_SCHEMA, ensure_ascii=False, indent=2),
            "```",
            "",
            "Decision rules:",
            "",
            "- Use `approve` only for a real standalone teaching topic that belongs in the recommended degree.",
            "- For `approve` + `recommended_degree=level3`, set `recommended_level3_category` to exactly one locked level3 category.",
            "- Use `merge_existing` when the material is real but should not become a separate canonical entry.",
            "- Use `route_later_degree` when the current candidate degree is too early but the topic is valid for a later degree.",
            "- Use `reject` with a reason that clearly says `alias_only` or `relation_only` when the candidate should stay non-publish for one of those reasons.",
            "- Use `reject` for procedural, administrative, source-residue, or dependent fragment material.",
            "- Use `defer` when the excerpt is insufficient.",
            "",
            "## Candidates",
            "",
            "```json",
            json.dumps(candidates, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def render_master_prompt(total_batches: int) -> str:
    return "\n".join(
        [
            "# NotebookLM Degree Review Instructions",
            "",
            "Upload or paste one batch file at a time.",
            "",
            "For each batch, answer only with the required JSON array.",
            "",
            "After receiving all batches, save each answer as a separate response file so it can be converted into review decisions.",
            "",
            f"Total batches: {total_batches}",
            "",
            "Important: this review recommends degree placement only. It does not publish content and does not mutate canonical site data.",
            "",
        ]
    )


def main() -> None:
    args = build_parser().parse_args()
    output_dir = ensure_dir(args.output_dir.resolve())
    queue_entries = load_queue(args.queue_file)
    compact_entries = [
        compact_candidate(row, max_excerpt_chars=args.max_excerpt_chars)
        for row in queue_entries
    ]
    batches = batch_items(compact_entries, args.batch_size)
    extra_rubric = args.rubric_file.read_text(encoding="utf-8-sig") if args.rubric_file else ""

    manifest = {
        "created_at": utc_timestamp(),
        "queue_file": str(args.queue_file.resolve()),
        "candidate_count": len(compact_entries),
        "batch_size": args.batch_size,
        "batch_count": len(batches),
        "outputs": [],
    }

    for index, candidates in enumerate(batches, start=1):
        batch_name = f"notebooklm_degree_review_batch_{index:02d}.md"
        batch_path = output_dir / batch_name
        write_text(
            batch_path,
            render_batch_markdown(
                batch_number=index,
                total_batches=len(batches),
                candidates=candidates,
                extra_rubric=extra_rubric,
            ),
        )
        manifest["outputs"].append(str(batch_path))

    write_text(output_dir / "notebooklm_degree_review_master_prompt.md", render_master_prompt(len(batches)))
    write_json(output_dir / "notebooklm_degree_review_candidates.json", compact_entries)
    write_json(output_dir / "notebooklm_degree_review_manifest.json", manifest)
    print(
        "[done] notebooklm degree review packet "
        f"candidates={len(compact_entries)} batches={len(batches)} output={output_dir}",
        flush=True,
    )


if __name__ == "__main__":
    main()
