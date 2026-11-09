"""finishes2 - full build of the PAINT / CAMO finishes (whitewash, DAK, Kriegsmarine, airborne OD (+ the 101st variant on the
same coat), splitter, pea, telo, amoeba) for every holdable gun, into a STAGING tree for zzzzzzzzzz_coop_finishes_hd.pk3:
  textures/coop_finishes_hd/<sheet>/mask.png, mask_ww.png        coat coverage (grey), shared by the finishes of a sheet
  textures/coop_finishes_hd/<sheet>/<fin>.jpg                    the premultiplied coat, q85, max side 1024 (user)
  scripts/coop_finishes_hd.shader                                one shader per sheet x finish (fs2_layers.shader_block)
  models/weapons/<stem>_fs2_<fin>.tik                            the variant weapon: name "<Base> (<Finish>)", rank 1240+
  rows.tsv                                                       give path, fid (40+), variant tik - for loadoutskins.scr
Nothing is deployed: the pak is written to the staging dir only. Sheets two guns share are baked once (the first gun's mask).
    python fs2_build.py <roster.tsv> [stem ...]
"""
import hashlib, io, json, os, re, sys, time, zipfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import finishlib as fl  # noqa: E402
import fs2_layers as L  # noqa: E402
import uvview  # noqa: E402
sys.path.insert(0, os.path.join(HERE, '..', '..', 'ironsights_2026-09-28', 'tools'))
import vfs  # noqa: E402

STAGE = os.path.join("H:" + os.sep, "hzm_work", "finishes2_build")
PAK = "zzzzzzzzzz_coop_finishes_hd.pk3"
FINS = ('whitewash', 'dak', 'kriegsmarine', 'airborne', 'splitter', 'pea', 'telo', 'amoeba')
VARIANTS = FINS + ('airborne101',)                   # airborne101 = the airborne coat; its patch is a bench quad
DISPLAY = dict(whitewash='Whitewash', dak='Afrika Korps', kriegsmarine='Kriegsmarine', airborne='Airborne',
               airborne101='Airborne 101st', splitter='Splinter', pea='Pea Dot', telo='Telo', amoeba='Amoeba')
FID0, RANK0 = 40, 1240                               # agreed ranges (README)
SKIP = re.compile(r'(clip|sight|scope|glass|bullet|round|ammo|strap|sling|reticle|lens|hand|flash|muzzle|env|gloss)', re.I)
GRENADES = {'64', '65', '66', '67', '68', '69'}


def sheet_key(path):
    stem = re.sub(r'[^a-z0-9]+', '_', os.path.splitext(os.path.basename(path))[0].lower()).strip('_')
    return "%s_%s" % (stem, hashlib.md5(path.lower().encode()).hexdigest()[:4])


def put(rel, data):
    p = os.path.join(STAGE, 'pak', *rel.split('/'))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(data)


def main():
    rows = [l.rstrip('\n').split('\t') for l in open(sys.argv[1], encoding='utf-8') if l.strip()]
    only = set(sys.argv[2:])
    os.makedirs(STAGE, exist_ok=True)
    state_p = os.path.join(STAGE, 'state.json')
    st = json.load(open(state_p)) if os.path.exists(state_p) else dict(sheets={}, guns={}, rank=RANK0)
    for gid, tik, name, cls in rows:
        stem = os.path.splitext(os.path.basename(tik))[0]
        if gid in GRENADES or (only and stem not in only):
            continue
        t0 = time.time()
        g = fl.load_gun(tik)
        surf_map = {}
        for sh in sorted(set(s['shader'] for s in g['surfs'])):
            m, path, pk, im, blk = uvview.shader_image(sh)
            if im is None or SKIP.search(path or '') or min(im.size) < 256:
                continue
            key = sheet_key(path)
            if key not in st['sheets']:
                _p, masks, coats = L.layers(g, sh, FINS)
                # the mask as a GREY png (coverage in its value; the darken stage is GL_ZERO GL_ONE_MINUS_SRC_COLOR). Measured
                # for all 126 sheets: grey png 40.6 MB, grey jpeg 49.8 (the chip noise), RGBA png 58.7
                b = io.BytesIO(); masks['dak'].split()[3].save(b, 'PNG', optimize=True)
                put('textures/coop_finishes_hd/%s/mask.png' % key, b.getvalue())
                b = io.BytesIO(); masks['whitewash'].split()[3].save(b, 'PNG', optimize=True)
                put('textures/coop_finishes_hd/%s/mask_ww.png' % key, b.getvalue())
                for f in FINS:
                    b = io.BytesIO(); coats[f].save(b, 'JPEG', quality=85, optimize=True)
                    put('textures/coop_finishes_hd/%s/%s.jpg' % (key, f), b.getvalue())
                st['sheets'][key] = dict(path=path, shader=sh, size=list(im.size))
            surf_map[sh] = key
        if not surf_map:
            print(gid, stem, 'no paintable sheet', flush=True)
            continue
        raw = vfs.read(tik)
        text = raw.decode('latin-1').replace('\r\n', '\n')
        base_name = re.search(r'(?mi)^\s*name\s+"([^"]+)"', text).group(1)
        gun = st['guns'].setdefault(stem, dict(tik=tik, name=base_name, variants={}))
        for i, f in enumerate(VARIANTS):
            coat = 'airborne' if f == 'airborne101' else f
            smap = {sh: 'coop_fs2_%s_%s' % (key, coat) for sh, key in surf_map.items()}
            if f not in gun['variants']:
                gun['variants'][f] = dict(rank=st['rank'], fid=FID0 + i)
                st['rank'] += 1
            v = gun['variants'][f]
            vt = L.variant_tik(text, DISPLAY[f], v['rank'], smap).replace('\n', '\r\n')
            put('models/weapons/%s_fs2_%s.tik' % (stem, f), vt.encode('latin-1'))
        json.dump(st, open(state_p, 'w'), indent=1)
        print(gid, stem, len(surf_map), 'sheets', '%.0fs' % (time.time() - t0), flush=True)
    # shaders + rows for everything built so far
    blocks = []
    for key, s in sorted(st['sheets'].items()):
        for f in FINS:
            mp = 'textures/coop_finishes_hd/%s/%s.png' % (key, 'mask_ww' if f == 'whitewash' else 'mask')
            blocks.append(L.shader_block('coop_fs2_%s_%s' % (key, f), s['path'], mp,
                                         'textures/coop_finishes_hd/%s/%s.jpg' % (key, f)))
    put('scripts/coop_finishes_hd.shader', ('// GENERATED by docs/proposals/finishes2_2026-11-09/tools/fs2_build.py\n\n'
                                           + '\n'.join(blocks)).replace('\n', '\r\n').encode())
    with open(os.path.join(STAGE, 'rows.tsv'), 'w', encoding='utf-8') as f:
        f.write('give\tfid\tfinish\tvariant\trank\n')
        for stem, gun in sorted(st['guns'].items()):
            for fin, v in sorted(gun['variants'].items(), key=lambda kv: kv[1]['fid']):
                f.write('%s\t%d\t%s\tmodels/weapons/%s_fs2_%s.tik\t%d\n' % (gun['tik'], v['fid'], fin, stem, fin, v['rank']))
    pak = os.path.join(STAGE, PAK)
    with zipfile.ZipFile(pak, 'w', zipfile.ZIP_DEFLATED) as z:
        root = os.path.join(STAGE, 'pak')
        for d, _ds, fs_ in os.walk(root):
            for n in sorted(fs_):
                p = os.path.join(d, n)
                rel = os.path.relpath(p, root).replace(os.sep, '/')
                z.write(p, rel, compress_type=zipfile.ZIP_STORED if rel.endswith(('.jpg', '.png')) else zipfile.ZIP_DEFLATED)
    print('pak', pak, '%.1f MB' % (os.path.getsize(pak) / 1e6), len(st['sheets']), 'sheets', len(st['guns']), 'guns')


if __name__ == '__main__':
    main()
