"""Channel-open transaction builder.

`build_open_channel_tx` composes a `VersionedTransaction` that:
  * funds the channel PDA with the deposit (USDC transfer via the program)
  * registers the consumer's session-key public key as the authorized signer
  * locks `prepaid_input_micro` on-chain as the settlement floor (whitepaper §4.9)

The transaction is returned to the caller unsigned-by-payer if requested,
so callers can either sign and submit themselves or hand it off to an
x402 facilitator that will broadcast it on their behalf."""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from solders.hash import Hash
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import VersionedTransaction

from tap.chain.instructions import open_channel_ix
from tap.chain.pda import derive_channel_pda


@dataclass(frozen=True, slots=True)
class OpenChannelPlan:
    """Pre-signed inputs ready to assemble into a transaction. Splitting
    'plan' from 'transaction' lets the caller add compute-budget or priority
    fee instructions without our build function dictating policy."""

    nonce: int
    channel: Pubkey
    transaction: VersionedTransaction


def build_open_channel_tx(
    *,
    consumer: Pubkey,
    producer: Pubkey,
    consumer_usdc: Pubkey,
    usdc_mint: Pubkey,
    session_key: Pubkey,
    deposit_micro: int,
    input_price_micro: int,
    output_price_micro: int,
    prepaid_input_micro: int,
    duration_secs: int,
    dispute_secs: int,
    trailing_buffer: int,
    blockhash: Hash,
    nonce: int | None = None,
) -> OpenChannelPlan:
    nonce = nonce if nonce is not None else _random_nonce()
    channel, _ = derive_channel_pda(consumer, producer, nonce)

    ix = open_channel_ix(
        consumer=consumer,
        producer=producer,
        consumer_usdc=consumer_usdc,
        usdc_mint=usdc_mint,
        session_key=session_key,
        nonce=nonce,
        deposit_micro=deposit_micro,
        input_price_micro=input_price_micro,
        output_price_micro=output_price_micro,
        prepaid_input_micro=prepaid_input_micro,
        duration_secs=duration_secs,
        dispute_secs=dispute_secs,
        trailing_buffer=trailing_buffer,
    )
    message = MessageV0.try_compile(
        payer=consumer,
        instructions=[ix],
        address_lookup_table_accounts=[],
        recent_blockhash=blockhash,
    )
    # Placeholder signature — the consumer wallet signs in `_sign` once the
    # tx is in hand. solders requires a `Signature`, not raw bytes.
    tx = VersionedTransaction.populate(message, [Signature.default()])
    return OpenChannelPlan(nonce=nonce, channel=channel, transaction=tx)


def _random_nonce() -> int:
    return int.from_bytes(secrets.token_bytes(8), "little")
