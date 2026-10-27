import os, sys, time, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
rundir = notes = None
rays = [((3680,-3640,-475),(3680,-3540,-478)), ((3690,-3640,-478),(3690,-3540,-478)), ((3670,-3640,-470),(3670,-3540,-480)), ((3680,-3600,-420),(3680,-3600,-500)), ((3690,-3580,-420),(3690,-3580,-500))]
try:
    rundir, notes = G.boot("m2_wi", "m2l2c")
    G.cmd("god"); time.sleep(3)
    for a, b in rays:
        p0 = G.cmd("whatis", x=a[0], y=a[1], z=a[2], yaw=b[0], pitch=b[1], k=b[2])
        for l in G.since(p0, r"\^~\^~\^ OX (WHATIS[^\r\n]*)"): G.log("wi", a, "->", b, l)
finally:
    G.end(rundir, notes)
