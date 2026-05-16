/**
 * Producer discovery: POST the prompt body with no payment, expect a 402
 * carrying the prompt-bound `PaymentRequirements` in `X-PAYMENT-REQUIREMENTS`.
 * Mirrors `tap.consumer.discovery.discover_with_prompt` in the Python SDK.
 */

import { X402Error } from "../exceptions.js";
import { HEADER_PAYMENT_REQUIREMENTS } from "../x402/headers.js";
import { decodeRequirements, type PaymentRequirements } from "../x402/requirements.js";

export interface DiscoverArgs {
  producerUrl: string;
  promptBody: unknown;
  fetchImpl?: typeof fetch;
}

export async function discoverWithPrompt(args: DiscoverArgs): Promise<PaymentRequirements> {
  const f = args.fetchImpl ?? fetch;
  const response = await f(args.producerUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(args.promptBody),
  });

  if (response.status !== 402) {
    throw new X402Error(
      `expected HTTP 402 from ${args.producerUrl}, got ${response.status}`,
    );
  }
  const header = response.headers.get(HEADER_PAYMENT_REQUIREMENTS);
  if (!header) {
    throw new X402Error(`${HEADER_PAYMENT_REQUIREMENTS} missing from 402 response`);
  }
  // Drain the body so the connection can be reused.
  await response.arrayBuffer().catch(() => undefined);

  return decodeRequirements(header);
}
