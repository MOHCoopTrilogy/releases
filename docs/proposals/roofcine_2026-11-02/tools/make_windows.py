"""make_windows.py <in.bsp> <out.bsp> <out_asset_dir> - map v10: every lit window of m2l3 (shader textures/light/jh_rustwin1lit, 8 panes:
the three in the yard's south wall and the two in the east shed - all five in the ending's one-shot frame - plus three in the west
guard building) becomes real breakable glass: a stock MOHAA func_window (fgame/windows.cpp WindowObject: 250 health, MOD_EXPLOSION x10,
on death the engine sends CGM_MAKE_WINDOW_DEBRIS - the stock glass shards + break sound - and swaps in its target's model).

Per pane, appended (every stock index unchanged, like the other v-builds):
  * model A  = func_window: a copy of the lit pane (same texture, same lightmap coords: looks identical) 0.3 u proud of the wall, plus a
               2 u thick glass brush in front of it (collision for shots / blast traces; the entity sets its own contents).
  * model B  = the broken pane: a dark, smashed window (textures/hzm/window_broken: black room behind, jagged shards in the frame, a
               little soot) - targeted by A, so WindowSetup takes its model and removes the placeholder entity.
  * the world copy of the pane is switched to nodraw (A draws it until it breaks; B after).
The window glow is a self-lit TEXTURE (jh_rustwin1lit), so breaking the pane takes its light with it; the faint bounce it baked into the
wall lightmap around it stays (it is 96 x 144 u and dim - not visible from the yard camera).
Writes <out_asset_dir>/scripts/hzm_window.shader + textures/hzm/window_broken.tga (ship them in the map pak, like hzm_breach.shader)."""
import os, sys, struct, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "v7"))
import bspedit as E
from make_chunks import read_vert, VF

SRC, DST, ASSETS = sys.argv[1], sys.argv[2], sys.argv[3]
WINDOW_SHADERS = ("textures/light/jh_rustwin1lit",)

b = E.Bsp(open(SRC, "rb").read())
sh = b.shaders()
names = [x[0] for x in sh]
shl = b.get("shaders")
nodraw = names.index("textures/common/nodraw")


def add_shader(name, surf, contents):
    if name in names:
        return names.index(name)
    rec = bytearray(140)
    nb = name.encode("latin1"); rec[:len(nb)] = nb
    struct.pack_into("<3i", rec, 64, surf, contents, 0)
    shl.extend(rec); names.append(name)
    return len(names) - 1


SH_BROKEN = add_shader("textures/hzm/window_broken", 0, 0)
SH_GLASS = add_shader("textures/hzm/window_glass", 0x80, 1)        # SURF_NODRAW-style flag bit is irrelevant: the brush has no surface
plL, bl, sl, sfl, dvl, ixl, mdl = (b.get(n) for n in ("planes", "brushes", "brushsides", "surfaces", "drawverts", "drawidx", "models"))
dv0 = bytes(dvl); sf0 = bytes(sfl); ix0 = bytes(ixl)
mods = b.models()
fs0, ns0 = mods[0][6], mods[0][7]


def emit_surface(rec, vo, io):
    struct.pack_into("<4i", rec, 12, len(dvl) // 44, len(vo), len(ixl) // 4, len(io))
    for q in vo:
        dvl.extend(struct.pack(VF, *q))
    ixl.extend(struct.pack("<%di" % len(io), *io)); sfl.extend(rec)


panes = []
for s in range(fs0, fs0 + ns0):
    shn = struct.unpack_from("<i", sf0, s * 108)[0]
    if names[shn] in WINDOW_SHADERS:
        panes.append(s)

ents = bytearray(b.get("ents"))
add = ""
model_no = len(mdl) // 40
for k, s in enumerate(panes, 1):
    rec0 = bytearray(sf0[s * 108:(s + 1) * 108])
    shn, fog, typ, fv, nv, fi, ni = struct.unpack_from("<7i", rec0, 0)
    V = [read_vert(dv0, fv + j) for j in range(nv)]
    I = list(struct.unpack_from("<%di" % ni, ix0, fi * 4))
    nrm = V[0][7:10]
    ax = max(range(3), key=lambda a: abs(nrm[a])); sg = 1 if nrm[ax] > 0 else -1
    mn = [min(v[a] for v in V) for a in range(3)]; mx = [max(v[a] for v in V) for a in range(3)]
    o = [round((mn[a] + mx[a]) / 2, 1) for a in range(3)]
    off = [0.0, 0.0, 0.0]; off[ax] = 0.3 * sg

    # --- model A: the intact pane + a glass brush
    sA = len(sfl) // 108
    vo = [[v[0] + off[0] - o[0], v[1] + off[1] - o[1], v[2] + off[2] - o[2]] + list(v[3:]) for v in V]
    emit_surface(bytearray(rec0), vo, I)
    bA = len(bl) // 12
    face = mn[ax]                                      # the pane plane (axial)
    bmn = list(mn); bmx = list(mx)
    if sg > 0: bmn[ax] = face; bmx[ax] = face + 2
    else: bmn[ax] = face - 2; bmx[ax] = face
    s0 = len(sl) // 12
    for a in range(3):
        for sgn, val in ((-1, bmn[a]), (1, bmx[a])):
            n = [0.0, 0.0, 0.0]; n[a] = float(sgn)
            d = sgn * val - sgn * o[a]                  # local coordinates (entity origin = o)
            pi = len(plL) // 16; plL.extend(struct.pack("<4f", n[0], n[1], n[2], d))
            sl.extend(struct.pack("<3i", pi, SH_GLASS, 0))
    bl.extend(struct.pack("<3i", s0, 6, SH_GLASS))
    lmn = [bmn[a] - o[a] - 1 for a in range(3)]; lmx = [bmx[a] - o[a] + 1 for a in range(3)]
    mdl.extend(struct.pack("<6f4i", *lmn, *lmx, sA, 1, bA, 1))
    mA = model_no; model_no += 1

    # --- model B: the smashed pane (dark room behind, shards in the frame)
    sB = len(sfl) // 108
    u_ax = [a for a in range(3) if a != ax]
    # st: u along the horizontal axis, v down
    hz = u_ax[0] if u_ax[0] != 2 else u_ax[1]
    vb = []
    for v in V:
        su = (v[hz] - mn[hz]) / max(1.0, mx[hz] - mn[hz])
        tv = (mx[2] - v[2]) / max(1.0, mx[2] - mn[2])
        vb.append([v[0] + off[0] * 1.3 - o[0], v[1] + off[1] * 1.3 - o[1], v[2] + off[2] * 1.3 - o[2], su, tv, 0.0, 0.0, nrm[0], nrm[1], nrm[2], 120, 112, 106, 255])
    recB = bytearray(108)
    struct.pack_into("<12i", recB, 0, SH_BROKEN, -1, 1, 0, 4, 0, 6, -1, 0, 0, 0, 0)
    struct.pack_into("<9f", recB, 60, 0, 0, 0, 0, 0, 0, *nrm)
    emit_surface(recB, vb, I)
    mdl.extend(struct.pack("<6f4i", *lmn, *lmx, sB, 1, len(bl) // 12, 0))
    mB = model_no; model_no += 1

    # --- the world copy goes invisible
    struct.pack_into("<i", sfl, s * 108, nodraw)

    tn = "fin_win_%d" % k
    add += ('{\n"classname" "func_window"\n"model" "*%d"\n"origin" "%g %g %g"\n"targetname" "%s"\n"target" "%s_broken"\n"debristype" "0"\n}\n'
            % (mA, o[0], o[1], o[2], tn, tn))
    add += ('{\n"classname" "script_object"\n"model" "*%d"\n"origin" "%g %g %g"\n"targetname" "%s_broken"\n}\n' % (mB, o[0], o[1], o[2], tn))
    print(tn, "pane surface", s, "origin", o, "normal axis", ax, sg, "models", mA, mB)

b.lumps[E.IX["ents"]] = bytearray(bytes(ents).split(b"\0")[0] + add.encode("latin1") + b"\x00")
open(DST, "wb").write(b.tobytes())

# --- assets: shader + the smashed-pane texture (procedural)
from PIL import Image, ImageDraw
import numpy as np
os.makedirs(os.path.join(ASSETS, "scripts"), exist_ok=True)
os.makedirs(os.path.join(ASSETS, "textures", "hzm"), exist_ok=True)
open(os.path.join(ASSETS, "scripts", "hzm_window.shader"), "w", newline="\n").write(
    "// map v10 (docs/proposals/roofcine_2026-11-02/tools/make_windows.py): the smashed state of the breakable windows\n"
    "textures/hzm/window_broken\n{\n\tsurfaceparm nolightmap\n\t{\n\t\tmap textures/hzm/window_broken.tga\n\t\trgbGen vertex\n\t}\n}\n\n"
    "textures/hzm/window_glass\n{\n\tsurfaceparm nodraw\n\tsurfaceparm nolightmap\n\tsurfaceparm trans\n}\n")
W, H = 256, 128
rnd = random.Random(7)
rng = np.random.RandomState(7)
base = (rng.rand(H, W) * 10 + 12)
img = Image.fromarray(np.dstack([base + 4, base + 2, base]).clip(0, 255).astype(np.uint8), "RGB")
d = ImageDraw.Draw(img)
for _ in range(9):                                    # faint glow of a fire deep in the room
    x, y = rnd.randint(30, W - 30), rnd.randint(70, H - 10); r = rnd.randint(10, 26)
    d.ellipse((x - r, y - r // 2, x + r, y + r // 2), fill=(46 + rnd.randint(0, 20), 22, 10))
def shard(edge):
    t = rnd.uniform(0.05, 0.95); w = rnd.uniform(0.05, 0.16); L = rnd.uniform(0.12, 0.45)
    if edge == 0: a, bb, c = (t * W, 0), ((t + w) * W, 0), ((t + w / 2 + rnd.uniform(-.05, .05)) * W, L * H)
    if edge == 1: a, bb, c = (t * W, H), ((t + w) * W, H), ((t + w / 2 + rnd.uniform(-.05, .05)) * W, H - L * H)
    if edge == 2: a, bb, c = (0, t * H), (0, (t + w * 2) * H), (L * W * 0.5, (t + w + rnd.uniform(-.05, .05)) * H)
    if edge == 3: a, bb, c = (W, t * H), (W, (t + w * 2) * H), (W - L * W * 0.5, (t + w + rnd.uniform(-.05, .05)) * H)
    g = rnd.randint(70, 120)
    d.polygon([a, bb, c], fill=(g - 6, g + 4, g + 12))
    d.line([a, c, bb], fill=(g + 50, g + 58, g + 66), width=1)
for e in range(4):
    for _ in range(rnd.randint(3, 6)):
        shard(e)
d.rectangle((0, 0, W - 1, H - 1), outline=(26, 22, 20), width=3)
img.save(os.path.join(ASSETS, "textures", "hzm", "window_broken.tga"))
print("panes", len(panes), "->", DST)
