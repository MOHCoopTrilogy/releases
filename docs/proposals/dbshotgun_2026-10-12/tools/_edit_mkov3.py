"""one-off edit of tools/mkov_dbs.py + tools/dbs_world.scr (fourth pass): base on the deployed weather.scr, --world
(driver + timing probe), --tree (the mod TREE's torso state file + the fixes dir's delta), --nopatch (no torso rows)."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))

p = os.path.join(HERE, 'dbs_world.scr')
s = open(p, encoding='latin-1').read()
a = '\tlocal.p ammo shotgun 0\n'
if a in s:
    s = s.replace(a, '')
a = ' + " weapon=" + local.g.weapon )'
if a in s:
    s = s.replace(a, ' )')
open(p, 'w', encoding='latin-1', newline='\n').write(s)

p = os.path.join(HERE, 'mkov_dbs.py')
s = open(p, encoding='utf-8').read()
assert 'WORLDHOOK' not in s
i = s.index('BASE = r"')
j = s.index('\n', i)
s = s[:i] + ('# the plumbing on the DEPLOYED weather.scr (tools/mkbase_dbs.py); the ADS lanes\' ovbase_1021.pk3 is the 1.10.21 one\n'
             'BASE = os.environ.get("DBS_OVBASE") or os.path.join(L.BUILD, "ovbase_cur.pk3")') + s[j:]

a = "def weather(src, keepunlocks=False):\n"
assert s.count(a) == 1
s = s.replace(a, '''WORLDHOOK = (
    '\\t\\tlocal.ww = getcvar( "coop_dbsW" )\\n'
    '\\t\\tif( local.ww != "" && local.ww != local.lastW && $player != NULL && $player.size >= 1 ){\\n'
    '\\t\\t\\tlocal.lastW = local.ww\\n'
    '\\t\\t\\tthread dbsw_main local.ww\\n'
    '\\t\\t}\\n')


def weather(src, keepunlocks=False, world=False):
''')

a = "    s = s[:w] + DROP + HOOKS + s[w:]\n"
assert s.count(a) == 1
s = s.replace(a, a + '''    if world:                            # --world: the world-behaviour driver + the server timing probe (tools/dbs_world.scr)
        a2 = '\\tlocal.lastM = ""\\n'
        assert s.count(a2) == 1
        s = s.replace(a2, a2 + '\\tlocal.lastW = ""\\n\\tthread dbsw_probe\\n')
        w = s.index('\\t\\twaitframe\\n', s.index('coop_is_test:'))
        s = s[:w] + WORLDHOOK + s[w:]
        s = s.rstrip('\\n') + '\\n' + open(os.path.join(L.PROP, 'tools', 'dbs_world.scr'), encoding='latin-1').read().replace('\\r\\n', '\\n')
''')

a = "data = weather(data.decode('latin-1'), '--armory' in sys.argv).encode('latin-1')"
assert s.count(a) == 1
s = s.replace(a, "data = weather(data.decode('latin-1'), '--armory' in sys.argv, '--world' in sys.argv).encode('latin-1')")

a = ("            st = HV.read('coop_mod/player_Torso.st').decode('latin-1')\n"
     "            z.writestr('coop_mod/player_Torso.st', PT.patch(st).encode('latin-1'))\n")
assert s.count(a) == 1
s = s.replace(a, '''            if '--tree' in sys.argv:
                st = open(os.path.join(os.path.dirname(L.DOCS), 'hzm-mohaa-coop-mod', 'coop_mod', 'player_Torso.st'), 'rb').read().decode('latin-1')
                print('torso state file: the mod TREE, %d bytes' % len(st))
            else:
                st = HV.read('coop_mod/player_Torso.st').decode('latin-1')
            z.writestr('coop_mod/player_Torso.st', (st if '--nopatch' in sys.argv else PT.patch(st)).encode('latin-1'))
            if '--tree' in sys.argv:
                fxd = os.path.join(L.DOCS, 'tools', 'assets', 'fixes')
                have = set(z.namelist())
                k4 = 0
                for d4, _, fs4 in os.walk(fxd):
                    for f4 in fs4:
                        p4 = os.path.join(d4, f4)
                        arc = os.path.relpath(p4, fxd).replace(os.sep, '/')
                        if arc in have or arc.split('/')[0] not in TOP:
                            continue
                        data = open(p4, 'rb').read()
                        try:
                            same = HV.read(arc) == data
                        except Exception:
                            same = False
                        if not same:
                            z.writestr(arc, data); k4 += 1
                print('fixes dir: %d files the deployed paks do not have (or have differently)' % k4)
''')
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('mkov_dbs.py edited')
