"""x402 `X-PAYMENT-REQUIREMENTS` for the TAP `tap.v1.channel` scheme.

Producers publish a `PaymentRequirements` at session-open; consumers parse
it and verify that the producer's parameters meet their policy before
constructing the open-channel transaction (whitepaper §4.8).

The payload carries a per-prompt input quote (`input_token_count`,
`prepaid_input_micro`) alongside the per-token prices — see whitepaper §4.9.
The consumer SHOULD re-tokenize the prompt locally with `tokenizer_id` and
abort if the producer's count does not match (whitepaper §5.3.7)."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

from tap.exceptions import X402Error

SCHEME = "tap.v1.channel"


@dataclass(frozen=True, slots=True)
class PaymentRequirements:
    """Producer-published session terms.

    `network` follows x402's convention (`solana-mainnet`, `solana-devnet`).
    `asset` is the SPL mint the channel is denominated in (USDC).
    `recipient` is the program ID; the channel PDA is derived per-session
    by the consumer.

    Pricing is split per whitepaper §4.8. `input_price_micro` is charged
    once at channel open as `prepaid_input_micro` (= `input_token_count *
    input_price_micro`); `output_price_micro` is charged incrementally as
    output streams. The asymmetry reflects real-world LLM economics where
    output costs 3-5x as much as input."""

    scheme: str
    network: str
    asset: str
    recipient: str
    producer_pubkey: str
    input_price_micro: int
    output_price_micro: int
    max_unpaid_micro: int
    trailing_buffer_tokens: int
    duration_secs: int
    dispute_secs: int
    grace_ms: int
    pause_timeout_ms: int
    channel_open_url: str
    stream_url: str
    tokenizer_id: str
    # Per-prompt fields — present when the consumer submits the prompt as
    # part of discovery (whitepaper §4.9). For producers that advertise
    # generic terms without seeing a prompt yet, these are 0.
    input_token_count: int = 0
    prepaid_input_micro: int = 0
    model: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "scheme": self.scheme,
            "network": self.network,
            "asset": self.asset,
            "recipient": self.recipient,
            "extra": {
                "producer_pubkey": self.producer_pubkey,
                "input_price": self.input_price_micro,
                "output_price": self.output_price_micro,
                "tokenizer_id": self.tokenizer_id,
                "input_token_count": self.input_token_count,
                "prepaid_input": self.prepaid_input_micro,
                "max_unpaid": self.max_unpaid_micro,
                "trailing_buffer": self.trailing_buffer_tokens,
                "duration_secs": self.duration_secs,
                "dispute_secs": self.dispute_secs,
                "grace_ms": self.grace_ms,
                "pause_timeout_ms": self.pause_timeout_ms,
                "channel_open_url": self.channel_open_url,
                "stream_url": self.stream_url,
                "model": self.model,
            },
        }


def encode_requirements(req: PaymentRequirements) -> str:
    raw = json.dumps(req.to_payload(), separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def decode_requirements(header_value: str) -> PaymentRequirements:
    try:
        payload = json.loads(base64.b64decode(header_value, validate=True))
    except (ValueError, json.JSONDecodeError) as exc:
        raise X402Error("X-PAYMENT-REQUIREMENTS is not valid base64-JSON") from exc

    if payload.get("scheme") != SCHEME:
        raise X402Error(f"unsupported payment scheme {payload.get('scheme')!r}")
    extra = payload.get("extra") or {}

    try:
        return PaymentRequirements(
            scheme=payload["scheme"],
            network=payload["network"],
            asset=payload["asset"],
            recipient=payload["recipient"],
            producer_pubkey=extra["producer_pubkey"],
            input_price_micro=int(extra["input_price"]),
            output_price_micro=int(extra["output_price"]),
            tokenizer_id=str(extra["tokenizer_id"]),
            input_token_count=int(extra.get("input_token_count", 0)),
            prepaid_input_micro=int(extra.get("prepaid_input", 0)),
            max_unpaid_micro=int(extra["max_unpaid"]),
            trailing_buffer_tokens=int(extra["trailing_buffer"]),
            duration_secs=int(extra["duration_secs"]),
            dispute_secs=int(extra["dispute_secs"]),
            grace_ms=int(extra["grace_ms"]),
            pause_timeout_ms=int(extra["pause_timeout_ms"]),
            channel_open_url=str(extra["channel_open_url"]),
            stream_url=str(extra["stream_url"]),
            model=extra.get("model"),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise X402Error("X-PAYMENT-REQUIREMENTS is missing or malformed fields") from exc


__all__ = ["PaymentRequirements", "SCHEME", "encode_requirements", "decode_requirements"]
