"""The aim-only bolt cycle (`rechamber_ads`, boltcap.py) for EVERY tik that shares a bolt rifle's mesh (user 2026-10-13:
"all of these new guns will need their camo/variants too"). boltcap.py stages the row in the four BASE tiks only; the
hands' aimed rows are per prefix and reach every finish, so a finished rifle played the aimed hands clip over the
gun's FULL stroke - the bolt 0.0-0.9 u from the eye again. Here every released tik with the same `path` + `skelmodel`
gets the same row (boltcap.tik_with_row, the base tik's clip name) and is written under ../assets.

    python boltcap_variants.py            (after boltcap.py; then nosmoke.py for the measure tiks as before)
Prints, per rifle: the tiks covered, and the tiks of the same family on OTHER meshes (not covered: their bolt would
need its own capped clip - add them to boltcap.GUNS).
"""
import sys, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import staged
import boltcap as BC
vfs = staged.vfs
BASE = {'kar98': 'models/weapons/kar98.tik', 'springfield': 'models/weapons/springfield_unscoped.tik',
        'mosin': 'models/weapons/mosin_nagant_rifle.tik', 'enfield': 'models/weapons/enfield.tik'}
FAMILY = {'kar98': r'kar98|g98', 'springfield': r'springfield|m1903', 'mosin': r'mosin', 'enfield': r'enfield|p14|smle'}


def mesh_of(t):
    t = re.sub(r'//[^\n]*', '', t)
    m = re.search(r'skelmodel\s+(\S+)', t); pa = re.search(r'\bpath\s+(\S+)', t)
    return ((pa.group(1).lower().rstrip('/') + '/') if pa else '') + (m.group(1).lower() if m else '')


def main():
    staged.off()
    info = {}
    for p in vfs.index():
        lp = p.lower()
        if lp.startswith('models/weapons/') and lp.endswith('.tik') and lp.count('/') == 2:
            raw = vfs.read(p)
            if raw:
                info[lp] = raw.decode('latin-1')
    staged.on()
    total = 0
    for k, b in BASE.items():
        st = open(staged.path(b), 'rb').read().decode('latin-1')
        clip = re.search(r'(?m)^[ \t]*rechamber_ads[ \t]+(\S+)', st)
        assert clip, b + ': run boltcap.py first'
        clip = clip.group(1)
        mesh = mesh_of(info[b])
        done, other = [], []
        for p, t in sorted(info.items()):
            if mesh_of(t) == mesh:
                if p != b:
                    assert re.search(r'(?m)^[ \t]*rechamber[ \t]+\S+', re.sub(r'//[^\n]*', '', t)), p + ': no rechamber row'
                    new = BC.tik_with_row(t, clip)
                    d = 0
                    for ln in new.splitlines():
                        c = ln.split('//')[0]; d += c.count('{') - c.count('}')
                    assert d == 0 and new.count('rechamber_ads\t' + clip) == 1, p
                    dst = staged.path(p); os.makedirs(os.path.dirname(dst), exist_ok=True)
                    open(dst, 'wb').write(new.encode('latin-1'))
                done.append(os.path.basename(p)[:-4])
            elif re.search(FAMILY[k], os.path.basename(p)) and 'static' not in p:
                other.append('%s [%s]' % (os.path.basename(p)[:-4], mesh_of(t).split('/')[-1]))
        total += len(done)
        print('%s (%s, clip %s): %d tiks carry rechamber_ads' % (k, mesh.split('/')[-1], clip, len(done)))
        print('   covered: ' + ' '.join(done))
        print('   NOT covered (other mesh): ' + (' '.join(other) or '-'))
    print('total', total)


if __name__ == '__main__':
    main()
