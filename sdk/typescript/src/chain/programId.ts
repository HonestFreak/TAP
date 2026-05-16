/**
 * Program and mint addresses. Centralized so a redeploy touches one file.
 * Values MUST stay in lockstep with `sdk/python/tap/chain/program_id.py`.
 */

import { address, type Address } from "@solana/kit";

export const PROGRAM_ID: Address = address("FK1ejU1ua497e8TcuabUTm7vxqf6WdKyYXA6ZhxmNWbX");

export const USDC_MINT_MAINNET: Address = address("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v");
export const USDC_MINT_DEVNET: Address = address("4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU");

export const SYSTEM_PROGRAM_ID: Address = address("11111111111111111111111111111111");
export const TOKEN_PROGRAM_ID: Address = address("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA");
export const ASSOCIATED_TOKEN_PROGRAM_ID: Address = address(
  "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
);
export const RENT_SYSVAR: Address = address("SysvarRent111111111111111111111111111111111");
