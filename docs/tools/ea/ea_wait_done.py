#!/usr/bin/env python3
"""wait until no python process runs the given harness output dir (argument), excluding this process. usage: ea_wait_done.py <outdir-name>"""
import os, subprocess, sys, time
tok = sys.argv[1]
me = os.getpid()
while True:
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | % { \"$($_.ProcessId)`t$($_.CommandLine)\" }"],
                         capture_output=True, text=True).stdout
    alive = [l for l in out.splitlines() if tok in l and "ea_wait_done" not in l and not l.startswith(str(me))]
    if not alive:
        break
    time.sleep(15)
