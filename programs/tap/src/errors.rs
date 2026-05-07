//! Program-level error codes. One variant per failure mode the protocol can
//! reach; client code switches on these to surface meaningful messages.

use anchor_lang::prelude::*;

#[error_code]
pub enum TapError {
    #[msg("Channel is not in the active state")]
    ChannelNotActive,

    #[msg("Channel is not in the settling state")]
    ChannelNotSettling,

    #[msg("Channel is not yet eligible for close (dispute window still open)")]
    DisputeWindowOpen,

    #[msg("Dispute window has elapsed; no further disputes are accepted")]
    DisputeWindowElapsed,

    #[msg("Channel duration exceeds the protocol maximum")]
    DurationTooLong,

    #[msg("Dispute window exceeds the protocol maximum")]
    DisputeWindowTooLong,

    #[msg("Trailing buffer exceeds the protocol maximum")]
    TrailingBufferTooLarge,

    #[msg("Deposit must be positive")]
    DepositZero,

    #[msg("Input price must be positive")]
    InputPriceZero,

    #[msg("Output price must be positive")]
    OutputPriceZero,

    #[msg("Prepaid input cost exceeds the channel deposit")]
    PrepaidInputExceedsDeposit,

    #[msg("Commitment signature failed verification")]
    InvalidCommitmentSignature,

    #[msg("Commitment is for a different channel")]
    CommitmentChannelMismatch,

    #[msg("Commitment sequence is not strictly increasing")]
    CommitmentSequenceStale,

    #[msg("Commitment cumulative_paid is non-monotonic")]
    CommitmentNonMonotonic,

    #[msg("Commitment cumulative_paid is below the prepaid input floor")]
    CommitmentBelowPrepaidInput,

    #[msg("Commitment cumulative_paid exceeds the channel deposit")]
    CommitmentExceedsDeposit,

    #[msg("Channel duration has elapsed")]
    ChannelExpired,

    #[msg("Caller is not the consumer of this channel")]
    NotConsumer,

    #[msg("Caller is not the producer of this channel")]
    NotProducer,
}
