"""Probe Generator Agent: Generates, mutates, and refines test prompts across multi-turn trajectories."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from benchmark_engine.strategies.mutator import StrategyMutator, MutationPlan
from benchmark_engine.strategies.contextual_prober import ContextualProber, CrescendoPlan


class GeneratedProbe(BaseModel):
    scenario_id: str
    turn_number: int
    prompt_text: str
    strategy_used: str
    metadata: Dict[str, str] = Field(default_factory=dict)


class ProbeGeneratorAgent:
    """Agent responsible for iteratively synthesizing and mutating adversarial probes."""

    def __init__(self):
        self.mutator = StrategyMutator()
        self.contextual_prober = ContextualProber()
        self.active_crescendo_plans: Dict[str, CrescendoPlan] = {}

    def generate_initial_probe(
        self,
        scenario_id: str,
        base_intent: str,
        strategy: str = "random",
        canary_token: Optional[str] = None,
        planned_turns: int = 1,
    ) -> GeneratedProbe:
        """Create the first probe for a scenario."""
        if strategy in ["crescendo", "contextual_prober"]:
            plan = self.contextual_prober.create_plan(base_intent, planned_turns=planned_turns)
            self.active_crescendo_plans[scenario_id] = plan
            prompt = self.contextual_prober.generate_next_probe(plan)
            return GeneratedProbe(
                scenario_id=scenario_id,
                turn_number=1,
                prompt_text=prompt,
                strategy_used="crescendo_multi_turn",
                metadata={"stage": plan.state},
            )
        else:
            mutation = self.mutator.mutate(base_intent, strategy=strategy, canary_token=canary_token)
            return GeneratedProbe(
                scenario_id=scenario_id,
                turn_number=1,
                prompt_text=mutation.mutated_prompt,
                strategy_used=mutation.strategy_name,
                metadata=mutation.technique_metadata,
            )

    def generate_next_turn_probe(
        self,
        scenario_id: str,
        base_intent: str,
        last_response: str,
        last_verdict: str,
        last_severity: float,
        turn_number: int,
    ) -> GeneratedProbe:
        """Synthesize next mutated turn based on previous feedback from target and judge."""
        if scenario_id in self.active_crescendo_plans:
            plan = self.active_crescendo_plans[scenario_id]
            # Record last feedback
            if plan.turns_history:
                # Update last turn result
                pass
            prompt = self.contextual_prober.generate_next_probe(plan)
            return GeneratedProbe(
                scenario_id=scenario_id,
                turn_number=turn_number,
                prompt_text=prompt,
                strategy_used="crescendo_multi_turn",
                metadata={"stage": plan.state},
            )
        else:
            # Dynamic fallback mutation: if last probe was refused, try obfuscation or roleplay
            if last_verdict == "COMPLIANT":
                next_strat = "base64" if turn_number % 2 == 0 else "roleplay"
            else:
                next_strat = "delimiters"

            mutation = self.mutator.mutate(base_intent, strategy=next_strat)
            return GeneratedProbe(
                scenario_id=scenario_id,
                turn_number=turn_number,
                prompt_text=mutation.mutated_prompt,
                strategy_used=mutation.strategy_name,
                metadata=mutation.technique_metadata,
            )

    def record_turn_result(
        self,
        scenario_id: str,
        prompt: str,
        target_response: str,
        judge_verdict: str,
        severity_score: float,
    ) -> None:
        """Record turn outcome into active crescendo plan if present."""
        if scenario_id in self.active_crescendo_plans:
            plan = self.active_crescendo_plans[scenario_id]
            self.contextual_prober.record_turn(
                plan=plan,
                user_prompt=prompt,
                target_response=target_response,
                judge_verdict=judge_verdict,
                severity_score=severity_score,
            )
