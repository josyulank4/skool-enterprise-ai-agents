#!/usr/bin/env python3
"""
Tool-contract demo — Lesson 21: "Design a Tool Contract: From API to
Agent-Ready Tool".

Runs six scenarios through the contract and shows each one being handled:
  1. correct read call            -> succeeds
  2. correct write WITH confirm   -> succeeds
  3. write WITHOUT confirmation   -> BLOCKED by the confirmation guardrail
  4. cross-department write       -> BLOCKED by authorization scoping
  5. invalid input (bad enum)     -> BLOCKED by schema validation
  6. rate-limit burst             -> BLOCKED by the rate limiter

Run:
    python demo.py
"""

import json

from tool_contract import TOOL_SCHEMAS, RateLimiter, TicketToolContract


def show(label, response):
    status = "OK " if response["ok"] else "BLOCKED"
    detail = (json.dumps(response["result"])
              if response["ok"] else response["error"])
    print(f"[{status}] {label}\n       {detail}\n")


def main():
    agent = TicketToolContract(role="it_support_agent")

    # 1. correct read
    show("get_ticket T-1001",
         agent.call("get_ticket", {"ticket_id": "T-1001"}))

    # 2. correct write with explicit confirmation
    show("update T-1001 -> in_progress (confirmed)",
         agent.call("update_ticket_status",
                    {"ticket_id": "T-1001", "new_status": "in_progress",
                     "confirmed": True}))

    # 3. write WITHOUT confirmation -> blocked
    show("update T-1001 -> resolved (NOT confirmed)",
         agent.call("update_ticket_status",
                    {"ticket_id": "T-1001", "new_status": "resolved",
                     "confirmed": False}))

    # 4. cross-department write -> blocked (IT role, Finance ticket)
    show("create Finance ticket as IT role (confirmed)",
         agent.call("create_ticket",
                    {"title": "Q3 budget review", "department": "Finance",
                     "priority": "medium", "confirmed": True}))

    # 5. invalid input: bad enum value -> blocked by schema validation
    show("get_ticket with bad status enum",
         agent.call("search_tickets", {"status": "eventually"}))

    # 6. rate-limit burst: 3 allowed, 4th blocked
    burst = TicketToolContract(role="readonly_auditor",
                               rate_limiter=RateLimiter(max_calls=3,
                                                        window_s=60))
    for i in range(4):
        r = burst.call("get_ticket", {"ticket_id": "T-1003"})
        show(f"burst call {i + 1}/4 (limit 3)", r)

    # 7. the MCP-style manifest the model would discover
    print("MCP manifest tools exposed:",
          [t["name"] for t in agent.manifest()["tools"]])
    print(f"\nAudit log: {len(agent.audit_log)} calls recorded "
          f"({sum(1 for a in agent.audit_log if not a['ok'])} blocked)")

    with open("mcp_manifest.json", "w", encoding="utf-8") as f:
        json.dump(agent.manifest(), f, indent=2)
    print("Wrote mcp_manifest.json")


if __name__ == "__main__":
    main()
