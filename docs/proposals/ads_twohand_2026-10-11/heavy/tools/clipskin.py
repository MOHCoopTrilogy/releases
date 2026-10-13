"""BAR magazine prop tone (2b): the magazine in the hand (models/ammo/bar_clip.tik, shader `barclip`, texture
textures/models/weapons/bar/barclip) is light grey steel (mean 84 / 255) against the gun (S93_bar lifted: mean 45,
warm). In the reload the gun's own magazine surface is swapped for the prop, so the magazine changes colour in the
hand. Tone the prop's texture DOWN onto the lifted gun's: luminance scaled so the mean lands on TARGET, colour pulled
TINT of the way to the gun's own warm cast. Nothing repainted; both files (.dds = what the engine shows, .tga) staged.
The finish shaders (gold / chrome / blued clip) multiply this texture, bloody / camo have their own JPGs (untouched).

    cd heavy/assets; python ../tools/clipskin.py [--target 46] [--tint 0.6] [--preview out.jpg]
"""
import sys, os, io, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
from PIL import Image

DIR = 'textures/models/weapons/bar/'
GUN = 'textures/models/weapons/bar/S93_bar.dds'       # the STAGED lifted gun skin: where the cast comes from


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', type=float, default=46.0); ap.add_argument('--tint', type=float, default=0.6)
    ap.add_argument('--preview')
    a = ap.parse_args()
    H, R, V, CTL = hv.lib()
    g = np.asarray(Image.open(hv.staged(GUN)).convert('RGB'), float).reshape(-1, 3).mean(0)
    cast = g / g.mean()
    idx = {p.lower(): p for p in R.vfs.index()}
    prev = []
    for ext in ('dds', 'tga'):
        src = idx.get((DIR + 'barclip.' + ext).lower())
        assert src, ext
        print(src, 'from', R.vfs.pakname(src) if hasattr(R.vfs, 'pakname') else '?')
        im = Image.open(io.BytesIO(R.vfs.read(src)))
        alpha = im.getchannel('A') if im.mode == 'RGBA' else None
        rgb = np.asarray(im.convert('RGB'), float)
        k = a.target / rgb.mean()
        lum = rgb.mean(axis=2, keepdims=True)
        out = (rgb * k) * (1.0 + a.tint * (cast - 1.0))
        out = np.clip(np.round(out), 0, 255).astype(np.uint8)
        dst = hv.staged(src)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if ext == 'dds':
            assert alpha is None or np.asarray(alpha).min() == 255, 'alpha in ' + src
            sys.path.insert(0, r'C:\mohaa-coop-dev\docs\tools\weapon_hd')
            import build_sheets as BS
            open(dst, 'wb').write(bytes(BS.encode_mipped(out)))
        else:
            o = Image.fromarray(out)
            if alpha is not None:
                o.putalpha(alpha)
            o.save(dst, format='TGA')
        chk = np.asarray(Image.open(dst).convert('RGB'), float).reshape(-1, 3).mean(0)
        print('  %s %s mean %.1f -> %s (gun %s)' % (im.size, im.mode, rgb.mean(), chk.round(1), g.round(1)))
        if ext == 'dds':
            prev = [Image.fromarray(rgb.astype(np.uint8)), Image.fromarray(out)]
    if a.preview and prev:
        S = Image.new('RGB', (prev[0].size[0] * 2, prev[0].size[1]))
        S.paste(prev[0], (0, 0)); S.paste(prev[1], (prev[0].size[0], 0))
        S.save(a.preview, quality=88)


if __name__ == '__main__':
    main()
