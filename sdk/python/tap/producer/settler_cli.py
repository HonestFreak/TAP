"""One-shot CLI: scan and close every ready channel, then exit.

Useful for backfilling channels that piled up before the settler existed,
or for ops who'd rather run the worker out-of-process under cron/systemd
than embed it in the producer. Reads the same env vars as `demo.producer`
so it can be pointed at an existing producer's keypair without ceremony.

    python -m tap.producer.settler_cli

The producer process runs an in-process `Settler` automatically, so this
CLI is for *one-shot* maintenance only — running both at once is fine
(the on-chain handler handles double-submit), just wasteful."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from solders.keypair import Keypair
from solders.pubkey import Pubkey

from tap.chain.program_id import PROGRAM_ID
from tap.chain.rpc import ChainClient
from tap.producer.settler import Settler


def _load_keypair(path_or_json: str) -> Keypair:
    text = path_or_json.strip()
    if text.startswith("["):
        raw = json.loads(text)
    else:
        raw = json.loads(Path(text).expanduser().read_text())
    return Keypair.from_bytes(bytes(raw))


async def _run() -> int:
    keypair = _load_keypair(os.environ["TAP_PRODUCER_KEYPAIR"])
    producer_usdc = Pubkey.from_string(os.environ["TAP_PRODUCER_USDC"])
    rpc_url = os.environ.get("TAP_RPC", "https://api.devnet.solana.com")

    async with ChainClient(rpc_url) as chain:
        settler = Settler(
            chain=chain,
            program_id=PROGRAM_ID,
            producer=keypair,
            producer_usdc=producer_usdc,
        )
        return await settler.run_once()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    closed = asyncio.run(_run())
    print(f"closed {closed} channel(s)")
    sys.exit(0 if closed >= 0 else 1)


if __name__ == "__main__":
    main()
