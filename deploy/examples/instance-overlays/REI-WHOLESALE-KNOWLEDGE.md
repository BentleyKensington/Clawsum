# REI wholesaling knowledge — GHL MCO + Avenou (AVE)

**Audience:** `ghl-mco-rei`, `ghl-ave-rei` (and later `ghl-wnn-rei`)  
**Authority:** Tier 0–1 read/draft; Tier 2 send/write needs Boss approval  
**Companion:** [REI-GHL-AGENT-PLAYBOOK.md](./REI-GHL-AGENT-PLAYBOOK.md)

Distilled from live MCO REI CRM ops plus industry wholesaling CRM practice (separate acquisition vs disposition, SMS-first follow-up, speed-to-lead, buyer-list hygiene).

---

## 1. What wholesaling is (agent mental model)

| Side | Goal | CRM focus |
|------|------|-----------|
| **Acquisition** | Contract with motivated sellers (assign/double-close later) | Seller pipeline, SMS/calls, appointments, offers |
| **Disposition** | Assign contracted deals to cash buyers | Buyer pipeline, criteria tags, deal blasts |

**Never mix** seller acquisition and buyer disposition in one pipeline. Tags and automations must route separately.

Core funnel health signals (leading indicators > vanity):

- Speed-to-first-touch (target: **&lt;5–15 min** inbound; missed-call text-back **&lt;2 min**)
- Contact / conversation rate
- Appointment set rate
- Offers made / week
- Contracts / week
- Days under contract → assigned (healthy **7–21**; &gt;30 = price or buyer-list problem)
- Active buyers (engaged last 90d) — thin list kills disposition

---

## 2. What to look for in a GHL account (audit checklist)

### A. Account hygiene

| Check | Healthy | Red flag |
|-------|---------|----------|
| Timezone | Matches market | Wrong TZ → wrong drip timing |
| A2P / TCR | Approved for RE lead gen | Unregistered → carrier filter kills SMS |
| Dedicated numbers | Per caller + inbound | One shared blast number for high volume |
| Notifications | Inbound SMS + missed call + tasks on | Silent inbox → 48h+ gaps |

### B. Pipelines (must-have shape)

**Seller / acquisition (example stages):**  
New Lead → Attempted Contact → Contacted → Follow-Up / Nurture → Appointment Set → Offer Made → Negotiating → Under Contract → Closed / Dead

**Buyer / disposition (separate):**  
New Buyer → Criteria Captured → Proof of Funds → Active → Deal Sent → Offer Received → Assigned / Closed → Inactive

Look for:

- Missing **Attempted vs Contacted** split (hides bad numbers vs real no-interest)
- Seller + buyer mixed in one board
- Stages with **no next-action / task rule**
- Stale opps sitting 14+ days with no task
- Dead 2023–style duplicate pipelines still receiving leads

### C. Custom fields (REI minimum)

On seller contacts / opportunities:

- Property address (≠ mailing if different)
- Motivation (probate, divorce, vacant, behind payments, inherited, relocating, other)
- Timeline (now / 1–3 mo / 3–6 / no rush)
- Condition, beds/baths/sqft, estimated ARV, equity / owed
- Asking / offer price, contract date, assignment fee target
- Lead source, assigned VA / acq rep

On buyers:

- Buy box (zips/cities, property type, max price, rehab appetite)
- Close speed, proof of funds status, last deal response date
- Tags: `cash-buyer-active`, `cash-buyer-inactive`, `pof-verified`

### D. Tags (standard Clawsum REI)

| Tag | Meaning |
|-----|---------|
| `landline` + `no-sms` | SMS blocked — call-only / archive; **never** SMS re-engage |
| `bonafide-seller` | Confirmed motivated owner |
| `referral-partner` | Serious referrer track (not seller appt) |
| `dnc` / opt-out | Hard stop |
| `cash-buyer-active` / `inactive` | Disposition routing |
| `move-on` | Disposition documented; do not re-engage |

### E. Automations that should exist (recommend if missing)

1. **Speed-to-lead SMS** on new inbound / form / PPC
2. **Missed-call text-back** &lt;2 min
3. **Contact Attempted** drip (5 touches over ~30d) — stop on reply
4. **Offer Sent** follow-up (24h / 48h / 5d) — **manual override** when seller set a callback
5. **Under Contract → buyer blast** to matching buy-box segment
6. **Landline / Twilio 30006** → add `landline`+`no-sms`, exit SMS drips
7. **No stage without task / next action date**

### F. Conversation quality (live CRM truth)

Read transcripts — do **not** trust stale `lastActivity` alone.

| Signal | Action |
|--------|--------|
| Bonafide seller + unanswered inbound &gt;48h | Re-engage (priority) |
| Our drip only, zero inbound | `outbound_only_no_response` — likely landline; move on |
| Referral curiosity only | `referral_low_intent` — move on |
| Recent outbound within 7d already answered their ask | Already worked — do not duplicate SMS |
| Delivery failed / landline language | Tag; call-only |

---

## 3. Good practices (operating rules)

1. **Read-first.** Audit / `REENGAGE.md` before proposing sends.
2. **Personalize or don't send.** Hook = their address, question, motivation, or callback ask. Generic “just checking in” only when zero intel.
3. **Hot leads stay human.** Once Offer / Negotiating / Under Contract — no blind drip that ignores their timeline.
4. **Respect DNC / STOP.** Immediate tag + exit all SMS.
5. **One next action.** Every open opp needs owner + date.
6. **Separate nurture from active.** Cold 30/60/90 drip ≠ active negotiation.
7. **Buyer list quality &gt; size.** Prefer active 90d responders over bloated inactive lists.
8. **Cell isolation.** MCO never reads AVE PIT/DB; AVE never reads MCO.
9. **Compliance.** No legal/tax advice; escalate probate/title disputes to Boss.
10. **Weekly rhythm.** Monday weekly report → Boss reviews priorities → approved writes only.

---

## 4. Recommended responses

Tone: short, respectful, SMS-native, local cash buyer — **not** realtor listing pitch. Use company name from the GHL location; never invent fees or guaranteed prices.

### Sellers — first response (inbound / form)

> Hi {First}, got your note about {Address or “your property”}. We buy houses as-is for cash and can move on your timeline. What’s the best time for a quick call today?

### Sellers — missed call

> Hi {First}, sorry I missed you — this is {Rep} with {Company} about {Address}. Happy to text or call back. When works?

### Sellers — re-engage (bonafide + gap)

> Hi {First}, circling back on {hook — e.g. “the cash offer question for Oak St”}. Still helpful if we put numbers together this week?

### Sellers — post-offer (no response)

> Hi {First}, checking that the offer for {Address} came through clearly. Any questions on price or close date? Happy to adjust terms if needed.

### Sellers — soft close / exit

> Totally fine if timing isn’t right. Want me to pause outreach, or check back in 30–60 days?

### Referrers (serious)

> Thanks for thinking of us. If the owner is open to a cash conversation, send the address + best phone and we’ll take it from there — we’ll keep you updated.

### Referrers (curiosity only — do **not** push seller script)

> Appreciate it. If they decide they’re serious about selling, send them our way and we’ll help. No rush.

### Buyers — criteria capture

> Thanks for joining the buyer list. Quick check so we only send fits: which zips/cities, max purchase price, and rehab appetite (turnkey / light / heavy)?

### Buyers — deal alert (disposition)

> {Address} — {beds/baths}, {sqft}, ARV ~${arv}, asking ${ask}. Cash, flexible close. Reply YES for details/photos or call {number}.

### Buyers — inactive revive

> Still buying in {area}? We can keep you on active alerts, or mark you inactive so we don’t spam. Reply ACTIVE or STOP.

### Landline / SMS failed (internal note — call script)

> Hi {First}, this is {Rep} with {Company} following up about {Address}. We couldn’t reach you by text — do you have a few minutes now?

---

## 5. Examples from live GHL CRM (MCO REI)

These came from production MCO strategic audits — use as **patterns**, not as permission to re-open those contacts.

| Pattern | Live example | Correct disposition |
|---------|--------------|---------------------|
| Outbound drip, zero inbound | `206-365-3196` — “Hey there! What's your name?” with no reply | `outbound_only_no_response` / likely landline — **not** missed inbound |
| Referral-only, not serious | Tom Sahagian | `move_on` — exclude from re-engage |
| Script misread as seller Q | Our lines: “Before we dive in, what's your first name?” / “Did I catch you at a bad time?” | Never treat as unanswered **inbound** seller questions |
| SMS blocked | Transcript/body: landline, cannot receive SMS, Twilio **30006** | Tags `landline` + `no-sms`; call-only |

**Viable re-engage requires all three:** bonafide interest (or serious referral), real follow-up gap, not already worked in last 7d outbound.

---

## 6. Coaching cues (what went wrong → fix)

| Scenario | What went wrong | Process fix |
|----------|-----------------|-------------|
| Unanswered inbound | Seller text never answered | Inbound → SMS ≤5 min + acq task |
| Missed call, no text-back | Voicemail black hole | Missed-call workflow ≤2 min |
| Slow reply (&gt;48h) | Speed-to-lead broken | Alert unanswered &gt;15 min |
| Landline in SMS drip | Wasted touches + false “no response” | Auto-tag; exit SMS; call queue |
| Generic re-engage | Ignored their address/question | Require `contact_specific_hook` in SMS |
| Hot lead in cold drip | Annoyed seller mid-negotiation | Pause automation on Offer+ stages |

---

## 7. Weekly report (what Boss should see)

Nightly cron (`ghl-weekly-report.py`, sent 07:30 America/Chicago) for **MCO** and **Avenou** should surface:

1. **Pipeline snapshot** — open opps by stage (seller vs buyer)
2. **Re-engage** — viable count, top 5–10 hooks + suggested SMS
3. **Move-on / landline** — excluded counts (do not SMS)
4. **Conversation gaps** — unanswered inbound / slow replies
5. **Field & automation gaps** — missing REI fields, missing speed-to-lead / missed-call
6. **Recommendations** — prioritized; writes need Boss approval
7. **Links** — Obsidian audit + `REENGAGE.md` paths

Agent Telegram behavior unchanged: Boss asks → **read** `REENGAGE.md` (exact path) → summarize. Also read this file (`KNOWLEDGE-REI.md`) when drafting seller/buyer copy or audit advice.

---

## 8. Forbidden / escalate

- Sending SMS/email without Tier 2 approval
- Cross-account GHL or Postgres access
- Legal, title, or financing advice phrased as guarantees
- Bulk workflow edits without Boss sign-off
- Re-engaging DNC, landline-tagged, or move-on contacts via SMS

---

*Last updated: 2026-08-06 — research + MCO live CRM learnings for MCO REI and Avenou (AVE REI).*
