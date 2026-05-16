/**
 * x402 codec round-trip tests. Mirrors `sdk/python/tests/test_x402_codecs.py`.
 * Equality after encode→decode proves the codec is internally consistent;
 * cross-language wire-format parity is verified by decoding fixtures produced
 * by the Python SDK in `tests/python-fixtures.test.ts`.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { decodePayment, encodePayment, type OpenChannelPayment } from "../src/x402/payment.js";
import {
  SCHEME,
  decodeRequirements,
  encodeRequirements,
  type PaymentRequirements,
} from "../src/x402/requirements.js";
import {
  decodeResponse,
  encodeResponse,
  type PaymentResponse,
} from "../src/x402/response.js";

describe("x402 codecs", () => {
  it("PaymentRequirements round-trip", () => {
    const req: PaymentRequirements = {
      scheme: SCHEME,
      network: "solana-devnet",
      asset: "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
      recipient: "TapPRoTuQDmXiBg2H4Z7Lp4uKnxw3w6f8Y4F2X1aBcD",
      producerPubkey: "prod1111111111111111111111111111111111111111",
      inputPriceMicro: 1n,
      outputPriceMicro: 5n,
      maxUnpaidMicro: 1_000n,
      trailingBufferTokens: 10,
      durationSecs: 600,
      disputeSecs: 30,
      graceMs: 200,
      pauseTimeoutMs: 5_000,
      channelOpenUrl: "https://x/open",
      streamUrl: "https://x/stream",
      tokenizerId: "tap.tok.v1",
      inputTokenCount: 42,
      prepaidInputMicro: 42n,
      model: "claude-sonnet-4-6",
    };
    assert.deepEqual(decodeRequirements(encodeRequirements(req)), req);
  });

  it("OpenChannelPayment round-trip", () => {
    const p: OpenChannelPayment = {
      scheme: SCHEME,
      network: "solana-devnet",
      consumerPubkey: "cons111111111111111111111111111111111111111",
      sessionKey: "sess111111111111111111111111111111111111111",
      nonce: 42n,
      depositMicro: 50_000n,
      inputPriceMicro: 1n,
      outputPriceMicro: 5n,
      prepaidInputMicro: 200n,
      durationSecs: 600,
      disputeSecs: 30,
      trailingBufferTokens: 10,
      transactionB64: "AA==",
    };
    assert.deepEqual(decodePayment(encodePayment(p)), p);
  });

  it("PaymentResponse round-trip", () => {
    const r: PaymentResponse = {
      txHash: "sig",
      settlement: "confirmed",
      channelId: "chan",
      channelState: "active",
    };
    assert.deepEqual(decodeResponse(encodeResponse(r)), r);
  });
});
