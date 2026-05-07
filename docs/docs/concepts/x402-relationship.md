---
title: Relationship to x402
sidebar_position: 5
---

# Relationship to x402

TAP is built **on top of** [x402](https://x402.org), not alongside it.

x402 is the HTTP-native payment standard Coinbase released in 2025. It
defines how a client requests a paid resource, the server responds with
HTTP 402 + a structured payment-requirements payload, and the client
retries with a signed payment instruction in `X-PAYMENT`. The standard
handles **fixed-price one-shot payments** cleanly.

The x402 v2 specification explicitly defers two scenarios to future work:

1. **Variable-cost responses**, where the price depends on the work performed.
2. **Streaming responses**, where value flows continuously across the response.

These are precisely the scenarios LLM inference inhabits. TAP fills
this gap.

## What TAP reuses from x402

| Layer | Mechanism |
| --- | --- |
| **Discovery** | Standard `X-PAYMENT-REQUIREMENTS` 402 response. Any x402-aware client finds TAP producers without specialised discovery code. |
| **Channel bootstrap** | The `open_channel` Solana transaction is itself an x402 payment — a one-shot payment to a special endpoint. The consumer's funding tx travels in `X-PAYMENT`; the producer/facilitator submits it; settlement comes back in `X-PAYMENT-RESPONSE`. |
| **Settlement infrastructure** | When a TAP session closes, the on-chain settlement transaction can be submitted through the same facilitator pattern x402 uses, allowing producers to delegate Solana transaction submission to existing infrastructure. |

## What TAP adds

| Layer | Mechanism |
| --- | --- |
| **Streaming commitments** | `X-TAP-COMMIT` header carries one signed commitment per K tokens. Distinct from `X-PAYMENT` because in-session commits are *signaling*, not payment instructions; an x402 facilitator MUST NOT settle them. |
| **Halt detection** | Off-chain timing-based pause/halt logic (`grace_ms` / `pause_timeout_ms`). Both sides run symmetric detectors; no explicit halt message exchanged. |
| **Settlement bounds** | The on-chain Anchor program enforces `prepaid_input ≤ cumulative_paid ≤ deposit` and the dispute-window state machine. |

## What this composition gives you

* Consumers that already speak x402 can consume TAP services with
  minimal changes — they parse a few extra fields from the
  payment-requirements payload and add a streaming-commit loop.
* Producers running on x402 facilitators can offer TAP streaming
  without changing their settlement infrastructure.

The protocols compose cleanly at the application layer with no overlap
and no contradiction.

## Wire-level cheat sheet

```http
# 1. Generic discovery (no prompt yet)
GET /v1/messages
→ 402 Payment Required
  X-PAYMENT-REQUIREMENTS: <base64>

# 2. Prompt-bound quote (whitepaper §4.9)
POST /v1/messages
  Content-Type: application/json
  {"messages": [...]}
→ 402 Payment Required
  X-PAYMENT-REQUIREMENTS: <base64>
    extra: {input_token_count: 16, prepaid_input: 16, ...}

# 3. Channel open
POST /v1/messages
  X-PAYMENT: <base64-encoded signed Solana tx>
→ 200 OK
  X-PAYMENT-RESPONSE: <base64>
    extra: {channel_id: "...", channel_state: "active"}

# 4. Stream tokens
POST /v1/messages
  X-TAP-CHANNEL: <channel pda>
  {"messages": [...]}
→ 200 OK, Content-Type: text/event-stream
  data: {"text": "Hello", "ack": 0}
  data: {"text": " world", "ack": 1}
  data: [DONE]

# 5. Send commit (every K tokens, on a side connection)
POST /v1/messages/commit
  X-TAP-CHANNEL: <channel pda>
  X-TAP-COMMIT: <base64-encoded signed CommitMessage>
→ 204 No Content
```
