"""Test overlay pk3 for the private harness copy (never shipped): harness plumbing + every file under assets/.

    python tools/mkov_dbs.py <out.pk3> [--armory] [--notps]

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

# armory tests: challenge progress through the mod's own chal_bump (what a kill calls), a status line, one test AI
# armed through the mod's AI weapon path (aihandler.scr::coop_actorArm) and killed on a second command
HOOKS = (
    '\t\tlocal.b = getcvar( "coop_dbsBump" )\n'
    '\t\tif( local.b != "" && local.b != local.lastB && $player != NULL && $player.size >= 1 ){\n'
    '\t\t\tlocal.lastB = local.b\n'
    '\t\t\tlocal.bs = getcvar( "coop_dbsBumpStat" )\n'
    '\t\t\tlocal.bn = int( getcvar( "coop_dbsBumpN" ) )\n'
    '\t\t\twaitthread coop_mod/challenges.scr::chal_bump $player[1] local.bs local.bn\n'
    '\t\t\tprintln( "^~^~^ DBSBUMP " + local.b + " " + local.bs + " " + local.bn )\n'
    '\t\t}\n'
    '\t\tlocal.q = getcvar( "coop_dbsStat" )\n'
    '\t\tif( local.q != "" && local.q != local.lastQ && $player != NULL && $player.size >= 1 ){\n'
    '\t\t\tlocal.lastQ = local.q\n'
    '\t\t\tlocal.p = $player[1]\n'
    '\t\t\twaitthread coop_mod/challenges.scr::chal_ensure local.p\n'
    '\t\t\tlocal.v1 = local.p.flags["coop_chal_unlocks"]\n'
    '\t\t\tif( local.v1 == NIL ){ local.v1 = "NIL" }\n'
    '\t\t\tlocal.v2 = local.p.flags["coop_loSlot1"]\n'
    '\t\t\tif( local.v2 == NIL ){ local.v2 = "NIL" }\n'
    '\t\t\tlocal.v3 = local.p.flags["coop_loSlotId1"]\n'
    '\t\t\tif( local.v3 == NIL ){ local.v3 = "NIL" }\n'
    '\t\t\tlocal.v4 = local.p.flags["coop_loFin1"]\n'
    '\t\t\tif( local.v4 == NIL ){ local.v4 = "NIL" }\n'
    '\t\t\tlocal.v5 = local.p.flags["coop_chalP_wpn_shotgun_v"]\n'
    '\t\t\tif( local.v5 == NIL ){ local.v5 = "NIL" }\n'
    '\t\t\tlocal.v6 = local.p.flags["coop_chalP_wpn_shotgun"]\n'
    '\t\t\tif( local.v6 == NIL ){ local.v6 = "NIL" }\n'
    '\t\t\tprintln( "^~^~^ DBSSTAT " + local.q + " slot1=" + local.v2 + " id1=" + local.v3 + " fin1=" + local.v4 + " v=" + local.v5 + " base=" + local.v6 + " lock=" + getcvar( "coop_lockLoadout" ) + " sw=" + getcvar( "coop_dbShotgun" ) )\n'
    '\t\t\tprintln( "^~^~^ DBSUNLOCKS " + local.q + " " + local.v1 )\n'
    '\t\t}\n'
    '\t\tlocal.m = getcvar( "coop_dbsMortal" )\n'
    '\t\tif( local.m != "" && local.m != local.lastM && $player != NULL && $player.size >= 1 ){\n'
    '\t\t\tlocal.lastM = local.m\n'
    '\t\t\t$player[1] takedamage\n'
    '\t\t\tprintln( "^~^~^ DBSMORTAL " + local.m )\n'
    '\t\t}\n'
    '\t\tlocal.a = getcvar( "coop_dbsAI" )\n'
    '\t\tif( local.a != "" && local.a != local.lastA && $player != NULL && $player.size >= 1 ){\n'
    '\t\t\tlocal.lastA = local.a\n'
    '\t\t\tlocal.p = $player[1]\n'
    '\t\t\tlocal.fw = angles_toforward ( 0 local.p.viewangles[1] 0 )\n'
    '\t\t\tif( local.a == "kill" ){\n'
    '\t\t\t\tif( level.coop_dbsAI != NIL && level.coop_dbsAI != NULL ){\n'
    '\t\t\t\t\tlevel.coop_dbsAI takedamage\n'
    '\t\t\t\t\tlevel.coop_dbsAI kill\n'
    '\t\t\t\t\tprintln( "^~^~^ DBSAI killed" )\n'
    '\t\t\t\t}\n'
    '\t\t\t}else{\n'
    '\t\t\t\tlevel.coop_dbsAI = spawn models/human/german_wehrmact_soldier.tik "origin" ( local.p.origin + local.fw * 120.0 )\n'
    '\t\t\t\tlevel.coop_dbsAI.angles = ( 0 ( local.p.viewangles[1] + 180.0 ) 0 )\n'
    '\t\t\t\twait 1\n'
    '\t\t\t\tlevel.coop_dbsAI waitthread coop_mod/aihandler.scr::coop_actorArm "models/weapons/coop_dbshotgun.tik"\n'
    '\t\t\t\tprintln( "^~^~^ DBSAI armed " + local.a )\n'
    '\t\t\t}\n'
    '\t\t}\n'
)


def weather(src, keepunlocks=False):
    s = src.replace('\r\n', '\n')
    a = '\tlocal.lastF = ""\n'
    assert s.count(a) == 1
    s = s.replace(a, a + '\tlocal.lastD = ""\n\tlocal.lastC = ""\n\tlocal.hasCam = 0\n\tlocal.lastB = ""\n\tlocal.lastQ = ""\n\tlocal.lastA = ""\n\tlocal.lastM = ""\n')
    b = '\t\t\t\tlocal.p ammo pistol 400\n'
    assert s.count(b) == 1
    s = s.replace(b, b + '\t\t\t\tlocal.p ammo shotgun 400\n')
    k = s.index('coop_is_test:')
    w = s.index('\t\twaitframe\n', k)
    s = s[:w] + DROP + HOOKS + s[w:]
    if keepunlocks:                      # armory runs: the test `give` must not overwrite the player's unlock record
        u = '\t\t\t\tlocal.p.flags["coop_chal_unlocks"] = local.t'
        assert s.count(u) == 1
        s = s.replace(u, '\t\t\t\t//' + u.strip())
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
                data = weather(data.decode('latin-1'), '--armory' in sys.argv).encode('latin-1')
            z.writestr(i.filename, data)
        for d, _, fs in os.walk(L.ASSETS):
            for f in fs:
                p = os.path.join(d, f)
                arc = os.path.relpath(p, L.ASSETS).replace(os.sep, '/')
                if arc.split('/')[0] not in TOP:
                    continue
                z.write(p, arc); n += 1
        # the first-person rows: the RELEASED fixes-pak fps_anims_shotgun.txt + our rows block before its closing brace
        # (the shared file is not edited or staged whole - other lanes stage rows in it too)
        fx = open(os.path.join(L.DOCS, 'tools', 'assets', 'fixes', 'models', 'player', 'base', 'fps_anims_shotgun.txt'), 'rb').read().decode('latin-1')
        rows = open(os.path.join(L.PROP, 'rows', 'fps_rows_coop_dbshotgun.txt'), 'rb').read().decode('latin-1').replace('\r\n', '\n')
        nl = '\r\n' if '\r\n' in fx else '\n'
        k = fx.rstrip().rfind('}')
        z.writestr('models/player/base/fps_anims_shotgun.txt', (fx[:k] + rows.replace('\n', nl) + fx[k:]).encode('latin-1'))
        # third person: the INSTALLED alias file + our rows, the INSTALLED torso state file + our five rows
        # (rows/tps_rows_coop_dbshotgun.txt, wiring/patch_torso_dbs.py). --notps leaves both out.
        if '--notps' not in sys.argv:
            import importlib.util
            sp = importlib.util.spec_from_file_location('weapon_hd_vfs', os.path.join(L.DOCS, 'tools', 'weapon_hd', 'vfs.py'))
            HV = importlib.util.module_from_spec(sp); sp.loader.exec_module(HV)
            sp = importlib.util.spec_from_file_location('patch_torso_dbs', os.path.join(L.PROP, 'wiring', 'patch_torso_dbs.py'))
            PT = importlib.util.module_from_spec(sp); sp.loader.exec_module(PT)
            al = HV.read('models/player/base/anims_shotgun.txt').decode('latin-1')
            trow = open(os.path.join(L.PROP, 'rows', 'tps_rows_coop_dbshotgun.txt'), 'rb').read().decode('latin-1').replace('\r\n', '\n')
            nl2 = '\r\n' if '\r\n' in al else '\n'
            k2 = al.rstrip().rfind('}')
            z.writestr('models/player/base/anims_shotgun.txt', (al[:k2] + trow.replace('\n', nl2) + al[k2:]).encode('latin-1'))
            st = HV.read('coop_mod/player_Torso.st').decode('latin-1')
            z.writestr('coop_mod/player_Torso.st', PT.patch(st).encode('latin-1'))
            print('third person: alias rows + torso state rows added')
        # --armory: the own armory entry (wiring/stage_armory_dbs.py -> armory_ov/: the mod-tree files edited + what the
        # generators wrote). coop_defaults.cfg is ahead of the release in the mod tree: the INSTALLED file + the same edit.
        if '--armory' in sys.argv:
            import importlib.util
            sp = importlib.util.spec_from_file_location('weapon_hd_vfs', os.path.join(L.DOCS, 'tools', 'weapon_hd', 'vfs.py'))
            HV2 = importlib.util.module_from_spec(sp); sp.loader.exec_module(HV2)
            sys.path.insert(0, os.path.join(L.PROP, 'wiring'))
            import stage_armory_dbs as SA
            ov = os.path.join(L.PROP, 'armory_ov')
            k3 = 0
            for rel in open(os.path.join(ov, 'MANIFEST.txt')).read().split():
                if rel == 'coop_defaults.cfg':
                    z.writestr(rel, SA.defaults(HV2.read(rel).decode('latin-1')).encode('latin-1'))
                else:
                    z.write(os.path.join(ov, rel.replace('/', os.sep)), rel)
                k3 += 1
            print('armory: %d files from armory_ov' % k3)
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
