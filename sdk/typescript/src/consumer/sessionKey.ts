/**
 * Ephemeral Ed25519 keypair generated per session.
 *
 * Whitepaper §4.5: the consumer's primary wallet never signs per-token
 * commitments. Instead a fresh session keypair is generated, its public key
 * is written into the channel account at `open_channel`, and only that key
 * is used to sign `X-TAP-COMMIT` messages. Lifting compromise risk off the
 * funded wallet is the whole point.
 */

import * as ed from "@noble/ed25519";
import { address, getBase58Decoder, type Address } from "@solana/kit";

import { publicKeyFromSeed } from "../protocol/signing.js";

const BASE58 = getBase58Decoder();

export interface SessionKey {
  /** 32-byte secret seed. Hold in memory only. */
  readonly seed: Uint8Array;
  /** 32-byte Ed25519 public key. */
  readonly publicKeyBytes: Uint8Array;
  /** Base58-encoded Solana `Address` of the public key. */
  readonly publicKey: Address;
}

/** Generate a fresh session keypair. Uses the platform CSPRNG via
 * `@noble/ed25519`'s built-in `randomPrivateKey()`. */
export function generateSessionKey(): SessionKey {
  const seed = ed.utils.randomPrivateKey();
  const publicKeyBytes = publicKeyFromSeed(seed);
  return {
    seed,
    publicKeyBytes,
    publicKey: address(BASE58.decode(publicKeyBytes)),
  };
}

/** Reconstruct a session key from a stored 32-byte seed. Useful for tests
 * with deterministic keypairs; production code should always call
 * `generateSessionKey()`. */
export function sessionKeyFromSeed(seed: Uint8Array): SessionKey {
  if (seed.length !== 32) {
    throw new Error("session key seed must be 32 bytes");
  }
  const publicKeyBytes = publicKeyFromSeed(seed);
  return {
    seed,
    publicKeyBytes,
    publicKey: address(BASE58.decode(publicKeyBytes)),
  };
}
