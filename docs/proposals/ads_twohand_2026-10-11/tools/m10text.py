"""S&W M10 text side (run AFTER webtext.py - it edits the staged anims_shared.txt that script writes):

  coop_mod/player_Torso.st        (released copy) + RELOAD_M10 / _SINGLE / _CHECK_CONTINUE / _END, cloned from the Webley's
                                  states, and the M10 routed to them ahead of the generic pistol reload
  models/player/base/anims_shared.txt   + coop_reload_m10_start / _loop / _end (server events: gun anims, cases, the round)
  rows_m10.txt                    the fps_anims rows (hip + aimed + the empty-cylinder start with the case dump)

    python m10text.py <stage root> [--slow]
"""
import sys, os, re, glob
sys.path.insert(0, glob.glob(r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\batches\heavy\tools')[0])
import vfs
root = sys.argv[1]
SLOW = '--slow' in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
ROUND = 'models/ammo/nagant_pistol_shell.tik'


def put(rel, text, crlf):
    p = os.path.join(root, rel.replace('/', os.sep))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write((text.replace('\n', '\r\n') if crlf else text).encode('latin-1'))
    print('wrote', rel, len(text))


# ---------------------------------------------------------------- player_Torso.st
raw = vfs.read('coop_mod/player_Torso.st').decode('latin-1')
crlf = '\r\n' in raw
s = raw.replace('\r\n', '\n')
a = s.index('\nstate RELOAD_WEBLEY\n')
b = s.index('\nstate RELOAD_NAGANTREV\n')
blk = s[a:b]
assert blk.count('\nstate ') == 4, blk.count('\nstate ')
for old in ('coop_reload_webley_start', 'WEBLEY_reload_loop', 'WEBLEY_reload_end'):
    assert old in blk, old
m = blk.replace('RELOAD_WEBLEY', 'RELOAD_M10').replace('coop_reload_webley_start', 'coop_reload_m10_start')
m = m.replace('WEBLEY_reload_loop', 'coop_reload_m10_loop').replace('WEBLEY_reload_end', 'coop_reload_m10_end')
m = '\n// HZM coop [revolver reload 2026-10-12] S&W M10: open / one round per loop / close - the Webley\'s states, cloned\n' + m.lstrip('\n')
s = s[:b] + '\n' + m.rstrip('\n') + '\n' + s[b:]
route = re.search(r'(?m)^([ \t]*)RELOAD_WEBLEY([ \t]+): IS_WEAPON_ACTIVE "mainhand" "Webley Revolver"[^\n]*\n', s)
assert route, 'route'
s = s[:route.start()] + '%sRELOAD_M10%s: IS_WEAPON_ACTIVE "mainhand" "S&W M10 .38"\n' % (route.group(1), route.group(2) + '\t') + s[route.start():]
# brace depth
d = 0
for i, l in enumerate(s.splitlines()):
    c = l.split('//')[0]
    d += c.count('{') - c.count('}')
    assert d >= 0, i
assert d == 0, d
put('coop_mod/player_Torso.st', s, crlf)

# ---------------------------------------------------------------- anims_shared.txt (staged copy)
p = os.path.join(root, 'models', 'player', 'base', 'anims_shared.txt')
raw = open(p, 'rb').read().decode('latin-1')
crlf = '\r\n' in raw
u = raw.replace('\r\n', '\n')
anchor = '\tcoop_reload_m10\tviewmodel/pistol/reload_colt.skc\tcrossblend 0.3\n'
assert u.count(anchor) == 1
if SLOW:
    loop_clip = 'viewmodel/webley/coop_webley_tp_single_slow.skc'
    loop_ev = ('\t\t\tfirst weaponcommand mainhand anim reload_single\n'
               '\t\t\t10 attachmodel %s tag_weapon_left\n'
               '\t\t\t20 weaponcommand mainhand clip_add 1\n'
               '\t\t\t20 removeattachedmodel tag_weapon_left 0 %s\n' % (ROUND, ROUND))
else:
    loop_clip = 'viewmodel/webley/webley_reload_single.skc'
    loop_ev = ('\t\t\tfirst weaponcommand mainhand anim reload_single\n'
               '\t\t\t6 attachmodel %s tag_weapon_left\n'
               '\t\t\t12 weaponcommand mainhand clip_add 1\n'
               '\t\t\t12 removeattachedmodel tag_weapon_left 0 %s\n' % (ROUND, ROUND))
new = ('\t// HZM coop [revolver reload 2026-10-12] S&W M10 as a real swing-out: start (1.0 s: cylinder out, fired cases dumped\n'
       '\t// with the ejector rod), one round from the pouch per loop, close. Torso states RELOAD_M10* (player_Torso.st).\n'
       '\tcoop_reload_m10_start\tviewmodel/coop_m10/coop_m10_tp_start.skc\tcrossblend 0.1\n\t{\n\t\tserver\n\t\t{\n'
       '\t\t\tfirst reloadweapon\n'
       '\t\t\t21\tcoop_ejectcases models/ammo/pistolshell.tik tag_weapon_right 6\n\t\t}\n\t}\n'
       '\tcoop_reload_m10_loop\t%s\tcrossblend 0\n\t{\n\t\tserver\n\t\t{\n%s\t\t}\n\t}\n'
       '\tcoop_reload_m10_end\tviewmodel/webley/webley_reload_end.skc\tcrossblend 0.0\n\t{\n\t\tserver\n\t\t{\n'
       '\t\t\tfirst weaponcommand mainhand anim reload_end\n\t\t}\n\t}\n' % (loop_clip, loop_ev))
if SLOW:
    # the gun's own loop clip must last as long as the torso loop: the tik's reload_single points at the 24-frame clip
    tp = os.path.join(root, 'models', 'weapons', 'm10_revolver.tik')
    t = open(tp, 'rb').read().decode('latin-1')
    assert 'reload_single\tcoop_m10_single.skc' in t
    open(tp, 'wb').write(t.replace('reload_single\tcoop_m10_single.skc', 'reload_single\tcoop_m10_single_slow.skc', 1).encode('latin-1'))
u = u.replace(anchor, new + anchor, 1)
put('models/player/base/anims_shared.txt', u, crlf)

# ---------------------------------------------------------------- fps rows
dump = ('\t{\n\t\tclient\n\t\t{\n\t\t\t21 tagspawn tag_weapon_right\t// the ejector rod pushes the six fired cases out of the open cylinder (first person)\n'
        '\t\t\t(\n\t\t\t\tcount 6\n\t\t\t\tmodel models/ammo/pistolshell.tik\n\t\t\t\tspawnrange 1024\n\t\t\t\tscale .75\n'
        '\t\t\t\toffsetalongaxis 3.2 -2.2 -1.5\n\t\t\t\trandvelaxis range -60 -25 crandom 18 crandom 18\n'
        '\t\t\t\tavelocity crandom 360 crandom 360 crandom 180\n\t\t\t\taccel 0 0 -800\n\t\t\t\tphysicsrate 20\n\t\t\t\tlife 2.0\n'
        '\t\t\t\tfadedelay 1.7\n\t\t\t\tcollision\n\t\t\t\tbouncefactor 0.2\n\t\t\t\tbouncesoundonce snd_pistol_shell\n\t\t\t)\n\t\t}\n\t}\n')
sl = '_slow' if SLOW else ''
rows = ('\t//===================== HZM coop S&W M10: swing-out reload (hand-keyed), hip + aimed + empty-cylinder start =====================\n'
        '\tm10_reload_single\t\tviewmodel/coop_m10/coop_m10_reload_single%s.skc\t\tcrossblend 0.1\n' % sl +
        '\tm10_reload_end\t\tviewmodel/coop_m10/coop_m10_reload_end.skc\t\tcrossblend 0.2\n'
        '\tm10_reload_empty\t\tviewmodel/coop_m10/coop_m10_reload_empty.skc\t\tcrossblend 0.1\n' + dump +
        '\tm10_reload_ads\t\tviewmodel/coop_m10/m10_reload_ads.skc\t\tcrossblend 0.1\n'
        '\tm10_reload_single_ads\t\tviewmodel/coop_m10/m10_reload_single%s_ads.skc\t\tcrossblend 0.1\n' % sl +
        '\tm10_reload_end_ads\t\tviewmodel/coop_m10/m10_reload_end_ads.skc\t\tcrossblend 0.1\n'
        '\tm10_reload_empty_ads\t\tviewmodel/coop_m10/m10_reload_empty_ads.skc\t\tcrossblend 0.1\n' + dump)
open(os.path.join(HERE, 'rows_m10%s.txt' % sl), 'w', newline='\n').write(rows)
print('wrote rows_m10%s.txt' % sl)
