# MOH Coop Trilogy - gl2 A/B screenshot sweep (HARDENED)
# Usage:  .\tools\gl2_ab_sweep.ps1 [-MapList tools\gl2_ab_maps.txt] [-DryRun]
#
# Captures side-by-side screenshots of each map under several renderer configs (gl1 vs
# gl2-default vs gl2-upgraded) so you can judge which gl2 wins are worth shipping.
#
# WHY THIS REWRITE EXISTS - it designs out the three failures the 07-2x sweep hit:
#   1. TWO SWEEPS AT ONCE. The old runaway (pids 579301 + 581530) came from a second sweep
#      launching while the first was still alive. Each sweep killed openmohaa *by name*, so they
#      cross-killed each other's boots mid-load -> both saw failures -> both respawned -> cascade
#      and process accumulation. FIX: a single global mutex. A second instance refuses to start.
#   2. KILL BY NAME. FIX: we only ever kill the exact PID *we* launched (and its child tree).
#      A stray play session or another tool's openmohaa is never touched.
#   3. taskkill LEFT HUNG PROCS. The old code's Kill used taskkill, which didn't force-terminate
#      hung instances. FIX: Stop-Process -Force with empty-pipeline guards (this is what actually
#      cleared them), mirroring the proven fourbot_combat.ps1 shutdown (window close -> force kill).
#   Plus a per-boot WATCHDOG: a boot that never produces a screenshot within -BootTimeoutSec is
#   force-killed and recorded as a miss, so one modal-hung map (the old m4/m5 NO-SPAWN hangs) can
#   no longer wedge the whole run into an endless completion-waiter.
#
# NOTE: this harness is UNTESTED here (built off-machine). The process-management skeleton is the
# hardened part; the in-engine CAPTURE step (how openmohaa loads a map, screenshots, and quits) is
# templated below and marked - confirm it matches how your original sweep drove the engine, then
# run once with -DryRun before a real sweep.
param(
    [string]$MapList        = "$PSScriptRoot\gl2_ab_maps.txt",
    [string]$OutDir         = "C:\mohaa-coop-dev\gl2_ab",
    [string]$Gog            = "G:\GOG\Medal of Honor - Allied Assault War Chest",
    [string]$ShotDir        = "$env:APPDATA\openmohaa\maintt\screenshots",
    [string]$UpgradeCfg     = "$PSScriptRoot\gl2_upgrades.cfg",
    [int]$DwellSec          = 8,     # in-map settle before the shot
    [int]$BootTimeoutSec    = 90,    # hang watchdog: force-kill a boot that never captures
    [string[]]$Configs      = @("gl1","gl2-default","gl2-upgraded"),
    [switch]$Force,                  # run even if an openmohaa is already up (still never killed by name)
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"

# --- 1. single-instance guard (root-cause #1) -------------------------------------------------
# A named mutex is released automatically if this process dies, so there is no stale-lock problem
# the way a lockfile has. A second sweep simply cannot acquire it and exits.
$created = $false
$mutex = New-Object System.Threading.Mutex($true, "Global\mohaa_gl2_ab_sweep", [ref]$created)
if (-not $created) {
    throw "another gl2_ab_sweep is already running - refusing to start a second one (this is the exact concurrent-sweep bug that caused the runaway). Stop the other one first."
}

# --- helpers ----------------------------------------------------------------------------------
# Kill ONLY the process tree we launched. Never Get-Process -Name openmohaa (root-cause #2).
function Stop-Tree([System.Diagnostics.Process]$proc) {
    if (-not $proc -or $proc.HasExited) { return }
    $kids = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$($proc.Id)" -ErrorAction SilentlyContinue)
    foreach ($k in $kids) { try { Stop-Process -Id $k.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }
    try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}   # -Force = the fix
    try { [void]$proc.WaitForExit(5000) } catch {}
}

# Wait until a NEW screenshot lands, or the watchdog fires. Returns the new file, or $null on timeout.
function Wait-Shot([string]$dir, [datetime]$since, [int]$timeoutSec) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        $shot = @(Get-ChildItem -Path $dir -Filter *.jpg -ErrorAction SilentlyContinue |
                  Where-Object { $_.LastWriteTime -gt $since } |
                  Sort-Object LastWriteTime -Descending) | Select-Object -First 1   # empty-pipeline safe
        if ($shot) { return $shot }
        Start-Sleep -Milliseconds 500
    }
    return $null
}

try {
    $exe = Join-Path $Gog "openmohaa.exe"
    if (-not (Test-Path $exe))     { throw "openmohaa.exe not found at $exe" }
    if (-not (Test-Path $MapList)) { throw "map list not found: $MapList" }
    if (-not (Test-Path $UpgradeCfg)) { throw "gl2 upgrade cfg not found: $UpgradeCfg" }

    # Refuse to trample a real play session. We do NOT auto-kill by name (that is the bug); we abort
    # and let you close it, unless you explicitly pass -Force.
    $existing = @(Get-CimInstance Win32_Process -Filter "Name='openmohaa.exe'" -ErrorAction SilentlyContinue)
    if ($existing.Count -gt 0 -and -not $Force) {
        throw "$($existing.Count) openmohaa.exe already running. Close it first (or pass -Force). This harness will never kill an openmohaa it did not launch."
    }

    $maps = @(Get-Content $MapList | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith('#') })
    if ($maps.Count -eq 0) { throw "no maps in $MapList" }
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
    New-Item -ItemType Directory -Path $ShotDir -Force | Out-Null

    Write-Host ("== gl2 A/B sweep: {0} map(s) x {1} config(s) = {2} shots ==" -f $maps.Count, $Configs.Count, ($maps.Count * $Configs.Count))
    if ($DryRun) {
        foreach ($m in $maps) { foreach ($c in $Configs) { Write-Host ("  would capture  {0,-12} {1}" -f $m, $c) } }
        Write-Host "DRY RUN - nothing launched."
        return
    }

    $results = @()
    foreach ($map in $maps) {
        foreach ($cfg in $Configs) {
            # --- build the per-shot boot cfg (CAPTURE STEP - confirm against your setup) ----------
            # Renderer + cvar leg for this config. cl_renderer needs a fresh start, which is exactly
            # what each boot is. gl2-upgraded pulls in the confirmed wins from gl2_upgrades.cfg.
            $lines = switch ($cfg) {
                "gl1"          { @('seta cl_renderer "opengl1"') }
                "gl2-default"  { @('seta cl_renderer "opengl2"') }
                "gl2-upgraded" { @("exec `"$UpgradeCfg`"") }   # sets opengl2 + r_ssao/r_sunShadows/etc.
            }
            # load map, let it settle, screenshot, quit. Tune the dwell/mechanism to your capture
            # method (the mod's coop_maptest mode is an alternative auto-driver).
            $lines += @(
                "map $map",
                "wait $([int]($DwellSec * 20))",   # ~20 server frames/sec at sv_fps 40 is approximate
                "screenshot",
                "wait 40",
                "quit"
            )
            $bootCfg = Join-Path $env:TEMP ("gl2ab_{0}_{1}.cfg" -f $map, $cfg)
            Set-Content -Path $bootCfg -Value $lines -Encoding ascii

            $since = Get-Date
            Write-Host ("  [{0,-12}] {1} ..." -f $map, $cfg) -NoNewline
            $proc = Start-Process -FilePath $exe -PassThru -WorkingDirectory $Gog `
                        -ArgumentList @("+set","fs_game","maintt","+exec","`"$bootCfg`"")

            $shot = Wait-Shot -dir $ShotDir -since $since -timeoutSec $BootTimeoutSec
            Stop-Tree $proc                       # always PID-scoped, always -Force
            Remove-Item $bootCfg -ErrorAction SilentlyContinue

            if ($shot) {
                $dest = Join-Path $OutDir ("{0}__{1}.jpg" -f $map, $cfg)
                Move-Item $shot.FullName $dest -Force
                Write-Host " ok" -ForegroundColor Green
                $results += [pscustomobject]@{ map = $map; config = $cfg; status = "ok"; file = $dest }
            } else {
                Write-Host (" TIMEOUT (>{0}s) - skipped" -f $BootTimeoutSec) -ForegroundColor Yellow
                $results += [pscustomobject]@{ map = $map; config = $cfg; status = "timeout"; file = $null }
            }
        }
    }

    # --- summary ------------------------------------------------------------------------------
    $ok = @($results | Where-Object status -eq "ok").Count
    $to = @($results | Where-Object status -eq "timeout").Count
    Write-Host ""
    Write-Host ("== done: {0} captured, {1} timed out -> {2} ==" -f $ok, $to, $OutDir)
    if ($to -gt 0) {
        Write-Host "timed-out shots (likely modal-hung maps - capture these manually):" -ForegroundColor Yellow
        $results | Where-Object status -eq "timeout" | ForEach-Object { Write-Host ("   {0} / {1}" -f $_.map, $_.config) }
    }
}
finally {
    # Always release the single-instance lock, even on Ctrl-C / throw, so the NEXT run can start.
    try { $mutex.ReleaseMutex() } catch {}
    $mutex.Dispose()
}
