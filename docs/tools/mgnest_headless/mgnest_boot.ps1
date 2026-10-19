# [bug-2976] Headless MG42-nest gunner rig: does a mounted gunner stay on his gun under enemy fire?
#
# Boots a PRIVATE omohaaded copy (never the live install's exe, never port 12203) in coop with bots,
# with a private homepath whose maintt\ carries the rig script and any loose working-tree overrides
# (loose homepath files beat the basepath pk3, so unbuilt script changes can be tested without
# build.ps1). Then start the rig over rcon (it needs cheats, which developer 1 keeps on):
#
#   python docs\tools\rcon.py --port 12291 --pw mgtest --timeout 20 "script turret3 exec coop_mod/zz_mgtest.scr"
#
# `script <targetname> exec <file>` runs the file from the top; `thread <file>::<label>` fails with
# "current thread is NULL" from the console, and exec does not take a ::label. On a map without a
# $turret3 use any entity targetname, or *<entnum>.
# Summarise:  python docs\tools\mgnest_headless\mgt_summary.py <HomeDir>\maintt\qconsole.log
#
# The rig is written for m4l1 (baked build-mode nest coop_mgnest1 + vanilla $turret3/$turret4); on
# another map it still places and tracks its own nest (the build-mode path) and skips what is absent.
#
#   powershell -File docs\tools\mgnest_headless\mgnest_boot.ps1 -DedDir <dir with omohaaded.exe+game.dll+DLLs> `
#       -HomeDir <private dir> [-Map m4l1] [-Bots 4] [-Loose coop_mod/officer.scr] [-Extra "+set,mgt_godgunners,1"]
#
# Rig cvars (pass through -Extra):
#   mgt_godgunners 1   tracked gunners take no damage (armed bots otherwise kill a 5-hp gunner in seconds)
#   mgt_fixcheck 1     prints coop_isMannedGunner per gunner, i.e. proves the patched officer.scr loaded
param(
    [Parameter(Mandatory = $true)][string]$DedDir,
    [Parameter(Mandatory = $true)][string]$HomeDir,
    [string]$Map = 'm4l1',
    [int]$Port = 12291,
    [int]$Bots = 4,
    [string[]]$Loose = @(),
    [string]$Extra = '',
    [string]$Base = 'G:\mohaa-gl2',
    [string]$ModRoot = 'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'
)
$ErrorActionPreference = 'Stop'
$Exe = Join-Path $DedDir 'omohaaded.exe'
if (-not (Test-Path $Exe)) { throw "no omohaaded.exe in $DedDir - copy omohaaded.exe, game.dll, OpenAL64.dll, SDL2.dll, libcurl.dll from $Base" }
if ((Resolve-Path $DedDir).Path -eq (Resolve-Path $Base).Path) { throw 'DedDir must be a PRIVATE copy, not the live install' }
$mt = Join-Path $HomeDir 'maintt'
New-Item -ItemType Directory -Force (Join-Path $mt 'coop_mod') | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'zz_mgtest.scr') (Join-Path $mt 'coop_mod\zz_mgtest.scr') -Force
foreach ($rel in $Loose) {
    $dst = Join-Path $mt $rel
    New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
    Copy-Item (Join-Path $ModRoot $rel) $dst -Force
    "loose override: $rel"
}
$log = Join-Path $mt 'qconsole.log'
Remove-Item $log -ErrorAction SilentlyContinue
$a = @(
  '+set','com_target_game','2','+set','dedicated','1',
  '+set','fs_basepath',$Base,'+set','fs_homepath',$HomeDir,
  '+set','net_port',"$Port",'+set','sv_maxclients','8',
  '+set','g_gametype','2','+set','developer','1','+set','logfile','2','+set','sv_fps','20',
  '+set','rconpassword','mgtest',
  '+set','sv_maxbots',"$Bots",'+set','sv_numbots',"$Bots",
  '+set','coop_st_autodeploy','1',
  # coop_probe is 0 by default since 2026-09-27 (docs/proposals/console_quiet_2026-09-27): the
  # rig reads PRB records, so it turns the bus on itself (actor + census = 129).
  '+set','coop_probe','129',
  '+set','coop_probeFilter','gunner','+set','coop_probeInterval','5'
)
if ($Extra) { $a += ($Extra -split ',') }
$a += @('+map', $Map)
$p = Start-Process $Exe -ArgumentList $a -WorkingDirectory $DedDir -PassThru -WindowStyle Hidden
"PID $($p.Id)  log $log"
exit 0
