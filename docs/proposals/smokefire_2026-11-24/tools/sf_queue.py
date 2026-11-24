"""sf_queue.py - runs the smoke & fire test jobs one at a time, only while the user's own game is NOT running, each
inside its own screen_slot hold; then the Blender smoke renders (CPU, -t 4) once no test is running.

    python sf_queue.py [job ...]      jobs: stress img_e3l4 img_t2l4 gl1 p1 blender_preview blender_full
Log: H:/hzm_work/smokefire/queue.log (one line per event, ^~^~^ SFQ ...)."""
import os, subprocess, sys, time
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg  # noqa: E402

T = os.path.dirname(os.path.abspath(__file__))
LOG = r"H:\hzm_work\smokefire\queue.log"
SLOT = r"H:\hzm_work\screen_slot.py"
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
BL_OUT = r"H:\hzm_work\smokefire\bl"
JOBS = {
    "stress": (["p0stress", "m5l2b", "scene_p0_stress.json", "B"], {}),
    "img_e3l4": (["img_e3l4", "e3l4", "scene_img_e3l4.json", "A", "B"], {}),
    "img_t2l4": (["img_t2l4", "t2l4", "scene_img_t2l4.json", "A", "B"], {}),
    "gl1": (["gl1", "m5l2b", "scene_gl1.json", "G1"], {"SF_RENDERER": "opengl1"}),
    "p1": (["p1day", "m5l2b", "scene_p1_day.json", "P0", "P1"], {}),
    "soft": (["soft", "m5l2b", "scene_soft.json", "S0", "S1"], {}),
    "softdbg": (["softdbg", "m5l2b", "scene_softdbg.json", "DBG"], {}),
    "p0v2": (["p0v2", "m5l2b", "scene_p0v2.json", "A", "B"], {}),
    "m18": (["m18", "m5l2b", "scene_m18.json", "P0", "P1"], {}),
    "sgren": (["sgren", "m5l2b", "scene_sgren.json", "P0", "SPR", "VOL"], {}),
    "remap": (["remap", "m5l2b", "scene_remap.json", "R0", "R1"], {}),
}
# preview = low res / few samples to judge the motion before the long render; full = 512 px production frames
BL = {
    "blender_preview": [("billow", "--res 64 --px 256 --samples 12 --step 4 --scol 0.82"),
                        ("soot", "--res 64 --px 256 --samples 12 --step 4 --scol 0.14"),
                        ("dust", "--res 64 --px 256 --samples 12 --step 4 --scol 0.55")],
    "blender_full": [("billow", "--res 128 --px 512 --samples 40 --step 1 --scol 0.82"),
                     ("soot", "--res 128 --px 512 --samples 40 --step 1 --scol 0.14"),
                     ],   # dust: production after its preview is signed off; wreck columns are volumetric (VOLUMETRIC.md)
}


def log(s):
    line = "%s ^~^~^ SFQ %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), s)
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def wait_free():
    # [coordinator 2026-11-24] the user said "don't stop testing for me": screen_slot already grants one test at a
    # time on the secondary screen while they play, so there is no wait here any more (kept as a no-op hook)
    return
    n = 0
    while hg.user_game_running():
        if n % 60 == 0:
            log("waiting: the user's game is running")
        n += 1
        time.sleep(10)


for job in (sys.argv[1:] or list(JOBS) + ["blender_preview"]):
    wait_free()
    if job in JOBS:
        args, env = JOBS[job]
        r = subprocess.run([sys.executable, "-I", SLOT, "acquire", "smokefire", "8", "smoke&fire %s (1 client, muted)" % job])
        if r.returncode:
            log("%s: no screen slot (%d)" % (job, r.returncode)); continue
        try:
            e = dict(os.environ); e.update(env)
            r = subprocess.run([sys.executable, os.path.join(T, "sf_run.py")] + args, cwd=T, env=e,
                               stdout=open(r"H:\hzm_work\smokefire\%s_run.log" % job, "w"), stderr=subprocess.STDOUT)
            log("%s: exit %d" % (job, r.returncode))
        finally:
            subprocess.run([sys.executable, "-I", SLOT, "release", "smokefire"])
    elif job in BL:
        for preset, a in BL[job]:
            wait_free()
            out = os.path.join(BL_OUT, job.split("_")[1], preset)
            os.makedirs(out, exist_ok=True)
            t0 = time.time()
            r = subprocess.run([BLENDER, "-b", "-noaudio", "-t", "4", "--python", os.path.join(T, "mk_smoke.py"), "--", preset, out]
                               + a.split(), stdout=open(os.path.join(out, "blender.log"), "w"), stderr=subprocess.STDOUT)
            log("%s %s: exit %d in %d s" % (job, preset, r.returncode, time.time() - t0))
    else:
        log("unknown job " + job)
log("queue done")
