/**
 * Codec parity test. Mirrors `sdk/python/tests/test_codec_parity.py`.
 * The byte layout MUST match the on-chain Rust verifier exactly; this test
 * reconstructs the expected bytes by hand and compares to the encoder.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { address, getAddressEncoder } from "@solana/kit";

import { encodeCommitmentBytes, encodeCommitment, decodeCommitment } from "../src/protocol/codec.js";
import { signCommitment, verifyCommitment } from "../src/protocol/signing.js";
import { sessionKeyFromSeed } from "../src/consumer/sessionKey.js";
import type { CommitMessage } from "../src/protocol/commit.js";

const ADDR = getAddressEncoder();

describe("commit codec", () => {
  it("byte layout matches the hand-constructed Rust layout", () => {
    const channel = address("TapPRoTuQDmXiBg2H4Z7Lp4uKnxw3w6f8Y4F2X1aBcD");
    const message: CommitMessage = {
      channel,
      sequence: 42n,
      cumulativePaid: 1_234_567n,
      tokensReceived: 12_345,
      timestampMs: 1_700_000_000_000n,
    };
    const encoded = encodeCommitmentBytes(message);

    const expected = new Uint8Array(32 + 8 + 8 + 4 + 8);
    const view = new DataView(expected.buffer);
    expected.set(ADDR.encode(channel), 0);
    view.setBigUint64(32, 42n, true);
    view.setBigUint64(40, 1_234_567n, true);
    view.setUint32(48, 12_345, true);
    view.setBigUint64(52, 1_700_000_000_000n, true);

    assert.deepEqual(encoded, expected);
    assert.equal(encoded.length, 60);
  });

  it("JSON header form round-trips", () => {
    const channel = address("TapPRoTuQDmXiBg2H4Z7Lp4uKnxw3w6f8Y4F2X1aBcD");
    const message: CommitMessage = {
      channel,
      sequence: 7n,
      cumulativePaid: 500n,
      tokensReceived: 100,
      timestampMs: 1_700_000_000_000n,
    };
    const signed = {
      message,
      signature: new Uint8Array(64).fill(0x42),
    };
    const header = encodeCommitment(signed);
    const back = decodeCommitment(header);

    assert.equal(back.message.channel, message.channel);
    assert.equal(back.message.sequence, message.sequence);
    assert.equal(back.message.cumulativePaid, message.cumulativePaid);
    assert.equal(back.message.tokensReceived, message.tokensReceived);
    assert.equal(back.message.timestampMs, message.timestampMs);
    assert.deepEqual(back.signature, signed.signature);
  });
});

describe("commit signing", () => {
  it("sign + verify round-trip", () => {
    const seed = new Uint8Array(32);
    for (let i = 0; i < 32; i++) seed[i] = i + 1;
    const session = sessionKeyFromSeed(seed);

    const message: CommitMessage = {
      channel: address("TapPRoTuQDmXiBg2H4Z7Lp4uKnxw3w6f8Y4F2X1aBcD"),
      sequence: 1n,
      cumulativePaid: 100n,
      tokensReceived: 20,
      timestampMs: 0n,
    };
    const signed = signCommitment(message, seed);
    // Should not throw.
    verifyCommitment(signed, session.publicKeyBytes);
    assert.equal(signed.signature.length, 64);
  });

  it("verify rejects a tampered signature", () => {
    const seed = new Uint8Array(32).fill(1);
    const session = sessionKeyFromSeed(seed);
    const message: CommitMessage = {
      channel: address("TapPRoTuQDmXiBg2H4Z7Lp4uKnxw3w6f8Y4F2X1aBcD"),
      sequence: 1n,
      cumulativePaid: 100n,
      tokensReceived: 20,
      timestampMs: 0n,
    };
    const signed = signCommitment(message, seed);
    const tampered = {
      message,
      signature: new Uint8Array(signed.signature),
    };
    tampered.signature[0] = (tampered.signature[0]! ^ 0xff) & 0xff;
    assert.throws(() => verifyCommitment(tampered, session.publicKeyBytes), /failed verification/);
  });
});
