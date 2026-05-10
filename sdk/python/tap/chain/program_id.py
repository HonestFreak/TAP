"""Program and mint addresses. Centralized so a redeploy touches one file."""

from __future__ import annotations

from solders.pubkey import Pubkey

PROGRAM_ID: Pubkey = Pubkey.from_string("FK1ejU1ua497e8TcuabUTm7vxqf6WdKyYXA6ZhxmNWbX")

USDC_MINT_MAINNET: Pubkey = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
USDC_MINT_DEVNET: Pubkey = Pubkey.from_string("4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU")
