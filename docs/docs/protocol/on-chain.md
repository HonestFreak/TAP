---
title: On-chain interface
sidebar_position: 1
---

# On-chain interface

The TAP Anchor program lives at `programs/tap/` in the repo. Four
instructions; one Channel PDA per session.

Devnet program ID: `2tqofcitv1LHFGCLCmR9Kyke6TmArQwpHSinWWtmCje9`

## Channel state

```rust
#[account]
pub struct Channel {
    pub bump: u8,
    pub vault_bump: u8,
    pub nonce: u64,

    pub consumer: Pubkey,
    pub producer: Pubkey,
    pub session_key: Pubkey,

    pub deposit_micro: u64,
    pub input_price_micro: u64,
    pub output_price_micro: u64,
    pub prepaid_input_micro: u64,        // settlement floor (§4.9)
    pub trailing_buffer_micro: u64,      // off-chain pacing hint (§4.6)

    pub last_sequence: u64,              // monotonically increasing
    pub last_cumulative_paid: u64,       // monotonically non-decreasing

    pub expires_at: i64,
    pub settled_at: i64,
    pub dispute_secs: u32,
    pub status: ChannelStatus,           // Active | Settling | Closed
}
```

## Instructions

### `open_channel`

```rust
open_channel(
    channel_nonce:       u64,
    session_key:         Pubkey,
    deposit_micro:       u64,
    input_price_micro:   u64,
    output_price_micro:  u64,
    prepaid_input_micro: u64,
    duration_secs:       u32,
    dispute_secs:        u32,
    trailing_buffer:     u32,
)
```

Creates a new channel PDA and transfers `deposit_micro` USDC into the
vault. Registers `session_key` as the authorized signer for in-session
commitments. Records `prepaid_input_micro` as the on-chain settlement
floor: at any subsequent `settle` or `close`, the producer is guaranteed
to receive at least that much regardless of off-chain commitment state.

PDA seeds: `["tap-channel", consumer, producer, channel_nonce]`.
Vault seeds: `["tap-vault", channel_pda]`.

### `settle`

```rust
settle(
    commitment:       CommitMessage,
    signature:        [u8; 64],
)
```

Verifies the Ed25519 signature against the channel's `session_key` (via
a sibling Ed25519Program ix in the same transaction), validates
`commitment.sequence > channel.last_sequence` and `commitment.cumulative_paid
>= channel.last_cumulative_paid`, then enforces

```
prepaid_input_micro ≤ cumulative_paid ≤ deposit_micro
```

On success, records the latest accepted state and transitions the
channel to `Settling`, opening the dispute window. **No tokens move
yet** — that happens in `close`.

### `dispute`

```rust
dispute(
    superseding:       CommitMessage,
    signature:         [u8; 64],
)
```

Within the dispute window, accepts a higher-sequence commitment and
adjusts `last_cumulative_paid` accordingly. Same invariants as `settle`.
Reverses any over-refund or under-payment from the initial settle —
no funds have moved yet, so this is a state-only update.

### `close`

```rust
close()
```

After the dispute window (`Settling` status) **or** after channel
expiry (`Active` status — the consumer's escape hatch), finalises the
split:

```
let paid   = max(channel.last_cumulative_paid, channel.prepaid_input_micro);
let refund = channel.deposit_micro - paid;
```

The `max` is load-bearing on the expiry escape hatch: if the producer
accepted prefill but never settled, the producer still receives at
least `prepaid_input_micro`. After `settle`/`dispute` paths the floor
is already enforced, so the `max` is redundant there but safe.

`paid` flows from the channel vault to the producer's USDC ATA;
`refund` to the consumer's. The vault and channel accounts are closed,
rent reclaimed to the consumer.

## Channel reuse

The channel state machine has no notion of "request" — a session is
just a stretch of streaming inside an active channel. A consumer that
expects to make many requests against the same producer can:

1. Open a channel once with a larger deposit.
2. Run many sessions through it (each ending with the producer's
   commit-update being held, not settled).
3. Settle the channel only periodically (daily, weekly, when the
   deposit nears exhaustion).

This drives per-session protocol overhead toward zero for high-volume
consumers.
