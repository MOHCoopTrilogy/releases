# Unattended weapon-HD batch under the quiet rule: BELOW-NORMAL priority, pinned to 4 cores (affinity 0x0F),
# one job at a time. Child processes (ESRGAN) inherit both.
#   powershell -NoProfile -File docs\tools\weapon_hd\run_batch.ps1 -BatchArgs "--cls 1"
# NOT $Args: an automatic variable in PowerShell - binding it silently does nothing (TRAPS T2, ps-home-var)
param([string]$BatchArgs = "--cls 1")
$py = (Get-Command python).Source
$script = Join-Path $PSScriptRoot "build_sheets.py"
$p = Start-Process -FilePath $py -ArgumentList "`"$script`" $BatchArgs" -NoNewWindow -PassThru
$p.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::BelowNormal
$p.ProcessorAffinity = [IntPtr]0x0F
$p.WaitForExit()
exit $p.ExitCode
