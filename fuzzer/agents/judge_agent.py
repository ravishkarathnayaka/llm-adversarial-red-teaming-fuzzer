"""Fuzzer Judge Agent bridge."""

from benchmark_engine.agents.judge_evaluator import (
    JudgeEvaluator as JudgeAgent,
    JudgeVerdict,
    EvaluationResult,
)

__all__ = ["JudgeAgent", "JudgeVerdict", "EvaluationResult"]
