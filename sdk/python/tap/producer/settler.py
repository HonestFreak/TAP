"""Periodic settler: closes channels whose dispute window has elapsed.

The TAP program's `close` instruction is the only place USDC moves out of
the channel vault. `settle` records the cumulative_paid commitment but
performs no token transfer; the producer must come back later — after
`dispute_secs` — to actually claim the funds.

The producer process owns this worker. It poll-scans the program for
Channel accounts in `Settling` status whose `settled_at + dispute_secs`
is in the past, and submits `close` for each one. The chain itself is the
source of truth, which means:

  * No local persistence is required. A producer that crashes mid-window
    will still close the channel on next startup.
  * Stale channels from before the worker existed get cleaned up the
    first time the loop runs, which is exactly what we want for the demo.

We do not (yet) handle the consumer's expiry escape hatch — `close` on an
`Active` channel past its `expires_at`. That's the consumer's path; if a
producer is doing its job they reach `Settling` first."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from solana.rpc.types import MemcmpOpts
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from tap.chain.channel_account import (
    ChannelAccount,
    ChannelStatus,
    PRODUCER_OFFSET,
    STATUS_OFFSET,
    decode_channel,
)
from tap.chain.instructions import close_ix
from tap.chain.rpc import ChainClient

_log = logging.getLogger(__name__)

# `MemcmpOpts.bytes` is base58 — the on-the-wire RPC format. For the Anchor
# enum tag we only need single-byte values; precomputing avoids importing a
# base58 encoder for one byte.
_STATUS_BYTE_BASE58 = {0: "1", 1: "2", 2: "3"}


@dataclass(frozen=True, slots=True)
class _Pending:
    address: Pubkey
    account: ChannelAccount


class Settler:
    """Background worker that polls for channels ready to close.

    Use `start()` to spawn the loop and `stop()` for graceful shutdown.
    Idempotent: if `close` lost the race (another caller already closed),
    the on-chain handler returns `ChannelNotSettling` and we just log."""

    def __init__(
        self,
        *,
        chain: ChainClient,
        program_id: Pubkey,
        producer: Keypair,
        producer_usdc: Pubkey,
        poll_interval_secs: float = 10.0,
        clock_slack_secs: int = 5,
    ) -> None:
        self._chain = chain
        self._program_id = program_id
        self._producer = producer
        self._producer_usdc = producer_usdc
        self._poll_interval = poll_interval_secs
        self._clock_slack = clock_slack_secs
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()

    def start(self) -> None:
        if self._task is not None:
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._run_loop(), name="tap-settler")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stopping.set()
        self._task.cancel()
        try:
            await self._task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
        self._task = None

    async def _run_loop(self) -> None:
        while not self._stopping.is_set():
            try:
                await self.run_once()
            except Exception as exc:  # noqa: BLE001
                # Never let one bad poll kill the worker. Network blips and
                # transient RPC errors are expected.
                _log.warning("settler poll failed: %s", exc)
            try:
                await asyncio.wait_for(
                    self._stopping.wait(), timeout=self._poll_interval
                )
            except asyncio.TimeoutError:
                continue

    async def run_once(self) -> int:
        """Single scan/close pass. Returns the number of close txs submitted.
        Useful in tests and as a one-shot CLI entrypoint."""
        pending = await self._find_ready()
        if not pending:
            return 0
        submitted = 0
        for entry in pending:
            try:
                await self._submit_close(entry)
                submitted += 1
            except Exception as exc:  # noqa: BLE001
                _log.warning(
                    "close failed for %s: %s", entry.address, exc
                )
        return submitted

    async def _find_ready(self) -> list[_Pending]:
        # Filter on-chain by both status (Settling) and producer pubkey, so
        # the RPC only returns *our* channels in the relevant state. This
        # also avoids fee-paying for someone else's channels.
        filters: list[MemcmpOpts | int] = [
            MemcmpOpts(
                offset=STATUS_OFFSET,
                bytes=_STATUS_BYTE_BASE58[ChannelStatus.SETTLING],
            ),
            MemcmpOpts(
                offset=PRODUCER_OFFSET,
                bytes=str(self._producer.pubkey()),
            ),
        ]
        accounts = await self._chain.get_program_accounts(
            self._program_id, filters=filters
        )
        now = int(time.time())
        ready: list[_Pending] = []
        for address, data in accounts:
            try:
                channel = decode_channel(data)
            except ValueError as exc:
                _log.debug("skip undecodable account %s: %s", address, exc)
                continue
            dispute_until = channel.settled_at + channel.dispute_secs
            if now >= dispute_until + self._clock_slack:
                ready.append(_Pending(address=address, account=channel))
        return ready

    async def _submit_close(self, entry: _Pending) -> None:
        from tap.chain.pda import derive_ata
        from tap.chain.program_id import USDC_MINT_DEVNET

        consumer_usdc = derive_ata(entry.account.consumer, USDC_MINT_DEVNET)
        ix = close_ix(
            caller=self._producer.pubkey(),
            channel=entry.address,
            consumer=entry.account.consumer,
            producer=self._producer.pubkey(),
            consumer_usdc=consumer_usdc,
            producer_usdc=self._producer_usdc,
        )
        result = await self._chain.submit([ix], signers=[self._producer])
        _log.info(
            "closed channel %s in tx %s (paid=%d refund=%d)",
            entry.address,
            result.signature,
            entry.account.last_cumulative_paid,
            entry.account.deposit_micro - entry.account.last_cumulative_paid,
        )


