# TAP Reference Demo

End-to-end demo of the protocol: producer wraps Gemini 2.5 Flash, consumer
streams output through the TAP SDK, evaluator halts on JSON-schema
violation, on-chain settlement refunds the unused deposit.

```
demo/
├── README.md
├── producer.py     # FastAPI producer (Gemini-backed) — uvicorn entry
├── runner.py       # HTTP/SSE backend that drives TapConsumer for the React UI
├── consumer.py     # CLI consumer that issues a single streaming request
├── dashboard.py    # Real-time terminal dashboard (alternative to the React UI)
└── frontend/       # Vite + React + TypeScript dashboard
```

## Quick start

```bash
# 0. Install
pip install -e sdk/python
(cd demo/frontend && npm install)

# 1. Set keys + accounts
export GEMINI_API_KEY=...
export TAP_PRODUCER_KEYPAIR=~/.config/solana/producer.json
export TAP_PRODUCER_USDC=<producer USDC ATA on devnet>
export TAP_CONSUMER_KEYPAIR=~/.config/solana/consumer.json
export TAP_PRODUCER_PUBKEY=$(solana-keygen pubkey "$TAP_PRODUCER_KEYPAIR")
export TAP_RPC=https://api.devnet.solana.com

# 2. Run the producer
uvicorn demo.producer:app --host 0.0.0.0 --port 8000

# 3a. (React UI) start the runner backend + frontend in two more terminals
uvicorn demo.runner:app --port 8001
(cd demo/frontend && npm run dev)

# 3b. (Terminal alternative) one-shot consumer + dashboard
python demo/dashboard.py
```

Open `http://localhost:5173` for the React dashboard. Toggle "Enforce JSON
schema" on, ask for prose, and watch the evaluator halt mid-stream and
the unspent deposit refund on close.

## What you see

* **Token stream** — accumulating output, token by token.
* **Cost meter** — `cumulative_paid` ticking up; the prepaid-input floor
  shown separately so you can see the §4.9 split clearly.
* **Commit timeline** — every signed `X-TAP-COMMIT` as a timeline event.
* **Halt event** — the evaluator name that triggered, and the cumulative
  paid at the moment of halt.
* **On-chain transactions** — Solscan links for `open_channel`, `settle`,
  and `close` as they confirm.
