"""Exception hierarchy. Every TAP-raised error inherits from `TapError` so
applications can catch the protocol's failures without catching unrelated
network or wallet errors."""

from __future__ import annotations


class TapError(Exception):
    """Base class for all TAP exceptions."""


class ProtocolError(TapError):
    """A wire-format or schema violation."""


class CommitmentError(TapError):
    """A commitment failed validation (sequence, monotonicity, signature)."""


class HaltError(TapError):
    """Raised on the consumer side when the producer halts unexpectedly, or
    on the producer side when commitments stop arriving."""


class SettlementError(TapError):
    """An on-chain settlement failed or returned an unexpected state."""


class ChannelStateError(TapError):
    """The channel is not in the state required for the requested operation."""


class X402Error(TapError):
    """An x402-layer failure (bad requirements payload, missing fields, etc.)."""
