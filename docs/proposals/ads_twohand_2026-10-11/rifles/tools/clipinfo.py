"""Timeline of a weapon animation: the first-person row's clip (frames, frame time, where the right / left hand is in the
gun frame), the gun's own clip (which bones move, when), and the tik block's frame commands.

    python clipinfo.py <tik> <gun anim> <view clip under models/human/animation/> [offhand lo,hi]
"""
import sys, os, re
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T)
_c = os.getcwd(); os.chdir(T)
import vmcam as V
os.chdir(_c)
R = V.R


def tik_anim(tik, anim):
    t = R.vfs.read(tik).decode('latin-1')
    path = re.search(r'(?mi)^\s*path\s+(\S+)', t).group(1)
    m = re.search(r'(?m)^\s*%s\s+(\S+\.skc)[^\n]*\n' % re.escape(anim), t)
    i = t.index('{', m.end()); d = 0; j = i
    while True:
        d += (t[j] == '{') - (t[j] == '}'); j += 1
        if d == 0:
            break
    return path.rstrip('/') + '/' + m.group(1), t[i:j]


def moving(a, eps_r=0.004, eps_p=0.02):
    out = []
    for c, nm in enumerate(a.names):
        v = a.V[:, c, :]
        d = np.abs(v - v[0]).max(axis=1)
        eps = eps_p if nm.endswith(' pos') else eps_r
        fr = [f for f in range(a.numFrames) if d[f] > eps]
        if fr:
            ch = [f for f in range(1, a.numFrames) if np.abs(v[f] - v[f - 1]).max() > eps / 3]
            runs = []
            for f in ch:
                if runs and f - runs[-1][1] <= 1:
                    runs[-1][1] = f
                else:
                    runs.append([f, f])
            out.append((nm, ' '.join('%d-%d' % (x, y) for x, y in runs)))
    return out


def main():
    tik, anim, view = sys.argv[1:4]
    gclip, blk = tik_anim(tik, anim)
    g = R.load(gclip)
    print('GUN  %s: %d frames x %.4f s = %.2f s' % (gclip, g.numFrames, g.frameTime, g.numFrames * g.frameTime))
    for nm, runs in moving(g):
        print('   moves: %-28s %s' % (nm, runs))
    for ln in blk.splitlines():
        s = ln.split('//')[0].strip()
        if re.match(r'^(entry|exit|first|last|\d+)\s', s):
            print('   tik:', s[:110])
    v = R.load(R.ANIM + view)
    print('VIEW %s: %d frames x %.4f s = %.2f s  (gun frame = view frame x %.3f)' % (view, v.numFrames, v.frameTime, v.numFrames * v.frameTime, v.frameTime / g.frameTime))
    lo, hi = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 else (-1, -1)
    print('   f   R hand in gun (fwd, right, down)    L hand in gun     gun tag in model (x,y,z)')
    for f in range(0, v.numFrames, max(1, v.numFrames // 34)):
        W = R.evaluate(R.pose_dict(v, f))
        G = W['tag_weapon_left' if lo <= f <= hi else 'tag_weapon_right']
        rr = (W['Bip01 R Hand'] @ R.inv(G))[3, 0:3] * R.S
        ll = (W['Bip01 L Hand'] @ R.inv(G))[3, 0:3] * R.S
        print('   %3d  %6.1f %6.1f %6.1f     %6.1f %6.1f %6.1f     %6.1f %6.1f %6.1f' % ((f,) + tuple(rr) + tuple(ll) + tuple(G[3, 0:3] * R.S)))


if __name__ == '__main__':
    main()
