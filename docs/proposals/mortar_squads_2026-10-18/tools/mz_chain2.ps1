param([string]$Label = "p2", [string]$Maps = "m3l2 m1l3a m1l3b e1l1 e3l2 e3l4")
Set-Location $PSScriptRoot
python mz_probe.py $Label ($Maps -split " ")
