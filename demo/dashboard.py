"""Terminal dashboard for the TAP demo.

Renders the streaming response alongside a live cost meter. Built with
`rich` so the demo doesn't require a browser; visually identical
information to the on-stage panel described in whitepaper §6.4."""

from __future__ import annotations

import asyncio
import os

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from tap import TapConsumer, evaluators
from tap.chain.keypair_io import load_keypair
from tap.chain.rpc import ChainClient

PRODUCER_URL = os.environ.get("TAP_PRODUCER_URL", "http://localhost:8000/v1/messages")
RPC_URL = os.environ.get("TAP_RPC", "https://api.devnet.solana.com")
EXPECTED_SCHEMA = {"type": "object", "required": ["title"], "properties": {"title": {"type": "string"}}}

console = Console()


def _render(text: str, paid_micro: int, tokens: int, halted: str | None) -> Group:
    body = Panel(Text(text or "…", style="white"), title="Output", border_style="cyan")
    meter = Table.grid(padding=(0, 1))
    meter.add_row("Tokens", f"[bold]{tokens}[/bold]")
    meter.add_row("Paid (USDC)", f"[bold]{paid_micro / 1_000_000:.6f}[/bold]")
    meter.add_row("Halted by", halted or "[dim]—[/dim]")
    side = Panel(meter, title="TAP Meter", border_style="magenta", width=32)
    return Group(body, side)


async def main() -> None:
    wallet = load_keypair(os.environ["TAP_CONSUMER_KEYPAIR"])

    async with ChainClient(RPC_URL) as chain, TapConsumer(wallet=wallet, chain=chain) as consumer:
        session = await consumer.open_session(
            producer_url=PRODUCER_URL,
            deposit_micro=50_000,
            evaluator=evaluators.compose(
                evaluators.json_schema(EXPECTED_SCHEMA),
                evaluators.length_cap(2_000),
            ),
        )

        accumulated = ""
        with Live(console=console, refresh_per_second=20) as live:
            async for chunk in session.stream(
                {
                    "messages": [
                        {"role": "user", "content": "Return a JSON object with key `title`."}
                    ]
                }
            ):
                accumulated += chunk.text
                live.update(
                    _render(
                        accumulated,
                        chunk.cumulative_paid_micro,
                        chunk.tokens_received,
                        session.halted_by,
                    )
                )

        console.rule("Settled")
        console.print(
            f"Paid [bold]{session.cumulative_paid_micro / 1_000_000:.6f}[/bold] USDC "
            f"for [bold]{session.tokens_received}[/bold] tokens. "
            f"Halt reason: [bold]{session.halted_by or 'completion'}[/bold]"
        )


if __name__ == "__main__":
    asyncio.run(main())
