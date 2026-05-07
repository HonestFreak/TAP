"""Per-active-session in-memory state held by the producer.

Lives only between channel open and settlement. Persisting this across
restarts is out of scope for v1 — a producer that crashes mid-session
will lose the latest commitment beyond what's already been disk-flushed,
and will recover (with `trailing_buffer` of slack) by settling whatever
commitment they last persisted."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from solders.pubkey import Pubkey

from tap.protocol.commit import SignedCommitment


@dataclass(slots=True)
class ActiveChannel:
    channel_id: Pubkey
    consumer: Pubkey
    session_key: Pubkey
    consumer_usdc: Pubkey
    deposit_micro: int
    input_price_micro: int
    output_price_micro: int
    prepaid_input_micro: int
    trailing_buffer_tokens: int
    expires_at_ms: int

    tokens_delivered: int = 0
    last_commitment: SignedCommitment | None = None
    last_commit_at_ms: int = field(default_factory=lambda: int(time.monotonic() * 1_000))
    halted: bool = False
    halted_reason: str | None = None

    @property
    def cumulative_paid_micro(self) -> int:
        """Floor at `prepaid_input_micro` even before any commitment lands —
        the on-chain program will pay out at least that much regardless of
        off-chain state (whitepaper §4.9)."""
        if self.last_commitment is None:
            return self.prepaid_input_micro
        return self.last_commitment.message.cumulative_paid

    @property
    def output_value_delivered_micro(self) -> int:
        return self.tokens_delivered * self.output_price_micro

    @property
    def unpaid_value_micro(self) -> int:
        """Output-side unpaid value. Input is already secured by prepaid_input."""
        committed_output = max(0, self.cumulative_paid_micro - self.prepaid_input_micro)
        return self.output_value_delivered_micro - committed_output

    @property
    def trailing_buffer_micro(self) -> int:
        return self.trailing_buffer_tokens * self.output_price_micro

    def note_token(self) -> None:
        self.tokens_delivered += 1

    def note_commit(self, signed: SignedCommitment) -> None:
        self.last_commitment = signed
        self.last_commit_at_ms = int(time.monotonic() * 1_000)

    def mark_halted(self, reason: str) -> None:
        self.halted = True
        self.halted_reason = reason
