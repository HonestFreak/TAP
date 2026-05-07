"""Producer discovery via x402.

Two flows exist (whitepaper §4.9):

* `discover_generic` does an unauthenticated GET. The producer returns generic
  terms (zero `input_token_count` / `prepaid_input`); the consumer can audit
  pricing/policy parameters but must POST a prompt before opening a channel.

* `discover_with_prompt` POSTs the prompt body without payment. The producer
  tokenizes the prompt with its declared tokenizer and returns
  `input_token_count` / `prepaid_input` bound to that exact prompt. The
  consumer verifies the count locally before opening the channel.

This is the only HTTP call in the consumer SDK that happens before any
funds are committed; everything that follows assumes the requirements have
been audited against consumer policy."""

from __future__ import annotations

import json
from typing import Any

import httpx

from tap.exceptions import X402Error
from tap.x402.headers import HEADER_PAYMENT_REQUIREMENTS
from tap.x402.requirements import PaymentRequirements, decode_requirements


async def discover_generic(
    producer_url: str, *, http: httpx.AsyncClient | None = None
) -> PaymentRequirements:
    """Issue an unauthenticated GET to `producer_url` and return the parsed
    `PaymentRequirements` with generic (no-prompt) terms."""
    own_client = http is None
    client = http or httpx.AsyncClient(timeout=10.0)
    try:
        resp = await client.get(producer_url)
    finally:
        if own_client:
            await client.aclose()
    return _parse_402(resp, producer_url)


async def discover_with_prompt(
    producer_url: str,
    body: dict[str, Any],
    *,
    http: httpx.AsyncClient | None = None,
) -> PaymentRequirements:
    """POST `body` (no payment) and return the prompt-bound `PaymentRequirements`.

    This is the whitepaper §4.9 step 2 quote. The producer tokenizes the
    prompt and returns `input_token_count` / `prepaid_input_micro` bound to
    this exact body. Caller MUST run `ConsumerPolicy.verify_prompt_tokens`
    against the same body before opening the channel."""
    own_client = http is None
    client = http or httpx.AsyncClient(timeout=10.0)
    try:
        resp = await client.post(
            producer_url,
            content=json.dumps(body, separators=(",", ":")),
            headers={"Content-Type": "application/json"},
        )
    finally:
        if own_client:
            await client.aclose()
    return _parse_402(resp, producer_url)


def _parse_402(resp: httpx.Response, producer_url: str) -> PaymentRequirements:
    if resp.status_code != 402:
        raise X402Error(
            f"expected HTTP 402 from {producer_url}, got {resp.status_code}"
        )
    header = resp.headers.get(HEADER_PAYMENT_REQUIREMENTS)
    if not header:
        raise X402Error(f"{HEADER_PAYMENT_REQUIREMENTS} missing from 402 response")
    return decode_requirements(header)


# Backwards-compatible alias for callers that just need the generic flow.
discover = discover_generic
