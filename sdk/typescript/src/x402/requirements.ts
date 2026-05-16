/**
 * x402 `X-PAYMENT-REQUIREMENTS` for the TAP `tap.v1.channel` scheme.
 *
 * Producers publish session terms; consumers parse them and verify the
 * producer's parameters meet local policy before constructing the open-channel
 * transaction (whitepaper §4.8). The payload carries a per-prompt input quote
 * (`inputTokenCount`, `prepaidInputMicro`) alongside the per-token prices —
 * see whitepaper §4.9.
 *
 * Wire format MUST stay byte-compatible with `tap.x402.requirements` in the
 * Python SDK (same field names, same `extra` nesting, same base64-then-JSON
 * transport).
 */

import { X402Error } from "../exceptions.js";
import { _internal } from "../protocol/codec.js";

export const SCHEME = "tap.v1.channel" as const;

export interface PaymentRequirements {
  readonly scheme: string;
  readonly network: string;
  readonly asset: string;
  readonly recipient: string;
  readonly producerPubkey: string;
  readonly inputPriceMicro: bigint;
  readonly outputPriceMicro: bigint;
  readonly maxUnpaidMicro: bigint;
  readonly trailingBufferTokens: number;
  readonly durationSecs: number;
  readonly disputeSecs: number;
  readonly graceMs: number;
  readonly pauseTimeoutMs: number;
  readonly channelOpenUrl: string;
  readonly streamUrl: string;
  readonly tokenizerId: string;
  readonly inputTokenCount: number;
  readonly prepaidInputMicro: bigint;
  readonly model: string | null;
}

interface ExtraPayload {
  producer_pubkey: string;
  input_price: number;
  output_price: number;
  tokenizer_id: string;
  input_token_count?: number;
  prepaid_input?: number;
  max_unpaid: number;
  trailing_buffer: number;
  duration_secs: number;
  dispute_secs: number;
  grace_ms: number;
  pause_timeout_ms: number;
  channel_open_url: string;
  stream_url: string;
  model: string | null;
}

function bigintToNumber(value: bigint, field: string): number {
  if (value > BigInt(Number.MAX_SAFE_INTEGER) || value < 0n) {
    throw new RangeError(
      `x402 requirements field ${field} (${value}) exceeds Number.MAX_SAFE_INTEGER`,
    );
  }
  return Number(value);
}

interface RootPayload {
  scheme: string;
  network: string;
  asset: string;
  recipient: string;
  extra: ExtraPayload;
}

function toPayload(req: PaymentRequirements): RootPayload {
  return {
    scheme: req.scheme,
    network: req.network,
    asset: req.asset,
    recipient: req.recipient,
    extra: {
      producer_pubkey: req.producerPubkey,
      input_price: bigintToNumber(req.inputPriceMicro, "input_price"),
      output_price: bigintToNumber(req.outputPriceMicro, "output_price"),
      tokenizer_id: req.tokenizerId,
      input_token_count: req.inputTokenCount,
      prepaid_input: bigintToNumber(req.prepaidInputMicro, "prepaid_input"),
      max_unpaid: bigintToNumber(req.maxUnpaidMicro, "max_unpaid"),
      trailing_buffer: req.trailingBufferTokens,
      duration_secs: req.durationSecs,
      dispute_secs: req.disputeSecs,
      grace_ms: req.graceMs,
      pause_timeout_ms: req.pauseTimeoutMs,
      channel_open_url: req.channelOpenUrl,
      stream_url: req.streamUrl,
      model: req.model,
    },
  };
}

export function encodeRequirements(req: PaymentRequirements): string {
  return _internal.utf8ToBase64(JSON.stringify(toPayload(req)));
}

export function decodeRequirements(headerValue: string): PaymentRequirements {
  let payload: RootPayload;
  try {
    payload = JSON.parse(_internal.base64ToUtf8(headerValue)) as RootPayload;
  } catch (cause) {
    throw new X402Error("X-PAYMENT-REQUIREMENTS is not valid base64-JSON", {
      cause: cause as Error,
    });
  }

  if (payload.scheme !== SCHEME) {
    throw new X402Error(`unsupported payment scheme ${JSON.stringify(payload.scheme)}`);
  }
  const extra = payload.extra;
  if (!extra) {
    throw new X402Error("X-PAYMENT-REQUIREMENTS is missing or malformed fields");
  }

  try {
    return {
      scheme: payload.scheme,
      network: payload.network,
      asset: payload.asset,
      recipient: payload.recipient,
      producerPubkey: extra.producer_pubkey,
      inputPriceMicro: BigInt(extra.input_price),
      outputPriceMicro: BigInt(extra.output_price),
      tokenizerId: String(extra.tokenizer_id),
      inputTokenCount: Number(extra.input_token_count ?? 0),
      prepaidInputMicro: BigInt(extra.prepaid_input ?? 0),
      maxUnpaidMicro: BigInt(extra.max_unpaid),
      trailingBufferTokens: Number(extra.trailing_buffer),
      durationSecs: Number(extra.duration_secs),
      disputeSecs: Number(extra.dispute_secs),
      graceMs: Number(extra.grace_ms),
      pauseTimeoutMs: Number(extra.pause_timeout_ms),
      channelOpenUrl: String(extra.channel_open_url),
      streamUrl: String(extra.stream_url),
      model: extra.model ?? null,
    };
  } catch (cause) {
    throw new X402Error("X-PAYMENT-REQUIREMENTS is missing or malformed fields", {
      cause: cause as Error,
    });
  }
}
