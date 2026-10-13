"""fix_p4d.py - p4_ev.py 'far': the player goes 8000u away at the squad's own height (3000u up made every man 'fell');
p3_sess.py: 'here' as x = call the stick where the player spawns."""
import io


def patch(p, pairs):
    s = io.open(p, encoding="utf-8").read()
    for a, b in pairs:
        assert s.count(a) == 1, (p, a[:60])
        s = s.replace(a, b)
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("patched", p)


patch("p4_ev.py", [
    ("""        G.cmd("fly", x=X + 8000, y=Y, z=Z + 3000, pitch=0, yaw=YAW)""",
     """        G.cmd("fly", x=X + 8000, y=Y, z=Z + 8, pitch=0, yaw=YAW)"""),
    ("""        log(cam(float(OPT.get("ncd", 210)), float(OPT.get("nca", 110)), 30, 60))""",
     """        log(cam(float(OPT.get("ncd", 210)), float(OPT.get("nca", 110)), float(OPT.get("ncz", 30)), 60))"""),
])
patch("p3_sess.py", [
    ("""X, Y, Z, YAW = [float(v) for v in sys.argv[3:7]]""",
     """HERE_ = sys.argv[3] == "here"
X, Y, Z, YAW = (0.0, 0.0, 0.0, 0.0) if HERE_ else [float(v) for v in sys.argv[3:7]]"""),
    ("""    G.cmd("tp", x=X, y=Y, z=Z + 8, yaw=YAW, pitch=0)
    time.sleep(1.0)""",
     """    if HERE_:
        hh = G.since(G.cmd("here"), r"P3 here \\( ([-\\d.]+) ([-\\d.]+) ([-\\d.]+) \\) ang=\\( [-\\d.]+ ([-\\d.]+)")
        X, Y, Z, YAW = [float(v) for v in hh[-1]]
        RES["at"] = [X, Y, Z, YAW]
        log("call at the player's spawn:", X, Y, Z, YAW)
    G.cmd("tp", x=X, y=Y, z=Z + 8, yaw=YAW, pitch=0)
    time.sleep(1.0)"""),
])
