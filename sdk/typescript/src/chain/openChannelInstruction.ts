/**
 * Builder for the `open_channel` instruction.
 *
 * Argument layout MUST match the Anchor handler signature in
 * `programs/tap/src/lib.rs::open_channel` and the Python builder in
 * `sdk/python/tap/chain/instructions.py`. Order: discriminator (8), nonce
 * (u64 LE), session_key (32), deposit (u64 LE), input_price (u64 LE),
 * output_price (u64 LE), prepaid_input (u64 LE), duration_secs (u32 LE),
 * dispute_secs (u32 LE), trailing_buffer (u32 LE).
 *
 * Returned as a `@solana/kit` `IInstruction` ready to drop into a transaction
 * message — composition with compute-budget or priority-fee ixs happens at
 * the caller site.
 */

import {
  AccountRole,
  getAddressEncoder,
  type Address,
  type IInstruction,
} from "@solana/kit";

import { OPEN_CHANNEL } from "./discriminator.js";
import { deriveChannelPda, deriveVaultPda } from "./pda.js";
import {
  ASSOCIATED_TOKEN_PROGRAM_ID,
  PROGRAM_ID,
  RENT_SYSVAR,
  SYSTEM_PROGRAM_ID,
  TOKEN_PROGRAM_ID,
} from "./programId.js";

const ADDR = getAddressEncoder();

export interface OpenChannelArgs {
  consumer: Address;
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
}

export interface OpenChannelInstruction {
  channel: Address;
  vault: Address;
  instruction: IInstruction;
}

export async function buildOpenChannelInstruction(
  args: OpenChannelArgs,
): Promise<OpenChannelInstruction> {
  const [channel] = await deriveChannelPda(args.consumer, args.producer, args.nonce);
  const [vault] = await deriveVaultPda(channel);

  const data = encodeOpenChannelData(args);

  const instruction: IInstruction = {
    programAddress: PROGRAM_ID,
    accounts: [
      { address: args.consumer, role: AccountRole.WRITABLE_SIGNER },
      { address: args.producer, role: AccountRole.READONLY },
      { address: channel, role: AccountRole.WRITABLE },
      { address: vault, role: AccountRole.WRITABLE },
      { address: args.usdcMint, role: AccountRole.READONLY },
      { address: args.consumerUsdc, role: AccountRole.WRITABLE },
      { address: SYSTEM_PROGRAM_ID, role: AccountRole.READONLY },
      { address: TOKEN_PROGRAM_ID, role: AccountRole.READONLY },
      { address: ASSOCIATED_TOKEN_PROGRAM_ID, role: AccountRole.READONLY },
      { address: RENT_SYSVAR, role: AccountRole.READONLY },
    ],
    data,
  };

  return { channel, vault, instruction };
}

function encodeOpenChannelData(args: OpenChannelArgs): Uint8Array {
  // 8 (disc) + 8 (nonce) + 32 (session_key) + 8*4 (price/deposit fields)
  //   + 4*3 (duration/dispute/trailing_buffer) = 92 bytes total.
  const buf = new Uint8Array(8 + 8 + 32 + 8 + 8 + 8 + 8 + 4 + 4 + 4);
  const view = new DataView(buf.buffer);
  let offset = 0;

  buf.set(OPEN_CHANNEL, offset); offset += 8;
  view.setBigUint64(offset, args.nonce, true); offset += 8;
  buf.set(ADDR.encode(args.sessionKey), offset); offset += 32;
  view.setBigUint64(offset, args.depositMicro, true); offset += 8;
  view.setBigUint64(offset, args.inputPriceMicro, true); offset += 8;
  view.setBigUint64(offset, args.outputPriceMicro, true); offset += 8;
  view.setBigUint64(offset, args.prepaidInputMicro, true); offset += 8;
  view.setUint32(offset, args.durationSecs, true); offset += 4;
  view.setUint32(offset, args.disputeSecs, true); offset += 4;
  view.setUint32(offset, args.trailingBuffer, true); offset += 4;

  return buf;
}
