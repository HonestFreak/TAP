"""Builder for the Solana Ed25519Program verify instruction.

Solana has no in-program syscall to verify Ed25519 signatures; the standard
pattern (used by Squads, Privy, and the TAP `settle`/`dispute` handlers) is
to include an Ed25519Program instruction earlier in the same transaction
and let the verifying program inspect it via the instructions sysvar.

The byte layout below is the program's documented single-signature form;
see solana-program / sdk docs for the offset table."""

from __future__ import annotations

from solders.instruction import Instruction
from solders.pubkey import Pubkey

ED25519_PROGRAM_ID = Pubkey.from_string("Ed25519SigVerify111111111111111111111111111")

_HEADER_LEN = 16  # 1 num_sigs + 1 padding + 7×u16 offsets/sizes


def ed25519_verify_ix(public_key: bytes, signature: bytes, message: bytes) -> Instruction:
    """Build a single-signature Ed25519 verify instruction.

    The data layout is:
        [num_sigs:u8=1][padding:u8=0][sig_off:u16][sig_ix:u16=0xFFFF]
        [pk_off:u16][pk_ix:u16=0xFFFF][msg_off:u16][msg_size:u16][msg_ix:u16=0xFFFF]
        [pk_bytes][sig_bytes][msg_bytes]
    """
    if len(public_key) != 32:
        raise ValueError("ed25519 public key must be 32 bytes")
    if len(signature) != 64:
        raise ValueError("ed25519 signature must be 64 bytes")

    pk_off = _HEADER_LEN
    sig_off = pk_off + 32
    msg_off = sig_off + 64
    msg_len = len(message)

    data = bytearray()
    data += (1).to_bytes(1, "little")    # num signatures
    data += (0).to_bytes(1, "little")    # padding
    data += sig_off.to_bytes(2, "little")
    data += (0xFFFF).to_bytes(2, "little")  # signature instruction index (none)
    data += pk_off.to_bytes(2, "little")
    data += (0xFFFF).to_bytes(2, "little")  # pk ix index (none)
    data += msg_off.to_bytes(2, "little")
    data += msg_len.to_bytes(2, "little")
    data += (0xFFFF).to_bytes(2, "little")  # msg ix index (none)
    data += public_key
    data += signature
    data += message

    return Instruction(ED25519_PROGRAM_ID, bytes(data), [])
