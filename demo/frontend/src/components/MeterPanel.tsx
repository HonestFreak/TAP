// Live cost meter. Aggregates the four numbers a viewer cares about during
// the demo: tokens received, USDC paid, deposit consumed %, halt status.

import { Pill } from './ui/Pill'
import { Stat } from './ui/Stat'
import { formatUsdc } from '../lib/format'
import type { SessionPhase } from '../lib/types'

interface Props {
  tokens: number
  paidMicro: number
  /** input_token_count × input_price_micro, locked at channel open (whitepaper §4.9). */
  prepaidInputMicro: number
  depositMicro: number
  phase: SessionPhase
  haltedBy: string | null
  commitsCount: number
}

const phaseLabels: Record<SessionPhase, string> = {
  idle:      'Idle',
  opening:   'Opening channel',
  streaming: 'Streaming',
  settling:  'Settling',
  closed:    'Settled',
  error:     'Error',
}

const phaseTones: Record<SessionPhase, Parameters<typeof Pill>[0]['tone']> = {
  idle:      'muted',
  opening:   'purple',
  streaming: 'accent',
  settling:  'purple',
  closed:    'accent',
  error:     'danger',
}

export function MeterPanel({
  tokens,
  paidMicro,
  prepaidInputMicro,
  depositMicro,
  phase,
  haltedBy,
  commitsCount,
}: Props) {
  const consumedPct = depositMicro > 0 ? (paidMicro / depositMicro) * 100 : 0
  const refundMicro = Math.max(0, depositMicro - paidMicro)
  // Output spend = total - prepaid input floor (whitepaper §4.9).
  const outputPaidMicro = Math.max(0, paidMicro - prepaidInputMicro)

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-dim)]">
          TAP Meter
        </h2>
        <Pill
          tone={phaseTones[phase]}
          pulse={phase === 'streaming' || phase === 'opening'}
        >
          {phaseLabels[phase]}
        </Pill>
      </div>

      <div className="grid grid-cols-2 gap-5">
        <Stat label="Output tokens" value={tokens.toLocaleString()} />
        <Stat
          label="Paid"
          value={formatUsdc(paidMicro)}
          unit="USDC"
          tone="accent"
        />
        <Stat
          label="Prepaid input"
          value={formatUsdc(prepaidInputMicro)}
          unit="USDC"
        />
        <Stat
          label="Output spend"
          value={formatUsdc(outputPaidMicro)}
          unit="USDC"
          tone="accent"
        />
        <Stat
          label="Refundable"
          value={formatUsdc(refundMicro)}
          unit="USDC"
          tone="purple"
        />
        <Stat
          label="Commits"
          value={commitsCount.toString()}
        />
      </div>

      <div className="mt-5">
        <div className="mb-1.5 flex items-center justify-between text-[10px] uppercase tracking-wider">
          <span className="font-medium text-[var(--color-text-muted)]">Deposit consumed</span>
          <span className="font-mono text-[var(--color-text-dim)]">
            {consumedPct.toFixed(1)}%
          </span>
        </div>
        <div className="relative h-1.5 overflow-hidden rounded-full bg-[var(--color-surface-2)]">
          <div
            className="absolute inset-y-0 left-0 bg-gradient-to-r from-[var(--color-accent)] to-[var(--color-purple)] transition-all duration-300"
            style={{ width: `${Math.min(100, consumedPct)}%` }}
          />
        </div>
      </div>

      {haltedBy && (
        <div className="mt-4 rounded border border-[var(--color-danger)]/30 bg-[var(--color-danger-dim)] p-3 text-xs">
          <div className="font-mono font-semibold text-[var(--color-danger)]">
            Evaluator halted
          </div>
          <div className="mt-1 text-[var(--color-text-dim)]">
            <span className="text-[var(--color-text)]">{haltedBy}</span> rejected the
            stream. The unspent deposit will refund on close.
          </div>
        </div>
      )}
    </div>
  )
}
