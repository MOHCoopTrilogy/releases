"""finishes2, second pass (2026-11-09, wiring agent): re-bake a coat, add the four LAYERED finishes, repack the pak.

    python fs2_finish2.py rebake splitter [stem ...]   re-bake the named coat(s) on every sheet, from the gun that baked the sheet
                                                       first (same geometry -> the coat stays registered to the shipped mask.png);
                                                       also records each sheet's world-per-UV (wpu) for the layered shaders
    python fs2_finish2.py layers                       tiles + one shader per sheet x layered finish + 4 variant tiks per gun
    python fs2_finish2.py pack                         rows.tsv + scripts/coop_finishes_hd.shader + the pak (deterministic)

THE LAYERED FINISHES (README "four shader-composited finishes"): no per-gun texture at all. Each is the gun's own texture plus
stages over shared 512 px tiles from patterns.py (tcMod scale = this sheet's world-per-UV / the tile's physical size, so a tile
is the same size in the world on every gun):
  battleworn (49)  base x 0.84, then scratches + rub-through chips ADDED and lit (wear_scratch + wear_chips, 18 cm)
  trenchart  (50)  base x a warm brass tint, hand-cut vine scroll MULTIPLIED in (engrave_vines, 10 cm), a soft polished sheen
  parade     (51)  base x base x 2 (deeper, richer contrast), a bright polished sheen (tcGen environment)
  captured   (52)  base x field grime (a soft mottled brown multiply, 30 cm) + chips; the souvenir / waffenamt marks are bench decals
fids 49-52, ranks continue after the paint coats' (state.json 'rank'). Nothing here deploys: the pak stays in the staging dir.
"""
import hashlib, io, json, os, re, sys, time, zipfile
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import finishlib as fl  # noqa: E402
import finish_sheet as fs  # noqa: E402
import fs2_layers as L  # noqa: E402
import fs2_build as B  # noqa: E402
import uvview  # noqa: E402

STAGE = B.STAGE
LAYERED = (('battleworn', 'Battle-worn', 49), ('trenchart', 'Trench Art', 50), ('parade', 'Parade', 51), ('captured', 'Captured', 52))
TILE_DIR = 'textures/coop_finishes_hd/tiles'
TILE_CM = {'fs2_worn': 18.0, 'fs2_vines': 10.0, 'fs2_grime': 30.0}
ENV = TILE_DIR + '/fs2_env.jpg'


def load_state():
    return json.load(open(os.path.join(STAGE, 'state.json')))


def save_state(st):
    json.dump(st, open(os.path.join(STAGE, 'state.json'), 'w'), indent=1)


def gun_sheets(g):
    """{shader: sheet key} exactly as fs2_build picks them"""
    out = {}
    for sh in sorted(set(s['shader'] for s in g['surfs'])):
        m, path, pk, im, blk = uvview.shader_image(sh)
        if im is None or B.SKIP.search(path or '') or min(im.size) < 256:
            continue
        out[sh] = (B.sheet_key(path), im.size)
    return out


def rebake(coats, only):
    st = load_state()
    todo = {k for k in st['sheets']}
    t00 = time.time()
    for stem, gun in st['guns'].items():            # build order: the first gun holding a sheet is the one that baked it
        if not todo:
            break
        g = fl.load_gun(gun['tik'])
        mine = {sh: k for sh, (k, _sz) in gun_sheets(g).items() if k in todo}
        for sh, key in sorted(mine.items()):
            if key not in todo:
                continue                            # a second shader on the same sheet (g43): fs2_build baked it from the first
            todo.discard(key)
            s = st['sheets'][key]
            s['wpu'] = fl.world_per_uv(g, sh)
            s['baker'] = stem
            if only and stem not in only:
                continue
            t0 = time.time()
            _p, masks, out = L.layers(g, sh, tuple(coats) + ('dak',))
            # registration check: the dak coverage recomputed now must be the mask that ships
            shipped = np.asarray(Image.open(os.path.join(STAGE, 'pak', 'textures', 'coop_finishes_hd', key, 'mask.png')), float)
            now = np.asarray(masks['dak'].split()[3], float)
            err = float(np.abs(shipped - now).mean()) if shipped.shape == now.shape else 999.0
            for c in coats:
                b = io.BytesIO(); out[c].save(b, 'JPEG', quality=85, optimize=True)
                B.put('textures/coop_finishes_hd/%s/%s.jpg' % (key, c), b.getvalue())
            print('%-14s %-24s mask err %.3f  %.0fs' % (stem, key, err, time.time() - t0), flush=True)
            assert err < 1.0, 'the coat would not sit on the shipped mask (%s %s err %.2f)' % (stem, key, err)
        save_state(st)
    assert not todo, 'sheets no gun claims: %s' % sorted(todo)
    print('rebake %s: %d sheets, %.0fs' % (','.join(coats), len(st['sheets']), time.time() - t00))


# ---------------------------------------------------------------- layered finishes
def make_tiles():
    T = os.path.join(HERE, '..', 'assets', 'tiles')
    sc = np.asarray(Image.open(os.path.join(T, 'wear_scratch.png')).convert('L'), float) / 255.0
    ch = np.asarray(Image.open(os.path.join(T, 'wear_chips.png')).convert('RGBA'), float)[..., 3] / 255.0
    vi = np.asarray(Image.open(os.path.join(T, 'engrave_vines.png')).convert('RGBA'), float)[..., 3] / 255.0
    n = sc.shape[0]
    # battle-worn: light scratches (the scratch tile is 1 = clean) and rub-through chips, ADDED (black = nothing added)
    if ch.shape != sc.shape:
        ch = np.asarray(Image.fromarray((ch * 255).astype(np.uint8)).resize(sc.shape[::-1], Image.LANCZOS), float) / 255.0
    # in-game QA (r1_1080, Thompson): chips at 0.30 read as white snow specks on the wood - rub-through is a faint lightening, warm
    worn = np.clip((1 - sc) * 0.40 + (1 - ch) * 0.12, 0, 0.45)
    worn_rgb = np.dstack([worn * 1.00, worn * 0.96, worn * 0.88])
    # trench art: the cut lines darken (multiply, white = unchanged)
    vines = np.clip(1 - 0.62 * vi, 0, 1)
    # captured: soft brown mottling + small dark pits (multiply)
    rng = np.random.default_rng(1945)
    noise = np.zeros((n, n))
    for k, amp in ((8, 1.0), (16, 0.5), (32, 0.25)):
        g = rng.random((k, k))
        noise += amp * np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((n, n), Image.BICUBIC), float) / 255.0
    noise = (noise - noise.min()) / (noise.max() - noise.min())
    # seamless: the low-frequency grids above are resized, not wrapped - blend with a half-shifted copy across the seams
    w = np.minimum(np.arange(n), n - 1 - np.arange(n)) / (n / 2.0)
    wm = np.minimum(w[:, None], w[None, :])
    noise = noise * wm + np.roll(np.roll(noise, n // 2, 0), n // 2, 1) * (1 - wm)
    grime = 1 - 0.30 * np.clip((noise - 0.45) * 2.2, 0, 1)
    pits = 1 - 0.35 * (1 - ch)
    gr = np.dstack([grime * pits * 0.97, grime * pits * 0.92, grime * pits * 0.84])
    # a polished sheen: soft studio light for tcGen environment
    yy, xx = np.mgrid[0:128, 0:128] / 127.0
    env = np.clip(0.15 + 0.85 * np.exp(-((xx - 0.35) ** 2 + (yy - 0.3) ** 2) / 0.05) + 0.35 * np.exp(-((yy - 0.75) ** 2) / 0.02), 0, 1)
    tiles = {'fs2_worn.jpg': worn_rgb, 'fs2_vines.jpg': np.dstack([vines] * 3), 'fs2_grime.jpg': gr, 'fs2_env.jpg': np.dstack([env] * 3)}
    for name, a in tiles.items():
        b = io.BytesIO()
        Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), 'RGB').save(b, 'JPEG', quality=92)
        B.put('%s/%s' % (TILE_DIR, name), b.getvalue())
    print('tiles', sorted(tiles))


def make_swatches():
    """textures/coop_finishes_hd/sw/<key>.jpg, 64 x 40: the Armory's second chip row (gen_armory_urc.py) - each chip shows the real
    pattern (a crop of its tile at about the scale it has on a rifle) or the real coat colour, over the same gunmetal"""
    T = os.path.join(HERE, '..', 'assets', 'tiles')
    W, H = 64, 40
    rng = np.random.default_rng(7)
    metal = np.clip(0.22 + 0.05 * rng.standard_normal((H, W, 1)) * 0.3 + np.linspace(0.06, -0.04, H)[:, None, None], 0, 1) * np.array([1.0, 1.0, 1.08])
    chips = np.asarray(Image.open(os.path.join(T, 'wear_chips.png')).convert('RGBA').resize((W * 3, H * 3)), float)[:H, :W, 3:4] / 255.0

    def tile(name, scale):
        im = Image.open(os.path.join(T, name + '.png')).convert('RGBA')
        n = int(im.width * scale)
        return np.asarray(im.resize((n, n), Image.LANCZOS), float)[:H, :W] / 255.0

    def coat(rgb):
        return np.clip(np.array(rgb, float) / 255.0 * (0.92 + 0.08 * rng.random((H, W, 1))), 0, 1)
    out = {}
    for k in ('splitter', 'pea', 'telo', 'amoeba'):
        out[k] = tile('camo_' + k, 0.30)[..., :3]
    out['dak'] = coat((194, 166, 106))
    out['airborne'] = coat((88, 86, 56))
    out['airborne101'] = coat((88, 86, 56))
    km = coat((52, 56, 60))
    km[H // 2:, ::9] = np.array([0.46, 0.24, 0.11])          # a rust run or two
    out['kriegsmarine'] = km
    ww = tile('camo_whitewash', 0.5)[..., 3:4]
    out['whitewash'] = metal * (1 - ww) + np.array([0.86, 0.86, 0.84]) * ww
    sc = 1 - tile('wear_scratch', 0.5)[..., :1]
    out['battleworn'] = np.clip(metal * 0.9 + sc * 0.6 + (1 - chips) * 0.25, 0, 1)
    vi = tile('engrave_vines', 0.45)[..., 3:4]
    out['trenchart'] = np.clip(np.array([0.62, 0.50, 0.30]) * (1 - 0.6 * vi), 0, 1)
    g = np.linspace(0, 1, W)[None, :, None]
    out['parade'] = np.clip(metal * 1.2 + 0.45 * np.exp(-((g - 0.4) ** 2) / 0.02), 0, 1)
    gr = np.asarray(Image.open(io.BytesIO(open(os.path.join(STAGE, 'pak', *TILE_DIR.split('/'), 'fs2_grime.jpg'), 'rb').read())).resize((W * 2, W * 2)), float)[:H, :W] / 255.0
    out['captured'] = np.clip(metal * 1.25 * gr, 0, 1)
    for k, a in out.items():
        b = io.BytesIO()
        Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), 'RGB').save(b, 'JPEG', quality=92)
        B.put('textures/coop_finishes_hd/sw/%s.jpg' % k, b.getvalue())
    sheet = Image.new('RGB', (len(out) * (W + 4), H), (30, 30, 30))
    for i, k in enumerate(sorted(out)):
        sheet.paste(Image.fromarray((np.clip(out[k], 0, 1) * 255).astype(np.uint8)), (i * (W + 4), 0))
    sheet.save(os.path.join(HERE, '..', 'media', 'swatches.png'))
    print('swatches', sorted(out))


def layer_block(name, base_path, fin, wpu):
    base = re.sub(r'\.(dds|jpg|png)$', '.tga', base_path, flags=re.I)       # as the stock shaders name it (.dds wins at load)
    rep = lambda t: '%.3f' % (wpu / (TILE_CM[t] * fl.U_PER_CM))
    S = [name, "{", "\tqer_editorimage %s" % base, "\t{", "\t\tmap %s" % base, "\t\trgbGen lightingSpherical", "\t}"]

    def st(*lines):
        S.extend(["\t{"] + ["\t\t" + l for l in lines] + ["\t}"])
    if fin == 'battleworn':
        st("map $whiteimage", "blendFunc GL_DST_COLOR GL_ZERO", "rgbGen const 0.84 0.82 0.80")
        st("map %s/fs2_worn.jpg" % TILE_DIR, "blendFunc GL_ONE GL_ONE", "rgbGen lightingSpherical",
           "tcMod scale %s %s" % (rep('fs2_worn'), rep('fs2_worn')))
    elif fin == 'trenchart':
        st("map $whiteimage", "blendFunc GL_DST_COLOR GL_ZERO", "rgbGen const 1.00 0.90 0.72")
        st("map %s/fs2_vines.jpg" % TILE_DIR, "blendFunc GL_DST_COLOR GL_ZERO",
           "tcMod scale %s %s" % (rep('fs2_vines'), rep('fs2_vines')))
        st("map %s" % ENV, "blendFunc GL_ONE GL_ONE", "tcGen environment", "rgbGen const 0.16 0.12 0.06")
    elif fin == 'parade':
        st("map %s" % base, "blendFunc GL_DST_COLOR GL_SRC_COLOR")
        st("map %s" % ENV, "blendFunc GL_ONE GL_ONE", "tcGen environment", "rgbGen const 0.32 0.32 0.34")
    elif fin == 'captured':
        st("map %s/fs2_grime.jpg" % TILE_DIR, "blendFunc GL_DST_COLOR GL_ZERO",
           "tcMod scale %s %s" % (rep('fs2_grime'), rep('fs2_grime')))
    else:
        raise KeyError(fin)
    S += ["}", ""]
    return "\n".join(S)


def layers():
    st = load_state()
    missing = [k for k, s in st['sheets'].items() if 'wpu' not in s]
    assert not missing, 'run rebake first (no wpu for %d sheets)' % len(missing)
    make_tiles()
    for stem, gun in st['guns'].items():
        g = fl.load_gun(gun['tik'])
        surf_map = {sh: k for sh, (k, _sz) in gun_sheets(g).items()}
        text = B.vfs.read(gun['tik']).decode('latin-1').replace('\r\n', '\n')
        for fin, disp, fid in LAYERED:
            if fin not in gun['variants']:
                gun['variants'][fin] = dict(rank=st['rank'], fid=fid)
                st['rank'] += 1
            v = gun['variants'][fin]
            smap = {sh: 'coop_fs2_%s_%s' % (key, fin) for sh, key in surf_map.items()}
            vt = L.variant_tik(text, disp, v['rank'], smap).replace('\n', '\r\n')
            B.put('models/weapons/%s_fs2_%s.tik' % (stem, fin), vt.encode('latin-1'))
    save_state(st)
    print('layers: %d guns x %d finishes, rank now %d' % (len(st['guns']), len(LAYERED), st['rank']))


def pack():
    make_swatches()
    st = load_state()
    blocks = []
    for key, s in sorted(st['sheets'].items()):
        for f in B.FINS:
            mp = 'textures/coop_finishes_hd/%s/%s.png' % (key, 'mask_ww' if f == 'whitewash' else 'mask')
            blocks.append(L.shader_block('coop_fs2_%s_%s' % (key, f), s['path'], mp, 'textures/coop_finishes_hd/%s/%s.jpg' % (key, f)))
        if 'wpu' in s:
            for fin, _d, _fid in LAYERED:
                blocks.append(layer_block('coop_fs2_%s_%s' % (key, fin), s['path'], fin, s['wpu']))
    B.put('scripts/coop_finishes_hd.shader', ('// GENERATED by docs/proposals/finishes2_2026-11-09/tools/fs2_build.py + fs2_finish2.py\n\n'
                                             + '\n'.join(blocks)).replace('\n', '\r\n').encode())
    with open(os.path.join(STAGE, 'rows.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('give\tfid\tfinish\tvariant\trank\n')
        for stem, gun in sorted(st['guns'].items()):
            for fin, v in sorted(gun['variants'].items(), key=lambda kv: kv[1]['fid']):
                f.write('%s\t%d\t%s\tmodels/weapons/%s_fs2_%s.tik\t%d\n' % (gun['tik'], v['fid'], fin, stem, fin, v['rank']))
    # deterministic: sorted names, one fixed timestamp, fixed compression per type (the updater compares sha256)
    pak = os.path.join(STAGE, B.PAK)
    root = os.path.join(STAGE, 'pak')
    rels = []
    for d, _ds, fs_ in os.walk(root):
        for n in fs_:
            rels.append(os.path.relpath(os.path.join(d, n), root).replace(os.sep, '/'))
    tmp = pak + '.tmp'
    with zipfile.ZipFile(tmp, 'w') as z:
        for rel in sorted(rels, key=str.lower):
            zi = zipfile.ZipInfo(rel, date_time=(2026, 11, 9, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_STORED if rel.endswith(('.jpg', '.png')) else zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, open(os.path.join(root, *rel.split('/')), 'rb').read())
    os.replace(tmp, pak)
    h = hashlib.sha256(open(pak, 'rb').read()).hexdigest()
    print('pak %s %.1f MB, %d files, sha256 %s' % (pak, os.path.getsize(pak) / 1e6, len(rels), h))


def rerank(start):
    """[v1.10.68] the agreed 1240+ band collides with the standard finishes already shipped (1000-1724 are taken: 81 guns x 7
    finishes + model variants), so every finishes2 variant moves to a clean band: start, start+1, ... in gun / fid order"""
    st = load_state()
    r = start
    for stem, gun in st['guns'].items():
        for fin, v in sorted(gun['variants'].items(), key=lambda kv: kv[1]['fid']):
            v['rank'] = r
            p = os.path.join(STAGE, 'pak', 'models', 'weapons', '%s_fs2_%s.tik' % (stem, fin))
            t = open(p, 'rb').read().decode('latin-1')
            t2, n = re.subn(r"(?mi)^(\s*rank\s+)\d+\s+\d+", lambda m: "%s%d %d" % (m.group(1), r, r), t, count=1)
            assert n == 1, p
            open(p, 'wb').write(t2.encode('latin-1'))
            r += 1
    st['rank'] = r
    save_state(st)
    print('rerank: %d .. %d' % (start, r - 1))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'rebake':
        rebake(sys.argv[2].split(','), set(sys.argv[3:]))
    elif cmd == 'layers':
        layers()
    elif cmd == 'rerank':
        rerank(int(sys.argv[2]))
    elif cmd == 'pack':
        pack()
    else:
        raise SystemExit(__doc__)
