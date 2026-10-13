"""What a gun's own model can do: mesh, bones, which bones move in its fire / reload clips (and how far, in the weapon
frame), the reload row's server frames (magazine surface hidden / shown), its sound, its name key for the per-weapon
hands rows (coopr_<key>_reload...).     python gunsurvey.py <tik> [<tik> ...]
"""
import sys, os, re
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
import gen_fire as GF
os.chdir(_c)
PR = V.PR; G = PR.gungeo; SK = PR.skdlib; vfs = PR.vfs


def key_of(name):
    out, gap = '', False
    for c in name.lower():
        if c.isalnum() and c.isascii():
            out += ('_' if gap and out else '') + c
            gap = False
        else:
            gap = True
    return out


def block(txt, name):
    m = re.search(r'(?m)^[ \t]*%s[ \t]+(\S+)[^\r\n]*\r?\n[ \t]*\{' % re.escape(name), txt)
    if not m:
        m2 = re.search(r'(?m)^[ \t]*%s[ \t]+(\S+)' % re.escape(name), txt)
        return (m2.group(1), '') if m2 else (None, '')
    d, i = 0, m.end() - 1
    for j in range(i, len(txt)):
        d += (txt[j] == '{') - (txt[j] == '}')
        if d == 0:
            return m.group(1), txt[i:j + 1]
    return m.group(1), ''


for tik in sys.argv[1:]:
    if '/' not in tik:
        tik = 'models/weapons/' + tik
    txt = vfs.read(tik).decode('latin-1')
    t = G.parse_tik(tik)
    skd = G._res(t, t['skel'][0])
    sk = SK.read_skd(vfs.read(skd))
    nm = re.search(r'(?m)^[ \t]*name[ \t]+"([^"]+)"', txt)
    grp = re.search(r'(?m)^[ \t]*weapongroup[ \t]+(\S+)', txt)
    print('== %s  "%s"  key %s  group %s' % (tik, nm.group(1) if nm else '?', key_of(nm.group(1)) if nm else '?', grp.group(1) if grp else '?'))
    print('   mesh %s  scale %s  bones: %s' % (skd, t['scale'], ' '.join(b.name for b in sk.bones)))
    print('   surfaces: %s' % ' '.join('%s(%d)' % (s.name, len(s.vert_bytes) // 1) for s in sk.surfaces)[:300])
    for an in ('idle', 'fire', 'reload', 'fire_empty', 'idle_empty', 'reload_empty'):
        clip, blk = block(txt, an)
        if not clip:
            continue
        try:
            c = GF.read_skc_any(G._res(t, clip))
        except Exception as e:
            print('   %-8s %s  (unreadable: %s)' % (an, clip, e)); continue
        V_ = np.array(c.values, float)                       # frames x channels x 4
        mv = []
        for ci, ch in enumerate(c.names if hasattr(c, 'names') else [x.name for x in c.channels]):
            rng = V_[:, ci, :].max(0) - V_[:, ci, :].min(0)
            if rng.max() > (1e-3 if ch.endswith('rot') else 0.02):
                mv.append('%s %.2f' % (ch, rng.max() * (t['scale'] if ch.endswith('pos') else 1.0)))
        cmds = ' | '.join(l.strip() for l in blk.splitlines() if re.search(r'surface|sound|\bshow|\bhide', l))
        print('   %-8s %-26s %3d fr x %.4f s  moving: %s' % (an, clip, c.numFrames, c.frameTime, '; '.join(mv) or '-'))
        if cmds:
            print('            %s' % cmds[:260])
