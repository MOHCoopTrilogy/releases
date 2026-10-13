"""fix_p4c.py - driver: 'pcap' pins the pitch of the gun a player is on (with the side camera cued the client's command
angles follow the camera, so the test cannot look up or down itself); camg does not count hidden squad mates.
p4_pitch.py: the player's angles through pcap; the others hidden again before the player stills."""
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


patch("p3_drv.scr", [
    ("""	if( local.c == "paim" ){""", """	if( local.c == "pcap" ){
		// TEST SET-UP for stills: the pitch of gun level.p3_gunEnt is pinned p3_pitch degrees UP (negative = down) by
		// closing its pitch caps on that angle; p3_n 0 = the caps of mgSetup again
		if( level.p3_gunEnt != NIL && level.p3_gunEnt != NULL ){
			if( int( getcvar( "p3_n" ) ) == 1 ){
				local.el = 0 - ( float( getcvar( "p3_pitch" ) ) )
				level.p3_gunEnt pitchCaps ( local.el local.el 0 )
			} else {
				level.p3_gunEnt pitchCaps ( -25 12 0 )
			}
		}
	}
	if( local.c == "paim" ){"""),
    ("""			if( int( getcvar( "p3_n" ) ) == 1 ){
				local.m rendereffects "-coopboss\"""", """			level.p3_hidden = int( getcvar( "p3_n" ) )
			if( int( getcvar( "p3_n" ) ) == 1 ){
				local.m rendereffects "-coopboss\""""),
    ("""				if( !isAlive local.m ){ continue }
				local.v = local.m.origin - local.eye""", """				if( !isAlive local.m ){ continue }
				if( level.p3_hidden == 1 ){ continue }
				local.v = local.m.origin - local.eye"""),
], "latin-1")

patch("p4_pitch.py", [
    ("""            R.step(["set cl_pitchspeed 40", "wait 100"], timeout=20)
            cur = 0
            for el, fire in ((0, 0), (12, 0), (20, 0), (20, 1), (25, 0), (-10, 0), (0, 0)):
                if el != cur:
                    key = "lookup" if el > cur else "lookdown"
                    R.step(["+" + key, "wait %d" % int(abs(el - cur) / 40.0 * 1000), "-" + key, "wait 200"], timeout=30)
                    cur = el
                time.sleep(0.8)
""", """            for el, fire in ((0, 0), (12, 0), (20, 0), (20, 1), (25, 0), (-10, 0), (0, 0)):
                G.cmd("pcap", pitch=el, n=1)      # TEST SET-UP: the pitch is pinned for the still
                time.sleep(1.0)
"""),
    ("""            R.step(["set cg_3rd_person 0", "wait 300"], timeout=30)
            G.cmd("nocam")""", """            G.cmd("pcap", pitch=0, n=0)
            R.step(["set cg_3rd_person 0", "wait 300"], timeout=30)
            G.cmd("nocam")"""),
    ("""        G.cmd("nocorpse")           # TEST SET-UP: the dead gunner is taken out of the picture
""", """        G.cmd("nocorpse")           # TEST SET-UP: the dead gunner is taken out of the picture
        G.cmd("others", n=1)
"""),
])
