---
title: Running the demo
sidebar_position: 1
---

# Running the demo

The reference demo wraps Gemini 2.5 Flash with TAP and renders a live
React dashboard while a session streams. End-to-end you'll see:
token-by-token cost accrual, signed commitments arriving, an evaluator
trigger, and an on-chain refund of the unused deposit.

## Prerequisites

- Solana CLI, with `~/.config/solana/id.json` funded on devnet.
- Two additional keypairs for producer + consumer at
  `~/.config/solana/{producer,consumer}.json`, both holding USDC on
  devnet (faucet: [https://faucet.circle.com](https://faucet.circle.com)).
- Gemini API key — set `GEMINI_API_KEY=...`.
- Anchor 0.32+, Node 20+, Python 3.12+.

## One-time setup

```bash
git clone https://github.com/your-org/tap
cd tap

# Python SDK
pip install -e sdk/python
pip install -r demo/requirements.txt   # uvicorn, fastapi, httpx

# Frontend
(cd demo/frontend && npm install)

# Anchor program — already deployed to devnet at
# 2tqofcitv1LHFGCLCmR9Kyke6TmArQwpHSinWWtmCje9.
# To redeploy a local build: anchor deploy --provider.cluster devnet
```

## Wire up the env

```bash
export GEMINI_API_KEY=...
export TAP_PRODUCER_KEYPAIR=~/.config/solana/producer.json
export TAP_CONSUMER_KEYPAIR=~/.config/solana/consumer.json
export TAP_PRODUCER_PUBKEY=$(solana-keygen pubkey ~/.config/solana/producer.json)
export TAP_PRODUCER_USDC=$(spl-token address --token <USDC_MINT> --owner $TAP_PRODUCER_PUBKEY --verbose | grep "Associated Token Address" | awk '{print $NF}')
export TAP_RPC=https://api.devnet.solana.com
export TAP_NETWORK=solana-devnet
```

## Run

Three terminals:

```bash
# Terminal 1 — producer (FastAPI on :8000)
uvicorn demo.producer:app --host 0.0.0.0 --port 8000

# Terminal 2 — consumer runner backend (FastAPI on :8001)
uvicorn demo.runner:app --port 8001

# Terminal 3 — React dashboard (Vite on :5173)
cd demo/frontend && npm run dev
```

Open `http://localhost:5173`. Type a prompt, click *Run*, watch the
meter tick up token-by-token. Toggle "Enforce JSON schema" off and
ask for prose to see the no-halt path; toggle it on and watch the
evaluator halt mid-stream.

## What's happening under the hood

1. The frontend POSTs `{prompt, deposit_micro, enforce_schema}` to
   `runner.py`.
2. `runner.py` calls `TapConsumer.open_session(...)`:
   - POST the prompt to `producer.py` (no payment) → 402 with
     `prepaid_input` quote.
   - Re-tokenize locally; verify match.
   - Build + sign `open_channel` Solana tx; submit via x402.
3. The producer wraps Gemini's output stream with `TapProducer`'s
   meter and emits SSE.
4. `TapConsumer` signs commits every K tokens; the React side
   renders each as a timeline event.
5. When the evaluator halts (or the stream completes), the producer
   submits `settle` on-chain. After the dispute window, `close`
   moves USDC.

## Quick smoke test (no chain involvement)

To verify the wire format without funding accounts:

```bash
# Boot just the producer
GEMINI_API_KEY=placeholder \
  TAP_PRODUCER_KEYPAIR=~/.config/solana/producer.json \
  TAP_PRODUCER_USDC=<any base58 pubkey> \
  uvicorn demo.producer:app --port 8000

# In another shell — hit the prompt-bound 402 endpoint
curl -s -X POST http://localhost:8000/v1/messages \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"hello world"}]}' \
  -D - -o /dev/null \
  | grep -i x-payment-requirements \
  | sed 's/x-payment-requirements: //' \
  | python3 -c "import sys,base64,json; print(json.dumps(json.loads(base64.b64decode(sys.stdin.read().strip())), indent=2))"
```

You should see `input_token_count` and `prepaid_input` populated based
on the prompt you sent.
