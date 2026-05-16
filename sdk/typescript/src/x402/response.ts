/**
 * x402 `X-PAYMENT-RESPONSE` for the TAP `tap.v1.channel` scheme. Returned by
 * the producer once the channel-open transaction confirms; the consumer
 * treats this as the channel-open acknowledgement and proceeds to the
 * streaming phase. Mirrors `tap.x402.response`.
 */

import { X402Error } from "../exceptions.js";
import { _internal } from "../protocol/codec.js";

export interface PaymentResponse {
  readonly txHash: string;
  /** "confirmed" | "finalized" */
  readonly settlement: string;
  readonly channelId: string;
  /** "active" — channel lifecycle state at ack time. */
  readonly channelState: string;
}

interface RootPayload {
  tx_hash: string;
  settlement: string;
  extra: {
    channel_id: string;
    channel_state: string;
  };
}

function toPayload(r: PaymentResponse): RootPayload {
  return {
    tx_hash: r.txHash,
    settlement: r.settlement,
    extra: {
      channel_id: r.channelId,
      channel_state: r.channelState,
    },
  };
}

export function encodeResponse(resp: PaymentResponse): string {
  return _internal.utf8ToBase64(JSON.stringify(toPayload(resp)));
}

export function decodeResponse(headerValue: string): PaymentResponse {
  let payload: RootPayload;
  try {
    payload = JSON.parse(_internal.base64ToUtf8(headerValue)) as RootPayload;
  } catch (cause) {
    throw new X402Error("X-PAYMENT-RESPONSE is not valid base64-JSON", {
      cause: cause as Error,
    });
  }
  const extra = payload.extra;
  if (!extra) {
    throw new X402Error("X-PAYMENT-RESPONSE is missing or malformed fields");
  }
  try {
    return {
      txHash: String(payload.tx_hash),
      settlement: String(payload.settlement),
      channelId: String(extra.channel_id),
      channelState: String(extra.channel_state),
    };
  } catch (cause) {
    throw new X402Error("X-PAYMENT-RESPONSE is missing or malformed fields", {
      cause: cause as Error,
    });
  }
}
