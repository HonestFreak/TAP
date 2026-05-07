"""Commitment data classes.

The `CommitMessage` byte layout MUST stay in sync with the on-chain Rust
`CommitMessage::message_bytes`. The order, sizes, and endianness here are
the source of truth for both the Solana program and the Python SDK; if you
change one, change the other in the same commit."""

from __future__ import annotations

from dataclasses import dataclass

from solders.pubkey import Pubkey

SCHEMA = "tap.v1.commit"
"""Identifier embedded in JSON-encoded commitments. Bumped on any
breaking change to the message layout."""


@dataclass(frozen=True, slots=True)
class CommitMessage:
    """Off-chain payment authorization for a single point in a session.

    `cumulative_paid` is the only field the on-chain program acts on at
    settlement; `tokens_received` and `timestamp_ms` are present for
    auditing and analytics."""

    channel: Pubkey
    sequence: int
    cumulative_paid: int
    tokens_received: int
    timestamp_ms: int


@dataclass(frozen=True, slots=True)
class SignedCommitment:
    """A `CommitMessage` together with the session-key Ed25519 signature
    over its canonical byte form."""

    message: CommitMessage
    signature: bytes
