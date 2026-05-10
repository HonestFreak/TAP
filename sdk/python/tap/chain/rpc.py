"""Thin RPC wrapper.

`ChainClient` is the only place in the SDK that talks to a Solana RPC node.
Higher layers receive a `ChainClient` injected at construction time, which
makes them trivially mockable for tests and lets applications swap in their
own facilitator-backed transport without subclassing."""

from __future__ import annotations

from dataclasses import dataclass

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.types import MemcmpOpts, TxOpts
from solders.hash import Hash
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import VersionedTransaction


@dataclass(frozen=True, slots=True)
class SubmitResult:
    signature: Signature
    slot: int | None


class ChainClient:
    """Wraps `AsyncClient` with the small subset of operations the TAP SDK
    actually needs: latest blockhash, send-and-confirm, account fetch."""

    def __init__(self, endpoint: str, *, commitment: str = "confirmed") -> None:
        self._endpoint = endpoint
        self._client = AsyncClient(endpoint, commitment=commitment)

    async def close(self) -> None:
        await self._client.close()

    async def __aenter__(self) -> "ChainClient":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def latest_blockhash(self) -> Hash:
        resp = await self._client.get_latest_blockhash()
        return resp.value.blockhash

    async def submit(
        self,
        instructions: list[Instruction],
        signers: list[Keypair],
        *,
        payer: Pubkey | None = None,
    ) -> SubmitResult:
        if not signers:
            raise ValueError("at least one signer required")
        fee_payer = payer or signers[0].pubkey()
        blockhash = await self.latest_blockhash()
        message = MessageV0.try_compile(
            payer=fee_payer,
            instructions=instructions,
            address_lookup_table_accounts=[],
            recent_blockhash=blockhash,
        )
        tx = VersionedTransaction(message, signers)
        resp = await self._client.send_transaction(
            tx,
            opts=TxOpts(skip_confirmation=False, preflight_commitment=Confirmed),
        )
        return SubmitResult(signature=resp.value, slot=None)

    async def send_raw(self, raw_tx: bytes) -> Signature:
        """Submit an already-signed serialized transaction. Used when the
        caller built and signed the transaction itself (e.g. an x402
        channel-open arriving from the consumer)."""
        resp = await self._client.send_raw_transaction(raw_tx)
        return resp.value

    async def get_account(self, address: Pubkey) -> bytes | None:
        resp = await self._client.get_account_info(address)
        if resp.value is None:
            return None
        return bytes(resp.value.data)

    async def token_balance_micro(self, token_account: Pubkey) -> int:
        """Fetch a SPL token account's `amount` field. Returns 0 if the
        account does not exist (token-2022 accounts are not supported here;
        the demo sticks to the classic SPL Token program)."""
        resp = await self._client.get_token_account_balance(token_account)
        if resp.value is None:
            return 0
        return int(resp.value.amount)

    async def get_program_accounts(
        self,
        program_id: Pubkey,
        *,
        filters: list[MemcmpOpts | int] | None = None,
    ) -> list[tuple[Pubkey, bytes]]:
        """List program-owned accounts matching `filters`, returning each as
        `(pubkey, raw_data)`. Thin wrapper around solana-py's typed RPC; the
        settler uses this to find channels in `Settling` status."""
        resp = await self._client.get_program_accounts(
            program_id, encoding="base64", filters=filters
        )
        out: list[tuple[Pubkey, bytes]] = []
        for entry in resp.value:
            data = entry.account.data
            # solana-py returns either bytes (already decoded) or a tuple of
            # (encoded_str, encoding); normalise to bytes.
            if isinstance(data, (bytes, bytearray)):
                out.append((entry.pubkey, bytes(data)))
            else:
                import base64
                out.append((entry.pubkey, base64.b64decode(data[0])))
        return out

    async def signatures_for_address(
        self, address: Pubkey, *, limit: int = 10
    ) -> list[dict[str, object]]:
        """Most-recent-first list of confirmed signatures touching `address`,
        normalised to plain dicts so callers don't need the solders type
        surface. Powers the demo's "open / settle / close" explorer panel."""
        resp = await self._client.get_signatures_for_address(address, limit=limit)
        return [
            {
                "signature":  str(item.signature),
                "slot":       int(item.slot),
                "block_time": int(item.block_time) if item.block_time is not None else None,
                "err":        item.err,
            }
            for item in resp.value
        ]
