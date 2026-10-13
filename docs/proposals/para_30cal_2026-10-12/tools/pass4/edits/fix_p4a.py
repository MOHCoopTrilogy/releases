"""fix_p4a.py - p4_pitch.py: the squad is sent 450u behind the camera instead of hidden (their star markers stay in
the sky when they are hidden); the dead gunner is removed before the player stills; the player's pitch is driven with
+lookup / +lookdown (the turret takes its angles from the client's commands); driver: 'nocorpse'."""
import io


def patch(p, pairs, enc="utf-8"):
    s = io.open(p, encoding=enc, newline="").read()
    nl = "\r\n" if "\r\n" in s else "\n"
    s = s.replace("\r\n", "\n")
    for a, b in pairs:
        assert s.count(a) == 1, (p, a[:60])
        s = s.replace(a, b)
    io.open(p, "w", encoding=enc, newline="").write(s.replace("\n", nl))
    print("patched", p)


patch("p3_drv.scr", [("""	if( local.c == "paim" ){""", """	if( local.c == "nocorpse" ){
		// TEST SET-UP for stills: dead squad members are taken away
		for( local.k = 1; local.k <= 5; local.k++ ){
			local.m = level.coop_psqM[level.coop_psqN][local.k]
			if( local.m == NIL || local.m == NULL ){ continue }
			if( !isAlive local.m ){ local.m remove }
		}
	}
	if( local.c == "paim" ){""")], "latin-1")

patch("p4_pitch.py", [
    ("""        G.cmd("others", n=1)        # TEST SET-UP: the rest of the squad is hidden for the stills
""", """        # TEST SET-UP for the stills: the squad's hold point goes 450u to the gunner's left, behind the camera
        ms = re.search(r"mg setup k=1 mode=(\\w) gun=\\(([^)]*)\\) yaw=([-\\d.]+)", m.group(0))
        gunp, gyaw = G.vec(ms.group(2)), float(ms.group(3))
        G.cmd("hold", x="%.0f" % (gunp[0] + math.cos(math.radians(gyaw + 90)) * 450),
              y="%.0f" % (gunp[1] + math.sin(math.radians(gyaw + 90)) * 450), z=Z, yaw=YAW)
        time.sleep(float(OPT.get("clear", 9)))
"""),
    ("""        # a player takes it
""", """        G.cmd("nocorpse")           # TEST SET-UP: the dead gunner is taken out of the picture
        time.sleep(0.5)
        G.cmd("camg", n=SIDE[0], yaw=SIDE[1], z=CZ, pitch=28)
        shot("rest_side_clean", 45 if not OPT.get("room") else 70)
        G.cmd("camg", n=SIDE[0] + 10, yaw=150, z=CZ + 30, pitch=28)
        shot("rest_rear_clean", 50 if not OPT.get("room") else 75)
        # a player takes it
"""),
    ("""            for el, fire in ((0, 0), (12, 0), (20, 0), (20, 1), (-10, 0), (0, 0)):
                G.cmd("paim", pitch=el, yaw=0)
                time.sleep(1.0)
""", """            R.step(["set cl_pitchspeed 40", "wait 100"], timeout=20)
            cur = 0
            for el, fire in ((0, 0), (12, 0), (20, 0), (20, 1), (25, 0), (-10, 0), (0, 0)):
                if el != cur:
                    key = "lookup" if el > cur else "lookdown"
                    R.step(["+" + key, "wait %d" % int(abs(el - cur) / 40.0 * 1000), "-" + key, "wait 200"], timeout=30)
                    cur = el
                time.sleep(0.8)
"""),
])
