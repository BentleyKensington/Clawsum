# Clawsum Company hub — adapt from CEOroof patterns (non-roofing)

**Purpose:** Port the *platform / CEO UX* patterns proven on CEOroof onto Clawsum — without roofing-only product features.  
**Audience:** Operator upgrading the Clawsum VPS (`76.13.97.82` / `boss.clawsum.com`).  
**Owner:** Gerald  
**Source of truth:** `C:\APPS\Projects\Clawsum` → `deploy/` + this doc  
**Excluded:** Roofing departments, hail scripts, JobNimbus, roof pipeline KPIs, CEOroof brand/assets, Right Way margin floors, weather.ceoroof, estimation/PostGIS, Colton welcome pack.

**Deferred:** BeHive research engine — revisit ~2026-08-02 (snoozed 5 days from 2026-07-28).

Use as a checklist. Prefer adapting Clawsum paths in-place over blind rsync from CEOroof. Do **not** copy secrets between cells/VPSes.

---

## 0. Quick outcomes (what Clawsum should end up with)

| Area | Result |
|------|--------|
| **SSO entry** | One Authelia login; CEO home at `https://boss.clawsum.com/` → Company **Start** (or `/home`) |
| **Start home** | Clawsum brand + **ops KPI panel** (approvals, inbox needs_boss, Paperclip queue, cells, uptime) |
| **Dash** | Same KPIs, fuller workspace (period toggle optional) |
| **Chat** | Hermes/JARVIS; skin welcome before cursor; sticky Chat dock on every Company view |
| **Sidebar** | One priority list (no Start/Company/Dash duplicates) |
| **Skills** | Primary Clawsum skills always visible; rest under **Toolbox** |
| **Hermes persona** | Proactive **Next** guidance; session startup = last session + deltas + full pending table |
| **Company pack** | Shared `COMPANY / VALUES / APPROVALS / …` for all agents (Clawsum platform pack) |
| **Agents / skills** | Existing 10 core agents + authority matrix; Skill map heatmap already live |
| **Monitoring** | Grafana Operations strip embeddable in Company → Ops |
| **Owner pack** | Short Gerald/Clawsum ops intro (not CEOroof PDF) |

---

## 1. Suggested work order on Clawsum VPS

Assume layout: `/docker/clawsum/` (compose, OpenClaw, Hermes plugins, scripts, personas).

1. Keep current Authelia / Traefik / domains (already cut over — see [DOMAIN-MAP.md](./DOMAIN-MAP.md)).
2. Extend Hermes cockpit into a **Company hub** (Start / Dash / Chat dock / sidebar) — adapt CEOroof nav patterns into `examples/hermes-cockpit`.
3. Harden Hermes persona: `LAST_SESSION.md`, ranked pending in `MEMORY.md`, every-reply **Next**, W9 wrap-up.
4. Seed a **shared company pack** into all agent workspaces + Hermes (not a roofing vertical pack).
5. Skills UI: mark primary vs toolbox in authority / panels.
6. Grafana embed flags + Ops tile pointing at `clawsum-operations`.
7. Smoke §6. Leave Connect / OAuth / CRM mirrors as owner steps.

---

## 2. Files / trees (Clawsum paths)

### 2.1 Hermes Company hub (Start / Dash / Chat dock)

**Today:** Home `/home`, Agents, Skill map, Inbox via:

```
deploy/examples/hermes-cockpit/plugin/
  clawsum-cockpit/     # Home + API + crest
  clawsum-agents/      # Team / cell map
  clawsum-skills/      # Authority heatmap
  clawsum-inbox/
  _shared/clawsum-panels.js
```

**Adapt (from CEOroof nav idea — rewrite for Clawsum, do not copy roofing KPIs):**

| Feature | Clawsum target |
|---------|----------------|
| Default home | Force `/` → `/home` or `/company?view=start` (beat React router; `?noredirect=1` escape) |
| Start KPI panel | Ops counters from cockpit APIs + Prometheus textfile (not roof pipeline stages) |
| Chat dock | Sticky dock on Home / Agents / Skills / Inbox with quick prompts |
| Sidebar | Single ordered list (see §5.4) |
| Style | Existing Clawsum teal technicolor in `dist/style.css` |

Install: `bash scripts/install-clawsum-sidebar-plugins.sh` (+ extend when hub ships).

Docs to update: [CEO-COCKPIT.md](./CEO-COCKPIT.md)

### 2.2 Hermes persona + session handoff

**Today:** `deploy/examples/hermes-cockpit/SOUL.md` (proactive standing orders).

**Add / adapt:**

```
deploy/examples/hermes-cockpit/   (or agents/hermes/ when split)
  SOUL.md          # Every-reply Next contract + startup brief shape
  BOOT.md          # Session Startup Brief
  USER.md          # Gerald
  MEMORY.md        # Ranked pending queue (Paperclip + inbox + approvals)
  LAST_SESSION.md  # Handoff rewritten at wrap-up
  WORKFLOWS.md     # W0 startup, W9 EOD handoff
  APPROVALS.md
  …
```

Skin welcome (already present):

```
deploy/examples/hermes-cockpit/skins/clawsum.yaml   # branding.welcome
```

### 2.3 Shared company persona pack (Clawsum — not Right Way)

Create:

```
deploy/personas/clawsum/
  README.md COMPANY.md VALUES.md APPROVALS.md
  COMMUNICATION.md MEMORY_POLICY.md
  DECISIONS.md ESCALATION.md SECURITY.md USER.md
```

Seed into OpenClaw workspaces + Hermes via extension of `scripts/seed-persona-os.sh` (or new `seed-clawsum-company-pack.sh`).

Keep cell overlays (`templates/ghl/`, RE, etc.) as **overrides**, not replacements of the company pack.

### 2.4 Agents + skill map (already Clawsum)

Do **not** import CEOroof roofing departments.

| Keep | Path |
|------|------|
| 10 core agents | [AUTHORITY.md](../skills/AUTHORITY.md), `authority.json` |
| ~33 skills | [CATALOG.md](../skills/CATALOG.md) |
| Cell map + heatmap UI | `plugin/_shared/clawsum-panels.js` |
| Persona seed | `scripts/seed-persona-os.sh` |
| GHL overlays (when needed) | `templates/ghl/`, [GHL-MULTI-ACCOUNT-PLAN.md](./GHL-MULTI-ACCOUNT-PLAN.md) |

Optional later (non-roofing): Security / Finance agents when workload justifies — still not CEOroof dept clones.

### 2.5 Auth / users / Paperclip branding

```
deploy/scripts/setup-authelia.sh
deploy/docs/DOMAIN-MAP.md
deploy/docs/BOSS-OPS-PORTAL.md
```

Add if missing (adapt from CEOroof scripts, rename):

- `add-authelia-user.sh` with `USER_GROUPS`
- Paperclip dark/brand patch (Clawsum naming)
- Sidebar “show all agents” patch if Paperclip truncates

Secrets: recreate per VPS — never copy `ops-portal-auth.json` / `.env`.

### 2.6 Monitoring / Grafana embed

**Already live:**

```
deploy/grafana/provisioning/dashboards/json/clawsum-health.json
deploy/grafana/provisioning/dashboards/json/clawsum-operations.json
deploy/scripts/clawsum-ops-metrics.py
deploy/scripts/verify-monitoring.sh
```

**Still adapt:**

- Compose Grafana: `GF_SECURITY_ALLOW_EMBEDDING=true`, `GF_SECURITY_COOKIE_SAMESITE=lax`
- Company → Ops iframe → `https://grafana.clawsum.com/d/clawsum-operations?...&kiosk`
- [BOSS-UI-AND-MONITORING.md](./BOSS-UI-AND-MONITORING.md) note on embed + Authelia cookie

### 2.7 Owner welcome pack (Clawsum)

Short Gerald-facing note only:

- How to land on Start
- Authelia email
- Surfaces: Boss / Paperclip / OpenClaw / Grafana / Connect
- What still needs Connect (Gmail scopes, GHL PITs, etc.)

Skip CEOroof PDF / Colton email / roofing cover art.

---

## 3. Install commands (Clawsum VPS)

```bash
# 1) Sidebar plugins + cockpit (current)
bash /docker/clawsum/scripts/install-clawsum-sidebar-plugins.sh

# 2) When Company hub ships — install nav overlay
# bash /docker/clawsum/scripts/install-clawsum-company-hub.sh

# 3) Hermes persona + LAST_SESSION + company pack
# bash /docker/clawsum/scripts/deploy-hermes-persona.sh
# bash /docker/clawsum/scripts/seed-clawsum-company-pack.sh

# 4) Personas (existing)
bash /docker/clawsum/scripts/seed-persona-os.sh

# 5) Monitoring refresh
bash /docker/clawsum/scripts/install-monitoring.sh
bash /docker/clawsum/scripts/verify-monitoring.sh

# 6) Skin
cp /docker/clawsum/examples/hermes-cockpit/skins/clawsum.yaml \
   /docker/clawsum/paperclip-data/.hermes/skins/clawsum.yaml
```

Hard-refresh: `https://boss.clawsum.com/` (and `/home`).

---

## 4. Per-cell / per-VPS config (do not copy blindly)

| Item | Clawsum action |
|------|----------------|
| Domain | Already `*.clawsum.com` — only rewrite if spinning a *second* Clawsum-like cell |
| Authelia master | Gerald email in `admins,boss`; keep break-glass `boss` |
| Grafana URLs | `grafana.clawsum.com` / `clawsum-operations` |
| Connect | Owner wires Gmail / GHL / etc. — hub stays honest until live |
| Brand voice | Edit `personas/clawsum/COMMUNICATION.md`, re-seed |
| `LAST_SESSION.md` | Seed Clawsum-specific handoff; Hermes rewrites on wrap-up |
| `MEMORY.md` pending | Paperclip + inbox needs_boss + approvals — *this* cell |
| Paperclip company id | Confirm in `.env` / wire scripts |

### Hub URL constants (search/replace only on domain fork)

- `boss.clawsum.com`
- `paperclip.clawsum.com`
- `grafana.clawsum.com`
- `openclaw.clawsum.com`
- `auth.clawsum.com`
- `login.clawsum.com`
- `connect.clawsum.com`
- `clawsum.com`

---

## 5. Feature detail (platform only)

### 5.1 Start = default home (not Chat)

- Force `/`, `/sessions`, … → Clawsum Start / Home.
- Escape: `?noredirect=1` or session flag.

### 5.2 Start KPI panel (ops — not roofing pipeline)

Suggested tiles (live data, demo only if API down):

| Tile | Source |
|------|--------|
| Approvals pending | `ops.approvals` / cockpit `/brief` |
| Inbox needs Boss | `ops.emails` review_status |
| Paperclip todo / in_progress / blocked | Paperclip API |
| Active business cells | `ops.businesses` |
| Gmail sync age | textfile / ops metrics |
| Service uptime 24h | Prometheus probes |
| Agents / skills counts | `authority.json` |

Period toggle optional: 24h · 7d · MTD.

**Do not** port CEOroof contact stages (Prospect → Install → Revenue) or squares / insurance mix.

### 5.3 Chat dock on every Company view

Sticky dock + quick prompts (“Brief me”, “Inbox triage”, “Pending approvals”) + “Open chat →”. Full chat remains `/chat` with skin welcome above the prompt.

### 5.4 Sidebar priority (single Clawsum list)

Suggested order:

1 Home · 2 Dash · 3 Chat · 4 Team · 5 Skills · 6 Inbox · 7 Ops · 8 Paperclip · 9 Connect · 10 OpenClaw · 11 Grafana · 12 Login hub  

Remove duplicate Company / long Agents dump from plugin extras.

### 5.5 Skills: primary + Toolbox

**Primary (always shown)** — examples:

- `ceo-daily-brief`, `overwatch-approvals`, `gmail-inbox-review`, `paperclip-task-routing`, `hermes-proactive-drive`, `research-brief`, `credential-hygiene`

**Toolbox (collapsed):** remaining catalog skills (GHL, RE, deploy, MinIO, etc.).

Encode in `authority.json` or panel constants — not a roofing skill map.

### 5.6 Hermes proactive / session boot

Every new session:

1. Last session summary (`LAST_SESSION.md` or “fresh start”)  
2. Changes since then  
3. Full pending-items table (ranked `MEMORY.md` / Paperclip + inbox + approvals)  
4. Risks  
5. **Next** (one action + exact say/do)

Every useful reply ends with **Next**. Wrap-up rewrites `LAST_SESSION.md`.

Align with existing SOUL standing orders (Paperclip truth, inbox analyses, archive drive, Tier 2+ escalate).

### 5.7 Company pack

Shared policy tree for all agents + Hermes. Approvals / security cannot be overridden by casual prompts. Cell packs (GHL, RE, personal-admin) inherit and narrow.

### 5.8 Paperclip UX

Dark theme, Clawsum branding, all agents visible in sidebar when patch scripts exist.

### 5.9 Monitoring

`clawsum-operations` + health dashboards; Company → Ops embeds Grafana; Authelia SSO cookie may need one Grafana visit first.

---

## 6. Smoke checklist

- [ ] Authelia login (Gerald)  
- [ ] `https://boss.clawsum.com/` lands on **Start / Home** (brand + ops KPI tiles)  
- [ ] Sidebar: one Clawsum list, priority order, no duplicates  
- [ ] Chat dock on Home / Team / Skills / Inbox  
- [ ] `/chat` welcome above prompt  
- [ ] New Hermes chat: pending table + recommended Next  
- [ ] Paperclip: branding + agents visible  
- [ ] Company → Ops: Grafana operations strip  
- [ ] Connect honest until owner wires integrations  
- [ ] `verify-monitoring.sh` → `MONITORING_OK`  

---

## 7. Explicitly still per-owner (not auto-complete)

- Connect: Gmail OAuth scopes, GHL PITs, other CRM/API wires  
- Cell-specific brand voice / approval thresholds  
- Heartbeats / RESUME-POLICY (CLA-41)  
- Channel go-live (Telegram groups, Discord later)  
- BeHive (snoozed)  
- Second VPS / second domain fork (use this doc + DOMAIN-MAP; still no roofing trees)

---

## 8. Related Clawsum docs

| Doc | Role |
|-----|------|
| [DOMAIN-MAP.md](./DOMAIN-MAP.md) | Hosts + Authelia |
| [CEO-COCKPIT.md](./CEO-COCKPIT.md) | Hermes-first shell |
| [CEO-OVERWATCH.md](./CEO-OVERWATCH.md) | Governance model |
| [AI-PERSONA-OS.md](./AI-PERSONA-OS.md) | Persona inheritance |
| [AUTHORITY.md](../skills/AUTHORITY.md) | Agents / tiers |
| [CATALOG.md](../skills/CATALOG.md) | Skills |
| [BOSS-UI-AND-MONITORING.md](./BOSS-UI-AND-MONITORING.md) | Grafana vs tasks |
| [HERMES-POLICY.md](./HERMES-POLICY.md) | Hermes boundaries |

---

## 9. Mapping cheat sheet (CEOroof → Clawsum)

| CEOroof | Clawsum |
|---------|---------|
| `boss.ceoroof.com` | `boss.clawsum.com` |
| `ceoroof-nav` plugin | Extend `clawsum-cockpit` (+ optional `clawsum-nav`) |
| Right Way persona | `personas/clawsum/` |
| 11 roofing depts | **Skip** — keep 10 core + cell overlays |
| Roofing KPI / JN | **Skip** — ops KPIs from Paperclip / inbox / probes |
| Colton welcome | Gerald ops note only |
| `grafana` CEO strip | `clawsum-operations` |
| `/docker/ceoroof` | `/docker/clawsum` |

---

## 10. Build priority (recommended)

1. **Session boot + Next** (persona files — high value, low surface risk)  
2. **Company pack** seed  
3. **Start KPIs + default home redirect**  
4. **Chat dock + sidebar priority**  
5. **Primary / Toolbox skills**  
6. **Grafana embed in Ops**  

---

*Adapted for Clawsum from CEOroof cross-VPS summary (2026-07-28), roofing-only items removed.*
