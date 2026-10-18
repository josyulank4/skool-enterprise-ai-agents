"""
Agent tool contract: the adapter layer between the raw ticket API and the
model. Implements everything from Lesson 21:

  - function-calling JSON schema the model can trust
  - input validation (types, enums, required fields)
  - authorization scoping (role -> departments, read vs write)
  - guardrails: rate limits + explicit confirmation for write operations
  - audit logging of every call, argument, and result
"""

import json
import time
from dataclasses import asdict

from ticket_api import TicketAPI

# ---------------------------------------------------------------- schemas
# These are the model-facing contracts: precise types, enums, constraints,
# and human-readable descriptions. The model never sees the raw API.

TOOL_SCHEMAS = {
    "get_ticket": {
        "name": "get_ticket",
        "description": "Look up a single support ticket by ID. Read-only.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "pattern": "^T-[0-9]{4}$",
                    "description": "Ticket ID, e.g. T-1001",
                }
            },
            "required": ["ticket_id"],
            "additionalProperties": False,
        },
    },
    "search_tickets": {
        "name": "search_tickets",
        "description": "Search tickets, optionally filtered. Read-only.",
        "parameters": {
            "type": "object",
            "properties": {
                "department": {"type": "string",
                               "description": "Department name filter"},
                "status": {"type": "string",
                           "enum": ["open", "in_progress", "resolved",
                                    "closed"]},
            },
            "additionalProperties": False,
        },
    },
    "update_ticket_status": {
        "name": "update_ticket_status",
        "description": "Change a ticket's status. WRITE operation: requires "
                       "confirmation and department authorization.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "pattern": "^T-[0-9]{4}$"},
                "new_status": {"type": "string",
                               "enum": ["open", "in_progress", "resolved",
                                        "closed"]},
                "confirmed": {"type": "boolean",
                              "description": "Must be true: the caller "
                                             "explicitly confirmed this write"},
            },
            "required": ["ticket_id", "new_status", "confirmed"],
            "additionalProperties": False,
        },
    },
    "create_ticket": {
        "name": "create_ticket",
        "description": "Open a new ticket. WRITE operation: requires "
                       "confirmation and department authorization.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "minLength": 5, "maxLength": 120},
                "department": {"type": "string"},
                "priority": {"type": "string",
                             "enum": ["low", "medium", "high", "critical"]},
                "confirmed": {"type": "boolean"},
            },
            "required": ["title", "department", "priority", "confirmed"],
            "additionalProperties": False,
        },
    },
}

WRITE_TOOLS = {"update_ticket_status", "create_ticket"}

# role -> {departments it may touch, may_write}
ROLE_POLICY = {
    "it_support_agent": {"departments": {"IT"}, "may_write": True},
    "finance_agent": {"departments": {"Finance"}, "may_write": True},
    "readonly_auditor": {"departments": {"IT", "Finance"}, "may_write": False},
}


class ToolError(Exception):
    """A structured, model-readable tool failure (not a raw traceback)."""


class RateLimiter:
    def __init__(self, max_calls=10, window_s=60):
        self.max_calls, self.window_s = max_calls, window_s
        self._calls = []

    def check(self):
        now = time.time()
        self._calls = [t for t in self._calls if now - t < self.window_s]
        if len(self._calls) >= self.max_calls:
            raise ToolError(
                f"rate limit exceeded: {self.max_calls} calls per "
                f"{self.window_s}s")
        self._calls.append(now)


def _validate(schema, args):
    """Minimal JSON-schema-style validation (stdlib only)."""
    props = schema["parameters"]["properties"]
    for req in schema["parameters"].get("required", []):
        if req not in args:
            raise ToolError(f"missing required parameter '{req}'")
    for k in args:
        if k not in props and not schema["parameters"].get(
                "additionalProperties", True):
            raise ToolError(f"unexpected parameter '{k}'")
    for k, v in args.items():
        spec = props[k]
        if spec.get("type") == "string" and not isinstance(v, str):
            raise ToolError(f"parameter '{k}' must be a string")
        if spec.get("type") == "boolean" and not isinstance(v, bool):
            raise ToolError(f"parameter '{k}' must be a boolean")
        if "enum" in spec and v not in spec["enum"]:
            raise ToolError(
                f"parameter '{k}' must be one of {spec['enum']}, got {v!r}")
        if "pattern" in spec:
            import re
            if not re.match(spec["pattern"], v):
                raise ToolError(
                    f"parameter '{k}' does not match {spec['pattern']}")
        if "minLength" in spec and len(v) < spec["minLength"]:
            raise ToolError(f"parameter '{k}' too short")
        if "maxLength" in spec and len(v) > spec["maxLength"]:
            raise ToolError(f"parameter '{k}' too long")


class TicketToolContract:
    """The contract: validates, authorizes, rate-limits, confirms, audits."""

    def __init__(self, role, api=None, rate_limiter=None):
        if role not in ROLE_POLICY:
            raise ValueError(f"unknown role {role}")
        self.role = role
        self.policy = ROLE_POLICY[role]
        self.api = api or TicketAPI()
        self.limiter = rate_limiter or RateLimiter()
        self.audit_log = []

    def _audit(self, tool, args, ok, detail):
        self.audit_log.append({
            "tool": tool, "args": args, "role": self.role,
            "ok": ok, "detail": detail,
        })

    def _authorize(self, tool, args, target_department=None):
        if tool in WRITE_TOOLS and not self.policy["may_write"]:
            raise ToolError(f"role '{self.role}' is read-only")
        if target_department and target_department not in \
                self.policy["departments"]:
            raise ToolError(
                f"role '{self.role}' may not touch department "
                f"'{target_department}'")
        if tool in WRITE_TOOLS and not args.get("confirmed"):
            raise ToolError(
                "write operation blocked: 'confirmed' must be true — "
                "the agent must obtain explicit confirmation first")

    def call(self, tool, args):
        if tool not in TOOL_SCHEMAS:
            raise ToolError(f"unknown tool '{tool}'")
        try:
            self.limiter.check()
            _validate(TOOL_SCHEMAS[tool], args)
            if tool == "get_ticket":
                t = self.api.get_ticket(args["ticket_id"])
                if t is None:
                    raise ToolError(f"ticket {args['ticket_id']} not found")
                self._authorize(tool, args, t.department)
                result = asdict(t)
            elif tool == "search_tickets":
                dept = args.get("department")
                self._authorize(tool, args, dept)
                result = [asdict(t) for t in
                          self.api.search_tickets(**{k: v for k, v in
                                                     args.items()})]
            elif tool == "update_ticket_status":
                t = self.api.get_ticket(args["ticket_id"])
                if t is None:
                    raise ToolError(f"ticket {args['ticket_id']} not found")
                self._authorize(tool, args, t.department)
                result = asdict(self.api.update_status(
                    args["ticket_id"], args["new_status"]))
            elif tool == "create_ticket":
                self._authorize(tool, args, args["department"])
                result = asdict(self.api.create_ticket(
                    args["title"], args["department"], args["priority"]))
            self._audit(tool, args, True, "ok")
            return {"ok": True, "result": result}
        except ToolError as e:
            self._audit(tool, args, False, str(e))
            return {"ok": False, "error": str(e)}
        except (KeyError, ValueError) as e:
            self._audit(tool, args, False, str(e))
            return {"ok": False, "error": f"api error: {e}"}

    def manifest(self):
        """MCP-style manifest describing this tool server."""
        return {
            "server": "ticket-tool-server",
            "version": "1.0.0",
            "role": self.role,
            "tools": list(TOOL_SCHEMAS.values()),
        }
