/**
 * Canonical byte and JSON codecs for `CommitMessage`.
 *
 * Two encodings exist, intentionally:
 *
 *  * The byte encoding (`encodeCommitmentBytes`) is what the session key
 *    signs and what the on-chain program verifies. Fixed-width, no labels.
 *  * The JSON encoding (`encodeCommitment` / `decodeCommitment`) is what
 *    travels over HTTP in the `X-TAP-COMMIT` header. Verbose so intermediaries
 *    can debug it.
 *
 * Always sign and verify the byte form; never the JSON.
 */

import { address, getAddressEncoder, type Address } from "@solana/kit";

import { ProtocolError } from "../exceptions.js";
import { SCHEMA, type CommitMessage, type SignedCommitment } from "./commit.js";

const ADDR = getAddressEncoder();

/** Produce the bytes the on-chain program verifies against. */
export function encodeCommitmentBytes(message: CommitMessage): Uint8Array {
  const out = new Uint8Array(32 + 8 + 8 + 4 + 8);
  const view = new DataView(out.buffer);

  out.set(ADDR.encode(message.channel), 0);
  view.setBigUint64(32, message.sequence, true);
  view.setBigUint64(40, message.cumulativePaid, true);
  view.setUint32(48, message.tokensReceived, true);
  view.setBigUint64(52, message.timestampMs, true);

  return out;
}

interface CommitJsonPayload {
  schema: string;
  channel_id: string;
  sequence: number;
  cumulative_paid: number;
  tokens_received: number;
  timestamp_ms: number;
  signature: string;
}

/** JSON-then-base64 encoding for HTTP header transport. Numeric fields are
 * serialized as JSON numbers (matching Python's `json.dumps(int)`). All TAP
 * values fit within `Number.MAX_SAFE_INTEGER` (2^53 − 1): timestamp_ms,
 * cumulative_paid (micro-USDC), and sequence are all well under that bound. */
export function encodeCommitment(signed: SignedCommitment): string {
  const payload: CommitJsonPayload = {
    schema: SCHEMA,
    channel_id: signed.message.channel,
    sequence: bigintToNumber(signed.message.sequence, "sequence"),
    cumulative_paid: bigintToNumber(signed.message.cumulativePaid, "cumulative_paid"),
    tokens_received: signed.message.tokensReceived,
    timestamp_ms: bigintToNumber(signed.message.timestampMs, "timestamp_ms"),
    signature: bytesToBase64(signed.signature),
  };
  // Python uses `json.dumps(..., separators=(",", ":"))` — no whitespace.
  // `JSON.stringify` without a third argument already matches this.
  return utf8ToBase64(JSON.stringify(payload));
}

function bigintToNumber(value: bigint, field: string): number {
  if (value > BigInt(Number.MAX_SAFE_INTEGER) || value < BigInt(Number.MIN_SAFE_INTEGER)) {
    throw new RangeError(`commitment field ${field} (${value}) exceeds Number.MAX_SAFE_INTEGER`);
  }
  return Number(value);
}

/** Inverse of `encodeCommitment`. Raises `ProtocolError` on malformed input. */
export function decodeCommitment(headerValue: string): SignedCommitment {
  let payload: CommitJsonPayload;
  try {
    payload = JSON.parse(base64ToUtf8(headerValue)) as CommitJsonPayload;
  } catch (cause) {
    throw new ProtocolError("X-TAP-COMMIT is not valid base64-encoded JSON", {
      cause: cause as Error,
    });
  }

  if (payload.schema !== SCHEMA) {
    throw new ProtocolError(`unknown commit schema ${JSON.stringify(payload.schema)}`);
  }

  let signature: Uint8Array;
  let channel: Address;
  let message: CommitMessage;
  try {
    channel = address(String(payload.channel_id));
    message = {
      channel,
      sequence: BigInt(payload.sequence),
      cumulativePaid: BigInt(payload.cumulative_paid),
      tokensReceived: Number(payload.tokens_received),
      timestampMs: BigInt(payload.timestamp_ms),
    };
    signature = base64ToBytes(String(payload.signature));
  } catch (cause) {
    throw new ProtocolError("X-TAP-COMMIT payload is missing or malformed fields", {
      cause: cause as Error,
    });
  }

  if (signature.length !== 64) {
    throw new ProtocolError("commitment signature must be 64 bytes");
  }

  return { message, signature };
}

// --- internal base64 helpers ---------------------------------------------
// Browser and Node both expose `btoa`/`atob` on globalThis; Node ≥20 also has
// `Buffer`, but staying in WHATWG-only primitives keeps the SDK isomorphic.

function utf8ToBase64(text: string): string {
  return bytesToBase64(new TextEncoder().encode(text));
}

function base64ToUtf8(b64: string): string {
  return new TextDecoder().decode(base64ToBytes(b64));
}

function bytesToBase64(bytes: Uint8Array): string {
  let bin = "";
  for (let i = 0; i < bytes.length; i++) {
    bin += String.fromCharCode(bytes[i]!);
  }
  return btoa(bin);
}

function base64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) {
    out[i] = bin.charCodeAt(i);
  }
  return out;
}

// Exported for x402 codecs which share the same base64 transport rules.
export const _internal = {
  utf8ToBase64,
  base64ToUtf8,
  bytesToBase64,
  base64ToBytes,
};
