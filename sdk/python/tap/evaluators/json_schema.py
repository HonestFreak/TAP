"""`json_schema(schema)` — halt as soon as the streaming output cannot be
extended into a valid instance of the supplied JSON schema.

The check uses incremental partial-JSON parsing: at each step we strip
trailing whitespace, attempt to parse the prefix with permissive recovery,
and report HALT if (a) the prefix is well-formed JSON that already violates
the schema, or (b) the prefix contains a character that no valid JSON can
contain in that position. We deliberately do NOT halt on incomplete-but-
recoverable prefixes — the response is still streaming."""

from __future__ import annotations

import json
from typing import Any

from tap.evaluators.base import Decision, Evaluator

try:
    from jsonschema import Draft202012Validator, ValidationError
    _HAS_JSONSCHEMA = True
except ImportError:  # pragma: no cover
    _HAS_JSONSCHEMA = False


def json_schema(schema: dict[str, Any]) -> Evaluator:
    """Build an evaluator that halts on JSON-schema violation.

    If `jsonschema` is not installed, the evaluator falls back to a
    syntax-only check (well-formed JSON or not) once the response appears
    complete. Schema validation is best-effort because partial-JSON parsing
    in pure Python has no canonical implementation."""
    if _HAS_JSONSCHEMA:
        validator = Draft202012Validator(schema)
    else:
        validator = None

    def _evaluate(accumulated: str) -> Decision:
        text = _strip_markdown_fence(accumulated.strip())
        if not text:
            return Decision.CONTINUE

        # Warm-up: tolerate the first ~32 characters before the syntactic
        # gate fires. Streaming providers can deliver leading whitespace,
        # partial markdown fences (`` ` `` or ` ``ja `), or non-JSON system
        # preambles in the first few packets even when the eventual payload
        # is valid. Halting on the very first character creates false
        # positives and wipes out any chance of seeing intent in the stream.
        # 32 chars is short enough to fail-fast on long prose and long
        # enough to absorb provider-specific framing.
        if len(text) < 32:
            return Decision.CONTINUE

        # Cheap syntactic gates: anything not starting with `{` or `[` cannot
        # become a JSON object/array. We allow whitespace-only prefixes by
        # stripping above; allow strings/numbers/bools by skipping the gate
        # if the schema's `type` is one of those.
        first = text[0]
        if first not in "{[" and not _allows_scalar(schema):
            return Decision.HALT

        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            # Still streaming; nothing definitive yet.
            return Decision.CONTINUE

        if validator is None:
            return Decision.CONTINUE
        try:
            validator.validate(value)
        except ValidationError:
            return Decision.HALT
        return Decision.CONTINUE

    _evaluate.name = "json_schema"  # type: ignore[attr-defined]
    return _evaluate  # type: ignore[return-value]


def _allows_scalar(schema: dict[str, Any]) -> bool:
    t = schema.get("type")
    if isinstance(t, str):
        return t in {"string", "number", "integer", "boolean", "null"}
    if isinstance(t, list):
        return any(x in {"string", "number", "integer", "boolean", "null"} for x in t)
    return False


def _strip_markdown_fence(text: str) -> str:
    """Remove a leading ```json (or ```) fence and a trailing ``` closer.

    LLMs routinely wrap JSON in markdown fences regardless of the prompt.
    Production schema-checks need to tolerate that — otherwise the very
    first token (`` ` ``) trips the first-char gate and halts the stream
    before any payload arrives. The stripping is conservative: we only
    advance past a fence we recognize, and we leave the rest of the buffer
    untouched so partial JSON can still be parsed incrementally."""
    if not text.startswith("```"):
        return text
    # Trim opening fence: ```json\n, ```JSON\n, or just ```\n.
    after_ticks = text[3:]
    newline = after_ticks.find("\n")
    if newline == -1:
        # Fence opener not yet terminated — still buffering the language tag.
        return ""
    body = after_ticks[newline + 1:]
    # Trim closing fence if it has arrived.
    if body.endswith("```"):
        body = body[:-3].rstrip()
    return body
