import React from 'react';
import styles from './Comparison.module.css';

const ROWS: {label: string; current: string; tap: string}[] = [
  {label: 'Halt mid-response', current: 'No — full response is billed', tap: 'Either side, any token boundary'},
  {label: 'Refund unused tokens', current: 'Not possible after delivery', tap: 'On-chain, automatic at settlement'},
  {label: 'Producer trusts consumer for', current: 'Pre-funded account / KYC', tap: '< 1¢ of unsigned tokens'},
  {label: 'Consumer trusts producer for', current: 'Full request value, every request', tap: '< 1¢ trailing buffer'},
  {label: 'Per-token settlement cost', current: 'Bundled at end (no per-token rail)', tap: 'Off-chain. One Solana tx per session'},
  {label: 'Input-cost protection', current: 'None — bundled with output', tap: 'prepaid_input locked at channel open'},
];

export default function Comparison(): JSX.Element {
  return (
    <section className={styles.wrap}>
      <div className={styles.head}>
        <h2 className={styles.h2}>The structural shift</h2>
        <p className={styles.sub}>
          Today's pay-after-delivery model bundles commitment and value in two
          coarse points; TAP makes them flow together, token by token. The
          trust window collapses from "full request value" to "a few tokens of
          inference cost".
        </p>
      </div>

      <div className={styles.tableWrap}>
        <div className={styles.tableHead}>
          <div className={styles.col}> </div>
          <div className={styles.col}>
            <span className={styles.colTagBad}>Today</span>
            Pay-after-delivery API
          </div>
          <div className={styles.col}>
            <span className={styles.colTagGood}>TAP</span>
            Streaming state-channel
          </div>
        </div>
        {ROWS.map((row) => (
          <div className={styles.row} key={row.label}>
            <div className={styles.label}>{row.label}</div>
            <div className={styles.current}>{row.current}</div>
            <div className={styles.tap}>{row.tap}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
