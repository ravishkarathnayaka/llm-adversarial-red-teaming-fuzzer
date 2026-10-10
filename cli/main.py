"""CLI Runner for Multi-Agent Adversarial Red Teaming and LLM Safety Benchmark."""

import argparse
import os
import sys
from typing import List, Optional

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from benchmark_engine.orchestrator import Orchestrator, BenchmarkConfig
from benchmark_engine.reporting.metrics import ScenarioResult, TurnTelemetry, BenchmarkMetrics

console = Console(safe_box=True)


def print_banner():
    banner = Text()
    banner.append("[*] MULTI-AGENT ADVERSARIAL RED TEAMING & SAFETY BENCHMARK\n", style="bold cyan")
    banner.append("    Automated LLM Fuzzer & Boundary Evaluator | MITRE ATLAS & NIST AI RMF", style="dim white")
    console.print(Panel(banner, box=box.ROUNDED, border_style="cyan"))


def run_benchmark_cli(args: argparse.Namespace) -> int:
    """Execute benchmark run with provided CLI arguments."""
    print_banner()

    # Normalize scenario count from either --iterations or --scenarios
    count = args.iterations if args.iterations is not None else args.scenarios
    count = count if count is not None else 5

    use_mock = args.mock or (args.target is None) or ("mock" in (args.target or "").lower())
    target_url = None if use_mock else (args.target or "http://localhost:11434")
    model_name = args.model or ("mock-hardened" if use_mock else "llama3")

    config = BenchmarkConfig(
        target_url=target_url,
        model_name=model_name,
        max_scenarios=count,
        max_turns_per_scenario=args.max_turns,
        strategy_override=args.strategy if args.strategy != "all" else None,
        use_mock=use_mock,
        mock_mode=args.mock_mode,
        output_dir=args.output_dir,
    )

    console.print(
        f"[bold blue]Target Engine:[/bold blue] {'Deterministic Mock LLM' if use_mock else target_url} "
        f"([cyan]{model_name}[/cyan]) | [bold blue]Scenarios:[/bold blue] {count} | "
        f"[bold blue]Max Turns:[/bold blue] {args.max_turns} | [bold blue]Mode:[/bold blue] {args.mock_mode}"
    )
    console.print()

    orchestrator = Orchestrator(config=config)

    # Prepare streaming table
    results_table = Table(title="Execution Progress & Live Telemetry", box=box.SIMPLE_HEAVY)
    results_table.add_column("ID", style="dim", width=14)
    results_table.add_column("Scenario Name", style="bold white", width=36)
    results_table.add_column("MITRE ID", style="cyan", width=12)
    results_table.add_column("Turns", justify="center", width=7)
    results_table.add_column("Final Verdict", justify="center", width=16)
    results_table.add_column("Severity", justify="center", width=10)
    results_table.add_column("Canary", justify="center", width=10)

    completed_results: List[ScenarioResult] = []

    def on_scenario_done(res: ScenarioResult):
        completed_results.append(res)
        canary_str = "[red]LEAKED[/red]" if res.canary_leaked else "[green]SAFE[/green]"
        v_text = "[red]VIOLATION[/red]" if res.is_compromised else (
            "[yellow]PARTIAL[/yellow]" if res.final_verdict == "PARTIAL_DISCLOSURE" else "[green]COMPLIANT[/green]"
        )
        results_table.add_row(
            res.scenario_id,
            res.name[:34],
            res.mitre_id,
            str(res.total_turns),
            v_text,
            f"{res.max_severity_score}/10",
            canary_str,
        )

    with console.status("[bold green]Executing multi-agent evaluation rounds...", spinner="dots"):
        metrics, results = orchestrator.run_benchmark(on_scenario_complete=on_scenario_done)

    console.print(results_table)
    console.print()

    # Scorecard Panel
    score_color = "green" if metrics.resilience_score >= 80 else ("yellow" if metrics.resilience_score >= 50 else "red")
    scorecard = Table.grid(padding=1)
    scorecard.add_column(style="bold white", width=34)
    scorecard.add_column(style="bold", width=20)

    scorecard.add_row("[+] Overall Resilience Score:", f"[{score_color}]{metrics.resilience_score} / 100[/{score_color}]")
    scorecard.add_row("[*] Safety Adherence Rate (SAR):", f"[green]{metrics.safety_adherence_rate_pct}%[/green]")
    scorecard.add_row("[!] Attack Success Rate (ASR):", f"[red]{metrics.attack_success_rate_pct}%[/red]")
    scorecard.add_row("[?] Canary Leakage Rate:", f"[yellow]{metrics.canary_leakage_rate_pct}%[/yellow]")
    scorecard.add_row("[#] Average Severity Score (0-10):", f"{metrics.average_severity_score}")
    scorecard.add_row("[~] Total Conversational Turns:", f"{metrics.total_turns}")

    console.print(Panel(scorecard, title="[bold cyan]Benchmark Risk Scorecard[/bold cyan]", box=box.ROUNDED, border_style="blue"))
    console.print()

    # Generated Reports List
    console.print("[bold green]Reports generated successfully:[/bold green]")
    console.print(f"  JSON:      [cyan]{os.path.abspath(os.path.join(args.output_dir, 'benchmark_report.json'))}[/cyan]")
    console.print(f"  CSV:       [cyan]{os.path.abspath(os.path.join(args.output_dir, 'telemetry.csv'))}[/cyan]")
    console.print(f"  Markdown:  [cyan]{os.path.abspath(os.path.join(args.output_dir, 'benchmark_report.md'))}[/cyan]")
    console.print(f"  HTML:      [cyan]{os.path.abspath(os.path.join(args.output_dir, 'benchmark_report.html'))}[/cyan]")
    console.print()

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fuzzer",
        description="Automated Multi-Agent Adversarial Red Teaming & LLM Safety Fuzzer",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Add run subcommand
    run_parser = subparsers.add_parser("run", help="Execute adversarial benchmark against target")
    _add_benchmark_args(run_parser)

    # Also add arguments to root parser so 'python -m cli.main --mock --iterations 5' works directly!
    _add_benchmark_args(parser)

    return parser


def _add_benchmark_args(p: argparse.ArgumentParser):
    p.add_argument("--target", "-t", type=str, default=None, help="Target LLM endpoint URL (e.g. http://localhost:11434)")
    p.add_argument("--model", "-m", type=str, default=None, help="Target model name (e.g. llama3, mistral)")
    p.add_argument("--iterations", "-i", type=int, default=None, help="Number of test scenarios/iterations to execute")
    p.add_argument("--scenarios", "-n", type=int, default=None, help="Alias for --iterations")
    p.add_argument("--max-turns", type=int, default=3, help="Max conversational turns per scenario (default: 3)")
    p.add_argument("--mock", action="store_true", help="Run against deterministic local mock LLM (Zero network)")
    p.add_argument("--mock-mode", choices=["hardened", "vulnerable"], default="hardened", help="Mock model security profile")
    p.add_argument("--strategy", "-s", type=str, default="all", help="Strategy filter (all, crescendo, base64, rot13, leetspeak, delimiters, roleplay, boundary)")
    p.add_argument("--output-dir", "-o", type=str, default="./reports", help="Directory where reports are saved")
    p.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logging")


def main():
    parser = build_parser()
    args = parser.parse_args()
    return run_benchmark_cli(args)


if __name__ == "__main__":
    sys.exit(main())
