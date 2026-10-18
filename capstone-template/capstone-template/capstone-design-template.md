# Capstone: Production Agent Design

> **Instructions:** Replace every `[bracketed prompt]` with your own content.
> The *worked example* (invoice-exception handling agent) shows what a
> completed section looks like — delete it as you fill in your own.

**Author:** [Your name]
**Organization:** [Your org]
**Process:** [The business process this agent will handle]
**Date:** [YYYY-MM-DD]

---

## 1. Business Case & ROI (maps to S1)

**[Prompt]** What business problem does this solve? Who feels the pain?
What does it cost today (hours × fully-loaded rate, error rate × rework
cost, SLA penalties)? What will the agent change, and what is the
conservative 12-month ROI? Who is the executive sponsor?

**Worked example — invoice-exception handling agent:**
AP clerks at a 500-person company manually resolve ~400 invoice exceptions
per month (PO mismatches, missing approvals, tax discrepancies). Each takes
~25 minutes → 167 hours/month ≈ $12,500/month at $75/hr fully-loaded, plus
late-payment penalties averaging $3,000/month. The agent auto-resolves
routine exceptions and drafts resolution proposals for complex ones,
targeting 70% auto-resolution. Conservative ROI: ($12,500 + $3,000) × 70% ×
12 = **$130,200/year** against ~$35,000 build + run cost. Sponsor: CFO.

---

## 2. Workflow Map (maps to S3)

**[Prompt]** Map the as-is process step by step. Mark: which steps the agent
owns, which stay human, and where the handoffs are. List the top 5
exceptions (the 20% that breaks you) and how each is handled.

**Worked example:** Steps: ingest invoice → match PO → validate tax →
route for approval → post to ERP. Agent owns ingest/match/validate and
drafts approval requests; humans approve anything >$5,000 or with tax
ambiguity. Exceptions: PO missing (request from buyer), duplicate invoice
(flag + hold), tax mismatch (draft correction for reviewer), currency
variance >2% (escalate), vendor not in master data (create draft vendor
record for approval).

---

## 3. Agent Architecture (maps to S2)

**[Prompt]** Which architecture (reactive / planning / reflective) and why?
Describe the four components: reasoning engine (model + prompting strategy),
memory (what persists across turns and sessions), tools (list them),
guardrails (layered: input, tool, output).

**Worked example:** Planning architecture (multi-step matching workflow).
Reasoning: GPT-4o-class model, structured planning prompt with explicit
"verify before posting" step. Memory: session memory for the invoice batch;
long-term memory of vendor-specific matching rules. Tools: `get_invoice`,
`match_po`, `validate_tax`, `draft_approval_request`, `post_to_erp`
(write-gated). Guardrails: input PII redaction, tool-level amount limits,
output schema validation, human approval gate before ERP posting.

---

## 4. RAG & Memory Design (maps to S4)

**[Prompt]** What knowledge does the agent need? Sources, chunking strategy,
permission model (who sees what), freshness requirements, and what the
agent must remember across sessions.

**Worked example:** Sources: AP policy docs, vendor master data, tax tables
by jurisdiction. Chunking: 500-char windows on policy docs; structured rows
for vendor/tax data. Permissions: AP clerks see all vendors; regional
leads see only their region's data. Freshness: tax tables refreshed monthly
(stale >45 days blocks answers). Memory: per-vendor matching preferences
learned from past resolutions, reviewed quarterly.

---

## 5. Tool Contracts (maps to S5)

**[Prompt]** For each tool: function schema, input validation, authorization
scope, rate limits, confirmation requirements. Which tools are read vs
write? Attach or link your contract definitions.

**Worked example:** 5 tools (see `demo-tool-contract/` for the pattern).
`post_to_erp` is the only unconditional-write: requires `confirmed=true`
plus human approval for amounts >$5,000. `match_po` read-only, scoped to
requester's region. All tools rate-limited (100/min) and audit-logged.

---

## 6. Multi-Agent Design — if applicable (maps to S6)

**[Prompt]** Single agent or multi-agent? If multi: orchestration pattern
(pipeline / orchestrator / debate / swarm), specialist roles, communication
protocol, and failure modes.

**Worked example:** Single agent suffices — the workflow is linear. (If your
process has parallel specialist work, e.g. legal + finance review, design
the orchestrator pattern here.)

---

## 7. Eval Plan (maps to S7)

**[Prompt]** Golden dataset: how many tasks, covering what? Scorers
(exact-match, schema, safety, judge). Target pass rate. How evals run in
CI/CD (per-commit / nightly / pre-release).

**Worked example:** 60-task golden set: 30 routine matches, 15 exceptions,
10 adversarial (duplicate invoices, poisoned vendor names), 5 safety traps
(agent must NOT post without approval). Scorers: exact amount-match,
schema validation, safety (no unapproved ERP post). Target: 95% routine,
90% exceptions, 100% safety. CI: fast 20-task subset per commit, full set
nightly, gate on 90%+ to promote.

---

## 8. Cost Model (maps to S8)

**[Prompt]** Cost breakdown: model inference (tokens × price), retrieval,
tool calls, human review time. Monthly projection at expected volume.
Optimization levers: routing (small model for classification), caching,
prompt efficiency. Build-vs-buy note.

**Worked example:** 400 exceptions/month × ~8k tokens × $2.50/1M ≈
$8/month inference. Retrieval + ERP calls negligible. Human review: 30% of
cases × 10 min × $75/hr = $1,500/month. Total ~$1,510/month vs $15,500
manual cost. Routing: Haiku-class model for initial classification cuts
inference 60%.

---

## 9. Governance & Security (maps to S9)

**[Prompt]** Who owns what the agent does (accountability)? Threat model:
prompt injection, data exfiltration, tool misuse — mitigations. Compliance
requirements (SOX, GDPR, etc.). Audit trail design. Data privacy: PII
handling, retention, deletion.

**Worked example:** Owner: AP manager (accountable), platform team
(operational). Threats: vendor-name injection in invoice notes → input
sanitization + allowlist; exfiltration via approval drafts → drafts never
leave the ERP boundary. SOX: every ERP post has immutable audit trail
(who/what/when/approval). PII: vendor bank details masked in logs,
retained 7 years per policy.

---

## 10. UX & Rollout Plan (maps to S10–S11)

**[Prompt]** Human-agent interface: where do users meet the agent, how are
its actions presented, how is trust calibrated (confidence display, undo)?
Approval flows. Change management. Phased rollout: pilot scope, success
criteria, hardening checklist, monitoring, incident response, scale plan.

**Worked example:** UX: exception queue in the existing AP dashboard; each
item shows agent's proposed resolution + confidence + "one-click approve /
edit / reject". Trust: first 2 weeks every action requires approval
(calibration period), then auto-approve >95%-confidence routine matches.
Pilot: one region, 100 invoices, success = 65%+ auto-resolution with zero
unapproved posts. Hardening: eval gate in CI, PagerDuty on error-rate
spike, rollback to manual queue in one click. Scale: region by region after
pilot sign-off.

---

## Self-grade

| Part | Score (0–2) | Notes |
|------|-------------|-------|
| 1. Business case | | |
| 2. Workflow | | |
| 3. Architecture | | |
| 4. RAG & memory | | |
| 5. Tool contracts | | |
| 6. Multi-agent | | |
| 7. Eval plan | | |
| 8. Cost model | | |
| 9. Governance | | |
| 10. UX & rollout | | |
| **Total** | **/20** | Pass mark: 14/20 |
