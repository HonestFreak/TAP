"""`TimingParameters` — the trio of timeouts that govern pause/halt behavior.

Whitepaper §4.2.3 specifies three independent durations:
    * grace_ms        — when "no recent action" becomes "paused"
    * pause_timeout_ms — when "paused" becomes "halted"
    * total_session_ms — outer bound on session length

These are negotiated at session open via the x402 requirements payload and
held immutable for the duration of the session."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TimingParameters:
    grace_ms: int = 200
    pause_timeout_ms: int = 5_000
    total_session_ms: int = 5 * 60 * 1_000

    def __post_init__(self) -> None:
        if self.grace_ms < 0 or self.pause_timeout_ms < 0 or self.total_session_ms < 0:
            raise ValueError("timing parameters must be non-negative")
        if self.grace_ms > self.pause_timeout_ms:
            raise ValueError("grace_ms must be <= pause_timeout_ms")
        if self.pause_timeout_ms > self.total_session_ms:
            raise ValueError("pause_timeout_ms must be <= total_session_ms")
