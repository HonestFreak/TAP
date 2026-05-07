---
title: Installing the SDK
sidebar_position: 1
---

# Installing the SDK

The TAP Python SDK lives at `sdk/python/` in the repo. Install it
editable:

```bash
git clone https://github.com/your-org/tap
cd sol
pip install -e sdk/python
```

Optional model adapters are extras:

```bash
pip install -e 'sdk/python[anthropic]'   # Claude
pip install -e 'sdk/python[openai]'      # GPT-4o family
pip install -e 'sdk/python[ollama]'      # Local Llama via Ollama
# Gemini works out of the box with httpx — no extra install required.
```

## Public surface

```python
from tap import (
    TapConsumer, ConsumerSession,    # consumer client + per-session iterator
    TapProducer,                     # producer host
    Decision, Evaluator,             # halt-on-evaluator types
    compose, content_policy,         # standard-library evaluators
    json_schema, length_cap, topic_drift,
    tokenizer,                       # process-local tokenizer registry
)
```

Lower-level layers — exposed for custom integrations:

| Module | Purpose | Guide |
| --- | --- | --- |
| `tap.consumer.policy.ConsumerPolicy` | Audit producer terms before escrow | [Consumer](/sdk/consumer) |
| `tap.consumer.session.TokenChunk` / `CommitSigned` | Streaming + observability events | [Consumer](/sdk/consumer) |
| `tap.producer.pricing.Pricing` | Producer price + tokenizer config | [Producer](/sdk/producer) |
| `tap.producer.channel.ActiveChannel` | Per-session producer state | [Producer](/sdk/producer) |
| `tap.timing.parameters.TimingParameters` | grace / pause / total timeouts | [Consumer](/sdk/consumer#timing) |
| `tap.protocol.commit.CommitMessage` / `SignedCommitment` | Off-chain commitment types | [Consumer](/sdk/consumer) |
| `tap.protocol.codec` | Commit encode/decode (mirrors on-chain layout) | [Wire format](/protocol/wire-format) |
| `tap.protocol.signing` | Ed25519 commit signing | [Wire format](/protocol/wire-format) |
| `tap.x402.*` | x402 wire-format codecs | [x402](/sdk/x402) |
| `tap.chain.instructions` | `open_channel` / `settle` / `dispute` / `close` builders | [On-chain](/protocol/on-chain) |
| `tap.chain.pda` | Channel + vault PDA derivation | [On-chain](/protocol/on-chain) |
| `tap.chain.rpc.ChainClient` | Thin async-RPC convenience wrapper | — |
| `tap.evaluators.*` | JSON schema, length, topic, repetition, content policy | [Evaluators](/sdk/evaluators) |
| `tap.adapters.*` | Anthropic / OpenAI / Gemini / Ollama wrappers | [Producer](/sdk/producer#adapters) |

## Exceptions

Every SDK error subclasses `tap.exceptions.TapError`, so applications
can catch protocol failures without trapping unrelated network or
wallet errors.

| Exception | Raised when |
| --- | --- |
| `TapError` | Base class — catch this to handle any TAP failure |
| `X402Error` | Bad / missing fields in `X-PAYMENT-REQUIREMENTS`, `X-PAYMENT`, or `X-PAYMENT-RESPONSE`; producer terms violate the consumer's `ConsumerPolicy`; tokenizer mismatch on the §5.3.7 check |
| `ProtocolError` | Wire-format or schema violation in a commit, SSE frame, or codec |
| `CommitmentError` | Commit fails sequence / monotonicity / signature validation |
| `HaltError` | Counterparty stops responding past the configured pause window |
| `SettlementError` | On-chain `settle` / `close` returned an unexpected state |
| `ChannelStateError` | Operation requested on a channel in the wrong lifecycle state |

## System requirements

- Python 3.12+ (uses `slots=True` dataclasses extensively)
- A Solana keypair with USDC and SOL on the target cluster
- For the demo: a Gemini API key (or wire your own model adapter)

## Verifying the install

```bash
python3 -c "from tap import TapConsumer, TapProducer, tokenizer; print(tokenizer.is_registered('tap.tok.v1'))"
# True
```

## Tests

```bash
cd sdk/python
pytest tests/test_codec_parity.py tests/test_pda_parity.py tests/test_x402_codecs.py tests/test_tokenizer.py
```
