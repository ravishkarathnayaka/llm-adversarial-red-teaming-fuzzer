"""Fuzzer strategies package bridge."""

from fuzzer.strategies.mutator import StrategyMutator, MutationPlan
from fuzzer.strategies.encoding_obfuscator import EncodingObfuscator
from fuzzer.strategies.roleplay_hijacker import RoleplayHijacker
from fuzzer.strategies.crescendo_attacker import CrescendoAttacker
from fuzzer.strategies.extraction_prober import ExtractionProber

__all__ = [
    "StrategyMutator",
    "MutationPlan",
    "EncodingObfuscator",
    "RoleplayHijacker",
    "CrescendoAttacker",
    "ExtractionProber",
]
