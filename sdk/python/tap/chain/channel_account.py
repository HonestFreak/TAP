"""Decoder for the on-chain `Channel` account.

Layout reflects what the **deployed** program writes, which is one revision
behind `programs/tap/src/state/channel.rs` — the deployed bytecode was
built before `prepaid_input_micro` and `trailing_buffer_micro` were added.
Account size on chain is 175 bytes (8 discriminator + 167 payload); the
source struct is 191 bytes. When the program is redeployed, this decoder
needs the two missing u64 fields added in the order the source declares.

Anchor serializes accounts as `sha256("account:<TypeName>")[:8]`
discriminator followed by Borsh-encoded fields. Channel has no Vec/String
fields, so the layout is fully static and trivial to decode without
pulling in a Borsh runtime.

Used by the settler worker (`tap.producer.settler`) to find channels whose
dispute window has closed and submit `close` for them."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import IntEnum

from solders.pubkey import Pubkey


def _account_disc(name: str) -> bytes:
    return hashlib.sha256(f"account:{name}".encode("utf-8")).digest()[:8]


CHANNEL_DISCRIMINATOR = _account_disc("Channel")


class ChannelStatus(IntEnum):
    """Mirrors the Rust `ChannelStatus` enum. Anchor serializes enums as a
    single u8 variant tag in declaration order."""
    ACTIVE = 0
    SETTLING = 1
    CLOSED = 2


@dataclass(frozen=True, slots=True)
class ChannelAccount:
    bump: int
    vault_bump: int
    nonce: int
    consumer: Pubkey
    producer: Pubkey
    session_key: Pubkey
    deposit_micro: int
    input_price_micro: int
    output_price_micro: int
    last_sequence: int
    last_cumulative_paid: int
    expires_at: int
    settled_at: int
    dispute_secs: int
    status: ChannelStatus


# Byte offsets inside account data (including the leading 8-byte discriminator).
# Useful for `getProgramAccounts` memcmp filters: the RPC compares against the
# raw account bytes, not the post-discriminator payload.
DISCRIMINATOR_LEN = 8
PRODUCER_OFFSET = DISCRIMINATOR_LEN + 1 + 1 + 8 + 32  # past bumps, nonce, consumer
STATUS_OFFSET = (
    DISCRIMINATOR_LEN
    + 1 + 1                # bump, vault_bump
    + 8                    # nonce
    + 32 + 32 + 32         # consumer, producer, session_key
    + 8 + 8 + 8            # deposit, input_price, output_price
    + 8 + 8                # last_sequence, last_cumulative_paid
    + 8                    # expires_at
    + 8 + 4                # settled_at, dispute_secs
)
ACCOUNT_SIZE = STATUS_OFFSET + 1


def decode_channel(data: bytes) -> ChannelAccount:
    """Deserialize a Channel account's raw bytes. Raises if the discriminator
    or the trailing length do not match what the on-chain layout demands."""
    if len(data) < ACCOUNT_SIZE:
        raise ValueError(
            f"Channel account too small: got {len(data)} bytes, "
            f"expected at least {ACCOUNT_SIZE}"
        )
    if data[:DISCRIMINATOR_LEN] != CHANNEL_DISCRIMINATOR:
        raise ValueError("account discriminator does not match Channel")

    o = DISCRIMINATOR_LEN
    bump = data[o]; o += 1
    vault_bump = data[o]; o += 1
    nonce = int.from_bytes(data[o:o + 8], "little"); o += 8
    consumer = Pubkey.from_bytes(data[o:o + 32]); o += 32
    producer = Pubkey.from_bytes(data[o:o + 32]); o += 32
    session_key = Pubkey.from_bytes(data[o:o + 32]); o += 32
    deposit_micro = int.from_bytes(data[o:o + 8], "little"); o += 8
    input_price_micro = int.from_bytes(data[o:o + 8], "little"); o += 8
    output_price_micro = int.from_bytes(data[o:o + 8], "little"); o += 8
    last_sequence = int.from_bytes(data[o:o + 8], "little"); o += 8
    last_cumulative_paid = int.from_bytes(data[o:o + 8], "little"); o += 8
    # Solana clock timestamps are i64 seconds; can technically be negative in
    # tests with custom validators, so decode signed.
    expires_at = int.from_bytes(data[o:o + 8], "little", signed=True); o += 8
    settled_at = int.from_bytes(data[o:o + 8], "little", signed=True); o += 8
    dispute_secs = int.from_bytes(data[o:o + 4], "little"); o += 4
    status = ChannelStatus(data[o])

    return ChannelAccount(
        bump=bump,
        vault_bump=vault_bump,
        nonce=nonce,
        consumer=consumer,
        producer=producer,
        session_key=session_key,
        deposit_micro=deposit_micro,
        input_price_micro=input_price_micro,
        output_price_micro=output_price_micro,
        last_sequence=last_sequence,
        last_cumulative_paid=last_cumulative_paid,
        expires_at=expires_at,
        settled_at=settled_at,
        dispute_secs=dispute_secs,
        status=status,
    )
