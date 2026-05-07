//! Protocol-wide constants. Magic numbers live here, not in code.

/// PDA seed for a channel account: ("tap-channel", consumer, producer, nonce).
pub const CHANNEL_SEED: &[u8] = b"tap-channel";

/// PDA seed for the channel's USDC vault token account.
pub const VAULT_SEED: &[u8] = b"tap-vault";

/// Maximum trailing buffer (in tokens) the program will accept at open time.
/// Caps consumer exposure on graceful disconnect (whitepaper §4.6).
pub const MAX_TRAILING_BUFFER_TOKENS: u32 = 64;

/// Maximum dispute window. Bounds the time settlement can be contested
/// (whitepaper §4.2.4).
pub const MAX_DISPUTE_WINDOW_SECS: u32 = 600;

/// Maximum channel duration. Prevents channels from being held open
/// indefinitely against the consumer's deposit (whitepaper §4.2.3).
pub const MAX_CHANNEL_DURATION_SECS: u32 = 60 * 60 * 24 * 30;
