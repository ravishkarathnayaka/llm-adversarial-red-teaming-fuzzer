"""Fuzzer encoding obfuscator bridge."""

from benchmark_engine.strategies.perturbation_engine import (
    PerturbationEngine as EncodingObfuscator,
    PerturbationResult,
)

__all__ = ["EncodingObfuscator", "PerturbationResult"]
