// Status pill — small rounded badge used for phase, network, halt status.

import type { ReactNode } from 'react'

type Tone = 'neutral' | 'accent' | 'purple' | 'danger' | 'muted'

const tones: Record<Tone, string> = {
  neutral: 'bg-[var(--color-surface-2)] text-[var(--color-text-dim)] border-[var(--color-border)]',
  accent:  'bg-[var(--color-accent-dim)] text-[var(--color-accent)] border-[var(--color-accent)]/30',
  purple:  'bg-[var(--color-purple-dim)] text-[var(--color-purple)] border-[var(--color-purple)]/30',
  danger:  'bg-[var(--color-danger-dim)] text-[var(--color-danger)] border-[var(--color-danger)]/30',
  muted:   'bg-transparent text-[var(--color-text-muted)] border-[var(--color-border)]',
}

interface Props {
  tone?: Tone
  pulse?: boolean
  children: ReactNode
}

export function Pill({ tone = 'neutral', pulse = false, children }: Props) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium tracking-wide ${tones[tone]}`}
    >
      {pulse && (
        <span className={`h-1.5 w-1.5 rounded-full bg-current ${pulse ? 'pulse-dot' : ''}`} />
      )}
      {children}
    </span>
  )
}
