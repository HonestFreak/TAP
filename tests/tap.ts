/**
 * Smoke test: TAP channel full lifecycle on a local validator.
 *
 * Flow: open_channel → settle (state-only) → [dispute window elapses] → close (funds move)
 *
 * The ed25519 verify ix is constructed inline to mirror what the SDK does;
 * the settle instruction finds it via the instructions sysvar.
 *
 * The settlement commitment must clear the prepaid-input floor recorded at
 * open time (whitepaper §4.9); cumulative_paid_micro = prepaid_input + output cost.
 */
import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import {
  Ed25519Program,
  Keypair,
  LAMPORTS_PER_SOL,
  PublicKey,
  SystemProgram,
  SYSVAR_INSTRUCTIONS_PUBKEY,
  SYSVAR_RENT_PUBKEY,
  Transaction,
} from "@solana/web3.js";
import {
  ASSOCIATED_TOKEN_PROGRAM_ID,
  TOKEN_PROGRAM_ID,
  createMint,
  createAssociatedTokenAccount,
  mintTo,
  getAccount,
} from "@solana/spl-token";
import { assert } from "chai";
import * as nacl from "tweetnacl";

import { Tap } from "../target/types/tap";

const CHANNEL_SEED = Buffer.from("tap-channel");
const VAULT_SEED   = Buffer.from("tap-vault");

describe("tap", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);
  const program = anchor.workspace.Tap as Program<Tap>;

  let usdcMint: PublicKey;
  let consumer: Keypair;
  let producer: Keypair;
  let consumerUsdc: PublicKey;
  let producerUsdc: PublicKey;
  let sessionKp: nacl.SignKeyPair;

  const DEPOSIT       = 1_000_000n;   // 1 USDC (6 decimals)
  const INPUT_PRICE   = 1n;
  const OUTPUT_PRICE  = 5n;
  const INPUT_TOKENS  = 100n;
  const PREPAID_INPUT = INPUT_TOKENS * INPUT_PRICE;  // 100
  const DURATION      = 600;
  const DISPUTE       = 5;            // 5 s — short for test
  const TRAILING      = 10;

  before(async () => {
    consumer  = Keypair.generate();
    producer  = Keypair.generate();
    sessionKp = nacl.sign.keyPair();

    for (const kp of [consumer, producer]) {
      const sig = await provider.connection.requestAirdrop(kp.publicKey, 5 * LAMPORTS_PER_SOL);
      await provider.connection.confirmTransaction(sig);
    }

    usdcMint = await createMint(
      provider.connection, consumer, consumer.publicKey, null, 6,
    );
    consumerUsdc = await createAssociatedTokenAccount(
      provider.connection, consumer, usdcMint, consumer.publicKey,
    );
    producerUsdc = await createAssociatedTokenAccount(
      provider.connection, producer, usdcMint, producer.publicKey,
    );
    await mintTo(provider.connection, consumer, usdcMint, consumerUsdc, consumer, 5_000_000n);
  });

  it("open → settle → close", async () => {
    const nonce = new anchor.BN(1);
    const [channel] = PublicKey.findProgramAddressSync(
      [
        CHANNEL_SEED,
        consumer.publicKey.toBuffer(),
        producer.publicKey.toBuffer(),
        nonce.toArrayLike(Buffer, "le", 8),
      ],
      program.programId,
    );
    const [vault] = PublicKey.findProgramAddressSync(
      [VAULT_SEED, channel.toBuffer()],
      program.programId,
    );

    // ── open ──────────────────────────────────────────────────────────────────
    await program.methods
      .openChannel(
        nonce,
        new PublicKey(sessionKp.publicKey),
        new anchor.BN(DEPOSIT.toString()),
        new anchor.BN(INPUT_PRICE.toString()),
        new anchor.BN(OUTPUT_PRICE.toString()),
        new anchor.BN(PREPAID_INPUT.toString()),
        DURATION, DISPUTE, TRAILING,
      )
      .accounts({
        consumer: consumer.publicKey,
        producer: producer.publicKey,
        channel,
        vault,
        usdcMint,
        consumerUsdc,
        systemProgram: SystemProgram.programId,
        tokenProgram: TOKEN_PROGRAM_ID,
        associatedTokenProgram: ASSOCIATED_TOKEN_PROGRAM_ID,
        rent: SYSVAR_RENT_PUBKEY,
      })
      .signers([consumer])
      .rpc();

    const vaultAfterOpen = await getAccount(provider.connection, vault);
    assert.equal(vaultAfterOpen.amount, DEPOSIT, "vault should hold full deposit");

    // ── settle (state-only, no fund movement) ─────────────────────────────────
    // cumulative_paid = prepaid_input + (output tokens × output_price)
    const sequence       = 1n;
    const outputTokens   = 9_900n;
    const cumulativePaid = PREPAID_INPUT + outputTokens * OUTPUT_PRICE;  // 100 + 49,500 = 49,600
    const tokensReceived = Number(outputTokens);
    const timestampMs    = BigInt(Date.now());

    const message = Buffer.concat([
      channel.toBuffer(),
      bnLE(sequence,                  8),
      bnLE(cumulativePaid,            8),
      bnLE(BigInt(tokensReceived),    4),
      bnLE(timestampMs,               8),
    ]);
    const signature = nacl.sign.detached(message, sessionKp.secretKey);

    const verifyIx = Ed25519Program.createInstructionWithPublicKey({
      publicKey: sessionKp.publicKey,
      message,
      signature,
    });
    const settleIx = await program.methods
      .settle(
        {
          channel,
          sequence:       new anchor.BN(sequence.toString()),
          cumulativePaid: new anchor.BN(cumulativePaid.toString()),
          tokensReceived,
          timestampMs:    new anchor.BN(timestampMs.toString()),
        } as any,
        Array.from(signature),
      )
      .accounts({
        caller: producer.publicKey,
        channel,
        consumer: consumer.publicKey,
        producer: producer.publicKey,
        instructionsSysvar: SYSVAR_INSTRUCTIONS_PUBKEY,
      })
      .instruction();

    const settleTx = new Transaction().add(verifyIx, settleIx);
    await provider.sendAndConfirm(settleTx, [producer]);

    // vault still holds everything
    const vaultAfterSettle = await getAccount(provider.connection, vault);
    assert.equal(vaultAfterSettle.amount, DEPOSIT, "vault untouched after settle");

    // ── wait for dispute window to elapse (5 s) ───────────────────────────────
    await new Promise((r) => setTimeout(r, 6_000));

    // ── close (fund movement) ─────────────────────────────────────────────────
    await program.methods
      .close()
      .accounts({
        caller: producer.publicKey,
        channel,
        consumer: consumer.publicKey,
        producer: producer.publicKey,
        vault,
        producerUsdc,
        consumerUsdc,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .signers([producer])
      .rpc();

    const producerBal = (await getAccount(provider.connection, producerUsdc)).amount;
    const consumerBal = (await getAccount(provider.connection, consumerUsdc)).amount;
    assert.equal(producerBal, cumulativePaid, "producer receives committed amount");
    assert.equal(consumerBal, 5_000_000n - DEPOSIT + (DEPOSIT - cumulativePaid),
      "consumer gets initial balance minus what was paid");
  });
});

function bnLE(value: bigint, bytes: number): Buffer {
  const buf = Buffer.alloc(bytes);
  for (let i = 0; i < bytes; i++) {
    buf[i] = Number((value >> BigInt(8 * i)) & 0xffn);
  }
  return buf;
}
