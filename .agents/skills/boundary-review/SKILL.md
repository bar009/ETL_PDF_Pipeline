---
name: boundary-review
description: Review degree boundaries, leakage, routing, preservation, and knowledge-flow placement in PDF_handle. Use when Codex needs to inspect or adjust whether content belongs in library, level1, level2, preservation, or future-entry queues, especially around F1/F2/F3/F4 style audits.
---

# Boundary Review

Use this skill when the core question is "does this content belong here?"

## Read First

Read these files in order:

1. `PDF_handle/AGENTS.md`
2. `PDF_handle/docs/DOMAIN_BOUNDARIES.md`
3. `PDF_handle/docs/RELATION_RULES.md`
4. `PDF_handle/docs/PROJECT_SCOPE.md`
5. `PDF_handle/docs/KNOWN_ISSUES.md`

Then read the directly relevant tool or report:

- `PDF_handle/TOOLS/audit_degree_classification.py`
- `PDF_handle/TOOLS/semantic_system_purity_review.py`
- `PDF_handle/TOOLS/content_routing_review.py`
- `PDF_handle/TOOLS/content_apply_engine.py`
- `PDF_handle/TOOLS/audit_knowledge_flow.py`

## Review Workflow

1. Identify the current lane of the material:
   - `library`
   - `level1`
   - `level2`
   - preservation
   - future-entry candidate
2. Identify whether the question is about:
   - degree leakage
   - system or rite purity
   - routing destination
   - relation quality
   - preservation-before-removal
3. Prefer the smallest decision that preserves provenance and reviewability.

## Boundary Heuristics

- Use `library` for preservation-first reference material.
- Use `level1` only for content that truly belongs in first-degree instruction.
- Use `level2` for material that is valid but too advanced or mis-scoped for `level1`.
- Use preservation or future-entry queues when the content should survive but not remain where it is.

## Do Not

- collapse boundary questions into keyword matching alone
- remove source content before preservation is explicit
- use knowledge links as a substitute for correct lane placement
