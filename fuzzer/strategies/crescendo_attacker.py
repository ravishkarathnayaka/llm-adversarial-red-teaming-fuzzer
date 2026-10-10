"""Fuzzer crescendo attacker bridge."""

from benchmark_engine.strategies.contextual_prober import (
    ContextualProber as CrescendoAttacker,
    CrescendoPlan,
    TurnContext,
)

__all__ = ["CrescendoAttacker", "CrescendoPlan", "TurnContext"]
