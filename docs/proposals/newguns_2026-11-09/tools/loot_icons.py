"""Use-to-loot icons for the new guns, in the use_pickup_2026-10-05 set's own finish (its build_icons.finish / canvas): the side
silhouette of each gun's game mesh (the extracted triangles in its gun frame, filled at 4x), saved as textures/hud/loot/w_<stem>.tga,
plus the cg_coopfeed_loot.h rows (name, texture, short name, visible width / height).
    python loot_icons.py <outdir>
"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
UP = r"C:\mohaa-coop-dev\docs\proposals\use_pickup_2026-10-05\tools"
sys.path.insert(0, UP)
_c = os.getcwd(); os.chdir(UP)
import build_icons as BI  # noqa: E402
os.chdir(_c)
import brenlib, mp28lib, pzflib  # noqa: E402

GUNS = [  # (item name, texture stem, short name, gun-frame converter, npz, parts to drop)
    ("Bren", "bren", "Bren", brenlib.to_gun, r"H:\hzm_work\newguns\build\bren\tris.npz", ()),
    ("MP28", "mp28", "MP 28", mp28lib.to_gun, r"H:\hzm_work\newguns\build\mp28\tris.npz", ()),
    ("Panzerfaust", "panzerfaust", "Panzerfaust", pzflib.to_gun, r"H:\hzm_work\newguns\build\pzf\tris.npz", ()),
]


def silhouette(to_gun, npz, px=12.0):
    d = np.load(npz)
    A = d['corners']
    if 'bren' in npz:                                      # the bipod folded, as the game mesh has it
        import build_bren
        A = build_bren.fold_legs(A, d['part'])
    G = to_gun(A[:, :, :3])                    # (T, 3, 3) gun frame: x muzzle, z DOWN
    x, z = G[..., 0], G[..., 2]
    x0, z0 = x.min(), z.min()
    W, H = int((x.max() - x0) * px) + 4, int((z.max() - z0) * px) + 4
    im = Image.new('L', (W, H), 0)
    dr = ImageDraw.Draw(im)
    for tx, tz in zip(x, z):
        dr.polygon([(float((a - x0) * px) + 2, float((b - z0) * px) + 2) for a, b in zip(tx, tz)], fill=255)
    return im, float(x.max() - x0)


def main():
    out = sys.argv[1]
    sil = os.path.join(out, 'sil'); os.makedirs(sil, exist_ok=True)
    rows = []
    for name, stem, short, conv, npz, _drop in GUNS:
        im, units = silhouette(conv, npz)
        im.save(os.path.join(sil, 'w_%s.png' % stem))
        BI.HERE = out                                        # weapon_icon reads <HERE>/sil/<stem>.png
        icon = BI.weapon_icon('w_' + stem if False else 'w_%s' % stem, units)
        BI.save(icon, out, 'w_' + stem)
        vw, vh = BI.vis(icon)
        rows.append('    {"%s", "w_%s", "%s", %.3ff, %.3ff},' % (name, stem, short, vw, vh))
        icon.save(os.path.join(out, 'w_%s_preview.png' % stem))
    open(os.path.join(out, 'loot_rows.h'), 'w', newline='\n').write('\n'.join(rows) + '\n')
    print('\n'.join(rows))


if __name__ == '__main__':
    main()
