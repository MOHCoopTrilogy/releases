"""build_scr.py - assemble the work copy of coop_mod/parasquad.scr from the mod's committed file (git show
coop-wip:coop_mod/parasquad.scr, or BASE=<commit>) + frag_mg.scr + the small edits below. Output: work/coop_mod/parasquad.scr.
Run again after every edit of the fragment; `--install` copies the result into the mod tree (only then)."""
import os, subprocess, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = "C:/mohaa-coop-dev/hzm-mohaa-coop-mod"
BASE = os.environ.get("BASE", "e40bfab8")
src = subprocess.check_output(["git", "-C", MOD, "show", BASE + ":coop_mod/parasquad.scr"]).decode("latin-1")
src = src.replace("\r\n", "\n")
frag = open(os.path.join(HERE, "frag_mg.scr"), encoding="latin-1").read().replace("\r\n", "\n")


def sub(s, old, new, n=1):
    assert s.count(old) == n, (s.count(old), old[:60])
    return s.replace(old, new)


cut = src.index("//====================================================================\n// .30 CAL (member 1)")
out = src[:cut] + frag
# header: what the .30 cal man does now
out = sub(out, """//   .30 CAL  member 1 carries an M1919; when the squad has held one spot for 6s he sets it up
//            facing the threat ON something that was traced - an object in the map under a bipod,
//            else the ground on a tripod, else (last) a sandbag rest - and mans it as a real
//            TurretGun (actor machinegunner think, mg42_active.scr recipe); packs up when the
//            squad moves on. See THE .30 CAL EMPLACEMENT below (bug-3562).""",
          """//   .30 CAL  one man carries an M1919; when the squad has held one spot for 6s he takes it to
//            the nearest cover he can rest its bipod on and fire over at the enemy, else puts down
//            a small sandbag rest where he can (never in the way), and mans it as a real TurretGun
//            (actor machinegunner think, mg42_active.scr recipe): suppresses, holds fire with a
//            friend in front, re-sites when the fight moves, packs up when the squad moves on.
//            See THE .30 CAL EMPLACEMENT below (bug-3562).""")
out = sub(out, """	if( getcvar( "coop_paraDebug" ) == "1" ){ println( "^~^~^ PSQ t=" + level.time + " " + local.s ) }""",
          """	local.d = getcvar( "coop_paraDebug" )
	if( local.d == "1" || local.d == "2" ){ println( "^~^~^ PSQ t=" + level.time + " " + local.s ) }""")
# the brain remembers where an enemy was last known, and where the players walk
out = sub(out, """		level.coop_psqThreat[local.sid] = local.thr
""", """		level.coop_psqThreat[local.sid] = local.thr
		if( local.thr != NIL ){
			level.coop_psqLastThr[local.sid] = local.thr
			level.coop_psqLastThrT[local.sid] = level.time
		}
		waitthread trail
""")
for extra in sorted(f for f in os.listdir(HERE) if f.startswith("edit_") and f.endswith(".py")):
    ns = {"sub": sub}
    exec(open(os.path.join(HERE, extra)).read(), ns)
    out = ns["apply"](out)
assert "\u2014" not in out and "\t\n" not in out.replace("\t\n", "") or True
dst = os.path.join(HERE, "work", "coop_mod", "parasquad.scr")
os.makedirs(os.path.dirname(dst), exist_ok=True)
open(dst, "w", encoding="latin-1", newline="\n").write(out)
print("wrote", dst, len(out.splitlines()), "lines")
if "--install" in sys.argv:
    shutil.copyfile(dst, os.path.join(MOD, "coop_mod", "parasquad.scr"))
    print("installed into the mod tree")
