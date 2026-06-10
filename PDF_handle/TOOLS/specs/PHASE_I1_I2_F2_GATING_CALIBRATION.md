# Phase I.1-I.2: F2 Gating Calibration, Hebrew Signal Taxonomy, and Mixed Content Handling

## Goal

Phase I.1-I.2 hardens `semantic_system_purity_review.py` so F2 can distinguish more reliably between:

- `native`
- `mixed`
- `foreign`

without pushing more semantic burden onto the provider.

The product goal is conservative protection against higher-degree leakage while reducing false-positive escalation on legitimate Degree 1 material that happens to be ritual, symbolic, comparative, or research-framed.

## Why This Phase Exists

After Phase H and H.1:

- runtime stability improved
- malformed JSON dropped
- structured output became much more stable
- F3 improved more than F2

The remaining bottleneck in F2 is no longer provider transport quality. It is heuristic calibration:

- English-biased signal libraries on a mostly Hebrew corpus
- weak mixedness detection
- poor distinction between ritual mention and actual cross-degree leakage
- insufficient observability around why a unit was escalated

## Scope

In scope:

- `semantic_system_purity_review.py`
- Hebrew-aware signal libraries
- asymmetric native-confidence vs foreign-risk scoring
- mixedness detection
- reason-code observability
- golden-set evaluation design

Out of scope:

- model changes
- provider-policy redesign
- provider schema expansion
- F3/F4 redesign
- broad provider prompt redesign

## Architectural Rules

- AI remains escalation-only.
- The new distinctions live primarily in local heuristics, not in provider schema.
- Not every product distinction becomes a provider field.
- False negatives on foreign leakage remain more dangerous than false positives on native content.

## Internal Taxonomy

### `native_like`

Use when the unit has a valid Degree 1 core, no strong later-degree leakage, and only weak or safe medium framing.

### `mixed_like`

Use when the unit contains a valid Degree 1 core but then pivots into comparative, hierarchical, esoteric, or partially out-of-scope material.

### `foreign_like`

Use when the unit contains strong later-degree leakage or dominant foreign-system material whose primary function is out-of-degree disclosure.

## Two Separate Risk Axes

F2 should not collapse everything into one generic "foreign" suspicion bucket.

It should distinguish between:

- `later_degree_leakage`
- `foreign_system_contamination`

These are related, but not identical, product risks.

## Phase I.1: Hebrew-Aware Signal Libraries

Signal libraries should be corpus-aware and grounded in the Hebrew material actually appearing in F2 runs.

### Native-safe markers

Examples:

- `תלמיד בונה`
- `דרגה ראשונה`
- `סינר לבן`
- `עור כבש`
- `חבל טקסי`
- `חדר הרהורים`
- `כיסוי העיניים`
- `ריסון`
- `משמעת`
- `מוסר`

### Weak framing markers

These do not justify escalation by themselves.

Examples:

- `ברמה הסימבולית`
- `במבט מחקרי`
- `במבט רחב יותר`
- `אפשר לראות`
- `דפוסי חניכה`

### Medium comparative markers

These may indicate mixedness when accumulated or when they follow a native core.

Examples:

- `במסורות אחרות`
- `בהשוואה ל`
- `לעומת`
- `מעבר לכך`
- `ברמה עמוקה יותר`

### Strong later-degree markers

These should strongly raise leakage risk.

Examples:

- `דרגה שביעית`
- `המילה האבודה`
- `חירם`
- `חירם אביף`
- `מות חירם`
- `ידע אבוד`
- `קשת מלכותית`
- `קשת חיה`
- `סודות הדרגה`

### Mixed / pivot phrases

These help identify movement inside the unit.

Examples:

- `אך`
- `אולם`
- `לעומת זאת`
- `בהמשך`
- `מכאן`
- `מעבר לכך`
- `לא רק ... אלא גם`

## Phase I.2: Pattern Scoring and Reason Codes

F2 should not rely on keyword presence alone.

It should detect:

- phrase patterns
- native-opening plus advanced-tail patterns
- cluster logic
- mixedness pivots
- heterogeneous signal composition

### Scoring model

Maintain two explicit local scores:

- `native_confidence_score`
- `foreign_risk_score`

Optionally retain subordinate local axes:

- `later_degree_risk_score`
- `foreign_system_risk_score`

The model must be asymmetric:

- strong foreign risk can dominate even if a native core exists
- native confidence can suppress unnecessary escalation only when strong leakage markers are absent
- mixedness is a separate handling path, not just a lower confidence score

## Reason-Code Architecture

Reason codes are required for observability and calibration.

### Native codes

- `native_core_detected`
- `native_symbolism_detected`
- `native_moral_frame_detected`
- `research_framing_only`

### Mixed codes

- `comparative_pivot_detected`
- `rank_hierarchy_detected`
- `native_then_advanced_tail`
- `heterogeneous_signal_mix`
- `context_truncated_after_native_core`

### Foreign codes

- `later_degree_marker_detected`
- `lost_word_cluster_detected`
- `hiram_cluster_detected`
- `explicit_degree_reference_detected`
- `secret_knowledge_cluster_detected`
- `foreign_system_marker_detected`

### Escalation codes

- `provider_due_to_strong_foreign_signal`
- `provider_due_to_unresolved_mixedness`
- `provider_due_to_context_loss`
- `provider_due_to_low_native_confidence`

These do not need to become public provider fields, but they must be available in row/debug metadata and aggregated in summary counts.

## Mixed Content Handling

Mixed units are not automatic foreign rejects.

Preferred handling order:

1. keep full when the pivot is weak and still safe
2. keep core / trim tail when deterministic
3. escalate only when the mixed boundary requires real semantic judgment

## Golden Set Evaluation

Calibration should be validated against a fixed manual set of 30-50 units labeled as:

- `native`
- `mixed`
- `foreign`

The evaluation must separately track:

- false positives on native content
- false negatives on foreign leakage
- mixed misclassification

This evaluation should start early, before broader pilot scaling, so calibration does not become smoke-driven guesswork.

## Output Expectations

F2 rows should expose local debug metadata such as:

- `heuristic_content_class`
- `heuristic_signal_strength`
- `reason_codes`
- `mixedness_reason_codes`
- `native_confidence_score`
- `foreign_risk_score`
- `later_degree_leakage_detected`
- `foreign_system_contamination_detected`

F2 summary should aggregate at least:

- `reason_code_counts`
- `mixedness_reason_code_counts`
- `mixedness_detected_count`
- `later_degree_leakage_detected_count`
- `foreign_system_contamination_detected_count`

## Recommended Execution Order

1. build Hebrew signal inventories from the corpus
2. add native / weak / medium / strong Hebrew families
3. add pivot and mixedness detection
4. split later-degree leakage from foreign-system contamination
5. add asymmetric scoring
6. add reason codes and summary counts
7. rerun a small smoke
8. compare against the prior Phase I smoke
9. build and run the golden-set evaluation pass
10. only then consider a medium pilot

## Definition of Done

Phase I.1-I.2 is complete only if:

- Hebrew-aware signal libraries are active in F2
- mixedness is actually detected in real runs
- advanced framing alone no longer causes routine escalation
- later-degree leakage still receives strict handling
- reason-code visibility exists in rows and summary counts
- `provider_invoked_units` drops meaningfully relative to the first Phase I smoke
- no material runtime regression appears
- manual review shows better separation between native, mixed, and foreign

## Summary

Phase I.1-I.2 is not about making Gemini smarter.

It is about making F2 heuristics sharper, more Hebrew-aware, more explainable, and more aligned with the product rule:

> serious ritual language is not automatically unsafe, but real later-degree leakage must still be blocked.
