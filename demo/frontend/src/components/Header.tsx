// Top bar: brand + network indicator + program-id link.

import { Hash } from './ui/Hash'
import { Pill } from './ui/Pill'
import type { ConfigResponse } from '../lib/types'

interface Props {
  config: ConfigResponse | null
}

export function Header({ config }: Props) {
  return (
    <header className="border-b border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-sm">
      <div className="mx-auto flex max-w-[1400px] items-center justify-between px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-gradient-to-br from-[var(--color-accent)] to-[var(--color-purple)]">
            <span className="font-mono text-sm font-bold text-[var(--color-bg)]">T</span>
          </div>
          <div>
            <h1 className="text-base font-semibold tracking-tight text-[var(--color-text)]">
              TAP <span className="text-[var(--color-text-dim)] font-normal">Token Access Protocol</span>
            </h1>
            <p className="text-[11px] text-[var(--color-text-muted)]">
              Streaming LLM inference settled per token on Solana
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {config && (
            <>
              <Pill tone="accent" pulse>
                {config.network.replace('solana-', '').toUpperCase()}
              </Pill>
              <div className="flex items-center gap-1.5 rounded-md border border-[var(--color-border)] bg-[var(--color-surface-2)] px-2.5 py-1.5">
                <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
                  Program
                </span>
                <Hash value={config.program_id} kind="address" label="TAP program" />
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
