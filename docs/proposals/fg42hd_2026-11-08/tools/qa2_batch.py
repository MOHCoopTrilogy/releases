"""QA #2 batch (2026-11-08): the scoped FG 42's in-scope view next to the Kar98k sniper's, at 1080 and the user's 3440x1440, the hip in
good light, the raise frames for a GIF, viewer + Armory. One client at a time: waits for ANY openmohaa.exe (other sessions' too) to exit
before each launch. Windows go on the 3440x1440 ultrawide (WV_DISPLAY_RES, picked by resolution); the harness launches muted.
    python qa2_batch.py <tagprefix>
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
WV = r"C:\mohaa-coop-dev\docs\proposals\wpnviewer_2026-11-04\tools"
pre = sys.argv[1] if len(sys.argv) > 1 else "q2"
MOD = os.path.join("H:" + os.sep, "hzm_work", "fg42hd-mod")


def busy():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq openmohaa.exe"], capture_output=True, text=True).stdout
    return "openmohaa.exe" in out.lower()


def wait_free():
    t0 = time.time()
    while busy():
        if time.time() - t0 > 1800:
            raise SystemExit("a client has been running for 30 min - giving up")
        time.sleep(10)


def run(args, env_extra):
    wait_free()
    env = dict(os.environ, WV_DISPLAY_RES="3440x1440", **env_extra)
    p = subprocess.run([sys.executable] + args, env=env, capture_output=True, text=True)
    for l in (p.stdout + p.stderr).splitlines():
        if "launched" in l or "VIOLATION" in l or " run " in l or "Error" in l:
            print(l[:170], flush=True)


wait_free()
subprocess.run([sys.executable, os.path.join(WV, "wpnview_run.py"), "setup_fix"], env=dict(os.environ, WV_MOD=MOD))
base = dict(WV_BOOT=os.environ.get("QA_BOOT", "60000"), WV_SPAWN="models/weapons/fg42.tik")
run([os.path.join(HERE, "run_fg42.py"), "39", "FG 42", pre + "fg1080"], dict(base, WV_RES="1080", WV_RAISE="1", WV_RAISE_TURN_MS="900"))
run([os.path.join(HERE, "run_fg42.py"), "39", "FG 42", pre + "fguw"], dict(base, WV_RES="uw"))
if os.environ.get("QA_SKIP_K") != "1":          # the Kar98k reference pair (unchanged by FG 42 work: reuse the last batch's)
    run([os.path.join(HERE, "run_fg42.py"), "13", "KAR98 - Sniper", pre + "k1080"], dict(base, WV_RES="1080"))
    run([os.path.join(HERE, "run_fg42.py"), "13", "KAR98 - Sniper", pre + "kuw"], dict(base, WV_RES="uw"))
run([os.path.join(WV, "wpnview_run.py"), "shots", "1080", pre + "_views", "exec ui/wpnview/e374.cfg",
     "pushmenu coop_loadout|set coop_loP3 1;set coop_loP2 0|exec ui/loadout/eq39.cfg"], {"WV_MOD": r"H:\hzm_work\fg42hd-mod"})
print("batch done", flush=True)
