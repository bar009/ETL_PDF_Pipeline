"""The review workflow boundary (systemic plan WS9).

Staged content moves through explicit states; "the AI suggested it" and "it
entered the canon" are never the same thing:

    suggested -> reviewed -> approved -> published
        \\            \\           \\
         +-> rejected  +-> rejected +-> rejected

- new staged operations are stamped ``suggested`` at creation time
- only ``approved`` operations may cross the staging→runtime door
- ``published`` is set by the release flow after a merge lands
- ``rejected`` is terminal

``assert_operations_approved`` is the door. Operations written before this
field existed carry no ``review_state``; callers must opt in to merging them
with ``allow_unreviewed_legacy=True``, which returns warnings instead of
silently passing.
"""

from __future__ import annotations

from typing import Any

REVIEW_STATE_FIELD = "review_state"
INITIAL_REVIEW_STATE = "suggested"
MERGEABLE_REVIEW_STATE = "approved"

REVIEW_STATES = ("suggested", "reviewed", "approved", "published", "rejected")

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "suggested": frozenset({"reviewed", "rejected"}),
    "reviewed": frozenset({"approved", "rejected"}),
    "approved": frozenset({"published", "rejected"}),
    "published": frozenset(),
    "rejected": frozenset(),
}


class ReviewBoundaryError(RuntimeError):
    """Raised when staged content tries to cross a boundary it has not earned."""


def is_valid_state(state: Any) -> bool:
    return state in REVIEW_STATES


def validate_transition(current: str, target: str) -> None:
    if not is_valid_state(current):
        raise ReviewBoundaryError(f"Unknown review state: {current!r}")
    if not is_valid_state(target):
        raise ReviewBoundaryError(f"Unknown review state: {target!r}")
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ReviewBoundaryError(
            f"Illegal review transition {current} -> {target}; "
            f"allowed from {current}: {sorted(ALLOWED_TRANSITIONS[current]) or 'none (terminal)'}"
        )


def transition(operation: dict[str, Any], target: str) -> dict[str, Any]:
    current = operation.get(REVIEW_STATE_FIELD, INITIAL_REVIEW_STATE)
    validate_transition(current, target)
    operation[REVIEW_STATE_FIELD] = target
    return operation


def assert_operations_approved(
    operations: list[dict[str, Any]],
    *,
    allow_unreviewed_legacy: bool = False,
) -> list[str]:
    """The staging→runtime door: every operation must be explicitly approved.

    Returns warnings (legacy operations admitted under the explicit flag).
    Raises ReviewBoundaryError when any operation is not mergeable.
    """
    warnings: list[str] = []
    blocked: list[str] = []

    for operation in operations:
        label = str(operation.get("slug") or operation.get("marker_id") or "<unlabeled>")
        state = operation.get(REVIEW_STATE_FIELD)

        if state == MERGEABLE_REVIEW_STATE:
            continue
        if state is None:
            if allow_unreviewed_legacy:
                warnings.append(f"{label}: legacy operation without review_state admitted explicitly")
                continue
            blocked.append(f"{label}: missing review_state (legacy data needs allow_unreviewed_legacy)")
            continue
        if not is_valid_state(state):
            blocked.append(f"{label}: unknown review_state {state!r}")
            continue
        blocked.append(f"{label}: review_state is {state!r}, only '{MERGEABLE_REVIEW_STATE}' may merge")

    if blocked:
        raise ReviewBoundaryError(
            "Staged operations blocked at the staging→runtime boundary:\n- " + "\n- ".join(blocked)
        )
    return warnings
