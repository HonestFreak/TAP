//! On-chain events emitted at every channel state transition. Indexers and
//! settlement watchers consume these instead of scanning account writes.

use anchor_lang::prelude::*;

#[event]
pub struct ChannelOpened {
    pub channel: Pubkey,
    pub consumer: Pubkey,
    pub producer: Pubkey,
    pub session_key: Pubkey,
    pub deposit_micro: u64,
    pub input_price_micro: u64,
    pub output_price_micro: u64,
    pub prepaid_input_micro: u64,
    pub trailing_buffer: u32,
    pub expires_at: i64,
}

#[event]
pub struct ChannelSettling {
    pub channel: Pubkey,
    pub paid_micro: u64,
    pub refund_micro: u64,
    pub sequence: u64,
    pub dispute_until: i64,
}

#[event]
pub struct ChannelDisputed {
    pub channel: Pubkey,
    pub previous_sequence: u64,
    pub superseding_sequence: u64,
    pub revised_paid_micro: u64,
}

#[event]
pub struct ChannelClosed {
    pub channel: Pubkey,
}
