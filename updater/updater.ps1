# MOH Coop Trilogy - launch-time updater
# Design: _research/auto_update.md section 4. Rules that must never break:
#   1. NEVER block play: any failure -> launch the existing install immediately.
#   2. Never install an unverified file (sha256 checked before any swap).
#   3. Never re-hash the full install at launch: diff remote manifest vs installed_manifest.json.
# Runs hidden via launch_coop.vbs; shows a progress window only when there is work to do.
# Continue, not Stop: native stderr (curl) must never become a terminating error in PS 5.1.
$ErrorActionPreference = "Continue"

$app = Split-Path -Parent $MyInvocation.MyCommand.Path
$log = Join-Path $app "updater.log"

function Log($msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Add-Content -Path $log -Value $line -ErrorAction SilentlyContinue
}

# rolling log: keep it under ~200 KB
try {
    if ((Test-Path $log) -and (Get-Item $log).Length -gt 200KB) {
        Get-Content $log -Tail 200 | Set-Content $log
    }
} catch {}

# ensure Windows saves a crash dump if openmohaa.exe hard-crashes, so Report-a-Problem can attach it.
# Per-user (HKCU) registry, no admin needed; DumpType 1 = minidump (small, has the call stack).
try {
    $wer = "HKCU:\SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps\openmohaa.exe"
    if (-not (Test-Path $wer)) { New-Item -Path $wer -Force | Out-Null }
    $dumps = Join-Path $env:LOCALAPPDATA "CrashDumps"
    if (-not (Test-Path $dumps)) { New-Item -ItemType Directory -Path $dumps -Force | Out-Null }
    New-ItemProperty -Path $wer -Name "DumpFolder" -Value $dumps -PropertyType ExpandString -Force | Out-Null
    New-ItemProperty -Path $wer -Name "DumpType"   -Value 1 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $wer -Name "DumpCount"  -Value 5 -PropertyType DWord -Force | Out-Null
} catch { Log "crash-dump registry setup skipped: $_" }

# single instance: a second double-click must not fight the first - two concurrent
# downloads writing the same .tmp corrupt it (seen in the field 2026-07-05). The first
# instance owns the update AND the game launch; extras just leave.
$updMutex = New-Object System.Threading.Mutex($false, "Local\MOHCoopTrilogyUpdater")
$gotMutex = $false
try { $gotMutex = $updMutex.WaitOne(0) } catch { $gotMutex = $true }  # abandoned = holder died; take over
if (-not $gotMutex) { Log "another updater instance is already running - exiting"; exit }

# --- read updater.ini (written by the installer) ---
$ini = @{}
try {
    foreach ($line in Get-Content (Join-Path $app "updater.ini")) {
        $i = $line.IndexOf('=')
        if ($i -gt 0) { $ini[$line.Substring(0, $i).Trim()] = $line.Substring($i + 1).Trim() }
    }
} catch { Log "updater.ini unreadable: $_" }

function LaunchGame {
    try {
        # never start a second copy (a game launched mid-update, or by another shortcut)
        if (Get-Process openmohaa -ErrorAction SilentlyContinue) { exit }
        $exe = Join-Path $app "openmohaa.exe"
        $args = $ini["LaunchArgs"]
        if (-not $args) {
            # last-resort reconstruction from install_info.txt
            $gog = ""
            $infoFile = Join-Path $app "install_info.txt"
            if (Test-Path $infoFile) {
                $m = Select-String -Path $infoFile -Pattern "^GogPath=(.*)$"
                if ($m) { $gog = $m.Matches[0].Groups[1].Value }
            }
            $args = "+set fs_basepath `"$gog`" +set fs_homepath `"$app\home`" +set com_target_game 2"
        }
        Start-Process -FilePath $exe -ArgumentList $args -WorkingDirectory $app
    } catch {
        Log "LaunchGame FAILED: $_"
    }
    exit
}

# one-time migration: older patches baked the report webhook into report_problem.ps1;
# newer reporters read it from updater.ini. If the ini lacks the key, harvest it from the
# local legacy file BEFORE any update replaces that file with the secret-free version.
try {
    if (-not $ini["ReportWebhook"]) {
        $rp = Join-Path $app "report_problem.ps1"
        if (Test-Path $rp) {
            $m = Select-String -Path $rp -Pattern 'Webhook = "(https://discord[^"]+)"'
            if ($m) {
                $wh = $m.Matches[0].Groups[1].Value
                Add-Content -Path (Join-Path $app "updater.ini") -Value "ReportWebhook=$wh"
                $ini["ReportWebhook"] = $wh
                Log "migrated report webhook into updater.ini"
            }
        }
    }
} catch {}

# safety net: any unexpected terminating error still launches the game (functions above are defined)
trap { Log "UNEXPECTED: $_"; LaunchGame }

# 0. never fight a running game
if (Get-Process openmohaa -ErrorAction SilentlyContinue) { Log "game already running - skip update"; LaunchGame }

$manifestUrl  = $ini["ManifestUrl"]
$fallbackUrl  = $ini["ManifestUrlFallback"]
if (-not $manifestUrl) { Log "no ManifestUrl configured"; LaunchGame }

$curl = "$env:SystemRoot\System32\curl.exe"
if (-not (Test-Path $curl)) { $curl = "curl.exe" }

# 1. fetch remote manifest. Fetch BOTH the primary (GitHub CDN latest/download) and the fallback
# (raw.githubusercontent, git-backed = instant) and use whichever advertises the NEWER version.
# The CDN caches the "latest" redirect per-region and can serve a stale pointer for many minutes
# after a publish; without this a user's updater would see the old version and never update.
$tmpPrimary  = Join-Path $env:TEMP "mohcoop_manifest_p.json"
$tmpFallback = Join-Path $env:TEMP "mohcoop_manifest_f.json"
$tmpManifest = Join-Path $env:TEMP "mohcoop_manifest.json"
Remove-Item $tmpPrimary, $tmpFallback, $tmpManifest -Force -ErrorAction SilentlyContinue

function TryFetch($url, $out) {
    if (-not $url) { return $null }
    & $curl -fsSL --connect-timeout 4 --max-time 20 $url -o $out 2>$null
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $out)) { return $null }
    try { return Get-Content $out -Raw | ConvertFrom-Json } catch { return $null }
}
function VerKey($v) {
    # "1.1.32" -> comparable [version]; tolerates missing/odd values
    try { return [version]("$($v.version)".Trim()) } catch { return [version]"0.0.0" }
}
function SafeRelPath($p) {
    # the updater must never write outside its own install dir: reject absolute/rooted
    # paths and any '..' traversal. This protects the user's GOG install (including a
    # separately installed vanilla OpenMOHAA) from a malformed or tampered manifest.
    if (-not $p) { return $false }
    if ("$p" -match '\.\.') { return $false }
    if ("$p" -match '^[A-Za-z]:' -or "$p".StartsWith('\') -or "$p".StartsWith('/')) { return $false }
    return $true
}

$mp = TryFetch $manifestUrl  $tmpPrimary
$mf = TryFetch $fallbackUrl  $tmpFallback
if (-not $mp -and -not $mf) { Log "manifest fetch failed (offline?)"; LaunchGame }

$remote = $mp
Copy-Item $tmpPrimary $tmpManifest -Force -ErrorAction SilentlyContinue
if (-not $mp -or ($mf -and (VerKey $mf) -gt (VerKey $mp))) {
    $remote = $mf
    Copy-Item $tmpFallback $tmpManifest -Force
    if ($mp) { Log "fallback manifest ($($mf.version)) newer than CDN ($($mp.version)) - using fallback" }
}
if (-not $remote -or $remote.manifestVersion -gt 1) { Log "manifest version unsupported"; LaunchGame }

# 2. diff against the installed manifest (never full-disk hashing)
$installedPath = Join-Path $app "installed_manifest.json"
$installedMap = @{}
if (Test-Path $installedPath) {
    try {
        $inst = Get-Content $installedPath -Raw | ConvertFrom-Json
        foreach ($f in $inst.files) { $installedMap[$f.path] = $f.sha256 }
    } catch { Log "installed manifest unreadable - treating all as unknown" }
}

$work = @()
foreach ($f in $remote.files) {
    if (-not (SafeRelPath $f.path)) { Log "unsafe manifest path skipped: $($f.path)"; continue }
    $diskPath = Join-Path $app ($f.path -replace "/", "\")
    $disk = Get-Item $diskPath -ErrorAction SilentlyContinue
    $known = $installedMap[$f.path]
    if (-not $disk) { $work += $f; continue }
    if ($known -ne $f.sha256) { $work += $f; continue }
    # size sanity only for files users never edit (skip cfg: user settings may legitimately differ)
    if ($f.path -notlike "*.cfg" -and $disk.Length -ne $f.size) { $work += $f }
}
$deletes = @()
if ($remote.delete) { $deletes = @($remote.delete | Where-Object { (SafeRelPath $_) -and (Test-Path (Join-Path $app ($_ -replace "/", "\"))) }) }

if ($work.Count -eq 0 -and $deletes.Count -eq 0) {
    Copy-Item $tmpManifest $installedPath -Force -ErrorAction SilentlyContinue
    # clear the one-shot What's New trigger: the card shows on the first launch after an
    # update and stays hidden from then on (autoexec.cfg execs this file every launch)
    try { Set-Content -Path (Join-Path $app "home\maintt\whatsnew_pending.cfg") -Value "// up to date - no announcement" -Encoding ascii } catch {}
    Log "up to date (v$($remote.version))"
    LaunchGame
}

$totalBytes = ($work | Measure-Object -Property size -Sum).Sum
$totalMB = [math]::Round($totalBytes / 1MB, 1)
Log "update to v$($remote.version): $($work.Count) file(s), $totalMB MB, $($deletes.Count) delete(s)"

# 3. preflight disk space (download volume + 200MB slack)
try {
    $drive = (Get-Item $app).PSDrive
    $freeMB = [math]::Round($drive.Free / 1MB)
    if ($freeMB -lt ($totalMB + 200)) { Log "disk space low ($freeMB MB free) - skipping update"; LaunchGame }
} catch {}

# progress UI (visible only when there is work). TopMost so it cannot open buried behind
# other windows, and the download loop pumps messages so it never ghosts to "Not Responding".
$ui = $null
try {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $form = New-Object System.Windows.Forms.Form
    $form.Text = "MOH Coop Trilogy - updating to v$($remote.version)"
    $form.Size = New-Object System.Drawing.Size(480, 140)
    $form.StartPosition = "CenterScreen"
    $form.FormBorderStyle = "FixedDialog"
    $form.MaximizeBox = $false
    $form.TopMost = $true
    $form.ControlBox = $false   # no X: closing would not stop the update anyway
    $label = New-Object System.Windows.Forms.Label
    $label.Location = New-Object System.Drawing.Point(12, 15)
    $label.Size = New-Object System.Drawing.Size(440, 34)
    $label.Text = "Preparing... ($totalMB MB). The game starts by itself when this is done."
    $bar = New-Object System.Windows.Forms.ProgressBar
    $bar.Location = New-Object System.Drawing.Point(12, 58)
    $bar.Size = New-Object System.Drawing.Size(440, 24)
    $bar.Maximum = [int][math]::Max([math]::Ceiling($totalBytes / 1KB), 1)
    $form.Controls.Add($label); $form.Controls.Add($bar)
    $form.Show(); $form.Refresh()
    [System.Windows.Forms.Application]::DoEvents()
    $ui = @{ form = $form; label = $label; bar = $bar }
} catch { $ui = $null }

function Set-Progress($doneKB, $text) {
    if ($ui) {
        try {
            $ui.bar.Value = [math]::Min([int]$doneKB, $ui.bar.Maximum)
            $ui.label.Text = $text
            [System.Windows.Forms.Application]::DoEvents()
        } catch {}
    }
}

# 4. download everything to .tmp first, verify each. curl runs as a child process while
# this loop keeps the window painted and shows real byte progress.
$doneBytes = 0
$idx = 0
foreach ($f in $work) {
    $idx++
    $diskPath = Join-Path $app ($f.path -replace "/", "\")
    $tmpPath = "$diskPath.tmp"
    $dir = Split-Path -Parent $diskPath
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $name = Split-Path -Leaf $f.path
    $fileMB = [math]::Round($f.size / 1MB, 1)

    $ok = $false
    foreach ($attempt in 1..2) {
        # a complete .tmp from an earlier interrupted run needs no download - just verification
        # (also avoids curl failing a resume of an already-complete file with HTTP 416)
        $have = 0
        if (Test-Path $tmpPath) { $have = (Get-Item $tmpPath).Length }
        if ($have -lt $f.size) {
            Log "downloading $($f.path) from $($f.url)"
            $curlArgs = "-fsL --retry 3 --retry-delay 2 -C - -o `"$tmpPath`" `"$($f.url)`""
            $p = Start-Process -FilePath $curl -ArgumentList $curlArgs -WindowStyle Hidden -PassThru
            while (-not $p.HasExited) {
                $cur = 0
                try { $cur = (Get-Item $tmpPath -ErrorAction SilentlyContinue).Length } catch {}
                $overall = $doneBytes + $cur
                Set-Progress ($overall / 1KB) ("Downloading $name  ($fileMB MB)  [file $idx of $($work.Count)]`n" +
                    "$([math]::Round($overall/1MB)) / $([math]::Round($totalBytes/1MB)) MB total")
                Start-Sleep -Milliseconds 250
            }
            if ($p.ExitCode -ne 0) {
                # resume of an already-complete file reports an error - let the hash decide then
                $have = 0
                if (Test-Path $tmpPath) { $have = (Get-Item $tmpPath).Length }
                if ($have -lt $f.size) { Log "curl exit $($p.ExitCode) on $($f.path) (attempt $attempt)"; continue }
            }
        } else {
            Log "reusing complete download for $($f.path)"
        }
        $fh = Get-FileHash -Path $tmpPath -Algorithm SHA256 -ErrorAction SilentlyContinue
        if ($fh -and $fh.Hash.ToLower() -eq $f.sha256.ToLower()) { $ok = $true; break }
        Log "hash mismatch on $($f.path) (attempt $attempt) - re-downloading from scratch"
        Remove-Item $tmpPath -Force -ErrorAction SilentlyContinue
    }
    if (-not $ok) {
        Log "download failed for $($f.path) - aborting update, launching existing install"
        if ($ui) { try { $ui.form.Close() } catch {} }
        LaunchGame
    }
    $doneBytes += $f.size
    Set-Progress ($doneBytes / 1KB) "Verified $name  [$idx/$($work.Count)]"
}

# if the game was started while we downloaded, do not swap files under it; the verified
# .tmp files stay put and the next launch applies them without re-downloading.
if (Get-Process openmohaa -ErrorAction SilentlyContinue) {
    Log "game started during download - update will apply on next launch"
    if ($ui) { try { $ui.form.Close() } catch {} }
    exit
}

# 5. swap: content first, engine binary group last (all verified, game not running)
Set-Progress ($totalBytes / 1KB) "Applying update..."
$engineFirst = @("openmohaa.exe", "cgame.dll", "game.dll", "renderer_opengl1.dll", "renderer_opengl2.dll")
$ordered = @($work | Where-Object { $engineFirst -notcontains $_.path }) + @($work | Where-Object { $engineFirst -contains $_.path })
foreach ($f in $ordered) {
    $diskPath = Join-Path $app ($f.path -replace "/", "\")
    $tmpPath = "$diskPath.tmp"
    $moved = $false
    foreach ($try in 1..3) {
        try { Move-Item -Force $tmpPath $diskPath -ErrorAction Stop; $moved = $true; break }
        catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $moved) { Log "SWAP FAILED for $($f.path) - next launch will retry"; if ($ui) { try { $ui.form.Close() } catch {} }; LaunchGame }
}
foreach ($d in $deletes) {
    Remove-Item (Join-Path $app ($d -replace "/", "\")) -Force -ErrorAction SilentlyContinue
    Log "retired $d"
}

# 6. persist state, then play
Copy-Item $tmpManifest $installedPath -Force
# arm the in-game What's New card (ui/coop_whatsnew.urc, changelog baked into the pk3 we just
# installed): autoexec.cfg execs this cfg every launch; the wait defers the pushmenu until the
# main menu is up. The next up-to-date launch rewrites this file empty = shown once per update.
try {
    Set-Content -Path (Join-Path $app "home\maintt\whatsnew_pending.cfg") -Value @"
// one-shot post-update announcement (cleared by the next up-to-date launch)
wait 300
pushmenu coop_whatsnew
"@ -Encoding ascii
} catch {}
Log "updated to v$($remote.version) OK"
if ($ui) { try { $ui.form.Close() } catch {} }
# always confirm a completed update with the version received - shown even when the
# progress-bar UI could not open. Auto-dismisses after 15s so it can never block play.
try {
    $pop = New-Object -ComObject WScript.Shell
    [void]$pop.Popup("MOH Coop Trilogy updated to v$($remote.version).`n`nThe game will now start.", 15, "MOH Coop Trilogy - Update Complete", 64)
} catch {}
LaunchGame
