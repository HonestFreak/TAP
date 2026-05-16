# `tap-protocol`

Python SDK for the TAP (Token Access Protocol) — token-by-token payments for
LLM inference on Solana.

## Install

```bash
pip install tap-protocol            # core
pip install 'tap-protocol[anthropic]' # + Anthropic adapter
pip install 'tap-protocol[openai]'    # + OpenAI adapter
pip install 'tap-protocol[ollama]'    # + Ollama adapter
```

## Consumer

```python
from tap import TapConsumer, evaluators
from tap.chain.rpc import ChainClient
from solders.keypair import Keypair

wallet = Keypair.from_bytes(...)
async with ChainClient("https://api.devnet.solana.com") as chain, \
           TapConsumer(wallet=wallet, chain=chain) as consumer:
    session = await consumer.open_session(
        producer_url="https://provider.example/v1/messages",
        deposit_micro=50_000,                  # 0.05 USDC max
        evaluator=evaluators.compose(
            evaluators.json_schema(my_schema),
            evaluators.length_cap(2_000),
        ),
    )
    async for chunk in session.stream({"messages": [...]}):
        print(chunk.text, end="")
    print(f"\nPaid {session.cumulative_paid_micro} micro-USDC")
```

## Producer

```python
from solders.pubkey import Pubkey

from tap import TapProducer
from tap.adapters.anthropic import stream_anthropic
from tap.chain.keypair_io import load_keypair
from tap.chain.rpc import ChainClient
from tap.producer.pricing import Pricing

producer = TapProducer(
    keypair=load_keypair("~/.config/solana/producer.json"),
    producer_usdc=Pubkey.from_string("<producer USDC ATA>"),
    chain=ChainClient("https://api.devnet.solana.com"),
    pricing=Pricing(
        input_price_micro=1,              # 0.000001 USDC per prompt token
        output_price_micro=5,              # 0.000005 USDC per output token
        max_unpaid_micro=5_000,
        trailing_buffer_tokens=10,
        tokenizer_id="tap.tok.v1",        # must be registered before construction
    ),
)

@producer.handler("/v1/messages")
async def handle(body):
    return stream_anthropic(body)

# producer.app is a FastAPI app. Mount with uvicorn / hypercorn / etc.
```

## Layout

| Module | Purpose |
|---|---|
| `tap.protocol` | Commitment dataclass + signing |
| `tap.chain` | PDA derivation, instruction builders, RPC |
| `tap.x402` | x402 wire codecs |
| `tap.consumer` | TapConsumer + ConsumerSession |
| `tap.producer` | TapProducer + verifier + settlement |
| `tap.adapters` | Anthropic / OpenAI / Ollama wrappers |
| `tap.evaluators` | JSON schema, length, topic, content, repetition |
| `tap.timing` | Grace / pause / total-session timeouts |

See [`docs/docs/architecture.md`](../../docs/docs/architecture.md) for the full file-to-responsibility map.
