"""Test overlay pk3 for the private harness copy (never shipped): harness plumbing + every file under assets/.

    python tools/mkov_dbs.py <out.pk3>

Plumbing = the ADS lanes' ovbase_1021.pk3 (marker shader + the RELEASED coop_mod/weather.scr with the coop_isPoll test
thread, built by ads_twohand_2026-10-11/tools/mkbase.py) with two test-only additions to that thread:
    shotgun ammo on every give;   cvar coop_dbsDrop <n>: spawn the tik named by coop_dbsDropTik on the ground 70 u in
    front of player 1 (a real weapon item: it can be walked over / used), prints ^~^~^ DBSDROP.
"""
import sys, os, re, zipfile
import dbslib as L

BASE = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad\ads2h\ovbase_1021.pk3"
TOP = ('models', 'scripts', 'sound', 'textures', 'coop_mod', 'ui', 'global', 'ubersound')

DROP = (
    '\t\tlocal.d = getcvar( "coop_dbsDrop" )\n'
    '\t\tif( local.d != "" && local.d != local.lastD && $player != NULL && $player.size >= 1 ){\n'
    '\t\t\tlocal.lastD = local.d\n'
    '\t\t\tlocal.p = $player[1]\n'
    '\t\t\tlocal.fw = angles_toforward ( 0 local.p.viewangles[1] 0 )\n'
    '\t\t\tlocal.dist = float( getcvar( "coop_dbsDropDist" ) )\n'
    '\t\t\tlocal.dyaw = float( getcvar( "coop_dbsDropYaw" ) )\n'
    '\t\t\tlocal.dtik = getcvar( "coop_dbsDropTik" )\n'
    '\t\t\tlocal.o = local.p.origin + local.fw * local.dist + ( 0 0 24 )\n'
    '\t\t\tlocal.e = spawn local.dtik "origin" local.o\n'
    '\t\t\tlocal.e.angles = ( 0 ( local.p.viewangles[1] + local.dyaw ) 0 )\n'
    '\t\t\tprintln( "^~^~^ DBSDROP " + local.d + " at " + local.o )\n'
    '\t\t}\n'
    # a script camera looking at player 1 from any side (cg_3rd_person only ever looks along the player's facing)
    '\t\tlocal.c = getcvar( "coop_dbsCam" )\n'
    '\t\tif( local.c != "" && local.c != local.lastC && $player != NULL && $player.size >= 1 ){\n'
    '\t\t\tlocal.lastC = local.c\n'
    '\t\t\tlocal.p = $player[1]\n'
    '\t\t\tif( local.c == "0" ){\n'
    '\t\t\t\tcueplayer\n'
    '\t\t\t}else{\n'
    '\t\t\t\tif( local.hasCam == 0 ){\n'
    '\t\t\t\t\tlocal.cam = spawn Camera\n'
    '\t\t\t\t\tlocal.hasCam = 1\n'
    '\t\t\t\t}\n'
    '\t\t\t\tlocal.cyaw = local.p.viewangles[1] + float( getcvar( "coop_dbsCamYaw" ) )\n'
    '\t\t\t\tlocal.cdist = float( getcvar( "coop_dbsCamDist" ) )\n'
    '\t\t\t\tlocal.cup = float( getcvar( "coop_dbsCamUp" ) )\n'
    '\t\t\t\tlocal.clz = float( getcvar( "coop_dbsCamLookZ" ) )\n'
    '\t\t\t\tlocal.cdir = angles_toforward ( 0 local.cyaw 0 )\n'
    '\t\t\t\tlocal.look = local.p.origin + ( 0 0 local.clz )\n'
    '\t\t\t\tlocal.pos = local.look + local.cdir * local.cdist + ( 0 0 local.cup )\n'
    '\t\t\t\tlocal.cam.origin = local.pos\n'
    '\t\t\t\tlocal.cam.angles = vector_toangles ( local.look - local.pos )\n'
    '\t\t\t\tcuecamera local.cam\n'
    '\t\t\t}\n'
    '\t\t\tprintln( "^~^~^ DBSCAM " + local.c )\n'
    '\t\t}\n')


def weather(src):
    s = src.replace('\r\n', '\n')
    a = '\tlocal.lastF = ""\n'
    assert s.count(a) == 1
    s = s.replace(a, a + '\tlocal.lastD = ""\n\tlocal.lastC = ""\n\tlocal.hasCam = 0\n')
    b = '\t\t\t\tlocal.p ammo pistol 400\n'
    assert s.count(b) == 1
    s = s.replace(b, b + '\t\t\t\tlocal.p ammo shotgun 400\n')
    k = s.index('coop_is_test:')
    w = s.index('\t\twaitframe\n', k)
    s = s[:w] + DROP + s[w:]
    d = 0                                   # running-depth brace scan (TRAPS: never negative, 0 at column-0 labels)
    for i, l in enumerate(s.splitlines()):
        c = l.split('//')[0]
        if re.match(r'^[A-Za-z_][A-Za-z0-9_ ]*:', c):
            assert d == 0, (i + 1, l)
        d += c.count('{') - c.count('}')
        assert d >= 0, (i + 1, l)
    assert d == 0
    assert '\u2014' not in s and '(-' not in s[k:]
    return s.replace('\n', '\r\n')


def main():
    out = sys.argv[1]
    n = 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        b = zipfile.ZipFile(BASE)
        for i in b.infolist():
            data = b.read(i.filename)
            if i.filename == 'coop_mod/weather.scr':
                data = weather(data.decode('latin-1')).encode('latin-1')
            z.writestr(i.filename, data)
        for d, _, fs in os.walk(L.ASSETS):
            for f in fs:
                p = os.path.join(d, f)
                arc = os.path.relpath(p, L.ASSETS).replace(os.sep, '/')
                if arc.split('/')[0] not in TOP:
                    continue
                z.write(p, arc); n += 1
        # --var s46=0.46 ... : TEST-ONLY copies of the tik at another scale (models/weapons/coop_dbshotgun_<tag>.tik)
        base = open(os.path.join(L.ASSETS, 'models', 'weapons', 'coop_dbshotgun.tik')).read()
        for v in [x for x in sys.argv[2:] if '=' in x]:
            tag, sc = v.split('=')
            assert '\tscale 0.52\n' in base
            z.writestr('models/weapons/coop_dbshotgun_%s.tik' % tag, base.replace('\tscale 0.52\n', '\tscale %s\n' % sc))
            print('variant', tag, 'scale', sc)
    print('wrote', out, n, 'asset files', os.path.getsize(out), 'bytes')


if __name__ == '__main__':
    main()
