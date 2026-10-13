"""The mod's CURRENT Mauser C96: triangle counts, texture sizes, and the skinned mesh as JSON for the comparison render.
Reuses the project's own readers (ironsights_2026-09-28/tools: vfs / skdlib / gungeo). Reads the mod's files only.
    python old_c96_dump.py <out.json>
"""
import sys, os, re, json, struct
HERE = os.path.dirname(os.path.abspath(__file__))
IS = os.path.join(HERE, '..', '..', 'ironsights_2026-09-28', 'tools')
sys.path.insert(1, os.path.abspath(IS))
import gungeo  # noqa: E402

MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'
g = gungeo.load_gun('models/weapons/mauser_c96.tik')
sh = open(os.path.join(MOD, 'scripts', 'coop_c96.shader'), encoding='latin-1').read()
tex = {}
for m in re.finditer(r'^(\w+)\s*\{(.*?)^\}', sh, re.M | re.S):
    mm = re.search(r'^\s*map\s+(\S+)', m.group(2), re.M)
    if mm:
        tex[m.group(1).lower()] = mm.group(1)


def tga(p):
    h = open(p, 'rb').read(18)
    return '%dx%d %dbpp' % (struct.unpack('<HH', h[12:16]) + (h[16],))


out = {'skd': g['skd'], 'pak': g['skdpak'], 'scale': g['tik']['scale'], 'surfs': []}
tot = 0
for s in g['surfs']:
    t = tex.get(s['shader'].lower())
    ap = os.path.join(MOD, t.replace('/', os.sep)) if t else None
    info = tga(ap) if ap and os.path.exists(ap) else None
    pre = ap + '.pre_upscale_nobuild' if ap else None
    pinfo = tga(pre) if pre and os.path.exists(pre) else None
    n = len(s['tri']); tot += n
    print('%-12s %-18s tris %5d verts %5d  %s  now %s  before upscale %s' % (s['name'], s['shader'], n, len(s['P']), t, info, pinfo))
    out['surfs'].append({'name': s['name'], 'shader': s['shader'], 'tex': ap, 'P': s['P'].tolist(), 'UV': s['UV'].tolist(), 'tri': s['tri'].tolist()})
import numpy as np  # noqa: E402
P = np.vstack([np.array(s['P']) for s in out['surfs']])
print('TOTAL tris', tot, 'surfaces', len(out['surfs']), 'bbox min', P.min(0).round(2), 'max', P.max(0).round(2), 'pak', g['skdpak'])
json.dump(out, open(sys.argv[1], 'w'))
