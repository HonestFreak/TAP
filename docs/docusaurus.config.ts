import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'TAP — Token Access Protocol',
  tagline: 'Token-by-token payments for LLM inference, on Solana state channels.',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  // Enable native Mermaid rendering for ```mermaid code blocks.
  markdown: {
    mermaid: true,
  },
  themes: [
    '@docusaurus/theme-mermaid',
    [
      // Fully-local Lunr search; no third-party service needed.
      // Build hashes the index into the bundle, so production search works
      // out of the box on any static host.
      require.resolve('@easyops-cn/docusaurus-search-local'),
      {
        hashed: true,
        indexBlog: false,
        docsRouteBasePath: '/',
        highlightSearchTermsOnTargetPage: true,
        explicitSearchResultPath: true,
      },
    ],
  ],

  url: 'https://tap.example.com',
  baseUrl: '/',

  organizationName: 'tap',
  projectName: 'tap',

  onBrokenLinks: 'throw',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          routeBasePath: '/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      logo: {
        alt: 'TAP — Token Access Protocol',
        src: 'img/logo.png',
        height: 28,
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'mainSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          to: '/beyond-llm/overview',
          label: 'Beyond LLM',
          position: 'left',
        },
        {
          href: '/TAP_Whitepaper.pdf',
          label: 'Whitepaper',
          position: 'left',
          target: '_blank',
          rel: null,
        },
        {
          href: 'https://demo.tapprotocol.space',
          label: 'Demo',
          position: 'left',
          target: '_blank',
          rel: null,
        },
        {
          href: 'https://github.com/HonestFreak/TAP',
          position: 'right',
          className: 'navbar-github-link',
          'aria-label': 'GitHub repository',
        },
      ],
    },
    footer: {
      style: 'dark',
      logo: {
        alt: 'TAP',
        src: 'img/logo.png',
        height: 40,
      },
      links: [
        {
          title: 'Protocol',
          items: [
            {label: 'Overview', to: '/intro'},
            {label: 'Whitepaper', href: '/TAP_Whitepaper.pdf', target: '_blank', rel: null},
            {label: 'On-chain interface', to: '/protocol/on-chain'},
          ],
        },
        {
          title: 'SDK',
          items: [
            {label: 'Producer', to: '/sdk/producer'},
            {label: 'Consumer', to: '/sdk/consumer'},
            {label: 'x402 wire format', to: '/sdk/x402'},
          ],
        },
        {
          title: 'Demo',
          items: [
            {label: 'Run locally', to: '/demo/run'},
            {label: 'Architecture', to: '/demo/architecture'},
          ],
        },
      ],
      copyright: `TAP — Token Access Protocol · Solana Frontier ${new Date().getFullYear()} · MIT licensed.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['rust', 'python', 'bash', 'json', 'typescript', 'toml'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
