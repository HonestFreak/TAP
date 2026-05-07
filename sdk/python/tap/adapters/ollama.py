"""Ollama (local Llama-family) adapter.

Useful for running the demo end-to-end without external API keys, or for
testing the protocol layer against a controllable local server."""

from __future__ import annotations

from typing import Any, AsyncIterator


async def stream_ollama(
    body: dict[str, Any],
    *,
    model: str = "llama3.2",
    host: str = "http://localhost:11434",
) -> AsyncIterator[str]:
    """Yield content deltas from a local Ollama server."""
    try:
        from ollama import AsyncClient
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Ollama adapter requires `pip install tap-protocol[ollama]`"
        ) from exc

    client = AsyncClient(host=host)
    body = {"model": model, "stream": True, **body}

    async for chunk in await client.chat(**body):
        message = chunk.get("message") if isinstance(chunk, dict) else None
        if message and message.get("content"):
            yield message["content"]
