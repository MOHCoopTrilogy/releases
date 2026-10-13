r"""Stage what the shotgun reload needs besides the baked clips (sgbake.py) and the rows (stage_rows.py):

  1. tiks: the 14 staged shotgun tiks (stage_sgsight.py wrote them) get the gun row
         reload_end_loaded  coop_shotgun_still32.skc
     - the end of a reload that started with rounds in the gun: the slide does not move, no pump sound. cgame
     ads-heavy-next (apply_sgpump.py) shows it instead of `reload_end`; the server still runs `reload_end`.
  2. models/player/base/anims_shotgun.txt = the retail file (pak3) + the third-person loop row's server commands:
     a shell on the support hand's tag from the pouch to the gate, and the round COUNTED WHEN IT IS IN (retail counted
     it 0.17 s into the loop, before the hand has left the pouch - a reload broken off then kept a shell that was
     never loaded); the end row clears a shell left in the hand by a break-off.

    cd heavy/assets; python ../tools/stage_sgreload.py     (after stage_sgsight.py; the mod tree is never written)
"""
import sys, os, re, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
H, R, V, CTL = hv.lib()
SHELL = 'models/ammo/shotgunshell.tik'
ATTACH, COUNT, GONE = 7, 14, 15
ROW = '\treload_end_loaded coop_shotgun_still32.skc\t// HZM coop [heavy lane] end of a reload that began with rounds in the gun: no pump, no pump sound (stage_sgreload.py; cgame shows it in place of reload_end)'


def tiks():
    n = 0
    for p in sorted(glob.glob(hv.staged('models/weapons/shotgun*.tik'))):
        t = open(p, 'rb').read().decode('latin-1')
        nl = '\r\n' if '\r\n' in t else '\n'
        t = re.sub(r'(?m)^[ \t]*reload_end_loaded[^\r\n]*\r?\n', '', t)
        m = re.search(r'(?m)^[ \t]*reload_end[ \t]+\S+[^\r\n]*', t)
        assert m, p
        i = t.index('{', m.end()); d = 0; j = i
        while True:
            if t[j] == '{':
                d += 1
            elif t[j] == '}':
                d -= 1
                if d == 0:
                    break
            j += 1
        e = t.index(nl, j) + len(nl)
        t = t[:e] + ROW + nl + t[e:]
        assert 'coop_bead' in t and 'coop_groove' in t, p
        open(p, 'wb').write(t.encode('latin-1'))
        n += 1
    print(n, 'staged tiks: reload_end_loaded')


def anims():
    rel = 'models/player/base/anims_shotgun.txt'
    t = R.vfs.read(rel).decode('latin-1')
    assert 'HZM coop [heavy lane]' not in t, 'run WITHOUT the overlay in IRONSIGHT_EXTRA_PAKS: this reads the retail file'
    nl = '\r\n' if '\r\n' in t else '\n'
    a = re.search(r'(?m)^([ \t]*)5 weaponcommand mainhand clip_add 1[^\r\n]*', t)
    assert a and t.count('weaponcommand mainhand clip_add 1') == 1
    ind = a.group(1)
    new = nl.join([
        ind + '%d attachmodel %s tag_weapon_left\t\t// HZM coop [heavy lane] a shell in the support hand, from the pouch (stage_sgreload.py)' % (ATTACH, SHELL),
        ind + '%d weaponcommand mainhand clip_add 1\t\t// counted when it is IN the gate (retail: frame 5, the hand still at the pouch)' % COUNT,
        ind + '%d removeattachedmodel tag_weapon_left 0 %s' % (GONE, SHELL)])
    t = t[:a.start()] + new + t[a.end():]
    b = re.search(r'(?m)^([ \t]*)first weaponcommand mainhand anim reload_end[^\r\n]*', t)
    assert b
    t = t[:b.end()] + nl + b.group(1) + 'first removeattachedmodel tag_weapon_left 0 %s\t// HZM coop [heavy lane] a reload broken off with the shell still in the hand' % SHELL + t[b.end():]
    out = hv.staged(rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'wb').write(t.encode('latin-1'))
    print('staged', rel, '(retail + shell prop, count at frame %d)' % COUNT)


if __name__ == '__main__':
    tiks()
    anims()
