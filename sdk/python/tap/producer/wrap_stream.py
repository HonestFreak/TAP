"""`wrap_stream` — convert a model's raw token iterator into the protocol-aware
stream a `TapProducer` mounts as an HTTP handler.

The wrapper is the integration point with model SDKs. It:
  * forwards tokens unchanged
  * meters them against the channel's pricing
  * pauses when unpaid value approaches the cap
  * halts when the consumer goes silent past the pause window

Backpressure on the model: most provider SDKs let us stop iterating to
stop generation. The wrapper relies on this; if a wrapped SDK does NOT
honor cancellation, the producer may continue spending compute past the
halt point with no recovery — a SDK bug, not a protocol bug."""

from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator

from tap.producer.channel import ActiveChannel
from tap.producer.halt import should_halt, should_pause
from tap.producer.pricing import Pricing
from tap.timing.parameters import TimingParameters


async def wrap_stream(
    tokens: AsyncIterator[str],
    *,
    channel: ActiveChannel,
    pricing: Pricing,
    timing: TimingParameters,
) -> AsyncIterator[tuple[str, int]]:
    """Yield `(token, ack_sequence)` pairs. `ack_sequence` is the latest
    accepted commitment sequence at the moment the token is emitted; the
    consumer uses it to verify the producer has registered their progress
    (whitepaper §B.3)."""
    # Reset the silence clock on each token sent, not just on commits
    # received. Without this, slow upstream models (Gemini's first-token
    # latency is routinely 3–8s) eat into the budget before the consumer
    # has any chance to respond, and we'd halt before streaming a single
    # byte. With per-token reset the budget measures what it should: time
    # the consumer has been silent since the last byte we sent them.
    channel.last_commit_at_ms = int(time.monotonic() * 1_000)

    first = True
    async for token in tokens:
        deadline_ms = timing.grace_ms
        while should_pause(channel, pricing.max_unpaid_micro):
            await asyncio.sleep(0.01)
            deadline_ms -= 10
            if deadline_ms <= 0:
                if should_halt(channel, timing):
                    channel.mark_halted("consumer commitments lapsed")
                    return
                deadline_ms = timing.grace_ms

        if should_halt(channel, timing):
            channel.mark_halted("consumer commitments lapsed")
            return

        # Demo pacing: providers (Gemini in particular) can deliver many
        # logical tokens in a single network chunk. Without a small inter-
        # token gap the consumer renders them as one batch, defeating the
        # whole "watch the meter tick up" point of the dashboard. 30 ms is
        # imperceptible to a reader but enough to keep TCP frames separate
        # end-to-end.
        if not first:
            await asyncio.sleep(0.03)
        first = False

        channel.note_token()
        ack = channel.last_commitment.message.sequence if channel.last_commitment else 0
        yield token, ack

        # Refresh the silence clock after each successful send. The clock
        # then measures "how long since I last gave the consumer something
        # to respond to" — exactly what `pause_timeout_ms` is supposed to
        # bound.
        channel.last_commit_at_ms = int(time.monotonic() * 1_000)
