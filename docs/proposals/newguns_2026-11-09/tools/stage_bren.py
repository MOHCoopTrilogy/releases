"""Stage the Bren into the wpnfix sources (docs/tools/assets/wpnfix of THIS worktree) and pin the new files in its manifest.

  models/weapons/coop_bren.tik                 the Vickers-Berthier's tik (stress-pak winner), re-pointed: own mesh, sheet, name, rank
  models/weapons/coop_bren/coop_bren.skd       build_bren.py
  models/weapons/coop_bren/*.skc               the VB's weapon clips (v14 -> v13), tag_barrel moved onto the Bren's muzzle (it is
                                               4.7 u shorter than the VB at the grip the hands hold) and tag_eject under the body:
                                               the Bren throws its cases DOWN through a port under the receiver
  textures/models/weapons/coop_bren/bren.jpg   bren_sheet.py
  scripts/coop_newguns.shader                  + coop_bren (the new guns' own shader file)
  credits/coop_cc_models.txt                   + the Bren's CC BY 4.0 credit
    python stage_bren.py [--root <worktree root>]
"""
import os, sys, json, re, shutil, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools")
import pk, brenlib as L
import skc14to13 as C
import skdlib

ROOT = sys.argv[sys.argv.index('--root') + 1] if '--root' in sys.argv else os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
SRC = os.path.join(ROOT, 'docs', 'tools', 'assets', 'wpnfix')
MAN = os.path.join(SRC, 'wpnfix_manifest.json')
CLIPS = ['Uk_W_Vickers.skc', 'A_W_Vickers_reload_W.skc', 'coop_A_W_Vickers_reload_W_s.skc', 'coop_A_W_Vickers_reload_W_m.skc',
         'coop_vickers_fire.skc']
NEWCLIP = {'Uk_W_Vickers.skc': 'coop_bren_idle.skc', 'A_W_Vickers_reload_W.skc': 'coop_bren_reload.skc',
           'coop_A_W_Vickers_reload_W_s.skc': 'coop_bren_reload_s.skc', 'coop_A_W_Vickers_reload_W_m.skc': 'coop_bren_reload_m.skc',
           'coop_vickers_fire.skc': 'coop_bren_fire.skc'}
VB_LOCAL = np.diag([1 / 0.52, -1 / 0.52, -1 / 0.52])      # gun frame -> `vickers` bone-local (vb_affine_1: no translation)
EJECT_SRC = np.array([2.3, 0.0, 1.0])                       # under the receiver, below the magazine well (source)
EJECT_DIR = np.array([0.15, 0.25, 0.95])                    # gun frame: down, a little right and forward


def mat_to_quat(R):
    """inverse of skdlib.quat_to_mat3 (checked by round trip below)"""
    best = None
    for q in _candidates(R):
        e = np.abs(np.array(skdlib.quat_to_mat3(q)) - R).max()
        if best is None or e < best[0]:
            best = (e, q)
    assert best[0] < 1e-4, best
    return best[1]


def _candidates(R):
    import itertools
    t = np.trace(R)
    out = []
    for M in (R, R.T):
        w = np.sqrt(max(0.0, 1 + M[0, 0] + M[1, 1] + M[2, 2])) / 2
        x = np.sqrt(max(0.0, 1 + M[0, 0] - M[1, 1] - M[2, 2])) / 2
        y = np.sqrt(max(0.0, 1 - M[0, 0] + M[1, 1] - M[2, 2])) / 2
        z = np.sqrt(max(0.0, 1 - M[0, 0] - M[1, 1] + M[2, 2])) / 2
        for sx, sy, sz in itertools.product((1, -1), repeat=3):
            out.append((sx * x, sy * y, sz * z, w))
    return out


def eject_rot():
    x = EJECT_DIR / np.linalg.norm(EJECT_DIR)
    xl = x @ VB_LOCAL; xl /= np.linalg.norm(xl)
    z = np.array([1.0, 0, 0]); z = z - np.dot(z, xl) * xl; z /= np.linalg.norm(z)
    y = np.cross(z, xl)
    return mat_to_quat(np.array([xl, y, z]))


def clip(name, bren_muzzle_x):
    b = pk.read('models/weapons/Vickers/' + name)
    if struct.unpack_from('<i', b, 4)[0] == 14:
        b = C.convert(b)
    b = bytearray(b)
    ch, fr = pk.skc(bytes(b))
    nf = struct.unpack_from('<i', b, 44)[0]
    ib, ie, ir = ch.index('tag_barrel pos'), ch.index('tag_eject pos'), ch.index('tag_eject rot')
    ep = L.to_gun(EJECT_SRC) @ VB_LOCAL
    q = eject_rot()
    for f in range(nf):
        ov = struct.unpack_from('<i', b, 48 + 48 * f + 44)[0]
        px, py, pz, _ = struct.unpack_from('<4f', b, ov + 16 * ib)
        struct.pack_into('<4f', b, ov + 16 * ib, float(bren_muzzle_x / 0.52), py, pz, 0.0)
        struct.pack_into('<4f', b, ov + 16 * ie, float(ep[0]), float(ep[1]), float(ep[2]), 0.0)
        struct.pack_into('<4f', b, ov + 16 * ir, *[float(v) for v in q])
    return bytes(b), (px, float(bren_muzzle_x / 0.52))


def tik():
    t = pk.read('models/weapons/uk_w_vickers.tik').decode('latin-1')
    setup = ("setup\n{\n\tscale 0.52\n"
             "\t// HZM coop [newguns 2026-11-09] the Bren Mk I: maximiliaanmaene's \"Bren Mk1 LMG\" (Sketchfab df74f7e3720d469e8bf425407e7ddc34,\n"
             "\t// CC BY 4.0, modified: ~10k triangles, its PBR maps baked to one 2048 sheet, the bipod folded), rigged on the Vickers-Berthier's\n"
             "\t// bones so the VB's hands and clips drive it (docs/proposals/newguns_2026-11-09). Its clips are copies with tag_barrel on\n"
             "\t// the Bren's muzzle and tag_eject under the body.\n"
             "\tpath models/weapons/coop_bren\n\tskelmodel coop_bren.skd\n"
             "\tsurface bren* shader coop_bren\n\tsurface brenclip shader coop_bren\n\tsurface brenchg shader coop_bren\n}\n")
    t = re.sub(r"setup\s*\{.*?\}\s*\n", setup, t, count=1, flags=re.S)
    assert t.count('name\t\t\t"Vickers-Berthier"') == 1
    t = t.replace('name\t\t\t"Vickers-Berthier"', 'name\t\t\t"Bren"')
    t = re.sub(r"(\n\s*rank\s+)430 430", r"\g<1>431 431", t, count=1)
    t = t.replace('cache models/weapons/Uk_W_Vickers_clip.tik', 'cache models/weapons/coop_bren_clip.tik')   # its own reload prop
    # the Bren cycles ~500 rounds a minute (the VB's 0.14 s is ~430): 0.12 s in every mode
    t = re.sub(r"(\n\s*(?:dm|realism) firedelay\s+)0\.14", r"\g<1>0.12", t)
    t = t.replace('exec coop_mod/itemhandler.scr "initialiseItem" "mg" "Vickers-Berthier"',
                  'exec coop_mod/itemhandler.scr "initialiseItem" "mg" "Bren"')
    for a, b in NEWCLIP.items():
        t = re.sub(r"(\s)%s(\s)" % re.escape(a), r"\g<1>%s\g<2>" % b, t)
    t = re.sub(r"surface\s+material3\s+([+-]nodraw)", r"surface brenclip \1", t, flags=re.I)
    t = re.sub(r"/\*QUAKED.*?\*/", "/*QUAKED weapon_coop_bren (0.0 0.0 0.0) (-65 -40 0) (65 40 120) Bren\n*/", t, flags=re.S)
    bad = [l for l in t.splitlines() if ('Vickers-Berthier' in l or 'Uk_W_Vickers.skc' in l) and not l.strip().startswith('//')]
    assert not bad, bad
    return t


SHADER = """
// [newguns 2026-11-09] the Bren Mk I's sheet: maximiliaanmaene's Bren Mk1 LMG (CC BY 4.0, modified), PBR baked to one diffuse
coop_bren
{
	qer_editorimage textures/models/weapons/coop_bren/bren.jpg
	{
		map textures/models/weapons/coop_bren/bren.jpg
		rgbGen lightingSpherical
	}
}
"""
HEAD = "// HZM coop [newguns 2026-11-09] shaders of the new CC-model guns (docs/proposals/newguns_2026-11-09)\n"
CREDIT = """
Bren Mk I (models/weapons/coop_bren.tik, models/weapons/coop_bren/, textures/models/weapons/coop_bren/, its finishes)
  "Bren Mk1 LMG" by maximiliaanmaene
  https://sketchfab.com/3d-models/df74f7e3720d469e8bf425407e7ddc34
  Licence: Creative Commons Attribution 4.0 International (CC BY 4.0) - https://creativecommons.org/licenses/by/4.0/
  Modified: reduced to about 10,000 triangles, levelled, the bipod folded, rigged on the Vickers-Berthier's skeleton and
  animations, PBR maps baked into one diffuse sheet, finish variants derived from it.
"""


def put(rel, data, man):
    p = os.path.join(SRC, *rel.split('/'))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(data)
    man.setdefault(rel, {'new': True})
    print('  %-58s %8d bytes' % (rel, len(data)))


def main():
    man = json.load(open(MAN))
    meta = json.load(open(os.path.join(L.BUILD, 'coop_bren.json')))
    muzzle_x = meta['gun_max'][0]
    put('models/weapons/coop_bren/coop_bren.skd', open(os.path.join(L.BUILD, 'ship', 'models', 'weapons', 'coop_bren', 'coop_bren.skd'), 'rb').read(), man)
    put('textures/models/weapons/coop_bren/bren.jpg', open(os.path.join(L.BUILD, 'bren.jpg'), 'rb').read(), man)
    for n in CLIPS:
        data, (old, new) = clip(n, muzzle_x)
        put('models/weapons/coop_bren/' + NEWCLIP[n], data, man)
    print('  tag_barrel x %.2f -> %.2f (local)' % (old, new))
    put('models/weapons/coop_bren.tik', tik().encode('latin-1'), man)
    # the new guns' shaders live in their own file (no edit to coop_wpnfix.shader, which other branches change)
    sh = os.path.join(SRC, 'scripts', 'coop_newguns.shader')
    s = open(sh, 'rb').read().decode('latin-1') if os.path.isfile(sh) else HEAD
    if '\ncoop_bren\n' not in s:
        s = s.rstrip() + '\n' + SHADER
    put('scripts/coop_newguns.shader', s.encode('latin-1'), man)
    cr = os.path.join(SRC, 'credits', 'coop_cc_models.txt')
    c = open(cr, 'rb').read().decode('utf-8')
    if 'maximiliaanmaene' not in c:
        nl = '\r\n' if '\r\n' in c else '\n'
        open(cr, 'wb').write((c.rstrip() + nl + CREDIT.replace('\n', nl)).encode('utf-8'))
    # gen_wpnfix_pak's own format (LF, sorted keys, indent 2)
    open(MAN, 'w', encoding='utf-8', newline='\n').write(json.dumps(man, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
