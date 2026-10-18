"""sl_chain.py - fair-queue chain: wait for the turn, run ONE batch (sl_run.py on m1l2a), release, build the GIF.
    python sl_chain.py [map]   (log: logs/chain.txt)"""
import os, subprocess, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__))
MAP = sys.argv[1] if len(sys.argv) > 1 else "m1l2a"
HT = r"C:\mohaa-coop-dev\docs\tools\harness_turn.py"
LOG = open(os.path.join(HERE, "logs", "chain.txt"), "a")
def say(s):
    LOG.write(s + "\n"); LOG.flush()
subprocess.run([sys.executable, HT, "wait", "searchlight"], stdout=LOG, stderr=LOG)
say("TURN granted")
try:
    for attempt, client in enumerate(["hudfeed2", "hudfeed5", "hudfeed2"]):
        env = dict(os.environ, SLCLIENT=client)
        say("batch attempt %d on %s" % (attempt, client))
        subprocess.run([sys.executable, os.path.join(HERE, "sl_run.py"), "p1", MAP], stdout=LOG, stderr=LOG, timeout=840, env=env)
        rl = os.path.join(HERE, "logs", "run_p1.txt")
        if os.path.exists(rl) and "SlotBusy" not in open(rl, errors="ignore").read():
            break
        say("slot busy, trying the next copy")
finally:
    subprocess.run([sys.executable, HT, "release", "searchlight"], stdout=LOG, stderr=LOG)
    say("released")
runs = sorted(glob.glob(os.path.join(HERE, "runs", "sl_p1", "p1_det_*.jpg"))) + sorted(glob.glob(os.path.join(HERE, "runs", "sl_p1", "p1_dtb_*.jpg")))
say("frames %d" % len(runs))
if runs:
    from PIL import Image
    fr = [Image.open(f).convert("RGB").resize((800, 450)).quantize(colors=64, dither=0) for f in runs[::2]]
    out = os.path.join(HERE, "searchlight_detected2.gif")
    fr[0].save(out, save_all=True, append_images=fr[1:], duration=240, loop=0)
    say("GIF " + out)
