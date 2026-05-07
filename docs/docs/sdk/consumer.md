---
title: Consumer SDK
sidebar_position: 3
---

# Consumer SDK

`TapConsumer` discovers a producer, audits its terms, opens a Solana
channel, and yields a streaming iterator of token chunks.

## Minimal example

```python
import asyncio
from solders.keypair import Keypair

from tap import TapConsumer, evaluators
from tap.chain.rpc import ChainClient

EXPECTED_SCHEMA = {
    "type": "object",
    "required": ["title", "summary", "tags"],
    "properties": {
        "title":   {"type": "string"},
        "summary": {"type": "string"},
        "tags":    {"type": "array", "items": {"type": "string"}},
    },
}

PROMPT_BODY = {
    "messages": [
        {"role": "user", "content": "Return a JSON object with keys title, summary, tags."}
    ]
}


async def main():
    wallet = Keypair.from_bytes(load_secret_key())

    async with ChainClient("https://api.devnet.solana.com") as chain, \
               TapConsumer(wallet=wallet, chain=chain) as consumer:

        session = await consumer.open_session(
            producer_url="https://provider.example.com/v1/messages",
            deposit_micro=50_000,           # max session cost: $0.05
            prompt_body=PROMPT_BODY,
            evaluator=evaluators.compose(
                evaluators.json_schema(EXPECTED_SCHEMA),
                evaluators.length_cap(2_000),
                evaluators.repetition_guard(),
            ),
        )

        async for chunk in session.stream(PROMPT_BODY):
            print(chunk.text, end="", flush=True)

        print(f"\nSettled: paid {session.cumulative_paid_micro} micro-USDC, "
              f"halted by {session.halted_by or 'completion'}")


asyncio.run(main())
```

## `TapConsumer`

```python
TapConsumer(
    *,
    wallet: Keypair,                      # primary wallet — funds the deposit
    chain: ChainClient,                   # async-RPC convenience wrapper
    policy: ConsumerPolicy | None = None,
    usdc_mint: Pubkey | None = None,      # defaults to the devnet USDC mint
    http: httpx.AsyncClient | None = None,
)
```

Use as an async context manager (`async with TapConsumer(...) as c:`)
so the underlying `httpx` client is released cleanly. If you supply
your own `http=` client, ownership stays with you.

### `open_session`

```python
await consumer.open_session(
    *,
    producer_url: str,
    deposit_micro: int,
    prompt_body: dict[str, Any],
    evaluator: Evaluator | None = None,
    k_max: int = 16,                       # adaptive-batching ceiling
    on_commit: CommitCallback | None = None,
) -> ConsumerSession
```

Steps performed:

1. **POST the prompt body to the producer** with no payment — receives
   the prompt-bound 402 quote.
2. **Audit terms** against `ConsumerPolicy` (max input/output prices,
   max trailing buffer, allowed networks, etc.). Any unfavorable
   parameter aborts before any funds escrow.
3. **Re-tokenize the prompt** locally with the producer's declared
   `tokenizer_id` and check against `input_token_count`. Mismatch is
   misbehaviour and aborts.
4. **Verify deposit covers prepaid input** — `prepaid_input_micro <=
   deposit_micro`.
5. **Generate a session keypair** in memory (whitepaper §4.5 — your
   primary wallet doesn't sign per-token).
6. **Build and sign** the `open_channel` transaction with
   `prepaid_input_micro` locked on-chain.
7. **POST X-PAYMENT** to the producer; receive `X-PAYMENT-RESPONSE`
   with the channel ID.
8. **Return** a `ConsumerSession` ready to stream.

## `ConsumerSession`

The object returned from `open_session`. One session per request; a
new session is opened for each prompt (or reuse the channel; see
[Channel reuse](/protocol/on-chain#channel-reuse)).

### Streaming

`session.stream(body)` is an async iterator yielding `TokenChunk`s.
The session internally:

- Accumulates output and runs the evaluator after each token.
- Signs an `X-TAP-COMMIT` every K tokens (K floats per AIMD pressure).
- Detects producer pauses via the `HaltDetector`; raises `HaltError`
  if the producer goes silent past the pause window.
- Halts the stream and force-signs a final commit if the evaluator
  returns `Decision.HALT`.

The `body` you pass to `stream()` should be the **same** object you
passed to `open_session(prompt_body=...)`. The prepaid-input floor on
the channel is bound to that prompt's tokenization.

### Properties

| Property | Type | Description |
| --- | --- | --- |
| `channel_id` | `str` | Base58 channel PDA |
| `session_pubkey` | `str` | The in-memory session-key pubkey registered on-chain |
| `open_tx_signature` | `str \| None` | Signature of the `open_channel` transaction |
| `cumulative_paid_micro` | `int` | Latest `cumulative_paid` the consumer has signed |
| `prepaid_input_micro` | `int` | On-chain settlement floor for this session |
| `tokens_received` | `int` | Output tokens streamed so far |
| `halted_by` | `str \| None` | Name of the evaluator that halted the session, if any |

### `TokenChunk`

```python
@dataclass(frozen=True, slots=True)
class TokenChunk:
    text: str
    cumulative_paid_micro: int
    tokens_received: int
```

The unit yielded by `session.stream(...)`. `text` is what the
application consumes; `cumulative_paid_micro` is the running
authorization at the moment this chunk was received.

### `CommitSigned`

```python
@dataclass(frozen=True, slots=True)
class CommitSigned:
    sequence: int
    cumulative_paid_micro: int
    tokens_received: int
    timestamp_ms: int
```

Pass `on_commit=` to `open_session(...)` to receive these every time
the session signs a commit. Useful for dashboards:

```python
async def on_commit(signed: CommitSigned) -> None:
    metrics.record_commit(signed.cumulative_paid_micro, signed.tokens_received)

session = await consumer.open_session(..., on_commit=on_commit)
```

## Policy

`ConsumerPolicy` has sensible defaults; override per workload:

```python
from tap.consumer.policy import ConsumerPolicy

policy = ConsumerPolicy(
    max_input_price_micro=10,        # 0.00001 USDC/input token
    max_output_price_micro=50,       # 0.00005 USDC/output token
    max_trailing_buffer_tokens=20,
    min_pause_timeout_ms=1_000,
    max_dispute_secs=300,
    allowed_networks=frozenset({"solana-mainnet"}),
    verify_input_tokens=True,        # whitepaper §5.3.7 defense
)

consumer = TapConsumer(wallet=..., chain=..., policy=policy)
```

### Audit rules

Any of these abort `open_session` *before* the funding tx is built:

- `network` not in `allowed_networks`
- `input_price_micro` > `max_input_price_micro`
- `output_price_micro` > `max_output_price_micro`
- `trailing_buffer_tokens` > `max_trailing_buffer_tokens`
- `pause_timeout_ms` < `min_pause_timeout_ms`
- `dispute_secs` > `max_dispute_secs`
- `prepaid_input_micro` ≠ `input_token_count × input_price_micro`
  (catches producers smuggling extra cost into `prepaid_input`)
- (when `verify_input_tokens=True`) consumer's local tokenizer count
  differs from the producer's `input_token_count`

`verify_input_tokens=False` is acceptable for low-stakes sessions
where the producer has established reputation; the protocol exposes
the choice rather than mandating a single cost model.

## Timing

The trio of timeouts that govern pause / halt behaviour
([whitepaper §4.2.3](/concepts/session-lifecycle)):

```python
from tap.timing.parameters import TimingParameters

timing = TimingParameters(
    grace_ms=200,                    # absence → "paused"
    pause_timeout_ms=5_000,          # paused → "halted"
    total_session_ms=5 * 60 * 1_000, # outer bound on session length
)
```

Construction enforces `grace_ms ≤ pause_timeout_ms ≤ total_session_ms`.
Producers publish their values in the x402 payment requirements; the
consumer adopts them after passing the policy audit.
