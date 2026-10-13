"""fix_p4b.py - stills: the others are hidden WITH their star (rendereffects -coopboss), not sent away; 'behind' finds
the ground with a trace that passes the gun."""
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
    ("""			if( int( getcvar( "p3_n" ) ) == 1 ){ local.m hide } else { local.m show }""",
     """			if( int( getcvar( "p3_n" ) ) == 1 ){
				local.m rendereffects "-coopboss"
				local.m hide
			} else {
				local.m rendereffects "+coopboss"
				local.m show
			}"""),
    ("""			local.g = waitthread coop_mod/officer.scr::coop_find_ground ( local.b - ( 0 0 22 ) )
			if( local.g == NIL ){ local.g = local.b }""",
     """			local.tr = traced ( local.b + ( 0 0 6 ) ) ( local.b - ( 0 0 140 ) ) local.gg.entnum ( 0 0 0 ) ( 0 0 0 ) 1
			local.g = local.tr["endpos"]"""),
], "latin-1")

s = io.open("p4_pitch.py", encoding="utf-8").read()
a = s.index("        # TEST SET-UP for the stills: the squad's hold point goes 450u")
b = s.index("        for el, fire in ((0, 0), (12, 0), (20, 0), (20, 1), (25, 0), (-10, 0), (0, 0)):\n            G.cmd(\"aimp\"")
s = s[:a] + "        G.cmd(\"others\", n=1)        # TEST SET-UP: the rest of the squad is hidden for the stills\n" + s[b:]
io.open("p4_pitch.py", "w", encoding="utf-8", newline="\n").write(s)
print("patched p4_pitch.py")
