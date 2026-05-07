import React from 'react';
import Layout from '@theme/Layout';

import Hero from '@site/src/components/landing/Hero';
import MeterDemo from '@site/src/components/landing/MeterDemo';
import Comparison from '@site/src/components/landing/Comparison';
import Features from '@site/src/components/landing/Features';
import CtaFooter from '@site/src/components/landing/CtaFooter';

export default function Home(): JSX.Element {
  return (
    <Layout
      title="TAP — Token Access Protocol"
      description="Token-by-token payments for LLM inference, with bilateral halt for fair, low-waste generation. Built on Solana state channels and the x402 HTTP payment standard."
    >
      <main>
        <Hero />
        <MeterDemo />
        <Comparison />
        <Features />
        <CtaFooter />
      </main>
    </Layout>
  );
}
