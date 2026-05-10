# TAP Demo Frontend

Vite + React + TypeScript dashboard for the TAP demo. Streams a token-by-token
LLM response, shows the live cost meter, and renders the channel lifecycle
(open → commitments → settle → close) with Solscan links for every on-chain
action.

```
demo/frontend/
├── src/
│   ├── App.tsx                  # top-level layout, owns session state
│   ├── lib/
│   │   ├── api.ts               # REST + SSE client (calls /api/* on the runner)
│   │   ├── format.ts            # USDC / address / Solscan formatters
│   │   └── types.ts             # SSE event union mirroring runner.py
│   ├── hooks/
│   │   └── useTapSession.ts     # session reducer wired to runSession()
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── PromptForm.tsx       # prompt + deposit + schema toggle
│   │   ├── OutputPanel.tsx      # live token stream
│   │   ├── MeterPanel.tsx       # tokens, paid, refundable, halt status
│   │   ├── TimelinePanel.tsx    # channel-open + commitment timeline
│   │   ├── ExplorerPanel.tsx    # polls /api/sessions/.../signatures; Solscan links
│   │   ├── BalancePanel.tsx     # consumer / producer USDC balances
│   │   └── ui/                  # Pill, Stat, Hash primitives
│   ├── index.css                # Tailwind v4 + theme tokens
│   └── main.tsx
└── vite.config.ts               # /api proxy → http://localhost:8001
```

## Architecture

```
[Browser]  ──fetch SSE──▶  [demo/runner.py (FastAPI)]  ──TAP/x402──▶  [demo/producer.py]
                                       │
                                       └──▶  TapConsumer SDK ──▶  Solana devnet
```

The browser never touches Solana directly. The Python runner wraps the
existing `TapConsumer` SDK (signing, RPC, x402) and pushes one SSE event per
state transition: `phase`, `session_open`, `token`, `commit_signed`,
`complete`, `error`. The frontend reduces those into the panels.

## Run the demo

In three terminals, from the repo root:

```bash
# 1. Producer (Gemini-backed)
export GEMINI_API_KEY=...
export TAP_PRODUCER_KEYPAIR=~/.config/solana/producer.json
export TAP_PRODUCER_USDC=9W5hHPgmLu8Qh9bjsmedXKHs78CAtwojXWe3WyVVaVUC
uvicorn demo.producer:app --port 8000

# 2. Runner (frontend's backend)
export TAP_CONSUMER_KEYPAIR=~/.config/solana/consumer.json
export TAP_PRODUCER_PUBKEY=AVFkpQTxiQx1sJSoMYJ6jZ6sQHKs1jTe4pioTPnpCg6M
export TAP_PRODUCER_USDC=9W5hHPgmLu8Qh9bjsmedXKHs78CAtwojXWe3WyVVaVUC
uvicorn demo.runner:app --port 8001

# 3. Frontend
cd demo/frontend
npm install
npm run dev   # → http://localhost:5173
```

The "Halt-trigger prompt" preset asks Gemini for prose; with the JSON-schema
evaluator on, the stream halts mid-response and the unspent deposit refunds
on close. The "Schema-respecting prompt" runs to completion.
