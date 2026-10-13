"""finlift.py - the texture lifts carried to the FINISHES that use their own sheets (pistol lane, 2026-10-13 pm).

Awaiting the user's approval like the base lifts (weltex.py, gamtex.py): staged, in no cut.

The gold / chrome / blued finishes of the Welrod and the Beretta draw the BASE sheets (lifted already). The bloody and
camo finishes draw their own sheets under textures/coop_skins/<gun>/:
    bloody   the base art with blood on it, as dark as the base was (Welrod: mean 7-8 of 255; Beretta: 28)
             -> the base sheet's own curve, on the steel only: a texel keeps its colour where it is blood (red well
                above green / blue), the blend follows how red it is
    camo     paint over the whole sheet, mean 47-143 of 255 - nothing is near black, nothing to lift: left as they are
             (the figures are printed)
Curves = the base lifts': Welrod  out = (in / p99.5 of the BASE sheet) ^ 0.80 * TOP   (weltex.TOP per sheet)
                          Beretta out = 255 * (in / 255) ^ 0.62                        (gamtex)

    python finlift.py <stage root> [--sheet out.jpg]
"""
import sys, os, io
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc
import weltex
vfs = gunskc.R.vfs
MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
SK = os.path.join(MOD, 'textures', 'coop_skins')


def blood_mask(rgb):
    """0..1: how much a texel is blood (red dominant)"""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    dom = (r - np.maximum(g, b)) / np.maximum(r, 1.0)          # 0 grey .. 1 pure red
    return np.clip((dom - 0.18) / 0.25, 0.0, 1.0) * np.clip((r - 14.0) / 20.0, 0.0, 1.0)


def run(root, sheet=None):
    tiles = []
    out_dir = os.path.join(root, 'textures', 'coop_skins')
    # Welrod bloody: the base sheet's curve
    for n, top in weltex.TOP.items():
        base = np.asarray(Image.open(io.BytesIO(vfs_released('textures/models/weapons/welrod/%s.tga' % n))).convert('RGB')).astype(np.float64)
        hi = max(1.0, float(np.percentile(base.max(axis=2), 99.5)))
        src = os.path.join(SK, 'welrod', '%s_bloody.jpg' % n)
        a = np.asarray(Image.open(src).convert('RGB')).astype(np.float64)
        # the finish sheets are JPEGs: at 0-10 of 255 their chroma noise would be amplified into a brown cast, so the
        # curve is applied to the grey level and the texel's own hue comes back in only above the noise (grey 6 -> 30)
        gray = a.mean(axis=2, keepdims=True)
        lg = np.clip((np.clip(gray / hi, 0.0, 1.6) ** weltex.GAMMA) * top, 0, 255)
        sat = np.clip((gray - 6.0) / 24.0, 0.0, 1.0)
        lifted = np.clip(lg * (1.0 + sat * (a / np.maximum(gray, 1.0) - 1.0)), 0, 255)
        m = blood_mask(a)[..., None]
        o = lifted * (1 - m) + np.maximum(a, lifted * 0.55) * m          # blood: its own colour, never darker than before
        save(out_dir, 'welrod/%s_bloody.jpg' % n, o)
        print('welrod %-7s bloody: base p99.5 %3.0f -> %d | mean %.1f -> %.1f | blood share %.1f %%' % (n, hi, top, a.mean(), o.mean(), 100 * m.mean()))
        tiles.append((a, o))
    # Beretta bloody: gamma 0.62
    src = os.path.join(SK, 'it_w_beretta', 'it_w_beretta_bloody.jpg')
    a = np.asarray(Image.open(src).convert('RGB')).astype(np.float64)
    lifted = 255.0 * (a / 255.0) ** 0.62
    m = blood_mask(a)[..., None]
    o = lifted * (1 - m) + np.maximum(a, lifted * 0.7) * m
    save(out_dir, 'it_w_beretta/it_w_beretta_bloody.jpg', o)
    print('beretta bloody: mean %.1f -> %.1f | blood share %.1f %%' % (a.mean(), o.mean(), 100 * m.mean()))
    tiles.append((a, o))
    for g in ('welrod', 'it_w_beretta'):
        for f in sorted(os.listdir(os.path.join(SK, g))):
            if '_camo_' in f and f.lower().endswith('.jpg'):
                c = np.asarray(Image.open(os.path.join(SK, g, f)).convert('RGB')).astype(np.float64)
                print('camo, NOT lifted: %-36s mean %5.1f  median %5.1f  share darker than 20: %4.1f %%' % (g + '/' + f, c.mean(), np.median(c), 100 * (c.max(axis=2) < 20).mean()))
    if sheet:
        W = 300
        S_ = Image.new('RGB', (W * len(tiles), W * 2 + 4), 'black')
        for i, (a, o) in enumerate(tiles):
            S_.paste(Image.fromarray(a.astype(np.uint8)).resize((W, W)), (i * W, 0))
            S_.paste(Image.fromarray(o.astype(np.uint8)).resize((W, W)), (i * W, W + 4))
        S_.save(sheet, quality=88); print(sheet)


def vfs_released(p):
    """the RELEASED sheet (the stage holds the lifted one under the same name)"""
    env = os.environ.pop('IRONSIGHT_EXTRA_PAKS', None)
    try:
        return vfs.read(p)
    finally:
        if env is not None:
            os.environ['IRONSIGHT_EXTRA_PAKS'] = env


def save(out_dir, rel, o):
    dst = os.path.join(out_dir, rel.replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    Image.fromarray(np.clip(o, 0, 255).astype(np.uint8)).save(dst, quality=93)


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[sys.argv.index('--sheet') + 1] if '--sheet' in sys.argv else None)
