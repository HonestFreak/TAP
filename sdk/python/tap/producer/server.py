"""`TapProducer` — HTTP surface for a TAP-enabled inference provider.

Mounts onto a FastAPI app and exposes:
  * GET  `/<path>`         → x402 402 challenge with generic terms (no prompt yet)
  * POST `/<path>` (no payment, with prompt body) → x402 402 challenge with
                             prompt-bound `input_token_count` / `prepaid_input`
                             per whitepaper §4.9
  * POST `/<path>`         → channel-open via x402 X-PAYMENT (with optional body)
  * POST `/<path>/commit`  → in-session X-TAP-COMMIT receiver
The streaming POST is the same `/<path>` URL once the channel is open
(carried on the `X-TAP-CHANNEL` header).

The producer is intentionally framework-light: a thin layer over FastAPI
handles routing and SSE; everything else lives in dedicated modules so it
can be swapped (e.g. for a non-FastAPI server) without touching protocol
logic."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

from tap import tokenizer
from tap.chain.rpc import ChainClient
from tap.exceptions import CommitmentError, ProtocolError, X402Error
from tap.producer.channel import ActiveChannel
from tap.producer.handler_types import HandlerFn
from tap.producer.pricing import Pricing
from tap.producer.registry import ChannelRegistry
from tap.producer.settle import settle_channel
from tap.producer.settler import Settler
from tap.producer.sse import encode_sse
from tap.producer.verifier import accept_commitment
from tap.producer.wrap_stream import wrap_stream
from tap.protocol.codec import decode_commitment
from tap.protocol.prompt import extract_prompt_text
from tap.timing.parameters import TimingParameters
from tap.x402.headers import (
    HEADER_PAYMENT,
    HEADER_PAYMENT_REQUIREMENTS,
    HEADER_PAYMENT_RESPONSE,
    HEADER_TAP_COMMIT,
)
from tap.x402.payment import decode_payment
from tap.x402.requirements import PaymentRequirements, SCHEME, encode_requirements
from tap.x402.response import PaymentResponse, encode_response

_log = logging.getLogger(__name__)

# On-chain dispute window we advertise in `_build_requirements`. The settler
# waits past `settled_at + dispute_secs` before calling `close`; the value
# itself is enforced on-chain, this is just the producer's negotiated terms.
_DISPUTE_SECS = 30

# How often the settler scans for channels ready to close. Trades RPC load
# against worst-case time-to-close after the dispute window expires.
_SETTLER_POLL_SECS = 10.0


@dataclass(slots=True)
class _Route:
    path: str
    handler: HandlerFn


class TapProducer:
    """A producer host. Construct one, register handlers with `.handler(path)`,
    then mount `producer.app` in your ASGI server.

    The producer is responsible for:
      * advertising session terms via x402 (input/output prices, tokenizer id)
      * tokenizing the prompt and quoting `prepaid_input` per whitepaper §4.9
      * accepting the consumer's open-channel transaction
      * verifying every incoming commitment (including the prepaid-input floor)
      * streaming tokens with payment-aware pacing
      * settling on-chain when the session ends
    """

    def __init__(
        self,
        *,
        keypair: Keypair,
        producer_usdc: Pubkey,
        chain: ChainClient,
        pricing: Pricing,
        timing: TimingParameters | None = None,
        network: str = "solana-devnet",
        usdc_mint: Pubkey | None = None,
        public_base_url: str | None = None,
        model_name: str | None = None,
    ) -> None:
        from tap.chain.program_id import PROGRAM_ID, USDC_MINT_DEVNET

        if not tokenizer.is_registered(pricing.tokenizer_id):
            raise ValueError(
                f"tokenizer {pricing.tokenizer_id!r} is not registered; "
                "call tap.tokenizer.register(...) before constructing TapProducer"
            )

        self._keypair = keypair
        self._producer_usdc = producer_usdc
        self._chain = chain
        self._pricing = pricing
        self._timing = timing or TimingParameters()
        self._network = network
        self._usdc_mint = usdc_mint or USDC_MINT_DEVNET
        self._program_id = PROGRAM_ID
        self._public_base_url = public_base_url or "http://localhost:8000"
        self._model_name = model_name

        self._registry = ChannelRegistry()
        self._routes: dict[str, _Route] = {}
        # Background settle tasks per session. Held strongly so asyncio
        # doesn't GC them — the SSE response that triggered them has
        # already finished sending bytes by the time settle lands on chain.
        self._pending_settles: set[asyncio.Task[Any]] = set()
        # The settler picks up *any* of our channels in `Settling` past the
        # dispute window — including ones that survived a process restart,
        # which an in-process `asyncio.sleep` timer could never recover.
        self._settler = Settler(
            chain=self._chain,
            program_id=self._program_id,
            producer=self._keypair,
            producer_usdc=self._producer_usdc,
            poll_interval_secs=_SETTLER_POLL_SECS,
        )

        # FastAPI's `lifespan=` is the post-0.110 replacement for the now-
        # removed `add_event_handler("startup"/"shutdown", ...)`. We bind the
        # settler's start/stop into one async context manager.
        settler = self._settler

        @asynccontextmanager
        async def lifespan(_app: FastAPI):
            settler.start()
            try:
                yield
            finally:
                await settler.stop()

        self._app = FastAPI(
            title="TAP Producer",
            docs_url=None,
            redoc_url=None,
            lifespan=lifespan,
        )

    @property
    def app(self) -> FastAPI:
        return self._app

    def handler(self, path: str) -> Any:
        """Decorator. Registers `fn` as the model-stream handler for `path`."""
        def decorate(fn: HandlerFn) -> HandlerFn:
            normalized = path if path.startswith("/") else f"/{path}"
            self._routes[normalized] = _Route(path=normalized, handler=fn)
            self._mount(normalized)
            return fn
        return decorate

    def _mount(self, path: str) -> None:
        producer = self

        @self._app.get(path)
        async def _challenge_generic() -> Response:
            # No prompt available yet — return generic terms with zeroed
            # input_token_count/prepaid_input. The consumer must follow up
            # with a prompt-carrying POST to receive the prompt-bound quote.
            req = producer._build_requirements(path, prompt_text=None)
            return Response(
                status_code=402,
                headers={HEADER_PAYMENT_REQUIREMENTS: encode_requirements(req)},
            )

        @self._app.post(path)
        async def _stream(
            request: Request,
            x_payment: str | None = Header(default=None, alias=HEADER_PAYMENT),
            x_tap_channel: str | None = Header(default=None, alias="X-TAP-CHANNEL"),
        ) -> Any:
            # The protocol allows four shapes:
            #   1. Body, no X-PAYMENT, no X-TAP-CHANNEL  → 402 with prompt-bound quote
            #   2. X-PAYMENT only, no body               → channel-open ack
            #   3. X-TAP-CHANNEL + body                  → stream on existing channel
            #   4. X-PAYMENT + body                      → legacy combined open+stream
            raw = await request.body()
            body = json.loads(raw) if raw else None

            if x_tap_channel and body is not None:
                channel = await producer._registry.get(Pubkey.from_string(x_tap_channel))
                if channel is None:
                    raise HTTPException(404, "unknown channel")
                return await producer._stream_response(path, channel, body)

            if x_payment and body is None:
                channel = await producer._open_channel_from_payment(x_payment)
                ack = encode_response(
                    PaymentResponse(
                        tx_hash="pending",
                        settlement="confirmed",
                        channel_id=str(channel.channel_id),
                        channel_state="active",
                    )
                )
                return Response(status_code=200, headers={HEADER_PAYMENT_RESPONSE: ack})

            if x_payment and body is not None:
                channel = await producer._open_channel_from_payment(x_payment)
                response = await producer._stream_response(path, channel, body)
                response.headers[HEADER_PAYMENT_RESPONSE] = encode_response(
                    PaymentResponse(
                        tx_hash="pending",
                        settlement="confirmed",
                        channel_id=str(channel.channel_id),
                        channel_state="active",
                    )
                )
                return response

            # Body without payment: whitepaper §4.9 prompt-bound 402.
            if body is not None:
                prompt_text = extract_prompt_text(body)
                req = producer._build_requirements(path, prompt_text=prompt_text)
                return Response(
                    status_code=402,
                    headers={HEADER_PAYMENT_REQUIREMENTS: encode_requirements(req)},
                )

            raise HTTPException(402, "X-PAYMENT, X-TAP-CHANNEL, or prompt body required")

        @self._app.post(f"{path}/commit")
        async def _commit(
            x_tap_commit: str = Header(alias=HEADER_TAP_COMMIT),
            x_tap_channel: str = Header(alias="X-TAP-CHANNEL"),
        ) -> Response:
            try:
                signed = decode_commitment(x_tap_commit)
            except ProtocolError as exc:
                raise HTTPException(400, str(exc)) from exc
            channel = await producer._registry.get(Pubkey.from_string(x_tap_channel))
            if channel is None:
                raise HTTPException(404, "unknown channel")
            try:
                accept_commitment(channel, signed)
            except CommitmentError as exc:
                raise HTTPException(409, str(exc)) from exc
            return Response(status_code=204)

    def _build_requirements(
        self, path: str, *, prompt_text: str | None
    ) -> PaymentRequirements:
        # If the consumer has already submitted a prompt, run the producer's
        # declared tokenizer and lock in the input quote. Otherwise return
        # generic terms with zero input cost — the consumer must POST the
        # prompt to get a binding quote (whitepaper §4.9).
        if prompt_text is not None:
            input_token_count = tokenizer.count(self._pricing.tokenizer_id, prompt_text)
            prepaid_input_micro = input_token_count * self._pricing.input_price_micro
        else:
            input_token_count = 0
            prepaid_input_micro = 0

        return PaymentRequirements(
            scheme=SCHEME,
            network=self._network,
            asset=str(self._usdc_mint),
            recipient=str(self._program_id),
            producer_pubkey=str(self._keypair.pubkey()),
            input_price_micro=self._pricing.input_price_micro,
            output_price_micro=self._pricing.output_price_micro,
            tokenizer_id=self._pricing.tokenizer_id,
            input_token_count=input_token_count,
            prepaid_input_micro=prepaid_input_micro,
            max_unpaid_micro=self._pricing.max_unpaid_micro,
            trailing_buffer_tokens=self._pricing.trailing_buffer_tokens,
            duration_secs=self._timing.total_session_ms // 1_000,
            dispute_secs=_DISPUTE_SECS,
            grace_ms=self._timing.grace_ms,
            pause_timeout_ms=self._timing.pause_timeout_ms,
            channel_open_url=f"{self._public_base_url}{path}",
            stream_url=f"{self._public_base_url}{path}",
            model=self._model_name,
        )

    async def _open_channel_from_payment(self, header_value: str) -> ActiveChannel:
        try:
            payment = decode_payment(header_value)
        except X402Error as exc:
            raise HTTPException(400, str(exc)) from exc

        try:
            tx = VersionedTransaction.from_bytes(base64.b64decode(payment.transaction_b64))
        except Exception as exc:
            raise HTTPException(400, "X-PAYMENT.transaction is not a valid Solana tx") from exc

        # In production a producer would forward the tx to its x402
        # facilitator and wait for confirmation. For the reference flow we
        # submit directly via the configured RPC client.
        await self._chain.send_raw(bytes(tx))

        from tap.chain.pda import derive_ata, derive_channel_pda
        consumer = Pubkey.from_string(payment.consumer_pubkey)
        channel_id, _ = derive_channel_pda(consumer, self._keypair.pubkey(), payment.nonce)
        consumer_usdc = derive_ata(consumer, self._usdc_mint)

        channel = ActiveChannel(
            channel_id=channel_id,
            consumer=consumer,
            session_key=Pubkey.from_string(payment.session_key),
            consumer_usdc=consumer_usdc,
            deposit_micro=payment.deposit_micro,
            input_price_micro=payment.input_price_micro,
            output_price_micro=payment.output_price_micro,
            prepaid_input_micro=payment.prepaid_input_micro,
            trailing_buffer_tokens=payment.trailing_buffer_tokens,
            expires_at_ms=int(payment.duration_secs * 1_000),
        )
        await self._registry.put(channel)
        return channel

    async def _stream_response(
        self,
        path: str,
        channel: ActiveChannel,
        body: dict[str, Any],
    ) -> StreamingResponse:
        route = self._routes[path]
        token_iter = await route.handler(body)
        wrapped = wrap_stream(
            token_iter,
            channel=channel,
            pricing=self._pricing,
            timing=self._timing,
        )

        async def event_source() -> Any:
            # `encode_sse` already produces fully-formatted "data: ...\n\n"
            # frames, so we hand them to StreamingResponse verbatim.
            #
            # If the upstream model adapter raises mid-stream (Gemini 503,
            # network blip, etc.), we send a final error frame and end the
            # stream cleanly. Without this the consumer sees an incomplete
            # chunked-encoded body and surfaces a confusing transport error
            # instead of the actual upstream failure.
            try:
                try:
                    async for chunk in encode_sse(wrapped):
                        yield chunk
                except Exception as exc:
                    payload = json.dumps(
                        {"error": f"{type(exc).__name__}: {exc}"},
                        separators=(",", ":"),
                    )
                    yield f"data: {payload}\n\n"
                    yield "data: [DONE]\n\n"
            finally:
                # Settle MUST run as a separate task: doing it inline here
                # races with Starlette's `aclose()` of the SSE generator
                # (client disconnect, response finalize) and the settle code
                # gets dropped on the floor without a log line. As a task
                # it's owned by the event loop, not the generator's frame.
                self._spawn_settle_task(channel)

        return StreamingResponse(
            event_source(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    def _spawn_settle_task(self, channel: ActiveChannel) -> None:
        """Schedule `settle` for `channel` in a fresh task. Strong-refs the
        task on `self` so the event loop doesn't GC it mid-flight. The task
        always logs its outcome — without a log line, a failing settle is
        invisible because the SSE response that initiated it has long since
        finished writing bytes to the wire."""
        task = asyncio.create_task(
            self._settle_and_cleanup(channel),
            name=f"tap-settle-{channel.channel_id}",
        )
        self._pending_settles.add(task)
        task.add_done_callback(self._pending_settles.discard)

    async def _settle_and_cleanup(self, channel: ActiveChannel) -> None:
        try:
            if channel.last_commitment is None:
                _log.warning(
                    "skipping settle for channel %s: no accepted commitment",
                    channel.channel_id,
                )
                return
            result = await settle_channel(
                chain=self._chain,
                producer=self._keypair,
                producer_usdc=self._producer_usdc,
                channel=channel,
            )
            _log.info(
                "settled channel %s in tx %s (paid=%d)",
                channel.channel_id,
                result.signature,
                channel.last_commitment.message.cumulative_paid,
            )
        except Exception:
            # `exception()` includes the traceback — exactly what was missing
            # before. The producer process keeps running; the settler will
            # retry on its own poll cadence if it ever needs to.
            _log.exception("settle failed for channel %s", channel.channel_id)
        finally:
            try:
                await self._registry.remove(channel.channel_id)
            except Exception:
                _log.exception(
                    "registry cleanup failed for channel %s", channel.channel_id
                )
