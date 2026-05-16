/**
 * Anchor instruction discriminators. Anchor identifies an instruction by
 * `sha256("global:<name>")[:8]`. Hard-coding these would risk drift on a
 * rename; we derive them once at import time so the source-of-truth lives
 * alongside the Anchor names.
 */

import { sha256 } from "@noble/hashes/sha256";

function disc(name: string): Uint8Array {
  return sha256(new TextEncoder().encode(`global:${name}`)).slice(0, 8);
}

export const OPEN_CHANNEL = disc("open_channel");
export const SETTLE = disc("settle");
export const DISPUTE = disc("dispute");
export const CLOSE = disc("close");
