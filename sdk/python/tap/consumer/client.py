"""`TapConsumer` — entry point. Discovers producers, opens channels, returns
`ConsumerSession`s.

The open flow follows whitepaper §4.9:
  1. POST the prompt body to the producer (no payment).
  2. Receive a prompt-bound 402 with `input_token_count` / `prepaid_input`.
  3. Locally re-tokenize the prompt; abort on mismatch (§5.3.7).
  4. Build the channel-open transaction with `prepaid_input_micro` locked
     on-chain as the settlement floor.
  5. Submit via X-PAYMENT and proceed to streaming.
"""

from __future__ import annotations

import base64
from typing import Any

import httpx
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

from tap.chain.pda import derive_ata
from tap.chain.program_id import USDC_MINT_DEVNET
from tap.chain.rpc import ChainClient
from tap.consumer.discovery import discover_with_prompt
from tap.consumer.opener import build_open_channel_tx
from tap.consumer.policy import ConsumerPolicy
from tap.consumer.session import CommitCallback, ConsumerSession
from tap.consumer.session_key import SessionKey
from tap.evaluators.base import Evaluator
from tap.exceptions import X402Error
from tap.protocol.prompt import extract_prompt_text
from tap.timing.parameters import TimingParameters
from tap.x402.headers import HEADER_PAYMENT, HEADER_PAYMENT_RESPONSE
from tap.x402.payment import OpenChannelPayment, encode_payment
from tap.x402.requirements import SCHEME
from tap.x402.response import decode_response


class TapConsumer:
    """Top-level consumer client.

    The consumer wallet (`wallet`) is the one funding the deposit; an
    in-memory `SessionKey` is generated per session and registered on-chain
    in the open transaction."""

    def __init__(
        self,
        *,
        wallet: Keypair,
        chain: ChainClient,
        policy: ConsumerPolicy | None = None,
        usdc_mint: Pubkey | None = None,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._wallet = wallet
        self._chain = chain
        self._policy = policy or ConsumerPolicy()
        self._usdc_mint = usdc_mint or USDC_MINT_DEVNET
        self._http = http or httpx.AsyncClient(timeout=60.0)
        self._owns_http = http is None

    async def close(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> "TapConsumer":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def open_session(
        self,
        *,
        producer_url: str,
        deposit_micro: int,
        prompt_body: dict[str, Any],
        evaluator: Evaluator | None = None,
        k_max: int = 16,
        on_commit: CommitCallback | None = None,
    ) -> ConsumerSession:
        """Discover the producer with the prompt body, audit terms, and open a
        channel. Returns a `ConsumerSession` ready for `.stream(...)` against
        the same prompt body.

        `prompt_body` is the request the consumer intends to send (e.g.
        `{"messages": [...]}`). The producer tokenizes it for the input quote;
        the consumer verifies the count locally before any funds escrow."""
        requirements = await discover_with_prompt(producer_url, prompt_body, http=self._http)
        self._policy.audit(requirements)

        # Whitepaper §5.3.7: re-tokenize the same prompt locally.
        prompt_text = extract_prompt_text(prompt_body)
        self._policy.verify_prompt_tokens(requirements, prompt_text)

        if requirements.prepaid_input_micro > deposit_micro:
            raise X402Error(
                f"deposit {deposit_micro} cannot cover prepaid input cost "
                f"{requirements.prepaid_input_micro}"
            )

        session_key = SessionKey.generate()
        timing = TimingParameters(
            grace_ms=requirements.grace_ms,
            pause_timeout_ms=requirements.pause_timeout_ms,
            total_session_ms=requirements.duration_secs * 1_000,
        )

        consumer_usdc = self._derive_usdc_account()
        blockhash = await self._chain.latest_blockhash()
        plan = build_open_channel_tx(
            consumer=self._wallet.pubkey(),
            producer=Pubkey.from_string(requirements.producer_pubkey),
            consumer_usdc=consumer_usdc,
            usdc_mint=self._usdc_mint,
            session_key=session_key.public_key,
            deposit_micro=deposit_micro,
            input_price_micro=requirements.input_price_micro,
            output_price_micro=requirements.output_price_micro,
            prepaid_input_micro=requirements.prepaid_input_micro,
            duration_secs=requirements.duration_secs,
            dispute_secs=requirements.dispute_secs,
            trailing_buffer=requirements.trailing_buffer_tokens,
            blockhash=blockhash,
        )

        signed_tx = self._sign(plan.transaction)
        payment = OpenChannelPayment(
            scheme=SCHEME,
            network=requirements.network,
            consumer_pubkey=str(self._wallet.pubkey()),
            session_key=str(session_key.public_key),
            nonce=plan.nonce,
            deposit_micro=deposit_micro,
            input_price_micro=requirements.input_price_micro,
            output_price_micro=requirements.output_price_micro,
            prepaid_input_micro=requirements.prepaid_input_micro,
            duration_secs=requirements.duration_secs,
            dispute_secs=requirements.dispute_secs,
            trailing_buffer_tokens=requirements.trailing_buffer_tokens,
            transaction_b64=base64.b64encode(bytes(signed_tx)).decode("ascii"),
        )

        resp = await self._http.post(
            requirements.channel_open_url,
            headers={HEADER_PAYMENT: encode_payment(payment)},
        )
        resp.raise_for_status()
        ack_header = resp.headers.get(HEADER_PAYMENT_RESPONSE)
        if not ack_header:
            raise X402Error(f"{HEADER_PAYMENT_RESPONSE} missing from open ack")
        ack = decode_response(ack_header)

        session = ConsumerSession(
            http=self._http,
            requirements=requirements,
            channel_id=ack.channel_id,
            session_key=session_key,
            timing=timing,
            evaluator=evaluator,
            input_price_micro=requirements.input_price_micro,
            output_price_micro=requirements.output_price_micro,
            prepaid_input_micro=requirements.prepaid_input_micro,
            deposit_micro=deposit_micro,
            unpaid_cap_micro=requirements.max_unpaid_micro,
            k_max=k_max,
            on_commit=on_commit,
        )
        session.open_tx_signature = ack.tx_hash
        return session

    def _derive_usdc_account(self) -> Pubkey:
        return derive_ata(self._wallet.pubkey(), self._usdc_mint)

    def _sign(self, tx: VersionedTransaction) -> VersionedTransaction:
        # `populate` placed a zero-byte signature; `Transaction.sign`-style
        # API for `VersionedTransaction` is to construct anew with signers.
        return VersionedTransaction(tx.message, [self._wallet])


__all__ = ["TapConsumer"]
