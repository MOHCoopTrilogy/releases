# one fair-queue turn: the Allied proof run, then the whitelist site probe on a batch of maps (client from MZ_CLIENT)
param([string]$Label = "c1", [string]$Maps = "m1l3b e1l1 e3l2 t3l1")
Set-Location $PSScriptRoot
$env:MZ_DIST = "1500"
python mz_run.py ("a_" + $Label) m3l2 para
python mz_probe.py $Label ($Maps -split " ")
