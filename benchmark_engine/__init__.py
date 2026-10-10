"""Automated LLM Safety & Robustness Benchmark Suite."""

from benchmark_engine.orchestrator import Orchestrator, BenchmarkConfig
from benchmark_engine.agents.target_client import TargetClient, TargetResponse
from benchmark_engine.agents.judge_evaluator import JudgeEvaluator, JudgeVerdict, EvaluationResult
from benchmark_engine.agents.probe_generator import ProbeGeneratorAgent, GeneratedProbe
from benchmark_engine.strategies.mutator import StrategyMutator
from benchmark_engine.reporting.metrics import BenchmarkMetrics, ScenarioResult, compute_metrics
from benchmark_engine.reporting.report_generator import ReportGenerator

__version__ = "1.0.0"

__all__ = [
    "Orchestrator",
    "BenchmarkConfig",
    "TargetClient",
    "TargetResponse",
    "JudgeEvaluator",
    "JudgeVerdict",
    "EvaluationResult",
    "ProbeGeneratorAgent",
    "GeneratedProbe",
    "StrategyMutator",
    "BenchmarkMetrics",
    "ScenarioResult",
    "compute_metrics",
    "ReportGenerator",
]
