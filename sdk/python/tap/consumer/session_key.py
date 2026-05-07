"""Session key generation and lifecycle (whitepaper §4.5).

A session key is generated in-memory at session start, registered in the
channel program at `open_channel`, used to sign every commitment in the
session, and dropped when the session closes. Compromise of a session key
is bounded by the channel deposit; the consumer's primary wallet remains
uncompromised."""

from __future__ import annotations

from dataclasses import dataclass

from nacl.signing import SigningKey
from solders.pubkey import Pubkey


@dataclass(frozen=True, slots=True)
class SessionKey:
    """In-memory Ed25519 session key. Treat instances as one-shot — discard
    them as soon as the session settles."""

    signer: SigningKey

    @classmethod
    def generate(cls) -> "SessionKey":
        return cls(signer=SigningKey.generate())

    @property
    def public_key(self) -> Pubkey:
        return Pubkey.from_bytes(bytes(self.signer.verify_key))
