"""Reference TAP consumer.

Issues one streaming request against the demo producer with a JSON-schema
evaluator. Halts (and refunds) if the model breaks the schema mid-stream.

Discovery follows whitepaper §4.9: the consumer POSTs the prompt without
payment, receives a prompt-bound 402 quote, locally re-tokenizes the prompt
to verify the producer's `input_token_count`, and only then opens the channel."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from solders.keypair import Keypair

from tap import TapConsumer, evaluators
from tap.chain.rpc import ChainClient

PRODUCER_URL = os.environ.get("TAP_PRODUCER_URL", "http://localhost:8000/v1/messages")
RPC_URL = os.environ.get("TAP_RPC", "https://api.devnet.solana.com")

EXPECTED_SCHEMA = {
    "type": "object",
    "required": ["title", "summary", "tags"],
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
}

PROMPT_BODY = {
    "messages": [
        {
            "role": "user",
            "content": (
                "Return a JSON object with keys `title`, `summary`, `tags`. "
                "Strictly JSON only, no prose."
            ),
        }
    ],
}


def _load_wallet(path: str) -> Keypair:
    raw = json.loads(Path(path).expanduser().read_text())
    return Keypair.from_bytes(bytes(raw))


async def main() -> None:
    wallet = _load_wallet(os.environ["TAP_CONSUMER_KEYPAIR"])

    async with ChainClient(RPC_URL) as chain, TapConsumer(wallet=wallet, chain=chain) as consumer:
        session = await consumer.open_session(
            producer_url=PRODUCER_URL,
            deposit_micro=50_000,  # 0.05 USDC
            prompt_body=PROMPT_BODY,
            evaluator=evaluators.compose(
                evaluators.json_schema(EXPECTED_SCHEMA),
                evaluators.length_cap(2_000),
                evaluators.repetition_guard(),
            ),
        )

        printed = 0
        async for chunk in session.stream(PROMPT_BODY):
            print(chunk.text, end="", flush=True)
            printed += len(chunk.text)

        print()
        print(
            f"Settled: paid {session.cumulative_paid_micro} micro-USDC "
            f"({session.tokens_received} output tokens, prepaid input "
            f"{session.prepaid_input_micro} micro-USDC). "
            f"Halted by: {session.halted_by or 'completion'}."
        )


if __name__ == "__main__":
    asyncio.run(main())
