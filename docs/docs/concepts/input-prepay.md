---
title: Input pre-pay model
sidebar_position: 3
---

# Input pre-pay model

LLM inference has two cost components: **prefill** (the producer runs the
model over the entire input prompt) and **decode** (the producer generates
output tokens one by one). Prefill is **irreversible** — once the
producer starts it, the compute is spent. Decode can be halted at any
token boundary.

TAP's pricing model reflects this asymmetry:

| | Input | Output |
| --- | --- | --- |
| Charged | Once, at channel open | Per token, as it streams |
| Reversible | No (prefill is sunk cost) | Yes (consumer can halt) |
| On-chain bound | Settlement *floor* (`prepaid_input ≤ cumulative_paid`) | Settlement *ceiling* (`cumulative_paid ≤ deposit`) |
| Typical price ratio | 1× | 3–5× |

## How the floor works

At channel open the consumer's transaction carries a `prepaid_input_micro`
field equal to `input_token_count × input_price_micro`. The on-chain
program records it on the channel PDA. From that point:

- `settle` and `dispute` reject any commit with `cumulative_paid <
  prepaid_input_micro` (`CommitmentBelowPrepaidInput` error).
- `close` (whether after `settle` or via the consumer's escape hatch on
  channel expiry) pays out **at least** `prepaid_input_micro` to the
  producer, regardless of off-chain commitment state.

The first signed commitment in the session has `cumulative_paid ≥
prepaid_input` by construction; subsequent commitments accumulate
output cost on top.

## Why this design

Without `prepaid_input`, a malicious consumer could:

1. Submit a long, expensive prompt
2. Receive prefill (which the producer has already spent compute on)
3. Refuse to sign any commitments
4. Walk away while the producer ate the prefill cost

With `prepaid_input` locked at open, this attack is closed: the producer
is guaranteed payment for the prefill they're about to run, **before**
they run it.

The reciprocal attack (producer inflates `input_token_count` to overcharge)
is closed by [§5.3.7 input verification](/protocol/trust-model):
the consumer re-tokenizes locally and aborts on mismatch.

## What's *not* closed

A producer that takes `prepaid_input` and then never delivers any output
extracts up to the prepaid amount. The protocol bounds this loss to
exactly the input cost (no exposure on the output budget) and surfaces
it via:

- A `max_time_to_first_token` SLA in the producer's published metadata.
- Statistical detection (a producer whose input-only-settlement rate is
  anomalous is identifiable to registries and clients).
- Future [TEE-attested execution](/concepts/halt-and-bounded-loss)
  closes the residual risk cryptographically.

The protocol's honesty about this scope cut is the design choice.
Pretending otherwise would understate the asymmetry that any
non-attested streaming payment system inherits.
