//! `Channel` PDA state. One account per open session (or per long-lived
//! reused channel — see whitepaper §4.7).

use anchor_lang::prelude::*;

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq, Debug)]
pub enum ChannelStatus {
    /// Streaming in progress; off-chain commitments are being exchanged.
    Active,
    /// `settle` has been called; the dispute window is open.
    Settling,
    /// `close` has been called; account ready for rent reclamation.
    Closed,
}

#[account]
pub struct Channel {
    /// Bump for the channel PDA.
    pub bump: u8,
    /// Bump for the channel's USDC vault PDA.
    pub vault_bump: u8,

    /// Identifier supplied by the consumer to allow multiple channels with
    /// the same producer.
    pub nonce: u64,

    pub consumer: Pubkey,
    pub producer: Pubkey,
    /// Public key authorized to sign in-session commitments. Distinct from
    /// `consumer` so that compromise of an in-memory session key cannot drain
    /// the consumer's primary wallet (whitepaper §4.5).
    pub session_key: Pubkey,

    /// Total escrowed deposit in micro-USDC.
    pub deposit_micro: u64,
    /// Negotiated price per prompt (input) token in micro-USDC.
    /// Charged once at channel open as `prepaid_input_micro` (whitepaper §4.9).
    pub input_price_micro: u64,
    /// Negotiated price per generated (output) token in micro-USDC.
    /// Charged incrementally as output streams.
    pub output_price_micro: u64,

    /// Settlement floor recorded at channel open (whitepaper §4.9). Equal to
    /// `input_token_count × input_price_micro`. The on-chain program guarantees
    /// the producer receives at least this much at settlement, compensating the
    /// irreversible prefill compute. Enforced as `prepaid_input ≤ cumulative_paid ≤ deposit`.
    pub prepaid_input_micro: u64,

    /// Highest cumulative_paid the producer is permitted to settle without
    /// presenting a fresh signature, reflecting the trailing-buffer pre-auth
    /// (whitepaper §4.6). Computed at open as `trailing_buffer × output_price`.
    /// Applies to output streaming only; input cost is already secured by
    /// `prepaid_input_micro`.
    pub trailing_buffer_micro: u64,

    /// Latest accepted commitment sequence; monotonically increases.
    pub last_sequence: u64,
    /// Latest accepted cumulative_paid; monotonically non-decreasing.
    pub last_cumulative_paid: u64,

    /// Wall-clock deadline after which `close` is permitted regardless of
    /// dispute window (channel duration).
    pub expires_at: i64,

    /// When `settle` was called. `dispute_until = settled_at + dispute_secs`.
    pub settled_at: i64,
    /// Length of the dispute window in seconds.
    pub dispute_secs: u32,

    pub status: ChannelStatus,
}

impl Channel {
    /// Discriminator (8) plus all fixed-size fields. There are no Vecs or
    /// Strings on this account, so the layout is fully static.
    pub const SIZE: usize = 8   // discriminator
        + 1 + 1                  // bumps
        + 8                      // nonce
        + 32 + 32 + 32           // consumer, producer, session_key
        + 8                      // deposit
        + 8 + 8                  // input_price, output_price
        + 8                      // prepaid_input_micro
        + 8                      // trailing_buffer_micro
        + 8 + 8                  // last_sequence, last_cumulative_paid
        + 8                      // expires_at
        + 8 + 4                  // settled_at, dispute_secs
        + 1; // status (Anchor enum tag)
}
