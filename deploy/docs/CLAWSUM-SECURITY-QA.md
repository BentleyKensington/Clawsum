# Clawsum security Q&A

**As of:** 2026-08-06  
**Source document:** Origin Platform V1 Product & Technical Specification (uploaded DOCX) + Origin `SPEC-REVIEW.md` kickoff questions  
**Scope of this file:** Answers for **Clawsum** (ops platform), **not** Origin commerce product decisions  

Related: [AUTHORITY.md](../skills/AUTHORITY.md), [CREDENTIALS-EXCLUSION.md](./CREDENTIALS-EXCLUSION.md), pentest agent `pentest`

---

## How to read this

| Column | Meaning |
|--------|---------|
| **Q** | Question from the Origin secure-system kickoff (adapted where Clawsum differs) |
| **Applies?** | Whether it maps to Clawsum today |
| **Clawsum answer** | Current state / target control |

Origin-specific commerce answers live under `workspace-admin/projects/origin/docs/SPEC-REVIEW.md` and are **out of scope** here except as the question source.

---

## A. Ownership & delivery (platform)

### A1. Show architecture, data-flow, dependencies, delivery plan
**Applies?** Yes  

**Clawsum answer:** Three-plane ops stack: **Traefik + Authelia** (edge) → **Hermes/Boss UI** (`boss.clawsum.com` → Hermes `:9119`) + **Paperclip** (`paperclip.clawsum.com` / loopback `:3100`) → **OpenClaw gateway** (agents) → **Postgres / MinIO / Obsidian / Grafana**. Agent work is Paperclip-assigned; public Paperclip API is Authelia-gated; agents use `host.docker.internal:3102` proxy. Docs: DOMAIN-MAP, BOSS-OPS-PORTAL, MEDIA-PRODUCTION-STUDIO, STATUS-REPORT-2026-08-06.

### A2. Custom vs managed; vendor exit plan
**Applies?** Yes  

**Clawsum answer:** **Custom:** OpenClaw agent roster, Paperclip wiring, ops Postgres schemas, Hermes cockpit plugins, GHL cell overlays, media pipeline, chat outage replay. **Managed:** VPS host, Docker, Traefik/LE, Discord/Telegram, Codex/OpenAI OAuth, optional MinIO, Grafana/Prometheus. **Exit:** keep truth in Postgres + Obsidian + git deploy template; isolate vendors behind scripts/adapters; no product state only in SaaS UIs.

### A3. Tenancy ownership (repos, cloud, DNS, email, AI, monitoring)
**Applies?** Partially (single-tenant Boss ops)  

**Clawsum answer:** Clawsum VPS + `clawsum.com` DNS (Porkbun), Authelia users, Paperclip company “Clawsum”, OpenClaw workspaces. Gerald is Boss; agents get least-privilege tool policies. Personal vs business cells isolated (`personal-admin` vs GHL cells). Asset inventory should stay in Obsidian + `.env` prefixes (values never committed).

### A4. Milestone payments / warranty / on-call
**Applies?** No (internal platform)  

**Clawsum answer:** N/A commercially. Ops equivalent: Paperclip issues + RESUME-POLICY before heartbeats; Tier 2/3 for prod apply / credential rotate.

### A5. PR review, tests, preview, rollback for every change?
**Applies?** Yes (target)  

**Clawsum answer:** **Target yes** for production-bound deploy. Today: repo + VPS scripts; not all changes go through CI preview. Rollback = compose/config restore + documented scripts. Pentest agent flags missing review/rollback notes on Tier 2 changes.

---

## B. Security & reliability (primary set)

### B1. Threat model for this system
**Applies?** Yes  

**Clawsum answer — top threats:**
1. Authelia / Traefik misconfig → public Boss/Paperclip/OpenClaw exposure  
2. Agent using **public** Paperclip URL → Authelia 302 / stuck closeouts / confused deputy  
3. `configure-openclaw` or similar **disabling Discord/Telegram** → silent chat outage  
4. Credential leakage into chat, SOUL, MEMORY, Discord/Telegram  
5. Cross-cell GHL PIT / data bleed  
6. Gateway `exec` abuse (coding/media) without Tier gates  
7. Insider/session compromise on Boss UI  
8. MinIO / Postgres backup gaps; Hermes dashboard down → Boss 502  
9. Prompt injection via Discord/Telegram/Gmail into agents  
10. Referral-style fraud N/A; **affiliate of risk** = rogue agent tool use / spoofed notify  

Pentest agent owns living threat register + event notify.

### B2. Secrets storage/rotation; who can access prod; MFA; step-up admin
**Applies?** Yes  

**Clawsum answer:** Secrets in VPS `/docker/clawsum/.env` (+ Authelia users DB); **not** in git (CREDENTIALS-EXCLUSION). Production SSH = named operator. Authelia fronts Boss/Paperclip/Grafana/OpenClaw UI. **Gaps:** no universal hardware MFA story documented for all staff paths; step-up for “lot release” N/A — Clawsum step-up equivalents are **Tier 2 `ops.approvals` + Gerald** for publish/deploy/send and **Tier 3** for wipe/rotate. Rotate tokens if ever printed in logs/chat.

### B3. Payment tokenization / PCI scope
**Applies?** No for core Clawsum  

**Clawsum answer:** Clawsum is not a card processor. Any future paid media/API spend uses vendor APIs (keys as prefixes); no PAN storage. Origin PCI answers stay on Origin.

### B4. Uploads scanned, metadata stripped, encrypted, ACL, backup deletion, V1 blocks
**Applies?** Partially  

**Clawsum answer:** Inbound media/chat attachments land under OpenClaw `media/inbound` and MinIO when wired. **Current:** trust boundary is Authelia + private MinIO; malware scan / EXIF strip not fully productized. ChatGPT archive is governed import (no wholesale Hermes dump). **Policy:** never put secrets in uploads mirrored to chat; MinIO deletes = Tier 2+; surgical backup delete not promised — retention windows TBD. Pentest reviews upload paths and flags world-readable buckets.

### B5. RPO/RTO, backups, restore drills, log retention, WAF/rate limits, DDoS, incident runbooks
**Applies?** Yes  

**Clawsum answer (current / target):**
| Control | Current | Target |
|---------|---------|--------|
| RPO | Best-effort VPS + `backup-platform.sh` / MinIO | ≤1h critical DB |
| RTO | Manual compose restore | ≤4h documented |
| Backups | Scripts exist; cadence uneven | Nightly + PITR where available |
| Restore test | Ad hoc | Quarterly |
| Logs | Docker + Grafana/Prometheus | 90d hot app + longer audit |
| Edge | Traefik + Authelia | Add explicit rate limits / WAF notes |
| Runbooks | Admin-Runbooks, STATUS reports | Expand: auth outage, gateway chat outage, Paperclip proxy, Hermes :9119, credential compromise |

### B6. Eligibility / policy checks at multiple points
**Applies?** Yes (authority tiers, not SKU lots)  

**Clawsum answer:** Executable policy = **AUTHORITY risk tiers + cell isolation + skill credential prefixes + Paperclip assignee**. Recheck at: skill start checklist, Paperclip assignment, gateway tool allow/deny, Authelia at edge. Fail closed for Tier 2/3 without approval.

### B7. Immutable allocation / append-only ledger
**Applies?** Partially  

**Clawsum answer:** Sacred-ish records: `ops.audit_logs`, Paperclip issue history/work-products, ChatGPT archive tables, media object hashes (when fully wired). Not a commerce lot ledger. Pentest verifies audit coverage on high-risk actions.

### B8. Referral fraud / self-referral / coupon leakage
**Applies?** No  

**Clawsum answer:** N/A. Analog: prevent **self-approval** bypass (agents must not decide Tier 2/3 for themselves); notify dual-write without secret leakage.

### B9. AI retrieval grounded, citations, high-risk refusals, auditable outputs
**Applies?** Yes  

**Clawsum answer:** Hermes/Admin must prefer Paperclip + ops DB + approved docs; ChatGPT archive promote skips `scope=personal`; no secret dumps. High-risk (wipe, rotate, client send, publish) → refuse autonomous. Show-work narration uses **credential prefixes only**. Gap: not every model output is hashed/replayable yet — pentest tracks that as finding.

### B10. Moderation / classifier fail-closed
**Applies?** Partially (ops, not community product)  

**Clawsum answer:** Community product N/A. Ops analog: if Discord/Telegram/plugins disabled or Hermes down → **detect + notify + replay**; do not silently drop Boss messages. Authelia fail → deny public access (closed).

### B11. Analytics without leaking sensitive data
**Applies?** Yes  

**Clawsum answer:** Grafana/Prometheus metrics are low-cardinality ops signals. Do **not** ship prompt bodies, GHL PII, or tokens into metrics/chat. Daily reports summarize counts/status only.

---

## C. Best-practice requirements (Clawsum checklist)

Extracted as **requirements** the pentest agent enforces/reports:

1. **Edge auth** on all Boss surfaces (Boss, Paperclip UI, Grafana, OpenClaw Control UI).  
2. **Agents never call Authelia-fronted APIs** for machine closeout — use loopback/`3102` proxy.  
3. **Secrets:** prefixes in docs/chat; values only in vault/`.env`; rotate on exposure.  
4. **Cell isolation** for GHL and personal vs business.  
5. **Tier gates** for send/publish/deploy/wipe.  
6. **Chat channel health** watched; outage → replay Discord history; notify Boss.  
7. **Hermes dashboard keepalive** (`:9119`) for Boss UI.  
8. **Audit** high-risk actions; no silent config disable of Discord/Telegram.  
9. **Backups + restore evidence** for Postgres/critical volumes.  
10. **Upload/MinIO** private; no public anonymous write.  
11. **Notify** on new critical/high findings and security events (Discord `#boss-alerts` / Telegram admin dual-write via `clawsum_notify`).  
12. **Pentest agent** may scan and report; **may not** exploit production or rotate credentials without Tier 2/3.

---

## D. Questions that do **not** apply to Clawsum (leave to Origin)

- Processor underwriting / custom checkout vs hosted fields for regulated goods  
- Lot state machine / COA public pages / recall commerce flows  
- Affiliate commission ledger / self-referral commerce fraud  
- Community pre-moderation product UX  
- Age-gating / regulated-product disclosures as storefront law  
- Milestone payment schedule to an external build vendor for Origin V1  

Those remain in Origin `SPEC-REVIEW.md` / Origin project docs.

---

## E. Open gaps (track as pentest findings)

| ID | Gap | Severity (initial) |
|----|-----|--------------------|
| C-SEC-01 | MFA/step-up story incomplete for all admin paths | Medium |
| C-SEC-02 | Upload malware-scan / metadata strip not productized | Medium |
| C-SEC-03 | RPO/RTO + quarterly restore drill not evidenced | High |
| C-SEC-04 | Explicit WAF/API rate-limit policy not documented | Medium |
| C-SEC-05 | Model output audit hash/replay incomplete | Low |
| C-SEC-06 | Telegram bot token may need rotation if ever logged | Medium |
| C-SEC-07 | Heartbeats still gated — good for safety; document when re-enabled | Info |

---

## F. Pentest agent contract

- **OpenClaw id:** `pentest`  
- **Paperclip name:** Clawsum Pentest  
- **Cell:** `clawsum-platform` (+ read-only review of other cells’ **public** config surfaces)  
- **Auto tier:** 0–1 report/notify; **no** offensive exploit payloads; **no** credential rotate (Tier 3 human)  
- **Skills:** `pentest-threat-model`, `pentest-surface-scan`, `pentest-report`, `pentest-notify`  
- **Training corpus:** this file + AUTHORITY + CREDENTIALS-EXCLUSION + Origin SPEC security questions (as checklist, not Origin answers)
