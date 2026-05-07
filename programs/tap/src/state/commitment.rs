//! `CommitMessage` is the off-chain payment authorization. The consumer's
//! session key signs a serialized form of this struct; the producer presents
//! the latest signed copy at settlement time.
//!
//! Wire-compat note: the field order, types, and sizes here MUST match the
//! Python `tap.protocol.commit.CommitMessage` codec in the SDK. Any change
//! must be made in lockstep on both sides.

use anchor_lang::prelude::*;

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, Debug, PartialEq, Eq)]
pub struct CommitMessage {
    pub channel: Pubkey,
    /// Strictly increasing per-channel sequence number.
    pub sequence: u64,
    /// Total micro-USDC the consumer authorizes to be paid if settled now.
    pub cumulative_paid: u64,
    /// Tokens delivered as of this commitment. Informational; the program
    /// settles on `cumulative_paid` alone.
    pub tokens_received: u32,
    /// Consumer-side wall-clock at signing. Used for client-side auditing
    /// only; not validated on-chain.
    pub timestamp_ms: u64,
}

impl CommitMessage {
    /// Bytes signed by the session key. Layout is the AnchorSerialize default
    /// (little-endian, no padding); Python codec reproduces this byte-for-byte.
    pub fn message_bytes(&self) -> Vec<u8> {
        let mut buf = Vec::with_capacity(32 + 8 + 8 + 4 + 8);
        buf.extend_from_slice(self.channel.as_ref());
        buf.extend_from_slice(&self.sequence.to_le_bytes());
        buf.extend_from_slice(&self.cumulative_paid.to_le_bytes());
        buf.extend_from_slice(&self.tokens_received.to_le_bytes());
        buf.extend_from_slice(&self.timestamp_ms.to_le_bytes());
        buf
    }
}
