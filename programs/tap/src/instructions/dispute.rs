//! `dispute` — within the dispute window, replace a stale settlement with
//! a higher-sequence commitment. No token movements; the split is updated
//! in channel state and `close` will use it when paying out.

use anchor_lang::prelude::*;

use crate::errors::TapError;
use crate::events::ChannelDisputed;
use crate::state::commitment::CommitMessage;
use crate::Dispute;

pub fn handler(
    ctx: Context<Dispute>,
    superseding: CommitMessage,
    signature: [u8; 64],
) -> Result<()> {
    let channel = &mut ctx.accounts.channel;

    let now = Clock::get()?.unix_timestamp;
    let dispute_until = channel.settled_at.saturating_add(channel.dispute_secs as i64);
    require!(now <= dispute_until, TapError::DisputeWindowElapsed);

    require_keys_eq!(superseding.channel, channel.key(), TapError::CommitmentChannelMismatch);
    require!(
        superseding.sequence > channel.last_sequence,
        TapError::CommitmentSequenceStale
    );
    require!(
        superseding.cumulative_paid >= channel.last_cumulative_paid,
        TapError::CommitmentNonMonotonic
    );
    // Whitepaper §4.9 / §A.2: settlement floor applies to disputes too.
    require!(
        superseding.cumulative_paid >= channel.prepaid_input_micro,
        TapError::CommitmentBelowPrepaidInput
    );
    require!(
        superseding.cumulative_paid <= channel.deposit_micro,
        TapError::CommitmentExceedsDeposit
    );

    crate::instructions::settle::verify_ed25519_sibling(
        &ctx.accounts.instructions_sysvar.to_account_info(),
        &channel.session_key,
        &superseding.message_bytes(),
        &signature,
    )?;

    let previous_sequence = channel.last_sequence;

    channel.last_sequence        = superseding.sequence;
    channel.last_cumulative_paid = superseding.cumulative_paid;

    emit!(ChannelDisputed {
        channel:              channel.key(),
        previous_sequence,
        superseding_sequence: superseding.sequence,
        revised_paid_micro:   superseding.cumulative_paid,
    });

    Ok(())
}
