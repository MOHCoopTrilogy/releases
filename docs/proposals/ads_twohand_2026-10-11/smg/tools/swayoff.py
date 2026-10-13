"""Offline: how much of the centre box does the SETTLED AIM alone uncover beyond its own (grown) mask when the game's
aim sway + breath translate the whole first-person rig, as a function of an eye-relief offset.
    cd smg/assets; python ../tools/swayoff.py <gun> [bias,bias,...] [--sheet out.jpg]
sway: cg_adsSway 0.1 -> L/R +-0.10 u, U/D +-0.07 u; breath (cg_weaponBreath 1, aiming, calm) U/D +-0.105 u, L/R +-0.042 u
"""
import sys, os, itertools
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import smgbake as SB
R, V, RB = SB.R, SB.V, SB.RB
from PIL import Image, ImageDraw

def run(name, biases, sheet=None, W=640, drop=0.0):
    g = SB.GUNS[name]
    aimp = os.path.join('.', 'models', 'human', 'animation', g['aim'].replace('/', os.sep))
    aim = R.load(aimp if os.path.isfile(aimp) else R.ANIM + g['aim'])
    sight = V.SIGHTS[g['sight']]
    corr = V.rig_target(V.evaluate_ctl(R.pose_dict(aim, aim.numFrames - 1), RB.CTL), sight)
    surfs, E, Wb = V.scene2(R.pose_dict(aim, aim.numFrames - 1), g['sight'], sight['tik'], 'idle', 0.0, RB.CTL, corr, None)
    Hh = W * 9 // 16
    fov = V.weapon_fov()
    x0, x1, y0, y1 = int(W * 0.4), int(W * 0.6), int(Hh * 0.4), int(Hh * 0.6)
    r = max(1, int(round(6 * W / 1280.0)))
    LY, UZ = 0.142, 0.175
    states = [(0, 0)] + [(LY * a, UZ * b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1), (.7, .7), (.7, -.7), (-.7, .7), (-.7, -.7))]
    tiles = []
    for b in biases:
        ms = []
        for (dy, dz) in states:
            sh = [dict(s, P=s['P'] + np.array([b, dy, dz - drop])) for s in surfs]
            rgb, ids, _ = V.shade_render(sh, E, fov, W, Hh, bg=(206, 212, 218), tex=bool(sheet) and (dy, dz) == (0, 0))
            ms.append((ids >= 0)[y0:y1, x0:x1])
            if sheet and (dy, dz) == (0, 0):
                im = Image.fromarray(rgb); d = ImageDraw.Draw(im)
                d.rectangle((x0, y0, x1, y1), outline=(255, 230, 0)); d.text((4, 3), '%s relief %+.1f u' % (name, b), fill=(0, 0, 0))
                tiles.append(im)
        def grow(m):
            o = m.copy()
            for ddy in range(-r, r + 1):
                for ddx in range(-r, r + 1):
                    o |= np.roll(np.roll(m, ddy, axis=0), ddx, axis=1)
            return o
        gs = [grow(m) for m in ms]
        ex = [float((ms[j] & ~gs[i]).mean()) for i in range(len(ms)) for j in range(len(ms)) if i != j]
        from_centre = [float((ms[j] & ~gs[0]).mean()) for j in range(1, len(ms))]
        print('%-16s relief %+5.1f u  aim covers %4.1f %% of the box | sway alone, beyond the aim mask: from the rest pose max %.1f %%, between two sway states max %.1f %% (median %.1f %%)' % (
            name, b, 100 * ms[0].mean(), 100 * max(from_centre), 100 * max(ex), 100 * float(np.median(ex))))
    if sheet:
        S = Image.new('RGB', (W * min(4, len(tiles)), Hh * ((len(tiles) + 3) // 4)), 'white')
        for k, t in enumerate(tiles):
            S.paste(t, ((k % 4) * W, (k // 4) * Hh))
        S.save(sheet, quality=86); print(sheet)

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    sheet = sys.argv[sys.argv.index('--sheet') + 1] if '--sheet' in sys.argv else None
    drop = float(sys.argv[sys.argv.index('--drop') + 1]) if '--drop' in sys.argv else 0.0
    if sheet: a.remove(sheet)
    if '--drop' in sys.argv: a.remove(str(sys.argv[sys.argv.index('--drop') + 1]))
    run(a[0], [float(x) for x in a[1].split(',')] if len(a) > 1 else [0.0], sheet, drop=drop)
