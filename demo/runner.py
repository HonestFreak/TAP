"""Consumer runner — thin HTTP/SSE backend that the React frontend talks to.

Why a backend at all? The TAP consumer SDK is in Python: it owns the
session-key signer, the Solana RPC client, x402 wire codecs, and the
streaming state machine. Reimplementing that in TypeScript for the demo
would mean keeping two consumers in sync. Instead the browser drives a
controller that wraps `TapConsumer` and pushes session events as SSE.

Endpoints:
  GET  /api/config            static info (network, addresses)
  GET  /api/balances          live consumer + producer USDC balances
  POST /api/run               accepts a prompt; streams session events as SSE

Run with:
    uvicorn demo.runner:app --host 0.0.0.0 --port 8001
"""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from tap import TapConsumer, evaluators
from tap.chain.keypair_io import load_keypair
from tap.chain.pda import derive_ata
from tap.chain.program_id import PROGRAM_ID, USDC_MINT_DEVNET
from tap.chain.rpc import ChainClient
from tap.consumer.session import CommitSigned

PRODUCER_URL = os.environ.get("TAP_PRODUCER_URL", "http://localhost:8000/v1/messages")
RPC_URL = os.environ.get("TAP_RPC", "https://api.devnet.solana.com")
NETWORK = os.environ.get("TAP_NETWORK", "solana-devnet")

# Comma-separated list of allowed origins for CORS. In dev the Vite proxy
# means the browser sees the API as same-origin, but a hosted frontend on a
# different domain (Vercel etc.) needs explicit allow-listing.
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("TAP_CORS_ORIGIN", "http://localhost:5173").split(",")
    if o.strip()
]

# Optional shared access code for hosted demos. When set, /api/run and
# /api/balances require an `X-Tap-Access` header matching this value.
# Unset (None or empty string) disables the gate, which is what local dev wants.
ACCESS_CODE = os.environ.get("TAP_ACCESS_CODE") or None

# Hard cap on per-session deposit, in micro-USDC. Defends the shared devnet
# wallet against abuse even if the access gate is bypassed.
MAX_DEPOSIT_MICRO = int(os.environ.get("TAP_MAX_DEPOSIT_MICRO", "200000"))


def require_access(
    x_tap_access: str | None = Header(default=None, alias="X-Tap-Access"),
) -> None:
    """Reject requests missing the shared access code when one is configured."""
    if ACCESS_CODE is None:
        return
    if x_tap_access != ACCESS_CODE:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid access code")


@dataclass(frozen=True, slots=True)
class _Config:
    consumer_pubkey: str
    consumer_usdc: str
    producer_pubkey: str
    producer_usdc: str
    network: str
    rpc_url: str
    program_id: str
    usdc_mint: str
    producer_url: str


@asynccontextmanager
async def _lifespan(app: FastAPI):
    consumer_kp = load_keypair(os.environ["TAP_CONSUMER_KEYPAIR"])
    producer_pk = Pubkey.from_string(os.environ["TAP_PRODUCER_PUBKEY"])
    producer_usdc = Pubkey.from_string(os.environ["TAP_PRODUCER_USDC"])
    consumer_usdc = derive_ata(consumer_kp.pubkey(), USDC_MINT_DEVNET)

    app.state.config = _Config(
        consumer_pubkey=str(consumer_kp.pubkey()),
        consumer_usdc=str(consumer_usdc),
        producer_pubkey=str(producer_pk),
        producer_usdc=str(producer_usdc),
        network=NETWORK,
        rpc_url=RPC_URL,
        program_id=str(PROGRAM_ID),
        usdc_mint=str(USDC_MINT_DEVNET),
        producer_url=PRODUCER_URL,
    )
    app.state.consumer_kp = consumer_kp
    app.state.http = httpx.AsyncClient(timeout=60.0)
    app.state.chain = ChainClient(RPC_URL)
    yield
    await app.state.http.aclose()
    await app.state.chain.close()


app = FastAPI(title="TAP Consumer Runner", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*", "X-Tap-Access"],
)


@app.get("/healthz")
async def healthz() -> dict:
    """Unauthenticated liveness probe for hosting platforms (Render, Fly).
    Kept separate from /api/* so the access gate covers the real surface."""
    return {"status": "ok"}


@app.get("/api/config", dependencies=[Depends(require_access)])
async def get_config() -> dict:
    cfg = app.state.config
    return {
        "consumer_pubkey":  cfg.consumer_pubkey,
        "consumer_usdc":    cfg.consumer_usdc,
        "producer_pubkey":  cfg.producer_pubkey,
        "producer_usdc":    cfg.producer_usdc,
        "network":          cfg.network,
        "rpc_url":          cfg.rpc_url,
        "program_id":       cfg.program_id,
        "usdc_mint":        cfg.usdc_mint,
        "producer_url":     cfg.producer_url,
    }


@app.get("/api/balances", dependencies=[Depends(require_access)])
async def get_balances() -> dict:
    cfg = app.state.config
    chain: ChainClient = app.state.chain
    consumer_balance = await chain.token_balance_micro(Pubkey.from_string(cfg.consumer_usdc))
    producer_balance = await chain.token_balance_micro(Pubkey.from_string(cfg.producer_usdc))
    return {
        "consumer_micro": consumer_balance,
        "producer_micro": producer_balance,
    }


@app.get(
    "/api/sessions/{channel_id}/signatures",
    dependencies=[Depends(require_access)],
)
async def get_session_signatures(channel_id: str) -> dict:
    """List the on-chain transactions that touched this channel PDA, oldest
    first. Used by the demo's explorer panel so users can click through to
    Solscan and see the open / settle / close lifecycle land in real time
    without having to copy/paste signatures."""
    chain: ChainClient = app.state.chain
    try:
        address = Pubkey.from_string(channel_id)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid channel_id") from exc
    sigs = await chain.signatures_for_address(address, limit=10)
    sigs.sort(key=lambda s: s["slot"])
    return {"channel_id": channel_id, "signatures": sigs}


class RunRequest(BaseModel):
    prompt: str
    # Server-side ceiling on the deposit. Even with the access gate in place,
    # we never want a single request to be able to drain the shared devnet
    # wallet — the cap is enforced here regardless of what the client sends.
    deposit_micro: int = Field(default=50_000, ge=1_000, le=MAX_DEPOSIT_MICRO)
    enforce_schema: bool = True


def _sse(event: dict) -> bytes:
    """Format a single SSE message. Frontend `EventSource` parses these."""
    return f"data: {json.dumps(event)}\n\n".encode("utf-8")


async def _run_session(req: RunRequest) -> AsyncIterator[bytes]:
    """One session: discover → open → stream → commit-loop → close.

    Every transition is yielded as an SSE event so the React side can render
    the channel lifecycle as it happens."""
    cfg = app.state.config
    consumer_kp: Keypair = app.state.consumer_kp

    # The schema toggle is the demo's halt-vs-no-halt switch. With it on, a
    # prose response triggers the JSON-schema evaluator and we settle early.
    eval_chain = evaluators.compose(
        evaluators.json_schema(
            {
                "type": "object",
                "required": ["title", "summary", "tags"],
                "properties": {
                    "title":   {"type": "string"},
                    "summary": {"type": "string"},
                    "tags":    {"type": "array"},
                },
            }
        ) if req.enforce_schema else _noop_evaluator,
        evaluators.length_cap(4_000),
    )

    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def on_commit(signed: CommitSigned) -> None:
        await queue.put(
            {
                "type":                  "commit_signed",
                "sequence":              signed.sequence,
                "cumulative_paid_micro": signed.cumulative_paid_micro,
                "tokens_received":       signed.tokens_received,
                "timestamp_ms":          signed.timestamp_ms,
            }
        )

    prompt_body = {"messages": [{"role": "user", "content": req.prompt}]}

    async def driver() -> None:
        try:
            async with ChainClient(RPC_URL) as chain, TapConsumer(
                wallet=consumer_kp, chain=chain
            ) as consumer:
                await queue.put({"type": "phase", "phase": "opening"})
                session = await consumer.open_session(
                    producer_url=cfg.producer_url,
                    deposit_micro=req.deposit_micro,
                    prompt_body=prompt_body,
                    evaluator=eval_chain,
                    on_commit=on_commit,
                )
                await queue.put(
                    {
                        "type":                "session_open",
                        "channel_id":          session.channel_id,
                        "session_pubkey":      session.session_pubkey,
                        "open_tx_signature":   session.open_tx_signature,
                        "deposit_micro":       req.deposit_micro,
                        "prepaid_input_micro": session.prepaid_input_micro,
                    }
                )
                await queue.put({"type": "phase", "phase": "streaming"})

                async for chunk in session.stream(prompt_body):
                    await queue.put(
                        {
                            "type":                  "token",
                            "text":                  chunk.text,
                            "tokens_received":       chunk.tokens_received,
                            "cumulative_paid_micro": chunk.cumulative_paid_micro,
                        }
                    )

                await queue.put(
                    {
                        "type":                  "complete",
                        "tokens_received":       session.tokens_received,
                        "cumulative_paid_micro": session.cumulative_paid_micro,
                        "halted_by":             session.halted_by,
                    }
                )
        except Exception as exc:
            await queue.put({"type": "error", "message": str(exc)})
        finally:
            await queue.put(None)

    task = asyncio.create_task(driver())
    try:
        while True:
            event = await queue.get()
            if event is None:
                break
            yield _sse(event)
    finally:
        task.cancel()


def _noop_evaluator(_: str):
    from tap.evaluators.base import Decision
    return Decision.CONTINUE


@app.post("/api/run", dependencies=[Depends(require_access)])
async def run(req: RunRequest) -> StreamingResponse:
    return StreamingResponse(
        _run_session(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
