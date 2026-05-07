"""Canonical byte and JSON codecs for `CommitMessage`.

Two encodings exist, intentionally:

* The byte encoding (`encode_commitment_bytes`) is what the session key
  signs and what the on-chain program verifies. It is fixed-width and has
  no field labels.
* The JSON encoding (`encode_commitment` / `decode_commitment`) is what
  travels over HTTP in the `X-TAP-COMMIT` header. It is verbose so that
  intermediaries can debug it.

Always sign and verify the byte form; never the JSON.
"""

from __future__ import annotations

import base64
import json
from typing import Any

from solders.pubkey import Pubkey

from tap.exceptions import ProtocolError
from tap.protocol.commit import SCHEMA, CommitMessage, SignedCommitment


def encode_commitment_bytes(message: CommitMessage) -> bytes:
    """Produce the bytes the on-chain program expects to verify against."""
    return b"".join(
        [
            bytes(message.channel),  # 32
            message.sequence.to_bytes(8, "little"),
            message.cumulative_paid.to_bytes(8, "little"),
            message.tokens_received.to_bytes(4, "little"),
            message.timestamp_ms.to_bytes(8, "little"),
        ]
    )


def encode_commitment(signed: SignedCommitment) -> str:
    """JSON-then-base64 encoding for HTTP header transport."""
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "channel_id": str(signed.message.channel),
        "sequence": signed.message.sequence,
        "cumulative_paid": signed.message.cumulative_paid,
        "tokens_received": signed.message.tokens_received,
        "timestamp_ms": signed.message.timestamp_ms,
        "signature": base64.b64encode(signed.signature).decode("ascii"),
    }
    return base64.b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")


def decode_commitment(header_value: str) -> SignedCommitment:
    """Inverse of `encode_commitment`. Raises `ProtocolError` on malformed
    input rather than letting JSON or base64 errors leak through."""
    try:
        raw = base64.b64decode(header_value, validate=True)
        payload = json.loads(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ProtocolError("X-TAP-COMMIT is not valid base64-encoded JSON") from exc

    if payload.get("schema") != SCHEMA:
        raise ProtocolError(f"unknown commit schema {payload.get('schema')!r}")

    try:
        message = CommitMessage(
            channel=Pubkey.from_string(payload["channel_id"]),
            sequence=int(payload["sequence"]),
            cumulative_paid=int(payload["cumulative_paid"]),
            tokens_received=int(payload["tokens_received"]),
            timestamp_ms=int(payload["timestamp_ms"]),
        )
        signature = base64.b64decode(payload["signature"], validate=True)
    except (KeyError, ValueError, TypeError) as exc:
        raise ProtocolError("X-TAP-COMMIT payload is missing or malformed fields") from exc

    if len(signature) != 64:
        raise ProtocolError("commitment signature must be 64 bytes")

    return SignedCommitment(message=message, signature=signature)
