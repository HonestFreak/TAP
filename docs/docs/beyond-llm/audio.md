---
title: Audio streaming
sidebar_position: 3
---

# Audio streaming

Audio breaks into two subtypes that map to TAP differently:

1. **Generated audio** (text-to-speech, on-the-fly music synthesis) —
   this is structurally identical to LLM inference. The producer
   generates output as the consumer is paying for it; halt-on-quality
   makes sense; per-second metering aligns with the unit of value.
2. **Catalog audio** (music streaming, podcasts) — the
   platform-aggregator pattern from [Video](/beyond-llm/video) applies.
   Don't put the meter in front of the listener.

## Generated audio (TTS, music synthesis)

The session shape is unchanged from the LLM mapping. What differs is
the quality signal:

| LLM session | Generated-audio session |
| --- | --- |
| `output_token` | `output_second` (or `output_chunk`) |
| `repetition_guard` | encoder-error / silence-detection evaluator |
| `json_schema` | format-conformance evaluator (sample rate, channels) |
| `topic_drift` | spoken-content drift (semantic check on transcript) |

The producer's `tokenizer_id` becomes a `chunk_unit_id` declaring
what the per-second unit means (e.g. `pcm-s16le-22050`). The
consumer can sanity-check incoming chunks against this declaration
and halt on encoding violation just as the LLM consumer halts on JSON
violation.

A useful concrete evaluator for TTS:

```python
def silence_guard(*, max_silent_seconds: int = 3) -> Evaluator:
    """Halt if more than max_silent_seconds of silence appear in the
    accumulated waveform. Catches the most common TTS failure mode —
    the model hung mid-sentence and is producing zeros."""
    # accumulated buffer; check trailing window for RMS below floor
    ...
```

## Catalog audio (Spotify-shaped products)

Same lessons as video:

* Listeners should not see a per-second meter.
* The platform plays consumer; the producer (artist, podcast host)
  plays producer.
* Settle in a platform-issued token whose redemption value is a
  function of monthly revenue.

The streaming math is even simpler than video — there is no quality
halt to speak of in catalog audio. The platform's per-second
commitment is the entire mechanism: it accrues during play, signs
periodic commits, settles at month-end. Producers see exactly how
many seconds of their work were played, with on-chain receipts.

## A specific product idea: split-track streaming

One area where per-second TAP commitments *can* be exposed to end-users
without breaking UX is interactive remixing — apps where a listener
loads multiple tracks and pays per-second only for the stems actually
audible at any moment. The cognitive overhead of "is this stem worth
paying for" is already part of the creative interaction; the meter is
a feature, not friction. Per-stem channels with bilateral halt
straightforwardly enable this.
