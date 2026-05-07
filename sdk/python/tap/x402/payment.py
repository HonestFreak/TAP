"""x402 `X-PAYMENT` payload for opening a TAP channel.

The payload carries the parameters the server needs to know about the
session even before the channel-open transaction is observed on-chain
(session key, deposit, agreed prices, prepaid input floor, nonce). The
actual transaction is base64-encoded so x402 facilitators can submit it
verbatim."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

from tap.exceptions import X402Error


@dataclass(frozen=True, slots=True)
class OpenChannelPayment:
    """Consumer-side x402 payment payload for `tap.v1.channel`."""

    scheme: str
    network: str
    consumer_pubkey: str
    session_key: str
    nonce: int
    deposit_micro: int
    input_price_micro: int
    output_price_micro: int
    prepaid_input_micro: int
    duration_secs: int
    dispute_secs: int
    trailing_buffer_tokens: int
    transaction_b64: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "scheme": self.scheme,
            "network": self.network,
            "extra": {
                "consumer_pubkey": self.consumer_pubkey,
                "session_key": self.session_key,
                "nonce": self.nonce,
                "deposit_micro": self.deposit_micro,
                "input_price_micro": self.input_price_micro,
                "output_price_micro": self.output_price_micro,
                "prepaid_input_micro": self.prepaid_input_micro,
                "duration_secs": self.duration_secs,
                "dispute_secs": self.dispute_secs,
                "trailing_buffer_tokens": self.trailing_buffer_tokens,
                "transaction": self.transaction_b64,
            },
        }


def encode_payment(payment: OpenChannelPayment) -> str:
    raw = json.dumps(payment.to_payload(), separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def decode_payment(header_value: str) -> OpenChannelPayment:
    try:
        payload = json.loads(base64.b64decode(header_value, validate=True))
    except (ValueError, json.JSONDecodeError) as exc:
        raise X402Error("X-PAYMENT is not valid base64-JSON") from exc

    extra = payload.get("extra") or {}
    try:
        return OpenChannelPayment(
            scheme=payload["scheme"],
            network=payload["network"],
            consumer_pubkey=extra["consumer_pubkey"],
            session_key=extra["session_key"],
            nonce=int(extra["nonce"]),
            deposit_micro=int(extra["deposit_micro"]),
            input_price_micro=int(extra["input_price_micro"]),
            output_price_micro=int(extra["output_price_micro"]),
            prepaid_input_micro=int(extra["prepaid_input_micro"]),
            duration_secs=int(extra["duration_secs"]),
            dispute_secs=int(extra["dispute_secs"]),
            trailing_buffer_tokens=int(extra["trailing_buffer_tokens"]),
            transaction_b64=str(extra["transaction"]),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise X402Error("X-PAYMENT payload is missing or malformed fields") from exc
