"""run viewclip jobs with an extra pak on the private client for the duration of each run only (queue-aware, as vc_queue):
the viewclip test overlay carries the branch's older anims_shared.txt (no revolver reload anims -> the Webley and Nagant
reloads crash the test server); this lays the current file over it while those guns run, then removes it.
    python vc_with_pak.py <pak> <job> [<job> ...]
"""
import os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vc_queue as Q  # noqa: E402
MAINTT = os.path.join("G:" + os.sep, "mohaa-wpnview", "home", "maintt")
pak, jobs = sys.argv[1], sys.argv[2:]
dst = os.path.join(MAINTT, os.path.basename(pak))
for j in jobs:
    Q.take_turn()
    shutil.copyfile(pak, dst)
    try:
        args = [os.path.join(HERE, "run_ab.py")] + j.split(":", 1)[1].split(":")
        p = subprocess.run([sys.executable] + args, env=dict(os.environ, WV_DISPLAY_RES="3440x1440"), capture_output=True, text=True)
        for l in (p.stdout + p.stderr).splitlines():
            if "launched" in l or " run " in l or "Traceback" in l or "VIOLATION" in l:
                print(l[:170], flush=True)
    finally:
        if os.path.exists(dst):
            os.remove(dst)
print("done", flush=True)
