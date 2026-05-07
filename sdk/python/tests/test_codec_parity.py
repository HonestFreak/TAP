"""Codec parity test: the bytes the Python signer produces must match the
bytes the on-chain Rust verifier expects.

We rebuild the Rust `CommitMessage::message_bytes` layout by hand here as
a cross-check; if either side changes the field order or width, this test
catches it before deployment."""

from __future__ import annotations

from solders.pubkey import Pubkey

from tap.protocol.codec import encode_commitment_bytes
from tap.protocol.commit import CommitMessage


def test_layout_matches_rust() -> None:
    channel = Pubkey.from_string("TapPRoTuQDmXiBg2H4Z7Lp4uKnxw3w6f8Y4F2X1aBcD")
    message = CommitMessage(
        channel=channel,
        sequence=42,
        cumulative_paid=1_234_567,
        tokens_received=12_345,
        timestamp_ms=1_700_000_000_000,
    )
    encoded = encode_commitment_bytes(message)

    expected = (
        bytes(channel)
        + (42).to_bytes(8, "little")
        + (1_234_567).to_bytes(8, "little")
        + (12_345).to_bytes(4, "little")
        + (1_700_000_000_000).to_bytes(8, "little")
    )
    assert encoded == expected
    assert len(encoded) == 32 + 8 + 8 + 4 + 8


def test_signing_round_trip() -> None:
    from nacl.signing import SigningKey

    from tap.protocol.signing import sign_commitment, verify_commitment

    key = SigningKey.generate()
    message = CommitMessage(
        channel=Pubkey.from_string("TapPRoTuQDmXiBg2H4Z7Lp4uKnxw3w6f8Y4F2X1aBcD"),
        sequence=1,
        cumulative_paid=100,
        tokens_received=20,
        timestamp_ms=0,
    )
    signed = sign_commitment(message, key)
    verify_commitment(signed, Pubkey.from_bytes(bytes(key.verify_key)))
