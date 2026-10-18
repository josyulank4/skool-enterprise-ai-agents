# Demo: Tool Contract Design

**Course lesson:** Lesson 21 — "[DEMO] Design a Tool Contract: From API to Agent-Ready Tool"
**Folder:** `demo-tool-contract/`

Converts a realistic enterprise API (a ticket system) into a safe,
agent-ready tool contract — the adapter layer between the raw API and the
model. Every protection from the lesson is implemented and demonstrated:
schema validation, authorization scoping, write-confirmation, rate limits,
and audit logging, plus an MCP-style manifest.

## What it does

- `ticket_api.py` — mock enterprise ticket API (lookup, search, status
  transitions, creation). No network, no credentials.
- `tool_contract.py` — the contract:
  - **Function-calling JSON schemas** for 4 tools (`get_ticket`,
    `search_tickets`, `update_ticket_status`, `create_ticket`) with types,
    enums, patterns, and model-facing descriptions.
  - **Input validation** — required fields, enums, regex, length limits.
  - **Authorization scoping** — roles (`it_support_agent`, `finance_agent`,
    `readonly_auditor`) mapped to departments and read/write rights.
  - **Write confirmation** — write tools require `"confirmed": true`.
  - **Rate limiting** — configurable calls-per-window.
  - **Audit log** — every call, argument, role, and outcome recorded.
  - **`manifest()`** — MCP-style server manifest describing the tools.
- `demo.py` — runs 7 scenarios: correct read, confirmed write, then each
  guardrail firing (unconfirmed write, cross-department write, invalid enum,
  rate-limit burst), and writes `mcp_manifest.json`.

## Prerequisites

- Python 3.9+ (standard library only — no install needed)

## Run

```bash
cd demo-tool-contract
python demo.py
```

## Expected output

```
[OK ] get_ticket T-1001 ...
[OK ] update T-1001 -> in_progress (confirmed) ...
[BLOCKED] update T-1001 -> resolved (NOT confirmed)
       write operation blocked: 'confirmed' must be true ...
[BLOCKED] create Finance ticket as IT role (confirmed)
       role 'it_support_agent' may not touch department 'Finance'
[BLOCKED] get_ticket with bad status enum
       parameter 'status' must be one of [...]
[BLOCKED] burst call 4/4 (limit 3)
       rate limit exceeded: 3 calls per 60s
MCP manifest tools exposed: ['get_ticket', 'search_tickets', ...]
Audit log: 5 calls recorded (3 blocked)
Wrote mcp_manifest.json
```

## Adapt it to your own API

1. Replace `TicketAPI` with your API client (keep the method names or update
   the contract's `call()` dispatch).
2. Write a JSON schema per tool in `TOOL_SCHEMAS` — precise `description`
   fields are what the model actually reasons with.
3. Encode your authorization model in `ROLE_POLICY`.
4. Decide which tools are write tools in `WRITE_TOOLS` — every one of them
   gets the confirmation gate automatically.

## Reusable checklist (from the lesson)

- [ ] Schema: types, enums, required, no open-ended `additionalProperties`
- [ ] Descriptions written for the model, not for humans
- [ ] Role-based department scoping on every tool
- [ ] Confirmation required on every write
- [ ] Rate limits on every tool
- [ ] Structured errors (never raw tracebacks to the model)
- [ ] Audit log on every call
