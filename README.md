# TAP — Token Access Protocol

Token-by-token payments for LLM inference, with bilateral halt for fair,
low-waste generation. Built on Solana state channels and the x402 HTTP
payment standard.

> *Hackathon entry — Solana Frontier 2026.*
> Specification: [TAP Whitepaper (PDF)](./TAP_Whitepaper.pdf)
> Docs site (landing + docs): `cd docs && npm install && npm start` — see [`docs/`](./docs)

## What this is

Pay for an LLM response one token at a time, with the asymmetric input/output
cost LLMs actually have. Either side can halt at any output-token boundary; the
on-chain settlement only ever touches the bytes the consumer actually accepted.

* **Input is prepaid at channel open.** The producer tokenizes the prompt with
  a declared tokenizer, the consumer re-tokenizes locally to verify, and the
  resulting `prepaid_input` is locked on-chain as the settlement floor — so the
  producer's prefill compute is non-refundable but bounded (whitepaper §4.9).
* **Output is paid token-by-token.** Each commitment the consumer signs has
  `cumulative_paid = prepaid_input + (output tokens × output_price)`.
* **Consumer halts** when the model goes off-topic, breaks a JSON schema,
  exceeds a length budget, or any custom evaluator says stop.
* **Producer halts** when the consumer stops signing commitments.
* **Maximum loss for either side** mid-stream is bounded by a small
  configurable batch — typically a fraction of a cent of output cost.

## Why now

Today's LLM APIs are pay-after-delivery: you are billed for every token
the model produces, including the ones you discard. In agentic workflows
some fraction of responses come back unusable, and the failure is often
visible mid-stream — but you've already paid for the tokens that revealed
it. As an illustrative back-of-the-envelope, a workflow making 1,000
calls/day at $0.02/response with a 5% reject rate wastes $10/day, before
counting the cost of any retries; the structural fact that matters is the
inability to halt at the moment of detection, not any specific dollar
figure. TAP halts generation when the consumer's evaluator says stop and
refunds the unused deposit on-chain.

## Architecture

```
┌────────────────┐     x402 (open channel)      ┌────────────────┐
│                │ ──────────────────────────►  │                │
│   Consumer     │                              │   Producer     │
│   (TapConsumer) │ ◄───────────────────────── │   (TapProducer)│
│                │     HTTP 402 + requirements  │                │
│                │                              │                │
│                │ ──── POST /messages (body) ► │   wraps        │
│                │                              │   Gemini       │
│                │ ◄ HTTP 402 + prompt-bound  ─ │   (Anthropic / │
│                │   input_token_count / quote  │    OpenAI /    │
│                │                              │    Ollama      │
│                │ ─ POST X-PAYMENT (open) ──►  │    scaffolded) │
│                │ ◄─── SSE: tokens + acks ───  │                │
│                │ ──── X-TAP-COMMIT (×N) ───►  │                │
│                │      (signed by session key) │                │
└───────┬────────┘                              └────────┬───────┘
        │                                                │
        │   Solana state channel (USDC escrow PDA)       │
        │   ──────  open_channel  ──────────────────►    │
        │   ◄─── settle (latest commitment) ────         │
        │   ──────  dispute (if stale)  ────────►        │
        │   ──────  close (after window)  ──────►        │
        ▼                                                ▼
              tap on-chain program (Anchor)
```

## Repository layout

```
tap/
├── programs/tap/             # Anchor program (Rust) — on-chain settlement
│   └── src/
│       ├── lib.rs
│       ├── constants.rs · errors.rs · events.rs
│       ├── state/        {channel,commitment}.rs
│       └── instructions/ {open_channel,settle,dispute,close}.rs
│
├── sdk/python/tap/           # Python SDK (`pip install -e sdk/python`)
│   ├── protocol/             # commit schema, codec, Ed25519 signing
│   ├── chain/                # PDA derivation, instruction builders, RPC
│   ├── x402/                 # x402 wire format (requirements, payment, response)
│   ├── consumer/             # TapConsumer + session orchestration + adaptive batching
│   ├── producer/             # TapProducer + verifier + settlement + auto-close settler
│   ├── adapters/             # Gemini (live) · Anthropic / OpenAI / Ollama (scaffolded)
│   ├── evaluators/           # JSON schema, length, topic, repetition, content policy
│   ├── tokenizer.py          # tokenizer registry for §4.9 prompt-token quoting
│   └── timing/               # grace / pause / total-session timeouts
│
├── sdk/typescript/           # TypeScript consumer SDK (Node 20+ / Bun / Deno / browser)
│   └── src/                  # protocol · x402 · chain · consumer — wire-format parity
│                             #   with Python is verified against fixtures
│
├── demo/                     # Reference end-to-end demo
│   ├── producer.py           # FastAPI producer (Gemini-backed)
│   ├── runner.py             # FastAPI backend that drives TapConsumer for the React UI
│   ├── consumer.py           # CLI consumer (one streaming request)
│   ├── dashboard.py          # Real-time terminal dashboard
│   └── frontend/             # Vite + React + TypeScript dashboard
│
├── docs/                     # Docusaurus site — landing page + protocol docs
│   ├── docs/                 # markdown content (concepts, protocol, SDK, demo, beyond-LLM)
│   ├── src/                  # landing page components
│   ├── static/               # served verbatim (incl. whitepaper PDF)
│   └── docusaurus.config.ts
│
├── tests/                    # Anchor TS tests
├── TAP_Whitepaper.pdf        # Canonical specification
├── TAP_Whitepaper.txt        # Plain-text source of the whitepaper
├── Anchor.toml · Cargo.toml  # Workspace config
└── README.md · LICENSE
```

The codebase is organised one-task-per-file. Single responsibility was the
top priority during construction; the file count is intentional.

## Hackathon side tracks

The whitepaper specifies LLM inference as the primary application; the
protocol primitives generalize cleanly. Tracks the project naturally fits:

* **AI track** — token-priced inference is the canonical use case.
* **Payments track** — a state-channel payments protocol that composes
  on top of x402 rather than competing with it; v1 specifies the wire
  format compatibility points (whitepaper §3.3, §B.1).
* **DePIN** — decentralised inference networks need fair per-request
  settlement; TAP provides a payment rail without a centralised billing
  service.
* **Consumer** — chat UIs get a real "stop" button that actually stops
  the meter on-chain, not just the visible tokens.

See whitepaper §9 for the audio / video / GPU-rental / metered-API
generalisations the same channel construction supports.

## Running it

### Anchor program

```bash
anchor build
anchor deploy --provider.cluster devnet
anchor test
```

### Python SDK

```bash
cd sdk/python
pip install -e '.[anthropic]'
pytest
```

### TypeScript SDK (consumer only)

```bash
cd sdk/typescript
npm install
npm run build
npm test
```

See [`sdk/typescript/README.md`](./sdk/typescript/README.md) and the
[TypeScript SDK docs page](./docs/docs/sdk/typescript.md) for usage.

### Demo

```bash
export GEMINI_API_KEY=...
export TAP_PRODUCER_KEYPAIR=~/.config/solana/producer.json
export TAP_CONSUMER_KEYPAIR=~/.config/solana/consumer.json
export TAP_PRODUCER_PUBKEY=$(solana-keygen pubkey "$TAP_PRODUCER_KEYPAIR")
export TAP_PRODUCER_USDC=<producer USDC ATA on devnet>
export TAP_RPC=https://api.devnet.solana.com

# Terminal 1 — producer
uvicorn demo.producer:app --host 0.0.0.0 --port 8000

# Terminal 2 — consumer runner backend
uvicorn demo.runner:app --port 8001

# Terminal 3 — React dashboard
(cd demo/frontend && npm install && npm run dev)
```

Open `http://localhost:5173`. Toggle "Enforce JSON schema" on, ask for
prose, and watch the evaluator halt mid-stream and the unspent deposit
refund on close. See [`demo/README.md`](./demo/README.md) for details.

### Docs site

```bash
cd docs
npm install
npm run start    # http://localhost:3000
```

## License

MIT.
