"""Pluggable consumer-side quality evaluators (whitepaper §4.4).

An evaluator is any callable from accumulated output to `Decision`. The
session runs them concurrently with token consumption; the first one to
return `HALT` ends the session.

Re-exporting the common evaluators here lets callers write
`from tap import evaluators; evaluators.json_schema(...)` without learning
the package layout."""

from tap.evaluators.base import Decision, Evaluator
from tap.evaluators.compose import compose
from tap.evaluators.content_policy import content_policy
from tap.evaluators.json_schema import json_schema
from tap.evaluators.length_cap import length_cap
from tap.evaluators.repetition import repetition_guard
from tap.evaluators.topic_drift import topic_drift

__all__ = [
    "Decision",
    "Evaluator",
    "compose",
    "content_policy",
    "json_schema",
    "length_cap",
    "repetition_guard",
    "topic_drift",
]
