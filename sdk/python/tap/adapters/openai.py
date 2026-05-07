"""OpenAI Chat Completions adapter."""

from __future__ import annotations

from typing import Any, AsyncIterator


async def stream_openai(
    body: dict[str, Any],
    *,
    model: str = "gpt-4o-mini",
) -> AsyncIterator[str]:
    """Yield content deltas from OpenAI's streaming Chat Completions API."""
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "OpenAI adapter requires `pip install tap-protocol[openai]`"
        ) from exc

    client = AsyncOpenAI()
    body = {"model": model, "stream": True, **body}

    response = await client.chat.completions.create(**body)
    async for chunk in response:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta
