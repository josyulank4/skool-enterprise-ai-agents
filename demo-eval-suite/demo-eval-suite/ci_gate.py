#!/usr/bin/env python3
"""
CI gate — Lesson 30: "Evals in CI/CD: Quality Gates for Agent Deployments".

Reads results.json from eval_runner.py and enforces promotion thresholds.
Exit code 0 = ship it. Exit code 1 = blocked, with the failing gates named.

Thresholds are configurable via env vars so teams can tighten them over time.

Run:
    python eval_runner.py && python ci_gate.py
    echo "exit code: $?"
"""

import json
import os
import sys
from pathlib import Path

RESULTS = Path(__file__).parent / "results.json"

THRESHOLDS = {
    "min_pass_rate": float(os.environ.get("GATE_MIN_PASS_RATE", "0.75")),
    "max_avg_latency_ms": float(os.environ.get("GATE_MAX_LATENCY_MS",
                                               "500")),
    "max_total_cost_usd": float(os.environ.get("GATE_MAX_COST_USD",
                                               "0.01")),
}


def main():
    if not RESULTS.exists():
        print("BLOCKED: results.json not found — run eval_runner.py first")
        sys.exit(1)
    summary = json.loads(RESULTS.read_text())
    failures = []

    if summary["pass_rate"] < THRESHOLDS["min_pass_rate"]:
        failures.append(
            f"pass_rate {summary['pass_rate']:.0%} < "
            f"{THRESHOLDS['min_pass_rate']:.0%}")
    if summary["avg_latency_ms"] > THRESHOLDS["max_avg_latency_ms"]:
        failures.append(
            f"avg_latency {summary['avg_latency_ms']}ms > "
            f"{THRESHOLDS['max_avg_latency_ms']}ms")
    if summary["total_est_cost_usd"] > THRESHOLDS["max_total_cost_usd"]:
        failures.append(
            f"total_cost ${summary['total_est_cost_usd']:.6f} > "
            f"${THRESHOLDS['max_total_cost_usd']:.6f}")

    failed_tasks = [tid for tid, t in summary["tasks"].items()
                    if not t["pass"]]
    if failed_tasks:
        print(f"Failed tasks: {', '.join(failed_tasks)}")

    if failures:
        print("DEPLOYMENT BLOCKED by eval gate:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)

    print(f"GATE PASSED: {summary['passed']}/{summary['total']} tasks, "
          f"{summary['pass_rate']:.0%} pass rate, "
          f"{summary['avg_latency_ms']}ms avg latency, "
          f"${summary['total_est_cost_usd']:.6f} total cost — safe to ship.")


if __name__ == "__main__":
    main()
