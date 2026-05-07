// Live USDC balance display for both consumer and producer wallets, with
// a manual refresh button. After a session settles, hitting refresh shows
// the on-chain payment effect without reloading the whole app.

import { useEffect, useState } from 'react'
import { Hash } from './ui/Hash'
import { fetchBalances } from '../lib/api'
import { formatUsdc } from '../lib/format'
import type { ConfigResponse } from '../lib/types'

interface Props {
  config: ConfigResponse
  refreshKey: number
}

export function BalancePanel({ config, refreshKey }: Props) {
  const [consumer, setConsumer] = useState<number | null>(null)
  const [producer, setProducer] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)

  const refresh = async () => {
    setLoading(true)
    try {
      const balances = await fetchBalances()
      setConsumer(balances.consumer_micro)
      setProducer(balances.producer_micro)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [refreshKey])

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-dim)]">
          USDC balances
        </h2>
        <button
          type="button"
          onClick={refresh}
          disabled={loading}
          className="rounded border border-[var(--color-border)] px-2 py-0.5 text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)] disabled:opacity-40 transition-colors"
        >
          {loading ? '…' : 'Refresh'}
        </button>
      </div>

      <div className="space-y-3">
        <BalanceRow
          role="Consumer"
          owner={config.consumer_pubkey}
          tokenAccount={config.consumer_usdc}
          balance={consumer}
        />
        <BalanceRow
          role="Producer"
          owner={config.producer_pubkey}
          tokenAccount={config.producer_usdc}
          balance={producer}
        />
      </div>
    </div>
  )
}

interface RowProps {
  role: string
  owner: string
  tokenAccount: string
  balance: number | null
}

function BalanceRow({ role, owner, tokenAccount, balance }: RowProps) {
  return (
    <div className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface-2)] p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
          {role}
        </span>
        <Hash value={owner} kind="address" label={`${role} wallet`} />
      </div>
      <div className="flex items-baseline justify-between">
        <div className="font-mono text-xl tabular-nums text-[var(--color-text)]">
          {balance === null ? '…' : formatUsdc(balance, 6)}
          <span className="ml-1.5 text-[11px] text-[var(--color-text-muted)]">USDC</span>
        </div>
        <Hash value={tokenAccount} kind="address" label={`${role} USDC ATA`} />
      </div>
    </div>
  )
}
