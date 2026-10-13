"""Use-to-loot prompt icon of the double barrel: assets/textures/hud/loot/w_dbshotgun.tga (512 x 256, RLE, 32 bit).

    python tools/dbs_icon.py            writes the icon + build/_icon_cmp.png (ours next to the trench gun's, on grey)
    python tools/dbs_icon.py look       only dumps the trench gun's icon numbers (style reference)

Style = the existing icons (docs/proposals/use_pickup_2026-10-05): a side silhouette, muzzle to the right, centred in
the 2:1 canvas, the colour and the alpha edge taken from the trench gun's icon as measured here (not assumed). The
silhouette is our own mesh (build/own/high_parts.json) seen from its left side, at the icon's visible width.
Prints the row for code/cgame/cg_coopfeed_loot.h (visible width / height as fractions of the canvas).
"""
import os, sys, io, importlib.util
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
import dbslib as L
import dbs_skin as SK

sp = importlib.util.spec_from_file_location('weapon_hd_vfs', os.path.join(L.DOCS, 'tools', 'weapon_hd', 'vfs.py'))
HV = importlib.util.module_from_spec(sp); sp.loader.exec_module(HV)
OUT = os.path.join(L.ASSETS, 'textures', 'hud', 'loot')


def ref():
    im = Image.open(io.BytesIO(HV.read('textures/hud/loot/w_shotgun.tga')))
    a = np.asarray(im.convert('RGBA'), np.float32)
    al = a[..., 3]
    ys, xs = np.nonzero(al > 128)
    core = al > 250
    info = dict(size=im.size, mode=im.mode, box=(int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())),
                rgb_core=a[core][:, :3].mean(0).round(1).tolist(), rgb_core_std=a[core][:, :3].std(0).round(1).tolist(),
                alpha_levels=int(len(np.unique(al))), rgb_outside=a[al < 5][:, :3].mean(0).round(1).tolist() if (al < 5).any() else None)
    return im, info


def main():
    rim, info = ref()
    print('trench gun icon:', info)
    if len(sys.argv) > 1 and sys.argv[1] == 'look':
        return
    T, pid, wood = SK.load()
    P = T[:, :, :3] * SK.CM
    lo = P.reshape(-1, 3).min(0); hi = P.reshape(-1, 3).max(0)
    Wc, Hc = 512, 256
    SS = 4                                                   # supersampling
    vis_w = 0.80                                             # a 60 cm gun next to the 100 cm trench gun (its icon: 0.902)
    sc = vis_w * Wc * SS / (hi[0] - lo[0])
    w = int((hi[0] - lo[0]) * sc) + 8; h = int((hi[2] - lo[2]) * sc) + 8
    hx = (P[:, :, 0] - lo[0]) * sc + 4                       # muzzle (+x) to the right
    vy = (hi[2] - P[:, :, 2]) * sc + 4
    tid, bw = SK.raster(np.stack([hx, vy], -1), len(T), w, h, eps=0.02)
    m = (tid >= 0).astype(np.float32)
    big = np.zeros((Hc * SS, Wc * SS), np.float32)
    oy = (Hc * SS - h) // 2; ox = (Wc * SS - w) // 2
    big[oy:oy + h, ox:ox + w] = m
    big = ndi.binary_closing(big > 0.5, iterations=5).astype(np.float32)       # seams between the mesh's parts
    al = np.asarray(Image.fromarray((big * 255).astype(np.uint8)).resize((Wc, Hc), Image.LANCZOS), np.float32) / 255.0
    # the existing icons carry a dark outline (measured: rgb about 16 14 12 around the cream silhouette)
    edge = ndi.binary_dilation(big > 0.5, iterations=3 * SS).astype(np.float32)
    ol = np.asarray(Image.fromarray((edge * 255).astype(np.uint8)).resize((Wc, Hc), Image.LANCZOS), np.float32) / 255.0
    rgb = np.array(info['rgb_core'], np.float32)
    dark = np.array(info['rgb_outside'] or [16.0, 14.0, 12.0], np.float32)
    out = np.zeros((Hc, Wc, 4), np.uint8)
    out[..., :3] = (rgb[None, None, :] * al[..., None] + dark[None, None, :] * (1 - al[..., None])).astype(np.uint8)
    out[..., 3] = np.clip(np.maximum(al, ol) * 255, 0, 255).astype(np.uint8)
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray(out, 'RGBA').save(os.path.join(OUT, 'w_dbshotgun.tga'), compression='tga_rle')
    ys, xs = np.nonzero(al > 0.5)
    vw, vh = (xs.max() - xs.min() + 1) / float(Wc), (ys.max() - ys.min() + 1) / float(Hc)
    print('wrote w_dbshotgun.tga  row:    {"Shotgun (Double Barrel)", "w_dbshotgun", "Double Barrel", %.3ff, %.3ff},' % (vw, vh))
    cmp_ = Image.new('RGBA', (Wc * 2 + 12, Hc), (70, 74, 80, 255))
    cmp_.alpha_composite(Image.fromarray(out, 'RGBA'), (0, 0))
    cmp_.alpha_composite(rim.convert('RGBA'), (Wc + 12, 0))
    cmp_.convert('RGB').save(os.path.join(L.BUILD, '_icon_cmp.png'))


if __name__ == '__main__':
    main()
