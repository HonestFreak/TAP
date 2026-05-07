"""PDA derivation parity test.

`derive_channel_pda` and `derive_vault_pda` mirror the seeds defined in
`programs/tap/src/constants.rs`. If the seeds drift, channels created by
the SDK will not be recognized by the on-chain program. We can't test
against the real Anchor here without `solana-test-validator`, but we can
at least guard against accidental seed renames."""

from __future__ import annotations

from solders.pubkey import Pubkey

from tap.chain.pda import CHANNEL_SEED, VAULT_SEED, derive_channel_pda, derive_vault_pda


def test_seeds_are_stable() -> None:
    assert CHANNEL_SEED == b"tap-channel"
    assert VAULT_SEED == b"tap-vault"


def test_pda_is_deterministic() -> None:
    consumer = Pubkey.from_string("11111111111111111111111111111112")
    producer = Pubkey.from_string("11111111111111111111111111111113")
    nonce = 7

    pda1, bump1 = derive_channel_pda(consumer, producer, nonce)
    pda2, bump2 = derive_channel_pda(consumer, producer, nonce)
    assert pda1 == pda2 and bump1 == bump2

    vault1, vbump1 = derive_vault_pda(pda1)
    vault2, vbump2 = derive_vault_pda(pda1)
    assert vault1 == vault2 and vbump1 == vbump2

    other_pda, _ = derive_channel_pda(consumer, producer, nonce + 1)
    assert other_pda != pda1
