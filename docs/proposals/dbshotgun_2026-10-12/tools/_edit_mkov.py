"""one-off editor (2026-10-13): mkov_dbs.py gets the armory test hooks, --armory in place of --wire. Already applied."""
import sys
p = sys.argv[1]
s = open(p, encoding='utf-8').read()
if 'HOOKS = (' in s:
    print('already applied'); sys.exit(0)
a = "    '\\t\\t\\tprintln( \"^~^~^ DBSCAM \" + local.c )\\n'\n    '\\t\\t}\\n')\n"
assert s.count(a) == 1, s.count(a)
H = [
    '\t\tlocal.b = getcvar( "coop_dbsBump" )',
    '\t\tif( local.b != "" && local.b != local.lastB && $player != NULL && $player.size >= 1 ){',
    '\t\t\tlocal.lastB = local.b',
    '\t\t\tlocal.bs = getcvar( "coop_dbsBumpStat" )',
    '\t\t\tlocal.bn = int( getcvar( "coop_dbsBumpN" ) )',
    '\t\t\twaitthread coop_mod/challenges.scr::chal_bump $player[1] local.bs local.bn',
    '\t\t\tprintln( "^~^~^ DBSBUMP " + local.b + " " + local.bs + " " + local.bn )',
    '\t\t}',
    '\t\tlocal.q = getcvar( "coop_dbsStat" )',
    '\t\tif( local.q != "" && local.q != local.lastQ && $player != NULL && $player.size >= 1 ){',
    '\t\t\tlocal.lastQ = local.q',
    '\t\t\tlocal.p = $player[1]',
    '\t\t\twaitthread coop_mod/challenges.scr::chal_ensure local.p',
    '\t\t\tlocal.v1 = local.p.flags["coop_chal_unlocks"]',
    '\t\t\tif( local.v1 == NIL ){ local.v1 = "NIL" }',
    '\t\t\tlocal.v2 = local.p.flags["coop_loSlot1"]',
    '\t\t\tif( local.v2 == NIL ){ local.v2 = "NIL" }',
    '\t\t\tlocal.v3 = local.p.flags["coop_loSlotId1"]',
    '\t\t\tif( local.v3 == NIL ){ local.v3 = "NIL" }',
    '\t\t\tlocal.v4 = local.p.flags["coop_loFin1"]',
    '\t\t\tif( local.v4 == NIL ){ local.v4 = "NIL" }',
    '\t\t\tlocal.v5 = local.p.flags["coop_chalP_wpn_shotgun_v"]',
    '\t\t\tif( local.v5 == NIL ){ local.v5 = "NIL" }',
    '\t\t\tlocal.v6 = local.p.flags["coop_chalP_wpn_shotgun"]',
    '\t\t\tif( local.v6 == NIL ){ local.v6 = "NIL" }',
    '\t\t\tprintln( "^~^~^ DBSSTAT " + local.q + " slot1=" + local.v2 + " id1=" + local.v3 + " fin1=" + local.v4 + " v=" + local.v5 + " base=" + local.v6 + " lock=" + getcvar( "coop_lockLoadout" ) + " sw=" + getcvar( "coop_dbShotgun" ) )',
    '\t\t\tprintln( "^~^~^ DBSUNLOCKS " + local.q + " " + local.v1 )',
    '\t\t}',
    '\t\tlocal.a = getcvar( "coop_dbsAI" )',
    '\t\tif( local.a != "" && local.a != local.lastA && $player != NULL && $player.size >= 1 ){',
    '\t\t\tlocal.lastA = local.a',
    '\t\t\tlocal.p = $player[1]',
    '\t\t\tlocal.fw = angles_toforward ( 0 local.p.viewangles[1] 0 )',
    '\t\t\tif( local.a == "kill" ){',
    '\t\t\t\tif( level.coop_dbsAI != NIL && level.coop_dbsAI != NULL ){',
    '\t\t\t\t\tlevel.coop_dbsAI damage local.p 5000 local.p level.coop_dbsAI.origin ( 0 0 0 ) ( 0 0 1 ) 0 0 18 5',
    '\t\t\t\t\tprintln( "^~^~^ DBSAI killed" )',
    '\t\t\t\t}',
    '\t\t\t}else{',
    '\t\t\t\tlevel.coop_dbsAI = spawn models/human/german_wehrmact_soldier.tik "origin" ( local.p.origin + local.fw * 120.0 )',
    '\t\t\t\tlevel.coop_dbsAI.angles = ( 0 ( local.p.viewangles[1] + 180.0 ) 0 )',
    '\t\t\t\twait 1',
    '\t\t\t\tlevel.coop_dbsAI waitthread coop_mod/aihandler.scr::coop_actorArm "models/weapons/coop_dbshotgun.tik"',
    '\t\t\t\tprintln( "^~^~^ DBSAI armed " + local.a )',
    '\t\t\t}',
    '\t\t}',
]
hooks = ('\n# armory tests: challenge progress through the mod\'s own chal_bump (what a kill calls), a status line, one test AI\n'
         '# armed through the mod\'s AI weapon path (aihandler.scr::coop_actorArm) and killed on a second command\n'
         'HOOKS = (\n' + ''.join('    %r\n' % (l + '\n') for l in H) + ')\n')
s = s.replace(a, a + hooks)
b = "    s = s.replace(a, a + '\\tlocal.lastD = \"\"\\n\\tlocal.lastC = \"\"\\n\\tlocal.hasCam = 0\\n')\n"
assert s.count(b) == 1
s = s.replace(b, "    s = s.replace(a, a + '\\tlocal.lastD = \"\"\\n\\tlocal.lastC = \"\"\\n\\tlocal.hasCam = 0\\n\\tlocal.lastB = \"\"\\n\\tlocal.lastQ = \"\"\\n\\tlocal.lastA = \"\"\\n')\n")
c = "    s = s[:w] + DROP + s[w:]\n"
assert s.count(c) == 1
s = s.replace(c, "    s = s[:w] + DROP + HOOKS + s[w:]\n"
              "    if keepunlocks:                      # armory runs: the test `give` must not overwrite the player's unlock record\n"
              "        u = '\\t\\t\\t\\tlocal.p.flags[\"coop_chal_unlocks\"] = local.t'\n"
              "        assert s.count(u) == 1\n"
              "        s = s.replace(u, '\\t\\t\\t\\t//' + u.strip())\n")
assert s.count("def weather(src):") == 1
s = s.replace("def weather(src):", "def weather(src, keepunlocks=False):")
d = "                data = weather(data.decode('latin-1')).encode('latin-1')"
assert s.count(d) == 1
s = s.replace(d, "                data = weather(data.decode('latin-1'), '--armory' in sys.argv).encode('latin-1')")
i = s.index("        # --wire: the INSTALLED mod files"); j = s.index("        # --var s46=0.46")
arm = '''        # --armory: the own armory entry (wiring/stage_armory_dbs.py -> armory_ov/: the mod-tree files edited + what the
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
'''
s = s[:i] + arm + s[j:]
s = s.replace("    python tools/mkov_dbs.py <out.pk3>\n", "    python tools/mkov_dbs.py <out.pk3> [--armory] [--notps]\n")
open(p, 'w', encoding='utf-8', newline='').write(s)
print('edited', p)
