# Boss Obsidian on Windows (SSHFS)

**Goal:** Open the VPS vault (`/docker/clawsum/obsidian`) as a normal Obsidian vault on your PC.  
**Source of truth:** VPS only — agents never write to your PC.

---

## Prerequisites

1. **SSH to VPS** already works (`ssh clawsum` or `ssh root@YOUR_VPS_IP`).
2. Install **WinFsp** + **SSHFS-Win** (one-time, admin):

   - WinFsp: https://winfsp.dev/rel/
   - SSHFS-Win: https://github.com/winfsp/sshfs-win/releases (install the `.msi`)

3. **Obsidian** desktop: https://obsidian.md

---

## One-time mount (manual)

Replace `CLAWSUM` with your SSH host alias or `root@YOUR_VPS_IP`.

```powershell
# Create mount point
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\ClawsumVault" | Out-Null

# Mount (uses Windows SSH config for host `clawsum`)
net use Z: \\sshfs\clawsum\docker\clawsum\obsidian /persistent:yes
```

If you don't use a host alias:

```powershell
net use Z: \\sshfs.r\root@YOUR_VPS_IP\docker\clawsum\obsidian /persistent:yes
```

Open Obsidian → **Open folder as vault** → `Z:\` (or `%USERPROFILE%\ClawsumVault` if you mapped there).

---

## Automated script (repo)

From the Clawsum repo on your PC:

```powershell
powershell -ExecutionPolicy Bypass -File deploy\scripts\setup-boss-obsidian-sshfs.ps1
```

Options:

```powershell
# Custom drive letter and host
.\deploy\scripts\setup-boss-obsidian-sshfs.ps1 -DriveLetter Z -SshHost clawsum

# Unmount
.\deploy\scripts\setup-boss-obsidian-sshfs.ps1 -Unmount
```

---

## What to read / write as Boss

| Folder | You |
|--------|-----|
| **Admin/** | **Write** — runbooks, inbox notes, Boss decisions |
| **Admin/Reports/** | Read — daily global reports |
| **Research/**, **RealEstate/**, etc. | **Read** — agent deliverables; delegate edits via Paperclip |
| **Paperclip/** | Read — orchestration notes |

See [OBSIDIAN-VAULT.md](./OBSIDIAN-VAULT.md) for full layout.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `network name cannot be found` | Install WinFsp + SSHFS-Win; reboot once |
| Permission denied | VPS path must be readable: `ssh clawsum "ls /docker/clawsum/obsidian"` |
| Stale files | Remount: `net use Z: /delete` then run setup script again |
| Slow save | Normal over SSH; Syncthing is an alternative (see OBSIDIAN-VAULT.md) |

---

## VPS check (ops)

```bash
python3 /docker/clawsum/scripts/setup-obsidian-vault.py --sync-only
ls -la /docker/clawsum/obsidian/Admin/Reports/
```

---

## Related

- [BOSS-ACCESS-GUIDE.md](./BOSS-ACCESS-GUIDE.md) — Boss UI, Control UI URLs  
- [Admin-Runbooks/daily-boss-routine.md](./Admin-Runbooks/daily-boss-routine.md) — daily flow  
- [HERMES-POLICY.md](./HERMES-POLICY.md) — Hermes via gateway (not standalone)
