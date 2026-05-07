"""Tokenizer registry for prompt-token counting (whitepaper §4.9).

The producer's 402 response declares which tokenizer it uses to count
input tokens; the consumer SHOULD re-tokenize the prompt locally with the
same identifier to detect inflation (whitepaper §5.3.7). Tokenizers are
deterministic, so honest disagreement is impossible — any mismatch implies
misbehaviour and is a signal to abort before any payment flows.

The registry is intentionally minimal: registering a tokenizer is a one-line
call from the producer/consumer SDKs at startup. Production deployments
plug in `tiktoken` for OpenAI/Anthropic models or the model vendor's own
SDK; the reference implementation ships a single deterministic
whitespace-and-punctuation tokenizer (`tap.tok.v1`) so the demo runs
without an extra dependency."""

from __future__ import annotations

import re
from typing import Callable, Dict

Tokenizer = Callable[[str], int]
"""A deterministic function from prompt text to token count."""

_REGISTRY: Dict[str, Tokenizer] = {}


def register(name: str, tokenizer: Tokenizer) -> None:
    """Register a tokenizer under `name`. Re-registering an existing name
    overwrites the prior entry, matching how vendor SDKs are typically wired
    in at process start."""
    _REGISTRY[name] = tokenizer


def count(name: str, text: str) -> int:
    """Count tokens in `text` using the tokenizer identified by `name`.

    Raises `KeyError` if the tokenizer is not registered — the consumer
    treats this as a non-recoverable mismatch and aborts the channel-open."""
    if name not in _REGISTRY:
        raise KeyError(f"unknown tokenizer {name!r}; register it before discovery")
    return _REGISTRY[name](text)


def is_registered(name: str) -> bool:
    return name in _REGISTRY


# ---------------------------------------------------------------------------
# Default tokenizer: deterministic, dependency-free, and good enough for
# demos. Real model providers register their own tokenizer at startup.
# ---------------------------------------------------------------------------

_TAP_V1_TOKEN_RE = re.compile(r"\w+|[^\w\s]")


def _tap_v1(text: str) -> int:
    """Whitespace-and-punctuation split. Stable across runs and platforms;
    will produce different counts than `cl100k_base` or vendor tokenizers,
    but that's the point — `tap.tok.v1` is a known identifier the consumer
    can run locally without any external library."""
    if not text:
        return 0
    return len(_TAP_V1_TOKEN_RE.findall(text))


register("tap.tok.v1", _tap_v1)


__all__ = ["Tokenizer", "count", "is_registered", "register"]
