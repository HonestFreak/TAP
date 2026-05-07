"""Solana RPC and instruction builders for the TAP program. Everything in
this package is a pure adapter on top of `solana-py`; no application logic
lives here."""

from tap.chain.program_id import PROGRAM_ID, USDC_MINT_DEVNET, USDC_MINT_MAINNET
from tap.chain.pda import derive_channel_pda, derive_vault_pda
from tap.chain.rpc import ChainClient

__all__ = [
    "PROGRAM_ID",
    "USDC_MINT_DEVNET",
    "USDC_MINT_MAINNET",
    "ChainClient",
    "derive_channel_pda",
    "derive_vault_pda",
]
