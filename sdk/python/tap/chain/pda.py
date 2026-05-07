"""PDA derivation. Mirrors the seeds defined in `programs/tap/src/constants.rs`.

The seeds and derivation order MUST match the on-chain program. Tests in
`tests/test_pda_parity.py` verify this against fixtures dumped from Anchor."""

from __future__ import annotations

from solders.pubkey import Pubkey
from spl.token.constants import ASSOCIATED_TOKEN_PROGRAM_ID, TOKEN_PROGRAM_ID

from tap.chain.program_id import PROGRAM_ID

CHANNEL_SEED = b"tap-channel"
VAULT_SEED = b"tap-vault"


def derive_channel_pda(consumer: Pubkey, producer: Pubkey, nonce: int) -> tuple[Pubkey, int]:
    """Derive the channel PDA for a `(consumer, producer, nonce)` triple."""
    return Pubkey.find_program_address(
        [
            CHANNEL_SEED,
            bytes(consumer),
            bytes(producer),
            nonce.to_bytes(8, "little"),
        ],
        PROGRAM_ID,
    )


def derive_vault_pda(channel: Pubkey) -> tuple[Pubkey, int]:
    """Derive the channel's USDC vault PDA."""
    return Pubkey.find_program_address([VAULT_SEED, bytes(channel)], PROGRAM_ID)


def derive_ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    """Derive the SPL associated token account address for `(owner, mint)`.

    Replicated locally so the SDK does not depend on `spl-token-py`'s
    higher-level client just for this one helper."""
    address, _ = Pubkey.find_program_address(
        [bytes(owner), bytes(TOKEN_PROGRAM_ID), bytes(mint)],
        ASSOCIATED_TOKEN_PROGRAM_ID,
    )
    return address
