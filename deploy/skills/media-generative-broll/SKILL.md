---
name: media-generative-broll
description: Generates B-roll, thumbnails, intros via ComfyUI / Velorn (local). Use when source footage is thin or thumbnails are needed.
agents: [media]
cells: [media-production, hardware-local-ai]
tier_autonomous: 1
credentials: [COMFY_*, MINIO_*]
approval_actions: [cloud_gpu_spend, paid_voice_music]
---

# Media generative B-roll (Phase 4 · Tier 1 local / Tier 2 paid)

## When to use

Need AI stills/video beds, thumbnails (Flux/SDXL/Wan), or Velorn timeline inserts.

## Instructions

1. Prefer **local ComfyUI** on Boss RTX; Velorn MCP when agent-driven timeline edits help.
2. Queue GPU jobs so Whisper/chat are not starved (`hardware-local-ai`).
3. Store generations in MinIO; cite workflow/model in Paperclip.
4. Optional local: AudioCraft/MusicGen, XTTS/F5-TTS. **ElevenLabs / cloud GPU** → create Tier 2 approval first.
5. OpenReelio remains watchlist — do not block on it.

## Escalation

- Paid cloud generation or voice = Tier 2 + Gerald.
- Trademark/likeness sensitive gens → Boss.

## References

- [MEDIA-PRODUCTION-STUDIO.md](../../docs/MEDIA-PRODUCTION-STUDIO.md)
