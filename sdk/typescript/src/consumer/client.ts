/**
 * `TapConsumer` — top-level entry point. Discovers a producer, opens a
 * channel, returns a `ConsumerSession`.
 *
 * The open flow follows whitepaper §4.9:
 *   1. POST the prompt body to the producer (no payment).
 *   2. Receive a prompt-bound 402 with `inputTokenCount` / `prepaidInputMicro`.
 *   3. Build the channel-open transaction with `prepaidInputMicro` locked
 *      on-chain as the settlement floor.
 *   4. Submit via X-PAYMENT and proceed to streaming.
 *
 * Policy auditing and local re-tokenization (whitepaper §5.3.7) are
 * deferred to a future iteration; this MVP trusts the producer's quote.
 */

import {
  address,
  createSolanaRpc,
  type Address,
  type Rpc,
  type SolanaRpcApi,
  type TransactionSigner,
} from "@solana/kit";

import { X402Error } from "../exceptions.js";
import { USDC_MINT_DEVNET } from "../chain/programId.js";
import { deriveAta } from "../chain/pda.js";
import {
  HEADER_PAYMENT,
  HEADER_PAYMENT_RESPONSE,
} from "../x402/headers.js";
import { decodeResponse } from "../x402/response.js";
import { encodePayment, type OpenChannelPayment } from "../x402/payment.js";
import { SCHEME } from "../x402/requirements.js";

import { discoverWithPrompt } from "./discovery.js";
import { buildAndSignOpenChannelTx } from "./openChannelTx.js";
import { generateSessionKey, type SessionKey } from "./sessionKey.js";
import { ConsumerSession, type Evaluator } from "./session.js";

export interface TapConsumerInit {
  /** Funded consumer wallet — pays the deposit and signs the channel-open tx. */
  wallet: TransactionSigner;
  /** RPC URL or pre-built RPC instance for `getLatestBlockhash`. */
  rpc: string | Rpc<SolanaRpcApi>;
  /** Defaults to the devnet USDC mint. */
  usdcMint?: Address;
  fetchImpl?: typeof fetch;
}

export interface OpenSessionArgs {
  producerUrl: string;
  depositMicro: bigint;
  promptBody: unknown;
  evaluator?: Evaluator;
  commitEveryTokens?: number;
  /** Override the auto-generated session key (testing). */
  sessionKey?: SessionKey;
  /** Override the auto-generated random nonce (testing). */
  nonce?: bigint;
}

export class TapConsumer {
  private readonly wallet: TransactionSigner;
  private readonly rpc: Rpc<SolanaRpcApi>;
  private readonly usdcMint: Address;
  private readonly fetchImpl: typeof fetch;

  constructor(init: TapConsumerInit) {
    this.wallet = init.wallet;
    this.rpc = typeof init.rpc === "string" ? createSolanaRpc(init.rpc) : init.rpc;
    this.usdcMint = init.usdcMint ?? USDC_MINT_DEVNET;
    this.fetchImpl = init.fetchImpl ?? fetch;
  }

  async openSession(args: OpenSessionArgs): Promise<ConsumerSession> {
    const requirements = await discoverWithPrompt({
      producerUrl: args.producerUrl,
      promptBody: args.promptBody,
      fetchImpl: this.fetchImpl,
    });

    if (requirements.prepaidInputMicro > args.depositMicro) {
      throw new X402Error(
        `deposit ${args.depositMicro} cannot cover prepaid input cost ${requirements.prepaidInputMicro}`,
      );
    }

    const sessionKey = args.sessionKey ?? generateSessionKey();
    const nonce = args.nonce ?? randomNonce();
    const consumerUsdc = await deriveAta(this.wallet.address, this.usdcMint);
    const { value: blockhashInfo } = await this.rpc.getLatestBlockhash().send();

    const { transactionB64, channel } = await buildAndSignOpenChannelTx({
      consumer: this.wallet,
      producer: address(requirements.producerPubkey),
      consumerUsdc,
      usdcMint: this.usdcMint,
      sessionKey: sessionKey.publicKey,
      nonce,
      depositMicro: args.depositMicro,
      inputPriceMicro: requirements.inputPriceMicro,
      outputPriceMicro: requirements.outputPriceMicro,
      prepaidInputMicro: requirements.prepaidInputMicro,
      durationSecs: requirements.durationSecs,
      disputeSecs: requirements.disputeSecs,
      trailingBuffer: requirements.trailingBufferTokens,
      blockhash: blockhashInfo.blockhash,
      lastValidBlockHeight: blockhashInfo.lastValidBlockHeight,
    });

    const payment: OpenChannelPayment = {
      scheme: SCHEME,
      network: requirements.network,
      consumerPubkey: this.wallet.address,
      sessionKey: sessionKey.publicKey,
      nonce,
      depositMicro: args.depositMicro,
      inputPriceMicro: requirements.inputPriceMicro,
      outputPriceMicro: requirements.outputPriceMicro,
      prepaidInputMicro: requirements.prepaidInputMicro,
      durationSecs: requirements.durationSecs,
      disputeSecs: requirements.disputeSecs,
      trailingBufferTokens: requirements.trailingBufferTokens,
      transactionB64,
    };

    const response = await this.fetchImpl(requirements.channelOpenUrl, {
      method: "POST",
      headers: { [HEADER_PAYMENT]: encodePayment(payment) },
    });
    if (!response.ok) {
      throw new X402Error(`channel-open POST failed: HTTP ${response.status}`);
    }
    const ackHeader = response.headers.get(HEADER_PAYMENT_RESPONSE);
    if (!ackHeader) {
      throw new X402Error(`${HEADER_PAYMENT_RESPONSE} missing from open ack`);
    }
    await response.arrayBuffer().catch(() => undefined);
    const ack = decodeResponse(ackHeader);

    const session = new ConsumerSession({
      fetchImpl: this.fetchImpl,
      requirements,
      channelId: address(ack.channelId),
      sessionKey,
      inputPriceMicro: requirements.inputPriceMicro,
      outputPriceMicro: requirements.outputPriceMicro,
      prepaidInputMicro: requirements.prepaidInputMicro,
      depositMicro: args.depositMicro,
      ...(args.evaluator !== undefined ? { evaluator: args.evaluator } : {}),
      ...(args.commitEveryTokens !== undefined
        ? { commitEveryTokens: args.commitEveryTokens }
        : {}),
    });

    // Local equality check: `channel` was derived from the SDK side; the
    // producer's ack should match. Drift here implies a PDA-seed mismatch.
    if (ack.channelId !== channel) {
      throw new X402Error(
        `producer returned channel_id ${ack.channelId} but SDK derived ${channel}`,
      );
    }

    session.openTxSignature = ack.txHash;
    return session;
  }
}

function randomNonce(): bigint {
  // The on-chain PDA seed is u64 LE; the x402 wire transports it as a JSON
  // number. Capping at 2^53 − 1 keeps the value losslessly representable on
  // both sides without changing the on-chain seed width.
  const bytes = new Uint8Array(8);
  crypto.getRandomValues(bytes);
  bytes[7] = 0;
  bytes[6] = bytes[6]! & 0x1f;
  return new DataView(bytes.buffer).getBigUint64(0, true);
}
