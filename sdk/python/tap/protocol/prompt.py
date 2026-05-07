"""Deterministic prompt-text extraction.

Producer and consumer must agree on the exact text fed to the tokenizer at
session open (whitepaper §4.9 / §5.3.7). Putting the extraction here gives
both sides a single source of truth and avoids the consumer reaching into
the producer module just to call a static helper.

Accepts the common chat-completion shape `{"messages": [{"role": ..., "content": ...}]}`
and a plain `{"prompt": "..."}` fallback. Unrecognized shapes fall back to a
stable JSON serialization so the count remains deterministic instead of
crashing."""

from __future__ import annotations

import json
from typing import Any


def extract_prompt_text(body: dict[str, Any]) -> str:
    if "messages" in body and isinstance(body["messages"], list):
        return "\n".join(
            msg.get("content", "")
            for msg in body["messages"]
            if isinstance(msg, dict) and isinstance(msg.get("content"), str)
        )
    if isinstance(body.get("prompt"), str):
        return body["prompt"]
    return json.dumps(body, sort_keys=True, separators=(",", ":"))
