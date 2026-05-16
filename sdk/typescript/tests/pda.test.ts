/**
 * PDA derivation parity test. Mirrors `sdk/python/tests/test_pda_parity.py`.
 * Guards against accidental seed renames; full cluster-level parity is
 * covered by the Anchor test suite.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { address } from "@solana/kit";

import {
  CHANNEL_SEED,
  VAULT_SEED,
  deriveChannelPda,
  deriveVaultPda,
} from "../src/chain/pda.js";

describe("PDA seeds", () => {
  it("seed bytes are stable", () => {
    assert.deepEqual(CHANNEL_SEED, new TextEncoder().encode("tap-channel"));
    assert.deepEqual(VAULT_SEED, new TextEncoder().encode("tap-vault"));
  });

  it("channel + vault PDAs are deterministic", async () => {
    const consumer = address("11111111111111111111111111111112");
    const producer = address("11111111111111111111111111111113");

    const [pda1, bump1] = await deriveChannelPda(consumer, producer, 7n);
    const [pda2, bump2] = await deriveChannelPda(consumer, producer, 7n);
    assert.equal(pda1, pda2);
    assert.equal(bump1, bump2);

    const [vault1, vbump1] = await deriveVaultPda(pda1);
    const [vault2, vbump2] = await deriveVaultPda(pda1);
    assert.equal(vault1, vault2);
    assert.equal(vbump1, vbump2);

    const [otherPda] = await deriveChannelPda(consumer, producer, 8n);
    assert.notEqual(otherPda, pda1);
  });
});
