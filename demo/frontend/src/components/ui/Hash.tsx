// Address/signature display — truncated, monospace, clickable to Solscan.

import { shortAddress, solscanAddressUrl, solscanTxUrl } from '../../lib/format'

interface Props {
  value: string
  kind: 'address' | 'tx'
  cluster?: string
  label?: string
}

export function Hash({ value, kind, cluster = 'devnet', label }: Props) {
  const href = kind === 'tx' ? solscanTxUrl(value, cluster) : solscanAddressUrl(value, cluster)
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer noopener"
      className="group inline-flex items-center gap-1.5 font-mono text-xs text-[var(--color-text-dim)] hover:text-[var(--color-accent)] transition-colors"
      title={`${label ? label + ': ' : ''}${value}`}
    >
      <span>{shortAddress(value, 4, 4)}</span>
      <svg
        className="h-3 w-3 opacity-50 group-hover:opacity-100 transition-opacity"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M14 3h7m0 0v7m0-7L10 14m-4-4H4a1 1 0 00-1 1v9a1 1 0 001 1h9a1 1 0 001-1v-2" />
      </svg>
    </a>
  )
}
