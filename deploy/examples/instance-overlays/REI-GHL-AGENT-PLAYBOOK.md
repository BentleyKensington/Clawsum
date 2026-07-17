# REI GHL agent playbook — shared learnings (MCO → AVE → WNN)

**Status:** Living document — distilled from MCO REI strategic audit rollout (2026)  
**Applies to:** `ghl-mco-rei`, `ghl-ave-rei`, `ghl-wnn-rei`  
**Platform reference:** `deploy/docs/GHL-AGENT-CAPABILITIES.md`

This document captures everything learned building and operating the first REI GHL agent (MCO) that **must be replicated** when standing up or operating AVE and WNN agents.

---

## 1. Architecture (non-negotiable)

| Principle | Rule |
|-----------|------|
| **One agent per GHL location** | Each account has its own OpenClaw agent id, workspace, PIT, MCP server, Postgres schema, Obsidian folder, Telegram binding |
| **No cross-account access** | Never query another location, another agent's schema, or the `realestate` database |
| **Read-first by default** | Tier A (audit/read) pre-approved; Tier B (writes/tags/SMS) requires Boss approval |
| **Sandbox is template only** | `ghl-template` has no CRM/Telegram — copy source for provisioning, not live work |

### Account map

| Slug | Agent id | Obsidian folder | Postgres schema |
|------|----------|-----------------|-----------------|
| `mco-rei` | `ghl-mco-rei` | `GHL/MCO-REI/` | `ghl.mco_rei_*` |
| `ave-rei` | `ghl-ave-rei` | `GHL/AVE-REI/` | `ghl.ave_rei_*` |
| `wnn-rei` | `ghl-wnn-rei` | `GHL/WNN-REI/` | `ghl.wnn_rei_*` |

Config source: `deploy/config/ghl-accounts.json`

---

## 2. Provisioning checklist (each new account)

Run on VPS after PIT + location ID are in `.env`:

```bash
python3 /docker/clawsum/scripts/provision-ghl-accounts.py --skip-paperclip --skip-postgres
python3 /docker/clawsum/scripts/verify-ghl-isolation.py
python3 /docker/clawsum/scripts/bind-ghl-telegram.py --slug {slug} --from-sessions
cd /docker/clawsum && docker compose restart openclaw-gateway
python3 /docker/clawsum/scripts/bind-ghl-telegram.py --status
```

Per account, confirm:

- [ ] Workspace seeded (`SOUL.md`, `AGENTS.md`, `TOOLS.md`, `WORKFLOWS.md`, `OBSIDIAN.md`)
- [ ] Tool deny list active: `search`, `grep`, `glob`, `browser`, `exec`
- [ ] MCP server bound to correct PIT + `locationId`
- [ ] Obsidian folders: `{ACCOUNT}/Audits/`, `{ACCOUNT}/Recommendations/`
- [ ] Telegram group bound (needles in `ghl-accounts.json` or explicit `telegram_group_id`)
- [ ] First strategic audit completes and writes `REENGAGE.md`

---

## 3. Telegram agent behavior (critical)

### What went wrong at MCO

- Agent tried **search/browser/exec** to find re-engage data → failed with separate `⚠️ tool failed` messages
- Agent claimed summary unavailable without reading the one file that exists

### Required behavior (all REI agents)

1. **Re-engage requests:** read `REENGAGE.md` at workspace root — **exact path, read tool only**
2. **Never** search, grep, glob, browse, or exec for re-engage
3. Reply with: viable/excluded counts, top 5–10 by priority, hook + suggested SMS each
4. Honor **Move on / landline** section — do not SMS those contacts
5. If read fails, report the exact path tried — do not guess

### File paths (workspace)

```
REENGAGE.md                          ← primary (refreshed every strategic audit)
notes/REENGAGE.md                    ← mirror
notes/LATEST-REENGAGE-SUMMARY.md     ← fallback
```

### File paths (Obsidian)

```
/home/node/obsidian/GHL/{ACCOUNT}/Recommendations/LATEST-REENGAGE-SUMMARY.md
/home/node/obsidian/GHL/{ACCOUNT}/Recommendations/YYYY-MM-DD-reengage-leads.md
/home/node/obsidian/GHL/{ACCOUNT}/Audits/YYYY-MM-DD-strategic-analysis.md
```

---

## 4. Strategic audit — the core REI workflow

Script: `deploy/scripts/ghl-strategic-audit.py`

```bash
# Standard run (recommended defaults: 400 contacts, 150 conversations)
python3 /docker/clawsum/scripts/ghl-strategic-audit.py --slug {slug} --use-llm

# Backfill landline tags in GHL (Tier B — Boss approval)
python3 /docker/clawsum/scripts/ghl-strategic-audit.py --slug {slug} --apply-landline-tags

# Read-only inventory
python3 /docker/clawsum/scripts/ghl-audit-readonly.py --slug {slug}
```

### Outputs (every run)

| Output | Location |
|--------|----------|
| Strategic analysis | `GHL/{ACCOUNT}/Audits/YYYY-MM-DD-strategic-analysis.md` |
| Re-engage list | `GHL/{ACCOUNT}/Recommendations/YYYY-MM-DD-reengage-leads.md` |
| CSV export | `GHL/{ACCOUNT}/Recommendations/YYYY-MM-DD-reengage-leads.csv` |
| Telegram summary | `GHL/{ACCOUNT}/Recommendations/LATEST-REENGAGE-SUMMARY.md` |
| Agent workspace | `workspace-{agent-id}/REENGAGE.md` |
| Postgres | `{schema}.audit_runs`, `reengage_leads`, `conversation_reviews` |

### Deep lookback

When viable leads **< 15**, audit automatically expands conversation scan up to **300 threads**. Do not rely on stale `lastActivity` alone — always use transcript review.

---

## 5. Re-engage criteria (what belongs on the list)

A contact is **viable for re-engage only when all three apply:**

1. **Bonafide interest** — direct seller motivation *or* serious referral with a sellable property
2. **Real follow-up gap** — inbound unanswered >48h, slow reply, or call/voicemail with no outbound
3. **Not already worked** — recent outbound SMS/call within 7 days counts as worked; slow outbound still counts as worked

### Always exclude

| Category | Why |
|----------|-----|
| Referral-only curiosity | "Considering referring" — not a motivated seller |
| Non-viable / tire kicker | Not interested, DNC, wrong number, no timeline |
| Already worked | Outbound sent + not a bonafide seller on transcript review |
| **Landline / SMS blocked** | Cannot receive SMS — not a missed SMS follow-up |
| **Outbound-only thread** | We sent qualify/drip; zero inbound — likely landline or dead number |

### Intent classes

| Intent | Re-engage? |
|--------|------------|
| `bonafide_seller` | Yes (if gap exists) |
| `bonafide_referral` | Yes — referrer nurture track, not seller appointment |
| `referral_low_intent` | **No** — move on |
| `non_viable` | **No** — move on |
| `unclear` | Only if unanswered **real** inbound exists |

---

## 6. Dispositions — agent must move on

These appear in `REENGAGE.md` under **Move on / landline (do NOT re-engage)**:

| Disposition | Meaning | Agent action |
|-------------|---------|--------------|
| `landline_no_sms` | Landline or SMS delivery failure detected | Tag `landline` + `no-sms`; call-only or archive; **no SMS** |
| `outbound_only_no_response` | Only our outbound (e.g. "What's your name?"); zero inbound | Same — likely landline; tag and move on |
| `move_on` | Referral-only, non-serious, or already worked | Note in GHL; do not re-engage |

**Example (MCO):** `206-365-3196` — we asked "Hey there! What's your name?" — no reply because landline/outbound-only, **not** because we missed their inbound.

**Example (MCO):** Tom Sahagian — referral-only, not serious referrer → `move_on`, excluded from list.

---

## 7. Landline & SMS delivery (GHL automation)

### Detection signals (audit)

- Transcript/body: `landline`, `cannot receive sms`, `30006`, `delivery failed`, `undeliverable`
- Contact already tagged `landline` / `no-sms`
- **Outbound-only thread** with zero inbound after our drip

### GHL tags (standard)

```
landline
no-sms
```

Apply via MCP `contacts_add-tags` (Tier B) or audit flag:

```bash
python3 /docker/clawsum/scripts/ghl-strategic-audit.py --slug {slug} --apply-landline-tags
```

### Recommended GHL workflow (manual — not in MCP v1)

On SMS delivery error (landline / Twilio 30006):

1. Auto-add tags `landline` + `no-sms`
2. Remove from SMS drip workflows
3. Route to call-only queue or archive
4. Do **not** count as missed SMS follow-up in reporting

---

## 8. Transcript analysis — lessons learned

### PIT scope required

Enable **View/Edit Conversation Messages** on the PIT. Without it, `conversations_get-messages` often returns empty and analysis falls back to `lastMessageBody` only — higher false-positive rate.

### Outbound vs inbound misclassification (fixed)

**Problem:** Our qualify/drip scripts were parsed as unanswered **inbound** seller questions:

- "Hey there! What's your name?"
- "Before we dive in, what's your first name?"
- "Did I catch you at a bad time?"

**Fix (in audit script — applies to all accounts automatically):**

- Recognize **our outbound script patterns** and never treat them as seller questions
- When `inbound_count == 0` and `outbound_count > 0` → `outbound_only_no_response`, not a gap
- Prefer `direction` / `lastMessageDirection` over defaulting unknown messages to inbound
- Filter our script lines from coaching ("question never answered")

### Worked lead definition

Outbound **after** inbound = worked, even if slow (>48h). Do not re-engage solely because `lastActivity` is stale if transcript shows we already texted/called.

---

## 9. Per-lead deliverables (viable re-engage only)

Each viable lead in the audit output includes:

| Field | Purpose |
|-------|---------|
| `contact_specific_hook` | Exact detail from their message (question, situation, address) |
| `suggested_sms` | Copy-paste follow-up referencing that hook — generic only when no intel |
| `what_went_wrong` | What our team did poorly in the thread |
| `process_improvement` | Concrete automation/script/training fix |

SMS generation: rule-based first; OpenAI batch when `--use-llm` and `OPENAI_API_KEY` set. LLM output is **rejected** if it ignores available contact intel.

### Coaching examples

| Scenario | What went wrong | Future fix |
|----------|-----------------|------------|
| Unanswered inbound | Seller text never got reply | Inbound trigger → SMS in 5 min + acq rep task |
| Missed call | Voicemail, no callback | Missed-call text-back workflow <2 min |
| Slow reply | >48h speed-to-lead | Alert on leads unanswered >15 min |
| Landline | SMS cannot deliver | Tag landline; call-only; remove from SMS drips |

---

## 10. MCP capabilities & limits

**36 official tools** (not community 250+ servers). Full catalog: `deploy/docs/GHL-AGENT-CAPABILITIES.md`

### Available for REI ops

Contacts, opportunities/pipelines, conversations (search + messages + send), location/custom fields, calendars, payments, email templates, blogs, social

### NOT available (document in Obsidian + Paperclip)

- List/edit **workflows & automations**
- Forms / form submissions
- Bulk workflow triggers
- Funnel/website builder

Agent **recommends**; Boss or Coding agent implements in GHL UI until workflow MCP ships.

---

## 11. Authorization tiers (all agents)

| Tier | Examples | Approval |
|------|----------|----------|
| **A — Read/audit** | get-contacts, search-conversation, get-messages, strategic audit | Pre-approved |
| **B — Operational write** | add-tags, update-contact, send message | Boss per task: `Boss approved GHL writes: yes` |
| **C — Marketing** | blog, social, email template create | Boss approves copy + timing |
| **D — Platform** | Obsidian reports, Postgres, Paperclip | Per runbook |

**Never:** another GHL location, bulk destructive actions without Boss sign-off.

---

## 12. Postgres & isolation

Each account has isolated schema (`mco_rei`, `ave_rei`, `wnn_rei`):

- `audit_runs`, `findings`
- `reengage_leads` (with `suggested_sms`, coaching columns)
- `conversation_reviews`

Verify after any config change:

```bash
python3 /docker/clawsum/scripts/verify-ghl-isolation.py
```

---

## 13. Telegram group binding

Per account in `ghl-accounts.json`:

- `telegram_needles` — title substring match (e.g. `"cs ghl"`, `"ave rei"`)
- `telegram_group_id` — explicit override (optional)

```bash
python3 /docker/clawsum/scripts/bind-ghl-telegram.py --slug {slug} --from-sessions
python3 /docker/clawsum/scripts/bind-ghl-telegram.py --status
```

After binding: restart `openclaw-gateway`. Boss @mentions bot (`requireMention` is on).

---

## 14. Anti-patterns (do not repeat)

| Anti-pattern | Correct approach |
|--------------|------------------|
| Flagging contacts by stale `lastActivity` only | Review SMS/call transcript; confirm bonafide interest + real gap |
| Treating our drip as unanswered inbound | Outbound-only → landline/move-on disposition |
| Re-engaging referral-only curiosity | `referral_low_intent` → `move_on` |
| SMS re-engage to landlines | Tag `landline` + `no-sms`; call-only |
| Agent search/browser for re-engage | Read `REENGAGE.md` directly |
| Generic SMS when intel exists | Reference their question, situation, or address |
| Cross-account MCP or DB queries | One location per agent, always |

---

## 15. First-week runbook (AVE / WNN rollout)

1. Add PIT + location ID to `.env` (`GHL_{SLUG}_PIT`, `GHL_{SLUG}_LOCATION_ID`, `GHL_{SLUG}_DB_PASSWORD`)
2. Confirm PIT has Conversation Messages scope
3. Run provision + isolation verify + Telegram bind
4. Run strategic audit: `--slug ave-rei --use-llm` (or `wnn-rei`)
5. Review `Audits/` and `Recommendations/` in Obsidian
6. Run `--apply-landline-tags` once (Boss approval) to backfill landline hygiene
7. Test Telegram: @mention bot → ask for re-engage summary → confirm it reads `REENGAGE.md`
8. Open Paperclip tasks for Boss-approved remediation only

---

## 16. Quick command reference

```bash
# Strategic audit + re-engage (replace slug)
python3 /docker/clawsum/scripts/ghl-strategic-audit.py --slug ave-rei --use-llm

# Landline tag backfill (Tier B)
python3 /docker/clawsum/scripts/ghl-strategic-audit.py --slug ave-rei --apply-landline-tags

# Refresh Telegram summary only
python3 /docker/clawsum/scripts/ghl-reengage-summary.py --slug ave-rei --refresh

# MCP tool inventory
python3 /docker/clawsum/scripts/dump-ghl-mcp-tools.py

# Connection smoke test
python3 /docker/clawsum/scripts/test-ghl-mco-connection.py   # adapt per account as needed
```

---

## Related documents

| Document | Location |
|----------|----------|
| MCP task catalog | `deploy/docs/GHL-AGENT-CAPABILITIES.md` |
| Multi-account plan | `deploy/docs/GHL-MULTI-ACCOUNT-PLAN.md` |
| Account config | `deploy/config/ghl-accounts.json` |
| Agent templates | `deploy/templates/ghl-account/` |
| Strategic audit script | `deploy/scripts/ghl-strategic-audit.py` |

---

*Last updated: 2026-07-01 — MCO REI production learnings. Update this doc when AVE or WNN audits surface account-specific differences.*
