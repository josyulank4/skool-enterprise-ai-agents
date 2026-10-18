---
title: VPN Access Runbook
department: IT
classification: internal
updated: 2026-09-12
---

# VPN Access Runbook

## Requesting VPN access
Employees request VPN access through the IT service portal. Approval requires
manager sign-off and completion of the security awareness training.

## Connection steps
1. Install the company VPN client from the software catalog.
2. Authenticate with SSO plus hardware-key MFA.
3. Select the gateway closest to your region: US-East, EU-Central, or APAC-South.

## Troubleshooting
If the tunnel drops repeatedly, switch gateways and check that UDP port 4500 is
open on your local firewall. Contact the network operations team if packet loss
exceeds 5% for more than ten minutes.

## Deprovisioning
VPN access is revoked automatically within 24 hours of employment termination.
Contractors lose access on the contract end date unless extended in writing.
