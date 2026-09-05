---
name: dinocrushboss
description: Dino Crush public game at dinocrushboss.com — vendored from DinoCrush2. Kid-safe match-3. Deploy, versions, and dash.dinohawk.com telemetry. No cash.
agents: [dinohawk, coding, funnel]
cells: [dino-hawk]
tier_autonomous: 1
credentials: [POSTGRES_*, SSH/VPS, optional PORKBUN_*]
approval_actions: [dns_change, production_deploy]
---

# DinoCrushBoss (dinocrushboss.com)

- Source: `modules/dinocrushboss/` — dinohawk workspace path **`game/`**
- Promo: **https://dinocrushboss.com** · Login: **https://login.dinocrushboss.com** · Play: **https://game.dinocrushboss.com**
- Guest play: no registration. Email save is optional (`play@dinocrushboss.com` family alias).
- Accounts: Postgres schema `dinocrush` (`29-ops-dinocrushboss.sql` + `30-ops-dinocrushboss-login.sql`)
- Telemetry: `ops.game_*` on save-level / errors → Alex desk [dinohawk-dash](../dinohawk-dash/SKILL.md)
- Rebuild: `bash /docker/clawsum/scripts/rebuild-dinocrushboss.sh` or `touch game/.apply-request`

## When to use

Change match-3 logic, levels, tiles, or start-screen play. Child-facing copy and play only.

## Instructions

1. **DinoHawk edits play here:** `workspace-dinohawk/game/` (bind-mounted to `modules/dinocrushboss`).
2. Logic files: `game/client/src/lib/gameLogic.ts`, `constants.ts`, `stores/useDinoCrush.tsx`, `types/game.ts`, `components/game/SimpleBoard.tsx`. See workspace `GAME.md`.
3. After a playable patch: `touch game/.apply-request` (watcher rebuilds + restarts the public game).
4. Guest stays local to the browser. Email is the cloud save key. Do not mix Pokémon/cash into the game UI.
5. Schema/DNS still: apply `29` + `30`, then `provision-dinocrushboss.sh`. DNS/TLS = Tier 2.

```bash
bash /docker/clawsum/scripts/rebuild-dinocrushboss.sh
# full edge (promo + Traefik + Authelia bypass):
bash /docker/clawsum/scripts/provision-dinocrushboss.sh
```

## Escalation

Public DNS, TLS, store listing, ads, or IAP → Boss (Tier 2). Child thread: no prices or payouts.
