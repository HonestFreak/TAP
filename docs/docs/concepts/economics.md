---
title: Economics
sidebar_position: 6
---

# Economics

This page derives the headline numbers used on the landing page from the
protocol's published parameters. Every figure here is **arithmetic on
configuration values** — not a measurement. We deliberately avoid
publishing measured benchmarks until the reference implementation has
been exercised against representative agent workloads on devnet under
controlled conditions; the methodology for that work is set out in
whitepaper §7.

If a stat on the landing page or in this site has a number, it should be
derivable from the equations below by plugging in the assumptions stated.

## Refund on a halted response

The single most consequential property of TAP, from a consumer's
perspective, is *how much of a rejected response gets refunded*.

**Setup.** A planned response of `N` output tokens. The consumer's
evaluator detects a violation at output token `p` and stops signing
commitments. The producer continues for at most `τ` tokens (the
trailing buffer, default 10) before halting. The producer settles
with `cumulative_paid = prepaid_input + (p + τ) × output_price`. Input
cost is pre-paid and non-refundable.

**Refund fraction (output-only):**

```
refund_pct = (N − p − τ) / N
```

The input portion is locked at channel open by design (whitepaper
§4.9), so we report output savings separately.

**Worked examples** (`τ = 10`, the default trailing buffer):

| N (planned) | p (halt point) | Refunded |
| ---: | ---: | ---: |
|   400 | 30  | 90.0% |
|   400 | 50  | 85.0% |
|   400 | 100 | 72.5% |
|   800 | 30  | 95.0% |
|   800 | 50  | **92.5%** ← landing-page stat |
|   800 | 100 | 86.2% |
|  1600 | 50  | 96.2% |
|  1600 | 100 | 93.1% |

**Why p ≈ 50 for the headline figure.** A streaming JSON-schema
evaluator detects "model emits prose instead of opening with `{`" within
the first ~30 characters of output, which is roughly 30–50 tokens
depending on the tokenizer. Topic-drift evaluators that operate over a
sliding window of accumulated tokens detect violations at p ≈ 80–150.
We pick the JSON-schema case as the headline because it is the most
adversarial-friendly evaluator — easy for a consumer to define, easy
for the model to violate, and gives a concrete halt point.

**Why N = 800.** Typical chat-agent responses from Gemini 2.5 Flash
land in the 400–1500 output-token range. 800 is a defensible midpoint;
the table above shows the figure for several N so readers can map it to
their own workload.

## Total spend reduction across a workload

If a workload has a rejection rate `f`, average response length `N`, and
average halt point `p`, the per-request average spend ratio of TAP to a
direct API is:

```
spend_ratio = (1 − f) × N + f × (p + τ)
              ──────────────────────────
                        N

spend_cut = 1 − spend_ratio
          = f × (N − p − τ) / N
          = f × refund_per_bad
```

That is: total spend reduction is the rejection rate times the per-bad
refund fraction. The refund is large; the multiplier (`f`) is what
turns it into a workload-level number.

**Examples** (`N = 800`, `τ = 10`):

| f (reject rate) | p (halt point) | Spend cut |
| ---: | ---: | ---: |
| 5%  |  50 | 4.6% |
| 5%  | 100 | 4.3% |
| 8%  |  50 | 7.4% |
| 10% |  50 | 9.3% |
| 10% | 100 | 8.6% |
| 15% |  50 | 13.9% |

We do not put a single workload number on the landing page because the
honest answer to "how much will TAP save me?" depends on three numbers
the consumer knows better than we do — their reject rate, their average
response length, and where their evaluator fires. The per-rejected-
response refund (the previous section) is invariant to those choices,
so we lead with that.

## Throughput overhead

The protocol adds three kinds of overhead to a streaming session:

1. **Channel open** — one Solana transaction, settled in ~1 slot
   (≈ 400 ms on devnet under typical conditions). Adds to
   time-to-first-token. **One-time per channel**; amortises to zero
   under channel reuse (whitepaper §4.7).
2. **Per-commit signing** — Ed25519 sign on the consumer side, verify
   on the producer side. Both are sub-100 µs operations in `nacl`.
   With adaptive batching at K = 5 (whitepaper §4.3), an 800-token
   session signs 160 commits, totalling ≈ 8 ms of sign work. **Off the
   critical path** — signing happens in parallel with token generation.
3. **Settle + close** — two transactions at session end (~800 ms
   total). **Off the critical path** for token delivery — the consumer
   already has the output before settlement starts.

**The only user-visible overhead is the channel-open round-trip** at the
start of a fresh session.

| Scenario | Streaming time @ 50 tok/s | Open overhead | % |
| --- | ---: | ---: | ---: |
| Short response (200 tok) | 4.0 s   | 0.4 s | **+10.0%** |
| Typical response (800 tok) | 16.0 s | 0.4 s | **+2.5%** |
| Long response (2000 tok) | 40.0 s  | 0.4 s | **+1.0%** |
| Reused channel, any length | n/a    | 0 s   | **0%** |

This is the payoff of channel reuse (§4.7): for a consumer that issues
many requests against the same producer, the open transaction is paid
once and the per-session overhead trends toward zero.

## On-chain cost

Per-session on-chain cost is the sum of two Solana base + priority fees:
one for `open_channel`, one for the `settle` + `close` pair. These are
small absolute amounts dominated by Solana's base fee (≈ 5,000 lamports
per signature, ~$0.0008 at SOL near $80) plus any priority fee under
load. The exact figure varies with network conditions and is best
measured rather than calculated; we report it in our benchmark output
rather than putting a fabricated number in the docs.

## What we don't claim

We deliberately don't put numbers on the landing page for:

- **Halt latency under load.** The configured grace period (default
  200 ms) is the *floor*, not the measured median. The actual median
  depends on RTT, evaluator latency, and producer scheduler behaviour.
- **Throughput vs. baseline at scale.** Headline-friendly numbers
  ("X% slower than direct API") require running real benchmarks across
  several workloads; we'd rather under-claim than mislead.
- **End-to-end TPS.** TAP doesn't change Solana's TPS budget; this is
  not a meaningful metric for a payment-channel protocol.

When we run the §7 benchmark, the measured numbers will go in the
whitepaper alongside the methodology, not as marketing copy.
