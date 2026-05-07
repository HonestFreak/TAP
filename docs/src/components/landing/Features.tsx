import React from 'react';
import Link from '@docusaurus/Link';
import styles from './Features.module.css';

const FEATURES: {
  icon: JSX.Element;
  title: string;
  body: string;
  to: string;
  toLabel: string;
}[] = [
  {
    icon: <Bilateral />,
    title: 'Bilateral halt',
    body:
      'Either party stops by ceasing their next action. No explicit halt message, no attack surface, no DoS vector. The session settles at the token boundary you chose.',
    to: '/concepts/halt-and-bounded-loss',
    toLabel: 'How halt works',
  },
  {
    icon: <PrepaidInput />,
    title: 'Input prepay (§4.9)',
    body:
      "Producer's prefill compute is non-refundable but bounded. The consumer locally re-tokenizes the prompt with the producer's declared tokenizer; mismatch aborts before any escrow.",
    to: '/concepts/input-prepay',
    toLabel: 'Read §4.9',
  },
  {
    icon: <X402 />,
    title: 'Built on x402',
    body:
      "TAP extends Coinbase's x402 standard into variable-cost streaming. Discovery, channel-open, and settlement compose with existing x402 facilitators with no contradictions.",
    to: '/concepts/x402-relationship',
    toLabel: 'x402 relationship',
  },
  {
    icon: <Solana />,
    title: 'Solana-native',
    body:
      'Anchor program enforces prepaid_input ≤ cumulative_paid ≤ deposit and the dispute-window state machine. Fast finality, sub-cent fees, PDAs as channel state.',
    to: '/protocol/on-chain',
    toLabel: 'On-chain interface',
  },
  {
    icon: <Eval />,
    title: 'Pluggable evaluators',
    body:
      'Halt-on-quality is application-level. Compose JSON-schema, length, repetition, topic-drift, content-policy. Or write a callable that returns Decision.HALT — the SDK handles the rest.',
    to: '/sdk/evaluators',
    toLabel: 'Evaluators',
  },
  {
    icon: <Substrate />,
    title: 'A streaming substrate',
    body:
      'The same channel construction maps to audio, video, GPU rental, metered APIs. Drops are tokens; per-second metering is just a different unit. LLM inference is the showcase, not the limit.',
    to: '/beyond-llm/overview',
    toLabel: 'Beyond LLM',
  },
];

export default function Features(): JSX.Element {
  return (
    <section className={styles.wrap}>
      <div className={styles.head}>
        <h2 className={styles.h2}>Why it works</h2>
        <p className={styles.sub}>
          Six properties together — none new on its own, but the combination
          is what makes per-token settlement economically viable.
        </p>
      </div>

      <div className={styles.grid}>
        {FEATURES.map((f) => (
          <article key={f.title} className={styles.card}>
            <div className={styles.iconBox}>{f.icon}</div>
            <h3 className={styles.cardTitle}>{f.title}</h3>
            <p className={styles.cardBody}>{f.body}</p>
            <Link to={f.to} className={styles.cardLink}>
              {f.toLabel} →
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}

/* Inline SVG icons keep this component dependency-free. Each uses
   `currentColor` so the per-card gradient styling drives the stroke. */

function Bilateral() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 8h12M16 8l-3-3M16 8l-3 3" />
      <path d="M20 16H8M8 16l3-3M8 16l3 3" />
    </svg>
  );
}

function PrepaidInput() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="6" width="18" height="14" rx="2" />
      <path d="M3 10h18" />
      <circle cx="8" cy="15" r="1.4" fill="currentColor" />
      <path d="M12 15h5" />
    </svg>
  );
}

function X402() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 7c0-1.1.9-2 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" />
      <path d="M3 10h18" />
      <path d="M7 14l2 2 4-4" />
    </svg>
  );
}

function Solana() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 6h12l3 3H8z" />
      <path d="M5 12h12l3 3H8z" />
      <path d="M5 18h12l3-3H8z" />
    </svg>
  );
}

function Eval() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h16v6H4z" />
      <path d="M4 14h10v6H4z" />
      <path d="M18 14h2v6h-2z" />
      <path d="M16 14h.01" />
    </svg>
  );
}

function Substrate() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 17l9-5 9 5" />
      <path d="M3 12l9-5 9 5" />
      <path d="M3 7l9-5 9 5" />
    </svg>
  );
}
