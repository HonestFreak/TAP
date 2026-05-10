---
title: Producer SDK
sidebar_position: 2
---

# Producer SDK

`TapProducer` mounts onto a FastAPI app and exposes the four endpoint
shapes the protocol needs.

## Minimal example

```python
from tap import TapProducer, tokenizer
from tap.adapters.gemini import stream_gemini
from tap.chain.program_id import USDC_MINT_DEVNET
from tap.chain.rpc import ChainClient
from tap.producer.pricing import Pricing
from tap.timing.parameters import TimingParameters

producer = TapProducer(
    keypair=load_producer_keypair(),
    producer_usdc=PRODUCER_USDC_ATA,
    chain=ChainClient("https://api.devnet.solana.com"),
    pricing=Pricing(
        input_price_micro=1,           # 0.000001 USDC per prompt token
        output_price_micro=5,          # 0.000005 USDC per output token
        max_unpaid_micro=5_000,        # halt if >0.005 USDC unpaid
        trailing_buffer_tokens=10,
        tokenizer_id="tap.tok.v1",     # must be registered before construction
    ),
    timing=TimingParameters(grace_ms=200, pause_timeout_ms=30_000),
    network="solana-devnet",
    usdc_mint=USDC_MINT_DEVNET,
    public_base_url="http://localhost:8000",
    model_name="gemini-2.5-flash",
)


@producer.handler("/v1/messages")
async def handle(body: dict):
    """Forward to your model SDK and return an AsyncIterator[str]."""
    return stream_gemini(body)


app = producer.app   # mount in any ASGI server
```

Run with:

```bash
uvicorn demo.producer:app --host 0.0.0.0 --port 8000
```

## What `TapProducer` does

1. **Advertises session terms** via x402 — the GET endpoint returns
   generic `PaymentRequirements`; the POST endpoint with a prompt
   body returns prompt-bound `input_token_count` /
   `prepaid_input_micro`.
2. **Tokenizes the prompt** with the declared `tokenizer_id` and
   locks the input quote at session open.
3. **Accepts the consumer's open-channel transaction** — by default
   it submits via the configured RPC client; in production it would
   forward to an x402 facilitator.
4. **Verifies every incoming `X-TAP-COMMIT`** — sequence and
   `cumulative_paid` invariants, prepaid-input floor, Ed25519
   signature.
5. **Streams tokens with payment-aware pacing** — pauses when
   unpaid value reaches `max_unpaid`; halts when commits stop
   arriving past the pause window.
6. **Settles on-chain** when the session ends — assembling the
   Ed25519 verify ix + the `settle` ix into one transaction.
7. **Closes channels after the dispute window** — a built-in
   background `Settler` polls `getProgramAccounts` on a 10s cadence
   for channels in `Settling` past `settled_at + dispute_secs` and
   submits `close` automatically, so USDC moves to the producer ATA
   without operator intervention. Survives process restarts because
   it relies on on-chain state rather than in-memory timers.

## Endpoints mounted by `handler(path)`

For `producer.handler("/v1/messages")` the four shapes are:

| Method | Path | Trigger | Purpose |
| --- | --- | --- | --- |
| `GET`  | `/v1/messages` | none | Generic 402 challenge (no prompt yet) |
| `POST` | `/v1/messages` | body, no headers | Prompt-bound 402 with `input_token_count` |
| `POST` | `/v1/messages` | `X-PAYMENT` header | Channel-open via x402 |
| `POST` | `/v1/messages` | `X-TAP-CHANNEL` header + body | Stream over an existing channel |
| `POST` | `/v1/messages/commit` | `X-TAP-COMMIT` + `X-TAP-CHANNEL` | In-session commit upload |

## `Pricing`

The single immutable struct configuring all per-session economics.
Defined in `tap.producer.pricing`:

```python
@dataclass(frozen=True, slots=True)
class Pricing:
    input_price_micro: int          # micro-USDC per prompt token
    output_price_micro: int         # micro-USDC per output token
    max_unpaid_micro: int           # producer halts past this unpaid value
    trailing_buffer_tokens: int     # output buffer pre-authorized at open
    tokenizer_id: str               # must be registered locally
    min_deposit_micro: int = 1_000          # 0.001 USDC
    max_deposit_micro: int = 1_000_000_000  # 1,000 USDC
```

`__post_init__` rejects any non-positive price, a negative trailing
buffer, an empty `tokenizer_id`, or `min_deposit > max_deposit`.

Real-world LLM economics typically have a 1:3 to 1:5 input:output
ratio. The reference demo ships with `1:5`.

## Choosing a tokenizer

Whatever you advertise as `tokenizer_id`, **the consumer must be able
to run the same tokenization locally** (whitepaper §5.3.7). The SDK
ships with `tap.tok.v1` (a deterministic whitespace-and-punctuation
split, dependency-free) for demos. For production, register `tiktoken`
or your model vendor's own tokenizer:

```python
from tap import tokenizer
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")
tokenizer.register("cl100k_base", lambda text: len(enc.encode(text)))
```

Then publish that ID in your `Pricing.tokenizer_id`.

## Adapters

Adapters live in `sdk/python/tap/adapters/` in the repo.
Each one is `(body: dict) -> AsyncIterator[str]` of token deltas; the
producer wrapper handles metering, pacing, and SSE encoding around
them.

| Adapter | Default model | Install extra | Notes |
| --- | --- | --- | --- |
| `stream_anthropic` | `claude-sonnet-4-6` | `[anthropic]` | Forwards `body` verbatim; supplies `model` / `max_tokens` defaults |
| `stream_openai` | `gpt-4o-mini` | `[openai]` | Sets `stream=True`; reads `choices[0].delta.content` |
| `stream_gemini` | `gemini-2.5-flash` | none (uses httpx) | Direct REST + SSE; falls back to `gemini-2.5-flash-lite` on transient 5xx; word-splits long chunks for visible metering |
| `stream_ollama` | `llama3.2` | `[ollama]` | Local Llama via Ollama; useful for offline demos |

### Writing your own

```python
from typing import AsyncIterator

async def stream_my_model(body: dict) -> AsyncIterator[str]:
    async for chunk in my_sdk.stream(body):
        yield chunk.delta_text
```

Pass it to `producer.handler(...)`. If your model's tokenization
isn't registered in `tap.tokenizer`, register it before constructing
the producer (`__init__` will raise `ValueError` otherwise).

## `ActiveChannel`

Per-session producer state. Lives in memory between channel-open and
settlement; not persisted across restarts.

| Property | Description |
| --- | --- |
| `channel_id`, `consumer`, `session_key`, `consumer_usdc` | Identity |
| `deposit_micro`, `input_price_micro`, `output_price_micro`, `prepaid_input_micro` | Frozen at open |
| `trailing_buffer_tokens` | Output overdraw the producer pre-accepted |
| `tokens_delivered` | Output tokens streamed to the consumer so far |
| `last_commitment` | Latest accepted `SignedCommitment`, or `None` |
| `cumulative_paid_micro` | `last_commitment.cumulative_paid` or `prepaid_input_micro` if no commit yet |
| `output_value_delivered_micro` | `tokens_delivered × output_price_micro` |
| `unpaid_value_micro` | `output_value_delivered − (cumulative_paid − prepaid_input)` |
| `trailing_buffer_micro` | `trailing_buffer_tokens × output_price_micro` |
| `halted`, `halted_reason` | Set when `mark_halted(reason)` fires |

The wrapper consults `unpaid_value_micro` against `Pricing.max_unpaid_micro`
on every emitted token; once it would exceed, generation pauses (within
the grace window) until a fresh commit arrives.

## Settlement

When the stream ends — completed, halted by the consumer, or halted
by the producer — the producer schedules `settle_channel` as a
background task (decoupled from the SSE generator's lifecycle, so a
client disconnect or response finalize can't cancel it):

1. Builds an Ed25519 verify instruction that asserts the latest
   commit's signature against the channel's session key.
2. Builds the `settle` instruction carrying the canonical commit
   bytes plus the same signature.
3. Submits both as one transaction signed by the producer keypair.
4. Logs success / failure to the producer's stdout.
5. Removes the channel from the in-memory `ChannelRegistry`.

If no commit was ever received (the consumer paid prefill but the
producer halted before any output token landed), the on-chain
program treats `cumulative_paid` as exactly `prepaid_input_micro`
(see Appendix A.2 of the [whitepaper](/whitepaper)).

## Auto-close (`Settler`)

`TapProducer` boots a `tap.producer.settler.Settler` in its FastAPI
lifespan. The worker:

1. On a 10s cadence, calls `getProgramAccounts` filtered by `status =
   Settling` and `producer = self.pubkey()`.
2. Decodes each match with `tap.chain.channel_account.decode_channel`.
3. For any whose `settled_at + dispute_secs + 5s slack` is in the past,
   submits the `close` instruction. The 5s slack absorbs producer-host
   vs. cluster clock skew.
4. Logs each successful close (`paid` / `refund`) and warns on failure
   without aborting the loop.

A one-shot CLI is also exposed for cron / maintenance use:

```bash
TAP_PRODUCER_KEYPAIR=... TAP_PRODUCER_USDC=... \
  python -m tap.producer.settler_cli
```
