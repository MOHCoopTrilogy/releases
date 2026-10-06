"""Offline prototype: renderer-side BONE-CHAIN COLLAPSE dismemberment on the real German soldier.

Bones: the engine-exact skeletor port (docs/proposals/ragdoll_2026-09-27/lookdev/tools/skel_extract.py).
Mesh:  the real composite (german_wehrmact_soldier.tik setup -> body + head + hands skds), CPU-skinned the
       way RB_SkelMesh does it: p = sum_w  w * ([offset,1] @ BoneWorld).
Cut:   every bone in the limb chain gets rows 0..2 = 0 and row 3 = the cut joint's world origin - exactly
       what a "Hook C" after ragdoll Hook A would write into skelBoneCache. KEEP mode (the severed-limb gib)
       is the inverse: every bone NOT in the chain collapses to the cut joint.
Out:   limb_proto.png (painter's-algorithm flat-shaded stills; red = triangles that touch the cut).
"""
import os, sys, math, re, types
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SE = os.path.normpath(os.path.join(HERE, "..", "..", "ragdoll_2026-09-27", "lookdev", "tools", "skel_extract.py"))
src = open(SE, encoding="utf-8").read()
# helpers (HOSEROT/AVROT): keep the parent's axes but apply the bone's base offset, so elbow/knee/hip helper
# verts sit at the joint instead of at the parent origin (lookdev approximation, noted in PLAN.md)
src = src.replace("""                unsupported.add(n)
                m = parent_tm(b).copy()""", """                unsupported.add(n)
                m = parent_tm(b).copy()
                off = b["base"][3:6] if t in (5, 10, 11) else b["base"][1:4]
                m[3] = m[3] + np.array(off) @ m[0:3]""")
src = src.replace("out = {n: get(n) for n, _ in RAG_BONES}", "out = {n: get(n) for n in self.order}")
se = types.ModuleType("se"); se.__file__ = SE
exec(compile(src, SE, "exec"), se.__dict__)

sys.path.insert(0, HERE)
import skd_collapse as K  # surfaces + weights parser

CHAINS = {
    "R_arm_upper": ["Bip01 R UpperArm", "Bip01 R Forearm", "Bip01 R Hand", "helper Relbow", "tag_weapon_right"],
    "L_arm_lower": ["Bip01 L Forearm", "Bip01 L Hand", "tag_weapon_left"],
    "L_leg_lower": ["Bip01 L Calf", "Bip01 L Foot", "Bip01 L Toe0", "helper Lankle"],
    "R_leg_upper": ["Bip01 R Thigh", "Bip01 R Calf", "Bip01 R Foot", "Bip01 R Toe0", "helper Rknee", "helper Rankle"],
}


def expand(chain, names):
    """+ every finger bone of that hand (they live in hand.skd, not the body skd)."""
    out = set(chain)
    for side in ("L", "R"):
        if ("Bip01 %s Hand" % side) in chain:
            out |= {n for n in names if n.startswith("Bip01 %s Finger" % side)}
    return out


def build():
    fs = se.GameFS()
    setup = se.tiki_setup(fs, "models/human/german_wehrmact_soldier.tik",
                          {"weapon": "Mauser KAR 98K", "headmodel": "head1", "headskin": "bensonazi"})
    skds, meshes = [], []
    for sm in setup["skelmodels"]:
        data = fs.read(sm)
        if data is None:
            continue
        _v, bones = se.parse_skd(data, sm)
        skds.append((sm, bones))
        _ver, kb, surfs = K.parse_skd(data)
        meshes.append((sm, [b["name"] for b in kb], surfs))
    skel = se.Skeleton(skds)
    aliases = se.tiki_aliases(fs, se.ALIAS_TIKS)
    return fs, setup, skel, aliases, meshes


def pose(fs, skel, aliases, alias, last):
    skc, _ = aliases[alias]
    anim = se.parse_skc(fs.read(skc), skc)
    f = anim["numFrames"] - 1 if last else 0
    tms, _c, _u = skel.evaluate(anim, f)
    return tms


def skin(meshes, tms, collapse=None, cutpos=None):
    tris_out = []
    for sm, bnames, surfs in meshes:
        for s in surfs:
            P, H = [], []
            for ws in s["verts"]:
                p = np.zeros(3); h = 0.0
                for bi, bw, off in ws:
                    n = bnames[bi]
                    if collapse is not None and n in collapse:
                        p += bw * cutpos; h += bw
                    else:
                        M = tms.get(n)
                        if M is None:
                            continue
                        p += bw * (np.append(off, 1.0) @ M)
                P.append(p); H.append(h)
            for t in s["tris"]:
                tris_out.append((np.array([P[i] for i in t]), max(H[i] for i in t), s["name"].lower()))
    return tris_out


def base_col(name):
    if "head" in name: return np.array([196, 152, 124])
    if "hand" in name: return np.array([190, 146, 118])
    if "pants" in name: return np.array([78, 84, 74])
    return np.array([96, 104, 88])


def draw(img, tris, cx, cy, scale, yaw, pitch, label, d):
    cyw, syw = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    R = np.array([[cyw, -syw, 0], [syw, cyw, 0], [0, 0, 1]]) @ np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    light = np.array([0.5, 0.3, 0.8]); light /= np.linalg.norm(light)
    items = []
    for V, h, nm in tris:
        W = V @ R  # x right(ish), y depth, z up
        n = np.cross(W[1] - W[0], W[2] - W[0]); ln = np.linalg.norm(n)
        if ln < 1e-6:
            continue  # degenerate (fully collapsed) triangles vanish - exactly as in the GPU/CPU path
        n /= ln
        shade = 0.35 + 0.65 * abs(float(n @ light))
        c = base_col(nm) * shade
        if h > 0.001:
            c = c * (1 - min(1, h) * 0.85) + np.array([110, 12, 6]) * min(1, h) * 0.85 * shade
        pts = [(cx + p[0] * scale, cy - p[2] * scale) for p in W]
        items.append((W[:, 1].mean(), pts, tuple(int(x) for x in c)))
    for _z, pts, c in sorted(items, key=lambda x: -x[0]):
        d.polygon(pts, fill=c)
    d.text((cx - 80, cy + 18), label, fill=(235, 235, 235))


YAW = float(os.environ.get('YAW', '60'))

def main():
    fs, setup, skel, aliases, meshes = build()
    names = list(skel.bones.keys())
    stand = pose(fs, skel, aliases, "idle", False)
    corpse = pose(fs, skel, aliases, "death_back1", True)
    W, Hh = 1900, 560
    img = Image.new("RGB", (W, Hh), (28, 30, 34)); d = ImageDraw.Draw(img)
    s = 2.4
    panels = []
    panels.append((skin(meshes, stand), "intact (idle f0)"))
    c1 = expand(CHAINS["R_arm_upper"], names) | expand(CHAINS["L_leg_lower"], names)
    # two cuts: collapse each chain to its own joint
    def two_cut(tms, a, b):
        t = dict(tms)
        for ch in (a, b):
            cs = expand(CHAINS[ch], names); root = CHAINS[ch][0]
            cut = tms[root][3].copy()
            for n in cs:
                if n in t:
                    M = np.zeros((4, 3)); M[3] = cut; t[n] = M
        return t
    t2 = two_cut(stand, "R_arm_upper", "L_leg_lower")
    tr = skin(meshes, t2)
    # mark seam triangles red: re-skin with weights to know which verts were collapsed
    def marked(tms_cut, chains):
        cs = set()
        for ch in chains:
            cs |= expand(CHAINS[ch], names)
        out = []
        for (V, _h, nm), (V2, h2, _n) in zip(skin(meshes, tms_cut), skin(meshes, tms_cut, cs, np.zeros(3))):
            out.append((V, h2, nm))
        return out
    panels.append((marked(t2, ["R_arm_upper", "L_leg_lower"]), "R arm @shoulder + L leg @knee"))
    t3 = two_cut(stand, "L_arm_lower", "R_leg_upper")
    panels.append((marked(t3, ["L_arm_lower", "R_leg_upper"]), "L arm @elbow + R leg @hip"))
    # KEEP mode: the severed limb as its own entity (everything else collapsed to the cut joint)
    keep = expand(CHAINS["R_arm_upper"], names)
    root = "Bip01 R UpperArm"; cut = stand[root][3].copy()
    tk = dict(stand)
    for n in names:
        if n not in keep and n in tk:
            M = np.zeros((4, 3)); M[3] = cut; tk[n] = M
    others = set(names) - keep
    kept = [(V, h2, nm) for (V, _h, nm), (_V2, h2, _n) in zip(skin(meshes, tk), skin(meshes, tk, others, np.zeros(3)))]
    panels.append((kept, "severed-limb gib (KEEP mode)"))
    tc = two_cut(corpse, "R_arm_upper", "L_leg_lower")
    panels.append((marked(tc, ["R_arm_upper", "L_leg_lower"]), "corpse death_back1 + same cuts"))
    xs = [150, 450, 750, 1020, 1560]
    for (tris, label), x in zip(panels, xs):
        sc = s if "corpse" not in label else 1.9
        draw(img, tris, x, 470 if "corpse" not in label else 330, sc, YAW if "corpse" not in label else 150,
             8 if "corpse" not in label else 50, label, d)
    d.text((12, 10), "OFFLINE PROTOTYPE - real german_wehrmact_soldier composite (heerprivate+head1+hand skd), engine-exact "
           "skeletor port; limb bones written as matrix 0 + cut-joint origin. Flat shading; red = triangles touching the cut.",
           fill=(220, 220, 220))
    out = os.path.join(HERE, "..", "evidence", "limb_collapse_offline.png"); img.save(out); print(out)


if __name__ == "__main__":
    main()
