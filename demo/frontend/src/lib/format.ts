/** Format micro-USDC (1e-6 USDC units) as a human-readable USDC amount. */
export function formatUsdc(micro: number, fractionDigits = 6): string {
  return (micro / 1_000_000).toFixed(fractionDigits)
}

/** Truncate a base58 address for display: 4 leading + 4 trailing. */
export function shortAddress(address: string, head = 4, tail = 4): string {
  if (address.length <= head + tail + 1) return address
  return `${address.slice(0, head)}…${address.slice(-tail)}`
}

/** Solscan URL builder for a tx signature on a given Solana cluster. */
export function solscanTxUrl(signature: string, cluster = 'devnet'): string {
  return `https://solscan.io/tx/${signature}?cluster=${cluster}`
}

/** Solscan URL builder for an account address. */
export function solscanAddressUrl(address: string, cluster = 'devnet'): string {
  return `https://solscan.io/account/${address}?cluster=${cluster}`
}
