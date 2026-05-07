// Live token stream display. Stays terse — no formatting, just monospace
// text with a blinking cursor while streaming so the user can see exactly
// what the model emitted, character by character.

import { useEffect, useRef } from 'react'
import type { SessionPhase } from '../lib/types'

interface Props {
  text: string
  phase: SessionPhase
  haltedBy: string | null
}

export function OutputPanel({ text, phase, haltedBy }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  // Autoscroll to keep the latest tokens in view as they arrive.
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [text])

  const isStreaming = phase === 'streaming'
  const isHalted = !!haltedBy

  return (
    <div
      className={`flex flex-col rounded-lg border bg-[var(--color-surface)] overflow-hidden h-full transition-colors ${
        isHalted
          ? 'border-[var(--color-danger)]/60'
          : 'border-[var(--color-border)]'
      }`}
    >
      <div
        className={`flex items-center justify-between border-b px-4 py-2.5 ${
          isHalted ? 'border-[var(--color-danger)]/40 bg-[var(--color-danger-dim)]' : 'border-[var(--color-border)]'
        }`}
      >
        <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-dim)]">
          {isHalted ? 'Output before halt' : 'Output stream'}
        </h2>
        {isHalted && (
          <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-danger)]">
            ✕ halted by {haltedBy}
          </span>
        )}
      </div>
      <div
        ref={ref}
        className="flex-1 overflow-y-auto p-4 font-mono text-sm leading-relaxed text-[var(--color-text)]"
      >
        {text ? (
          <span className={isHalted ? 'border-b-2 border-[var(--color-danger)]/60 pb-0.5' : ''}>
            {text}
          </span>
        ) : (
          <span className="text-[var(--color-text-muted)]">
            {phase === 'opening'
              ? 'Opening channel on-chain…'
              : phase === 'idle'
              ? 'Stream a response to see live token output here.'
              : '…'}
          </span>
        )}
        {isStreaming && (
          <span className="ml-0.5 inline-block h-4 w-1.5 align-middle bg-[var(--color-accent)] pulse-dot" />
        )}
        {isHalted && text && (
          <div className="mt-3 border-t border-[var(--color-border)] pt-3 text-[11px] text-[var(--color-text-muted)]">
            Stream truncated at {text.length} chars · further generation
            cancelled, unspent deposit refunds on close.
          </div>
        )}
      </div>
    </div>
  )
}
