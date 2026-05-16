"""Regenerate cross-language wire-format fixtures.

Captures byte and base64 outputs from the Python SDK so the TypeScript
parity test (`tests/python-fixtures.test.ts`) can assert against them.
Run after any change to a Python codec; paste the new constants into the
TypeScript test by hand.

    python3 sdk/typescript/scripts/dump_fixtures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Resolve relative to this script so it works from any cwd.
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "sdk" / "python"))

from solders.pubkey import Pubkey  # noqa: E402

from tap.protocol.codec import encode_commitment, encode_commitment_bytes  # noqa: E402
from tap.protocol.commit import CommitMessage, SignedCommitment  # noqa: E402
from tap.x402.payment import OpenChannelPayment, encode_payment  # noqa: E402
from tap.x402.requirements import SCHEME, PaymentRequirements, encode_requirements  # noqa: E402
from tap.x402.response import PaymentResponse, encode_response  # noqa: E402

channel = Pubkey.from_string("TapPRoTuQDmXiBg2H4Z7Lp4uKnxw3w6f8Y4F2X1aBcD")
commit_msg = CommitMessage(
    channel=channel,
    sequence=42,
    cumulative_paid=1_234_567,
    tokens_received=12_345,
    timestamp_ms=1_700_000_000_000,
)
print("COMMIT_BYTES_HEX:", encode_commitment_bytes(commit_msg).hex())
print("COMMIT_HEADER:   ", encode_commitment(SignedCommitment(commit_msg, bytes(64))))

req = PaymentRequirements(
    scheme=SCHEME,
    network="solana-devnet",
    asset="4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
    recipient="TapPRoTuQDmXiBg2H4Z7Lp4uKnxw3w6f8Y4F2X1aBcD",
    producer_pubkey="prod1111111111111111111111111111111111111111",
    input_price_micro=1,
    output_price_micro=5,
    max_unpaid_micro=1_000,
    trailing_buffer_tokens=10,
    duration_secs=600,
    dispute_secs=30,
    grace_ms=200,
    pause_timeout_ms=5_000,
    channel_open_url="https://x/open",
    stream_url="https://x/stream",
    tokenizer_id="tap.tok.v1",
    input_token_count=42,
    prepaid_input_micro=42,
    model="claude-sonnet-4-6",
)
print("REQ_HEADER:      ", encode_requirements(req))

pay = OpenChannelPayment(
    scheme=SCHEME,
    network="solana-devnet",
    consumer_pubkey="cons111111111111111111111111111111111111111",
    session_key="sess111111111111111111111111111111111111111",
    nonce=42,
    deposit_micro=50_000,
    input_price_micro=1,
    output_price_micro=5,
    prepaid_input_micro=200,
    duration_secs=600,
    dispute_secs=30,
    trailing_buffer_tokens=10,
    transaction_b64="AA==",
)
print("PAY_HEADER:      ", encode_payment(pay))

resp = PaymentResponse(
    tx_hash="sig",
    settlement="confirmed",
    channel_id="chan",
    channel_state="active",
)
print("RESP_HEADER:     ", encode_response(resp))
