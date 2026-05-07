// Stat — large numeric value with a small label above and optional unit.

import type { ReactNode } from 'react'

interface Props {
  label: string
  value: ReactNode
  unit?: string
  tone?: 'default' | 'accent' | 'purple' | 'danger'
}

const valueTones: Record<NonNullable<Props['tone']>, string> = {
  default: 'text-[var(--color-text)]',
  accent:  'text-[var(--color-accent)]',
  purple:  'text-[var(--color-purple)]',
  danger:  'text-[var(--color-danger)]',
}

export function Stat({ label, value, unit, tone = 'default' }: Props) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] font-medium uppercase tracking-[0.12em] text-[var(--color-text-muted)]">
        {label}
      </span>
      <div className="flex items-baseline gap-1.5">
        <span className={`font-mono text-2xl font-medium tabular-nums ${valueTones[tone]}`}>
          {value}
        </span>
        {unit && (
          <span className="text-xs text-[var(--color-text-muted)]">{unit}</span>
        )}
      </div>
    </div>
  )
}
