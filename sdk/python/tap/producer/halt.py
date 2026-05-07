"""Producer-side halt detection (whitepaper §4.2.3).

Symmetric to the consumer detector. The producer halts when:
  * `unpaid_value` would exceed `max_unpaid` if it kept generating; OR
  * the last commitment was received longer than `pause_timeout_ms` ago.

`should_pause` returns True when generation should briefly stall waiting
for the next commitment (within the grace window); `should_halt` returns
True when the session is dead and settlement should be initiated."""

from __future__ import annotations

import time

from tap.producer.channel import ActiveChannel
from tap.timing.parameters import TimingParameters


def should_pause(channel: ActiveChannel, pricing_max_unpaid_micro: int) -> bool:
    return channel.unpaid_value_micro >= pricing_max_unpaid_micro


def should_halt(channel: ActiveChannel, timing: TimingParameters) -> bool:
    if channel.halted:
        return True
    silent_for_ms = int(time.monotonic() * 1_000) - channel.last_commit_at_ms
    return silent_for_ms >= timing.pause_timeout_ms


def silent_ms(channel: ActiveChannel) -> int:
    return int(time.monotonic() * 1_000) - channel.last_commit_at_ms
