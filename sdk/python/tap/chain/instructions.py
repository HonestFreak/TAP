"""Builders for the four TAP instructions. Each function returns a
`solders.instruction.Instruction` ready to be added to a transaction.

These are pure functions: no RPC, no signing. Composition with the Ed25519
verify ix (for `settle`/`dispute`) happens at the caller site so callers
can decide priority-fee policy and account ordering."""

from __future__ import annotations

from solders.instruction import AccountMeta, Instruction
from solders.pubkey import Pubkey
from solders.sysvar import INSTRUCTIONS as INSTRUCTIONS_SYSVAR
from solders.sysvar import RENT as RENT_SYSVAR
from solders.system_program import ID as SYSTEM_PROGRAM_ID
from spl.token.constants import ASSOCIATED_TOKEN_PROGRAM_ID, TOKEN_PROGRAM_ID

from tap.chain.discriminator import CLOSE, DISPUTE, OPEN_CHANNEL, SETTLE
from tap.chain.pda import derive_channel_pda, derive_vault_pda
from tap.chain.program_id import PROGRAM_ID
from tap.protocol.codec import encode_commitment_bytes
from tap.protocol.commit import CommitMessage


def open_channel_ix(
    *,
    consumer: Pubkey,
    producer: Pubkey,
    consumer_usdc: Pubkey,
    usdc_mint: Pubkey,
    session_key: Pubkey,
    nonce: int,
    deposit_micro: int,
    input_price_micro: int,
    output_price_micro: int,
    prepaid_input_micro: int,
    duration_secs: int,
    dispute_secs: int,
    trailing_buffer: int,
) -> Instruction:
    channel, _ = derive_channel_pda(consumer, producer, nonce)
    vault, _ = derive_vault_pda(channel)

    # Argument layout must match the Anchor handler signature in
    # `programs/tap/src/lib.rs::open_channel`.
    data = bytearray(OPEN_CHANNEL)
    data += nonce.to_bytes(8, "little")
    data += bytes(session_key)
    data += deposit_micro.to_bytes(8, "little")
    data += input_price_micro.to_bytes(8, "little")
    data += output_price_micro.to_bytes(8, "little")
    data += prepaid_input_micro.to_bytes(8, "little")
    data += duration_secs.to_bytes(4, "little")
    data += dispute_secs.to_bytes(4, "little")
    data += trailing_buffer.to_bytes(4, "little")

    accounts = [
        AccountMeta(consumer, is_signer=True, is_writable=True),
        AccountMeta(producer, is_signer=False, is_writable=False),
        AccountMeta(channel, is_signer=False, is_writable=True),
        AccountMeta(vault, is_signer=False, is_writable=True),
        AccountMeta(usdc_mint, is_signer=False, is_writable=False),
        AccountMeta(consumer_usdc, is_signer=False, is_writable=True),
        AccountMeta(SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(ASSOCIATED_TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(RENT_SYSVAR, is_signer=False, is_writable=False),
    ]
    return Instruction(PROGRAM_ID, bytes(data), accounts)


def settle_ix(
    *,
    caller: Pubkey,
    channel: Pubkey,
    consumer: Pubkey,
    producer: Pubkey,
    commitment: CommitMessage,
    signature: bytes,
) -> Instruction:
    return _commit_carrying_ix(
        SETTLE,
        caller=caller,
        channel=channel,
        consumer=consumer,
        producer=producer,
        commitment=commitment,
        signature=signature,
    )


def dispute_ix(
    *,
    caller: Pubkey,
    channel: Pubkey,
    consumer: Pubkey,
    producer: Pubkey,
    commitment: CommitMessage,
    signature: bytes,
) -> Instruction:
    return _commit_carrying_ix(
        DISPUTE,
        caller=caller,
        channel=channel,
        consumer=consumer,
        producer=producer,
        commitment=commitment,
        signature=signature,
    )


def close_ix(
    *,
    caller: Pubkey,
    channel: Pubkey,
    consumer: Pubkey,
    producer: Pubkey,
    consumer_usdc: Pubkey,
    producer_usdc: Pubkey,
) -> Instruction:
    # Account order MUST match `programs/tap/src/lib.rs::Close`. `producer_usdc`
    # is required by the on-chain handler (it transfers paid_micro out of the
    # vault into this account); omitting it produces an opaque AccountNotFound
    # at submit time.
    vault, _ = derive_vault_pda(channel)
    accounts = [
        AccountMeta(caller, is_signer=True, is_writable=True),
        AccountMeta(channel, is_signer=False, is_writable=True),
        AccountMeta(consumer, is_signer=False, is_writable=True),
        AccountMeta(producer, is_signer=False, is_writable=False),
        AccountMeta(vault, is_signer=False, is_writable=True),
        AccountMeta(producer_usdc, is_signer=False, is_writable=True),
        AccountMeta(consumer_usdc, is_signer=False, is_writable=True),
        AccountMeta(TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
    ]
    return Instruction(PROGRAM_ID, bytes(CLOSE), accounts)


def _commit_carrying_ix(
    discriminator: bytes,
    *,
    caller: Pubkey,
    channel: Pubkey,
    consumer: Pubkey,
    producer: Pubkey,
    commitment: CommitMessage,
    signature: bytes,
) -> Instruction:
    """Builder shared by `settle_ix` and `dispute_ix`. The on-chain `Settle`
    and `Dispute` account contexts in `programs/tap/src/lib.rs` only need:
    caller, channel, consumer, producer, instructions_sysvar. Token-account
    movements happen in `close`, so vault / *_usdc accounts MUST NOT be
    listed here — Anchor positional matching would mis-bind them otherwise."""
    if len(signature) != 64:
        raise ValueError("signature must be 64 bytes")

    data = bytearray(discriminator)
    data += encode_commitment_bytes(commitment)
    data += signature

    accounts = [
        AccountMeta(caller, is_signer=True, is_writable=True),
        AccountMeta(channel, is_signer=False, is_writable=True),
        AccountMeta(consumer, is_signer=False, is_writable=False),
        AccountMeta(producer, is_signer=False, is_writable=False),
        AccountMeta(INSTRUCTIONS_SYSVAR, is_signer=False, is_writable=False),
    ]
    return Instruction(PROGRAM_ID, bytes(data), accounts)
