---
title: Halt and bounded loss
sidebar_position: 4
---

# Halt and bounded loss

Halt is not a special operation. It is the **absence of further commitments**.

If the consumer decides at output token 423 that the response is unacceptable
(JSON schema violated, off-topic drift detected, length budget exceeded),
they stop signing. Within the grace period the producer detects no new
commit has arrived and stops generation. The producer settles using the
most recent commit they hold, which corresponds to roughly token 423.
Both sides walk away whole; the consumer paid for what they received and
not for what would have come next.

Symmetrically, if the producer suspects the consumer is going to stop
signing — because the latest commit arrived later than expected — they
can stop generating. The consumer cannot then claim more output than
was delivered.

## Loss bounds

At any moment during a session:

| Party | Maximum loss |
| --- | --- |
| Consumer | `current_cumulative_paid + max_unpaid_micro` *(producer's published overdraw policy)* |
| Producer | `delivered_output × output_price - latest_cumulative_paid` *(bounded by the producer's own `max_unpaid` halt threshold)* |

In practice both are **a fraction of a cent** at typical configurations
(K=5 batch, $0.005 per 1k output tokens). Compared to the alternatives —
pay everything upfront and trust delivery, or pay nothing upfront and trust
post-delivery payment — TAP's exposure window is tiny and configurable.

## Three timing parameters

Halt is governed by three timing values negotiated at channel open:

* **Grace period** (default 200ms). After this duration without an
  expected next action, the party enters the *paused* state. Generation
  or signing stops; existing state is held.
* **Pause timeout** (default 5s). After this duration in the paused
  state, the session is considered *halted*. The party initiates settlement.
* **Total session timeout** (channel duration). Set at channel open.
  After this, the channel is eligible for unilateral close regardless
  of session state.

The grace period and pause timeout are independent. A consumer on a
flaky mobile connection may experience repeated short pauses (network
blips falling within the pause window), each resolving without halting;
a consumer who has actually disconnected will see the pause window
expire and the session settle.

## Halt evaluators

The consumer's halt decision is application-level. The protocol
provides the mechanism (stop signing); the policy is whatever the
consumer wires up. Common evaluators:

- **Schema validation** — halt when output deviates from a JSON schema.
- **Length cap** — halt at a configured max-token threshold.
- **Topic adherence** — halt when output drifts off-topic.
- **Repetition guard** — halt on n-gram repetition (catches degenerate
  generations).
- **Content policy** — halt on disallowed substrings or regex matches.
- **Manual halt** — a button in the chat UI.

Multiple evaluators can run in parallel; the first to return `HALT`
stops the session. See [SDK / Evaluators](/sdk/evaluators) for the API.

## Future: TEE

The protocol cannot verify that the producer used the model they
claimed, nor that the output is subjectively useful. For high-value
workloads where model substitution is a concern, attestation via
trusted execution environments (Intel SGX, AMD SEV, AWS Nitro Enclaves)
provides cryptographic assurance that a specific model binary executed
within an audited environment. v2 will specify how attestations are
exchanged at session open and how consumers verify them.
