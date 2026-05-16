/**
 * `CommitMessage` byte layout is the source of truth shared with the on-chain
 * Rust verifier and the Python SDK. Any change to field order or width here
 * MUST be mirrored in `programs/tap/src/state/commitment.rs` and
 * `sdk/python/tap/protocol/commit.py` in the same commit.
 */

import type { Address } from "@solana/kit";

/** Identifier embedded in JSON-encoded commitments. Bumped on any breaking
 * change to the message layout. Matches `tap.protocol.commit.SCHEMA`. */
export const SCHEMA = "tap.v1.commit" as const;

export interface CommitMessage {
  readonly channel: Address;
  readonly sequence: bigint;
  readonly cumulativePaid: bigint;
  readonly tokensReceived: number;
  readonly timestampMs: bigint;
}

export interface SignedCommitment {
  readonly message: CommitMessage;
  /** 64-byte Ed25519 signature over the canonical byte form. */
  readonly signature: Uint8Array;
}
