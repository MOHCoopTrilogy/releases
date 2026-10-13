"""Repaint test overlay: the harness plumbing built on the DEPLOYED weather.scr (the double-barrel lane's
build/ovbase_cur.pk3, read only: marker shader + coop_mod/weather.scr with the coop_isPoll test thread) + a TEST-ONLY
prop spawner (cvar coop_isProp = a new number -> up to three guns, tiks in coop_isP1 / P2 / P3, laid on the ground in
front of the player) +, unless --base, the staged files under ../assets whose game path matches --only (regex).

    python mkov.py <out.pk3> [--base] [--only <regex>]
"""
import sys, os, re, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, "..", "assets"))
BASE = os.path.normpath(os.path.join(HERE, "..", "..", "dbshotgun_2026-10-12", "build", "ovbase_cur.pk3"))


def prop_poll(src):
    k = src.rfind("coop_is_test:")
    assert k > 0
    head, body = src[:k], src[k:]
    nl = "\r\n" if "\r\n" in body else "\n"
    a1 = '\tlocal.lastF = ""' + nl
    assert body.count(a1) == 1
    body = body.replace(a1, a1 + '\tlocal.lastP = ""' + nl + '\tlevel.rp_have[1] = 0' + nl + '\tlevel.rp_have[2] = 0' + nl
                        + '\tlevel.rp_have[3] = 0' + nl)
    a2 = "\t\twaitframe" + nl + "\t}" + nl + "}end"
    assert body.count(a2) == 1, body[-200:]
    L = ['\t\tlocal.pr = getcvar( "coop_isProp" )',
         '\t\tif( local.pr != "" && local.pr != local.lastP && $player != NULL && $player.size >= 1 ){',
         '\t\t\tlocal.lastP = local.pr',
         '\t\t\tlocal.p = $player[1]',
         '\t\t\tlocal.ya = local.p.viewangles[1]',
         '\t\t\tlocal.va = ( 0 local.ya 0 )',
         '\t\t\tlocal.fw = angles_toforward local.va',
         '\t\t\tlocal.y2 = local.ya + 90',
         '\t\t\tlocal.base = local.p.origin + ( 0 0 7 )',
         '\t\t\tfor( local.i = 1; local.i <= 3; local.i++ ){',
         '\t\t\t\tif( level.rp_have[local.i] == 1 ){',
         '\t\t\t\t\tlevel.rp_m[local.i] remove',
         '\t\t\t\t\tlevel.rp_have[local.i] = 0',
         '\t\t\t\t}',
         '\t\t\t\tlocal.t = getcvar( "coop_isP" + local.i )',
         '\t\t\t\tif( local.t != "" && local.t != "none" ){',
         '\t\t\t\t\tlocal.m = spawn script_model',
         '\t\t\t\t\tlocal.m model local.t',
         '\t\t\t\t\tif( getcvar( "coop_isPmode" ) == "float" ){',
         '\t\t\t\t\t\tlocal.up = 30 + local.i * 15',
         '\t\t\t\t\t\tlocal.m.origin = local.p.origin + local.fw * 48 + ( 0 0 local.up )',
         '\t\t\t\t\t\tlocal.yy = local.y2',
         '\t\t\t\t\t\tif( getcvar( "coop_isPflip" ) == "1" ){ local.yy = local.ya + 270 }',
         '\t\t\t\t\t\tlocal.m.angles = ( 0 local.yy 180 )',
         '\t\t\t\t\t}else{',
         '\t\t\t\t\t\tlocal.m.origin = local.base + local.fw * ( 13 + local.i * 17 )',
         '\t\t\t\t\t\tlocal.roll = 90',
         '\t\t\t\t\t\tif( getcvar( "coop_isPflip" ) == "1" ){ local.roll = 270 }',
         '\t\t\t\t\t\tlocal.m.angles = ( 0 local.y2 local.roll )',
         '\t\t\t\t\t}',
         '\t\t\t\t\tlocal.m notsolid',
         '\t\t\t\t\tlevel.rp_m[local.i] = local.m',
         '\t\t\t\t\tlevel.rp_have[local.i] = 1',
         '\t\t\t\t}',
         '\t\t\t}',
         '\t\t\tprintln( "^~^~^ ISTEST props " + local.pr + " at " + local.base )',
         '\t\t}', '']
    body = body.replace(a2, nl.join(L) + a2)
    new = head + body
    d = 0
    for i, l in enumerate(new.splitlines()):
        c = l.split("//")[0]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_ ]*:", c):
            assert d == 0, ("depth at label", i + 1, l[:50])
        d += c.count("{") - c.count("}")
        assert d >= 0, (i + 1, l)
    assert d == 0
    return new


def main():
    out = sys.argv[1]
    base_only = "--base" in sys.argv
    only = re.compile(sys.argv[sys.argv.index("--only") + 1], re.I) if "--only" in sys.argv else None
    names = []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        b = zipfile.ZipFile(BASE)
        for i in b.infolist():
            data = b.read(i.filename)
            if i.filename == "coop_mod/weather.scr":
                data = prop_poll(data.decode("latin-1")).encode("latin-1")
            z.writestr(i.filename, data)
        if not base_only:
            for d, _, fs in os.walk(ASSETS):
                for f in fs:
                    p = os.path.join(d, f)
                    rel = os.path.relpath(p, ASSETS).replace(os.sep, "/")
                    if only and not only.search(rel):
                        continue
                    z.write(p, rel); names.append(rel)
    print("wrote", out, len(names), "staged files", names, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
