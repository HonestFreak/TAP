/**
 * Ed25519 signing and verification of `CommitMessage`. Thin by design — the
 * only crypto primitive TAP needs at the protocol layer is Ed25519 over the
 * 60-byte canonical message form. Key management lives in the consumer
 * package; this file is pure crypto.
 */

import * as ed from "@noble/ed25519";
import { sha512 } from "@noble/hashes/sha512";

import { CommitmentError } from "../exceptions.js";
import type { CommitMessage, SignedCommitment } from "./commit.js";
import { encodeCommitmentBytes } from "./codec.js";

// `@noble/ed25519` v2 requires a sha-512 implementation to be wired in once
// per process. We use `@noble/hashes/sha512` so the SDK runs unchanged on
// Node, Bun, Deno, and browsers without depending on `node:crypto`.
ed.etc.sha512Sync = (...msgs: Uint8Array[]) => sha512(ed.etc.concatBytes(...msgs));

/** Produce a `SignedCommitment` that the on-chain program will accept, given
 * the 32-byte session-key seed registered at `open_channel`. */
export function signCommitment(
  message: CommitMessage,
  sessionKeySeed: Uint8Array,
): SignedCommitment {
  if (sessionKeySeed.length !== 32) {
    throw new Error("session key seed must be 32 bytes");
  }
  const signature = ed.sign(encodeCommitmentBytes(message), sessionKeySeed);
  return { message, signature };
}

/** Throws `CommitmentError` if `signed` is not a valid signature by
 * `sessionPublicKey` over `signed.message`. */
export function verifyCommitment(
  signed: SignedCommitment,
  sessionPublicKey: Uint8Array,
): void {
  if (sessionPublicKey.length !== 32) {
    throw new CommitmentError("session public key must be 32 bytes");
  }
  const ok = ed.verify(signed.signature, encodeCommitmentBytes(signed.message), sessionPublicKey);
  if (!ok) {
    throw new CommitmentError("commitment signature failed verification");
  }
}

/** Derive the 32-byte Ed25519 public key from a 32-byte secret seed. Exposed
 * separately so consumers can derive the on-chain pubkey from a stored seed
 * without round-tripping through a signer object. */
export function publicKeyFromSeed(sessionKeySeed: Uint8Array): Uint8Array {
  if (sessionKeySeed.length !== 32) {
    throw new Error("session key seed must be 32 bytes");
  }
  return ed.getPublicKey(sessionKeySeed);
}
