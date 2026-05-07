//! `open_channel` — escrow the consumer's deposit and initialize the channel PDA.
//!
//! Whitepaper §4.2.1 / §4.9. Called as the settlement leg of an x402 payment;
//! from the program's point of view it is a single SPL token transfer plus
//! the channel terms (input/output prices, prepaid input floor, trailing buffer).
//!
//! `prepaid_input_micro` is recorded here as the on-chain settlement floor: the
//! producer is guaranteed to receive at least this much regardless of subsequent
//! off-chain commitment state, compensating the irreversible prefill compute on
//! the consumer's prompt.

use anchor_lang::prelude::*;
use anchor_spl::token::{self, Transfer};

use crate::constants::{MAX_CHANNEL_DURATION_SECS, MAX_DISPUTE_WINDOW_SECS, MAX_TRAILING_BUFFER_TOKENS};
use crate::errors::TapError;
use crate::events::ChannelOpened;
use crate::state::channel::ChannelStatus;
use crate::OpenChannel;

#[allow(clippy::too_many_arguments)]
pub fn handler(
    ctx: Context<OpenChannel>,
    channel_nonce: u64,
    session_key: Pubkey,
    deposit_micro: u64,
    input_price_micro: u64,
    output_price_micro: u64,
    prepaid_input_micro: u64,
    duration_secs: u32,
    dispute_secs: u32,
    trailing_buffer: u32,
) -> Result<()> {
    require!(deposit_micro > 0, TapError::DepositZero);
    require!(input_price_micro > 0, TapError::InputPriceZero);
    require!(output_price_micro > 0, TapError::OutputPriceZero);
    require!(
        prepaid_input_micro <= deposit_micro,
        TapError::PrepaidInputExceedsDeposit
    );
    require!(duration_secs <= MAX_CHANNEL_DURATION_SECS, TapError::DurationTooLong);
    require!(dispute_secs <= MAX_DISPUTE_WINDOW_SECS, TapError::DisputeWindowTooLong);
    require!(
        trailing_buffer <= MAX_TRAILING_BUFFER_TOKENS,
        TapError::TrailingBufferTooLarge
    );

    // Trailing buffer applies to output streaming only; input cost is already
    // secured by `prepaid_input_micro` (whitepaper §4.6).
    let trailing_buffer_micro = (trailing_buffer as u64).saturating_mul(output_price_micro);

    token::transfer(
        CpiContext::new(
            ctx.accounts.token_program.to_account_info(),
            Transfer {
                from:      ctx.accounts.consumer_usdc.to_account_info(),
                to:        ctx.accounts.vault.to_account_info(),
                authority: ctx.accounts.consumer.to_account_info(),
            },
        ),
        deposit_micro,
    )?;

    let now = Clock::get()?.unix_timestamp;
    let expires_at = now.saturating_add(duration_secs as i64);

    let channel = &mut ctx.accounts.channel;
    channel.bump                  = ctx.bumps.channel;
    channel.vault_bump            = ctx.bumps.vault;
    channel.nonce                 = channel_nonce;
    channel.consumer              = ctx.accounts.consumer.key();
    channel.producer              = ctx.accounts.producer.key();
    channel.session_key           = session_key;
    channel.deposit_micro         = deposit_micro;
    channel.input_price_micro     = input_price_micro;
    channel.output_price_micro    = output_price_micro;
    channel.prepaid_input_micro   = prepaid_input_micro;
    channel.trailing_buffer_micro = trailing_buffer_micro;
    channel.last_sequence         = 0;
    channel.last_cumulative_paid  = 0;
    channel.expires_at            = expires_at;
    channel.settled_at            = 0;
    channel.dispute_secs          = dispute_secs;
    channel.status                = ChannelStatus::Active;

    emit!(ChannelOpened {
        channel: channel.key(),
        consumer: channel.consumer,
        producer: channel.producer,
        session_key: channel.session_key,
        deposit_micro,
        input_price_micro,
        output_price_micro,
        prepaid_input_micro,
        trailing_buffer,
        expires_at,
    });

    Ok(())
}
