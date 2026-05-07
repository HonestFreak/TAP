"""`ConsumerSession` — the streaming iterator the application interacts with.

A session encapsulates a single streamed response. It:
  * holds the open channel and session key
  * advances `cumulative_paid` (starting at `prepaid_input_micro`) as output tokens arrive
  * runs the configured evaluator after each token batch
  * sends commitments every K tokens (K controlled by `AdaptiveBatcher`)
  * detects producer pauses/halts (`HaltDetector`)
  * surfaces a clean async iterator over token text

Each session is one-shot. Reuse is via `TapConsumer.open_session` returning
new instances; this keeps state machines small and avoids the need to
reset between requests."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Awaitable, Callable

import httpx
from solders.pubkey import Pubkey

from tap.consumer.batching import AdaptiveBatcher
from tap.consumer.halt import HaltDetector, StreamState
from tap.consumer.session_key import SessionKey
from tap.consumer.stream import iter_sse
from tap.evaluators.base import Decision, Evaluator
from tap.exceptions import HaltError
from tap.protocol.codec import encode_commitment
from tap.protocol.commit import CommitMessage
from tap.protocol.signing import sign_commitment
from tap.timing.parameters import TimingParameters
from tap.x402.headers import HEADER_TAP_COMMIT
from tap.x402.requirements import PaymentRequirements


@dataclass(frozen=True, slots=True)
class TokenChunk:
    """One unit of streamed output. `text` is what the application consumes;
    `cumulative_paid_micro` is what the consumer has authorized so far."""

    text: str
    cumulative_paid_micro: int
    tokens_received: int


@dataclass(frozen=True, slots=True)
class CommitSigned:
    """Observability event fired each time the session signs and posts a
    commitment to the producer. Surfaced via the `on_commit` callback so
    runners and dashboards can render the commitment timeline live."""

    sequence: int
    cumulative_paid_micro: int
    tokens_received: int
    timestamp_ms: int


CommitCallback = Callable[[CommitSigned], Awaitable[None]]


@dataclass(slots=True)
class _SessionState:
    sequence: int = 0
    tokens_received: int = 0
    cumulative_paid: int = 0
    accumulated: str = ""
    halted_by: str | None = None
    last_emitted_sequence: int = 0
    tokens_since_last_commit: int = 0


class ConsumerSession:
    """Single-request session against an open TAP channel."""

    def __init__(
        self,
        *,
        http: httpx.AsyncClient,
        requirements: PaymentRequirements,
        channel_id: str,
        session_key: SessionKey,
        timing: TimingParameters,
        evaluator: Evaluator | None,
        input_price_micro: int,
        output_price_micro: int,
        prepaid_input_micro: int,
        deposit_micro: int,
        unpaid_cap_micro: int,
        k_max: int,
        on_commit: "CommitCallback | None" = None,
    ) -> None:
        self._http = http
        self._requirements = requirements
        self._channel_id = channel_id
        self._session_key = session_key
        self._timing = timing
        self._evaluator = evaluator
        self._input_price_micro = input_price_micro
        self._output_price_micro = output_price_micro
        self._prepaid_input_micro = prepaid_input_micro
        self._deposit_micro = deposit_micro
        self._unpaid_cap_micro = unpaid_cap_micro
        self._batcher = AdaptiveBatcher(k_max=k_max)
        # Whitepaper §4.9: cumulative_paid starts at the prepaid input floor
        # before any output token arrives. The first signed commitment in the
        # session has `cumulative_paid >= prepaid_input` by construction.
        self._state = _SessionState(cumulative_paid=prepaid_input_micro)
        self._halt_detector = HaltDetector(timing)
        self._on_commit = on_commit
        self._open_tx_signature: str | None = None

    @property
    def channel_id(self) -> str:
        return self._channel_id

    @property
    def session_pubkey(self) -> str:
        return str(self._session_key.public_key)

    @property
    def open_tx_signature(self) -> str | None:
        return self._open_tx_signature

    @open_tx_signature.setter
    def open_tx_signature(self, value: str) -> None:
        self._open_tx_signature = value

    @property
    def cumulative_paid_micro(self) -> int:
        return self._state.cumulative_paid

    @property
    def prepaid_input_micro(self) -> int:
        return self._prepaid_input_micro

    @property
    def tokens_received(self) -> int:
        return self._state.tokens_received

    @property
    def halted_by(self) -> str | None:
        return self._state.halted_by

    async def stream(self, body: dict[str, Any]) -> AsyncIterator[TokenChunk]:
        """Open the streaming POST and yield one `TokenChunk` per token.

        `body` MUST be the same prompt body that produced the prompt-bound
        402 quote at session open — the prepaid-input floor is bound to that
        prompt's tokenization."""
        channel_pk = Pubkey.from_string(self._channel_id)

        async with self._http.stream(
            "POST",
            self._requirements.stream_url,
            json=body,
            headers={
                "Accept": "text/event-stream",
                "X-TAP-CHANNEL": self._channel_id,
            },
        ) as response:
            response.raise_for_status()
            async for event in iter_sse(response):
                if event.finished:
                    await self._send_commit(channel_pk, force=True)
                    return

                self._absorb_token(event.text)
                self._halt_detector.note_token()

                yield TokenChunk(
                    text=event.text,
                    cumulative_paid_micro=self._state.cumulative_paid,
                    tokens_received=self._state.tokens_received,
                )

                if self._evaluator and self._evaluator(self._state.accumulated) is Decision.HALT:
                    self._state.halted_by = getattr(self._evaluator, "name", "evaluator")
                    await self._send_commit(channel_pk, force=True)
                    return

                if self._halt_detector.evaluate() is StreamState.HALTED:
                    raise HaltError("producer stopped sending tokens past pause window")

                if self._batcher.should_commit(self._state.tokens_since_last_commit):
                    await self._send_commit(channel_pk)
                    self._batcher.update(
                        unpaid_value=self._unpaid_value(),
                        unpaid_cap=self._unpaid_cap_micro,
                    )

    def _absorb_token(self, text: str) -> None:
        self._state.tokens_received += 1
        self._state.tokens_since_last_commit += 1
        # Output cost accumulates on top of the prepaid input floor.
        self._state.cumulative_paid = min(
            self._deposit_micro,
            self._state.cumulative_paid + self._output_price_micro,
        )
        self._state.accumulated += text

    def _unpaid_value(self) -> int:
        return self._state.tokens_since_last_commit * self._output_price_micro

    async def _send_commit(self, channel_pk: Any, *, force: bool = False) -> None:
        if not force and self._state.tokens_since_last_commit == 0:
            return
        self._state.sequence += 1
        commitment = CommitMessage(
            channel=channel_pk,
            sequence=self._state.sequence,
            cumulative_paid=self._state.cumulative_paid,
            tokens_received=self._state.tokens_received,
            timestamp_ms=int(time.time() * 1_000),
        )
        signed = sign_commitment(commitment, self._session_key.signer)
        encoded = encode_commitment(signed)
        # Out-of-band ack: the producer reads commitments off the same TCP
        # connection the response is streaming on by parsing this header
        # from a second request to the producer's commit endpoint. Keeping
        # commitments on a side channel avoids interleaving them with the
        # response body and makes both sides easier to reason about.
        await self._http.post(
            self._requirements.stream_url + "/commit",
            headers={HEADER_TAP_COMMIT: encoded, "X-TAP-CHANNEL": self._channel_id},
        )
        self._state.last_emitted_sequence = self._state.sequence
        self._state.tokens_since_last_commit = 0
        if self._on_commit is not None:
            await self._on_commit(
                CommitSigned(
                    sequence=commitment.sequence,
                    cumulative_paid_micro=commitment.cumulative_paid,
                    tokens_received=commitment.tokens_received,
                    timestamp_ms=commitment.timestamp_ms,
                )
            )
