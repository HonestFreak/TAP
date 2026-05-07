// Lifecycle timeline: shows the channel-open tx, each signed commitment as
// it arrives, and (eventually) the settle/close — chronological order with
// the newest at the top so live activity is visible without scrolling.

import { Hash } from './ui/Hash'
import { formatUsdc } from '../lib/format'
import type { CommitSignedEvent, SessionOpenEvent } from '../lib/types'

interface Props {
  channel: SessionOpenEvent | null
  commits: CommitSignedEvent[]
}

export function TimelinePanel({ channel, commits }: Props) {
  // Display newest first: open at the bottom, latest commit at top.
  const reversed = [...commits].reverse()

  return (
    <div className="flex flex-col rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
      <div className="border-b border-[var(--color-border)] px-4 py-2.5">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-dim)]">
          Channel timeline
        </h2>
      </div>

      <div className="max-h-[420px] flex-1 divide-y divide-[var(--color-border)] overflow-y-auto">
        {!channel && (
          <div className="px-4 py-8 text-center text-xs text-[var(--color-text-muted)]">
            No active channel. Run a session to see the on-chain lifecycle.
          </div>
        )}

        {reversed.map((c) => (
          <CommitRow key={c.sequence} commit={c} />
        ))}

        {channel && <OpenRow channel={channel} />}
      </div>
    </div>
  )
}

function OpenRow({ channel }: { channel: SessionOpenEvent }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border border-[var(--color-purple)]/40 bg-[var(--color-purple-dim)] font-mono text-[10px] font-semibold text-[var(--color-purple)]">
        ↗
      </div>
      <div className="flex flex-1 items-center justify-between gap-3 min-w-0">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-[var(--color-text)]">
              Channel opened
            </span>
            <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">
              on-chain
            </span>
          </div>
          <div className="mt-0.5 flex items-center gap-2 text-[11px] text-[var(--color-text-muted)]">
            <span>deposit</span>
            <span className="font-mono text-[var(--color-text-dim)]">
              {formatUsdc(channel.deposit_micro, 4)} USDC
            </span>
            <span>·</span>
            <span>channel</span>
            <Hash value={channel.channel_id} kind="address" label="channel PDA" />
          </div>
        </div>
        {channel.open_tx_signature && (
          <Hash value={channel.open_tx_signature} kind="tx" label="open tx" />
        )}
      </div>
    </div>
  )
}

function CommitRow({ commit }: { commit: CommitSignedEvent }) {
  return (
    <div className="flex items-center gap-3 px-4 py-2.5">
      <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border border-[var(--color-accent)]/40 bg-[var(--color-accent-dim)] font-mono text-[10px] font-semibold text-[var(--color-accent)]">
        {commit.sequence}
      </div>
      <div className="flex flex-1 items-baseline justify-between gap-3 min-w-0">
        <div className="text-xs">
          <span className="font-mono text-[var(--color-text)]">
            seq #{commit.sequence}
          </span>
          <span className="ml-2 text-[var(--color-text-muted)]">
            signed off-chain
          </span>
        </div>
        <div className="flex items-center gap-3 font-mono text-[11px] text-[var(--color-text-dim)]">
          <span>{commit.tokens_received} tok</span>
          <span className="text-[var(--color-accent)]">
            {formatUsdc(commit.cumulative_paid_micro, 4)} USDC
          </span>
        </div>
      </div>
    </div>
  )
}
