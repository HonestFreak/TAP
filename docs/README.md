# TAP Documentation Site

This is the public-facing documentation and landing page for the
**TAP — Token Access Protocol**, built with
[Docusaurus](https://docusaurus.io/).

The site hosts:

- the marketing landing page (Hero + interactive meter demo + comparison),
- the protocol documentation (concepts, on-chain interface, wire format),
- the SDK reference (producer / consumer / evaluators / x402 codecs),
- the demo walkthrough,
- the canonical whitepaper PDF, served as `/TAP_Whitepaper.pdf`.

## Layout

```
docs/
├── docs/                    # markdown content (sidebar source)
│   ├── intro.md
│   ├── architecture.md
│   ├── concepts/            # protocol concepts
│   ├── protocol/            # on-chain + wire format + trust model
│   ├── sdk/                 # SDK reference
│   ├── demo/                # how to run the demo
│   ├── beyond-llm/          # generalisation to audio / video / GPU / APIs
│   └── whitepaper.md
├── src/
│   ├── pages/index.tsx      # landing page composition
│   ├── components/landing/  # Hero, MeterDemo, Comparison, Features, CtaFooter
│   └── css/custom.css
├── static/                  # served verbatim (incl. whitepaper PDF)
├── docusaurus.config.ts
└── sidebars.ts
```

## Local development

```bash
npm install
npm run start          # http://localhost:3000
```

## Build for static hosting

```bash
npm run build          # → docs/build/
npm run serve          # preview locally
```

The output of `npm run build` is plain static HTML/JS/CSS — host it on
any static-content host (GitHub Pages, Cloudflare Pages, S3, Vercel).
