# Phase F1: Rite / System Purity Audit

Phase F1 adds a second audit axis on top of degree purity.

- Degree purity asks: does this belong to the correct degree?
- System purity asks: does this belong to the correct ritual family at all?

For v1, the expected family for `level1` is `blue_lodge_symbolic`.

## In-Scope Fields

Hard teaching gate:
- `reading_layers.basic`
- `reading_layers.symbolic`
- `reading_layers.advanced`
- `symbolic_meaning`
- `candidate_lesson`

Soft legacy field:
- `full_summary`

Out of scope for F1 v1:
- `short_summary`

## Detected Families

The audit may emit:
- `royal_arch_or_appendant`
- `comparative_research`
- `external_symbolic_or_biblical_expansion`

## Rule Groups

- `cross-system-terms`
  - explicit rite markers from a foreign system
- `external-ritual-narrative`
  - foreign ritual story material or external symbolic expansion
- `comparative-without-framing`
  - foreign-system material in `reading_layers.advanced` without valid local framing
- `advanced-foreign-material-dominates`
  - framed comparison grows too large and stops being subordinate to the current entry
- `candidate-preserve-for-library`
  - material is likely better preserved in research/library context

## Framing Validity

For `reading_layers.advanced`, framing is valid only if the framing phrase appears:
- in the same paragraph as the foreign-system material
- or in the opening sentence of the immediately preceding paragraph

Framing never cascades beyond one paragraph.

The current framing allowlist is:
- `במסורות אחרות`
- `במערכות מאוחרות יותר`
- `במסלולים נלווים`
- `במבט מחקרי רחב יותר`
- `בהשוואה למסגרות אחרות`
- `בקריאות השוואתיות`
- `מחוץ ללשכה הסמלית`

## Comparative Allowlist

Comparative references are allowed in `reading_layers.advanced` only when they are:
- explicitly framed
- subordinate to the current entry's expected family

Allowed comparative families in that mode:
- `royal_arch_or_appendant`
- `comparative_research`
- `external_symbolic_or_biblical_expansion`

If more than half of the advanced paragraphs are foreign-system paragraphs, the audit emits `advanced-foreign-material-dominates`.

## Detection Confidence

- `high`
  - explicit rite markers such as `Royal Arch`, `Rabboni`, `Most Excellent`, `Excellent Master`, `קשת מלכותית`, `רבוני`
- `medium`
  - clustered narrative markers that strongly imply a specific foreign system
- `low`
  - weaker external symbolic or biblical expansion that does not justify a narrower family claim

## Severity vs Preservation

These are independent dimensions.

- `severity`
  - measures teaching or purity risk in the current entry
- `preservation_action`
  - measures recommended handling or destination

Examples:
- `error` + `move_to_library_or_research`
- `warning` + `keep_here_framed`

Allowed preservation actions:
- `keep_here_framed`
- `move_to_other_entry`
- `move_to_library_or_research`
- `drop`

`drop` is reserved for source-dump material with little teaching or research value.
