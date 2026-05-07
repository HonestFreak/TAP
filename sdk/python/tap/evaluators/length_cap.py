"""`length_cap(max_chars)` — halt when output exceeds a length budget.

Useful for capping spend on responses where the consumer has a hard size
limit (e.g. UI rendering width, downstream parser limit) regardless of
whether the model intends to keep generating."""

from __future__ import annotations

from tap.evaluators.base import Decision, Evaluator


def length_cap(max_chars: int) -> Evaluator:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")

    def _evaluate(accumulated: str) -> Decision:
        return Decision.HALT if len(accumulated) >= max_chars else Decision.CONTINUE

    _evaluate.name = f"length_cap({max_chars})"  # type: ignore[attr-defined]
    return _evaluate  # type: ignore[return-value]
