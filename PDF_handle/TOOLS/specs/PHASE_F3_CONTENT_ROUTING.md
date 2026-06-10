# Phase F3: Content Routing & Preservation Planning

Phase F3 is a read-only routing layer above F2.

It consumes an existing semantic system-purity review directory and produces a routing plan for flagged review units.

Goals:
- preserve coherent foreign or comparative material
- route good content toward existing entries, library/research, or future-entry seeds
- avoid dropping useful material by default
- prepare a later cleanup or merge phase without mutating site JSON in v1

Core behavior:
- input is an F2 report dir, not raw site data alone
- output is a routing plan only
- `move_to_existing_entry` is conservative and shortlist-bound
- `move_to_library` and `create_future_entry_candidate` use a checked-in routing taxonomy
- provider status is tracked as `routing_unit_status`
- taxonomy-driven routes record `taxonomy_match_reason`

Primary artifacts:
- `content_routing_summary.json`
- `content_routing_entries.json`
- `content_routing_findings.json`
- `content_routing_report.md`
- `content_routing_report.html`
- `future_entry_candidates.json`
- `library_preservation_queue.json`
