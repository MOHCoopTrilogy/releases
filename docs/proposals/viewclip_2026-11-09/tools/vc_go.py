"""wait for the display queue (no openmohaa.exe of ANY session running), refresh the private client from the viewclip engine
build (exe / cgame / game via wpnview_run setup_fix + both renderers), then run each job one at a time. Logs to stdout.
    python vc_go.py <job> [<job> ...]     job = "ab:<gid>:<gun name>:<tag>[:shots]"
"""
import os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
WV = r"C:\mohaa-coop-dev\docs\proposals\wpnviewer_2026-11-04\tools"
ENG = r"H:\hzm_work\wpnfix-eng\.cmake"
CLIENT = r"G:\mohaa-wpnview"
MOD = os.path.join("H:" + os.sep, "hzm_work", "viewclip-mod")


def busy():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq openmohaa.exe"], capture_output=True, text=True).stdout
    return "openmohaa.exe" in out.lower()


def wait_free():
    t0 = time.time()
    while busy():
        if time.time() - t0 > 3600:
            raise SystemExit("display busy for an hour - giving up")
        time.sleep(10)


def setup():
    subprocess.run([sys.executable, os.path.join(WV, "wpnview_run.py"), "setup_fix", "b4f53a1f", ENG],
                   env=dict(os.environ, WV_MOD=MOD))
    for r in ("renderergl2", "renderergl1"):
        n = "renderer_opengl%s.dll" % r[-1]
        shutil.copyfile(os.path.join(ENG, "code", "renderercommon", r, "Release", n), os.path.join(CLIENT, n))
    print("client refreshed from", ENG, flush=True)


def run(job):
    kind, rest = job.split(":", 1)
    if kind == "ab":
        a = rest.split(":")
        args = [os.path.join(HERE, "run_ab.py")] + a
    else:
        raise SystemExit("unknown job " + job)
    wait_free()
    p = subprocess.run([sys.executable] + args, env=dict(os.environ, WV_DISPLAY_RES="3440x1440"), capture_output=True, text=True)
    for l in (p.stdout + p.stderr).splitlines():
        if "launched" in l or "VIOLATION" in l or " run " in l or "Error" in l or "Traceback" in l:
            print(l[:170], flush=True)


wait_free()
setup()
for j in sys.argv[1:]:
    run(j)
print("vc_go done", flush=True)
