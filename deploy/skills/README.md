# Clawsum Skills Catalog

Platform skills for Hermes, Paperclip assignees, OpenClaw agents, and Cursor coding agents.

**Source of truth:** `deploy/skills/` (ships with VPS `/docker/clawsum`).  
Optional IDE mirror: copy or symlink into `.cursor/skills/` later.

## Layout

```text
deploy/skills/
├── README.md              ← this file
├── AUTHORITY.md           ← agents · cells · creds · risk tiers
├── CATALOG.md             ← full skill index + access matrix
├── _template/SKILL.md     ← copy when adding a skill
└── <skill-name>/
    ├── SKILL.md           ← required
    ├── reference.md       ← optional deep notes
    └── scripts/           ← optional helpers
```

## Skill contract (every SKILL.md)

YAML frontmatter must include:

| Field | Purpose |
|-------|---------|
| `name` | kebab-case id |
| `description` | WHAT + WHEN (third person) |
| `agents` | Which Paperclip/OpenClaw agents may run it |
| `cells` | Allowed `ops.businesses.slug` values (`*` = any with approval) |
| `tier_autonomous` | Max risk tier the skill may complete without Boss (0–1 typical) |
| `credentials` | Required env prefixes / vault keys (never paste secrets into skill text) |
| `approval_actions` | Action types that must create `ops.approvals` first |

## How agents load skills

| Runtime | How |
|---------|-----|
| **Hermes UI** | SOUL + explicit “use skill X”; prefer read `deploy/skills/<name>/SKILL.md` |
| **OpenClaw** | Agent workspace / ClawHub skill enablement; cell-scoped credentials only |
| **Paperclip** | Task description links skill name; assignee must match `agents:` |
| **Cursor** | Project skill under `.cursor/skills/` or `@`-mention path |

## Adding a skill

1. Copy `_template/SKILL.md` → `deploy/skills/<name>/SKILL.md`
2. Fill frontmatter + steps (keep under ~200 lines; put depth in `reference.md`)
3. Add a row to [CATALOG.md](./CATALOG.md)
4. Update [AUTHORITY.md](./AUTHORITY.md) if new creds or agents appear

## Related docs

- [AUTHORITY.md](./AUTHORITY.md)
- [CATALOG.md](./CATALOG.md)
- `../docs/PAPERCLIP-OVERWATCH.md`
- `../docs/RESUME-POLICY.md`
- `../docs/HERMES-POLICY.md`
