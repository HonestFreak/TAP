"""`repetition_guard(window, threshold)` — halt when the model gets stuck
in a loop. Catches the most common token-padding failure mode (whitepaper
§5.3.5) without requiring an external entropy model."""

from __future__ import annotations

from collections import Counter

from tap.evaluators.base import Decision, Evaluator


def repetition_guard(*, window: int = 200, threshold: float = 0.4) -> Evaluator:
    """Halt when more than `threshold` of the last `window` characters are
    repetitions of a single short n-gram."""
    if window < 32:
        raise ValueError("window must be at least 32 characters")
    if not 0.0 < threshold <= 1.0:
        raise ValueError("threshold must be in (0.0, 1.0]")

    def _evaluate(accumulated: str) -> Decision:
        if len(accumulated) < window:
            return Decision.CONTINUE
        tail = accumulated[-window:]
        # Look for any 8-char substring that occupies more than `threshold`
        # of the tail. Cheap O(window) scan; no allocation per char.
        ngrams: Counter[str] = Counter()
        for i in range(len(tail) - 8):
            ngrams[tail[i : i + 8]] += 1
        if not ngrams:
            return Decision.CONTINUE
        _, count = ngrams.most_common(1)[0]
        # A non-repeating window has count ~ 1 per ngram; clamp at len/8 to
        # account for natural recurrence.
        if count / (window / 8) >= threshold:
            return Decision.HALT
        return Decision.CONTINUE

    _evaluate.name = "repetition_guard"  # type: ignore[attr-defined]
    return _evaluate  # type: ignore[return-value]
