// Wire types — must mirror the SSE event shapes emitted by demo/runner.py.
// Keeping these in one file lets the rest of the app import a single union
// and switch on `type` exhaustively.

export interface ConfigResponse {
  consumer_pubkey: string
  consumer_usdc: string
  producer_pubkey: string
  producer_usdc: string
  network: string
  rpc_url: string
  program_id: string
  usdc_mint: string
  producer_url: string
}

export interface BalancesResponse {
  consumer_micro: number
  producer_micro: number
}

export type SessionPhase = 'idle' | 'opening' | 'streaming' | 'settling' | 'closed' | 'error'

export interface PhaseEvent {
  type: 'phase'
  phase: SessionPhase
}

export interface SessionOpenEvent {
  type: 'session_open'
  channel_id: string
  session_pubkey: string
  open_tx_signature: string | null
  deposit_micro: number
  /** input_token_count × input_price_micro, locked on-chain at open time
   *  (whitepaper §4.9). The producer is guaranteed at least this much
   *  regardless of subsequent off-chain commitments. */
  prepaid_input_micro: number
}

export interface TokenEvent {
  type: 'token'
  text: string
  tokens_received: number
  cumulative_paid_micro: number
}

export interface CommitSignedEvent {
  type: 'commit_signed'
  sequence: number
  cumulative_paid_micro: number
  tokens_received: number
  timestamp_ms: number
}

export interface CompleteEvent {
  type: 'complete'
  tokens_received: number
  cumulative_paid_micro: number
  halted_by: string | null
}

export interface ErrorEvent {
  type: 'error'
  message: string
}

export type SessionEvent =
  | PhaseEvent
  | SessionOpenEvent
  | TokenEvent
  | CommitSignedEvent
  | CompleteEvent
  | ErrorEvent
