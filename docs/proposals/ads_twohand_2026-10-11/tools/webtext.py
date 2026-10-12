"""Webley text side of the hand-keyed reload, written into the staging tree (and so into the test overlay):

  models/player/base/anims_pistol.txt   (retail pak3 copy) webley_reload_loop: a cartridge is attached to the support
      hand while it is at the pouch (frame 8), the round is counted and the prop removed when it seats (frame 13)
  models/weapons/webley_revolver.tik    (installed copy) reload_single: the chamber's own cartridge head shows from the
      seat frame; no case is thrown per round any more; reload (open): the cases are thrown as the action opens

    python webtext.py <stage root> [--cases N]
"""
import sys, os, re, glob
sys.path.insert(0, glob.glob(r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\batches\heavy\tools')[0])
import vfs
root = sys.argv[1]
cases = int(sys.argv[sys.argv.index('--cases') + 1]) if '--cases' in sys.argv else 6
ROUND = 'models/ammo/nagant_pistol_shell.tik'


def put(rel, text, crlf):
    p = os.path.join(root, rel.replace('/', os.sep))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write((text.replace('\n', '\r\n') if crlf else text).encode('latin-1'))
    print('wrote', rel, len(text))


# ---- anims_pistol.txt
raw = vfs.read('models/player/base/anims_pistol.txt').decode('latin-1')
crlf = '\r\n' in raw
s = raw.replace('\r\n', '\n')
m = re.search(r'(?m)^\s*webley_reload_loop\s[^\n]*\n\s*\{\n\s*server\n\s*\{\n(.*?)\n\s*\}\n\s*\}', s, re.S)
assert m, 'webley_reload_loop block'
body = m.group(1)
assert 'clip_add 1' in body and 'attachmodel' not in body, body
SLOW = '--slow' in sys.argv
if SLOW:
    new_body = ('\t\t\tfirst weaponcommand mainhand anim reload_single\n'
                '\t\t\t8 weaponcommand mainhand anim reload_single\t\t\t// HZM coop [revolver reload, slow loop] the gun\'s own clip is 16 frames: re-issued so it ends with this 24-frame loop\n'
                '\t\t\t10 attachmodel %s tag_weapon_left\t\t\t// a round in the support hand, from the pouch\n'
                '\t\t\t20 weaponcommand mainhand clip_add 1\t\t\t\t\t// counted when it seats\n'
                '\t\t\t20 removeattachedmodel tag_weapon_left 0 %s' % (ROUND, ROUND))
else:
    new_body = ('\t\t\tfirst weaponcommand mainhand anim reload_single\n'
                '\t\t\t6 attachmodel %s tag_weapon_left\t\t\t// HZM coop [revolver reload] a round in the support hand, from the pouch\n'
                '\t\t\t12 weaponcommand mainhand clip_add 1\t\t\t\t\t// counted when it seats\n'
                '\t\t\t12 removeattachedmodel tag_weapon_left 0 %s' % (ROUND, ROUND))
s = s[:m.start(1)] + new_body + s[m.end(1):]
if SLOW:
    a0 = s.index('webley_reload_loop')
    assert 'viewmodel/webley/webley_reload_single.skc' in s[a0:a0 + 120]
    s = s[:a0] + s[a0:a0 + 120].replace('viewmodel/webley/webley_reload_single.skc', 'viewmodel/webley/coop_webley_tp_single_slow.skc') + s[a0 + 120:]
put('models/player/base/anims_pistol.txt', s, crlf)

# ---- webley_revolver.tik
raw = vfs.read('models/weapons/webley_revolver.tik').decode('latin-1')
crlf = '\r\n' in raw
t = raw.replace('\r\n', '\n')
a = t.index('\treload_single \twebley_revolver_reload_single.skc')
b = t.index('\treload_end \twebley_revolver_reload_end.skc')
blk = t[a:b]
m = re.search(r'\t\t\t3 tagspawn tag_eject\n\t\t\t\(\n(.*?)\n\t\t\t\)\n', blk, re.S)
assert m, 'tagspawn block'
spawn_body = m.group(1)
blk2 = blk[:m.start()] + blk[m.end():]
blk2 = blk2.replace('\t\t\t2\tsurface shellmetal_cull -nodraw\n\t\t\t8\tsurface shellmetal_cull +nodraw\n',
                    '\t\t\t9\tsurface shellmetal_cull +nodraw\n\t\t\t12\tsurface shellmetal_cull -nodraw\t// HZM coop [revolver reload] shows as the round seats\n')
assert blk2 != blk and 'tagspawn' not in blk2
blk2 = blk2.replace('3 sound webley_snd_reload_single', '12 sound webley_snd_reload_single')
t = t[:a] + blk2 + t[b:]
# the open: the cases are thrown by the server's coop_ejectcases (anims_shared.txt, exact count) - no client spawn here
# closing: the chamber marker off again
old = '\treload_end \twebley_revolver_reload_end.skc\n\t{\n'
assert old in t
t = t.replace(old, old + '\t\tserver\n\t\t{\n\t\t\tfirst surface shellmetal_cull +nodraw\n\t\t}\n', 1)
put('models/weapons/webley_revolver.tik', t, crlf)

# ---- anims_shared.txt (the mod's): coop_reload_webley_start
raw = vfs.read('models/player/base/anims_shared.txt').decode('latin-1')
crlf = '\r\n' in raw
u = raw.replace('\r\n', '\n')
old = "\t\t\tfirst reloadweapon\n\t\t\t12\tcoop_ejectcases models/ammo/pistolshell.tik tag_weapon_right 6\n"
assert u.count(old) == 1, u.count(old)
new = ("\t\t\t3 reloadweapon\t\t// HZM coop [revolver reload] the gun's own opening clip is 13 frames: started 3 frames in, it ends as the\n"
       "\t\t\t\t\t\t\t// first round starts (it used to end 3 frames early and the gun snapped shut for those frames)\n"
       "\t\t\t15\tcoop_ejectcases models/ammo/pistolshell.tik tag_weapon_right 6\n")
put('models/player/base/anims_shared.txt', u.replace(old, new, 1), crlf)
