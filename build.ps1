Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$srcDir     = "C:\mohaa-coop-dev\hzm-mohaa-coop-mod"

# [user 2026-08-05] PARSE-KILLER GATE (detector rank 1, static half): a single BOM/em-dash/odd
# quote silently kills a whole .scr - the map then runs with no script. Never ship one again.
python "C:\mohaa-coop-dev\docs\tools\scrlint.py" $srcDir
if ($LASTEXITCODE -ne 0) { exit 1 }
# An assignment with no value parses as 'take the next statement as the value' and then
# dies on that statement's own '=', killing the WHOLE file (bug-1908). scrlint cannot see
# it: the braces balance and there is no BOM.
python "C:\mohaa-coop-dev\docs\tools\check_empty_rhs.py" $srcDir
if ($LASTEXITCODE -ne 0) { exit 1 }
# A tik naming a surface its mesh does not have leaves that surface untextured AND kills
# every frame command targeting it - which is how the Panzerfaust lost its fire animation
# commands for a whole session while the engine printed the reason on every load (bug-1912).
python "C:\mohaa-coop-dev\docs\tools\check_tik_surfaces.py" $srcDir
if ($LASTEXITCODE -ne 0) { exit 1 }

# [user 2026-08-18] DRIFT GATES ("how can we ensure we do not miss anything like that again"):
# every cross-source invariant gets an audit that BLOCKS the deploy. unlock_audit = every roster
# gun has an enforced path (free/challenge/rank) and the hover text matches it (7 hovers lied for
# weeks). ads_audit = every aimable gun resolves to a sight tune (exact/strip/donor).
python "C:\mohaa-coop-dev\docs\tools\unlock_audit.py"
if ($LASTEXITCODE -ne 0) { Write-Host "BUILD BLOCKED by unlock_audit" -ForegroundColor Red; exit 1 }
python "C:\mohaa-coop-dev\docs\tools\ads_audit.py"
if ($LASTEXITCODE -ne 0) { Write-Host "BUILD BLOCKED by ads_audit" -ForegroundColor Red; exit 1 }
# [user 2026-08-18] WIRING GATE: every exec resolves to a real file (exact case), every vstr
# in our namespaces is assigned somewhere, every bus token is registered AND dispatched.
python "C:\mohaa-coop-dev\docs\tools\ui_wiring_audit.py"
if ($LASTEXITCODE -ne 0) { Write-Host "BUILD BLOCKED by ui_wiring_audit" -ForegroundColor Red; exit 1 }
# [user 2026-08-18] SR pages are DERIVED, so derive them on every build - the checked-in copy
# shipped 3 ghost challenge rows for days because regeneration relied on memory. Idempotent and
# fast; a failure blocks the deploy like any other gate.
python "C:\mohaa-coop-dev\docs\tools\gen_service_record.py" build
if ($LASTEXITCODE -ne 0) { Write-Host "BUILD BLOCKED by gen_service_record" -ForegroundColor Red; exit 1 }
# [user 2026-08-18] variant->base reverse map, derived from the skin table on every build
python "C:\mohaa-coop-dev\docs\tools\gen_skinbase.py"
if ($LASTEXITCODE -ne 0) { Write-Host "BUILD BLOCKED by gen_skinbase" -ForegroundColor Red; exit 1 }

if ($LASTEXITCODE -ne 0) { Write-Host "BUILD BLOCKED by scrlint" -ForegroundColor Red; exit 1 }
$deployDir  = "G:\GOG\Medal of Honor - Allied Assault War Chest\maintt"
$appDataDir = "$env:APPDATA\openmohaa\maintt"
$gogRoot    = "G:\GOG\Medal of Honor - Allied Assault War Chest"
$cfgSrc     = Join-Path $srcDir "autoexec.cfg"
$cacheDir   = "C:\mohaa-coop-dev\build_out"   # last-built pk3 per bucket + input digest

# Packing must be DETERMINISTIC (bug-237): auto-update asset reuse compares pk3 sha256
# against the released manifest, so an unchanged bucket must produce the identical file.
# Rules: sorted entries, entry mtime = source file mtime (never "now"), git files excluded,
# and a digest cache that skips repacking entirely when a bucket's inputs are unchanged.
$packerVersion = "packer-v2-mtime-sorted-gitless"

# --- 3-way pk3 split (auto-update research, _research/auto_update.md section 5) ---
# Load order preserved: assets_snd < assets_tex < code (ASCII), all in the monolith's old
# alphabetical slot between zzzzzz-HRRTM_* and zzzzzz_hd_*. Code overrides assets.
$oldMonolith = "zzzzzz_co-op_hzm_mod_mohaa.pk3"
$paks = @(
    @{ Name = "zzzzzz_co-op_hzm_mod_assets_snd.pk3"; Dirs = @("sound") },
    @{ Name = "zzzzzz_co-op_hzm_mod_assets_tex.pk3"; Dirs = @("textures","models","gfx","env") },
    @{ Name = "zzzzzz_co-op_hzm_mod_code.pk3";       Dirs = @() }   # everything else (catch-all)
)
$assetDirs = @("sound","textures","models","gfx","env")
$excludeTop = @("_notes", "_research")   # dev notes + research (pipelines, retail extracts) never ship
$excludeNames = @(".gitignore", ".gitattributes", "README.md")   # repo housekeeping never ships

# HZM coop [user 2026-08-24] NEVER SHIP THE PRE-UPSCALE BACKUPS.
# 1,252 files / 200 MiB on disk / ~87 MiB inside zzzzzz_co-op_hzm_mod_assets_tex.pk3 were packed and
# pushed to every client on connect, for art the engine can NEVER load - ".pre_upscale_nobuild" is
# not an extension R_LoadImage ever probes (it tries .dds, .jpg, .tga and stops).
# The filenames literally end in "nobuild", so the intent to exclude them was DOCUMENTED IN THE NAME
# and never implemented anywhere. A convention nothing enforces is not a rule.

function Get-TopDir($relPath) {
    $i = $relPath.IndexOf('/')
    if ($i -lt 0) { return "" }
    return $relPath.Substring(0, $i)
}

# NEVER deploy under a running game: the engine memory-maps the pk3s at launch, and
# overwriting them mid-session makes it read garbage at stale offsets (bug-241: phantom
# 'label does not exist' errors and a watchdog server crash mid-playtest).
$clientRunning = Get-CimInstance Win32_Process -Filter "Name='openmohaa.exe'" | Where-Object { $_.CommandLine -notlike '*dedicated 1*' }
if ($clientRunning) {
    Write-Host 'ABORTED: openmohaa.exe is running - close the game before deploying.' -ForegroundColor Red
    exit 1
}

Write-Host "Packing $srcDir (3-way split, deterministic)..."
if (-not (Test-Path $cacheDir)) { New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null }
$allFiles = Get-ChildItem -Path $srcDir -Recurse -File | Where-Object {
    $_.Extension -ne '.bak' -and $_.Extension -ne '.pk3' -and
    $_.FullName -notmatch '\\\.git(\\|$)' -and
    $excludeNames -notcontains $_.Name -and
    $_.Name -notlike '*.pre_upscale_nobuild'
}

# bucket files
$buckets = @{}
foreach ($p in $paks) { $buckets[$p.Name] = New-Object System.Collections.ArrayList }
foreach ($file in $allFiles) {
    $rel = $file.FullName.Substring($srcDir.Length + 1).Replace('\', '/')
    $top = Get-TopDir $rel
    if ($excludeTop -contains $top) { continue }
    if ($top -eq "sound") { [void]$buckets[$paks[0].Name].Add(@($rel, $file)) }
    elseif ($assetDirs -contains $top) { [void]$buckets[$paks[1].Name].Add(@($rel, $file)) }
    else { [void]$buckets[$paks[2].Name].Add(@($rel, $file)) }
}

$sha = [System.Security.Cryptography.SHA256]::Create()
foreach ($p in $paks) {
    $list = @($buckets[$p.Name] | Sort-Object { $_[0] })
    # input digest: relpath|size|mtime of every member (this is exactly what the zip stores,
    # so digest-equal implies byte-equal output)
    $lines = @($packerVersion) + @($list | ForEach-Object { "{0}|{1}|{2}" -f $_[0], $_[1].Length, $_[1].LastWriteTimeUtc.Ticks })
    $digest = [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes(($lines -join "`n")))).Replace("-", "").ToLower()

    $outPath   = Join-Path $srcDir $p.Name
    $cachePk3  = Join-Path $cacheDir $p.Name
    $cacheSig  = Join-Path $cacheDir ($p.Name + ".inputs")
    $cachedSig = if (Test-Path $cacheSig) { (Get-Content $cacheSig -Raw).Trim() } else { "" }

    if ($cachedSig -eq $digest -and (Test-Path $cachePk3)) {
        Copy-Item $cachePk3 $outPath -Force
        $sizeMB = [math]::Round((Get-Item $outPath).Length / 1MB, 2)
        Write-Host ("  Cache hit  {0} files -> {1} ({2} MB, unchanged)" -f $list.Count, $p.Name, $sizeMB)
        continue
    }

    $stream  = [System.IO.File]::Open($outPath, [System.IO.FileMode]::Create)
    $archive = New-Object System.IO.Compression.ZipArchive($stream, [System.IO.Compression.ZipArchiveMode]::Create)
    foreach ($pair in $list) {
        $entry = $archive.CreateEntry($pair[0], [System.IO.Compression.CompressionLevel]::Optimal)
        $entry.LastWriteTime = [DateTimeOffset]$pair[1].LastWriteTime   # source mtime, not build time
        $es = $entry.Open()
        $fs = [System.IO.File]::OpenRead($pair[1].FullName)
        $fs.CopyTo($es)
        $fs.Dispose()
        $es.Dispose()
    }
    $archive.Dispose()
    $stream.Dispose()
    Copy-Item $outPath $cachePk3 -Force
    Set-Content -Path $cacheSig -Value $digest -Encoding ascii
    $sizeMB = [math]::Round((Get-Item $outPath).Length / 1MB, 2)
    Write-Host ("  Packed {0} files -> {1} ({2} MB)" -f $list.Count, $p.Name, $sizeMB)
}
$sha.Dispose()

# --- Deploy pk3s to both targets; retire the old monolith ---
foreach ($destDir in @($deployDir, $appDataDir)) {
    foreach ($p in $paks) {
        Copy-Item -Path (Join-Path $srcDir $p.Name) -Destination (Join-Path $destDir $p.Name) -Force
    }
    $mono = Join-Path $destDir $oldMonolith
    if (Test-Path $mono) {
        Remove-Item $mono -Force -Confirm:$false
        Write-Host "  Retired old monolith -> $mono"
    }
    # [2026-08-28] The CC0 terrain replacement pak. Built out-of-band by
    # docs/tools/build_terrain_pack.py (it downloads from ambientCG), so it is copied rather than
    # repacked here. THE NAME IS LOAD-BEARING: paks sort alphabetically and the LAST one wins, and the
    # HD packs reach zzzzzzzz_hd_seamfix (eight z). Nine beats it. Rename this below that and the
    # AI-upscaled ground silently wins again with no error anywhere.
    $terrainPak = Join-Path $srcDir 'zzzzzzzzz_coop_terrain.pk3'
    if (Test-Path $terrainPak) {
        Copy-Item -Path $terrainPak -Destination (Join-Path $destDir 'zzzzzzzzz_coop_terrain.pk3') -Force
        Write-Host "  Deployed terrain pak -> $destDir"
    }
    Write-Host "  Deployed 3 pk3s -> $destDir"
}

# --- Deploy cfgs. THREE targets: the live launch profile uses fs_homepath G:\mohaa-gl2\home, and a
#     homepath cfg SHADOWS the basepath copy - stale cfgs there silently ate deployed changes (bug-1633). ---
$gl2HomeDir = "G:\mohaa-gl2\home\maintt"
$cfgTargets = @($deployDir, $appDataDir)
if (Test-Path $gl2HomeDir) { $cfgTargets += $gl2HomeDir }
foreach ($destDir in $cfgTargets) {
    Copy-Item -Path $cfgSrc -Destination (Join-Path $destDir "autoexec.cfg") -Force
}
Write-Host "  Deployed autoexec.cfg -> $($cfgTargets.Count) targets"

# --- Deploy coop_defaults.cfg LOOSE (the engine execs it before the saved config so option changes
#     persist; deployed loose like autoexec to guarantee it's found at Com_Init, not just in the pk3) ---
$defSrc = Join-Path $srcDir "coop_defaults.cfg"
if (Test-Path $defSrc) {
    foreach ($destDir in $cfgTargets) {
        Copy-Item -Path $defSrc -Destination (Join-Path $destDir "coop_defaults.cfg") -Force
    }
    Write-Host "  Deployed coop_defaults.cfg -> $($cfgTargets.Count) targets"
}

# --- Deploy engine DLLs. TWO roots (bug-1634): the LIVE install the user launches is
#     G:\mohaa-gl2\openmohaa.exe, which loads game.dll/cgame.dll/renderer from G:\mohaa-gl2\.
#     The GOG root is kept in sync for release-packaging parity, but deploying ONLY there
#     meant a full day of engine builds (auto-cover included) never actually loaded. ---
$gl2Root = "G:\mohaa-gl2"
$binRoots = @($gogRoot)
if (Test-Path (Join-Path $gl2Root "openmohaa.exe")) { $binRoots += $gl2Root }

$binaries = @(
    # [user 2026-08-13, bug-1798] The CLIENT executable. Same gap as bug-1796 (gl2) and bug-1634 (GOG
    # root only): omohaaded.exe was deployed but openmohaa.exe never was, so any change in code/client
    # - the sound system, the UI bridge, input - built cleanly and then simply did not reach the game
    # the player launches. publish_release.ps1 stages it FROM the GOG root, so nothing downstream
    # noticed either. Deployed with the rest now.
    @{ Name = "openmohaa.exe";        Src = "C:\mohaa-coop-dev\openmohaa-hzm\.cmake\Release\openmohaa.exe" },
    @{ Name = "cgame.dll";            Src = "C:\mohaa-coop-dev\openmohaa-hzm\.cmake\code\client\cgame\Release\cgame.dll" },
    @{ Name = "game.dll";             Src = "C:\mohaa-coop-dev\openmohaa-hzm\.cmake\code\server\fgame\Release\game.dll" },
    @{ Name = "game.pdb";             Src = "C:\mohaa-coop-dev\openmohaa-hzm\.cmake\code\server\fgame\Release\game.pdb" },
    @{ Name = "renderer_opengl1.dll"; Src = "C:\mohaa-coop-dev\openmohaa-hzm\.cmake\code\renderercommon\renderergl1\Release\renderer_opengl1.dll" },
    # [user 2026-08-13, bug-1796] THE GL2 RENDERER WAS NEVER DEPLOYED. Only gl1 was listed here, but
    # the live install runs gl2 (cl_renderer "opengl2", and G:\mohaa-gl2\PLAY-GL2.bat force-sets it),
    # so every renderer-side engine change silently failed to reach the running game - the same shape
    # as bug-1634, where deploying to the GOG root alone never reached the live install. Both renderers
    # ship now, so a renderer fix lands whichever one the player is on.
    @{ Name = "renderer_opengl2.dll"; Src = "C:\mohaa-coop-dev\openmohaa-hzm\.cmake\code\renderercommon\renderergl2\Release\renderer_opengl2.dll" },
    # [user 2026-08-10] The DEDICATED server binary. It was never deployed here, so every engine
    # build silently left omohaaded.exe stale - and it is what a self-hosting player runs. It also
    # carries two fixes without which a dedicated server does not work AT ALL: bug-1664 (the command
    # buffer never ran, so it booted to silence and loaded no map) and bug-1667 (the Windows timer
    # was never raised, pinning the "slow server" icon on). publish_release.ps1 ships it too.
    @{ Name = "omohaaded.exe";        Src = "C:\mohaa-coop-dev\openmohaa-hzm\.cmake\Release\omohaaded.exe" }
)
foreach ($bin in $binaries) {
    if (-not (Test-Path $bin.Src)) { continue }
    foreach ($root in $binRoots) {
        try {
            Copy-Item -Path $bin.Src -Destination (Join-Path $root $bin.Name) -Force -ErrorAction Stop
            Write-Host "  Deployed $($bin.Name) -> $root"
        } catch {
            Write-Host "  WARNING: could not deploy $($bin.Name) to $root (game running?)"
        }
    }
}

# [user 2026-08-14] CHALLENGE REACHABILITY. A challenge that can never complete is
# indistinguishable from one nobody has finished yet, which is how 32 unearnable challenges
# reached players and sat there until somebody audited all 344 by hand. Run the check on every
# build so the count is in front of you, and a new one is noticed the day it is introduced
# rather than months later. --warn deliberately: there is a known backlog of unwired stats, and
# failing the build on it would just train everyone to ignore the failure.
$chk = "C:\mohaa-coop-dev\docs\tools\check_challenges.py"
if (Test-Path $chk) {
    $out = & python $chk --warn 2>&1
    # [2026-08-23] Surface the NO-OP REWARD header too. The filter used to show only the counts,
    # so a validator finding printed "3 challenge(s) cannot be completed as shipped" with no hint
    # of WHICH or WHY - a warning nobody can act on is a warning nobody reads.
    $summary = $out | Select-String -Pattern "^challenges:|cannot be completed|^OK - every|^NO-OP REWARD|^DEAD -|^SHORT -|^MISSING -"
    foreach ($line in $summary) { Write-Host "  $line" -ForegroundColor DarkGray }
}

# bug-1803: the skeletor channel name table is a process-global static that is NEVER reset between
# maps, so its ceiling has to cover every model the whole game can load, not one session's worth.
# Overflow strands the player on a loading screen of an innocent map late in a long session - the
# most expensive possible symptom to diagnose. Re-measure the real asset requirement on every
# build (cached on pk3 fingerprint, so it costs nothing unless assets changed) and say so out loud
# while there is still headroom. This is T4's rule: turn the capacity rule into a build-time check
# instead of a comment nobody re-reads after adding a model pack.
$skel = "C:\mohaa-coop-dev\docs\tools\count_skel_channels.py"
if (Test-Path $skel) {
    $out = & python $skel --check 2>&1
    foreach ($line in $out) { Write-Host "  $line" -ForegroundColor DarkGray }
}

# [2026-08-14] The README names the exact installer files a new player must download, with pinned
# URLs. It used to say "go to /releases/latest" instead, which quietly became impossible to follow
# the first time a release shipped without an installer (the full package is ~6.8 GB and is only
# published periodically). Nothing failed and nothing warned - the front door was simply broken.
# Five range-GETs on every build is a cheap price for knowing the install instructions still work.
$dl = "C:\mohaa-coop-dev\docs\tools\check_download_links.py"
if (Test-Path $dl) {
    $out = & python $dl 2>&1
    foreach ($line in $out) { Write-Host "  $line" -ForegroundColor DarkGray }
}

Write-Host "Done."
