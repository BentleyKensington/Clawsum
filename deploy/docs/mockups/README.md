# CEO cockpit mockups

Composite target: **5th-gen jet interior** — gauges, digital readouts, eye-ease color (cyan / amber / lime / rose), scrolling HUD marquee, clickable tiles, Graphify memory sphere, Ask Boss reply strip.

## Organized refs

| File | Use |
|------|-----|
| [ceo-cockpit-fighter-hud.png](./ceo-cockpit-fighter-hud.png) | Composite HUD direction (generated 2026-08-10) |
| ../../examples/hermes-cockpit/assets/crest.png | Crest / mark |
| ../../examples/hermes-cockpit/assets/logo-mark.png | Wordmark |
| ../../examples/hermes-cockpit/skins/clawsum.yaml | Live skin tokens |
| ../../examples/hermes-cockpit/theme/clawsum-command.yaml | Command theme |

Inbox / ChatGPT image attachments are filed by the analyst into MinIO + `ops.media_objects` (not this folder). Treat those mockups as **product input** — adopt / side-by-side / steal — via `inbound-adopt-evaluate`.

## Build into the live HUD

Start hub (`/home`) now carries:

- Scrolling marquee (greeting + live status)
- Clickable gauges → Inbox / Team / Skills / Paperclip / Cron / Channels / Graphify
- Ask Boss reply box (POST `/inbox/reply`)
- Graphify pane over `ops.memory_facts`
