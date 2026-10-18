---
title: SEV-2 Incident Runbook
department: Engineering
classification: internal
updated: 2026-10-01
---

# SEV-2 Incident Runbook

## Declaration
A SEV-2 is declared when a customer-facing service degrades for more than 15
minutes but core functionality remains available.

## Roles
The incident commander owns coordination. The communications lead posts status
updates every 30 minutes. The responder team investigates root cause.

## Response steps
1. Acknowledge the page within 5 minutes.
2. Open the incident channel and start the timeline.
3. Roll back the most recent deployment if it correlates with the degradation.
4. If rollback does not help, fail over to the secondary region.

## Post-incident
A blameless postmortem is due within 5 business days. Action items must have
owners and due dates before the review closes.
