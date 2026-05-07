"""Anthropic Messages API adapter.

Wraps the `messages.stream` SSE flow into a uniform `AsyncIterator[str]`
of token deltas. Defaults to Claude Sonnet 4.6 — the latest production
model at the time of writing — but accepts an override via `model`."""

from __future__ import annotations

from typing import Any, AsyncIterator

DEFAULT_MODEL = "claude-sonnet-4-6"


async def stream_anthropic(
    body: dict[str, Any],
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1024,
) -> AsyncIterator[str]:
    """Yield text deltas from Anthropic's streaming Messages API.

    `body` is forwarded verbatim except that `model` and `max_tokens`
    defaults are applied if absent."""
    try:
        from anthropic import AsyncAnthropic
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Anthropic adapter requires `pip install tap-protocol[anthropic]`"
        ) from exc

    client = AsyncAnthropic()
    body = {"model": model, "max_tokens": max_tokens, **body}

    async with client.messages.stream(**body) as stream:
        async for chunk in stream.text_stream:
            yield chunk
