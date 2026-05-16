/**
 * Build, sign, and base64-encode the channel-open transaction.
 *
 * The consumer doesn't submit the tx itself — it sends the signed bytes via
 * `X-PAYMENT` and the producer (or an x402 facilitator) forwards to the
 * cluster. This module keeps the transaction-building concerns separate
 * from the HTTP/x402 plumbing in `client.ts`.
 */

import {
  appendTransactionMessageInstructions,
  createTransactionMessage,
  getBase64EncodedWireTransaction,
  setTransactionMessageFeePayer,
  setTransactionMessageLifetimeUsingBlockhash,
  signTransactionMessageWithSigners,
  type Address,
  type Blockhash,
  type TransactionSigner,
} from "@solana/kit";

import { buildOpenChannelInstruction } from "../chain/openChannelInstruction.js";

export interface BuildOpenChannelTxArgs {
  consumer: TransactionSigner;
  producer: Address;
  consumerUsdc: Address;
  usdcMint: Address;
  sessionKey: Address;
  nonce: bigint;
  depositMicro: bigint;
  inputPriceMicro: bigint;
  outputPriceMicro: bigint;
  prepaidInputMicro: bigint;
  durationSecs: number;
  disputeSecs: number;
  trailingBuffer: number;
  blockhash: Blockhash;
  lastValidBlockHeight: bigint;
}

export interface OpenChannelTxResult {
  /** Base64-encoded signed wire transaction, ready for `X-PAYMENT`. */
  transactionB64: string;
  channel: Address;
}

export async function buildAndSignOpenChannelTx(
  args: BuildOpenChannelTxArgs,
): Promise<OpenChannelTxResult> {
  const { instruction, channel } = await buildOpenChannelInstruction({
    consumer: args.consumer.address,
    producer: args.producer,
    consumerUsdc: args.consumerUsdc,
    usdcMint: args.usdcMint,
    sessionKey: args.sessionKey,
    nonce: args.nonce,
    depositMicro: args.depositMicro,
    inputPriceMicro: args.inputPriceMicro,
    outputPriceMicro: args.outputPriceMicro,
    prepaidInputMicro: args.prepaidInputMicro,
    durationSecs: args.durationSecs,
    disputeSecs: args.disputeSecs,
    trailingBuffer: args.trailingBuffer,
  });

  const message = createTransactionMessage({ version: 0 });
  const withFeePayer = setTransactionMessageFeePayer(args.consumer.address, message);
  const withBlockhash = setTransactionMessageLifetimeUsingBlockhash(
    { blockhash: args.blockhash, lastValidBlockHeight: args.lastValidBlockHeight },
    withFeePayer,
  );
  const withIx = appendTransactionMessageInstructions([instruction], withBlockhash);

  const signed = await signTransactionMessageWithSigners(withIx);
  return {
    transactionB64: getBase64EncodedWireTransaction(signed),
    channel,
  };
}
