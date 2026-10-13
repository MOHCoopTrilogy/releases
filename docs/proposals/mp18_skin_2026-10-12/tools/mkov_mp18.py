"""MP18 skin test overlay: the ADS lanes' harness plumbing (ovbase_1021.pk3: marker shader + coop_mod/weather.scr
with the test thread) + a TEST-ONLY prop spawner (cvar coop_isProp: two MP18s and an MP40 laid on the ground in front
of the player) +, unless --base, every file under ../assets (the staged textures, game paths).

    python mkov_mp18.py <out.pk3> [--base]
"""
import sys, os, re, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, "..", "assets"))
BASE = (r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9"
        r"\scratchpad\adssmg\ovbase_1021.pk3")


def prop_poll(src):
    k = src.rfind("coop_is_test:")
    assert k > 0
    head, body = src[:k], src[k:]
    nl = "\r\n" if "\r\n" in body else "\n"
    a1 = '\tlocal.lastF = ""' + nl
    assert body.count(a1) == 1
    body = body.replace(a1, a1 + '\tlocal.lastP = ""' + nl)
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
         '\t\t\tif( level.mp18_have == 1 ){',
         '\t\t\t\tlevel.mp18_m1 remove',
         '\t\t\t\tlevel.mp18_m2 remove',
         '\t\t\t\tlevel.mp18_m3 remove',
         '\t\t\t}',
         '\t\t\tlocal.m1 = spawn script_model "model" "models/weapons/mp40_mp18.tik"',
         '\t\t\tlocal.m1.origin = local.base + local.fw * 30',
         '\t\t\tlocal.m1.angles = ( 0 local.y2 90 )',
         '\t\t\tlocal.m1 notsolid',
         '\t\t\tlocal.m2 = spawn script_model "model" "models/weapons/mp40_mp18.tik"',
         '\t\t\tlocal.m2.origin = local.base + local.fw * 47',
         '\t\t\tlocal.m2.angles = ( 0 local.y2 270 )',
         '\t\t\tlocal.m2 notsolid',
         '\t\t\tlocal.m3 = spawn script_model "model" "models/weapons/mp40.tik"',
         '\t\t\tlocal.m3.origin = local.base + local.fw * 64',
         '\t\t\tlocal.m3.angles = ( 0 local.y2 90 )',
         '\t\t\tlocal.m3 notsolid',
         '\t\t\tlevel.mp18_have = 1',
         '\t\t\tlevel.mp18_m1 = local.m1',
         '\t\t\tlevel.mp18_m2 = local.m2',
         '\t\t\tlevel.mp18_m3 = local.m3',
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
    n = 0
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
                    z.write(p, os.path.relpath(p, ASSETS).replace(os.sep, "/")); n += 1
    print("wrote", out, n, "staged files", os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
