---
title: Evaluators
sidebar_position: 4
---

# Evaluators

An evaluator is any callable from accumulated output to `Decision`:

```python
from tap.evaluators.base import Decision, Evaluator

def my_evaluator(text: str) -> Decision:
    return Decision.HALT if "forbidden" in text else Decision.CONTINUE
```

The session calls the evaluator after each token chunk; the first
`HALT` stops the session and force-signs a final commit.

`Decision` is a 2-value enum:

| Value | Meaning |
| --- | --- |
| `Decision.CONTINUE` | Keep streaming. |
| `Decision.HALT` | Stop the session and force-sign the final commit. |

## Built-in evaluators

### `json_schema(schema)`

Halts as soon as the streaming output cannot be extended into a valid
instance of the supplied JSON schema. Tolerates leading markdown
fences (` ```json `) and a 32-character warm-up window so partial
preambles don't trip the syntactic gate.

If `jsonschema` is installed, full Draft-2020-12 validation runs once
the buffer parses; otherwise the check degrades to syntax-only.

```python
evaluators.json_schema({
    "type": "object",
    "required": ["title"],
    "properties": {"title": {"type": "string"}},
})
```

### `length_cap(max_chars)`

Halts when accumulated output reaches `max_chars`. Raises `ValueError`
if `max_chars <= 0`. The `name` reports as `length_cap(<n>)` so
`session.halted_by` shows the bound.

### `topic_drift(reference, *, threshold=0.05, min_chars=200, scorer=None)`

Halts when `scorer(reference, accumulated)` falls below `threshold`.
Default `scorer` is a cheap token-overlap heuristic; pass your own
for embedding-based scoring. `min_chars` avoids halting on very short
prefixes where the score is noisy.

### `repetition_guard(*, window=200, threshold=0.4)`

Halts when more than `threshold` of the last `window` characters are
covered by a single 8-char n-gram — the most common token-padding
failure mode (whitepaper §5.3.5). Window must be ≥ 32 characters;
threshold must be in `(0.0, 1.0]`.

### `content_policy(banned)`

Halts on a substring or compiled regex match. Plain strings are
matched case-insensitively; pre-compiled `re.Pattern`s use their own
flags.

```python
import re
evaluators.content_policy([
    "API_KEY",
    re.compile(r"\b[A-Z0-9]{32,}\b"),  # candidate secret
])
```

## Composing evaluators

`evaluators.compose(*evaluators)` ORs them together — the first to
return `HALT` wins. The composed evaluator's `name` is
`"compose(<inner names>)"`, so `session.halted_by` still surfaces
which inner check fired.

```python
evaluator = evaluators.compose(
    evaluators.json_schema(EXPECTED_SCHEMA),
    evaluators.length_cap(2_000),
    evaluators.repetition_guard(),
)
```

Pass the composed evaluator to `consumer.open_session(evaluator=...)`.

## Writing custom evaluators

Any callable conforming to `Evaluator = Callable[[str], Decision]`
works:

```python
class TopicGuard:
    name = "topic_guard"  # surfaces in session.halted_by
    def __init__(self, allowed_topics: set[str]):
        self.allowed = allowed_topics

    def __call__(self, accumulated: str) -> Decision:
        # ... inspect text, return CONTINUE or HALT
        return Decision.CONTINUE
```

Set `.name` on the callable so `session.halted_by` reports a
meaningful value instead of a generic `"evaluator"`.

## Latency considerations

The evaluator runs after every token. Heavy per-token work — calls
to a remote API, expensive parsing — will starve the streaming loop.
Rule of thumb: evaluators should complete in **under 5ms** at the
median.

For evaluators that *must* be expensive (a classifier model, for
example), accumulate output and run the check every K tokens
internally:

```python
def heavy_evaluator():
    counter = {"i": 0}
    def _(text: str):
        counter["i"] += 1
        if counter["i"] % 50 != 0:
            return Decision.CONTINUE
        return run_classifier(text)
    return _
```
