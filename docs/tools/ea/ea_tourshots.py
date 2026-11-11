#!/usr/bin/env python3
"""ea_tourshots - the self-test walk of coop_ea_1_11 on camera: one private SINGLE-PLAYER background client
(coop_eatest 1: the map's self-test walks the player through the original's triggers in order); a still every few
seconds, named after the step the self-test is on (EATEST go / EAOBJ / EAGAG / EATANK / EAPROP lines in its own log).
SP, because a still needs the console of the game that runs the script. Our code; stills contain converted disc
content: LOCAL ONLY.

  python ea_tourshots.py <outdir> [--every 10] [--minutes 20]
"""
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ea_aiaudit  # noqa: E402,F401  (client folder, user-clip filter)
import byoclient   # noqa: E402

STEP = re.compile(r"\^~\^~\^ (EATEST go \d+ \S+|EAOBJ [^\n]+|EAGAG start \S+|EATANK [^\n]+|EAPROP [^\n]+|EASQUAD [^\n]+)")


def main():
    out = sys.argv[1]
    every = float(sys.argv[sys.argv.index("--every") + 1]) if "--every" in sys.argv else 10.0
    mins = float(sys.argv[sys.argv.index("--minutes") + 1]) if "--minutes" in sys.argv else 20.0
    os.makedirs(out, exist_ok=True)
    n = 0
    with byoclient.Client("coop_ea_1_11", sets=[("coop_eatest", "1"), ("coop_eatestPlayers", "1"), ("coop_health", "20000")],
                          coop=False, w=960, h=540, port=int(os.environ.get("BYO_PORT", "12488"))) as c:
        if not c.wait(r"EAAI ", 300):
            raise RuntimeError("map never loaded")
        time.sleep(8)
        c.step(["god", "wait 5", "cg_drawviewmodel 0"])
        t0 = time.time()
        while time.time() - t0 < mins * 60:
            c.check()
            s = c.text()
            steps = STEP.findall(s)
            tag = re.sub(r"[^A-Za-z0-9_]+", "_", steps[-1])[:60] if steps else "start"
            n += 1
            name = "t%03d_%s" % (n, tag)
            c.step(["screenshot " + name, "wait 4"])
            c.grab(name, out)
            if "EAMISSION complete" in s:
                break
            time.sleep(every)
        c.keep_log(os.path.join(out, "qconsole.log"))
    print("stills:", n)


if __name__ == "__main__":
    main()
