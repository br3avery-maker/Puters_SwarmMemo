"""Offline receipt state machine: acceptance is not verification.

No network, signer, secrets, or automatic publishing. Public synthetic fixtures only.
"""
from dataclasses import dataclass
from hashlib import sha256
from typing import Literal

State = Literal["attempted", "accepted", "verified", "failed"]


@dataclass(frozen=True)
class Receipt:
    payload_sha256: str
    state: State
    reason: str = ""


def digest(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def transition(receipt: Receipt, *, accepted: bool = False,
               readback: bytes | None = None, error: str = "") -> Receipt:
    """Move forward only on matching readback; failures remain explicit."""
    if receipt.state in ("verified", "failed"):
        raise ValueError("terminal receipt cannot transition")
    if error:
        return Receipt(receipt.payload_sha256, "failed", error)
    if readback is not None:
        if receipt.state != "accepted":
            raise ValueError("readback requires prior acceptance")
        if digest(readback) != receipt.payload_sha256:
            return Receipt(receipt.payload_sha256, "failed", "readback mismatch")
        return Receipt(receipt.payload_sha256, "verified")
    if accepted and receipt.state == "attempted":
        return Receipt(receipt.payload_sha256, "accepted")
    raise ValueError("no valid state transition")


def start(payload: bytes) -> Receipt:
    return Receipt(digest(payload), "attempted")
