"""Thompson (retail mesh ThompsonSMG.skd): take the PAINTED knob ring off the front end of the cocking slot, on STAGED
copies of every texture the twelve tiks on that mesh read (user, 2026-10-13: the real knob - smggun's added round one -
rests at the BACK of the slot on a cocked gun, so a ring painted at the front shows a second knob).

How: the slot is painted on the receiver's right wall, a planar strip of the UV sheet (u = 0.7875 - 0.04369 (x + 8.47),
v = 0.6939 + 0.0439 (z + 4.43); gun frame, u). Its REAR end (x -2.2) is a plain rounded end. That end, mirrored, is
laid over the ring: the patch x 1.7 .. 4.62 takes the pixels of x' = 1.65 - x (the slot's rear end comes to lie at
x 3.85 = the ring's front edge), blended into the sheet's own slot over 1.1 u at its rear, 0.1 u elsewhere. Nothing is invented: every pixel is the same sheet's own.
The same UV place in every finish (the skins repaint the sheet, not the layout) - each is checked by eye on the sheet
this prints (--preview).

Files (staged under ../assets at their game paths, same format as read; a .dds is written DXT1 / DXT5 with mipmaps by
the weapon-HD encoder): the HD sheet textures/models/weapons/ThompsonSMG/ThompsonSMG.dds (what the engine shows today;
the plain, Blued, Chrome and Gold finishes multiply it), its retail .tga if the VFS has one, and the finishes' own
sheets (coop_skins/thompsonsmg/*.jpg, coop_v3/*/ThompsonSMG.{tga,jpg}).
SHIPPING NOTE: a staged .dds has to sit in a pak that sorts above the HD pak it replaces.

    cd smg/assets;  python ../tools/stage_slot.py [--preview out.jpg]      (IRONSIGHT_EXTRA_PAKS unset)
"""
import sys, os, io, json
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import smggun as SG
sys.path.insert(0, r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools')
import texload

G = SG.G; vfs = SG.vfs
U0, UX = 0.7875, -0.04369          # u at x -8.47, per u of x
V0, VZ = 0.6939, 0.0439            # v at z -4.43, per u of z
X0, X1 = 1.7, 4.62                 # the patch (the wall ends at x 4.68); its rear 1.1 u is a slow blend into the slot
Z0, Z1 = -4.43, -3.3               # ring: z -4.35 .. -3.45; the wall's top edge is at -4.43 (hard edge there)
FADE_REAR, FADE_FRONT, FADE_LOW = 1.1, 0.14, 0.1            # u
MIR = 1.65                         # x' = MIR - x


def uv(x, z):
    return U0 + UX * (x + 8.47), V0 + VZ * (z + 4.43)


def patch(im):
    """im: PIL image (any mode) -> (new image, crop box of the patched place for the preview)"""
    a = np.asarray(im).astype(np.float32)
    H, W = a.shape[:2]
    ua, va = uv(X1, Z0); ub, vb = uv(X0, Z1)                    # u falls as x grows
    px0, px1 = int(round(ua * W)), int(round(ub * W))
    py0, py1 = int(round(va * H)), int(round(vb * H))
    # mirror about the u of x = MIR / 2
    um = uv(MIR / 2.0, 0)[0] * W
    xs = np.arange(px0, px1)
    src = np.clip(np.round(2 * um - xs - 1).astype(int), 0, W - 1)
    new = a.copy()
    blk = a[py0:py1][:, src]
    n, m = py1 - py0, px1 - px0
    ppu = abs(UX) * W                                           # pixels per u along the gun
    ppz = VZ * H
    # columns run from the FRONT (x X1) to the rear (x X0); rows from the top (z Z0) down
    wx = np.minimum(1.0, np.minimum((np.arange(m) + 1) / max(2.0, FADE_FRONT * ppu), (m - np.arange(m)) / max(2.0, FADE_REAR * ppu)))
    wy = np.minimum(1.0, np.minimum((np.arange(n) + 1) / 2.0, (n - np.arange(n)) / max(2.0, FADE_LOW * ppz)))
    w = (wy[:, None] * wx[None, :])
    w = w * w * (3 - 2 * w)
    if a.ndim == 3:
        w = w[:, :, None]
    new[py0:py1, px0:px1] = a[py0:py1, px0:px1] * (1 - w) + blk * w
    out = Image.fromarray(np.clip(np.round(new), 0, 255).astype(np.uint8), im.mode)
    cu0, cv0 = uv(4.7, -4.75); cu1, cv1 = uv(-3.4, -3.1)
    return out, (int(cu0 * W), int(cv0 * H), int(cu1 * W), int(cv1 * H))


def main():
    assert not os.environ.get('IRONSIGHT_EXTRA_PAKS'), 'unset IRONSIGHT_EXTRA_PAKS: the sheets are read from the released VFS'
    tiks = json.load(open(os.path.join(HERE, 'smggun_thompson.json')))['tiks']
    idx = {p.lower(): p for p in vfs.index()}
    files = {}
    for t in tiks:
        sh = G.surf_shader(G.parse_tik(t), 'ThompsonSMG1')
        maps = texload.shader_maps(sh)
        assert maps and maps[-1][2], (t, sh)
        mp = maps[-1][2][0]
        base = os.path.splitext(mp)[0]
        for ext in texload.EXTS:
            p = idx.get((base + ext).lower())
            if p:
                files.setdefault(p, []).append(os.path.basename(t))
    prev = []
    for p in sorted(files):
        if p.lower().endswith('.tga') and (os.path.splitext(p)[0] + '.dds').lower() in [q.lower() for q in files] and '--all' not in sys.argv:
            print('%-62s NOT staged (6.5 MB; the engine reads the .dds of the same sheet first) - --all writes it' % p)
            continue
        raw = vfs.read(p)
        im = Image.open(io.BytesIO(raw)); im.load()
        new, box = patch(im)
        dst = os.path.join('.', p.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        ext = os.path.splitext(p)[1].lower()
        if ext == '.dds':
            sys.path.insert(0, r'C:\mohaa-coop-dev\docs\tools\weapon_hd')
            import build_sheets as BS
            arr = np.asarray(new.convert('RGBA') if (im.mode == 'RGBA' and np.asarray(im.getchannel('A')).min() < 255) else new.convert('RGB'))
            open(dst, 'wb').write(bytes(BS.encode_mipped(arr)))
        elif ext == '.tga':
            new.save(dst, format='TGA', compression='tga_rle')
        elif ext in ('.jpg', '.jpeg'):
            new.convert('RGB').save(dst, format='JPEG', quality=93, subsampling=0)
        else:
            new.save(dst)
        back = Image.open(dst); back.load()
        d = np.abs(np.asarray(back.convert('RGB')).astype(int) - np.asarray(new.convert('RGB')).astype(int))
        print('%-62s %s %-4s %8d -> %8d bytes | file reads back within %d (mean %.2f) | %s' % (
            p, im.size, im.mode, len(raw), os.path.getsize(dst), d.max(), d.mean(), ' '.join(files[p])))
        for src in (im, back):
            c = src.convert('RGB').crop(box)
            prev.append(c.resize((560, max(1, c.size[1] * 560 // c.size[0])), Image.LANCZOS))
    if '--preview' in sys.argv:
        out = sys.argv[sys.argv.index('--preview') + 1]
        h = max(c.size[1] for c in prev)
        S = Image.new('RGB', (1130, (h + 6) * (len(prev) // 2)), (40, 40, 40))
        for i, c in enumerate(prev):
            S.paste(c, ((i % 2) * 570, (i // 2) * (h + 6)))
        S.save(out, quality=90)
        print(out, '(left: released, right: staged; u runs right-to-left along the gun)')


if __name__ == '__main__':
    main()
