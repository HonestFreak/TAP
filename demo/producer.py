"""Reference TAP producer wrapping Gemini.

Run with:
    uvicorn demo.producer:app --host 0.0.0.0 --port 8000

The producer exposes one endpoint, `/v1/messages`, that:
  * answers GET with HTTP 402 + generic x402 payment requirements
  * answers POST (no payment, with prompt body) with a prompt-bound 402
    quote carrying `input_token_count` and `prepaid_input` (whitepaper §4.9)
  * accepts POST with X-PAYMENT (channel open) and streams Gemini tokens
  * accepts POST .../commit with X-TAP-COMMIT for in-session commitments
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from solders.keypair import Keypair
from solders.pubkey import Pubkey

from tap.adapters.gemini import stream_gemini
from tap.chain.program_id import USDC_MINT_DEVNET
from tap.chain.rpc import ChainClient
from tap.producer.pricing import Pricing
from tap.producer.server import TapProducer
from tap.timing.parameters import TimingParameters


def _load_keypair(path_or_json: str) -> Keypair:
    """Accept either a filesystem path to a keypair JSON, or the JSON array
    inline. Hosted environments (Render, Fly) inject secrets as env vars,
    not files, so we support both shapes from the same env var."""
    text = path_or_json.strip()
    if text.startswith("["):
        raw = json.loads(text)
    else:
        raw = json.loads(Path(text).expanduser().read_text())
    return Keypair.from_bytes(bytes(raw))


KEYPAIR = _load_keypair(os.environ["TAP_PRODUCER_KEYPAIR"])
PRODUCER_USDC = Pubkey.from_string(os.environ["TAP_PRODUCER_USDC"])
RPC_URL = os.environ.get("TAP_RPC", "https://api.devnet.solana.com")
PUBLIC_BASE_URL = os.environ.get("TAP_PUBLIC_URL", "http://localhost:8000")

producer = TapProducer(
    keypair=KEYPAIR,
    producer_usdc=PRODUCER_USDC,
    chain=ChainClient(RPC_URL),
    pricing=Pricing(
        # 1:5 input:output ratio, mirroring the typical asymmetry of
        # frontier-model pricing (whitepaper §4.8).
        input_price_micro=1,             # 0.000001 USDC per prompt token
        output_price_micro=5,            # 0.000005 USDC per output token
        max_unpaid_micro=5_000,          # halt if >0.005 USDC unpaid
        trailing_buffer_tokens=10,
        tokenizer_id="tap.tok.v1",
    ),
    timing=TimingParameters(grace_ms=200, pause_timeout_ms=30_000, total_session_ms=5 * 60_000),
    network="solana-devnet",
    usdc_mint=USDC_MINT_DEVNET,
    public_base_url=PUBLIC_BASE_URL,
    model_name="gemini-2.5-flash",
)


@producer.handler("/v1/messages")
async def handle_messages(body: dict) -> object:
    """Forward the request to Gemini and return the raw token iterator;
    the TAP framework handles all metering and SSE encoding."""
    return stream_gemini(body)


app = producer.app


@app.get("/healthz")
async def healthz() -> dict:
    """Unauthenticated liveness probe for hosting platforms (Render, Fly).
    /v1/messages is x402-shaped (returns 402 by design) so platforms can't
    use it as a health signal."""
    return {"status": "ok"}
