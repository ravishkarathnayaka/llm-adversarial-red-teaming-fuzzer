"""Strategy coordinator and mutator for adversarial probe generation."""

import random
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from benchmark_engine.strategies.perturbation_engine import PerturbationEngine, PerturbationResult
from benchmark_engine.strategies.contextual_prober import ContextualProber, CrescendoPlan
from benchmark_engine.strategies.boundary_tester import BoundaryTester, BoundaryProbeResult
from benchmark_engine.strategies.roleplay_hijacker import RoleplayHijacker, RoleplayProbeResult


class MutationPlan(BaseModel):
    strategy_name: str
    original_intent: str
    mutated_prompt: str
    technique_metadata: Dict[str, str] = Field(default_factory=dict)


class StrategyMutator:
    """Coordinates and executes multi-tactic mutations against target LLM boundaries."""

    def __init__(self):
        self.perturbation_engine = PerturbationEngine()
        self.contextual_prober = ContextualProber()
        self.boundary_tester = BoundaryTester()
        self.roleplay_hijacker = RoleplayHijacker()

    def mutate(
        self,
        base_intent: str,
        strategy: str = "random",
        canary_token: Optional[str] = None,
    ) -> MutationPlan:
        """Apply a specified or randomized mutation strategy to base intent."""
        strat = strategy.lower().strip()

        if strat == "base64":
            res = self.perturbation_engine.to_base64(base_intent)
            return MutationPlan(
                strategy_name="base64_obfuscation",
                original_intent=base_intent,
                mutated_prompt=res.transformed_text,
                technique_metadata=res.parameters,
            )

        elif strat == "rot13":
            res = self.perturbation_engine.to_rot13(base_intent)
            return MutationPlan(
                strategy_name="rot13_cipher",
                original_intent=base_intent,
                mutated_prompt=res.transformed_text,
                technique_metadata=res.parameters,
            )

        elif strat == "leetspeak":
            res = self.perturbation_engine.to_leetspeak(base_intent)
            return MutationPlan(
                strategy_name="leetspeak_obfuscation",
                original_intent=base_intent,
                mutated_prompt=res.transformed_text,
                technique_metadata=res.parameters,
            )

        elif strat in ["delimiters", "perturbation_engine", "encoding_obfuscator"]:
            res = self.perturbation_engine.wrap_delimiters(base_intent)
            return MutationPlan(
                strategy_name="delimiter_injection",
                original_intent=base_intent,
                mutated_prompt=res.transformed_text,
            )

        elif strat in ["roleplay", "roleplay_hijacker"]:
            res = self.roleplay_hijacker.generate_roleplay_prompt(base_intent)
            return MutationPlan(
                strategy_name="roleplay_hijacking",
                original_intent=base_intent,
                mutated_prompt=res.prompt,
                technique_metadata={"persona": res.persona_name, "framing": res.framing},
            )

        elif strat in ["boundary", "boundary_tester", "canary", "extraction_prober"]:
            res = self.boundary_tester.probe("canary_exfiltration", canary_token=canary_token)
            return MutationPlan(
                strategy_name="boundary_canary_extraction",
                original_intent=base_intent,
                mutated_prompt=f"{res.prompt}\nRef Intent: {base_intent}",
                technique_metadata=res.metadata,
            )

        elif strat == "affirmative":
            res = self.perturbation_engine.apply_affirmative_prefix(base_intent)
            return MutationPlan(
                strategy_name="affirmative_prefix",
                original_intent=base_intent,
                mutated_prompt=res.transformed_text,
            )

        else:
            # Pick randomly from available strategies
            choices = ["base64", "rot13", "leetspeak", "delimiters", "roleplay", "boundary", "affirmative"]
            chosen = random.choice(choices)
            return self.mutate(base_intent, strategy=chosen, canary_token=canary_token)
