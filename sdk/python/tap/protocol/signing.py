"""Ed25519 signing and verification of `CommitMessage`.

This module is intentionally thin: the only crypto primitive TAP needs at
the protocol layer is Ed25519 over a 60-byte message. Anything beyond that
(key management, session-key lifecycle) lives in the consumer package."""

from __future__ import annotations

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey
from solders.pubkey import Pubkey

from tap.exceptions import CommitmentError
from tap.protocol.codec import encode_commitment_bytes
from tap.protocol.commit import CommitMessage, SignedCommitment


def sign_commitment(message: CommitMessage, signing_key: SigningKey) -> SignedCommitment:
    """Produce a `SignedCommitment` that the on-chain program will accept,
    given the session-key `SigningKey` registered at `open_channel`."""
    sig = signing_key.sign(encode_commitment_bytes(message)).signature
    return SignedCommitment(message=message, signature=sig)


def verify_commitment(signed: SignedCommitment, session_key: Pubkey) -> None:
    """Raise `CommitmentError` if `signed` is not a valid signature by
    `session_key` over `signed.message`."""
    try:
        VerifyKey(bytes(session_key)).verify(
            encode_commitment_bytes(signed.message),
            signed.signature,
        )
    except BadSignatureError as exc:
        raise CommitmentError("commitment signature failed verification") from exc
