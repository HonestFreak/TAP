/**
 * Cross-language wire-format parity. The base64 strings below were captured
 * from the Python SDK (`sdk/python/tap/...`) so this suite proves the TS
 * encoder emits the exact same bytes — and the TS decoder reads what Python
 * produced. Regenerate with:
 *
 *   python3 scripts/dump_fixtures.py
 *
 * Drift between languages will show up here before it shows up in production.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { address, getAddressEncoder } from "@solana/kit";

import {
  encodeCommitment,
  encodeCommitmentBytes,
  decodeCommitment,
} from "../src/protocol/codec.js";
import type { CommitMessage } from "../src/protocol/commit.js";

import {
  encodeRequirements,
  decodeRequirements,
  SCHEME,
  type PaymentRequirements,
} from "../src/x402/requirements.js";
import {
  encodePayment,
  decodePayment,
  type OpenChannelPayment,
} from "../src/x402/payment.js";
import {
  encodeResponse,
  decodeResponse,
  type PaymentResponse,
} from "../src/x402/response.js";

const ADDR = getAddressEncoder();

// --- commit ---------------------------------------------------------------

const COMMIT_BYTES_HEX =
  "06cf568aa5491897f96b803e1915df38b2436ed3e4d28dcf961f24b26032318a" +
  "2a00000000000000" + // sequence = 42
  "87d6120000000000" + // cumulative_paid = 1_234_567
  "39300000" +         // tokens_received = 12_345
  "0068e5cf8b010000";  // timestamp_ms = 1_700_000_000_000

const COMMIT_HEADER =
  "eyJzY2hlbWEiOiJ0YXAudjEuY29tbWl0IiwiY2hhbm5lbF9pZCI6IlRhcFBSb1R1UURtWGlCZzJINFo3THA0dUtueHczdzZmOFk0RjJYMWFCY0QiLCJzZXF1ZW5jZSI6NDIsImN1bXVsYXRpdmVfcGFpZCI6MTIzNDU2NywidG9rZW5zX3JlY2VpdmVkIjoxMjM0NSwidGltZXN0YW1wX21zIjoxNzAwMDAwMDAwMDAwLCJzaWduYXR1cmUiOiJBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQT09In0=";

describe("commit parity with Python", () => {
  it("byte encoding matches Python's encode_commitment_bytes hex", () => {
    const channel = address("TapPRoTuQDmXiBg2H4Z7Lp4uKnxw3w6f8Y4F2X1aBcD");
    const msg: CommitMessage = {
      channel,
      sequence: 42n,
      cumulativePaid: 1_234_567n,
      tokensReceived: 12_345,
      timestampMs: 1_700_000_000_000n,
    };
    assert.equal(bytesToHex(encodeCommitmentBytes(msg)), COMMIT_BYTES_HEX);
  });

  it("JSON header encoding matches Python's encode_commitment exactly", () => {
    const channel = address("TapPRoTuQDmXiBg2H4Z7Lp4uKnxw3w6f8Y4F2X1aBcD");
    const msg: CommitMessage = {
      channel,
      sequence: 42n,
      cumulativePaid: 1_234_567n,
      tokensReceived: 12_345,
      timestampMs: 1_700_000_000_000n,
    };
    const header = encodeCommitment({ message: msg, signature: new Uint8Array(64) });
    assert.equal(header, COMMIT_HEADER);
  });

  it("TS decoder reads Python's COMMIT_HEADER", () => {
    const decoded = decodeCommitment(COMMIT_HEADER);
    assert.equal(decoded.message.sequence, 42n);
    assert.equal(decoded.message.cumulativePaid, 1_234_567n);
    assert.equal(decoded.message.tokensReceived, 12_345);
    assert.equal(decoded.message.timestampMs, 1_700_000_000_000n);
    assert.equal(decoded.signature.length, 64);
  });

  // Sanity: the hex matches `ADDR.encode("TapPRoTu...")` for the first 32 bytes.
  it("first 32 bytes of the commit bytes match the channel address", () => {
    const channel = address("TapPRoTuQDmXiBg2H4Z7Lp4uKnxw3w6f8Y4F2X1aBcD");
    const head = encodeCommitmentBytes({
      channel,
      sequence: 0n,
      cumulativePaid: 0n,
      tokensReceived: 0,
      timestampMs: 0n,
    }).slice(0, 32);
    assert.deepEqual(head, ADDR.encode(channel));
  });
});

// --- x402 -----------------------------------------------------------------

const REQ_HEADER =
  "eyJzY2hlbWUiOiJ0YXAudjEuY2hhbm5lbCIsIm5ldHdvcmsiOiJzb2xhbmEtZGV2bmV0IiwiYXNzZXQiOiI0ek1NQzlzcnQ1Umk1WDE0R0FnWGhhSGlpM0duUEFFRVJZUEpnWkpEbmNEVSIsInJlY2lwaWVudCI6IlRhcFBSb1R1UURtWGlCZzJINFo3THA0dUtueHczdzZmOFk0RjJYMWFCY0QiLCJleHRyYSI6eyJwcm9kdWNlcl9wdWJrZXkiOiJwcm9kMTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMSIsImlucHV0X3ByaWNlIjoxLCJvdXRwdXRfcHJpY2UiOjUsInRva2VuaXplcl9pZCI6InRhcC50b2sudjEiLCJpbnB1dF90b2tlbl9jb3VudCI6NDIsInByZXBhaWRfaW5wdXQiOjQyLCJtYXhfdW5wYWlkIjoxMDAwLCJ0cmFpbGluZ19idWZmZXIiOjEwLCJkdXJhdGlvbl9zZWNzIjo2MDAsImRpc3B1dGVfc2VjcyI6MzAsImdyYWNlX21zIjoyMDAsInBhdXNlX3RpbWVvdXRfbXMiOjUwMDAsImNoYW5uZWxfb3Blbl91cmwiOiJodHRwczovL3gvb3BlbiIsInN0cmVhbV91cmwiOiJodHRwczovL3gvc3RyZWFtIiwibW9kZWwiOiJjbGF1ZGUtc29ubmV0LTQtNiJ9fQ==";

const PAY_HEADER =
  "eyJzY2hlbWUiOiJ0YXAudjEuY2hhbm5lbCIsIm5ldHdvcmsiOiJzb2xhbmEtZGV2bmV0IiwiZXh0cmEiOnsiY29uc3VtZXJfcHVia2V5IjoiY29uczExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMSIsInNlc3Npb25fa2V5Ijoic2VzczExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMSIsIm5vbmNlIjo0MiwiZGVwb3NpdF9taWNybyI6NTAwMDAsImlucHV0X3ByaWNlX21pY3JvIjoxLCJvdXRwdXRfcHJpY2VfbWljcm8iOjUsInByZXBhaWRfaW5wdXRfbWljcm8iOjIwMCwiZHVyYXRpb25fc2VjcyI6NjAwLCJkaXNwdXRlX3NlY3MiOjMwLCJ0cmFpbGluZ19idWZmZXJfdG9rZW5zIjoxMCwidHJhbnNhY3Rpb24iOiJBQT09In19";

const RESP_HEADER =
  "eyJ0eF9oYXNoIjoic2lnIiwic2V0dGxlbWVudCI6ImNvbmZpcm1lZCIsImV4dHJhIjp7ImNoYW5uZWxfaWQiOiJjaGFuIiwiY2hhbm5lbF9zdGF0ZSI6ImFjdGl2ZSJ9fQ==";

const REQ: PaymentRequirements = {
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

const PAY: OpenChannelPayment = {
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

const RESP: PaymentResponse = {
  txHash: "sig",
  settlement: "confirmed",
  channelId: "chan",
  channelState: "active",
};

describe("x402 parity with Python", () => {
  it("PaymentRequirements encodes byte-for-byte the same", () => {
    assert.equal(encodeRequirements(REQ), REQ_HEADER);
  });
  it("OpenChannelPayment encodes byte-for-byte the same", () => {
    assert.equal(encodePayment(PAY), PAY_HEADER);
  });
  it("PaymentResponse encodes byte-for-byte the same", () => {
    assert.equal(encodeResponse(RESP), RESP_HEADER);
  });

  it("TS decoder reads Python's REQ_HEADER", () => {
    assert.deepEqual(decodeRequirements(REQ_HEADER), REQ);
  });
  it("TS decoder reads Python's PAY_HEADER", () => {
    assert.deepEqual(decodePayment(PAY_HEADER), PAY);
  });
  it("TS decoder reads Python's RESP_HEADER", () => {
    assert.deepEqual(decodeResponse(RESP_HEADER), RESP);
  });
});

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}
