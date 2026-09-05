# DinoCrushBoss

Family-safe 3D match-3 (Dino Crush). Module for the DinoHawk cell.

- **Public:** https://dinocrushboss.com
- **Ops desk:** https://dash.dinohawk.com (Authelia)
- **Upstream:** https://github.com/aaaredrover/DinoCrush2

## Local

Requires Clawsum Postgres (`26-ops-dinocrush.sql` + `29-ops-dinocrushboss.sql`).

```bash
# from deploy/
docker compose up -d postgres
psql "$DATABASE_URL" -f postgres-init/26-ops-dinocrush.sql
psql "$DATABASE_URL" -f postgres-init/29-ops-dinocrushboss.sql
docker compose --profile dinohawk up -d --build dinocrushboss
# http://127.0.0.1:8092/
```

Or without Docker, from this folder:

```bash
npm install
export DATABASE_URL=postgresql://clawsum:clawsum_change_me@127.0.0.1:5432/clawsum
export SESSION_SECRET=dev-only
npm run dev   # http://127.0.0.1:5000
```

## Production

```bash
bash scripts/provision-dinocrushboss.sh
```

DNS/TLS for `dinocrushboss.com` is Tier 2. Guest play works without an account; signed-in progress is stored in schema `dinocrush`.
