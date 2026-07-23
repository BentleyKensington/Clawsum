# CEO Overwatch — report coverage & phase task board

**Source:** Gerald’s July 23, 2026 execution report (Hermes/JARVIS + Paperclip + OpenClaw + channels + archive).  
**Stack strategy:** Evolve the existing `/docker/clawsum` platform; do **not** greenfield a parallel Next.js/FastAPI monorepo.

---

## Was the report considered?

**Yes.** Architecture was reconciled against the pre-fork platform and used to drive:

| Report principle | Clawsum decision |
|------------------|------------------|
| Hermes talks · Paperclip manages · OpenClaw acts | Locked — [CEO-COCKPIT.md](./CEO-COCKPIT.md), [HERMES-POLICY.md](./HERMES-POLICY.md) |
| Hermes ≠ credential super-agent | Locked — route via Paperclip + cell-scoped agents |
| Business cells isolated | Seeded registry + GHL Approach A; per-gateway later |
| Gerald approves (tier 0–3) | [PAPERCLIP-OVERWATCH.md](./PAPERCLIP-OVERWATCH.md) + `ops.approvals` |
| ChatGPT archive ≠ dump into Hermes | Designed; **not built yet** (Phase 6) |
| Browser CEO cockpit | Hermes UI + cockpit plugin (Phase 1–2 of report UI path) |
| Discord | Deferred (Telegram live first) |
| Voice | Deferred |
| Greenfield `apps/web` | Deferred until Hermes+Paperclip loop is proven |

---

## Coverage matrix (report § → status)

| Report area | Status | Artifact / next |
|-------------|--------|-----------------|
| §1–2 Control model | ✅ Adopted | Docs + resume policy |
| §3.1 Hermes/JARVIS face | 🔄 In progress | Hermes UI + `hermes-cockpit` |
| §3.2 Paperclip overwatch | 🔄 Starter | Schema, seed, approval scripts; wire Hermes→Paperclip next |
| §3.3 OpenClaw execution | ✅ Partial | Live agents; approval-gated exec still thin |
| §3.4 Browser UI (12 tabs) | 🔄 MVP | Brief / Approvals / Health + Chat; rest later |
| §3.5 ChatGPT archive | ⬜ Not started | Phase 6 |
| §4 Business cells | 🔄 Profiles seeded | Isolation / per-gateway later |
| §5.1 Discord | ⬜ Deferred | After Telegram smoke + Hermes stable |
| §5.2 Telegram | ✅ Exists | Daily brief 7am CST fix; JARVIS DM later |
| §5.4 Voice | ⬜ Deferred | Speech scaffold exists |
| §6 UI Phase 1–2 | 🔄 | Hermes + theme/plugin |
| §6 UI Phase 3 custom console | ⬜ Deferred | |
| §7 Archive schema/pipeline | ⬜ Not started | `13-chatgpt-archive.sql` later |
| §8 Approval tiers | 🔄 Schema + scripts | UI approve buttons next |
| §9 Agent model | ✅ Partial | Specialists live; cell agents evolve |
| §10 Workflows (brief/command/approval) | 🔄 Partial | Daily report live; full cell brief later |
| §11 Security | ✅ Partial | Traefik wall; VPN/Authelia later |
| §12 Full API wrappers | ⬜ Stub via plugin | Expand as needed |
| §13 Folder structure `apps/` | ❌ Rejected for now | Keep `deploy/` template |
| §14 Phases 1–7 | See board below | |
| §15 Seed businesses | ✅ | `seed-business-cells.py` |
| §16–18 Prompts/policies | 🔄 Docs | Install into Hermes SOUL on VPS |
| §19 Greenfield IDE sequence | ❌ Adapted | Overlay existing stack instead |

---

## Phase task board (execute in order)

### P0 — Deploy now (this sprint)

- [x] CRON_TZ fix for 7:00 America/Chicago daily Telegram
- [x] Overwatch SQL + seed cells + approval CLI
- [x] Hermes cockpit theme/plugin (logo in `examples/hermes-cockpit/assets`)
- [x] Sync repo → VPS `/docker/clawsum` (2026-07-23)
- [x] Apply `12-overwatch.sql` + seed (8 cells)
- [x] Reinstall daily/reminders/obsidian crons (`CRON_TZ=America/Chicago`)
- [x] `install-hermes-dashboard` + `install-hermes-cockpit` + start dashboard (`127.0.0.1:9119`)
- [ ] Ops portal Traefik includes `hermes.*` (DNS as available)
- [ ] Resume policy: CLA-41 before heartbeats ([RESUME-POLICY.md](./RESUME-POLICY.md))

### P1 — Hermes face + Paperclip loop

- [ ] Install JARVIS routing prompt into Hermes SOUL (§16)
- [ ] Hermes/cockpit: create Paperclip task from Brief action
- [ ] Cockpit Approvals: approve/reject buttons → `overwatch-decide-approval.py` / API
- [ ] Telegram: optional JARVIS DM binding (mention policy)
- [ ] Grafana embed URL + `allow_embedding` if iframe blocked

### P2 — OpenClaw gated execution

- [ ] Read-only health tool path logged to `ops.audit_logs`
- [ ] Tier-2 actions blocked until approval row = approved
- [ ] One cell query smoke (e.g. WNN/GHL read-only)

### P3 — Business cell hardening

- [ ] Per-cell dashboard cards in cockpit
- [ ] Map Paperclip agents ↔ `ops.overwatch_agents`
- [ ] Document Approach A vs B gateways (WNN-only gateway later)

### P4 — ChatGPT history archive (§7 / Phase 6)

- [ ] `13-chatgpt-archive.sql` (imports, conversations, chunks, facts)
- [ ] MinIO raw export store
- [ ] Parse + embed + sensitivity scan
- [ ] Hermes archive-query tool (Paperclip-governed)
- [ ] Memory promotion workflow

### P5 — Channels & brief

- [ ] Discord HQ layout (§5.1) — one free-respond bot per channel
- [ ] Cross-cell CEO Daily Brief (Paperclip scheduled)
- [ ] Voice wake → Hermes (deferred)

### P6 — Optional custom console

- [ ] Only if Hermes plugin model hits a wall — Next.js cockpit shell

---

## Explicit non-goals (until P0–P2 done)

- Replacing Paperclip with a custom task DB  
- Giving Hermes all PITs / banking tools  
- Production Discord rollout  
- Dumping ChatGPT export into Hermes MEMORY.md  
- Multi-VPS clones before template gate  

---

## Related

- [CEO-COCKPIT.md](./CEO-COCKPIT.md)  
- [PAPERCLIP-OVERWATCH.md](./PAPERCLIP-OVERWATCH.md)  
- [RESUME-POLICY.md](./RESUME-POLICY.md)  
- [../examples/hermes-cockpit/README.md](../examples/hermes-cockpit/README.md)  
- [STATUS-REPORT-2026-07-08.md](./STATUS-REPORT-2026-07-08.md)  
