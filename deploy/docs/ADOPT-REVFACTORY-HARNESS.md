# RevFactory Harness vs Clawsum

**Verdict: steal the factory; do not replace Hermes or OpenClaw. Side-by-side study is worth it.**

Harness ([revfactory/harness](https://github.com/revfactory/harness)) is a **Claude Code plugin** — a *team-architecture factory*. You say “build a harness for this project” and it writes agent definitions + skills for that domain.

That is a different layer than Clawsum.

## How it actually overlaps (and doesn’t)

| Job | Harness | Clawsum today | Who wins / what to do |
|-----|---------|---------------|------------------------|
| Talk to the Boss, cockpit, voice | No | **Hermes** | Keep Hermes |
| Task board, assignees, approvals | No | **Paperclip** | Keep Paperclip |
| Run agents against live tools (Gmail, GHL, Docker) | No (Claude Code session) | **OpenClaw** | Keep OpenClaw |
| From one sentence → new specialist team + skills | **Yes — this is the product** | Manual: `provision-*.py`, `seed-persona-os.sh`, hand-written `SKILL.md` | **Steal this. We are weaker here.** |
| Six team patterns (pipeline, fan-out, expert pool, producer-reviewer, supervisor, hierarchy) | Built-in | Informal (W2 batch, cell agents) | Port the patterns into `skill-forge` |
| Validate “with skill vs without” | Built-in | Mostly missing | Steal |
| CEO overwatch, inbox, memory dream, Discord HQ | No | Clawsum | Keep |

So “it overlaps Hermes/OpenClaw” was too coarse. Harness does **not** chat with Gerald, manage CLA- tickets, or call GHL. It **does** mint a coordinated team + skill pack faster than we do.

## Adopt path

1. **Steal ideas now** — `skill-forge`: one Boss sentence → draft OpenClaw agent + `SKILL.md` + Paperclip assignee (Coding + Planning).
2. **Side-by-side (optional)** — Coding installs Harness in a scratch Claude Code workspace, generates a “Clawsum media” or “REI GHL” team, diffs against our catalog. No production cutover.
3. **Do not** point Boss chat at Claude Code / Harness as the daily driver.

## Owner

- Project: `clawsum-platform` (factory) / `techtasia` (roadmap)
- Agents: **Clawsum Planning** (patterns) + **Clawsum Coding** (wire into OpenClaw)
- Skills: `inbound-adopt-evaluate`, `skill-forge`, `openclaw-agent-config`, `paperclip-task-routing`
