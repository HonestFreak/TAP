"""Wire-level protocol primitives. Pure data + codecs; no I/O lives in this
package, which keeps the rest of the SDK testable without a network."""

from tap.protocol.commit import CommitMessage, SignedCommitment
from tap.protocol.codec import decode_commitment, encode_commitment
from tap.protocol.signing import sign_commitment, verify_commitment

__all__ = [
    "CommitMessage",
    "SignedCommitment",
    "decode_commitment",
    "encode_commitment",
    "sign_commitment",
    "verify_commitment",
]
