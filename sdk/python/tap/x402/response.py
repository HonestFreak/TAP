"""x402 `X-PAYMENT-RESPONSE` for the TAP `tap.v1.channel` scheme.

Returned by the producer once the channel-open transaction confirms. The
consumer treats this as the channel-open acknowledgement and proceeds to
the streaming phase."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

from tap.exceptions import X402Error


@dataclass(frozen=True, slots=True)
class PaymentResponse:
    tx_hash: str
    settlement: str  # "confirmed" | "finalized"
    channel_id: str
    channel_state: str  # "active"

    def to_payload(self) -> dict[str, Any]:
        return {
            "tx_hash": self.tx_hash,
            "settlement": self.settlement,
            "extra": {
                "channel_id": self.channel_id,
                "channel_state": self.channel_state,
            },
        }


def encode_response(resp: PaymentResponse) -> str:
    raw = json.dumps(resp.to_payload(), separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def decode_response(header_value: str) -> PaymentResponse:
    try:
        payload = json.loads(base64.b64decode(header_value, validate=True))
    except (ValueError, json.JSONDecodeError) as exc:
        raise X402Error("X-PAYMENT-RESPONSE is not valid base64-JSON") from exc

    extra = payload.get("extra") or {}
    try:
        return PaymentResponse(
            tx_hash=str(payload["tx_hash"]),
            settlement=str(payload["settlement"]),
            channel_id=str(extra["channel_id"]),
            channel_state=str(extra["channel_state"]),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise X402Error("X-PAYMENT-RESPONSE is missing or malformed fields") from exc
