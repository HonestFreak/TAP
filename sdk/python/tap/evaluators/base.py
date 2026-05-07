"""Evaluator protocol and `Decision` enum.

Evaluators are stateless from the framework's perspective: every call gets
the full accumulated output. This is intentional — it lets evaluators be
pure functions, makes them trivial to compose, and avoids making the
session loop responsible for evaluator state."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class Decision(Enum):
    CONTINUE = "continue"
    HALT = "halt"


@dataclass(frozen=True, slots=True)
class HaltReason:
    """Description of why an evaluator decided to halt. Surfaced in
    settlement logs and on the demo dashboard."""

    evaluator: str
    detail: str


class Evaluator(Protocol):
    """Callable that inspects the accumulated output stream and returns a
    `Decision`. Evaluators MUST be cheap — they run inside the per-token
    hot path."""

    name: str

    def __call__(self, accumulated: str) -> Decision: ...
