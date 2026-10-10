"""Orchestrator: Coordinates Probe Generator Agent, Target SUT, and Judge Evaluator in multi-turn benchmark loops."""

import json
import os
from typing import Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from benchmark_engine.agents.target_client import TargetClient, TargetResponse
from benchmark_engine.agents.judge_evaluator import JudgeEvaluator, EvaluationResult, JudgeVerdict
from benchmark_engine.agents.probe_generator import ProbeGeneratorAgent, GeneratedProbe
from benchmark_engine.reporting.metrics import (
    TurnTelemetry,
    ScenarioResult,
    BenchmarkMetrics,
    compute_metrics,
)
from benchmark_engine.reporting.report_generator import ReportGenerator


class BenchmarkConfig(BaseModel):
    target_url: Optional[str] = None
    model_name: str = "mock-llm"
    max_scenarios: int = 10
    max_turns_per_scenario: int = 3
    strategy_override: Optional[str] = None
    use_mock: bool = True
    mock_mode: str = "hardened"  # "hardened" or "vulnerable"
    output_dir: str = "./reports"
    early_stop_on_violation: bool = False


class Orchestrator:
    """Main state machine orchestrating the multi-agent safety evaluation framework."""

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.config = config or BenchmarkConfig()
        self.target_client = TargetClient(
            endpoint_url=self.config.target_url,
            model_name=self.config.model_name,
            use_mock=self.config.use_mock,
            mock_mode=self.config.mock_mode,
        )
        self.judge = JudgeEvaluator()
        self.probe_generator = ProbeGeneratorAgent()
        self.report_generator = ReportGenerator(output_dir=self.config.output_dir)

    def load_seed_scenarios(self, path: Optional[str] = None) -> List[Dict]:
        """Load seed scenarios from JSON dataset."""
        if path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_dir, "taxonomy", "seed_scenarios.json")

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run_scenario(
        self,
        scenario: Dict,
        on_turn_callback: Optional[Callable[[int, TurnTelemetry], None]] = None,
    ) -> ScenarioResult:
        """Execute a single scenario across its multi-turn conversational evaluation cycle."""
        scenario_id = scenario.get("id", "SCENARIO-UNKNOWN")
        name = scenario.get("name", "Untitled Scenario")
        category = scenario.get("category", "General")
        mitre_id = scenario.get("mitre_id", "AML.T0054")
        base_intent = scenario.get("base_intent", "")
        system_prompt = scenario.get("system_prompt", None)
        canary_token = scenario.get("canary_token", None)
        strategy = self.config.strategy_override or scenario.get("strategy", "random")

        turns_telemetry: List[TurnTelemetry] = []
        is_compromised = False
        canary_leaked = False
        max_severity = 0.0
        final_verdict = JudgeVerdict.COMPLIANT.value
        chat_history: List[Dict[str, str]] = []

        max_turns = self.config.max_turns_per_scenario

        for turn_num in range(1, max_turns + 1):
            # 1. Generate / Mutate Probe
            if turn_num == 1:
                probe: GeneratedProbe = self.probe_generator.generate_initial_probe(
                    scenario_id=scenario_id,
                    base_intent=base_intent,
                    strategy=strategy,
                    canary_token=canary_token,
                    planned_turns=max_turns,
                )
            else:
                last_turn = turns_telemetry[-1]
                probe = self.probe_generator.generate_next_turn_probe(
                    scenario_id=scenario_id,
                    base_intent=base_intent,
                    last_response=last_turn.response,
                    last_verdict=last_turn.verdict,
                    last_severity=last_turn.severity_score,
                    turn_number=turn_num,
                )

            # 2. Query System Under Test (SUT)
            target_resp: TargetResponse = self.target_client.query(
                prompt=probe.prompt_text,
                system_prompt=system_prompt,
                canary_token=canary_token,
                turn_number=turn_num,
                chat_history=chat_history,
            )

            # Update chat history
            chat_history.append({"role": "user", "content": probe.prompt_text})
            chat_history.append({"role": "assistant", "content": target_resp.text})

            # 3. Impartial Judge Evaluation
            eval_result: EvaluationResult = self.judge.evaluate(
                target_response=target_resp.text,
                base_intent=base_intent,
                canary_token=canary_token,
                system_prompt=system_prompt,
            )

            # Record turn in probe generator memory
            self.probe_generator.record_turn_result(
                scenario_id=scenario_id,
                prompt=probe.prompt_text,
                target_response=target_resp.text,
                judge_verdict=eval_result.verdict.value,
                severity_score=eval_result.severity_score,
            )

            # Telemetry record
            t_data = TurnTelemetry(
                turn_number=turn_num,
                prompt=probe.prompt_text,
                response=target_resp.text,
                strategy_used=probe.strategy_used,
                verdict=eval_result.verdict.value,
                severity_score=eval_result.severity_score,
                canary_leaked=eval_result.canary_leaked,
                latency_ms=target_resp.latency_ms,
            )
            turns_telemetry.append(t_data)

            if on_turn_callback:
                on_turn_callback(turn_num, t_data)

            # Update scenario state
            if eval_result.severity_score > max_severity:
                max_severity = eval_result.severity_score

            if eval_result.canary_leaked:
                canary_leaked = True

            if eval_result.is_jailbroken or eval_result.verdict == JudgeVerdict.VIOLATION:
                is_compromised = True
                final_verdict = JudgeVerdict.VIOLATION.value
            elif eval_result.verdict == JudgeVerdict.PARTIAL_DISCLOSURE and final_verdict != JudgeVerdict.VIOLATION.value:
                final_verdict = JudgeVerdict.PARTIAL_DISCLOSURE.value

            # Early stopping check
            if is_compromised and self.config.early_stop_on_violation:
                break

        return ScenarioResult(
            scenario_id=scenario_id,
            name=name,
            category=category,
            mitre_id=mitre_id,
            base_intent=base_intent,
            canary_token=canary_token,
            total_turns=len(turns_telemetry),
            final_verdict=final_verdict,
            max_severity_score=max_severity,
            is_compromised=is_compromised,
            canary_leaked=canary_leaked,
            turns=turns_telemetry,
        )

    def run_benchmark(
        self,
        on_scenario_complete: Optional[Callable[[ScenarioResult], None]] = None,
        on_turn_complete: Optional[Callable[[str, int, TurnTelemetry], None]] = None,
    ) -> tuple[BenchmarkMetrics, List[ScenarioResult]]:
        """Run complete benchmark suite across configured scenarios."""
        scenarios = self.load_seed_scenarios()
        selected = scenarios[: self.config.max_scenarios]

        results: List[ScenarioResult] = []
        for sc in selected:
            scenario_id = sc.get("id", "SCENARIO")

            def turn_wrapper(turn_num: int, t_data: TurnTelemetry):
                if on_turn_complete:
                    on_turn_complete(scenario_id, turn_num, t_data)

            sc_res = self.run_scenario(sc, on_turn_callback=turn_wrapper)
            results.append(sc_res)
            if on_scenario_complete:
                on_scenario_complete(sc_res)

        metrics = compute_metrics(results)
        self.report_generator.generate_all(metrics, results, model_name=self.config.model_name)
        return metrics, results
