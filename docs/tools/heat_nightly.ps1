# HZM [bot A5] NIGHTLY HEAT LEARNING - one unattended pass of the soak -> heat -> deploy loop (bug-2865/2870).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File docs\tools\heat_nightly.ps1 [-Minutes 6] [-KeepRuns 3] [-NoDeploy]
#
# 1. Refuses to run while the game client (openmohaa) or another soak (omohaaded) is running - it would steal the CPU
#    from a player and clobber the soak log.
# 2. Soaks every Push map into _soak_nightly\<yyyy-MM-dd> (bot_probe 500ms, nav_dump on).
# 3. Regenerates navlinks\<map>_mp_heat.txt from the BASELINE + the newest -KeepRuns nightly runs (older nights drop out,
#    so a spot that was fixed stops being costed once it has been clean for KeepRuns nights).
# 4. Runs the QA gates that guard the Push layouts: push_spawn_sweep.py + push_endzone_check.py on the fresh nav dumps.
#    A FAILED gate means a spawn or a bot goal has become unreachable - the heat still regenerates, but nothing deploys.
# 5. Deploys with build.ps1 (only if the client is still closed), and writes a before/after table.
# Everything lands in _soak_nightly\<date>\nightly_report.txt. Registering it as a Windows scheduled task is a persistent
# system change - do that deliberately, e.g.:
#   schtasks /Create /TN "HZM heat nightly" /SC DAILY /ST 03:00 /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\mohaa-coop-dev\docs\tools\heat_nightly.ps1"
param(
    [int]$Minutes = 6,
    [int]$KeepRuns = 3,
    [switch]$NoDeploy
)
$ErrorActionPreference = 'Stop'
$dev   = 'C:\mohaa-coop-dev'
$night = Join-Path $dev '_soak_nightly'
$date  = Get-Date -Format 'yyyy-MM-dd'
$out   = Join-Path $night $date
New-Item -ItemType Directory -Force $out | Out-Null
$report = Join-Path $out 'nightly_report.txt'
function Log($s) { $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $s; Write-Host $line; Add-Content -Path $report -Value $line }

if (Get-Process openmohaa -ErrorAction SilentlyContinue) { Log 'SKIP: the game client is running'; exit 0 }
if (Get-Process omohaaded -ErrorAction SilentlyContinue) { Log 'SKIP: a dedicated server / soak is already running'; exit 0 }

Set-Location $dev
Log "soak -> $out"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $dev 'docs\tools\bot_soak.ps1') -Minutes $Minutes -ProbeMs 500 -OutDir $out -Extra '+set,nav_dump,1' | Out-Null

# heat sources: the baseline + the newest KeepRuns nightly folders that hold logs
$runs = Get-ChildItem $night -Directory | Where-Object { (Get-ChildItem $_.FullName -Filter *.log -ErrorAction SilentlyContinue).Count -gt 0 } |
        Sort-Object Name -Descending | Select-Object -First $KeepRuns
$srcs = @('_soak_heatbase') + ($runs | ForEach-Object { '_soak_nightly\' + $_.Name })
Log ("heat sources: " + ($srcs -join ','))
python docs\tools\gen_navheat.py ($srcs -join ',') 2>&1 | Add-Content -Path $report

$gates = $true
foreach ($g in @('push_spawn_sweep.py', 'push_endzone_check.py')) {
    $res = python (Join-Path 'docs\tools' $g) 'hzm-mohaa-coop-mod\coop_mod\mp_push_bsp.scr' 'hzm-mohaa-coop-mod\coop_mod\mp_push_maps.scr' 2>&1
    $res | Add-Content -Path $report
    $tail = ($res | Select-Object -Last 1) -as [string]
    if ($tail -notmatch '(bad 0|: 0)$') { $gates = $false; Log "GATE FAILED: $g -> $tail" } else { Log "gate ok: $g" }
}

$prev = ($runs | Select-Object -Skip 1 -First 1)
$cmp = @('_soak_heatbase')
if ($prev) { $cmp += ('_soak_nightly\' + $prev.Name) }
$cmp += ('_soak_nightly\' + $date)
python docs\tools\heat_compare.py @cmp 2>&1 | Add-Content -Path $report

if ($NoDeploy) { Log 'no deploy (-NoDeploy)'; exit 0 }
if (-not $gates) { Log 'NOT DEPLOYED: a layout gate failed - fix the reported map first'; exit 1 }
if (Get-Process openmohaa -ErrorAction SilentlyContinue) { Log 'NOT DEPLOYED: the game client started during the run'; exit 0 }
Log 'deploy (build.ps1)'
& (Join-Path $dev 'build.ps1') 2>&1 | Select-String 'Packed|FAILED|BLOCKED' | ForEach-Object { Log $_.Line }
Log 'done'
