"""`topic_drift(reference, threshold)` — halt when the output drifts away
from the reference topic.

The default scoring uses a token-overlap heuristic: cheap, no external
dependencies, suitable for the per-token hot path. For higher-quality
detection, callers can pass a custom `scorer` that wraps an embedding
model. The framework only requires that the scorer return a value in
[0.0, 1.0] where higher means "more on topic"."""

from __future__ import annotations

import re
from collections import Counter
from typing import Callable

from tap.evaluators.base import Decision, Evaluator

Scorer = Callable[[str, str], float]

_TOKEN_RE = re.compile(r"[A-Za-z0-9']+")


def _overlap_score(reference: str, accumulated: str) -> float:
    ref = Counter(_TOKEN_RE.findall(reference.lower()))
    acc = Counter(_TOKEN_RE.findall(accumulated.lower()))
    if not ref or not acc:
        return 1.0
    overlap = sum((ref & acc).values())
    return overlap / max(sum(acc.values()), 1)


def topic_drift(
    reference: str,
    *,
    threshold: float = 0.05,
    min_chars: int = 200,
    scorer: Scorer | None = None,
) -> Evaluator:
    """Halt when `scorer(reference, accumulated)` falls below `threshold`.

    `min_chars` prevents premature halts on very short prefixes where the
    scorer is unreliable."""
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0.0, 1.0]")
    score = scorer or _overlap_score

    def _evaluate(accumulated: str) -> Decision:
        if len(accumulated) < min_chars:
            return Decision.CONTINUE
        return Decision.HALT if score(reference, accumulated) < threshold else Decision.CONTINUE

    _evaluate.name = "topic_drift"  # type: ignore[attr-defined]
    return _evaluate  # type: ignore[return-value]
