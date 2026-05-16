import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  mainSidebar: [
    {type: 'doc', id: 'intro', className: 'sidebar-icon sidebar-icon-intro'},
    {type: 'doc', id: 'architecture', className: 'sidebar-icon sidebar-icon-architecture'},
    {
      type: 'category',
      label: 'Concepts',
      collapsed: false,
      className: 'sidebar-icon sidebar-icon-concepts',
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
      className: 'sidebar-icon sidebar-icon-protocol',
      items: [
        'protocol/on-chain',
        'protocol/wire-format',
        'protocol/trust-model',
      ],
    },
    {
      type: 'category',
      label: 'SDK',
      className: 'sidebar-icon sidebar-icon-sdk',
      items: [
        'sdk/install',
        'sdk/producer',
        'sdk/consumer',
        'sdk/typescript',
        'sdk/evaluators',
        'sdk/x402',
        'sdk/tokenizer',
      ],
    },
    {
      type: 'category',
      label: 'Demo',
      className: 'sidebar-icon sidebar-icon-demo',
      items: [
        'demo/run',
        'demo/architecture',
      ],
    },
    {
      type: 'category',
      label: 'Beyond LLM',
      className: 'sidebar-icon sidebar-icon-beyond',
      items: [
        'beyond-llm/overview',
        'beyond-llm/video',
        'beyond-llm/audio',
        'beyond-llm/gpu',
        'beyond-llm/apis',
      ],
    },
    {type: 'doc', id: 'whitepaper', className: 'sidebar-icon sidebar-icon-whitepaper'},
  ],
};

export default sidebars;
