"""Program and mint addresses. Centralized so a redeploy touches one file."""

from __future__ import annotations

from solders.pubkey import Pubkey

PROGRAM_ID: Pubkey = Pubkey.from_string("2tqofcitv1LHFGCLCmR9Kyke6TmArQwpHSinWWtmCje9")

USDC_MINT_MAINNET: Pubkey = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
USDC_MINT_DEVNET: Pubkey = Pubkey.from_string("4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU")
