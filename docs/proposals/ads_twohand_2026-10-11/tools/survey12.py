"""gun-side survey of the twelve shared-clip pistols: tik animations, clip channels and which of them move"""
import sys, os, re
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc
R = gunskc.R
vfs = R.vfs
MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'


def rd(p):
    f = os.path.join(MOD, p.replace('/', os.sep))
    if os.path.isfile(f):
        return open(f, 'rb').read()
    return vfs.read(p)


for stem in sys.argv[1:]:
    t = rd('models/weapons/%s.tik' % stem).decode('latin-1').replace('\r\n', '\n')
    path = re.search(r'(?m)^\s*path\s+(\S+)', t).group(1)
    skd = re.search(r'(?m)^\s*skelmodel\s+(\S+)', t).group(1)
    name = re.search(r'(?m)^\s*name\s+"([^"]+)"', t).group(1)
    surf = re.findall(r'(?m)^\s*surface\s+(\S+)\s+shader\s+(\S+)', t)
    print('=== %s | "%s" | %s/%s | surfaces %s' % (stem, name, path, skd, ' '.join('%s=%s' % s for s in surf)))
    an = t[t.find('\nanimations'):]
    for m in re.finditer(r'(?m)^\s*(\w+)\s+(\S+\.skc)', an):
        try:
            a = R.load(path + '/' + m.group(2))
        except Exception as e:
            print('  %-12s %s LOAD FAILED %s' % (m.group(1), m.group(2), e)); continue
        mv = []
        for c, nm in enumerate(a.names):
            v = a.V[:, c, :3] if nm.endswith(' pos') else a.V[:, c, :]
            rng = float(np.abs(v - v[0]).max()) if a.numFrames > 1 else 0.0
            if rng > 1e-3:
                fr = np.where(np.abs(np.diff(v, axis=0)).max(axis=1) > 1e-3)[0]
                mv.append('%s(%.2f f%d-%d)' % (nm, rng, fr[0], fr[-1] + 1))
        print('  %-12s %-28s %3d fr | chans: %s | MOVING: %s' % (m.group(1), m.group(2), a.numFrames,
              ' '.join(n for n in a.names if not n.startswith(('tag_', 'origin'))), ' '.join(mv) or '-'))
