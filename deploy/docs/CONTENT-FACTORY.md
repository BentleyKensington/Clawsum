# Evergreen content factory

**Status:** Wired Aug 2026 — daily cron + FFmpeg draft renders. Live social APIs still Tier 2.  
**Idea in:** Hermes / Boss chat / Discord  
**Produce daily:** yes — even if Boss sent nothing (evergreen bank)

Related: [MEDIA-PRODUCTION-STUDIO.md](./MEDIA-PRODUCTION-STUDIO.md), [AUTHORITY.md](../skills/AUTHORITY.md)

---

## Flow

```text
Gerald → Hermes  "idea / make a post / flyer / video"
        │  content-factory.py intake --source boss
        ▼
   Research     evergreen angle + trend *format* (not news expiry)
        ▼
   Content      topic · flyer · image prompts · social story · script
        ▼
   Media        flyer.png · first-frame.png · thumbnail.png · draft-short.mp4
        ▼
   Social       ops.social_queue  schedule | --now
        ▼
   ops.approvals (Tier 2) → Gerald → post
```

Daily (America/Chicago): **07:10** seed one evergreen idea · **07:20** `run-one` (pack → produce → queue). Boss `inbox` ideas run first.

---

## What you get per idea

| Artifact | Path / table |
|----------|----------------|
| Pack | `data/media/exports/content/<id>/pack.json` |
| Flyer copy + card | `flyer.txt`, `flyer.png` |
| Social story | `story.txt` |
| Production script | `script.txt` |
| First frame | `first-frame.png` |
| Thumbnail | `thumbnail.png` |
| Draft video | `draft-short.mp4` (9:16 ~8s title card) |
| Queue | `ops.social_queue` (`pending_approval`) |

Upgrade later: Comfy/Flux for stills, ElevenLabs VO, `media-shorts-factory` for real cuts.

---

## Commands

```bash
# Boss idea (Hermes / Admin)
python3 /docker/clawsum/scripts/content-factory.py intake --text "Your idea"

# Daily seed (cron)
python3 /docker/clawsum/scripts/content-factory.py daily --count 1
python3 /docker/clawsum/scripts/content-factory.py run-one

# Manual stages
python3 /docker/clawsum/scripts/content-factory.py pack --idea-id UUID
python3 /docker/clawsum/scripts/content-factory.py produce --idea-id UUID
python3 /docker/clawsum/scripts/content-factory.py queue --idea-id UUID
python3 /docker/clawsum/scripts/content-factory.py queue --idea-id UUID --now
```

---

## Agents

| Step | Assignee |
|------|----------|
| Intake / track | Hermes (propose only) |
| Angle | Clawsum Research |
| Pack | Clawsum Content |
| Render | Clawsum Media |
| Schedule / post | Clawsum Social (**Tier 2**) |

---

## Schema

Apply once:

```bash
docker exec -i clawsum-postgres-1 psql -U clawsum -d clawsum \
  -f - < /docker/clawsum/postgres-init/20-ops-content-factory.sql
```

Tables: `ops.content_ideas`, `ops.content_packs`, `ops.content_assets`, `ops.social_queue`.

---

## Install cron

```bash
bash /docker/clawsum/scripts/install-content-factory-cron.sh
```

---

## Evergreen rule

Default **evergreen=true**. Trends inform *format* (hook length, on-screen style), not a claim that expires tonight. News-only seeds use `--not-evergreen` and are labeled on the issue.
