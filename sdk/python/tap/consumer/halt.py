"""Consumer-side halt detection for delayed producer output.

Mirrors the producer-side pause/halt logic at whitepaper §4.2.3: the
consumer enters `paused` state when the producer goes silent for
`grace_ms`, and treats the session as halted if silence exceeds
`pause_timeout_ms`."""

from __future__ import annotations

import time
from enum import Enum

from tap.timing.parameters import TimingParameters


class StreamState(Enum):
    LIVE = "live"
    PAUSED = "paused"
    HALTED = "halted"


class HaltDetector:
    """Tracks the time since the last token was received and reports
    state transitions. Stateful but cheap; one instance per session."""

    __slots__ = ("_timing", "_last_token_at", "_state")

    def __init__(self, timing: TimingParameters) -> None:
        self._timing = timing
        self._last_token_at = _now_ms()
        self._state = StreamState.LIVE

    def note_token(self) -> None:
        self._last_token_at = _now_ms()
        self._state = StreamState.LIVE

    def evaluate(self) -> StreamState:
        elapsed = _now_ms() - self._last_token_at
        if elapsed >= self._timing.pause_timeout_ms:
            self._state = StreamState.HALTED
        elif elapsed >= self._timing.grace_ms:
            if self._state is not StreamState.HALTED:
                self._state = StreamState.PAUSED
        else:
            self._state = StreamState.LIVE
        return self._state

    @property
    def state(self) -> StreamState:
        return self._state


def _now_ms() -> int:
    return time.monotonic_ns() // 1_000_000
