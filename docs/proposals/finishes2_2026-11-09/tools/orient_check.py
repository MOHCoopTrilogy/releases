"""finishes2 BUILD GATE - every gun's decal placement reads upright and unmirrored.
For each gun of the roster and each side (-y = the viewer / Armory side, +y = the far side) that gets a decal:
  1. place() picks the island from the gun's own mesh (no UVs shared with the other side) and the transform;
  2. the test glyph (red "F" left of a green up-arrow, assets/decals/_testF.png) is stamped through exactly that transform onto a
     flat grey copy of the gun's sheet;
  3. the gun is rendered looking straight at the decal from that side, and the glyph is read back from the pixels:
     arrow head (widest green row) in the upper half = upright; F's stem column on its left and F left of the arrow = unmirrored;
     F's top bar wider than its foot = not flipped;
  4. the far side is rendered too: any red there is a mirrored ghost (shared UVs) = FAIL.
Exit 1 if any gun fails.        python orient_check.py <roster.tsv> [out.tsv] [sheet.jpg]
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import finishlib as fl  # noqa: E402
import gungeo, raster, uvview  # noqa: E402

GLYPH = np.asarray(Image.open(os.path.join(HERE, '..', 'assets', 'decals', '_testF.png')).convert('RGBA'), float) / 255.0
_gr = GLYPH
_yel = (_gr[..., 0] > 0.75) & (_gr[..., 1] > 0.75) & (_gr[..., 2] < 0.43)
_yy, _yx = np.nonzero(_yel)
RED_FRAC = ((_gr[..., 0] > 0.67) & (_gr[..., 1] < 0.43)).sum() / float((np.ptp(_yx) + 1) * (np.ptp(_yy) + 1))
SKIP = {'64', '65', '66', '67', '68', '69'}           # grenades: no decal
KIND = {'rifle': 'butt', 'sniper': 'butt', 'heavy': 'butt', 'smg': 'grip', 'pistol': 'grip', 'shotgun': 'butt'}


def view(g, pls, side, W=360, H=270):
    """render looking at the side's decal (or the gun centre) from `side`, sheets flat grey with every placement stamped"""
    cache = {}
    real = uvview.shader_image

    def shader_image(sh):
        if sh not in cache:
            m, p, pk, im, blk = real(sh)
            if im is None:
                cache[sh] = (m, p, pk, im, blk)
            else:
                base = np.asarray(im.convert('RGBA'), float) / 255.0
                img = np.dstack([np.full(base.shape[:2] + (3,), 0.45), base[..., 3:4]])
                for pl in pls:
                    if pl['shader'] == sh:
                        img = fl.stamp(img, pl, GLYPH)
                cache[sh] = (m, p, pk, Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), 'RGBA'), blk)
        return cache[sh]
    uvview.shader_image = shader_image
    try:
        mine = [p for p in pls if p['side'] == side]
        lo, hi = fl.gun_box(g)
        if mine:
            cx, cz = mine[0]['centre']
            ext = mine[0]['size'] * 1.6
        else:
            cx, cz = (lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2
            ext = max(hi[0] - lo[0], hi[2] - lo[2])
        c = np.array([cx, (lo[1] + hi[1]) / 2, cz])
        dist = max(hi[0] - lo[0], 40) * 4
        eye = c + np.array([0, side * dist, 0])
        rgb, ids, dep = raster.render(g, eye, c, np.array([0, 0, 1.0]), fov=2 * math.degrees(math.atan(ext * 0.5 / dist)),
                                      W=W, H=H, tex=True, bg=(30, 30, 34), znear=1.0)
    finally:
        uvview.shader_image = real
    return rgb


def read_glyph(rgb):
    r, gr, b = [rgb[..., i].astype(int) for i in range(3)]
    red = (r > 170) & (gr < 110) & (b < 110)
    grn = (gr > 170) & (r < 120) & (b < 120)
    if red.sum() < 25 or grn.sum() < 25:
        return 'glyph not visible (red %d green %d px)' % (red.sum(), grn.sum())
    ys, xs = np.nonzero(grn)
    rows = np.bincount(ys - ys.min())
    if not np.argmax(rows) < len(rows) / 2:
        return 'FLIPPED (arrow head at bottom)'
    fy, fx = np.nonzero(red)
    if not fx.mean() < xs.mean():
        return 'MIRRORED (F right of the arrow)'
    cols = np.bincount(fx - fx.min())
    q = max(1, len(cols) // 4)
    if not cols[:q].mean() > cols[-q:].mean():
        return 'MIRRORED (F stem on the right)'
    yy, yx = np.nonzero((r > 190) & (gr > 190) & (b < 110))      # the yellow frame: whole and square, glyph not cut or skewed
    if len(yy) < 40:
        return 'CUT (frame missing)'
    fw, fh = np.ptp(yx) + 1, np.ptp(yy) + 1
    if not 0.75 < fw / fh < 1.33:
        return 'SKEWED (frame %dx%d)' % (fw, fh)
    sides = [(yy - yy.min() < 0.12 * fh, yx, fw), (yy.max() - yy < 0.12 * fh, yx, fw),
             (yx - yx.min() < 0.12 * fw, yy, fh), (yx.max() - yx < 0.12 * fw, yy, fh)]
    for k, (sel, coord, full) in enumerate(sides):
        if sel.sum() < 3 or len(np.unique(coord[sel])) < 0.75 * full:
            return 'CUT (frame side %s incomplete)' % 'TBLR'[k]
    ra = red.sum() / float(fw * fh)
    if not 0.6 * RED_FRAC < ra < 1.6 * RED_FRAC:
        return 'CUT/STRETCHED (F covers %.3f of the frame, expect %.3f)' % (ra, RED_FRAC)
    rws = np.bincount(fy - fy.min())
    q = max(1, len(rws) // 5)
    if not rws[:q].mean() > rws[-q:].mean():
        return 'FLIPPED (F foot wider than its top)'
    return 'ok'


def place_verified(g, kind, tries=24, side=None, avoid=(), allow_shared=True):
    """the first placement (best spot first) whose rendered test glyph reads upright, unmirrored, whole and square from the
    visible side -> (placement or None, verdict of the best try, render). The finishes build uses exactly this."""
    side = fl.VISIBLE if side is None else side
    first = None
    # an island whose UVs the other side reuses shows the decal there too, MIRRORED: unshared islands first, at full then at
    # smaller size; shared ones only as the last resort (flagged: then only a mirror-safe decal belongs there)
    order = [(k, f, sh) for sh in ((False, True) if allow_shared else (False,)) for k, f in [(k, 0.8) for k in range(tries)] + [(k, 0.5) for k in range(6)]]
    for k, fill, shared_ok in order:
        pl = fl.place(g, kind, side=side, rank=k, fill=fill, allow_shared=shared_ok)
        if pl is None:
            continue
        if any(a['shader'] == pl['shader'] and (fl.decal_texels(a) & fl.decal_texels(pl)).any() for a in avoid):
            continue                                  # would paint over (or be painted by) the other side's decal
        if pl['size'] < 1.5 * fl.U_PER_CM:         # under 1.5 cm nobody reads it
            continue
        im = uvview.shader_image(pl['shader'])[3]
        if im is not None and pl['size'] / fl.world_per_uv(g, pl['shader']) * max(im.size) < 28:
            continue                                  # under ~28 texels across the decal is a smudge
        rgb = view(g, [pl], side)
        v = read_glyph(rgb)
        if v == 'ok' and not fl.orientation_ok(pl):
            v = 'analytic gate disagrees'
        if v == 'ok':
            pl['rank'] = k
            return pl, v, rgb
        if first is None:
            first = (v, rgb)
    return None, (first[0] if first else 'no side island'), (first[1] if first else None)


def check(tik, cls):
    """both sides: the Armory / viewer side (the gun's right) with the finish's decal on the butt or grip, and the first-person
    side (the gun's left) with one on the receiver / slide that must not share a texel with the first. Each placed decal is
    re-read with BOTH stamped (the other one must not ghost over it); a side without its own decal reports any mirror copy."""
    g = fl.load_gun(tik)
    pa, va, _ = place_verified(g, KIND.get(cls, 'grip'), side=fl.ARMORY)
    # the first-person decal only where it has its OWN texels: on a shared island it would also print mirrored on the Armory side
    pf, vf, _ = place_verified(g, 'receiver', side=fl.FIRSTPERSON, avoid=[pa] if pa else [], allow_shared=False)
    pls = [p for p in (pa, pf) if p]
    res, shots = [], []
    for side, pl, v0 in ((fl.ARMORY, pa, va), (fl.FIRSTPERSON, pf, vf)):
        rgb = view(g, pls, side)
        shots.append(rgb)
        if pl is not None:
            v = read_glyph(rgb)
            res.append(('ok (spot #%d, %.1f cm%s)' % (pl['rank'] + 1, pl['size'] / fl.U_PER_CM,
                                                      ', SHARED UVs: mirror copy on the far side' if pl['shared'] >= 0.15 else ''))
                       if v == 'ok' else 'BAD WITH BOTH: ' + v)
        else:
            red = ((rgb[..., 0] > 170) & (rgb[..., 1] < 110) & (rgb[..., 2] < 110)).sum()
            res.append('NO CLEAN SPOT (%s)%s' % (v0, '; mirror copy of the other side shows' if red >= 25 else ''))
    return tuple(res), shots, pls


def main():
    roster, out = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
    sheet_p = sys.argv[3] if len(sys.argv) > 3 else None
    rows = [l.rstrip('\n').split('\t') for l in open(roster, encoding='utf-8') if l.strip()]
    lines, bad, tiles = [], 0, []
    for gid, tik, name, cls in rows:
        if gid in SKIP:
            continue
        try:
            (a, b), shots, pls = check(tik, cls)
        except Exception as e:
            a = b = 'ERROR %r' % e
            shots = []
        fail = any(not (x.startswith('ok') or x.startswith('NO CLEAN SPOT')) for x in (a, b)) or not a.startswith('ok')
        bad += fail
        lines.append('%s\t%s\t%s\t%s\t%s' % (gid, name, a, b, 'FAIL' if fail else 'pass'))
        print(lines[-1], flush=True)
        if shots:
            t = Image.new('RGB', (2 * 180 + 4, 135 + 14), (16, 16, 18))
            for i, s in enumerate(shots):
                t.paste(Image.fromarray(s).resize((180, 135)), (i * 184, 14))
            ImageDraw.Draw(t).text((3, 1), '%s %s %s' % (gid, name[:24], 'FAIL' if fail else ''),
                                   fill=(255, 90, 90) if fail else (220, 220, 220))
            tiles.append(t)
    if out:
        open(out, 'w', encoding='utf-8').write('id\tgun\tarmory side (gun right)\tfirst-person side (gun left)\tresult\n' + '\n'.join(lines) + '\n')
    if sheet_p and tiles:
        cols = 5
        tw, th = tiles[0].size
        sh = Image.new('RGB', (cols * (tw + 4), math.ceil(len(tiles) / cols) * (th + 4)), (8, 8, 8))
        for i, t in enumerate(tiles):
            sh.paste(t, ((i % cols) * (tw + 4), (i // cols) * (th + 4)))
        sh.save(sheet_p, quality=85)
    print('%d checked, %d FAIL' % (len(lines), bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
