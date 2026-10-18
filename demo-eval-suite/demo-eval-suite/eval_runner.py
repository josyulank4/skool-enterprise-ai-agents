#!/usr/bin/env python3
"""
Eval runner — Lesson 29: "Run an Eval Suite: Automated Testing for an Agent".

Runs the golden dataset through the test agent and scores every task with
four scorers (from the lesson):
  1. exact/contains match on the expected answer
  2. tool-sequence check (did the agent call the expected tools?)
  3. safety check (did the agent avoid disallowed tools?)
  4. heuristic judge (stand-in for LLM-as-judge; swap via EVAL_JUDGE=openai)

Metrics per task and in aggregate: pass rate, avg latency, estimated cost.
Writes results.json for the CI gate (Lesson 30).

Run:
    python eval_runner.py
"""

import json
import os
import time
from pathlib import Path

from test_agent import TestAgent

HERE = Path(__file__).parent
TOKEN_PRICE_PER_1K = 0.002  # USD, placeholder for the cost model

TICKET_STORE = {
    "T-1001": {"id": "T-1001", "title": "VPN tunnel drops hourly",
               "department": "IT", "status": "open", "priority": "high"},
    "T-1002": {"id": "T-1002", "title": "Expense report stuck in approval",
               "department": "Finance", "status": "in_progress",
               "priority": "medium"},
    "T-1003": {"id": "T-1003", "title": "New-hire laptop request",
               "department": "IT", "status": "resolved", "priority": "low"},
}


# ---------------------------------------------------------------- scorers

def score_answer_contains(answer, expected_terms):
    missing = [t for t in expected_terms if t.lower() not in answer.lower()]
    return {"pass": not missing, "detail": f"missing={missing}"}


def score_tool_sequence(calls, expected_tools):
    called = [tool for tool, _ in calls]
    ok = all(t in called for t in expected_tools)
    return {"pass": ok, "detail": f"called={called}"}


def score_safety(calls, disallowed):
    violations = [tool for tool, _ in calls if tool in disallowed]
    return {"pass": not violations, "detail": f"violations={violations}"}


def heuristic_judge(prompt, answer, expected_terms):
    """Deterministic stand-in for LLM-as-judge.

    In production, replace with an LLM judge call (see EVAL_JUDGE below)
    and validate it against human ratings first — exactly as the lesson
    teaches. The interface (prompt, answer, expected -> verdict) is the
    same either way.
    """
    coverage = sum(1 for t in expected_terms if t.lower() in answer.lower())
    verdict = coverage / max(len(expected_terms), 1) >= 0.5
    return {"pass": verdict,
            "detail": f"term coverage {coverage}/{len(expected_terms)}"}


def llm_judge(prompt, answer, expected_terms):
    """Optional real LLM-as-judge via OpenAI-compatible API.

    Enable with:  EVAL_JUDGE=openai  and  OPENAI_API_KEY=sk-...
    Uses only the standard library (urllib). Kept separate so the default
    path never needs a key or a dependency.
    """
    import urllib.request
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("EVAL_JUDGE=openai but OPENAI_API_KEY is not set")
    payload = {
        "model": os.environ.get("EVAL_JUDGE_MODEL", "gpt-4o-mini"),
        "messages": [{
            "role": "user",
            "content": (
                "You are an eval judge. Task prompt: " + prompt +
                "\nAgent answer: " + answer +
                "\nExpected content: " + ", ".join(expected_terms) +
                "\nReply with exactly PASS or FAIL and one line of reason."
            ),
        }],
        "max_tokens": 60,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        text = json.load(r)["choices"][0]["message"]["content"]
    verdict = text.strip().upper().startswith("PASS")
    return {"pass": verdict, "detail": text.strip()[:120]}


JUDGES = {"heuristic": heuristic_judge, "openai": llm_judge}


# ------------------------------------------------------------------ runner

def run_task(agent, task, judge):
    answer = agent.run(task["prompt"])
    results = {
        "answer_match": score_answer_contains(
            answer, task["expected_answer_contains"]),
        "tool_sequence": score_tool_sequence(
            agent.tool_calls, task["expected_tools"]),
        "safety": score_safety(agent.tool_calls,
                              task["safety"]["disallowed_tools"]),
        "judge": judge(task["prompt"], answer,
                       task["expected_answer_contains"]),
    }
    results["pass"] = all(r["pass"] for r in results.values())
    results["latency_ms"] = round(agent.latency_ms, 2)
    results["est_cost_usd"] = round(agent.tokens_used / 1000 *
                                    TOKEN_PRICE_PER_1K, 6)
    return results


def main():
    dataset = json.loads((HERE / "golden_dataset.json").read_text())
    judge_name = os.environ.get("EVAL_JUDGE", "heuristic")
    judge = JUDGES[judge_name]
    print(f"Judge: {judge_name} | Tasks: {len(dataset)}\n")

    per_task, passed = {}, 0
    for task in dataset:
        agent = TestAgent(TICKET_STORE)
        res = run_task(agent, task, judge)
        per_task[task["id"]] = {"prompt": task["prompt"], **res}
        passed += res["pass"]
        mark = "PASS" if res["pass"] else "FAIL"
        print(f"[{mark}] {task['id']}: {task['prompt']}")
        for name, r in res.items():
            if name in ("pass", "latency_ms", "est_cost_usd"):
                continue
            s = "ok" if r["pass"] else "FAIL"
            print(f"       {name:14s} {s:4s} {r['detail']}")
        print(f"       latency {res['latency_ms']}ms | "
              f"est cost ${res['est_cost_usd']:.6f}\n")

    latencies = [r["latency_ms"] for r in per_task.values()]
    costs = [r["est_cost_usd"] for r in per_task.values()]
    summary = {
        "judge": judge_name,
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total": len(dataset),
        "passed": passed,
        "pass_rate": round(passed / len(dataset), 3),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
        "total_est_cost_usd": round(sum(costs), 6),
        "tasks": per_task,
    }
    (HERE / "results.json").write_text(json.dumps(summary, indent=2))
    print("=" * 60)
    print(f"SUMMARY: {passed}/{len(dataset)} passed "
          f"({summary['pass_rate']:.0%}) | "
          f"avg latency {summary['avg_latency_ms']}ms | "
          f"total est cost ${summary['total_est_cost_usd']:.6f}")
    print("Wrote results.json")


if __name__ == "__main__":
    main()
