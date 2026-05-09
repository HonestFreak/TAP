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
        <a
          href="https://tapprotocol.space"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-3 outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] rounded-md"
        >
          <img
            src="/logo.png"
            alt="TAP — Token Access Protocol"
            className="h-9 w-9 object-contain"
          />
          <div>
            <h1 className="text-base font-semibold tracking-tight text-[var(--color-text)]">
              TAP <span className="text-[var(--color-text-dim)] font-normal">Token Access Protocol</span>
            </h1>
            <p className="text-[11px] text-[var(--color-text-muted)]">
              Streaming LLM inference settled per token on Solana
            </p>
          </div>
        </a>
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
