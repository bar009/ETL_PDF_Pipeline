"""Schema-facing helpers owned by the prod pipeline surface."""

from PDF_handle.prod.schema.data import (
    normalize_degree_data,
    normalize_entry,
    normalize_nullable_string,
    normalize_string_array,
    normalize_text,
    refresh_degree_indexes,
    serialize_degree_data,
    serialize_entry,
    unique_links,
    unique_strings,
    validate_against_schema,
    validate_degree_references,
)
from PDF_handle.prod.schema.patches import (
    APPEND_MARKER_PREFIX,
    STAGED_LIBRARY_CATEGORY_ENTRY_SLUG,
    STAGED_LIBRARY_CATEGORY_ID,
    apply_degree_patches,
    build_cross_degree_link,
    build_degree_patch_operation,
    build_source_note,
)
from PDF_handle.prod.schema.overrides import (
    OVERRIDE_SCHEMA_VERSION,
    OVERRIDE_STATUSES,
    OVERRIDABLE_FIELDS,
    REVIEWABLE_OVERRIDE_STATUSES,
    REVIEW_ACTIONS,
    apply_active_overrides,
    apply_override_review_decisions,
    build_override_review_template,
    empty_override_bundle,
    extract_override_bundle_from_diff,
    load_override_bundle,
    normalize_override_bundle,
    reconstruct_governance_base_from_effective_datasets,
    reconstruct_base_context_from_overrides,
    resolve_override_bundle,
    validate_override_bundle,
)
