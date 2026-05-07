"""Commitment verification.

Two checks happen for every incoming commitment: cryptographic (the
session-key signature is valid) and protocol-level (sequence, prepaid-input
floor, and cumulative_paid invariants hold relative to the last accepted
commitment). All must pass for the producer to advance its accepted state."""

from __future__ import annotations

from tap.exceptions import CommitmentError
from tap.producer.channel import ActiveChannel
from tap.protocol.commit import SignedCommitment
from tap.protocol.signing import verify_commitment


def accept_commitment(channel: ActiveChannel, signed: SignedCommitment) -> None:
    """Validate `signed` against `channel`'s session key and last-accepted
    commitment, then advance the channel's accepted state. Raises
    `CommitmentError` on any failure."""
    if signed.message.channel != channel.channel_id:
        raise CommitmentError("commitment is for a different channel")

    last = channel.last_commitment
    if last is not None:
        if signed.message.sequence <= last.message.sequence:
            raise CommitmentError(
                f"commitment sequence {signed.message.sequence} is not "
                f"strictly greater than {last.message.sequence}"
            )
        if signed.message.cumulative_paid < last.message.cumulative_paid:
            raise CommitmentError("commitment cumulative_paid is non-monotonic")

    # Whitepaper §4.9: every signed commitment must clear the prepaid-input
    # floor. The on-chain program enforces the same bound at settle time,
    # but rejecting low commits here means the producer never advances state
    # past one that would on-chain-fail anyway.
    if signed.message.cumulative_paid < channel.prepaid_input_micro:
        raise CommitmentError(
            f"commitment cumulative_paid {signed.message.cumulative_paid} is "
            f"below the prepaid input floor {channel.prepaid_input_micro}"
        )

    if signed.message.cumulative_paid > channel.deposit_micro:
        raise CommitmentError("commitment cumulative_paid exceeds deposit")

    verify_commitment(signed, channel.session_key)
    channel.note_commit(signed)
