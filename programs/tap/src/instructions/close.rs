//! `close` — after the dispute window, finalize the split and reclaim rent.
//!
//! This is the only instruction that moves USDC. Keeping all token transfers
//! here (rather than in `settle`) means:
//!   1. The vault balance is the single source of truth until settlement is final.
//!   2. `dispute` can freely update `last_cumulative_paid` without reversing
//!      already-sent tokens.
//!   3. The consumer's escape hatch (channel expired, producer never settled)
//!      is the same code path.

use anchor_lang::prelude::*;
use anchor_spl::token::{self, CloseAccount, Transfer};

use crate::constants::VAULT_SEED;
use crate::errors::TapError;
use crate::events::ChannelClosed;
use crate::state::channel::ChannelStatus;
use crate::Close;

pub fn handler(ctx: Context<Close>) -> Result<()> {
    let channel = &mut ctx.accounts.channel;
    let now = Clock::get()?.unix_timestamp;

    match channel.status {
        ChannelStatus::Settling => {
            let dispute_until = channel.settled_at.saturating_add(channel.dispute_secs as i64);
            require!(now > dispute_until, TapError::DisputeWindowOpen);
        }
        ChannelStatus::Active => {
            // Consumer's escape hatch: channel has expired without the
            // producer ever calling settle. Consumer reclaims the full deposit.
            require!(now > channel.expires_at, TapError::ChannelNotSettling);
        }
        ChannelStatus::Closed => return err!(TapError::ChannelNotSettling),
    }

    // Whitepaper §4.9 / §5.3.8: the prepaid input floor is binding even on
    // the consumer's expiry escape hatch. If the producer accepted prefill
    // but the channel was never settled, the producer still receives at least
    // `prepaid_input_micro`. `settle`/`dispute` already enforce this floor
    // for the active settlement path, so the `max` here is redundant for the
    // Settling branch — and load-bearing for the Active-after-expiry branch.
    let paid   = channel.last_cumulative_paid.max(channel.prepaid_input_micro);
    let refund = channel.deposit_micro.saturating_sub(paid);

    let channel_key = channel.key();
    let vault_bump  = channel.vault_bump;
    let seeds: &[&[u8]] = &[VAULT_SEED, channel_key.as_ref(), &[vault_bump]];
    let signer_seeds: &[&[&[u8]]] = &[seeds];

    if paid > 0 {
        token::transfer(
            CpiContext::new_with_signer(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from:      ctx.accounts.vault.to_account_info(),
                    to:        ctx.accounts.producer_usdc.to_account_info(),
                    authority: ctx.accounts.vault.to_account_info(),
                },
                signer_seeds,
            ),
            paid,
        )?;
    }
    if refund > 0 {
        token::transfer(
            CpiContext::new_with_signer(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from:      ctx.accounts.vault.to_account_info(),
                    to:        ctx.accounts.consumer_usdc.to_account_info(),
                    authority: ctx.accounts.vault.to_account_info(),
                },
                signer_seeds,
            ),
            refund,
        )?;
    }

    token::close_account(CpiContext::new_with_signer(
        ctx.accounts.token_program.to_account_info(),
        CloseAccount {
            account:     ctx.accounts.vault.to_account_info(),
            destination: ctx.accounts.consumer.to_account_info(),
            authority:   ctx.accounts.vault.to_account_info(),
        },
        signer_seeds,
    ))?;

    channel.status = ChannelStatus::Closed;
    emit!(ChannelClosed { channel: channel.key() });
    Ok(())
}
