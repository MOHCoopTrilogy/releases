# MOH Coop Trilogy - one-command release publisher
# Design: _research/auto_update.md section 6.
# Usage:  .\publish_release.ps1 -Version 1.1.0 [-Notes "..."] [-DryRun]
# Flow: preflight -> build -> stage -> manifest w/ asset reuse -> gh release (draft->publish)
#       -> record manifests/ in this repo.
param(
    [Parameter(Mandatory = $true)][string]$Version,
    [string]$Notes = "",
    [switch]$DryRun,
    [switch]$SkipBuild
)
$ErrorActionPreference = "Stop"

$repoOwner = "MOHCoopTrilogy"
$repoName  = "releases"
$repoSlug  = "$repoOwner/$repoName"
$tag       = "v$Version"

$dev  = "C:\mohaa-coop-dev"
$gog  = "G:\GOG\Medal of Honor - Allied Assault War Chest"
$bin  = "$dev\openmohaa-hzm\.cmake"
$mod  = "$dev\hzm-mohaa-coop-mod"
$gh   = "$env:LOCALAPPDATA\Programs\GitHub CLI\gh.exe"
if (-not (Test-Path $gh)) { $gh = "C:\Program Files\GitHub CLI\gh.exe" }
if (-not (Test-Path $gh)) { throw "gh CLI not found" }

# --- 1. preflight ---
$eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
& $gh auth status *> $null
if ($LASTEXITCODE -ne 0) { $ErrorActionPreference = $eap; throw "gh not authenticated - run: gh auth login" }
$ErrorActionPreference = $eap
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Version must be SemVer (e.g. 1.1.0)" }
$eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
& $gh release view $tag --repo $repoSlug *> $null
$tagExists = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $eap
if ($tagExists) { throw "release $tag already exists - never overwrite a published tag; bump the version" }

# --- 2. build ---
if (-not $SkipBuild) {
    Write-Host "== build.ps1 (3-way pk3 split) =="
    & "$dev\build.ps1"
}

# --- 3. stage: the complete shippable file set (manifest path -> source file) ---
$stage = [ordered]@{}
# engine binaries (root of {app}); grouped last by the updater on swap
$stage["openmohaa.exe"]        = "$bin\Release\openmohaa.exe"
$stage["cgame.dll"]            = "$bin\code\client\cgame\Release\cgame.dll"
$stage["game.dll"]             = "$bin\code\server\fgame\Release\game.dll"
$stage["renderer_opengl1.dll"] = "$bin\code\renderercommon\renderergl1\Release\renderer_opengl1.dll"
$stage["renderer_opengl2.dll"] = "$bin\code\renderercommon\renderergl2\Release\renderer_opengl2.dll"
# updater self-update
$stage["updater.ps1"]     = "$dev\updater\updater.ps1"
$stage["launch_coop.vbs"] = "$dev\updater\launch_coop.vbs"
$stage["report_problem.ps1"] = "$dev\installer\report_problem.ps1"   # secret-free: webhook comes from updater.ini
# mod pk3s (freshly built by build.ps1)
foreach ($p in @("zzzzzz_co-op_hzm_mod_assets_snd.pk3","zzzzzz_co-op_hzm_mod_assets_tex.pk3","zzzzzz_co-op_hzm_mod_code.pk3")) {
    $stage["home/maintt/$p"] = "$mod\$p"
}
# autoexec (ours; users edit omconfig, not this)
$stage["home/maintt/autoexec.cfg"] = "$mod\autoexec.cfg"
# What's New card trigger seed (constant content = constant hash = downloaded once ever).
# Lives in installer/ (NOT the mod tree) so build.ps1 never packs it into a pk3 - a pk3 copy
# could shadow the loose file the updater blanks, re-showing the card forever.
$stage["home/maintt/whatsnew_pending.cfg"] = "$dev\installer\whatsnew_seed.cfg"
# HD companion pk3s (rarely change; canonical deployed copies)
$hdPaks = @(
    "zzzzz-AA_HD_Project_Pak1.pk3","zzzzz-AA_HD_Project_Pak2.pk3","zzzzz-AA_HD_Project_Pak3.pk3",
    "zzzzz-AA_HD_Project_Pak4.pk3","zzzzz-hd_gunsounds.pk3","zzzzz_geared_soldiers.pk3",
    "zzzzz_hd_foliage.pk3","zzzzzz-HRRTM_Pak1_Models.pk3","zzzzzz-HRRTM_Pak2_Models_misc.pk3",
    "zzzzzz-HRRTM_Pak3_Textures.pk3","zzzzzz-HRRTM_Pak4_Weapons.pk3","zzzzzz-HRRTM_Pak4c_WeaponTGA.pk3",
    "zzzzzz_hd_charskins.pk3","zzzzzz_hd_fx.pk3","zzzzzz_hd_skybox.pk3","zzzzzz_hd_world.pk3",
    "zzzzzzz-HRRTM_Blood_effects_Addon.pk3","zzzzzzz_dds_override.pk3"
)
foreach ($p in $hdPaks) { $stage["home/maintt/$p"] = "$gog\maintt\$p" }
# v1.1.34 DXT memory pack: dds siblings for every HD texture lacking one - engine loads
# .dds first and DXT stays compressed in RAM (the m1l2a-era OOM pressure fix)
$stage["home/maintt/zzzzzzz_dds_hdmem.pk3"] = "$gog\maintt\zzzzzzz_dds_hdmem.pk3"
# NOTE: omconfig default is deliberately NOT in the update manifest - the installer seeds it
# once; auto-updates never stomp player settings.

foreach ($k in $stage.Keys) { if (-not (Test-Path $stage[$k])) { throw "staged file missing: $($stage[$k])" } }

# --- 4. manifest: hash everything; carry forward URLs for unchanged assets ---
Write-Host "== hashing $($stage.Count) files =="
$prevManifest = $null
$prevPath = "$dev\manifests\latest.json"
if (Test-Path $prevPath) {
    try { $prevManifest = Get-Content $prevPath -Raw | ConvertFrom-Json } catch {}
}
$prevMap = @{}
if ($prevManifest -and $prevManifest.version -eq $Version) {
    # latest.json must always describe the last LIVE release. Same version here means an
    # aborted publish left its manifest behind - continuing would silently re-upload
    # everything (no reuse baseline). Fail loudly instead of wasting 5 GB.
    throw "manifests/latest.json is already $Version (leftover from an aborted publish). Restore it: Copy-Item manifests/manifest-<lastLiveVersion>.json manifests/latest.json"
}
if ($prevManifest) { foreach ($f in $prevManifest.files) { $prevMap[$f.path] = $f } }

$files = @()
$uploads = @{}   # asset filename -> source path (assets are flat in a release)
foreach ($k in $stage.Keys) {
    $src = $stage[$k]
    $hash = (Get-FileHash -Path $src -Algorithm SHA256).Hash.ToLower()
    $size = (Get-Item $src).Length
    $assetName = Split-Path -Leaf $k
    $prev = $prevMap[$k]
    if ($prev -and $prev.sha256 -eq $hash) {
        $url = $prev.url   # unchanged: reuse the old release's permanent asset URL
    } else {
        $url = "https://github.com/$repoSlug/releases/download/$tag/$assetName"
        if ($uploads.ContainsKey($assetName)) { throw "asset name collision: $assetName" }
        $uploads[$assetName] = $src
    }
    $files += [pscustomobject]@{ path = $k; size = $size; sha256 = $hash; url = $url }
    Write-Host ("  {0}  {1,10:N0}  {2}" -f $hash.Substring(0,10), $size, $k)
}

$manifest = [pscustomobject]@{
    manifestVersion = 1
    version = $Version
    created = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    files = $files
    delete = @("home/maintt/zzzzzz_co-op_hzm_mod_mohaa.pk3")   # monolith retirement (harmless once gone)
}

$totalUploadMB = 0
foreach ($src in $uploads.Values) { $totalUploadMB += (Get-Item $src).Length / 1MB }
Write-Host ("== release {0}: {1} changed asset(s), {2:N0} MB to upload ==" -f $tag, $uploads.Count, $totalUploadMB)

if ($DryRun) {
    Write-Host "DRY RUN - would upload:"
    foreach ($n in $uploads.Keys) { Write-Host "   $n" }
    Write-Host "DRY RUN - no manifest files written, nothing uploaded"
    return
}

# manifest goes to TEMP for the asset upload; manifests/ in the repo is only written AFTER
# the release is live (an aborted publish must never poison the next run's reuse baseline)
$manifestPath = Join-Path $env:TEMP "manifest-$Version.json"
$manifest | ConvertTo-Json -Depth 5 | Set-Content $manifestPath -Encoding utf8

# --- 5. publish (Continue mode: gh/git write progress to stderr; rely on exit codes) ---
$ErrorActionPreference = "Continue"
$notesFile = Join-Path $env:TEMP "mohcoop_relnotes.md"
if ($Notes) { $Notes | Set-Content $notesFile -Encoding utf8 } else { "MOH Coop Trilogy $Version" | Set-Content $notesFile -Encoding utf8 }
& $gh release create $tag --repo $repoSlug --draft --title "MOH Coop Trilogy $Version" --notes-file $notesFile
if ($LASTEXITCODE -ne 0) { throw "gh release create failed" }

foreach ($n in $uploads.Keys) {
    Write-Host "uploading $n ..."
    & $gh release upload $tag --repo $repoSlug $uploads[$n]
    if ($LASTEXITCODE -ne 0) { throw "upload failed: $n" }
}
& $gh release upload $tag --repo $repoSlug $manifestPath
if ($LASTEXITCODE -ne 0) { throw "manifest upload failed" }
& $gh release edit $tag --repo $repoSlug --draft=false
if ($LASTEXITCODE -ne 0) { throw "undraft failed" }
Write-Host "release $tag is LIVE"

# rename manifest asset to manifest.json (must be post-undraft: the tag does not resolve while draft)
$relJson = & $gh api "repos/$repoSlug/releases/tags/$tag" | ConvertFrom-Json
$asset = $relJson.assets | Where-Object { $_.name -eq "manifest-$Version.json" }
if ($asset) { & $gh api -X PATCH "repos/$repoSlug/releases/assets/$($asset.id)" -f name=manifest.json | Out-Null; Write-Host "manifest.json published" }

# --- 6. record manifests in the repo (raw.githubusercontent fallback + audit trail) ---
# release is LIVE at this point, so NOW the local baseline may advance
New-Item -ItemType Directory -Path "$dev\manifests" -Force | Out-Null
Copy-Item $manifestPath "$dev\manifests\manifest-$Version.json" -Force
Copy-Item $manifestPath "$dev\manifests\latest.json" -Force
Set-Location $dev
git add manifests/ 2>$null
git commit -m "manifest $Version" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "WARNING: manifest commit failed - fallback URL will be stale!" -ForegroundColor Red }
git push origin main 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "WARNING: manifest push failed - fallback URL is STALE until you push manifests/ manually" -ForegroundColor Red }
else { Write-Host "manifests committed + pushed" }
Write-Host ""
Write-Host "Done. Testers on the updater get v$Version on next launch."
