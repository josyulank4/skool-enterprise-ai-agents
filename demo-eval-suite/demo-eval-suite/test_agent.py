"""
Test agent under evaluation — Lesson 29.

A small deterministic tool-using agent (no API keys, no network) so the eval
suite runs anywhere. It understands triage/search prompts over the ticket
store and follows the safety policy: read tools are free, write tools need
explicit confirmation, unknown tools don't exist.
"""

import os
import re
import time


# Regression switch for the Lesson 29 demo ("deliberately break the agent").
# When AGENT_BREAK_CONFIRMATION=1, the agent skips the explicit-confirmation
# safety behavior — simulating the "small prompt edit" from the lesson — so
# the eval suite catches the regression on the no-write-without-ask task.
BREAK_CONFIRMATION = os.environ.get("AGENT_BREAK_CONFIRMATION", "") == "1"


class TestAgent:
    ALLOWED_TOOLS = {"get_ticket", "search_tickets"}

    def __init__(self, store):
        self.store = store          # dict ticket_id -> dict
        self.tool_calls = []        # recorded per task: [(tool, args)]
        self.latency_ms = 0

    def _call(self, tool, args):
        if tool not in self.ALLOWED_TOOLS:
            raise PermissionError(f"tool '{tool}' is not available "
                                  f"to this agent")
        self.tool_calls.append((tool, args))
        if tool == "get_ticket":
            return self.store.get(args["ticket_id"])
        if tool == "search_tickets":
            out = list(self.store.values())
            if args.get("department"):
                out = [t for t in out
                       if t["department"] == args["department"]]
            if args.get("status"):
                out = [t for t in out if t["status"] == args["status"]]
            return out

    def run(self, prompt):
        """One agent turn: plan tool calls, execute, synthesize an answer."""
        self.tool_calls = []
        start = time.perf_counter()
        try:
            answer = self._route(prompt)
        except PermissionError as e:
            answer = f"Blocked by safety policy: {e}"
        self.latency_ms = (time.perf_counter() - start) * 1000
        # simulate token usage for the cost metric
        self.tokens_used = 400 + 25 * len(prompt.split())
        return answer

    # ------------------------------------------------------------- policy
    def _route(self, prompt):
        p = prompt.lower()

        m = re.search(r"t-?\d{4}", p)
        if m and ("triage" in p or "ticket" in p):
            tid = m.group(0).upper().replace("T", "T-") \
                if "-" not in m.group(0) else m.group(0).upper()
            tid = "T-" + re.search(r"\d{4}", tid).group(0)
            t = self._call("get_ticket", {"ticket_id": tid})
            if t is None:
                return f"Ticket {tid} not found."
            if "close" in p or "resolve" in p:
                if BREAK_CONFIRMATION:
                    # Regression mode: confirmation instruction removed —
                    # the agent "helpfully" resolves directly. The eval
                    # suite catches this on the no-write-without-ask task.
                    return (f"Ticket {tid} ('{t['title']}') resolved.")
                return (f"Ticket {tid} ('{t['title']}') is currently "
                        f"{t['status']}. I need your explicit confirmation "
                        f"before changing its status.")
            return (f"Ticket {tid}: '{t['title']}' — status {t['status']}, "
                    f"priority {t['priority']}, department {t['department']}.")

        if "list" in p or "which" in p:
            dept = next((d for d in ("IT", "Finance", "Engineering")
                         if d.lower() in p), None)
            status = next((s for s in ("open", "in_progress", "resolved",
                                       "closed") if s in p), None)
            tickets = self._call("search_tickets",
                                 {"department": dept, "status": status})
            if not tickets:
                return "No tickets match those filters."
            if "highest priority" in p:
                rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
                tickets = sorted(tickets,
                                 key=lambda t: rank[t["priority"]],
                                 reverse=True)
                top = tickets[0]
                return (f"Highest priority: {top['id']} "
                        f"('{top['title']}') — {top['priority']}.")
            return "Matching tickets: " + ", ".join(
                f"{t['id']} ('{t['title']}')" for t in tickets)

        return ("I can triage tickets by ID or list tickets by department "
                "and status.")
