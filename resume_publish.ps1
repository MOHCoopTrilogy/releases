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

$manifestPath = "$dev\manifests\manifest-$Version.json"
if (-not (Test-Path $manifestPath)) { throw "no manifest for $Version - run publish_release.ps1 instead" }
$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json

# same stage map as publish_release.ps1 (manifest path -> source file)
function Get-Source($path) {
    switch -Wildcard ($path) {
        "openmohaa.exe"        { return "$bin\Release\openmohaa.exe" }
        "cgame.dll"            { return "$bin\code\client\cgame\Release\cgame.dll" }
        "game.dll"             { return "$bin\code\server\fgame\Release\game.dll" }
        "renderer_opengl1.dll" { return "$bin\code\renderercommon\renderergl1\Release\renderer_opengl1.dll" }
        "renderer_opengl2.dll" { return "$bin\code\renderercommon\renderergl2\Release\renderer_opengl2.dll" }
        "updater.ps1"          { return "$dev\updater\updater.ps1" }
        "launch_coop.vbs"      { return "$dev\updater\launch_coop.vbs" }
        "home/maintt/autoexec.cfg" { return "$mod\autoexec.cfg" }
        "home/maintt/zzzzzz_co-op_hzm_mod_*" { return Join-Path $mod (Split-Path -Leaf $path) }
        "home/maintt/*"        { return Join-Path "$gog\maintt" (Split-Path -Leaf $path) }
    }
    throw "no source mapping for $path"
}

# existing assets on the (draft) release
$existing = @(& $gh api "repos/$repoSlug/releases/tags/$tag" --jq ".assets[].name" 2>$null)
if ($LASTEXITCODE -ne 0) {
    # draft releases are not resolvable by tag via that endpoint; find by tag in the list
    $relId = & $gh api "repos/$repoSlug/releases" --jq ".[] | select(.tag_name==\"$tag\") | .id"
    if (-not $relId) { throw "release $tag not found (draft or otherwise)" }
    $existing = @(& $gh api "repos/$repoSlug/releases/$relId/assets" --jq ".[].name")
} else {
    $relId = & $gh api "repos/$repoSlug/releases/tags/$tag" --jq ".id"
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

# manifest asset: upload + rename to manifest.json if not present
if ($existing -notcontains "manifest.json") {
    if ($existing -contains "manifest-$Version.json") {
        $assetId = & $gh api "repos/$repoSlug/releases/$relId/assets" --jq ".[] | select(.name==\"manifest-$Version.json\") | .id"
    } else {
        & $gh release upload $tag --repo $repoSlug $manifestPath
        if ($LASTEXITCODE -ne 0) { throw "manifest upload failed" }
        $assetId = & $gh api "repos/$repoSlug/releases/$relId/assets" --jq ".[] | select(.name==\"manifest-$Version.json\") | .id"
    }
    if ($assetId) { & $gh api -X PATCH "repos/$repoSlug/releases/assets/$assetId" -f name=manifest.json | Out-Null }
}

& $gh release edit $tag --repo $repoSlug --draft=false
if ($LASTEXITCODE -ne 0) { throw "undraft failed" }
Write-Host "release $tag is LIVE"

Set-Location $dev
git add manifests/ 2>&1 | Out-Null
git commit -m "manifest $Version" 2>&1 | Out-Null
git push origin main 2>&1 | Out-Null
Write-Host "manifests pushed. Done."
