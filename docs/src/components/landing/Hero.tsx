import React from 'react';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import FlowHeroVisual from './FlowHeroVisual';
import styles from './Hero.module.css';

export default function Hero(): JSX.Element {
  return (
    <header className={styles.hero}>
      <div className={styles.gridBg} aria-hidden="true" />
      <div className={styles.glowA} aria-hidden="true" />
      <div className={styles.glowB} aria-hidden="true" />

      <div className={styles.content}>
        <span className={styles.eyebrow}>Token Access Protocol</span>

        <FlowHeroVisual />

        <h1 className={styles.title}>
          Pay for AI <em>token-by-token</em>.
          <br />
          Shut the tap the moment it goes wrong.
        </h1>

        <p className={styles.tagline}>
          A Solana state-channel payment protocol for streaming LLM inference.
          Either side can halt at any output-token boundary; settlement only
          ever moves USDC for output the consumer actually accepted. Built on{' '}
          <a href="https://x402.org" target="_blank" rel="noreferrer">x402</a>.
        </p>

        <div className={styles.ctaRow}>
          <Link className={styles.primary} to="/intro">
            Read the docs
          </Link>
          <a
            className={styles.secondary}
            href={useBaseUrl('/TAP_Whitepaper.pdf')}
            target="_blank"
            rel="noreferrer"
          >
            View whitepaper
          </a>
          <a
            className={styles.ghost}
            href="https://github.com/HonestFreak/TAP"
            target="_blank"
            rel="noreferrer"
          >
            GitHub →
          </a>
        </div>

        <div className={styles.statsRow}>
          <Stat value="< 1¢" label="Bounded loss per side mid-stream" />
          <Stat value="~200 ms" label="Default halt grace period" />
          <Stat value="~92%" label="Refunded per halted response" />
          <Stat value="x402" label="HTTP payment standard, extended" />
        </div>
      </div>
    </header>
  );
}

function Stat({value, label}: {value: string; label: string}) {
  return (
    <div className={styles.stat}>
      <div className={styles.statValue}>{value}</div>
      <div className={styles.statLabel}>{label}</div>
    </div>
  );
}
