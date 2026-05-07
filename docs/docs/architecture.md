---
title: Architecture
sidebar_position: 2
---

# TAP Architecture

This document describes how the four implementation components fit
together. The whitepaper specifies what the protocol does; this document
specifies how the reference code does it.

## Trust boundary diagram

```
                  on-chain (Solana)
        ┌─────────────────────────────────┐
        │   tap program (Anchor)          │
        │   open_channel  settle          │
        │   dispute       close           │
        └────────────▲────────────────────┘
                     │ submitted by either side
                     │ at session boundaries
   off-chain  ───────┼─────────────────────────────────
                     │
                     │   x402 + TAP wire (HTTP+SSE)
        ┌────────────┴───────────┐    ┌────────────────┐
        │  Consumer SDK          │    │  Producer SDK  │
        │  • discover            │    │  • requirements│
        │  • policy.audit        │    │  • verifier    │
        │  • opener              │    │  • wrap_stream │
        │  • session_key.sign    │    │  • settle      │
        │  • batching            │    │                │
        │  • halt_detector       │    │                │
        │  • evaluators          │    │                │
        └────────────────────────┘    └────────────────┘
```

## File-to-responsibility map

| File | Single responsibility |
|---|---|
| `programs/tap/src/lib.rs` | Anchor program entrypoint; routes the four ix |
| `programs/tap/src/state/channel.rs` | `Channel` PDA layout |
| `programs/tap/src/state/commitment.rs` | Off-chain `CommitMessage` byte format |
| `programs/tap/src/instructions/open_channel.rs` | Escrow deposit, register session key |
| `programs/tap/src/instructions/settle.rs` | Verify Ed25519 sibling, split deposit, open dispute window |
| `programs/tap/src/instructions/dispute.rs` | Replace stale settle with higher-sequence commitment |
| `programs/tap/src/instructions/close.rs` | Reclaim rent after dispute window |
| `tap/protocol/commit.py` | Commitment dataclass |
| `tap/protocol/codec.py` | Canonical bytes ↔ JSON ↔ base64 codec |
| `tap/protocol/signing.py` | Ed25519 sign / verify of commitments |
| `tap/chain/pda.py` | PDA derivation (mirror of constants.rs) |
| `tap/chain/discriminator.py` | Anchor instruction discriminators |
| `tap/chain/instructions.py` | Instruction builders |
| `tap/chain/ed25519_ix.py` | Ed25519Program verify ix builder |
| `tap/chain/rpc.py` | RPC client wrapper |
| `tap/x402/headers.py` | Header name constants |
| `tap/x402/requirements.py` | `X-PAYMENT-REQUIREMENTS` codec (incl. `input_token_count`, `prepaid_input`) |
| `tap/x402/payment.py` | `X-PAYMENT` codec (incl. `prepaid_input_micro`) |
| `tap/x402/response.py` | `X-PAYMENT-RESPONSE` codec |
| `tap/tokenizer.py` | Tokenizer registry for §4.9 prompt-token quoting + §5.3.7 verification |
| `tap/timing/parameters.py` | Grace / pause / session timeouts |
| `tap/consumer/discovery.py` | x402 GET (generic) and POST (prompt-bound) → requirements parse |
| `tap/consumer/policy.py` | Audit producer terms vs. consumer policy + verify input-token count |
| `tap/consumer/session_key.py` | In-memory session keypair lifecycle |
| `tap/consumer/opener.py` | Build the open-channel transaction |
| `tap/consumer/batching.py` | AIMD adaptive K controller |
| `tap/consumer/halt.py` | Detect producer pause / halt |
| `tap/consumer/stream.py` | SSE → token stream |
| `tap/consumer/session.py` | Per-request session orchestration |
| `tap/consumer/client.py` | `TapConsumer` entry |
| `tap/producer/pricing.py` | Pricing dataclass |
| `tap/producer/channel.py` | In-memory active-channel state |
| `tap/producer/registry.py` | Active channel map |
| `tap/producer/verifier.py` | Sequence + signature checks |
| `tap/producer/halt.py` | Pause / halt detection (symmetric) |
| `tap/producer/wrap_stream.py` | Meter the model token iterator |
| `tap/producer/sse.py` | SSE encoder |
| `tap/producer/settle.py` | Build + submit settle transaction |
| `tap/producer/server.py` | FastAPI mount: GET 402 / POST stream / POST commit |
| `tap/adapters/anthropic.py` | Claude Sonnet streaming |
| `tap/adapters/openai.py` | GPT streaming |
| `tap/adapters/ollama.py` | Local Llama streaming |
| `tap/evaluators/base.py` | `Evaluator` protocol + `Decision` enum |
| `tap/evaluators/json_schema.py` | Streaming JSON schema check |
| `tap/evaluators/length_cap.py` | Halt at character budget |
| `tap/evaluators/topic_drift.py` | Token-overlap topic adherence |
| `tap/evaluators/content_policy.py` | Banned substring / regex |
| `tap/evaluators/repetition.py` | n-gram repetition guard |
| `tap/evaluators/compose.py` | OR-composition |

## Data flow for one session

1. **Prompt-bound discovery.** Consumer POSTs the prompt body (no payment)
   to `producer_url`. Producer tokenizes with its declared `tokenizer_id`
   and responds 402 with `X-PAYMENT-REQUIREMENTS` carrying
   `input_token_count` and `prepaid_input_micro = input_token_count *
   input_price_micro` (whitepaper §4.9). Consumer parses, audits via
   `ConsumerPolicy`, and re-tokenizes the same prompt locally — any
   mismatch with `input_token_count` aborts the open (whitepaper §5.3.7).
2. **Open.** Consumer generates a `SessionKey`, builds an `open_channel`
   tx (with `prepaid_input_micro` locked on-chain as the settlement floor),
   signs it with the wallet, base64-encodes, POSTs with `X-PAYMENT`.
   Producer (or its facilitator) submits to chain. Producer returns
   `X-PAYMENT-RESPONSE` with the channel PDA.
3. **Stream.** Producer streams tokens as SSE `data:` events with `ack`.
   Consumer accumulates output, runs evaluator, signs `CommitMessage`
   every K tokens with `cumulative_paid = prepaid_input + (output tokens *
   output_price)`. K floats per AIMD pressure.
4. **Halt.** Either side ceases its next move. Within the grace period the
   other side detects the silence; within the pause window it transitions
   to halted and initiates settlement.
5. **Settle.** Producer (or consumer) submits `settle` with the latest
   commitment. The on-chain Ed25519 verify happens via a sibling
   instruction; the program enforces `prepaid_input ≤ cumulative_paid ≤
   deposit`, splits the deposit, opens the dispute window.
6. **Close.** After the dispute window, either party calls `close`. Rent
   reclaimed. The expiry escape hatch always pays the producer at least
   `prepaid_input_micro` regardless of off-chain state — the consumer's
   loss on a producer that takes prefill and delivers nothing is bounded
   to exactly the input cost (whitepaper §5.3.8).

## Where state lives

* **On-chain**: deposit, last accepted commitment sequence and
  `cumulative_paid`, channel status, expiry. Authoritative.
* **Producer memory**: active-channel registry, latest signed commitment.
  Non-persistent — a producer crash forfeits up to one batch + trailing
  buffer's worth of unbilled tokens.
* **Consumer memory**: session key, accumulated output, current K.
  Non-persistent; sessions are one-shot.

## What's deferred

The whitepaper §10 future-work items are intentionally out of scope for
this implementation:

* hash-locked atomic delivery
* TEE-attested model identity
* hub-routed sessions
* decentralized facilitators
* consumer-side privacy

The shape of the SDK leaves room for each: facilitators are a single
function in `chain/rpc.py`; attestation would extend `PaymentRequirements`;
hub routing would compose `ConsumerSession`s.
