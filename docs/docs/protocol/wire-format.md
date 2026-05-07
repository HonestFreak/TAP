---
title: Wire format
sidebar_position: 2
---

# Wire format

All payloads are JSON, base64-encoded for transport in HTTP headers.

## `X-PAYMENT-REQUIREMENTS`

Returned by the producer in 402 responses. Both the generic GET and
the prompt-bound POST use this format.

```json
{
  "scheme":  "tap.v1.channel",
  "network": "solana-devnet",
  "asset":   "<USDC mint>",
  "recipient": "<channel program id>",
  "extra": {
    "producer_pubkey":     "<base58>",
    "input_price":         1,
    "output_price":        5,
    "tokenizer_id":        "tap.tok.v1",
    "input_token_count":   16,
    "prepaid_input":       16,
    "max_unpaid":          5000,
    "trailing_buffer":     10,
    "duration_secs":       300,
    "dispute_secs":        30,
    "grace_ms":            200,
    "pause_timeout_ms":    30000,
    "channel_open_url":    "https://provider/v1/messages",
    "stream_url":          "https://provider/v1/messages",
    "model":               "gemini-2.5-flash"
  }
}
```

`input_token_count` and `prepaid_input` are 0 in the generic GET
response (no prompt to tokenize); they are populated in the
prompt-bound POST response.

## `X-PAYMENT`

Sent by the consumer to open the channel.

```json
{
  "scheme":  "tap.v1.channel",
  "network": "solana-devnet",
  "extra": {
    "consumer_pubkey":       "<base58>",
    "session_key":           "<base58>",
    "nonce":                 12345,
    "deposit_micro":         50000,
    "input_price_micro":     1,
    "output_price_micro":    5,
    "prepaid_input_micro":   16,
    "duration_secs":         300,
    "dispute_secs":          30,
    "trailing_buffer_tokens": 10,
    "transaction":           "<base64-encoded signed Solana tx>"
  }
}
```

## `X-PAYMENT-RESPONSE`

Returned by the producer once the channel-open transaction confirms.

```json
{
  "tx_hash":    "<base58>",
  "settlement": "confirmed",
  "extra": {
    "channel_id":    "<base58 PDA>",
    "channel_state": "active"
  }
}
```

## `X-TAP-COMMIT`

Sent by the consumer every K tokens. **Distinct from `X-PAYMENT`** because
in-session commits are signaling, not payment instructions; an x402
facilitator must not settle them.

```json
{
  "schema":          "tap.v1.commit",
  "channel_id":      "<base58>",
  "sequence":        42,
  "cumulative_paid": 1234567,
  "tokens_received": 12345,
  "timestamp_ms":    1700000000000,
  "signature":       "<base64 Ed25519 signature>"
}
```

## Signature canonical form

The signed bytes (60 bytes total, little-endian, no padding):

```
[0..32)   channel pubkey
[32..40)  sequence (u64 LE)
[40..48)  cumulative_paid (u64 LE)
[48..52)  tokens_received (u32 LE)
[52..60)  timestamp_ms (u64 LE)
```

This layout is the source of truth for both the on-chain Rust
verifier (`programs/tap/src/state/commitment.rs::message_bytes`) and
the Python signer (`tap.protocol.codec.encode_commitment_bytes`).
A codec parity test in `sdk/python/tests/test_codec_parity.py`
guards against drift.

## Streaming SSE

Producer responses use Server-Sent Events. Each frame is one token
or token batch:

```
data: {"text":"Hello","ack":0}

data: {"text":" world","ack":1}

data: [DONE]
```

`ack` is the latest commit sequence the producer has accepted. The
consumer uses it to verify the producer has registered their
progress.
