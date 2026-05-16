/**
 * x402 `X-PAYMENT` payload for opening a TAP channel. Wire format mirrors
 * `tap.x402.payment` in the Python SDK: outer `{scheme, network, extra}`
 * with all TAP-specific fields under `extra`, base64-encoded JSON in the
 * HTTP header.
 */

import { X402Error } from "../exceptions.js";
import { _internal } from "../protocol/codec.js";

export interface OpenChannelPayment {
  readonly scheme: string;
  readonly network: string;
  readonly consumerPubkey: string;
  readonly sessionKey: string;
  readonly nonce: bigint;
  readonly depositMicro: bigint;
  readonly inputPriceMicro: bigint;
  readonly outputPriceMicro: bigint;
  readonly prepaidInputMicro: bigint;
  readonly durationSecs: number;
  readonly disputeSecs: number;
  readonly trailingBufferTokens: number;
  /** Fully-signed channel-open transaction, base64 of the serialized bytes. */
  readonly transactionB64: string;
}

interface ExtraPayload {
  consumer_pubkey: string;
  session_key: string;
  nonce: number;
  deposit_micro: number;
  input_price_micro: number;
  output_price_micro: number;
  prepaid_input_micro: number;
  duration_secs: number;
  dispute_secs: number;
  trailing_buffer_tokens: number;
  transaction: string;
}

interface RootPayload {
  scheme: string;
  network: string;
  extra: ExtraPayload;
}

function bigintToNumber(value: bigint, field: string): number {
  if (value > BigInt(Number.MAX_SAFE_INTEGER) || value < 0n) {
    throw new RangeError(`x402 payment field ${field} (${value}) exceeds Number.MAX_SAFE_INTEGER`);
  }
  return Number(value);
}

function toPayload(p: OpenChannelPayment): RootPayload {
  return {
    scheme: p.scheme,
    network: p.network,
    extra: {
      consumer_pubkey: p.consumerPubkey,
      session_key: p.sessionKey,
      nonce: bigintToNumber(p.nonce, "nonce"),
      deposit_micro: bigintToNumber(p.depositMicro, "deposit_micro"),
      input_price_micro: bigintToNumber(p.inputPriceMicro, "input_price_micro"),
      output_price_micro: bigintToNumber(p.outputPriceMicro, "output_price_micro"),
      prepaid_input_micro: bigintToNumber(p.prepaidInputMicro, "prepaid_input_micro"),
      duration_secs: p.durationSecs,
      dispute_secs: p.disputeSecs,
      trailing_buffer_tokens: p.trailingBufferTokens,
      transaction: p.transactionB64,
    },
  };
}

export function encodePayment(payment: OpenChannelPayment): string {
  return _internal.utf8ToBase64(JSON.stringify(toPayload(payment)));
}

export function decodePayment(headerValue: string): OpenChannelPayment {
  let payload: RootPayload;
  try {
    payload = JSON.parse(_internal.base64ToUtf8(headerValue)) as RootPayload;
  } catch (cause) {
    throw new X402Error("X-PAYMENT is not valid base64-JSON", { cause: cause as Error });
  }
  const extra = payload.extra;
  if (!extra) {
    throw new X402Error("X-PAYMENT payload is missing or malformed fields");
  }
  try {
    return {
      scheme: payload.scheme,
      network: payload.network,
      consumerPubkey: extra.consumer_pubkey,
      sessionKey: extra.session_key,
      nonce: BigInt(extra.nonce),
      depositMicro: BigInt(extra.deposit_micro),
      inputPriceMicro: BigInt(extra.input_price_micro),
      outputPriceMicro: BigInt(extra.output_price_micro),
      prepaidInputMicro: BigInt(extra.prepaid_input_micro),
      durationSecs: Number(extra.duration_secs),
      disputeSecs: Number(extra.dispute_secs),
      trailingBufferTokens: Number(extra.trailing_buffer_tokens),
      transactionB64: String(extra.transaction),
    };
  } catch (cause) {
    throw new X402Error("X-PAYMENT payload is missing or malformed fields", {
      cause: cause as Error,
    });
  }
}
