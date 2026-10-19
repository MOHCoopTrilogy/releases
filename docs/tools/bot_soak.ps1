# [user 2026-09-21] Headless bot SOAK harness for the push campaign maps.
# Boots omohaaded per map in PUSH mode with N bots, logs per-bot position/speed/blocks via the engine's
# `bot_probe` marker (^~^~^ BOTPROBE), soaks for the requested minutes, stops, and saves the log. Runs on a
# SEPARATE port + homepath so it never collides with the user's listen client on 12203 or its logs.
#
# Analyse with:  python docs/tools/bot_soak_analyze.py <OutDir>
#
#   powershell -File docs/tools/bot_soak.ps1 -Minutes 15                     # full 24-map soak
#   powershell -File docs/tools/bot_soak.ps1 -Maps m1l2b -Minutes 3          # quick validation
param(
    # 23 Push maps (m5l3 Rocket Facility pulled from Push, bug-2832; m5l2b pulled, bug-2747)
    [string[]]$Maps = @('m1l2b','m2l1','m3l3','m4l1','m4l2','m5l1a','m5l1b','t3l1','t2l1','t2l3','t2l4',
                        'm5l2a','m3l1b','m2l3','m1l3a','m1l3b','e1l1','e3l1','e3l2','e3l3','t1l1','t1l2','t1l3'),
    [int]$Minutes = 15,
    [int]$Bots = 10,
    [int]$Port = 12250,
    [int]$ProbeMs = 2000,
    [int]$Lookahead = 460,
    [string]$OutDir = 'C:\mohaa-coop-dev\_soak',
    [switch]$BlockLog,
    # Install to boot omohaaded from. Default is the live install; pass the GOG root
    # ('G:\GOG\Medal of Honor - Allied Assault War Chest') to soak while the user's client is running from
    # G:\mohaa-gl2 - its game.dll is then locked, so a new build can only be tested from the parallel GOG copy.
    [string]$Base = 'G:\mohaa-gl2',
    # Extra console args appended before +map, comma-joined for non-PowerShell callers, e.g. "+set,nav_dump,1"
    [string]$Extra = '',
    # a separate server folder (and -Port) lets a second soak run beside a long one without clobbering its log
    [string]$SoakDir = 'C:\mohaa-coop-dev\server_home_soak'
)

$ErrorActionPreference = 'Stop'
# allow "-Maps m4l2,e3l2" passed as a single comma-joined token (e.g. from a non-PowerShell caller)
if ($Maps.Count -eq 1 -and $Maps[0] -match ',') { $Maps = $Maps[0] -split ',' }
$Exe  = Join-Path $Base 'omohaaded.exe'
$SoakHome = $SoakDir
$Log  = Join-Path $SoakHome 'maintt\qconsole.log'

New-Item -ItemType Directory -Force $OutDir | Out-Null
New-Item -ItemType Directory -Force (Join-Path $SoakHome 'maintt') | Out-Null

# make sure no stray soak server is up on our port
Get-Process omohaaded -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $Exe } | ForEach-Object {
    # only kill ones we might have started; safest is to leave the user's other servers alone, but a soak
    # server on our dedicated port must be clear. The harness owns $Port, so kill any omohaaded (the fleet is
    # expected down during a soak). If the user is running their own, they'll be told to stop first.
}

$summary = @()
foreach ($m in $Maps) {
    # RESUME: skip a map already captured in this OutDir (so the run can be paused for a deploy and re-launched)
    $dest = Join-Path $OutDir ($m + '.log')
    if (Test-Path $dest) {
        $have = (Select-String -Path $dest -Pattern 'BOTPROBE' -SimpleMatch -ErrorAction SilentlyContinue).Count
        if ($have -gt 50) { Write-Host ("=== SKIP {0} (already have {1} probes) ===" -f $m, $have); continue }
    }
    Write-Host ("=== SOAK {0}  ({1} bots, {2} min, port {3}) ===" -f $m, $Bots, $Minutes, $Port)
    Remove-Item $Log -ErrorAction SilentlyContinue

    $botArgs = @(
        '+set','com_target_game','2','+set','dedicated','1',
        '+set','fs_basepath',$Base,'+set','fs_homepath',$SoakHome,
        '+set','net_port',"$Port",'+set','sv_maxclients','20',
        '+set','g_gametype','2','+set','developer','1','+set','logfile','2','+set','sv_fps','40',
        '+set','sv_maxbots',"$Bots",'+set','coop_mpBotFill',"$Bots",'+set','sv_numbots',"$Bots",
        '+set','coop_mpMode','push','+set','coop_mpPushRotate','0','+set','coop_mpPushTestPool','0',
        '+set','sv_mpForceArena','1',
        '+set','bot_probe',"$ProbeMs",'+set','bot_lookahead',"$Lookahead"
    )
    if ($BlockLog) { $botArgs += @('+set','bot_blocklog','1') }
    if ($Extra) { $botArgs += ($Extra -split ',') }
    $botArgs += @('+map',"$m")
    $proc = Start-Process $Exe -ArgumentList $botArgs -PassThru -WindowStyle Hidden
    $deadline = (Get-Date).AddMinutes($Minutes)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 15
        if ($proc.HasExited) { Write-Host ("  server EXITED early on {0}" -f $m); break }
    }
    if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
    Start-Sleep -Seconds 3

    if (Test-Path $Log) {
        $dest = Join-Path $OutDir ($m + '.log')
        Copy-Item $Log $dest -Force
        $n = (Select-String -Path $dest -Pattern 'BOTPROBE' -SimpleMatch).Count
        Write-Host ("  saved {0}  ({1} BOTPROBE lines)" -f $dest, $n)
        $summary += [pscustomobject]@{ Map=$m; Probes=$n }
    } else {
        Write-Host ("  NO LOG for {0}" -f $m)
        $summary += [pscustomobject]@{ Map=$m; Probes=0 }
    }
}
Write-Host '=== SOAK COMPLETE ==='
$summary | Format-Table -AutoSize
Write-Host ("Analyse: python docs/tools/bot_soak_analyze.py {0}" -f $OutDir)
