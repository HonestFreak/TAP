"""Producer-side settlement: build and submit the on-chain `settle` ix.

Settlement is composed from three instructions in the same transaction:
  1. ComputeBudget priority-fee (caller-controlled; not built here)
  2. Ed25519 verify of the latest commitment signature
  3. The TAP `settle` instruction itself

The Ed25519 ix is required because Solana cannot verify Ed25519 inside a
program; we attach it as a sibling and the program inspects it via the
instructions sysvar."""

from __future__ import annotations

from solders.keypair import Keypair
from solders.pubkey import Pubkey

from tap.chain.ed25519_ix import ed25519_verify_ix
from tap.chain.instructions import settle_ix
from tap.chain.rpc import ChainClient, SubmitResult
from tap.exceptions import SettlementError
from tap.producer.channel import ActiveChannel
from tap.protocol.codec import encode_commitment_bytes


async def settle_channel(
    *,
    chain: ChainClient,
    producer: Keypair,
    producer_usdc: Pubkey,
    channel: ActiveChannel,
) -> SubmitResult:
    """Submit `settle` for `channel` using the latest accepted commitment."""
    if channel.last_commitment is None:
        raise SettlementError(
            "no accepted commitment for this channel; nothing to settle"
        )

    signed = channel.last_commitment
    verify_ix = ed25519_verify_ix(
        public_key=bytes(channel.session_key),
        signature=signed.signature,
        message=encode_commitment_bytes(signed.message),
    )
    settle = settle_ix(
        caller=producer.pubkey(),
        channel=channel.channel_id,
        consumer=channel.consumer,
        producer=producer.pubkey(),
        commitment=signed.message,
        signature=signed.signature,
    )
    # `producer_usdc` is unused in `settle` (no token movement happens until
    # `close`), but kept on the call signature so the producer's lifecycle
    # caller doesn't need to thread the close-time account through.
    _ = producer_usdc
    return await chain.submit([verify_ix, settle], signers=[producer])
