"""Report Generator: Produces JSON, CSV, Markdown, and interactive HTML benchmark risk reports."""

import csv
import json
import os
from typing import Dict, List, Optional
from benchmark_engine.reporting.metrics import BenchmarkMetrics, ScenarioResult


class ReportGenerator:
    """Generates structured benchmark reports in multiple industry formats."""

    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_all(
        self,
        metrics: BenchmarkMetrics,
        results: List[ScenarioResult],
        model_name: str = "Target-SUT",
    ) -> Dict[str, str]:
        """Generate JSON, CSV, Markdown, and HTML reports."""
        paths = {}
        paths["json"] = self.generate_json(metrics, results)
        paths["csv"] = self.generate_csv(results)
        paths["markdown"] = self.generate_markdown(metrics, results, model_name)
        paths["html"] = self.generate_html(metrics, results, model_name)
        return paths

    def generate_json(self, metrics: BenchmarkMetrics, results: List[ScenarioResult]) -> str:
        """Export raw metrics and telemetry to JSON."""
        file_path = os.path.join(self.output_dir, "benchmark_report.json")
        payload = {
            "summary_metrics": metrics.model_dump(),
            "scenarios": [s.model_dump() for s in results],
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return file_path

    def generate_csv(self, results: List[ScenarioResult]) -> str:
        """Export turn-by-turn telemetry to CSV for data analysis."""
        file_path = os.path.join(self.output_dir, "telemetry.csv")
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "scenario_id",
                "scenario_name",
                "mitre_id",
                "turn_number",
                "strategy_used",
                "verdict",
                "severity_score",
                "canary_leaked",
                "latency_ms",
                "prompt_snippet",
                "response_snippet",
            ])
            for s in results:
                for t in s.turns:
                    writer.writerow([
                        s.scenario_id,
                        s.name,
                        s.mitre_id,
                        t.turn_number,
                        t.strategy_used,
                        t.verdict,
                        t.severity_score,
                        t.canary_leaked,
                        round(t.latency_ms, 2),
                        t.prompt.replace("\n", " ")[:80],
                        t.response.replace("\n", " ")[:80],
                    ])
        return file_path

    def generate_markdown(
        self,
        metrics: BenchmarkMetrics,
        results: List[ScenarioResult],
        model_name: str = "Target-SUT",
    ) -> str:
        """Generate human-readable Markdown summary report."""
        file_path = os.path.join(self.output_dir, "benchmark_report.md")
        lines = [
            f"# Automated LLM Safety & Robustness Benchmark Report",
            f"",
            f"**Target System**: `{model_name}`  ",
            f"**Resilience Score**: **{metrics.resilience_score} / 100**  ",
            f"**Safety Adherence Rate (SAR)**: `{metrics.safety_adherence_rate_pct}%`  ",
            f"**Attack Success Rate (ASR)**: `{metrics.attack_success_rate_pct}%`  ",
            f"**Canary Leakage Rate**: `{metrics.canary_leakage_rate_pct}%`  ",
            f"",
            f"---",
            f"",
            f"## 1. Executive Summary",
            f"",
            f"| Metric | Value | Reference Standard |",
            f"| :--- | :--- | :--- |",
            f"| Total Scenarios Evaluated | `{metrics.total_scenarios}` | NIST AI RMF MAP 1.5 |",
            f"| Total Conversational Turns | `{metrics.total_turns}` | Multi-Turn Stress Test |",
            f"| Policy Violations Identified | `{metrics.total_violations}` | MITRE ATLAS AML.T0054 |",
            f"| Partial Disclosures | `{metrics.total_partial_disclosures}` | NIST AI RMF MANAGE 2.4 |",
            f"| Canary Secret Leaks | `{metrics.total_canary_leaks}` | MITRE ATLAS AML.T0056 |",
            f"| Average Severity Score (0-10) | `{metrics.average_severity_score}` | Normalized Risk Index |",
            f"| Overall System Resilience | `{metrics.resilience_score} / 100` | Enterprise Safety Benchmark |",
            f"",
            f"## 2. MITRE ATLAS Matrix Breakdown",
            f"",
            f"| Technique ID | Description | Tests | Violations | Adherence Rate | Avg Severity |",
            f"| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for m_id, tech in metrics.technique_breakdown.items():
            lines.append(
                f"| `{m_id}` | Technique Evaluation | {tech.total_probes} | {tech.violations} | {tech.adherence_rate_pct}% | {tech.avg_severity}/10 |"
            )

        lines.extend([
            f"",
            f"## 3. Detailed Scenario Telemetry",
            f"",
            f"| ID | Scenario Name | Category | Turns | Final Verdict | Max Severity | Canary Leaked |",
            f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])

        for s in results:
            v_badge = "🔴 VIOLATION" if s.is_compromised else ("🟡 PARTIAL" if s.final_verdict == "PARTIAL_DISCLOSURE" else "🟢 COMPLIANT")
            leak_badge = "⚠️ YES" if s.canary_leaked else "SAFE"
            lines.append(
                f"| `{s.scenario_id}` | {s.name} | {s.category} | {len(s.turns)} | {v_badge} | {s.max_severity_score}/10 | {leak_badge} |"
            )

        lines.append("")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return file_path

    def generate_html(
        self,
        metrics: BenchmarkMetrics,
        results: List[ScenarioResult],
        model_name: str = "Target-SUT",
    ) -> str:
        """Generate sleek, responsive dark-mode interactive HTML report."""
        file_path = os.path.join(self.output_dir, "benchmark_report.html")

        # Color codes based on resilience
        score_color = "#10b981" if metrics.resilience_score >= 80 else ("#f59e0b" if metrics.resilience_score >= 50 else "#ef4444")

        # Build table rows
        rows_html = []
        for s in results:
            badge_class = "badge-danger" if s.is_compromised else ("badge-warning" if s.final_verdict == "PARTIAL_DISCLOSURE" else "badge-success")
            canary_badge = '<span class="badge-danger">LEAKED</span>' if s.canary_leaked else '<span class="badge-success">SAFE</span>'
            
            # Dialog details
            dialog_turns = []
            for t in s.turns:
                t_badge = "badge-danger" if t.verdict == "VIOLATION" else "badge-success"
                dialog_turns.append(f"""
                <div class="turn-box">
                    <div class="turn-header">
                        <strong>Turn {t.turn_number}</strong> — Strategy: <code>{t.strategy_used}</code>
                        <span class="{t_badge}">{t.verdict} ({t.severity_score}/10)</span>
                    </div>
                    <div class="prompt-view"><strong>Probe:</strong> {self._escape(t.prompt)}</div>
                    <div class="response-view"><strong>Response:</strong> {self._escape(t.response)}</div>
                </div>
                """)

            dialog_html = "".join(dialog_turns)

            rows_html.append(f"""
            <tr>
                <td><code>{s.scenario_id}</code></td>
                <td><strong>{self._escape(s.name)}</strong><br><small class="text-muted">{s.mitre_id} - {s.category}</small></td>
                <td>{len(s.turns)}</td>
                <td><span class="{badge_class}">{s.final_verdict}</span></td>
                <td><strong>{s.max_severity_score} / 10</strong></td>
                <td>{canary_badge}</td>
                <td>
                    <details>
                        <summary class="btn-inspect">Inspect Dialogue</summary>
                        <div class="turn-container">{dialog_html}</div>
                    </details>
                </td>
            </tr>
            """)

        table_body = "\n".join(rows_html)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Safety & Robustness Benchmark Report</title>
    <style>
        :root {{
            --bg-primary: #0a0f1d;
            --bg-secondary: #131b2e;
            --bg-card: #1c2640;
            --text-primary: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #2e3d63;
            --accent-blue: #38bdf8;
            --accent-green: #10b981;
            --accent-amber: #f59e0b;
            --accent-red: #ef4444;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        body {{ background: var(--bg-primary); color: var(--text-primary); padding: 32px 24px; }}
        .container {{ max-width: 1280px; margin: 0 auto; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 24px; margin-bottom: 32px; }}
        .header h1 {{ font-size: 26px; font-weight: 700; color: #fff; }}
        .header p {{ color: var(--text-muted); font-size: 14px; margin-top: 4px; }}
        .badge-target {{ background: rgba(56, 189, 248, 0.15); color: var(--accent-blue); padding: 6px 14px; border-radius: 999px; font-size: 13px; font-weight: 600; border: 1px solid rgba(56, 189, 248, 0.3); }}
        
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px; margin-bottom: 36px; }}
        .kpi-card {{ background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; text-align: center; }}
        .kpi-value {{ font-size: 32px; font-weight: 800; margin-top: 8px; }}
        .kpi-title {{ font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); }}

        .table-card {{ background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden; margin-bottom: 36px; }}
        .card-header {{ padding: 18px 24px; border-bottom: 1px solid var(--border-color); font-weight: 700; font-size: 18px; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }}
        th, td {{ padding: 14px 20px; border-bottom: 1px solid var(--border-color); }}
        th {{ background: #182239; color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 12px; letter-spacing: 0.05em; }}
        tr:hover td {{ background: rgba(255, 255, 255, 0.02); }}

        .badge-success {{ background: rgba(16, 185, 129, 0.15); color: var(--accent-green); padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 12px; border: 1px solid rgba(16, 185, 129, 0.3); }}
        .badge-warning {{ background: rgba(245, 158, 11, 0.15); color: var(--accent-amber); padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 12px; border: 1px solid rgba(245, 158, 11, 0.3); }}
        .badge-danger {{ background: rgba(239, 68, 68, 0.15); color: var(--accent-red); padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 12px; border: 1px solid rgba(239, 68, 68, 0.3); }}

        .btn-inspect {{ cursor: pointer; color: var(--accent-blue); font-weight: 600; outline: none; }}
        .turn-container {{ margin-top: 12px; padding: 12px; background: #0c1220; border-radius: 8px; border: 1px solid var(--border-color); }}
        .turn-box {{ margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #1a253c; }}
        .turn-box:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
        .turn-header {{ display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 12px; }}
        .prompt-view {{ background: #141c2e; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; font-family: monospace; font-size: 12px; }}
        .response-view {{ background: #1a233a; padding: 8px 12px; border-radius: 6px; font-family: monospace; font-size: 12px; color: #cbd5e1; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Automated LLM Safety & Robustness Benchmark</h1>
                <p>Mapped to MITRE ATLAS Matrix and NIST AI Risk Management Framework</p>
            </div>
            <div>
                <span class="badge-target">SUT: {model_name}</span>
            </div>
        </div>

        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-title">Resilience Score</div>
                <div class="kpi-value" style="color: {score_color};">{metrics.resilience_score} <span style="font-size:16px;">/ 100</span></div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Safety Adherence (SAR)</div>
                <div class="kpi-value" style="color: var(--accent-green);">{metrics.safety_adherence_rate_pct}%</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Attack Success (ASR)</div>
                <div class="kpi-value" style="color: var(--accent-red);">{metrics.attack_success_rate_pct}%</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Canary Leakage Rate</div>
                <div class="kpi-value" style="color: var(--accent-amber);">{metrics.canary_leakage_rate_pct}%</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Avg Severity (0-10)</div>
                <div class="kpi-value">{metrics.average_severity_score}</div>
            </div>
        </div>

        <div class="table-card">
            <div class="card-header">Scenario Evaluation Matrix</div>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Scenario Name & Category</th>
                        <th>Turns</th>
                        <th>Final Verdict</th>
                        <th>Max Severity</th>
                        <th>Canary Status</th>
                        <th>Telemetry</th>
                    </tr>
                </thead>
                <tbody>
                    {table_body}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return file_path

    @staticmethod
    def _escape(text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )
