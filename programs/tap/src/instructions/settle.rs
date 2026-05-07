//! `settle` — lock in the final payment split by verifying the latest signed
//! commitment. Funds stay in the vault through the dispute window; `close`
//! performs the actual token movements after the window elapses.
//!
//! This two-phase design (settle + close) mirrors Lightning's HTLC revocation
//! pattern and ensures that a stale-commitment attack can always be corrected
//! during the dispute window without needing to un-transfer already-moved funds.

use anchor_lang::prelude::*;
use anchor_lang::solana_program::sysvar::instructions::load_instruction_at_checked;

/// The Ed25519 native program (well-known constant across all Solana clusters).
/// In Solana SDK ≥ 2.x this is no longer re-exported through `solana_program`,
/// so we declare it directly from the Base58 pubkey.
const ED25519_PROGRAM_ID: Pubkey = pubkey!("Ed25519SigVerify111111111111111111111111111");

use crate::errors::TapError;
use crate::events::ChannelSettling;
use crate::state::channel::ChannelStatus;
use crate::state::commitment::CommitMessage;
use crate::Settle;

pub fn handler(ctx: Context<Settle>, commitment: CommitMessage, signature: [u8; 64]) -> Result<()> {
    let channel = &mut ctx.accounts.channel;

    require_keys_eq!(commitment.channel, channel.key(), TapError::CommitmentChannelMismatch);
    require!(
        commitment.sequence > channel.last_sequence,
        TapError::CommitmentSequenceStale
    );
    require!(
        commitment.cumulative_paid >= channel.last_cumulative_paid,
        TapError::CommitmentNonMonotonic
    );
    // Whitepaper §4.9 / §A.2: any settlement commitment must be at or above
    // the prepaid input floor — the producer's prefill cost is non-refundable.
    require!(
        commitment.cumulative_paid >= channel.prepaid_input_micro,
        TapError::CommitmentBelowPrepaidInput
    );
    require!(
        commitment.cumulative_paid <= channel.deposit_micro,
        TapError::CommitmentExceedsDeposit
    );

    verify_ed25519_sibling(
        &ctx.accounts.instructions_sysvar.to_account_info(),
        &channel.session_key,
        &commitment.message_bytes(),
        &signature,
    )?;

    let now = Clock::get()?.unix_timestamp;
    require!(now <= channel.expires_at, TapError::ChannelExpired);

    channel.last_sequence        = commitment.sequence;
    channel.last_cumulative_paid = commitment.cumulative_paid;
    channel.settled_at           = now;
    channel.status               = ChannelStatus::Settling;

    let dispute_until = now.saturating_add(channel.dispute_secs as i64);
    emit!(ChannelSettling {
        channel:      channel.key(),
        paid_micro:   commitment.cumulative_paid,
        refund_micro: channel.deposit_micro.saturating_sub(commitment.cumulative_paid),
        sequence:     commitment.sequence,
        dispute_until,
    });

    Ok(())
}

/// Locate an Ed25519Program sibling instruction and confirm its
/// `(pubkey, message, signature)` triple. The on-chain program cannot call
/// a syscall to verify Ed25519; requiring the Ed25519Program ix as a sibling
/// in the same transaction is the canonical Solana pattern for this.
pub(crate) fn verify_ed25519_sibling(
    ix_sysvar: &AccountInfo,
    expected_pubkey: &Pubkey,
    expected_message: &[u8],
    expected_signature: &[u8; 64],
) -> Result<()> {
    let mut idx: u16 = 0;
    loop {
        let Ok(ix) = load_instruction_at_checked(idx as usize, ix_sysvar) else {
            break;
        };
        idx = idx.saturating_add(1);
        if ix.program_id != ED25519_PROGRAM_ID {
            continue;
        }

        // Single-signature Ed25519Program data layout:
        //   [0]     num_signatures (u8)  = 1
        //   [1]     padding              = 0
        //   [2-3]   signature_offset     (u16 LE)
        //   [4-5]   signature_ix_index   (u16 LE) = 0xFFFF (same ix)
        //   [6-7]   public_key_offset    (u16 LE)
        //   [8-9]   public_key_ix_index  (u16 LE) = 0xFFFF
        //   [10-11] message_data_offset  (u16 LE)
        //   [12-13] message_data_size    (u16 LE)
        //   [14-15] message_ix_index     (u16 LE) = 0xFFFF
        let data = &ix.data;
        if data.len() < 16 || data[0] != 1 {
            continue;
        }
        let sig_off = u16::from_le_bytes([data[2],  data[3]])  as usize;
        let pk_off  = u16::from_le_bytes([data[6],  data[7]])  as usize;
        let msg_off = u16::from_le_bytes([data[10], data[11]]) as usize;
        let msg_len = u16::from_le_bytes([data[12], data[13]]) as usize;

        if pk_off + 32 > data.len()
            || sig_off + 64 > data.len()
            || msg_off + msg_len > data.len()
        {
            continue;
        }
        let pk  = &data[pk_off..pk_off + 32];
        let sig = &data[sig_off..sig_off + 64];
        let msg = &data[msg_off..msg_off + msg_len];

        if pk == expected_pubkey.as_ref() && sig == expected_signature && msg == expected_message {
            return Ok(());
        }
    }
    err!(TapError::InvalidCommitmentSignature)
}
