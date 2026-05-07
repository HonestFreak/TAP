"""Google Gemini adapter.

Wraps the Generative Language `streamGenerateContent` REST endpoint into a
uniform `AsyncIterator[str]` of token deltas. Defaults to `gemini-2.5-flash`
with `gemini-2.5-flash-lite` as a transient-failure fallback.

We talk to the REST API directly with httpx + SSE rather than via
`google-genai.aio.models.generate_content_stream` because that path packs
multiple JSON objects into a single read chunk and then fails its own
`json.loads` (raises `JSONDecodeError: Extra data`). With `alt=sse` Google
returns one well-formed `data:` frame per chunk and httpx's `aiter_lines`
gives us one frame at a time.

Retry policy: free-tier Gemini routinely returns 503 / 429 mid-day. We
retry the *open* call (before any tokens have been emitted) up to a few
times with backoff; once tokens start flowing we propagate any failure to
the caller so the producer can surface it as a clean SSE error frame
rather than dropping the chunked-encoded body.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, AsyncIterator

import httpx

DEFAULT_MODEL = "gemini-2.5-flash"
FALLBACK_MODEL = "gemini-2.5-flash-lite"
API_HOST = "https://generativelanguage.googleapis.com"
TRANSIENT_STATUSES = {429, 500, 502, 503, 504}
MAX_OPEN_ATTEMPTS = 3


def _to_gemini_contents(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Translate Anthropic-style `messages` into Gemini `contents`.

    Gemini uses `role: "user" | "model"` (no `assistant`) and wraps text in
    `parts: [{text: ...}]`. We map `assistant` → `model` and pass everything
    else through as `user`."""
    contents: list[dict[str, Any]] = []
    for m in messages:
        role = "model" if m.get("role") == "assistant" else "user"
        text = m["content"] if isinstance(m["content"], str) else str(m["content"])
        contents.append({"role": role, "parts": [{"text": text}]})
    return contents


def _extract_text(payload: dict[str, Any]) -> str:
    """Drill into a single Gemini stream chunk and concatenate all text parts."""
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts if "text" in p)


def _split_chunk(text: str, max_chunk_chars: int = 8) -> list[str]:
    """Re-chunk a Gemini delta into ~word-sized pieces.

    Gemini buffers short responses into one large chunk. The TAP demo bills
    one micro-price per delta, so we split on whitespace boundaries to make
    metering and the streaming UI feel granular without changing the
    rendered text. Long words are not broken — only inter-word splits."""
    if len(text) <= max_chunk_chars:
        return [text]
    pieces: list[str] = []
    current = ""
    for word in text.split(" "):
        prospective = (current + " " + word) if current else word
        if len(prospective) > max_chunk_chars and current:
            pieces.append(current + " ")
            current = word
        else:
            current = prospective
    if current:
        pieces.append(current)
    return pieces


async def stream_gemini(
    body: dict[str, Any],
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1024,
    fallback_model: str | None = FALLBACK_MODEL,
) -> AsyncIterator[str]:
    """Yield text deltas from Gemini's streamGenerateContent endpoint."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) is required")

    request_body = {
        "contents": _to_gemini_contents(body.get("messages", [])),
        "generationConfig": {"maxOutputTokens": body.get("max_tokens", max_tokens)},
    }

    attempts: list[str] = [model]
    if fallback_model and fallback_model != model:
        attempts.append(fallback_model)

    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=120.0) as client:
        for which in attempts:
            for attempt in range(MAX_OPEN_ATTEMPTS):
                url = f"{API_HOST}/v1beta/models/{which}:streamGenerateContent"
                try:
                    async with client.stream(
                        "POST",
                        url,
                        params={"alt": "sse", "key": api_key},
                        json=request_body,
                        headers={"Accept": "text/event-stream"},
                    ) as response:
                        if response.status_code in TRANSIENT_STATUSES:
                            await response.aread()
                            last_error = httpx.HTTPStatusError(
                                f"transient {response.status_code} on {which}",
                                request=response.request,
                                response=response,
                            )
                            await asyncio.sleep(0.5 * (attempt + 1))
                            continue
                        response.raise_for_status()
                        async for piece in _consume_sse(response):
                            yield piece
                        return
                except httpx.HTTPStatusError as exc:
                    last_error = exc
                    if exc.response.status_code in TRANSIENT_STATUSES:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    raise
    if last_error is not None:
        raise last_error


async def _consume_sse(response: httpx.Response) -> AsyncIterator[str]:
    """Drive `aiter_lines`, parse each `data:` frame, and yield text pieces."""
    async for line in response.aiter_lines():
        if not line or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        text = _extract_text(payload)
        if not text:
            continue
        for piece in _split_chunk(text):
            yield piece
