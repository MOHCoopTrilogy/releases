"""S&W M10: the rear face of the cylinder (coordinator 2026-10-12: "reads as a flat dark disc").

The mesh's cylinder is an open tube, so two NEW surfaces are appended to the split skd, weighted to the cylinder bone
(coop_cyl) so they swing out with it:
  coop_m10_face    a disc on the rear face: blued steel, six chamber mouths, the extractor star
  coop_m10_heads   six cartridge heads (brass rim + primer) just proud of it - hidden while the cylinder is empty
plus their two 128x128 textures (drawn here, nothing downloaded), one shader script and the tik lines.

    python m10face.py            (after m10probe.py; before m10build.py writes the tik - it calls tik_lines())
"""
import sys, os, struct, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T)
_c = os.getcwd(); os.chdir(T)
import vmcam as V
os.chdir(_c)
PR = V.PR; R = V.R
G = PR.gungeo; SK = PR.skdlib
STAGE = os.path.join(HERE, 'stage')
SKD = os.path.join(STAGE, 'models', 'weapons', 'coop_m10', 'm10.skd')
TIK = 'models/weapons/m10_revolver.tik'
N_CH = 6
RING = 0.60          # chamber circle radius / cylinder radius
R_CH = 0.235         # chamber mouth radius / cylinder radius


def disc(c, r, x, n=20):
    """fan facing -x (toward the shooter): [(pos, normal, uv)], tris; uv = the disc mapped onto the whole texture"""
    nrm = np.array([-1.0, 0.0, 0.0])
    verts = [(np.array([x, c[0], c[1]]), nrm, (0.5, 0.5))]
    for k in range(n):
        a = 2 * math.pi * k / n
        verts.append((np.array([x, c[0] + r * math.cos(a), c[1] + r * math.sin(a)]), nrm, (0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a))))
    tris = []
    for k in range(n):
        t = (0, 1 + k, 1 + (k + 1) % n)
        pa, pb, pc = (verts[i][0] for i in t)
        if np.cross(pb - pa, pc - pa) @ nrm > 0:          # retail winding: cross(b-a, c-a) . n < 0
            t = (t[0], t[2], t[1])
        tris.append(t)
    return verts, tris


def append_surface(data, name, verts, tris, bone, M, sc):
    """a new skelSurface_t after the last one. verts in GUN space (tik-scaled); M = the bone's 4x3 world (skd units)"""
    m = SK.read_skd(data)
    last = max(m.surfaces, key=lambda s: s.raw_off)
    off = last.raw_off
    ntri, nvert, static, oTri, oVerts, oColl, oEnd, oCI = struct.unpack_from('<8i', data, off + 68)
    assert off + oEnd == m.ofsEnd, (off + oEnd, m.ofsEnd, len(data))     # the file may carry a few padding bytes after ofsEnd
    ci_max = max(max(struct.unpack_from('<%di' % s.numVerts, data, s.raw_off + struct.unpack_from('<8i', data, s.raw_off + 68)[7]))
                 for s in m.surfaces)
    head = bytearray(data[off: off + oTri])            # ident + name + the 8 ints (+ anything the format keeps there)
    nb = name.encode('latin-1')
    head[4:68] = nb + b'\0' * (64 - len(nb))
    Rt = np.asarray(M)[0:3].T
    bt = b''.join(struct.pack('<3i', *t) for t in tris)
    bv = b''
    for p, n, uv in verts:
        o = (p / sc - np.asarray(M)[3]) @ Rt
        bv += struct.pack('<3f2f2i', *(n @ Rt), float(uv[0]), float(uv[1]), 1, 0) + struct.pack('<if3f', bone, 1.0, *o)
    bc = struct.pack('<%di' % len(verts), *([0] * len(verts)))
    bi = struct.pack('<%di' % len(verts), *([ci_max] * len(verts)))     # never cut by LOD before the rest of the gun
    o1 = oTri; o2 = o1 + len(bt); o3 = o2 + len(bv); o4 = o3 + len(bc); o5 = o4 + len(bi)
    struct.pack_into('<8i', head, 68, len(tris), len(verts), static, o1, o2, o3, o5, o4)
    blk = bytes(head) + bt + bv + bc + bi
    out = bytearray(data[:m.ofsEnd]) + blk + bytearray(data[m.ofsEnd:])
    end = m.ofsEnd + len(blk)
    struct.pack_into('<5i', out, 72, m.numSurfaces + 1, m.numBones, m.ofsBones, m.ofsSurfaces, end)
    tail = list(struct.unpack_from('<4i', out, 132))
    struct.pack_into('<4i', out, 132, *[end if x == m.ofsEnd else x for x in tail])
    return bytes(out)


def textures():
    from PIL import Image, ImageDraw
    d = os.path.join(STAGE, 'textures', 'coop_m10'); os.makedirs(d, exist_ok=True)
    S = 512
    # face: blued steel with chamber mouths and the extractor star (drawn 4x, reduced)
    im = Image.new('RGB', (S, S), (44, 52, 62)); g = ImageDraw.Draw(im)
    g.ellipse((6, 6, S - 6, S - 6), fill=(58, 68, 80), outline=(96, 108, 122), width=6)
    for k in range(N_CH):
        a = 2 * math.pi * k / N_CH
        cx, cy = S / 2 + RING * S / 2 * math.cos(a), S / 2 + RING * S / 2 * math.sin(a)
        r = R_CH * S / 2
        g.ellipse((cx - r - 7, cy - r - 7, cx + r + 7, cy + r + 7), fill=(104, 116, 130))      # chamfer
        g.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(6, 7, 9))                              # the mouth
        g.arc((cx - r, cy - r, cx + r, cy + r), 200, 320, fill=(40, 46, 54), width=5)
    star = []
    for k in range(2 * N_CH):
        a = 2 * math.pi * (k + 0.5) / (2 * N_CH)
        rr = (0.30 if k % 2 == 0 else 0.17) * S / 2
        star.append((S / 2 + rr * math.cos(a), S / 2 + rr * math.sin(a)))
    g.polygon(star, fill=(84, 96, 110), outline=(30, 34, 40))
    g.ellipse((S / 2 - 26, S / 2 - 26, S / 2 + 26, S / 2 + 26), fill=(112, 124, 138), outline=(30, 34, 40), width=4)
    im.resize((128, 128), Image.LANCZOS).save(os.path.join(d, 'coop_m10_face.tga'))
    # head: brass case head, rim ring, primer
    im = Image.new('RGB', (S, S), (150, 112, 48)); g = ImageDraw.Draw(im)
    g.ellipse((4, 4, S - 4, S - 4), fill=(196, 158, 78), outline=(120, 88, 36), width=22)
    g.ellipse((60, 60, S - 60, S - 60), outline=(214, 180, 104), width=10)
    g.ellipse((S / 2 - 96, S / 2 - 96, S / 2 + 96, S / 2 + 96), fill=(176, 150, 112), outline=(96, 72, 34), width=12)
    g.ellipse((S / 2 - 30, S / 2 - 40, S / 2 + 20, S / 2 + 10), fill=(214, 196, 160))
    im.resize((128, 128), Image.LANCZOS).save(os.path.join(d, 'coop_m10_head.tga'))
    sd = os.path.join(STAGE, 'scripts'); os.makedirs(sd, exist_ok=True)
    open(os.path.join(sd, 'coop_m10_face.shader'), 'w', newline='\n').write(
        '// HZM coop [revolver reload 2026-10-12] S&W M10 cylinder rear face + cartridge heads (m10face.py)\n'
        'coop_m10_face\n{\n\tqer_editorimage textures/coop_m10/coop_m10_face.tga\n\t{\n\t\tmap textures/coop_m10/coop_m10_face.tga\n\t\trgbGen lightingSpherical\n\t}\n}\n'
        'coop_m10_heads\n{\n\tqer_editorimage textures/coop_m10/coop_m10_head.tga\n\t{\n\t\tmap textures/coop_m10/coop_m10_head.tga\n\t\trgbGen lightingSpherical\n\t}\n}\n')


def tik_lines():
    return ('\tsurface coop_m10_face shader coop_m10_face\n\tsurface coop_m10_heads shader coop_m10_heads\n')


def main():
    data = open(SKD, 'rb').read()
    m = SK.read_skd(data)
    if any(s.name == 'coop_m10_face' for s in m.surfaces):
        print('face already in', SKD); textures(); return
    names = [b.name for b in m.bones]
    bi = names.index('coop_cyl')
    t = G.parse_tik(TIK)
    sc = t['scale']
    skc = SK.read_skc(PR.vfs.read(G._res(t, t['anims']['idle'])))
    mats, _ = G.bone_world(m, skc, 0)
    pts = json.load(open(os.path.join(HERE, 'm10_points.json')))
    cy, cz = pts['c_closed'][1], pts['c_closed'][2]
    rad = pts['radius']; x0 = pts['rear_x']
    fv, ft = disc((cy, cz), rad * 0.97, x0 - 0.015, 24)
    data = append_surface(data, 'coop_m10_face', fv, ft, bi, mats[bi], sc)
    hv, ht = [], []
    for k in range(N_CH):
        a = 2 * math.pi * k / N_CH
        v, tr = disc((cy + RING * rad * math.cos(a), cz + RING * rad * math.sin(a)), rad * R_CH * 1.12, x0 - 0.05, 10)
        b = len(hv)
        hv += v; ht += [(p + b, q + b, r_ + b) for p, q, r_ in tr]
    data = append_surface(data, 'coop_m10_heads', hv, ht, bi, mats[bi], sc)
    open(SKD, 'wb').write(data)
    m2 = SK.read_skd(data)
    print('surfaces', [(s.name, s.numVerts) for s in m2.surfaces][-3:], 'bytes', len(data))
    textures()
    json.dump(dict(ring=RING, r_ch=R_CH, chambers=[[x0, cy + RING * rad * math.cos(2 * math.pi * k / N_CH), cz + RING * rad * math.sin(2 * math.pi * k / N_CH)]
                                                   for k in range(N_CH)]), open(os.path.join(HERE, 'm10_face.json'), 'w'))


if __name__ == '__main__':
    main()
