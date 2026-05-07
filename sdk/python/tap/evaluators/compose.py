"""`compose(*evaluators)` — short-circuit OR over a list of evaluators.

Returned evaluator halts as soon as any constituent halts; otherwise
returns CONTINUE. Order matters only for performance — put cheap
evaluators first to short-circuit on common cases."""

from __future__ import annotations

from tap.evaluators.base import Decision, Evaluator


def compose(*evaluators: Evaluator) -> Evaluator:
    if not evaluators:
        raise ValueError("compose requires at least one evaluator")

    names = ",".join(getattr(e, "name", "anonymous") for e in evaluators)

    def _evaluate(accumulated: str) -> Decision:
        for evaluator in evaluators:
            if evaluator(accumulated) is Decision.HALT:
                return Decision.HALT
        return Decision.CONTINUE

    _evaluate.name = f"compose({names})"  # type: ignore[attr-defined]
    return _evaluate  # type: ignore[return-value]
