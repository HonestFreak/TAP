/**
 * PDA derivation. Mirrors the seeds in `programs/tap/src/constants.rs` and
 * `sdk/python/tap/chain/pda.py`. Drift here means channels created by the
 * SDK won't be recognized by the on-chain program.
 */

import {
  address,
  getAddressEncoder,
  getProgramDerivedAddress,
  type Address,
  type ProgramDerivedAddress,
} from "@solana/kit";

import {
  ASSOCIATED_TOKEN_PROGRAM_ID,
  PROGRAM_ID,
  TOKEN_PROGRAM_ID,
} from "./programId.js";

export const CHANNEL_SEED = new TextEncoder().encode("tap-channel");
export const VAULT_SEED = new TextEncoder().encode("tap-vault");

const ADDR = getAddressEncoder();

/** Derive the channel PDA for a `(consumer, producer, nonce)` triple.
 *  Returns the address and the bump byte. */
export async function deriveChannelPda(
  consumer: Address,
  producer: Address,
  nonce: bigint,
): Promise<ProgramDerivedAddress> {
  const nonceBytes = new Uint8Array(8);
  new DataView(nonceBytes.buffer).setBigUint64(0, nonce, true);

  return getProgramDerivedAddress({
    programAddress: PROGRAM_ID,
    seeds: [CHANNEL_SEED, ADDR.encode(consumer), ADDR.encode(producer), nonceBytes],
  });
}

/** Derive the channel's USDC vault PDA. */
export async function deriveVaultPda(channel: Address): Promise<ProgramDerivedAddress> {
  return getProgramDerivedAddress({
    programAddress: PROGRAM_ID,
    seeds: [VAULT_SEED, ADDR.encode(channel)],
  });
}

/** Derive the SPL associated token account address for `(owner, mint)`.
 * Replicated locally so the SDK doesn't pull in a higher-level SPL client
 * just for this one helper. */
export async function deriveAta(owner: Address, mint: Address): Promise<Address> {
  const [ata] = await getProgramDerivedAddress({
    programAddress: ASSOCIATED_TOKEN_PROGRAM_ID,
    seeds: [ADDR.encode(owner), ADDR.encode(TOKEN_PROGRAM_ID), ADDR.encode(mint)],
  });
  return ata;
}

// Re-export `address(...)` so callers don't need a second import for the
// rare case where they're constructing an `Address` from a base58 string.
export { address };
