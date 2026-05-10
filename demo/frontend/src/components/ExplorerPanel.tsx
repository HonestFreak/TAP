// On-chain explorer panel: lists every confirmed tx that touched the
// session's channel PDA, with Solscan links. Polls while a session is
// live or recently closed so the close tx — which lands ~30s after the
// dispute window — appears without the user reloading.

import { useEffect, useRef, useState } from 'react'
import { fetchChannelSignatures } from '../lib/api'
import type { ChannelSignature, SessionPhase } from '../lib/types'
import { Hash } from './ui/Hash'

interface Props {
  channelId: string | null
  phase: SessionPhase
}

// Tunables: poll cadence and total active window. The on-chain `dispute_secs`
// is 30s, so close lands within ~35s; we keep polling for a couple of minutes
// past that to absorb backend cold-starts and slow RPC.
const POLL_INTERVAL_MS = 5_000
const POLL_WINDOW_MS = 3 * 60_000

export function ExplorerPanel({ channelId, phase }: Props) {
  const [signatures, setSignatures] = useState<ChannelSignature[]>([])
  const [error, setError] = useState<string | null>(null)
  const startedAtRef = useRef<number | null>(null)

  // Reset when the channel changes (new session).
  useEffect(() => {
    setSignatures([])
    setError(null)
    startedAtRef.current = channelId ? Date.now() : null
  }, [channelId])

  useEffect(() => {
    if (!channelId) return
    let cancelled = false

    const poll = async () => {
      try {
        const resp = await fetchChannelSignatures(channelId)
        if (cancelled) return
        setSignatures(resp.signatures)
        setError(null)
      } catch (err) {
        if (cancelled) return
        setError((err as Error).message)
      }
    }

    void poll()
    const id = window.setInterval(() => {
      // Stop polling once the session is fully done AND we've waited long
      // enough for close to land. Keeps RPC quiet when the user leaves the
      // tab open.
      const startedAt = startedAtRef.current
      const exhausted = phase === 'closed' && startedAt !== null
        && Date.now() - startedAt > POLL_WINDOW_MS
      if (exhausted || phase === 'error') {
        window.clearInterval(id)
        return
      }
      void poll()
    }, POLL_INTERVAL_MS)

    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [channelId, phase])

  return (
    <div className="flex flex-col rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-2.5">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-dim)]">
          On-chain transactions
        </h2>
        <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">
          {channelId ? `${signatures.length} tx` : 'no session'}
        </span>
      </div>

      <div className="divide-y divide-[var(--color-border)]">
        {!channelId && (
          <div className="px-4 py-6 text-center text-xs text-[var(--color-text-muted)]">
            Run a session to see open / settle / close land on devnet.
          </div>
        )}
        {channelId && signatures.length === 0 && !error && (
          <div className="px-4 py-6 text-center text-xs text-[var(--color-text-muted)]">
            Waiting for the first confirmation…
          </div>
        )}
        {error && (
          <div className="px-4 py-3 text-xs text-[var(--color-danger)]">
            {error}
          </div>
        )}
        {signatures.map((sig, idx) => (
          <SignatureRow key={sig.signature} signature={sig} index={idx} total={signatures.length} />
        ))}
      </div>
    </div>
  )
}

// We label rows by position rather than guessing the instruction type — open
// is always first, settle is the second TAP-program-touching tx, close is
// the last. If the order ever changes (e.g. dispute mid-flight), the labels
// will lag, but Solscan shows the actual ix for anyone who clicks through.
function labelFor(index: number, total: number): string {
  if (total === 1) return 'open'
  if (index === 0) return 'open'
  if (index === total - 1 && total >= 3) return 'close'
  if (index === total - 1) return 'settle'
  if (index === 1) return 'settle'
  return 'commit'
}

function SignatureRow({
  signature,
  index,
  total,
}: {
  signature: ChannelSignature
  index: number
  total: number
}) {
  const label = labelFor(index, total)
  const errored = signature.err !== null
  return (
    <div className="flex items-center gap-3 px-4 py-2.5">
      <span
        className={`inline-flex items-center rounded px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider ${
          errored
            ? 'bg-[var(--color-danger-dim)] text-[var(--color-danger)]'
            : 'bg-[var(--color-accent-dim)] text-[var(--color-accent)]'
        }`}
      >
        {label}
      </span>
      <div className="flex flex-1 items-center justify-between gap-3 min-w-0">
        <div className="flex items-center gap-2 text-[11px] text-[var(--color-text-muted)]">
          <span className="font-mono">slot {signature.slot}</span>
          {signature.block_time && (
            <>
              <span>·</span>
              <span>{new Date(signature.block_time * 1_000).toLocaleTimeString()}</span>
            </>
          )}
        </div>
        <Hash value={signature.signature} kind="tx" label={`${label} tx`} />
      </div>
    </div>
  )
}
