import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  mainSidebar: [
    'intro',
    'architecture',
    {
      type: 'category',
      label: 'Concepts',
      collapsed: false,
      items: [
        'concepts/why-tap',
        'concepts/session-lifecycle',
        'concepts/input-prepay',
        'concepts/halt-and-bounded-loss',
        'concepts/x402-relationship',
        'concepts/economics',
      ],
    },
    {
      type: 'category',
      label: 'Protocol',
      items: [
        'protocol/on-chain',
        'protocol/wire-format',
        'protocol/trust-model',
      ],
    },
    {
      type: 'category',
      label: 'SDK',
      items: [
        'sdk/install',
        'sdk/producer',
        'sdk/consumer',
        'sdk/evaluators',
        'sdk/x402',
        'sdk/tokenizer',
      ],
    },
    {
      type: 'category',
      label: 'Demo',
      items: [
        'demo/run',
        'demo/architecture',
      ],
    },
    {
      type: 'category',
      label: 'Beyond LLM',
      items: [
        'beyond-llm/overview',
        'beyond-llm/video',
        'beyond-llm/audio',
        'beyond-llm/gpu',
        'beyond-llm/apis',
      ],
    },
    'whitepaper',
  ],
};

export default sidebars;
