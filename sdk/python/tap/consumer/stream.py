"""SSE consumer for the producer's response stream.

Producers emit one event per token (or token batch) — see whitepaper
Appendix B.3. This module is the only place in the SDK that knows about
SSE; the rest of the consumer treats tokens as a plain async iterator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import AsyncIterator

import httpx

from tap.exceptions import ProtocolError


@dataclass(frozen=True, slots=True)
class StreamEvent:
    """One SSE event from the producer. `text` is the model token; `ack` is
    the latest commitment sequence the producer has registered (see
    whitepaper §B.3)."""

    text: str
    ack_sequence: int | None
    finished: bool


async def iter_sse(response: httpx.Response) -> AsyncIterator[StreamEvent]:
    """Parse `response.aiter_lines()` as SSE and yield `StreamEvent`s.

    Producers emit JSON `data:` payloads; we tolerate blank-line keepalives
    and `event:` headers but ignore the latter — the only event type the
    protocol uses is the default `message`."""
    async for line in response.aiter_lines():
        if not line:
            continue
        if line.startswith(":") or line.startswith("event:"):
            continue
        if not line.startswith("data:"):
            raise ProtocolError(f"unexpected SSE line: {line[:80]!r}")

        payload = line[len("data:") :].strip()
        if payload == "[DONE]":
            yield StreamEvent(text="", ack_sequence=None, finished=True)
            return

        try:
            obj = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ProtocolError("SSE data is not valid JSON") from exc

        # Producer emits `{"error": "..."}` when an upstream model adapter
        # fails mid-stream; surface it as an exception so the consumer's
        # session can settle on whatever it has paid for so far.
        if "error" in obj:
            raise ProtocolError(f"producer error: {obj['error']}")

        yield StreamEvent(
            text=str(obj.get("text", "")),
            ack_sequence=int(obj["ack"]) if obj.get("ack") is not None else None,
            finished=bool(obj.get("finished", False)),
        )
