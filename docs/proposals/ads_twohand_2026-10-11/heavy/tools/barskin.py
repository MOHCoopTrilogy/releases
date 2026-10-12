"""BAR skin tone lift (user 2026-10-12: "WE can make it look slightly brither").

The S93 BAR skin is very dark (mean 19 / 255: on the light wall the gun reads 9 / 255 on screen where the DP-28 and
the Breda read 44-47). A tone LIFT of the existing texture only - a monotone curve on luminance, every pixel's RGB
re-scaled about its own grey (hue, grain and wear kept; nothing repainted, no new source):

    luminance 0 -> 0, 5 -> 11, 19 -> 44, 31 -> 66, 80 -> 124, 160 -> 200, 255 -> 255      (CURVE, --curve to try others)
    colour: the chroma of a pixel grows only with (luminance gain) ** 0.25 - hue kept, the crushed yellow of the darks not amplified

What reads the texture: shader S93_bar / S93_bar-bipod (american_weapons.shader, zzzzz_xw_weapons.pk3) on
models/weapons/bar_lmg/bar.skd = bar.tik, one tik for first person, third person, pickup and the Armory; the finishes
bar_blued / chrome / gold multiply the same texture (coop_skins.shader), bar_bloody / camo_* have their own JPGs
(textures/coop_skins/bar/) and are NOT touched. No other weapon reads it (M1919 / MG42 / the stock-mesh BAR variants
have their own). TWO files exist per sheet and BOTH are staged lifted, so no view / renderer is left dark:
    textures/models/weapons/bar/S93_bar.dds   the weapon-HD pak zzzzzzzzzz_coop_hd_m3l1a.pk3 (2048, DXT1) - what the
                                              engine shows today (R_LoadImage probes .dds first)
    textures/models/weapons/bar/s93_bar.tga   the pack's original (zzzzz_xw_weapons.pk3) - shown without the HD pak
(the same for S93_bar-bipod). SHIPPING NOTE: the lifted .dds has to replace the member of the weapon-HD pak or sit in
a pak that sorts above it, or that pak hides the change.

    cd heavy/assets; python ../tools/barskin.py [--curve "0:0,5:12,..."] [--preview out.jpg]
"""
import sys, os, io, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
from PIL import Image

CURVE = "0:0,5:11,19:44,31:66,80:124,160:200,255:255"
CHROMA = 0.25
SHEETS = ('S93_bar', 'S93_bar-bipod')
DIR = 'textures/models/weapons/bar/'


def lut(curve):
    H, R, V, CTL = hv.lib()
    import key_bolt as K
    pts = [tuple(float(x) for x in kv.split(':')) for kv in curve.split(',')]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return np.array([K.pchip(xs, ys, v) for v in range(256)])


def lift(rgb, L):
    a = rgb.astype(np.float64)
    lum = a.mean(axis=2)
    li = np.clip(lum, 0, 255)
    new = np.interp(li, np.arange(256), L)
    k = np.where(lum > 0.5, new / np.maximum(lum, 0.5), 1.0)
    # the hue is kept, the COLOUR is not multiplied with the luminance: the skin's darks are a crushed yellow-brown
    # (15, 12, 1 on screen) and a plain x2.6 turned the steel mustard / olive with blotches (runs hs2 / hn2: looked like
    # a camo finish). Chroma grows only with k ** CHROMA (0.25: x1.27 where the luminance grows x2.6).
    out = new[..., None] + (a - lum[..., None]) * (k ** CHROMA)[..., None]
    out = np.maximum(out, 0.0)
    # a channel that would clip: pull the pixel toward grey at the same luminance instead (hue kept, no clipping)
    mx = out.max(axis=2)
    over = mx > 255.0
    if over.any():
        g = new[over][:, None]
        o = out[over]
        s = (255.0 - g) / np.maximum(o.max(axis=1, keepdims=True) - g, 1e-6)
        out[over] = g + (o - g) * np.clip(s, 0, 1)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--curve', default=CURVE); ap.add_argument('--preview')
    a = ap.parse_args()
    H, R, V, CTL = hv.lib()
    L = lut(a.curve)
    idx = {p.lower(): p for p in R.vfs.index()}
    prev = []
    for sh in SHEETS:
        for ext in ('dds', 'tga'):
            src = idx.get((DIR + sh + '.' + ext).lower())
            assert src, (sh, ext)
            im = Image.open(io.BytesIO(R.vfs.read(src)))
            alpha = im.getchannel('A') if im.mode == 'RGBA' else None
            rgb = np.asarray(im.convert('RGB'))
            new = lift(rgb, L)
            dst = hv.staged(src)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if ext == 'dds':
                assert alpha is None or np.asarray(alpha).min() == 255, 'alpha in ' + src
                sys.path.insert(0, r'C:\mohaa-coop-dev\docs\tools\weapon_hd')
                import build_sheets as BS
                open(dst, 'wb').write(bytes(BS.encode_mipped(new)))
                chk = np.asarray(Image.open(dst).convert('RGB')).astype(float).mean()
            else:
                o = Image.fromarray(new)
                if alpha is not None:
                    o.putalpha(alpha)
                o.save(dst, format='TGA')
                chk = np.asarray(Image.open(dst).convert('RGB')).astype(float).mean()
            print('%-48s %s %s  mean %.1f -> %.1f (file reads back %.1f)  p90 %.0f -> %.0f' % (
                src, im.size, im.mode, rgb.mean(), new.mean(), chk, np.percentile(rgb.mean(2), 90), np.percentile(new.mean(2), 90)))
            if ext == 'dds':
                prev += [Image.fromarray(rgb).resize((512, 512), Image.LANCZOS), Image.fromarray(new).resize((512, 512), Image.LANCZOS)]
    if a.preview:
        S = Image.new('RGB', (1024, 512 * (len(prev) // 2)))
        for i, im in enumerate(prev):
            S.paste(im, ((i % 2) * 512, (i // 2) * 512))
        S.save(a.preview, quality=88)
        print(a.preview)


if __name__ == '__main__':
    main()
