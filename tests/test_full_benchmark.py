"""Integration tests running end-to-end benchmark cycles against deterministic Mock LLM."""

import os
import shutil
import pytest
from benchmark_engine.orchestrator import Orchestrator, BenchmarkConfig
from benchmark_engine.reporting.metrics import compute_metrics


@pytest.fixture
def temp_reports_dir(tmp_path):
    d = tmp_path / "reports"
    d.mkdir()
    return str(d)


def test_end_to_end_hardened_mock_run(temp_reports_dir):
    config = BenchmarkConfig(
        use_mock=True,
        mock_mode="hardened",
        max_scenarios=4,
        max_turns_per_scenario=2,
        output_dir=temp_reports_dir,
    )
    
    orchestrator = Orchestrator(config=config)
    metrics, results = orchestrator.run_benchmark()
    
    assert len(results) == 4
    assert metrics.total_scenarios == 4
    assert metrics.total_turns == 8
    
    # In hardened mode, target should adhere to safety rules and not leak canaries
    assert metrics.total_canary_leaks == 0
    assert metrics.safety_adherence_rate_pct >= 75.0
    assert metrics.resilience_score >= 70.0
    
    # Check reports were generated
    assert os.path.exists(os.path.join(temp_reports_dir, "benchmark_report.json"))
    assert os.path.exists(os.path.join(temp_reports_dir, "telemetry.csv"))
    assert os.path.exists(os.path.join(temp_reports_dir, "benchmark_report.md"))
    assert os.path.exists(os.path.join(temp_reports_dir, "benchmark_report.html"))


def test_end_to_end_vulnerable_mock_run(temp_reports_dir):
    config = BenchmarkConfig(
        use_mock=True,
        mock_mode="vulnerable",
        max_scenarios=3,
        max_turns_per_scenario=2,
        output_dir=temp_reports_dir,
    )
    
    orchestrator = Orchestrator(config=config)
    metrics, results = orchestrator.run_benchmark()
    
    assert len(results) == 3
    # In vulnerable mode, target complies with base64/canary probes
    assert metrics.attack_success_rate_pct > 0.0
    assert metrics.total_violations > 0
    assert metrics.resilience_score < 80.0


def test_empty_metrics_handling():
    metrics = compute_metrics([])
    assert metrics.total_scenarios == 0
    assert metrics.resilience_score == 100.0
    assert metrics.safety_adherence_rate_pct == 100.0
