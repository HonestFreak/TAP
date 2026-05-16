/**
 * `ConsumerSession` — the streaming iterator the application interacts with.
 *
 * One session per request. Internally:
 *   * advances `cumulativePaid` (starting at `prepaidInputMicro`) per output token
 *   * runs the optional evaluator after each token
 *   * signs an `X-TAP-COMMIT` every `commitEveryTokens` output tokens
 *   * surfaces token chunks as an async iterator
 *
 * Halt-on-evaluator and the AIMD adaptive-batch tuning from the Python SDK
 * are deferred to a future iteration; this MVP uses a fixed K.
 */

import { type Address } from "@solana/kit";

import { signCommitment } from "../protocol/signing.js";
import { encodeCommitment } from "../protocol/codec.js";
import type { CommitMessage } from "../protocol/commit.js";
import {
  HEADER_TAP_CHANNEL,
  HEADER_TAP_COMMIT,
} from "../x402/headers.js";
import type { PaymentRequirements } from "../x402/requirements.js";

import { iterSse } from "./sse.js";
import type { SessionKey } from "./sessionKey.js";

export interface TokenChunk {
  readonly text: string;
  readonly cumulativePaidMicro: bigint;
  readonly tokensReceived: number;
}

/** Two-value decision matching `tap.evaluators.base.Decision`. */
export const Decision = {
  CONTINUE: "CONTINUE",
  HALT: "HALT",
} as const;
export type Decision = (typeof Decision)[keyof typeof Decision];

export type Evaluator = (accumulated: string) => Decision;

export interface ConsumerSessionInit {
  fetchImpl: typeof fetch;
  requirements: PaymentRequirements;
  channelId: Address;
  sessionKey: SessionKey;
  inputPriceMicro: bigint;
  outputPriceMicro: bigint;
  prepaidInputMicro: bigint;
  depositMicro: bigint;
  evaluator?: Evaluator;
  /** Tokens per commit batch. Fixed cadence; the Python SDK adapts this. */
  commitEveryTokens?: number;
}

export class ConsumerSession {
  readonly channelId: Address;
  readonly sessionPublicKey: Address;
  openTxSignature: string | null = null;

  private readonly fetchImpl: typeof fetch;
  private readonly requirements: PaymentRequirements;
  private readonly sessionKey: SessionKey;
  private readonly outputPriceMicro: bigint;
  private readonly depositMicro: bigint;
  private readonly evaluator?: Evaluator;
  private readonly commitEveryTokens: number;

  private sequence = 0n;
  private tokensReceivedCount = 0;
  private cumulativePaid: bigint;
  private accumulated = "";
  private tokensSinceCommit = 0;
  private haltedByName: string | null = null;

  constructor(init: ConsumerSessionInit) {
    this.fetchImpl = init.fetchImpl;
    this.requirements = init.requirements;
    this.channelId = init.channelId;
    this.sessionKey = init.sessionKey;
    this.sessionPublicKey = init.sessionKey.publicKey;
    this.outputPriceMicro = init.outputPriceMicro;
    this.depositMicro = init.depositMicro;
    this.evaluator = init.evaluator;
    this.commitEveryTokens = init.commitEveryTokens ?? 8;
    // Whitepaper §4.9: cumulative_paid starts at the prepaid input floor
    // before any output token arrives.
    this.cumulativePaid = init.prepaidInputMicro;
  }

  get cumulativePaidMicro(): bigint { return this.cumulativePaid; }
  get tokensReceived(): number { return this.tokensReceivedCount; }
  get haltedBy(): string | null { return this.haltedByName; }

  /** Open the streaming POST and yield one `TokenChunk` per token.
   *
   * `body` MUST be the same prompt body that produced the prompt-bound 402
   * quote at session open — the prepaid-input floor is bound to that prompt's
   * tokenization. */
  async *stream(body: unknown): AsyncIterableIterator<TokenChunk> {
    const response = await this.fetchImpl(this.requirements.streamUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        [HEADER_TAP_CHANNEL]: this.channelId,
      },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new Error(`stream POST failed: HTTP ${response.status}`);
    }

    for await (const event of iterSse(response)) {
      if (event.finished) {
        await this.sendCommit({ force: true });
        return;
      }

      this.absorbToken(event.text);

      yield {
        text: event.text,
        cumulativePaidMicro: this.cumulativePaid,
        tokensReceived: this.tokensReceivedCount,
      };

      if (this.evaluator && this.evaluator(this.accumulated) === Decision.HALT) {
        this.haltedByName = (this.evaluator as { name?: string }).name ?? "evaluator";
        await this.sendCommit({ force: true });
        return;
      }

      if (this.tokensSinceCommit >= this.commitEveryTokens) {
        await this.sendCommit({ force: false });
      }
    }
  }

  private absorbToken(text: string): void {
    this.tokensReceivedCount += 1;
    this.tokensSinceCommit += 1;
    const next = this.cumulativePaid + this.outputPriceMicro;
    this.cumulativePaid = next > this.depositMicro ? this.depositMicro : next;
    this.accumulated += text;
  }

  private async sendCommit(opts: { force: boolean }): Promise<void> {
    if (!opts.force && this.tokensSinceCommit === 0) return;

    this.sequence += 1n;
    const message: CommitMessage = {
      channel: this.channelId,
      sequence: this.sequence,
      cumulativePaid: this.cumulativePaid,
      tokensReceived: this.tokensReceivedCount,
      timestampMs: BigInt(Date.now()),
    };
    const signed = signCommitment(message, this.sessionKey.seed);
    const encoded = encodeCommitment(signed);

    // Commits go to a side channel so they don't interleave with SSE frames.
    await this.fetchImpl(`${this.requirements.streamUrl}/commit`, {
      method: "POST",
      headers: {
        [HEADER_TAP_COMMIT]: encoded,
        [HEADER_TAP_CHANNEL]: this.channelId,
      },
    });
    this.tokensSinceCommit = 0;
  }
}
