"""`content_policy(banned)` — halt on disallowed content.

`banned` is an iterable of substrings or compiled regex patterns; matching
is case-insensitive for plain strings and uses the pattern's flags for
regexes. Useful for compliance-sensitive workflows where the consumer
needs to stop a generation that drifts into PII, profanity, or
copyright-flagged content."""

from __future__ import annotations

import re
from typing import Iterable

from tap.evaluators.base import Decision, Evaluator

Pattern = str | re.Pattern[str]


def content_policy(banned: Iterable[Pattern]) -> Evaluator:
    compiled: list[re.Pattern[str]] = []
    for item in banned:
        if isinstance(item, re.Pattern):
            compiled.append(item)
        else:
            compiled.append(re.compile(re.escape(item), re.IGNORECASE))
    if not compiled:
        raise ValueError("content_policy requires at least one pattern")

    def _evaluate(accumulated: str) -> Decision:
        for pat in compiled:
            if pat.search(accumulated):
                return Decision.HALT
        return Decision.CONTINUE

    _evaluate.name = "content_policy"  # type: ignore[attr-defined]
    return _evaluate  # type: ignore[return-value]
