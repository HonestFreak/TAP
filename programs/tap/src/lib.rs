//! TAP — Token Access Protocol
//!
//! On-chain settlement program for token-by-token LLM inference payments.
//! See `whitepaper §4.2` for the channel lifecycle this program implements.
//!
//! Anchor's `#[program]` macro generates `pub use crate::__client_accounts_<name>::*`
//! for each instruction, expecting the account structs' generated helper modules to
//! live at the crate root. All `#[derive(Accounts)]` structs are therefore defined here;
//! business logic lives in the `instructions::*` handler functions.

use anchor_lang::prelude::*;
use anchor_lang::solana_program::sysvar::instructions::ID as IX_SYSVAR_ID;
use anchor_spl::associated_token::AssociatedToken;
use anchor_spl::token::{Mint, Token, TokenAccount};

pub mod constants;
pub mod errors;
pub mod events;
pub mod instructions;
pub mod state;

pub use state::commitment::CommitMessage;

use constants::{CHANNEL_SEED, VAULT_SEED};
use state::channel::{Channel, ChannelStatus};

declare_id!("2tqofcitv1LHFGCLCmR9Kyke6TmArQwpHSinWWtmCje9");

// ---------------------------------------------------------------------------
// Account contexts — one struct per instruction entry point
// ---------------------------------------------------------------------------

#[derive(Accounts)]
#[instruction(channel_nonce: u64)]
pub struct OpenChannel<'info> {
    #[account(mut)]
    pub consumer: Signer<'info>,

    /// CHECK: receiver of settlement funds; stored on channel, not validated here.
    pub producer: UncheckedAccount<'info>,

    #[account(
        init,
        payer = consumer,
        space = Channel::SIZE,
        seeds = [
            CHANNEL_SEED,
            consumer.key().as_ref(),
            producer.key().as_ref(),
            &channel_nonce.to_le_bytes(),
        ],
        bump,
    )]
    pub channel: Account<'info, Channel>,

    #[account(
        init,
        payer = consumer,
        seeds = [VAULT_SEED, channel.key().as_ref()],
        bump,
        token::mint = usdc_mint,
        token::authority = vault,
    )]
    pub vault: Account<'info, TokenAccount>,

    pub usdc_mint: Account<'info, Mint>,

    #[account(
        mut,
        constraint = consumer_usdc.owner == consumer.key(),
        constraint = consumer_usdc.mint == usdc_mint.key(),
    )]
    pub consumer_usdc: Account<'info, TokenAccount>,

    pub system_program: Program<'info, System>,
    pub token_program: Program<'info, Token>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    pub rent: Sysvar<'info, Rent>,
}

#[derive(Accounts)]
pub struct Settle<'info> {
    /// Either the consumer or the producer can initiate settlement.
    #[account(mut)]
    pub caller: Signer<'info>,

    #[account(
        mut,
        has_one = consumer,
        has_one = producer,
        constraint = channel.status == ChannelStatus::Active @ errors::TapError::ChannelNotActive,
    )]
    pub channel: Account<'info, Channel>,

    /// CHECK: authoritative via has_one.
    pub consumer: UncheckedAccount<'info>,
    /// CHECK: authoritative via has_one.
    pub producer: UncheckedAccount<'info>,

    /// CHECK: validated by address constraint.
    #[account(address = IX_SYSVAR_ID)]
    pub instructions_sysvar: UncheckedAccount<'info>,
}

#[derive(Accounts)]
pub struct Dispute<'info> {
    #[account(mut)]
    pub caller: Signer<'info>,

    #[account(
        mut,
        has_one = consumer,
        has_one = producer,
        constraint = channel.status == ChannelStatus::Settling @ errors::TapError::ChannelNotSettling,
    )]
    pub channel: Account<'info, Channel>,

    /// CHECK: authoritative via has_one.
    pub consumer: UncheckedAccount<'info>,
    /// CHECK: authoritative via has_one.
    pub producer: UncheckedAccount<'info>,

    /// CHECK: validated by address constraint.
    #[account(address = IX_SYSVAR_ID)]
    pub instructions_sysvar: UncheckedAccount<'info>,
}

#[derive(Accounts)]
pub struct Close<'info> {
    #[account(mut)]
    pub caller: Signer<'info>,

    /// Rent lamports reclaimed to the consumer on account close.
    #[account(
        mut,
        close = consumer,
        has_one = consumer,
        has_one = producer,
    )]
    pub channel: Account<'info, Channel>,

    /// CHECK: rent recipient; authoritative via has_one.
    #[account(mut)]
    pub consumer: UncheckedAccount<'info>,
    /// CHECK: authoritative via has_one.
    pub producer: UncheckedAccount<'info>,

    #[account(
        mut,
        seeds = [VAULT_SEED, channel.key().as_ref()],
        bump = channel.vault_bump,
    )]
    pub vault: Account<'info, TokenAccount>,

    #[account(
        mut,
        constraint = producer_usdc.owner == producer.key(),
    )]
    pub producer_usdc: Account<'info, TokenAccount>,

    #[account(
        mut,
        constraint = consumer_usdc.owner == consumer.key(),
    )]
    pub consumer_usdc: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
}

// ---------------------------------------------------------------------------
// Program entry points — dispatch to per-instruction handler functions
// ---------------------------------------------------------------------------

#[program]
pub mod tap {
    use super::*;

    #[allow(clippy::too_many_arguments)]
    pub fn open_channel(
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
        instructions::open_channel::handler(
            ctx,
            channel_nonce,
            session_key,
            deposit_micro,
            input_price_micro,
            output_price_micro,
            prepaid_input_micro,
            duration_secs,
            dispute_secs,
            trailing_buffer,
        )
    }

    pub fn settle(
        ctx: Context<Settle>,
        commitment: CommitMessage,
        signature: [u8; 64],
    ) -> Result<()> {
        instructions::settle::handler(ctx, commitment, signature)
    }

    pub fn dispute(
        ctx: Context<Dispute>,
        superseding: CommitMessage,
        signature: [u8; 64],
    ) -> Result<()> {
        instructions::dispute::handler(ctx, superseding, signature)
    }

    pub fn close(ctx: Context<Close>) -> Result<()> {
        instructions::close::handler(ctx)
    }
}
