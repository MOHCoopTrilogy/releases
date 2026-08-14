# MOH Coop Trilogy - resume an interrupted publish (draft release with partial assets)
# Reads manifests\manifest-<Version>.json (written by publish_release.ps1 before uploads),
# uploads whatever assets the draft is still missing, fixes the manifest asset name,
# undrafts, and pushes the manifests dir.
param(
    [Parameter(Mandatory = $true)][string]$Version
)
$ErrorActionPreference = "Continue"

$repoSlug = "MOHCoopTrilogy/releases"
$tag = "v$Version"
$dev = "C:\mohaa-coop-dev"
$gog = "G:\GOG\Medal of Honor - Allied Assault War Chest"
$bin = "$dev\openmohaa-hzm\.cmake"
$mod = "$dev\hzm-mohaa-coop-mod"
$gh  = "C:\Program Files\GitHub CLI\gh.exe"

# [2026-08-13] publish_release.ps1 writes the manifest to $env:TEMP and only copies it into
# manifests\ AFTER the release is undrafted (its step 6). So on an interrupted publish - the
# only time this script runs - manifests\ does NOT have it yet, and looking only there made
# this throw immediately. Check the staging copy too.
$manifestPath = "$dev\manifests\manifest-$Version.json"
if (-not (Test-Path $manifestPath)) {
    $staged = Join-Path $env:TEMP "manifest-$Version.json"
    if (Test-Path $staged) {
        Copy-Item $staged $manifestPath -Force
        Write-Host "recovered staged manifest from TEMP"
    }
}
if (-not (Test-Path $manifestPath)) { throw "no manifest for $Version - run publish_release.ps1 instead" }
$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json

# same stage map as publish_release.ps1 (manifest path -> source file)
#
# [2026-08-13] This drifted from publish_release.ps1 in two ways, both of which broke a resume:
#
#  1. MISSING ENTRIES. omohaaded.exe, report_problem.ps1, dedicated_example.cfg and
#     whatsnew_pending.cfg are all staged by the publisher and had no mapping here, so a resume
#     threw "no source mapping" on the first one it reached.
#  2. WRONG SOURCE for the binaries. The publisher deliberately stages them from the DEPLOYED
#     GOG root, not the build tree - its own note says a --clean-first rebuild can leave .cmake
#     stale while the deployed set is what was actually play-tested. This file read them from
#     $bin, so a resume could upload a DIFFERENT binary than the one the manifest already
#     hashed, handing every updating player a hash mismatch. The manifest is written before any
#     upload, so on a resume its hashes are already fixed and the source must match them.
#
# Any future change to the publisher's stage map has to be mirrored here.
function Get-Source($path) {
    switch -Wildcard ($path) {
        "openmohaa.exe"        { return "$gog\openmohaa.exe" }
        "cgame.dll"            { return "$gog\cgame.dll" }
        "game.dll"             { return "$gog\game.dll" }
        "renderer_opengl1.dll" { return "$gog\renderer_opengl1.dll" }
        "renderer_opengl2.dll" { return "$gog\renderer_opengl2.dll" }
        "omohaaded.exe"        { return "$gog\omohaaded.exe" }
        "updater.ps1"          { return "$dev\updater\updater.ps1" }
        "launch_coop.vbs"      { return "$dev\updater\launch_coop.vbs" }
        "report_problem.ps1"   { return "$dev\installer\report_problem.ps1" }
        "home/maintt/autoexec.cfg"         { return "$mod\autoexec.cfg" }
        "home/maintt/whatsnew_pending.cfg" { return "$dev\installer\whatsnew_seed.cfg" }
        "home/maintt/dedicated_example.cfg" { return "$mod\coop_mod\cfg\dedicated_example.cfg" }
        "home/maintt/zzzzzz_co-op_hzm_mod_*" { return Join-Path $mod (Split-Path -Leaf $path) }
        "home/maintt/*"        { return Join-Path "$gog\maintt" (Split-Path -Leaf $path) }
    }
    throw "no source mapping for $path"
}

# existing assets on the (draft) release
#
# [2026-08-13] NEVER use a --jq expression containing a pipe from PowerShell 5.1. The previous
# version did (`.[] | select(...) | .id`) and PowerShell split it, so gh received 3 positional
# args, errored, left $relId empty, and this script threw "release not found" on a draft that
# demonstrably existed. That made resume_publish unable to resume the one situation it exists
# for. ConvertFrom-Json does the filtering in PowerShell, where it cannot be mangled.
# per_page=100 matters too: the draft is only on page 1 while the release count stays under 100.
$relId = $null
$existing = @()
$byTag = & $gh api "repos/$repoSlug/releases/tags/$tag" 2>$null
if ($LASTEXITCODE -eq 0 -and $byTag) {
    $rel = $byTag | ConvertFrom-Json
    $relId = $rel.id
    $existing = @($rel.assets | ForEach-Object { $_.name })
} else {
    # a DRAFT has no published tag, so the by-tag endpoint 404s by design - find it in the list
    $all = & $gh api "repos/$repoSlug/releases?per_page=100" | ConvertFrom-Json
    $rel = $all | Where-Object { $_.tag_name -eq $tag } | Select-Object -First 1
    if (-not $rel) { throw "release $tag not found (draft or otherwise)" }
    $relId = $rel.id
    $existing = @($rel.assets | ForEach-Object { $_.name })
}
Write-Host "release id $relId - $($existing.Count) asset(s) already uploaded"

# figure out what this release still needs: files whose manifest URL points at THIS tag
$needed = @()
foreach ($f in $manifest.files) {
    $assetName = Split-Path -Leaf $f.path
    if ($f.url -like "*/download/$tag/*" -and $existing -notcontains $assetName) {
        $needed += $f
    }
}
Write-Host "$($needed.Count) asset(s) still to upload"

foreach ($f in $needed) {
    $src = Get-Source $f.path
    $assetName = Split-Path -Leaf $f.path
    # verify source still matches the manifest hash (paranoia: nothing rebuilt since)
    $hash = (Get-FileHash -Path $src -Algorithm SHA256).Hash.ToLower()
    if ($hash -ne $f.sha256) { throw "SOURCE CHANGED since manifest: $($f.path) - do NOT resume; publish a new version" }
    Write-Host "uploading $assetName ($([math]::Round($f.size/1MB)) MB)..."
    & $gh release upload $tag --repo $repoSlug $src
    if ($LASTEXITCODE -ne 0) { throw "upload failed: $assetName (rerun to resume)" }
}

# manifest asset: upload + rename to manifest.json if not present.
#
# THE ASSET MUST END UP NAMED manifest.json. Every installed copy of the updater fetches
#   https://github.com/<repo>/releases/latest/download/manifest.json
# so if this rename does not happen, that URL 404s and the whole player base silently falls back
# to the raw.githubusercontent copy - which is only as fresh as the git push below.
#
# [2026-08-13] This is exactly what happened on v1.2.8, and the cause was the SAME piped --jq
# defect fixed above: `.[] | select(...) | .id` gets split by PowerShell 5.1, gh errors, $assetId
# comes back empty, and the `if ($assetId)` guard then skips the rename WITHOUT complaining. A
# silent no-op is the worst possible failure here, so the rename is now verified rather than
# assumed, and a failure is loud.
if ($existing -notcontains "manifest.json") {
    if ($existing -notcontains "manifest-$Version.json") {
        & $gh release upload $tag --repo $repoSlug $manifestPath
        if ($LASTEXITCODE -ne 0) { throw "manifest upload failed" }
    }
    $assets = & $gh api "repos/$repoSlug/releases/$relId/assets" | ConvertFrom-Json
    $asset = $assets | Where-Object { $_.name -eq "manifest-$Version.json" } | Select-Object -First 1
    if (-not $asset) { throw "manifest asset not found on release $tag - cannot rename to manifest.json" }
    & $gh api -X PATCH "repos/$repoSlug/releases/assets/$($asset.id)" -f name=manifest.json | Out-Null
    $after = (& $gh api "repos/$repoSlug/releases/$relId/assets" | ConvertFrom-Json) | Where-Object { $_.name -eq "manifest.json" }
    if (-not $after) { throw "manifest.json rename did not take - latest/download/manifest.json would 404" }
    Write-Host "manifest.json published"
}

& $gh release edit $tag --repo $repoSlug --draft=false
if ($LASTEXITCODE -ne 0) { throw "undraft failed" }
Write-Host "release $tag is LIVE"

# [2026-08-13] latest.json is the UPDATER'S FALLBACK source. publish_release.ps1 writes both this
# and the versioned copy; this script only wrote the versioned one, so after a resumed publish the
# fallback still advertised the PREVIOUS version. The updater takes whichever source advertises the
# newer version, so it kept working - but the safety net was silently one release out of date,
# which defeats the point of having it.
Set-Location $dev
Copy-Item $manifestPath "$dev\manifests\latest.json" -Force
git add manifests/ 2>&1 | Out-Null
git commit -m "manifest $Version" 2>&1 | Out-Null
git push origin main 2>&1 | Out-Null
Write-Host "manifests pushed (manifest-$Version.json + latest.json). Done."
