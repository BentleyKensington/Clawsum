# GAME.md — Dino Crush logic (dinohawk)

You **own** Dino Crush play. Edit files under `game/` (this workspace) — that folder is the live module `modules/dinocrushboss`.

## Where logic lives

| File | What to change |
|------|----------------|
| `game/client/src/lib/gameLogic.ts` | Board generation, swaps, matches, cascades, valid moves |
| `game/client/src/lib/constants.ts` | Grid size, level goals, star thresholds, timers, `LEVEL_COUNT` |
| `game/client/src/lib/stores/useDinoCrush.tsx` | Score, moves, level complete, power-ups |
| `game/client/src/types/game.ts` | Dino types, power-ups, board types |
| `game/client/src/components/game/SimpleBoard.tsx` | Tile art map, click/swap UX |
| `game/client/src/components/screens/MainMenu.tsx` | Start screen, level select |
| `game/client/src/components/screens/GameScreen.tsx` | In-level HUD |
| `game/client/src/components/screens/LevelComplete.tsx` | Stars / next level |

Do **not** mix Pokémon, cash, CloseBot, or Authelia into these files. Kid lane only.

## How to ship a playable change

1. Read the files above. Prefer the smallest patch that makes the play feel better.
2. Edit with apply_patch / write. Stay inside `game/`.
3. Apply live (rebuild + restart the public game):

```bash
touch /home/node/.openclaw/workspace-dinohawk/game/.apply-request
```

Wait until `https://game.dinocrushboss.com/api/health` returns ok (usually 1–3 minutes on a cold image, ~20s when cached). Then tell Boss what changed and how to feel it in play.

Host equivalent: `bash /docker/clawsum/scripts/rebuild-dinocrushboss.sh`

## Do not

- Change DNS, Traefik, or Authelia (Tier 2 / Boss).
- Print `DINOCRUSHBOSS_PLAY_PASSWORD` or session secrets.
- Switch the database back to Neon. Postgres schema `dinocrush` stays.
