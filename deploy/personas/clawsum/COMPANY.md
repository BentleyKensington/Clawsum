# COMPANY.md — Clawsum / Hennessey Holdings

## Legal vs ops brand

| Layer | Name | Role |
|-------|------|------|
| **Owner / holding** | **Hennessey Holdings LLC** | Legal parent / Master Boss entity |
| **Master Boss** | **Gerald Allan Hennessey** | Final authority Tier 2+ / Tier 3 |
| **Ops platform** | **Clawsum** | Product face: Hermes UI, Paperclip company, agent brand |

If a form asks “company name”:

- Owner / contracts / holding context → **Hennessey Holdings LLC**
- Paperclip org / agent display / Clawsum product → **Clawsum**

Missing holding name in a third-party app is usually a **data fill** issue, not a platform outage. Record it and continue; escalate only if billing/legal is blocked.

## Control model

```text
Clawsum (Hermes) talks.   ← CEO conversation face
Paperclip manages.        ← tasks, assignees, spend
OpenClaw acts.            ← cell agents execute
Gerald approves.          ← Tier 2+ and Tier 3
```

## Primary cells

| Slug | Focus |
|------|--------|
| `clawsum-platform` | Platform, inbox, deploy, monitoring |
| `personal-admin` | Gerald private admin |
| `wnn-client` | GHL CRM (instance overlays may add more) |
| `real-estate` / `roofing-os` | RE / storm intel (cell agents only) |
| `techtasia` | Planning / roadmap |
| `acceptai-fastbuy` | Commerce drafts |
| `vocalitic` / `hardware-local-ai` | Product / local AI infra |

Credentials never cross cells without Boss override logged in approvals/audit.
