"""SSE encoder for producer responses (whitepaper Appendix B.3).

One event per token (or token batch). Each event carries the token text
and the latest commitment ack so the consumer can confirm the producer
has registered its progress.

We keep this in a separate file from `wrap_stream` so the wire shape is
self-contained — swapping SSE for chunked-JSON or binary framing is a
single-file change."""

from __future__ import annotations

import json
from typing import AsyncIterator


async def encode_sse(
    chunks: AsyncIterator[tuple[str, int]],
) -> AsyncIterator[str]:
    """Convert `(token, ack_sequence)` pairs into SSE `data:` lines."""
    async for token, ack in chunks:
        payload = json.dumps({"text": token, "ack": ack}, separators=(",", ":"))
        yield f"data: {payload}\n\n"
    # Sentinel; consumer iterates until DONE arrives or the connection closes.
    yield "data: [DONE]\n\n"
