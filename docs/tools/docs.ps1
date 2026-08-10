<#
.SYNOPSIS
    Front end for the derived-documentation generator.

.DESCRIPTION
    docs build        regenerate docs/generated/ (no-op if inputs unchanged)
    docs build -Force regenerate unconditionally
    docs check        exit 1 if docs/generated is stale  <-- the testable guarantee
    docs status       print the input fingerprint and staleness, write nothing

    `check` is what makes the guarantee real rather than hoped-for: it
    regenerates in memory and byte-compares against what is on disk. A non-zero
    exit means the committed docs no longer describe the code.

.EXAMPLE
    .\docs\tools\docs.ps1 check
#>
param(
    [Parameter(Position = 0)]
    [ValidateSet('build', 'check', 'status')]
    [string]$Mode = 'build',

    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'docgen.py'

if (-not (Test-Path $script)) {
    Write-Error "docgen.py not found at $script"
    exit 2
}

# Prefer the py launcher, fall back to python on PATH.
$exe = $null
$preArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) { $exe = 'py'; $preArgs = @('-3') }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $exe = 'python' }
elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $exe = 'python3' }
else {
    Write-Error 'No Python interpreter found (tried py, python, python3).'
    exit 2
}

$argList = $preArgs + @($script, $Mode)
if ($Force) { $argList += '--force' }

& $exe @argList
exit $LASTEXITCODE
