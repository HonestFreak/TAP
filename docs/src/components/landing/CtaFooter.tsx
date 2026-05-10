import React from 'react';
import Link from '@docusaurus/Link';
import styles from './CtaFooter.module.css';

export default function CtaFooter(): JSX.Element {
  return (
    <section className={styles.wrap}>
      <div className={styles.glow} aria-hidden="true" />
      <div className={styles.inner}>
        <h2 className={styles.h2}>
          Stop paying for tokens you'll throw away.
        </h2>
        <p className={styles.sub}>
          Build a producer or consumer in a few lines. The reference demo
          wraps Gemini 2.5 Flash; adapters are scaffolded for Anthropic,
          OpenAI, and local Ollama. The on-chain program is deployed to
          Solana devnet under{' '}
          <code>FK1ejU1ua497e8TcuabUTm7vxqf6WdKyYXA6ZhxmNWbX</code>.
        </p>
        <div className={styles.actions}>
          <Link to="/sdk/install" className={styles.primary}>Install the SDK</Link>
          <Link to="/demo/run" className={styles.secondary}>Run the demo</Link>
        </div>
      </div>
    </section>
  );
}
