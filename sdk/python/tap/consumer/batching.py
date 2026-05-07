"""Adaptive batching controller (whitepaper §4.3).

The controller decides "should I send a commitment for the next K tokens?"
where K floats between 1 and `k_max`. The algorithm is the AIMD shape used
in TCP congestion control: multiplicative increase when the producer's
unpaid value is approaching the agreed cap, additive decrease otherwise.

The controller is intentionally pure: it takes signals (`tokens_since_last_commit`,
`unpaid_value`, `unpaid_cap`) and returns a decision. Wiring it to the
session loop is the caller's responsibility."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AdaptiveBatcher:
    k_max: int
    k: int = 1

    _high_water: float = 0.85
    _low_water: float = 0.30

    def __post_init__(self) -> None:
        if self.k_max < 1:
            raise ValueError("k_max must be >= 1")
        if self.k < 1 or self.k > self.k_max:
            self.k = 1

    def should_commit(self, tokens_since_last: int) -> bool:
        return tokens_since_last >= self.k

    def update(self, *, unpaid_value: int, unpaid_cap: int) -> None:
        """Adjust K based on observed pressure.

        High pressure (unpaid_value/cap above `_high_water`) means commitments
        are arriving too slowly — back off K toward 1 so they arrive more
        often. Low pressure means we have headroom; double K to reduce
        signing overhead, capped at `k_max`."""
        if unpaid_cap <= 0:
            return
        ratio = unpaid_value / unpaid_cap
        if ratio >= self._high_water and self.k > 1:
            self.k = max(1, self.k // 2)
        elif ratio <= self._low_water and self.k < self.k_max:
            self.k = min(self.k_max, self.k * 2)
