---
title: Trust model
sidebar_position: 3
---

# Trust model

TAP provides **bounded-loss guarantees**, not unconditional fair exchange.

## What the protocol guarantees

* The **consumer** cannot lose more than `current_cumulative_paid +
  max_unpaid_micro` at any moment in the session, regardless of producer
  behaviour. If the producer disappears, takes payment without
  delivering, or delivers garbage, the consumer's loss is bounded by
  what they have already authorized plus the producer's published
  overdraw policy.

* The **producer** cannot lose more than `delivered_output_tokens ×
  output_price - latest_cumulative_paid` at any moment. If the consumer
  stops signing, refuses to settle, or attempts to claim more than they
  paid, the producer's loss is bounded by tokens delivered past the
  latest commit, capped by the producer's own halt threshold (typically
  `max_unpaid` ÷ `output_price` tokens).

* Neither party can be forced to extend the session. Either party halts
  by ceasing their next action.

These hold under standard cryptographic assumptions (Ed25519
unforgeability, SHA-256 collision resistance) and the assumption that
Solana eventually permits transaction submission.

## What the protocol does *not* guarantee

* **Output quality.** A producer can commit to and deliver 1,000 tokens
  of grammatical garbage; the protocol will pay for them. Quality is
  the responsibility of the consumer's [evaluator](/sdk/evaluators)
  and of the producer's reputation, not the cryptographic protocol.

* **Model honesty.** The protocol cannot verify that the producer used
  the model they claimed. Mitigations include trusted execution
  environments (TEE attestation) and reputation; out of scope for v1.

* **Privacy.** Channel openings and settlements are visible on-chain.
  In-session commits are peer-to-peer but not encrypted. TAP is not a
  privacy-preserving protocol.

## Adversarial scenarios

### Consumer consumes without paying

Receives some tokens, then stops signing. The producer detects within
the grace period and halts generation. The consumer has paid for the
tokens received plus a small overdraw bound by `max_unpaid`. **Not
profitable.**

### Producer charges without delivering

Sends nothing or sends garbage tokens. The consumer's evaluator detects
and stops signing. The producer can only settle with the latest commit
held, which corresponds to the last useful tokens delivered. The
producer's prefill cost is still covered by `prepaid_input` — that's
the residual case below.

### Stale settlement

Either side initiates settlement with an older commit, hoping the
counterparty doesn't contest in time. The other party detects via
on-chain monitoring during the dispute window and submits a
higher-sequence commit, which supersedes.

### Producer accepts prepaid input and delivers no output

The whitepaper's [§5.3.8](/whitepaper) residual risk. Bounded by the
input cost (no exposure on the output budget). Mitigations:

* `max_time_to_first_token` SLA in producer metadata; consumers treat
  violation as a halt trigger and surface it to reputation
  infrastructure.
* Statistical detection — a producer with anomalous input-only
  settlement rate is identifiable.
* TEE attestation closes the residual risk cryptographically (deferred
  to v2).

### Input inflation

The producer reports `input_token_count` larger than the prompt
actually tokenizes to. The consumer's SDK runs the same tokenizer
locally and detects the discrepancy.

```python
# tap/consumer/policy.py
local = tokenizer.count(req.tokenizer_id, prompt_text)
if local != req.input_token_count:
    raise X402Error("input_token_count mismatch")
```

Tokenizers are deterministic, so honest disagreement is impossible —
any mismatch implies misbehaviour. The consumer aborts the
channel-open transaction; no on-chain state is created and no payment
flows. **Not profitable.**

### Token padding

A malicious producer pads responses with whitespace, repeated tokens,
or low-information content to maximize charged tokens. The protocol
does not solve this cryptographically. Mitigations:

* Consumer-side `repetition_guard` evaluator detects high-frequency
  repetition.
* Reputation systems penalize statistical anomalies.
* For high-value workloads, attested execution provides cryptographic
  assurance of model identity.

### Network partition mid-session

Network drops between consumer and producer. Producer settles using
the last commit received. The producer eats up to `trailing_buffer ×
output_price` of unbilled tokens (the overdraw they were willing to
absorb between commits). Consumer pays only what they signed. Both
end whole within the buffer's bounds; no dispute required.

## Comparison

| Model | Consumer trusts producer for... | Producer trusts consumer for... |
| --- | --- | --- |
| Pre-paid API (current) | Full request value, every request | Nothing |
| Post-paid invoice (enterprise) | Nothing | Full monthly bill, with collections recourse |
| x402 fixed-price one-shot | Full request value | Nothing |
| **TAP** | **`prepaid_input` + 1 batch (sub-cent of output)** | **1 batch (sub-cent)** |

TAP's contribution is not unconditional safety — that's impossible
without a trusted third party — but a **structural reduction** in the
trust window from "full request value" to "a few tokens of inference
cost".
