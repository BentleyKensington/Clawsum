# Mount Clawsum Obsidian vault from VPS via SSHFS (Windows).
param(
    [string]$DriveLetter = "Z",
    [string]$SshHost = "clawsum",
    [string]$RemotePath = "/docker/clawsum/obsidian",
    [switch]$Unmount
)

$ErrorActionPreference = "Stop"
$drive = "${DriveLetter}:"

if ($Unmount) {
    net use $drive /delete /y 2>$null
    Write-Host "Unmounted $drive (if it was connected)."
    exit 0
}

# WinFsp + SSHFS-Win required
$sshfs = "${env:ProgramFiles}\SSHFS-Win\bin\sshfs.exe"
if (-not (Test-Path $sshfs)) {
    Write-Host @"
SSHFS-Win not found. Install once (Administrator):
  1. WinFsp: https://winfsp.dev/rel/
  2. SSHFS-Win: https://github.com/winfsp/sshfs-win/releases
Then re-run this script.
"@
    exit 1
}

# Drop existing mapping
net use $drive /delete /y 2>$null | Out-Null

# sshfs-win UNC: \\sshfs[.r]\[user@]host[\path]
$unc = "\\sshfs\$SshHost$($RemotePath -replace '/','\')"
Write-Host "Mounting $drive -> $unc"
net use $drive $unc /persistent:yes

if ($LASTEXITCODE -ne 0) {
    Write-Host "Retry with explicit root@ form..."
    $unc = "\\sshfs.r\root@YOUR_VPS_IP$($RemotePath -replace '/','\')"
    net use $drive $unc /persistent:yes
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "Mount failed. Test: ssh $SshHost `"ls $RemotePath`""
}

Write-Host @"

Mounted $drive -> VPS $RemotePath

Next:
  1. Open Obsidian
  2. Open folder as vault -> $drive\
  3. Read Admin/Reports/; write in Admin/ only

Docs: deploy/docs/BOSS-OBSIDIAN-WINDOWS.md
"@
