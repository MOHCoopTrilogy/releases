"""wx_town.py - v1.10.67 the attic window's outside: the town, built and baked in Blender (the sky is real MOHAA skybox art, gen_wx_sky.py).

    blender -b --factory-startup -t 4 --python wx_town.py -- --tex H:/hzm_work/wx/tex --out H:/hzm_work/wx/town --mode preview|bake
            [--sky <sky.jpg> --skyjson <wx_sky.json>] [--cams home,close,ng] [--spp 32] [--res 600]

Metres on the GAME axes (x out of the window, y to the left, z up; game units = metres * 52.5): the bake writes positions the engine
takes as they are.

Authored at REAL scale - neighbours' roofs 10-25 m out, a town sloping away from 40 to 500 m, a church at ~350 m, wooded ridges at
1.5-3 km - then pulled in: the menu's 3D scene clips at 2048 units (the renderer's RDF_NOWORLDMODEL far plane, 39 m), so every
object is scaled uniformly about the HOME camera's eye by d'/d, with d' = d up to 12 m and 12 + 25 (1 - e^-(d-12)/25) beyond
(<= 37 m). From the main menu's camera that is exactly the real view; the other cameras (new game, the close-up) see a stage set that
gets flatter with distance, as the real thing would.
The horizon sits 2.8 deg below the home eye line (the town lies on ground falling away), so from the main menu the pane is mostly sky.

Lighting is one neutral bake (bright sky + a low warm sun from the left, diffuse); the engine multiplies it by the time-of-day tint.
Aerial haze is baked per vertex from the REAL distance. --mode preview renders the menu cameras through a stand-in wall with the pane
hole; --mode bake writes, per textured group (near, town, far, ground): <group>_L.npz (the LIGHT atlas: lighting x the material's wash
colour x (1 - haze), float) + <group>_H.npz (the HAZE atlas) + <group>.npz (triangles: squashed pos, atlas uv, the texture's own uv in
metres / repeat, material index; mats = the material names); the hills group as before (<group>.png, full colour); lights.npz,
marks.json. v1.10.68 (user QA 2026-11-09): the town's surfaces are the GAME's textures in the engine (gen_window_view.py: the vanilla
paths, which the installed HD packs override - nothing re-shipped), the bake only supplies light, wash and haze.
"""
import bpy, sys, os, math, json, random
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d):
    return argv[argv.index(n) + 1] if n in argv else d


TEX = arg("--tex", "H:/hzm_work/wx/tex")
OUT = arg("--out", "H:/hzm_work/wx/town")
MODE = arg("--mode", "preview")
SPP = int(arg("--spp", "32"))
RES = int(arg("--res", "600"))
os.makedirs(OUT, exist_ok=True)
rnd = random.Random(1944)
FP = []               # every house's footprint (x0, x1, y0, y1, centre): checked for overlaps before the build (QA "inside each other")
LRND = random.Random(77)        # the extra lit windows (separate, so the town layout never moves with it)

WALL_X = 358.05 / 52.5
WIN = dict(y0=209.5 / 52.5, y1=242.0 / 52.5, z0=80.85 / 52.5, z1=113.4 / 52.5)
WC = Vector((WALL_X, (WIN["y0"] + WIN["y1"]) / 2, (WIN["z0"] + WIN["z1"]) / 2))
CAMS = {
    "home": ((-36.7, 21.0, 102.4), 7.01, 0.0, 55.11),
    "close": ((268.0, 214.0, 96.0), -3.0, 8.0, 50.0),
    "ng": ((157.5, 68.1, 74.7), 0.0, 0.0, 46.0),
    "homezoom": ((-36.7, 21.0, 102.4), 1.6, 27.4, 8.0),        # QA only: the home camera's own pane, magnified
}
EYE = Vector(CAMS["home"][0]) / 52.5
HZ_DROP = math.radians(1.3)          # the home pane spans -2.77..+1.42 deg: town in its lower third, sky above
KNEE, SPAN = 12.0, 25.0


def horizon_z(x):
    return EYE.z - math.tan(HZ_DROP) * (x - EYE.x)


EPS = 5e-4          # a floor under the squash's slope: depth along a sight line never collapses (far walls / roofs / rows z-fought
                    # when 1000 m crushed to under a millimetre); 3.1 km still lands at 38.5 m, inside the 39 m far plane


def squash(d):
    return d if d <= KNEE else KNEE + SPAN * (1 - math.exp(-(d - KNEE) / SPAN)) + EPS * (d - KNEE)


SC = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

# ---------------------------------------------------------------- materials (all on the 'tex' UV map, metres / repeat baked into the UVs)
IMG = {}


def img(name):
    if name not in IMG:
        IMG[name] = bpy.data.images.load(os.path.join(TEX, name))
    return IMG[name]


HAZE = (0.60, 0.68, 0.80)


def finish(nt, col, rough=0.95):
    """colour -> aerial haze (vertex attribute 'hz', from the real distance) -> the BSDF"""
    N, L = nt.nodes, nt.links
    bs = N["Principled BSDF"]
    bs.inputs["Roughness"].default_value = rough
    at = N.new("ShaderNodeAttribute"); at.attribute_name = "hz"; at.attribute_type = 'GEOMETRY'
    mx = N.new("ShaderNodeMix"); mx.data_type = 'RGBA'
    L.new(at.outputs["Fac"], mx.inputs[0]); L.new(col, mx.inputs[6]); mx.inputs[7].default_value = (*HAZE, 1)
    L.new(mx.outputs[2], bs.inputs["Base Color"])


def mat_tex(name, tex, tint=(1, 1, 1)):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    uv = N.new("ShaderNodeUVMap"); uv.uv_map = "tex"
    ti = N.new("ShaderNodeTexImage"); ti.image = img(tex)
    L.new(uv.outputs["UV"], ti.inputs["Vector"])
    mx = N.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
    L.new(ti.outputs["Color"], mx.inputs[6]); mx.inputs[7].default_value = (*tint, 1)
    finish(nt, mx.outputs[2])
    return m


def mat_col(name, c):
    """ridges: a patchwork of fields and dark woods (world-space noise, coarse - at 1.5-3 km nothing finer reads)"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    gm = nt.nodes.new("ShaderNodeNewGeometry")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.9; nz.inputs["Detail"].default_value = 3.0
    nt.links.new(gm.outputs["Position"], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.interpolation = 'CONSTANT'
    cr.color_ramp.elements[0].color = (0.07, 0.10, 0.06, 1)            # woods
    cr.color_ramp.elements[1].position = 0.52
    cr.color_ramp.elements[1].color = tuple(c) + (1,)                   # fields
    e = cr.color_ramp.elements.new(0.70); e.color = tuple(x * 1.35 for x in c) + (1,)
    nt.links.new(nz.outputs["Fac"], cr.inputs["Fac"])
    finish(nt, cr.outputs["Color"], 1.0)
    return m


# The town's surfaces are drawn in the engine with the game's own textures (gen_window_view.py) times a baked LIGHT atlas plus a HAZE
# atlas. Here a material is only its wash colour (several plaster colours share one texture); the bake supplies light and shadow.
# TOWNTEX: engine texture (the vanilla path, overridden by the HD packs where they have it), metres per tile, wash colour.
TOWNTEX = {
    "plaster":   ("textures/general_structure/plasterwall3.jpg", 3.0, (0.97, 0.94, 0.88)),
    "plaster_o": ("textures/general_structure/plasterwall3.jpg", 3.0, (1.00, 0.84, 0.62)),
    "plaster_g": ("textures/general_structure/plasterwall3.jpg", 3.0, (0.86, 0.89, 0.80)),
    "plaster_b": ("textures/general_structure/plasterwall3.jpg", 3.0, (0.98, 0.80, 0.74)),
    "brick":     ("textures/general_structure/brickwall_set3.jpg", 2.4, (1.0, 1.0, 1.0)),
    "ochre":     ("textures/it_extwall/it_e_wall_brickochre01a.jpg", 2.6, (1.0, 1.0, 1.0)),
    "stone":     ("textures/general_structure/stonebricks1.jpg", 2.0, (1.0, 1.0, 1.0)),
    "chimney":   ("textures/general_structure/jh_brick4.jpg", 1.5, (0.95, 0.92, 0.90)),
    "tile":      ("textures/it_extwall/IT_e_rooftile01a.jpg", 2.4, (1.0, 0.95, 0.92)),
    "tile2":     ("textures/general_structure/jh_tileroof1.jpg", 2.0, (1.0, 1.0, 1.0)),
    "tile3":     ("textures/it_extwall/IT_e_rooftile01a.jpg", 2.4, (0.78, 0.68, 0.64)),
    "slate":     ("textures/general_structure/rotshingle1.jpg", 2.6, (0.92, 0.94, 1.0)),
    "copper":    ("textures/it_extwall/it_e_3-4stonebase.jpg", 2.0, (0.55, 0.80, 0.70)),
    "street":    ("textures/it_extwall/it_e_3-4cobblestone.jpg", 1.8, (1.0, 0.96, 0.9)),
    "yard":      ("textures/central_europe/earth_road_gen1dn.jpg", 8.0, (0.95, 0.95, 0.90)),
    "field":     ("textures/misc_outside/steve_grass512_set2.jpg", 12.0, (0.92, 1.0, 0.85)),
    "meadow":    ("textures/misc_outside/steve_grass512_set2.jpg", 14.0, (0.92, 1.0, 0.85)),
    "pasture":   ("textures/misc_outside/nu_grass_set1.jpg", 14.0, (0.85, 0.95, 0.8)),
    "wheat":     ("textures/misc_outside/bocagegrass_1.jpg", 14.0, (1.0, 0.92, 0.55)),
    "plough":    ("textures/misc_outside/bocagegrass_furrough.jpg", 14.0, (0.95, 0.85, 0.72)),
    "wood":      ("textures/mohtest/foliage1.jpg", 6.0, (0.85, 1.0, 0.85)),
    "window":    ("textures/TAHolland/hollwindow_f1.jpg", 1.0, (1.0, 1.0, 1.0)),
    "shopwin":   ("textures/TAHolland/hollwindow_f1.jpg", 1.0, (0.9, 0.9, 0.9)),
    "door1":     ("textures/general_structure/euro_door1.jpg", 1.0, (1.0, 1.0, 1.0)),
    "door2":     ("textures/general_structure/door_offwhite2.jpg", 1.0, (1.0, 1.0, 1.0)),
    "shutter":   ("textures/central_europe/shutter_set2.jpg", 1.0, (1.0, 1.0, 1.0)),
    "awning":    ("textures/central_europe/awning_french_overhang.tga", 1.0, (1.0, 1.0, 1.0)),
    "trim":      ("textures/mohcommon/trim_set1a.jpg", 1.0, (0.95, 0.93, 0.9)),
    "drain":     ("textures/central_europe/spouting_vertical_drain.jpg", 1.0, (0.8, 0.8, 0.8)),
    "pave":      ("textures/mohtest/sidewalk2.jpg", 1.0, (1.0, 1.0, 1.0)),
}
M, REP = {}, {}


def mat_wash(name, tint):
    """base colour = wash x (1 - haze) (the LIGHT bake's colour pass); emission = HAZE x haze (the HAZE bake), strength toggled"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, Lk = nt.nodes, nt.links
    bs = N["Principled BSDF"]
    bs.inputs["Roughness"].default_value = 0.95
    at = N.new("ShaderNodeAttribute"); at.attribute_name = "hz"; at.attribute_type = 'GEOMETRY'
    mx = N.new("ShaderNodeMix"); mx.data_type = 'RGBA'
    Lk.new(at.outputs["Fac"], mx.inputs[0]); mx.inputs[6].default_value = (*tint, 1); mx.inputs[7].default_value = (0, 0, 0, 1)
    Lk.new(mx.outputs[2], bs.inputs["Base Color"])
    me = N.new("ShaderNodeMix"); me.data_type = 'RGBA'
    Lk.new(at.outputs["Fac"], me.inputs[0]); me.inputs[6].default_value = (0, 0, 0, 1); me.inputs[7].default_value = (*HAZE, 1)
    Lk.new(me.outputs[2], bs.inputs["Emission Color"])
    bs.inputs["Emission Strength"].default_value = 0.0
    return m


for k, (t, r, c) in TOWNTEX.items():
    M[k] = mat_wash(k, c)
    REP[k] = r
for nm, c in (("hill_near", (0.20, 0.25, 0.15)), ("hill_far", (0.17, 0.22, 0.17)), ("forest", (0.09, 0.13, 0.08))):
    M[nm] = mat_col(nm, c)
    REP[nm] = 1.0

# ---------------------------------------------------------------- geometry
GROUPS = {}
LIGHTS = []
MARKS = []          # (kind, point, size): chimney tops (smoke) and tree cards, placed in the engine


def haze_of(p):
    d = (Vector(p) - WC).length
    return min(0.8, 0.85 * (1 - math.exp(-max(0.0, d - 60.0) / 1450.0)))


class Mesh:
    def __init__(self):
        self.v, self.f, self.uv, self.mi, self.mats, self.hz = [], [], [], [], [], []
        self.vs = []          # the squashed positions (what the engine draws); self.v stays real (what the bake lights)
        self.uvoff = (0.0, 0.0)   # added to the texture uv (metres) of every quad: each house its own patch of the texture
        self.step = 0.0       # > 0: quads / triangles are tessellated to this edge length (set per house from its distance)
        self.smooth = False   # smooth-shaded in the bake (the terrain and the woods: no facets)
        self.wf = []          # the window faces (pushed toward the eye after the squash: never lose the depth test to their wall)

    def mat(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def quad(self, pts, m, uvs=None):
        """pts real metres; uvs in metres (divided by the material's repeat here) or None = planar from the first edge"""
        pts = [Vector(p) for p in pts]
        if uvs is None:
            e1 = (pts[1] - pts[0])
            ln = e1.length or 1.0
            e1 = e1 / ln
            nrm = e1.cross(pts[-1] - pts[0]).normalized()
            e2 = nrm.cross(e1).normalized()
            if e2.z < 0:
                e2 = -e2
            uvs = [((p - pts[0]).dot(e1), (p - pts[0]).dot(e2) + pts[0].z) for p in pts]
        if self.step and len(pts) in (3, 4):
            self._tess(pts, m, uvs)
        else:
            self._face(pts, m, uvs)

    def _face(self, pts, m, uvs):
        r = REP.get(m, 1.0)
        i = len(self.v)
        self.v.extend(pts)
        self.vs.extend(p.copy() for p in pts)
        self.hz.extend(haze_of(p) for p in pts)
        self.f.append(tuple(range(i, i + len(pts))))
        ou, ov = self.uvoff
        self.uv.append([((u + ou) / r, (v + ov) / r) for u, v in uvs])
        self.mi.append(self.mat(m))

    def _grid(self, P_, m, faces):
        """shared vertices P_ (real metres) + faces as (index tuple, uv list) - one welded sheet, so the light atlas unwraps it as ONE
        island (unwelded pieces each became an island: ~1200 specks with mip bleeding and noise between them, QA 2026-11-09)"""
        i0 = len(self.v)
        self.v.extend(P_)
        self.vs.extend(p.copy() for p in P_)
        self.hz.extend(haze_of(p) for p in P_)
        r = REP.get(m, 1.0)
        ou, ov = self.uvoff
        mi = self.mat(m)
        for idx, uvs in faces:
            self.f.append(tuple(i0 + k for k in idx))
            self.uv.append([((u + ou) / r, (v + ov) / r) for u, v in uvs])
            self.mi.append(mi)

    def _tess(self, pts, m, uvs):
        """split a quad / triangle into pieces no longer than self.step: the squash bends a plane, and a big flat face is a chord
        that cuts behind its windows, chimneys and banners (QA 2026-11-09: windows 12 cm behind their wall's chord at 50 m)"""
        st = self.step
        U_ = [Vector((u, v, 0)) for u, v in uvs]
        if len(pts) == 4:
            nu = max(1, min(16, math.ceil(max((pts[1] - pts[0]).length, (pts[2] - pts[3]).length) / st)))
            nv = max(1, min(16, math.ceil(max((pts[3] - pts[0]).length, (pts[2] - pts[1]).length) / st)))

            def bl(c, a, b):
                return c[0] * (1 - a) * (1 - b) + c[1] * a * (1 - b) + c[2] * a * b + c[3] * (1 - a) * b
            P_ = [bl(pts, i_ / nu, j_ / nv) for i_ in range(nu + 1) for j_ in range(nv + 1)]
            T_ = [tuple(bl(U_, i_ / nu, j_ / nv))[:2] for i_ in range(nu + 1) for j_ in range(nv + 1)]
            K = lambda i_, j_: i_ * (nv + 1) + j_
            faces = []
            for i_ in range(nu):
                for j_ in range(nv):
                    idx = (K(i_, j_), K(i_ + 1, j_), K(i_ + 1, j_ + 1), K(i_, j_ + 1))
                    faces.append((idx, [T_[k] for k in idx]))
        else:
            n = max(1, min(16, math.ceil(max((pts[1] - pts[0]).length, (pts[2] - pts[0]).length, (pts[2] - pts[1]).length) / st)))

            def bt(c, a, b):
                return c[0] * (1 - a - b) + c[1] * a + c[2] * b
            keys = [(i_, j_) for i_ in range(n + 1) for j_ in range(n + 1 - i_)]
            K = {k: q for q, k in enumerate(keys)}
            P_ = [bt(pts, i_ / n, j_ / n) for i_, j_ in keys]
            T_ = [tuple(bt(U_, i_ / n, j_ / n))[:2] for i_, j_ in keys]
            faces = []
            for i_ in range(n):
                for j_ in range(n - i_):
                    idx = (K[(i_, j_)], K[(i_ + 1, j_)], K[(i_, j_ + 1)])
                    faces.append((idx, [T_[k] for k in idx]))
                    if j_ < n - i_ - 1:
                        idx = (K[(i_ + 1, j_)], K[(i_ + 1, j_ + 1)], K[(i_, j_ + 1)])
                        faces.append((idx, [T_[k] for k in idx]))
        self._grid(P_, m, faces)

    def squash_from(self, i0, anchor, l0=None, m0=None):
        """pull vertices i0.. (and lit-window quads l0.., markers m0..) towards the home eye by squash(d)/d of the anchor"""
        d = (Vector(anchor) - EYE).length
        f = squash(d) / d
        for i in range(i0, len(self.v)):
            self.vs[i] = EYE + (self.v[i] - EYE) * f
        if l0 is not None:
            for k in range(l0, len(LIGHTS)):
                LIGHTS[k] = [tuple(EYE + (Vector(p) - EYE) * f) for p in LIGHTS[k]]
        if m0 is not None:
            for k in range(m0, len(MARKS)):
                kind, pt, sz = MARKS[k]
                MARKS[k] = (kind, tuple(EYE + (Vector(pt) - EYE) * f), sz * f)

    def orient(self, f0, centre=None, up=False):
        """faces f0.. made to face out of `centre` (or up): the bake shoots its rays along the normal, an inward face bakes black"""
        for fi in range(f0, len(self.f)):
            idx = self.f[fi]
            p = [self.v[i] for i in idx]
            n = (p[1] - p[0]).cross(p[2] - p[0])
            c = sum(p, Vector()) / len(p)
            want = Vector((0, 0, 1)) if up else (c - Vector(centre))
            if n.dot(want) < 0:
                self.f[fi] = tuple(reversed(idx))
                self.uv[fi] = list(reversed(self.uv[fi]))

    def squash_each(self, i0):
        """every vertex by its own distance (so shared walls and sheets stay whole); then the window faces 3 cm toward the eye"""
        for i in range(i0, len(self.v)):
            d = (self.v[i] - EYE).length
            self.vs[i] = EYE + (self.v[i] - EYE) * (squash(d) / d)
        for fi in self.wf:
            for i in self.f[fi]:
                self.vs[i] = self.vs[i] + (EYE - self.vs[i]).normalized() * 0.04

    def build(self, name, group):
        me = bpy.data.meshes.new(name)
        # bake: the REAL town (lighting and shadows at true scale - squashed slivers baked black); preview: what the engine draws
        me.from_pydata([tuple(p) for p in (self.v if MODE == "bake" else self.vs)], [], self.f)
        sq = me.attributes.new("sq", 'FLOAT_VECTOR', 'POINT')
        sq.data.foreach_set("vector", [c for p in self.vs for c in p])
        uvl = me.uv_layers.new(name="tex")
        for poly, uvs in zip(me.polygons, self.uv):
            for li, uv in zip(poly.loop_indices, uvs):
                uvl.data[li].uv = uv
        at = me.attributes.new("hz", 'FLOAT', 'POINT')
        at.data.foreach_set("value", self.hz)
        for m in self.mats:
            me.materials.append(M[m])
        for poly, mi in zip(me.polygons, self.mi):
            poly.material_index = mi
            poly.use_smooth = self.smooth
        me.update()
        o = bpy.data.objects.new(name, me)
        SC.collection.objects.link(o)
        GROUPS.setdefault(group, []).append(o)
        return o


def sheet(mesh, c, m, nu, nv, ulen, vlen):
    """a bilinear sheet over corners c = (p00, p10, p11, p01), nu x nv quads (so a per-vertex squash keeps it on its curve)"""
    c = [Vector(x) for x in c]
    f0 = len(mesh.f)

    def at(u, v):
        return c[0] * (1 - u) * (1 - v) + c[1] * u * (1 - v) + c[2] * u * v + c[3] * (1 - u) * v
    for i in range(nu):
        for j in range(nv):
            u0, u1, v0, v1 = i / nu, (i + 1) / nu, j / nv, (j + 1) / nv
            mesh.quad([at(u0, v0), at(u1, v0), at(u1, v1), at(u0, v1)], m,
                      [(u0 * ulen, v0 * vlen), (u1 * ulen, v0 * vlen), (u1 * ulen, v1 * vlen), (u0 * ulen, v1 * vlen)])
    mesh.orient(f0, up=True)


def box_sides(mesh, P, corners, z0, z1, m):
    for a, b in zip(corners, corners[1:] + corners[:1]):
        L = (Vector(b) - Vector(a)).length
        mesh.quad([P(a[0], a[1], z0), P(b[0], b[1], z0), P(b[0], b[1], z1), P(a[0], a[1], z1)], m,
                  [(0, z0), (L, z0), (L, z1), (0, z1)])


def house(mesh, c, w, d, h, roof, rm, wm, rot=0.0, ridge_y=True, chims_at=(), wins=True, lit=0.4, dormers=0, smoke=False,
          oy=(0.3, 0.3), win_cols=None, banner=None, plinth=1.0, ww=0.62, front=False, shop=False, detail=True):
    """a house at ground point c (real metres; c.z = its floor level): w along y, d along x, wall height h, roof rise `roof`;
    ridge_y = the ridge runs along y. chims_at: chimney y offsets (local; +-w/2 = on a party wall, straddling both roofs).
    oy: the roof's overhang past the local -y / +y walls (0 on a party wall: neighbouring roofs meet, never overlap).
    plinth: how far the stone socle runs down below the floor level (to the lowest ground round the house, plus a margin).
    wins: True = window geometry on the long wall that faces the home eye (and lit ones among them); "lights" = lit panes only (the
    far rows, where a window is a pixel); False = none. banner = layout: 0 one banner centred between the two middle columns, 1 a
    pair between the outer columns - from just under the eaves down to above the ground-floor windows, flush on the wall."""
    cx, cy, cz = c
    Rm = Matrix.Rotation(rot, 3, 'Z')
    mesh.uvoff = (rnd.uniform(0, 30), rnd.uniform(0, 30))          # each house its own patch of the texture (no clones)
    mesh.step = max(2.5, 0.035 * (Vector((cx, cy, cz)) - EYE).length)  # one step for the whole house: shared edges split alike

    def P(x, y, z):
        v = Rm @ Vector((x, y, z))
        return Vector((cx + v.x, cy + v.y, cz + v.z))
    hw, hd = w / 2, d / 2
    _cs = [P(sx * hd, sy * hw, 0) for sx in (-1, 1) for sy in (-1, 1)]
    FP.append((min(v.x for v in _cs), max(v.x for v in _cs), min(v.y for v in _cs), max(v.y for v in _cs), (round(cx, 1), round(cy, 1))))
    # the facing frame: the long wall at local x = -hd in Q faces the home eye (Q = P turned half round when the +x wall does)
    nmx = Rm @ Vector((-1.0, 0.0, 0.0))
    sf = 1.0 if nmx.dot(EYE - Vector((cx, cy, cz + h / 2))) > 0 else -1.0

    def Q(x, y, z):
        return P(sf * x, sf * y, z)
    nface = Rm @ Vector((-sf, 0.0, 0.0))
    f0 = len(mesh.f)
    corners = [(-hd, -hw), (-hd, hw), (hd, hw), (hd, -hw)]
    SOC = 0.6
    box_sides(mesh, P, corners, SOC, h, wm)
    box_sides(mesh, P, corners, -plinth, SOC, "stone")              # the socle, down into the ground wherever it falls away
    o = 0.35
    oy0, oy1 = oy
    if ridge_y:
        for (ya, sg) in ((hw, 1), (-hw, -1)):
            mesh.quad([P(-hd * sg, ya, h), P(hd * sg, ya, h), P(0, ya, h + roof - 0.08)], wm, [(0, h), (d, h), (d / 2, h + roof - 0.08)])   # apex tucked under the ridge
        sl = math.hypot(hd + o, roof * (hd + o) / hd)
        zo = h - roof * o / hd
        ylo, yhi = -hw - oy0, hw + oy1
        for sgn in (-1, 1):
            a, b = P(sgn * (hd + o), ylo, zo), P(sgn * (hd + o), yhi, zo)
            c2, d2 = P(0, yhi, h + roof), P(0, ylo, h + roof)
            u1 = yhi - ylo
            mesh.quad([a, b, c2, d2], rm, [(ylo, 0), (yhi, 0), (yhi, sl), (ylo, sl)])
    else:
        for (xa, sg) in ((-hd, 1), (hd, -1)):
            mesh.quad([P(xa, -hw * sg, h), P(xa, hw * sg, h), P(xa, 0, h + roof - 0.08)], wm, [(0, h), (w, h), (w / 2, h + roof - 0.08)])
        sl = math.hypot(hw + o, roof * (hw + o) / hw)
        zo = h - roof * o / hw
        for sgn in (-1, 1):
            a, b = P(-hd - o, sgn * (hw + o), zo), P(hd + o, sgn * (hw + o), zo)
            c2, d2 = P(hd + o, 0, h + roof), P(-hd - o, 0, h + roof)
            mesh.quad([a, b, c2, d2], rm, [(-hd - o, 0), (hd + o, 0), (hd + o, sl), (-hd - o, sl)])
    mesh.orient(f0, P(0, 0, h * 0.5))
    ncol = win_cols or max(1, int(w / 2.6))
    cols = [(-hw + w * (k + 0.5) / ncol) for k in range(ncol)]

    def window(p_bl, p_br, p_tr, p_tl, lit_p):
        """a window quad (viewer's bottom-left, bottom-right, top-right, top-left), the game's window texture 0..1 on it"""
        mesh.uvoff = (0.0, 0.0)
        if wins is True:
            st_, mesh.step = mesh.step, 0.0
            mesh.quad([p_bl, p_br, p_tr, p_tl], "window", [(0, 0), (1, 0), (1, 1), (0, 1)])
            mesh.step = st_
            mesh.wf.append(len(mesh.f) - 1)
        if LRND.random() < lit_p:
            LIGHTS.append([tuple(x) for x in (p_bl, p_br, p_tr, p_tl)])
    # dormers on the eye-facing slope, centred in the bays (ridge along y only)
    nd0 = len(LIGHTS)
    if dormers and ridge_y:
        for k in range(dormers):
            yy = -hw + w * (k + 0.5) / dormers
            dw, dh = 0.85, 1.7
            xf = -hd * 0.62
            zf = h + roof * (1 - abs(xf) / hd) - 0.25
            xb = -hd * 0.12
            fd = len(mesh.f)
            ya2, yb2 = yy - dw, yy + dw
            mesh.quad([Q(xf, ya2, zf), Q(xf, yb2, zf), Q(xf, yb2, zf + dh), Q(xf, ya2, zf + dh)], wm, [(0, 0), (1.7, 0), (1.7, dh), (0, dh)])
            mesh.quad([Q(xf, ya2, zf + dh), Q(xf, yb2, zf + dh), Q(xf, yy, zf + dh + 0.9)], wm, [(0, 0), (1.7, 0), (0.85, 0.9)])
            for yside in (ya2, yb2):
                mesh.quad([Q(xf, yside, zf), Q(xb, yside, zf + 1.2), Q(xb, yside, zf + dh + 0.3), Q(xf, yside, zf + dh)], wm,
                          [(0, 0), (2, 0), (2, dh), (0, dh)])
            for ys, ye in ((ya2 - 0.15, yy), (yb2 + 0.15, yy)):
                mesh.quad([Q(xf - 0.2, ys, zf + dh - 0.1), Q(xb, ys, zf + dh + 0.2), Q(xb, ye, zf + dh + 1.0), Q(xf - 0.2, ye, zf + dh + 0.9)], rm,
                          [(0, 0), (2, 0), (2, 1.1), (0, 1.1)])
            mesh.orient(fd, Q(xb + 0.5, yy, zf + 0.6))
            e = xf - 0.04
            # viewer's left is local +y in the facing frame (the eye looks along +x in Q)
            window(Q(e, yy + 0.5, zf + 0.25), Q(e, yy - 0.5, zf + 0.25), Q(e, yy - 0.5, zf + 1.45), Q(e, yy + 0.5, zf + 1.45), lit + 0.2)
    # chimneys: on the ridge at the given y (+-w/2 = a party wall); the stack starts 4.5 m down inside the houses, so it never stands on
    # air over a lower neighbour's roof
    for k, cyy in enumerate(chims_at):
        mesh.uvoff = (rnd.uniform(0, 30), rnd.uniform(0, 30))
        fc = len(mesh.f)
        zt = h + roof + rnd.uniform(0.9, 1.5)
        q = 0.4
        box_sides(mesh, P, [(-q, cyy - q), (-q, cyy + q), (q, cyy + q), (q, cyy - q)], h - 4.5, zt, "chimney")
        mesh.quad([P(-q, cyy - q, zt), P(-q, cyy + q, zt), P(q, cyy + q, zt), P(q, cyy - q, zt)], "chimney",
                  [(0, 0), (0.8, 0), (0.8, 0.8), (0, 0.8)])
        mesh.orient(fc, P(0, cyy, h))
        if smoke and k == 0:
            MARKS.append(["smoke", tuple(P(0, cyy, zt + 0.05)), 1.0, None])
    def flat(m, y0, y1, z0, z1, e, uvs=None, lit_p=None):
        """a flat detail on the eye-facing wall (viewer's left = local +y in Q), `e` proud of it; pushed toward the eye like a window
        after the squash so it never loses the depth test to its wall"""
        q4 = (Q(-hd - e, y1, z0), Q(-hd - e, y0, z0), Q(-hd - e, y0, z1), Q(-hd - e, y1, z1))
        if wins is True:
            st_, mesh.step = mesh.step, 0.0
            mesh.quad(list(q4), m, uvs or [(0, 0), (1, 0), (1, 1), (0, 1)])
            mesh.step = st_
            mesh.wf.append(len(mesh.f) - 1)
        if lit_p is not None and LRND.random() < lit_p:
            LIGHTS.append([tuple(x) for x in q4])
        return q4

    if wins:
        floors = int((h - 0.6) / 3.0)
        l0 = len(LIGHTS)
        cand = []
        # the house's own style (consistent on the house, varied along the row): window width / height, shutters, door side
        wh_top = rnd.choice((1.7, 1.85, 2.0))
        shutters = detail and banner is None and rnd.random() < 0.4 and (w / ncol) > 4.4 * ww
        door_col = rnd.randrange(ncol) if (detail and ncol > 1) else -1
        for fl in range(floors):
            for ci, py in enumerate(cols):
                z0 = 1.2 + fl * 3.0
                wh = min(wh_top if fl else 2.0, h - 0.6 - z0)
                if wh < 1.2:
                    continue
                if fl == 0 and detail and wins is True:
                    if shop and ci in (0, 1) and ncol >= 2:
                        if ci == 0:          # one shop window over the first two bays, an awning over it, its door in the next bay
                            y0, y1 = cols[0] - ww, cols[1] + ww
                            q4 = flat("shopwin", y0, y1, 0.75, 2.75, 0.04, [(0, 0), (2, 0), (2, 1), (0, 1)], lit)
                            cand.append(q4)
                            # the awning: from 3.05 on the wall, 0.9 m out and 0.45 down, the stock scalloped canvas
                            st_, mesh.step = mesh.step, 0.0
                            mesh.quad([Q(-hd - 0.95, y1 + 0.15, 2.6), Q(-hd - 0.95, y0 - 0.15, 2.6), Q(-hd - 0.02, y0 - 0.15, 3.05), Q(-hd - 0.02, y1 + 0.15, 3.05)],
                                      "awning", [(0, 0), (2, 0), (2, 1), (0, 1)])
                            mesh.step = st_
                        continue
                    if ci == door_col or (shop and ci == 2):
                        dm = "door2" if (shop or rnd.random() < 0.5) else "door1"
                        if not front:
                            dm = "door1"
                        flat(dm, py - 0.55, py + 0.55, 0.62, 2.75, 0.04)
                        continue
                e = -hd - 0.04
                q4 = (Q(e, py + ww, z0), Q(e, py - ww, z0), Q(e, py - ww, z0 + wh), Q(e, py + ww, z0 + wh))
                cand.append(q4)
                window(*q4, lit)
                if shutters and fl > 0:
                    sw_ = ww * 0.9
                    flat("shutter", py + ww, py + ww + sw_, z0, z0 + wh, 0.045, [(0, 0), (0.5, 0), (0.5, 1), (0, 1)])
                    flat("shutter", py - ww - sw_, py - ww, z0, z0 + wh, 0.045, [(0.5, 0), (1, 0), (1, 1), (0.5, 1)])
        if lit >= 0.4 and cand and len(LIGHTS) == l0:
            LIGHTS.append([tuple(x) for x in LRND.choice(cand)])
        if detail and wins is True and floors >= 2:
            # a stone string course over the ground floor and a cornice under the eaves, wall to wall; a drainpipe at one party wall
            flat("trim", -hw, hw, 3.3, 3.48, 0.03, [(0, 0.55), (w / 2.0, 0.55), (w / 2.0, 0.75), (0, 0.75)])
            flat("trim", -hw, hw, h - 0.32, h - 0.02, 0.03, [(0, 0.1), (w / 2.0, 0.1), (w / 2.0, 0.45), (0, 0.45)])
            yp = hw - 0.16 if rnd.random() < 0.5 else -hw + 0.04
            flat("drain", yp, yp + 0.12, 0.62, h - 0.32, 0.05, [(0, 0), (1, 0), (1, (h - 1) / 2.0), (0, (h - 1) / 2.0)])
        if banner is not None:
            L = h - 0.12 - 3.6 - 0.3                         # from under the cornice to above the string course
            spots = [0.0] if (banner == 0 and ncol % 2 == 0) else [-hw + w / ncol, hw - w / ncol]
            for by in spots:
                MARKS.append(["banner:nazibanner1:%.2f" % L, tuple(Q(-hd, by, h - 0.36)), 1.0, tuple(nface)])
    mesh.uvoff = (0.0, 0.0)
    mesh.step = 0.0


# ---- near: the attic house's neighbours (real scale, under the sill), on their own flat yard
near = Mesh()
GN = WC.z - 17.5                        # their ridges stay ~5 m under the sill (coordinator: the near roof dominated the close view)
house(near, (WALL_X + 10.0, WC.y + 8.0, GN), 11.0, 8.0, 6.4, 3.6, "tile", "plaster", chims_at=[2.0], lit=0.5)
# (the second neighbour stood where the oak grows now: its crown must stay out of the room - x > 514 right of y -21)
# (it was 9 m wide at y -0.5: 1.5 m of it inside the first neighbour - QA 2026-11-09 "buildings inside each other"; now an alley
# of 0.8 m between them and its right wall clear of the oak's trunk)
house(near, (WALL_X + 12.0, WC.y - 1.65, GN), 6.7, 8.0, 6.4, 3.8, "tile2", "plaster_g", lit=0.5)
house(near, (WALL_X + 21.0, WC.y + 17.0, GN), 10.0, 7.0, 6.6, 3.6, "tile2", "ochre", ridge_y=False, lit=0.5)
house(near, (WALL_X + 23.0, WC.y + 3.0, GN), 12.0, 8.0, 6.2, 4.0, "tile", "plaster_o", chims_at=[-1.5], lit=0.5)
house(near, (WALL_X + 24.0, WC.y - 11.0, GN), 10.0, 8.0, 7.0, 3.6, "slate", "brick", lit=0.5)
gnd_near = Mesh()
f0 = len(gnd_near.f)
for ix in range(8):
    for iy in range(14):
        x0_, x1_ = WALL_X + 0.3 + (EYE.x + 38.0 - WALL_X - 0.3) * ix / 8, WALL_X + 0.3 + (EYE.x + 38.0 - WALL_X - 0.3) * (ix + 1) / 8
        y0_, y1_ = WC.y - 40 + 90.0 * iy / 14, WC.y - 40 + 90.0 * (iy + 1) / 14
        gnd_near.quad([(x0_, y0_, GN), (x1_, y0_, GN), (x1_, y1_, GN), (x0_, y1_, GN)], "yard", [(x0_, y0_), (x1_, y0_), (x1_, y1_), (x0_, y1_)])
gnd_near.orient(f0, up=True)

# ==== THE TOWN (v1.10.68 rework; user QA 2026-11-09: "floating buildings", "buildings inside each other", janky banners, "is that
# supposed to be a beach?"). Laid out like a small French town on a hillside, not scattered:
#   * streets run across the view (along y) at growing distances; between two streets a block of two back-to-back terraces with
#     yards between them (one row where the block is shallow); cross streets cut the terraces every 45-90 m (gable ends line up);
#   * a terrace is a run of houses sharing party walls - each exactly as wide as its plot: no gaps, no overlaps; ridges along the
#     street, chimneys on the party walls; one roof palette and one storey count (+-1) per row; every house its own texture patch;
#   * the ground steps down the hill BLOCK by block: each street is level across, the houses of a row stand on their street's
#     level, the yards behind ramp down to the next street; a stone socle runs from the floor down below the lowest ground round
#     the house, so on a slope it shows as a plinth and nothing ever stands on air;
#   * everything (houses, ground, windows, lights, smoke, banners) is squashed toward the eye per VERTEX at the end, so shared walls
#     stay shared and nothing parts at a seam;
#   * far rows (> 420 m) are the roof mass: simpler, wider, lit panes but no window geometry, up to 1150 m; then fields up to the
#     hills (their foot below the ground's edge) - no bare band at the horizon (the pale "beach").


def G(x, y):
    """the hillside's nominal height (real metres) at (x, y): a typical roof line sits a little under the home pane's bottom edge at
    every distance (roofs behind roofs, rising slowly to the skyline)"""
    d = max(20.0, math.hypot(x - EYE.x, y - EYE.y))
    e_r = -2.9 - 4.3 * math.exp(-(d - 40.0) / 240.0)                     # -7.1 deg at 46 m .. -3.1 at 1 km: rows step up; the home pane
    # (-6.1..+0.8 deg since window67) keeps its upper half for the hills, the spire and the sky
    h_nom = 8.0 + 4.5 * (1.0 - math.exp(-(d - 30.0) / 70.0))
    return EYE.z + d * math.tan(math.radians(e_r)) - h_nom


town = Mesh()
far = Mesh()
gnd = Mesh()


def place(az, dist):
    """(x, y) at `dist` metres from the home eye, `az` deg left of the pane's normal (+x)"""
    return EYE.x + dist * math.cos(math.radians(az)), EYE.y + dist * math.sin(math.radians(az))


trng = random.Random(1944)
STREETS = [(46, 7.0), (78, 7.0), (112, 7.5), (150, 8.0), (195, 8.0), (248, 8.5), (310, 9.0), (380, 9.0), (460, 10.0), (560, 10.0),
           (680, 11.0), (820, 11.0), (980, 12.0), (1140, 12.0)]
KERB = [(EYE.x + sx - sw / 2, EYE.x + sx + sw / 2) for sx, sw in STREETS]
YLO, YHI = -260.0, 1150.0               # the rows' extent across the view (from the eye's y): every camera that sees the pane
X_END = EYE.x + 1330.0                  # the fields run on under the hills' foot (1300+)
# the church: on its own square in the town, 650 m out on the pane's line of sight (no knoll - QA 2026-11-09); the rows keep clear
CH_X, CH_Y = place(26.0, 650)
KN_R, KN_Y = 40.0, 1.0                  # the square's radius (the rows are cut KN_R + 12 m round it)

PAVE, KH, KW = 1.6, 0.12, 0.03          # pavement width, kerb height, kerb face width (a near-vertical strip of the ground grid)
# the blocks: (x of the near kerb's far side, x of the next street's near kerb, front-row depth, double?)
BLOCKS = []
for si in range(len(STREETS) - 1):
    xa, xb = KERB[si][1], KERB[si + 1][0]
    dep = xb - xa
    if dep >= 26.0:
        BLOCKS.append((si, xa, xb, min(11.0, (dep - 2 * PAVE) * 0.36), True))
    else:
        BLOCKS.append((si, xa, xb, min(11.0, max(6.0, dep - 2.0 - PAVE)), False))      # never deeper than 11 m: a 23 m deep house carried a 10 m roof that filled the home pane (QA 2026-11-09)


def S(i, y):
    """street i's level (flat across the street) at y"""
    return G(KERB[i][0], y)


def Gl(x, y):
    """the ground actually built (real metres): street levels; a kerb up to the pavement and the rows' floor; yard ramps between"""
    if x <= KERB[0][1]:
        return S(0, y)
    for (si, xa, xb, d1, dbl) in BLOCKS:
        if x <= xa:
            return S(si, y)                              # on street si
        if x <= xb:
            s0, s1 = S(si, y) + KH, S(si + 1, y) + (KH if dbl else 0.0)
            if x < xa + KW:
                return S(si, y) + KH * (x - xa) / KW     # the kerb's face
            if dbl and x > xb - KW:
                return S(si + 1, y) + KH * (xb - x) / KW
            f0_ = xa + PAVE + d1
            if dbl:
                if x <= f0_:
                    return s0
                if x >= xb - PAVE - d1:
                    return s1
                t = (x - f0_) / ((xb - PAVE - d1) - f0_)
            else:
                if x <= f0_:
                    return s0
                t = (x - f0_) / (xb - f0_)
            t = t * t * (3 - 2 * t)
            return s0 + (s1 - s0) * t
    last = len(STREETS) - 1
    if x <= KERB[last][1]:
        return S(last, y)
    return G(x, y) + (S(last, y) - G(KERB[last][1], y)) * math.exp(-(x - KERB[last][1]) / 60.0)


def pave_v(x):
    """the pavement texture's v at x (sidewalk2: the kerb band at v 0.40-0.42, slabs below), or None off the pavements"""
    for (si, xa, xb, d1, dbl) in BLOCKS:
        for k0, sg in ((xa, 1.0), (xb, -1.0)) if dbl else ((xa, 1.0),):
            dk = (x - k0) * sg
            if -1e-6 <= dk <= PAVE + 1e-6:
                return 0.42 - 0.02 * dk / KW if dk < KW else 0.40 - 0.38 * (dk - KW) / (PAVE - KW)
    return None


def knoll_z(x, y):
    """the knoll over the ground (smoothstep from the church's footing to the ground at its rim); None outside it"""
    r = math.hypot(x - CH_X, (y - CH_Y) / KN_Y)
    if r >= KN_R:
        return None
    t = r / KN_R
    s = t * t * (3 - 2 * t)
    g = Gl(x, y)
    return (cgz - 0.6) + (g - (cgz - 0.6)) * s


def low_ground(xc, cy, hd, hw, rot):
    """the lowest ground within 2.5 m round a footprint (rotation 0 / pi only)"""
    m = 1e9
    for sx in (-1, -0.5, 0, 0.5, 1):
        for sy in (-1, -0.5, 0, 0.5, 1):
            m = min(m, Gl(xc + sx * (hd + 2.5), cy + sy * (hw + 2.5)))
    return m


def plots(y0, y1, rng, wr, fixed=None):
    """plot boundaries from y0 to y1, widths in wr; fixed = (ya, yb) a plot that must be exactly there"""
    def split(a, b):
        ys = [a]
        while ys[-1] < b - 0.01:
            w = rng.uniform(*wr)
            if b - (ys[-1] + w) < 5.0:
                w = b - ys[-1]
            ys.append(min(b, ys[-1] + w))
        return ys
    if fixed is None:
        return split(y0, y1), None
    fa, fb = fixed
    if fa - y0 < 5.0:
        fa = y0
    if y1 - fb < 5.0:
        fb = y1
    left = split(y0, fa) if fa > y0 else [y0]
    right = split(fb, y1) if fb < y1 else [y1]
    ys = left + right                     # left ends at fa, right starts at fb: the fixed plot is (fa, fb)
    return ys, len(left) - 1


def terrace(mesh, x_front, depth, y0, y1, faces_attic, cfg, rng, banner=None):
    """a run of houses along y from y0 to y1, fronts on the street at x_front (facing -x if faces_attic, else +x), sharing party
    walls exactly. banner = (y target, layout): the plot over y target becomes a 12.5 m, 4-bay house carrying the banner(s)."""
    fixed = None
    if banner is not None:
        yt = banner[0]
        if y0 + 7.0 < yt < y1 - 7.0:
            fixed = (yt - 6.25, yt + 6.25)
        else:
            banner = None
    ys, kb = plots(y0, y1, rng, cfg["width"], fixed)
    n = len(ys) - 1
    xc = x_front + depth / 2 if faces_attic else x_front - depth / 2
    rot = 0.0 if faces_attic else math.pi
    hd = depth / 2
    last_wall = last_roof = None
    for k in range(n):
        ya, yb = ys[k], ys[k + 1]
        w = yb - ya
        cy = (ya + yb) / 2
        is_b = banner is not None and k == kb
        st = cfg["storeys"] if is_b else max(1, cfg["storeys"] + rng.choice((-1, 0, 0, 0, 1)))
        h = st * 3.1 + 0.5
        roof = hd * math.tan(math.radians(cfg["pitch"] + rng.uniform(-3, 3)))
        walls = [m for m in cfg["walls"] if m != last_wall] or cfg["walls"]
        roofs = [m for m in cfg["roofs"] if m != last_roof] or cfg["roofs"]
        wm, rm = rng.choice(walls), rng.choice(roofs)
        if is_b:
            wm = cfg["walls"][0]
        last_wall, last_roof = wm, rm
        fl = Gl(x_front + (0.5 if faces_attic else -0.5), cy)            # the floor: the street's level at the door
        lo = low_ground(xc, cy, hd, w / 2, rot)
        # local -y/+y of a house turned half round is world +y/-y: overhangs and party-wall chimneys follow the world ends
        o_lo, o_hi = (0.3 if k == 0 else 0.0), (0.3 if k == n - 1 else 0.0)
        chim_w = []
        if cfg["chim"] and k < n - 1 and rng.random() < 0.65:
            chim_w.append(w / 2)                                         # world +y end: the party wall with the next plot
        if not faces_attic:
            o_lo, o_hi = o_hi, o_lo
            chim_w = [-v for v in chim_w]
        house(mesh, (xc, cy, fl), w, depth, h, roof, rm, wm, rot=rot, ridge_y=True, chims_at=chim_w, wins=cfg["wins"],
              lit=cfg["lit"], dormers=(0 if is_b else (rng.choice((0, 0, 1, 2)) if cfg["dormer"] else 0)),
              smoke=cfg["smoke"] and rng.random() < 0.35, oy=(o_lo, o_hi), win_cols=(4 if is_b else None),
              banner=(banner[1] if is_b else None), plinth=max(1.0, fl - lo + 0.5),
              ww=(0.55 if is_b else rng.choice((0.52, 0.58, 0.62, 0.68))), front=faces_attic, detail=cfg["detail"],
              shop=faces_attic and cfg["detail"] and not is_b and rng.random() < 0.22)
    return n


ROOFS_N = ["tile", "tile2", "tile3", "slate"]
WALLS_N = ["plaster", "plaster_o", "plaster_g", "brick", "plaster_b", "ochre"]
BANNER_ROWS = {0: 0, 2: 1}               # (QA 2026-11-09: rows 1-2 sat behind block 0 from LOOK OUTSIDE - the first front row is in full view)               # street index -> layout (0 one centred, 1 an even pair); on the row facing the attic
NHOUSE = 0
for (si, xa, xb, d1, dbl) in BLOCKS:
    sx0 = STREETS[si][0]
    farrow = sx0 > 420
    cfg = dict(storeys=2 if sx0 < 120 else (3 if sx0 < 420 else 2), pitch=trng.choice((36, 40, 44)),
               roofs=trng.sample(ROOFS_N, 2), walls=trng.sample(WALLS_N, 3), wins=("lights" if farrow else True),
               lit=0.5 if sx0 < 160 else (0.3 if not farrow else 0.12), chim=not farrow, dormer=sx0 < 200, smoke=sx0 < 260,
               width=(7.0, 11.0) if not farrow else (10.0, 16.0), detail=not farrow)
    ylo_r = EYE.y + max(YLO, -0.06 * sx0 - 25.0)                  # only what some camera through the pane can see
    yhi_r = EYE.y + min(YHI, 0.95 * sx0 + 60.0)
    cross, yc = [], ylo_r
    while yc < yhi_r:
        yc += trng.uniform(45, 90) * (1.0 if not farrow else 1.6)
        cross.append(yc)
    segs, prev = [], ylo_r
    for c in cross:
        cw = 6.0 if not farrow else 8.0
        segs.append((prev, min(c - cw / 2, yhi_r)))
        prev = c + cw / 2
        if prev >= yhi_r:
            break
    # the church square: no houses on it (cut the segments where the block crosses it)
    xn = min(max(CH_X, xa), xb)
    if abs(xn - CH_X) < KN_R + 12.0:
        hy = KN_Y * math.sqrt(max(0.0, (KN_R + 12.0) ** 2 - (xn - CH_X) ** 2)) + 6.0
        cut = []
        for (ya, yb) in segs:
            if yb <= CH_Y - hy or ya >= CH_Y + hy:
                cut.append((ya, yb))
                continue
            if ya < CH_Y - hy:
                cut.append((ya, CH_Y - hy))
            if yb > CH_Y + hy:
                cut.append((CH_Y + hy, yb))
        segs = cut
    target = BANNER_ROWS.get(si)
    yt = EYE.y + 0.52 * (xa + PAVE - EYE.x)                        # on the home camera's line of sight
    mesh = town if not farrow else far
    segs = [sg for sg in segs if sg[1] - sg[0] >= 12.0]
    if target is not None and segs:
        # the banner house: on the home camera's line of sight, pulled inside the nearest run (never across a cross street)
        sb = min(segs, key=lambda sg: 0.0 if sg[0] + 7.5 <= yt <= sg[1] - 7.5 else min(abs(yt - sg[0]), abs(yt - sg[1])))
        if sb[1] - sb[0] >= 16.0:
            yt = min(max(yt, sb[0] + 7.5), sb[1] - 7.5)
    for (ya, yb) in segs:
        bn = (yt, target) if (target is not None and ya + 7.0 < yt < yb - 7.0) else None
        NHOUSE += terrace(mesh, xa + PAVE, d1, ya, yb, True, cfg, trng, banner=bn)
        if dbl:
            NHOUSE += terrace(mesh, xb - PAVE, d1, ya, yb, False, cfg, trng)
print("TOWN houses", NHOUSE, flush=True)

# the ground: one continuous grid on Gl (streets cobbled, the blocks earth, fields past the town), from the retaining wall outwards;
# x breaks at every kerb and platform edge, finer near the eye; one y grid for every strip (no T-junction cracks)
xs = {EYE.x + 38.0, X_END}
for k0, k1 in KERB:
    xs |= {k0, k1}
for (si, xa, xb, d1, dbl) in BLOCKS:
    xs |= {xa + KW, xa + PAVE, xa + PAVE + d1} | ({xb - KW, xb - PAVE, xb - PAVE - d1} if dbl else set())
xs = sorted(xs)
gx = [xs[0]]
for a, b in zip(xs, xs[1:]):
    stp = max(2.0, 0.05 * (a - EYE.x))
    n = max(1, int(math.ceil((b - a) / stp)))
    gx += [a + (b - a) * (i + 1) / n for i in range(n)]
gy = [0.0]
while gy[-1] < YHI + 200:
    gy.append(gy[-1] + 3.0 + 0.05 * gy[-1])
gneg = [0.0]
while gneg[-1] > YLO - 120:
    gneg.append(gneg[-1] - (3.0 - 0.05 * gneg[-1]))
gy = sorted(set([EYE.y + v for v in gy + gneg]))


def gmat(xm):
    if xm > KERB[-1][1] + 6.0:
        return "field"
    if pave_v(xm) is not None:
        return "pave"
    for k0, k1 in KERB:
        if k0 <= xm <= k1:
            return "street"
    return "yard"


f0 = len(gnd.f)
for i in range(len(gx) - 1):
    x0_, x1_ = gx[i], gx[i + 1]
    mat = gmat((x0_ + x1_) / 2)
    for j in range(len(gy) - 1):
        y0_, y1_ = gy[j], gy[j + 1]
        if mat == "pave":
            v0_, v1_ = pave_v(x0_), pave_v(x1_)
            uvq = [(y0_ / 4.2, v0_), (y0_ / 4.2, v1_), (y1_ / 4.2, v1_), (y1_ / 4.2, v0_)]
        else:
            uvq = [(x0_, y0_), (x1_, y0_), (x1_, y1_), (x0_, y1_)]
        gnd.quad([(x0_, y0_, Gl(x0_, y0_)), (x1_, y0_, Gl(x1_, y0_)), (x1_, y1_, Gl(x1_, y1_)), (x0_, y1_, Gl(x0_, y1_))],
                 mat, uvq)
gnd.orient(f0, up=True)
# the step between the neighbours' yard (GN) and the town's first street level: a stone retaining wall facing the attic
_xw = EYE.x + 38.0
f0 = len(gnd.f)
for j in range(len(gy) - 1):
    y0_, y1_ = gy[j], gy[j + 1]
    za0, za1 = min(GN, Gl(_xw, y0_)) - 1.0, min(GN, Gl(_xw, y1_)) - 1.0
    zb0, zb1 = max(GN, Gl(_xw, y0_)), max(GN, Gl(_xw, y1_))
    gnd.quad([(_xw, y0_, za0), (_xw, y1_, za1), (_xw, y1_, zb1), (_xw, y0_, zb0)], "stone", [(y0_, za0), (y1_, za1), (y1_, zb1), (y0_, zb0)])
gnd.orient(f0, (_xw - 10.0, 0.0, GN))

# ---- the church: in the town on its own square (QA 2026-11-09: on a 1 km knoll it read as a grey cube on a pale snowfield).
# A nave of 26 x 11 m, its long side to the attic, a 7 m square tower at its right end with a slate spire: tip ~48 m up
cgz = Gl(CH_X, CH_Y)
_lo = min(Gl(CH_X + sx * 12.0, CH_Y + sy * 20.0) for sx in (-1, 0, 1) for sy in (-1, 0, 1))
town.step = 0.0
house(town, (CH_X, CH_Y + 4.5, cgz), 26.0, 11.0, 11.0, 7.5, "slate", "stone", ridge_y=True, chims_at=[], wins=False,
      oy=(0.0, 0.3), plinth=max(1.0, cgz - _lo + 0.6), detail=False)
q = 3.5
TX, TY = CH_X, CH_Y + 4.5 - 13.0 - q            # the tower abuts the nave's right gable (y - 13) - never inside it
f0 = len(town.f)
town.step = max(2.5, 0.035 * (Vector((TX, TY, cgz)) - EYE).length)
box_sides(town, lambda x, y, z: Vector((TX + x, TY + y, cgz + z)), [(-q, -q), (-q, q), (q, q), (q, -q)],
          -max(1.0, cgz - _lo + 0.6), 27.0, "stone")
box_sides(town, lambda x, y, z: Vector((TX + x, TY + y, cgz + z)), [(-q - 0.25, -q - 0.25), (-q - 0.25, q + 0.25), (q + 0.25, q + 0.25), (q + 0.25, -q - 0.25)],
          26.4, 27.0, "trim")                     # a string course under the spire
town.step = 0.0
for (a, b) in (((-q, -q), (-q, q)), ((-q, q), (q, q)), ((q, q), (q, -q)), ((q, -q), (-q, -q))):
    town.quad([(TX + a[0] * 1.08, TY + a[1] * 1.08, cgz + 27.0), (TX + b[0] * 1.08, TY + b[1] * 1.08, cgz + 27.0), (TX, TY, cgz + 48.0)],
              "slate", [(0, 0), (7.6, 0), (3.8, 21.4)])
town.orient(f0, (TX, TY, cgz + 20))
print("CHURCH at", round(CH_X - EYE.x), round(CH_Y - EYE.y), "floor", round(cgz, 1), "spire tip elev %.2f deg" %
      math.degrees(math.atan2(cgz + 48.0 - EYE.z, math.hypot(TX - EYE.x, TY - EYE.y))), flush=True)

# ---- the distance (QA 2026-11-09 "what's out in the distance?": one pale faceted mound): three soft rolling ridges, 1.3-3.4 km,
# layered by aerial perspective (haze_of: green to blue with distance); the nearest a patchwork of fields with hedgerows and
# woods, its crest lined with trees. Welded and smooth-shaded (no facets); textured like the town (the game's grass / foliage)
hills = Mesh()
trees = Mesh()
FIELDS_N = ["meadow", "pasture", "wheat", "plough", "meadow", "pasture", "wood"]
FIELDS_F = ["meadow", "wood", "pasture", "wood", "meadow"]
RIDGES = []


def ridge(x0, x1, e_base, e_amp, seed, fields, patch, ny=230, nx=16, ylo=-700, yhi=2700):
    """a ridge given by the elevation (deg, home eye) of its crest: rises from x0 (its foot under the ground in front), crests, falls
    to x1; the crest line rolls along y; a field patchwork (patch = (dx, dy) metres) picks each quad's material"""
    r = random.Random(seed)
    ph = [r.uniform(0, 6.28) for _ in range(6)]
    ys = [EYE.y + ylo + (yhi - ylo) * j / (ny - 1) for j in range(ny)]
    xs = [x0 + (x1 - x0) * i / (nx - 1) for i in range(nx)]

    def zfun(x, y):
        t = min(1.0, max(0.0, (x - x0) / (x1 - x0)))
        hgt = 0.72 + 0.16 * math.sin(y / 430 + ph[0]) + 0.08 * math.sin(y / 170 + ph[1]) + 0.04 * math.sin(y / 73 + ph[2])
        prof = 0.5 - 0.5 * math.cos(2 * math.pi * min(t, 0.5)) if t < 0.5 else 0.55 + 0.45 * math.cos(math.pi * (t - 0.5) * 1.6)
        roll = 0.10 * math.sin(x / 140 + ph[3]) * math.sin(y / 210 + ph[4])
        e = e_base + e_amp * hgt * prof + roll * prof
        d = math.hypot(x - EYE.x, y - EYE.y)
        return EYE.z + d * math.tan(math.radians(e))
    P_ = [Vector((x, y, zfun(x, y))) for x in xs for y in ys]
    K = lambda i, j: i * ny + j
    pr = random.Random(seed * 7 + 1)
    pmat = {}
    groups = {}
    for i in range(nx - 1):
        for j in range(ny - 1):
            xm, ym = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            key = (int((xm - x0) // patch[0]), int((ym - EYE.y + 5000) // patch[1]))
            if key not in pmat:
                pmat[key] = pr.choice(fields)
            m = pmat[key]
            idx = (K(i, j), K(i + 1, j), K(i + 1, j + 1), K(i, j + 1))
            groups.setdefault(m, []).append((idx, [(P_[k].y, P_[k].x) for k in idx]))
    for m, faces in groups.items():
        used = sorted({k for idx, _ in faces for k in idx})
        remap = {k: n for n, k in enumerate(used)}
        f0 = len(hills.f)
        hills._grid([P_[k] for k in used], m, [(tuple(remap[k] for k in idx), uv) for idx, uv in faces])
        hills.orient(f0, up=True)
    RIDGES.append((x0, x1, zfun, pmat, patch))
    return zfun


# feet just under the fields' edge (-3.75 deg); crests -1.5 / -1.0 / -0.5 deg on average: each ridge shows over the one before
z1 = ridge(EYE.x + 1300, EYE.x + 2150, -3.75, 2.7, 7, FIELDS_N, (170.0, 210.0))
z2 = ridge(EYE.x + 1950, EYE.x + 2850, -3.8, 3.3, 11, FIELDS_F, (420.0, 520.0), ny=170, nx=12)
z3 = ridge(EYE.x + 2650, EYE.x + 3350, -3.85, 3.9, 13, ["wood", "meadow"], (900.0, 900.0), ny=120, nx=10)


def clump(mesh, x, y, zf, rad, hgt, m="wood"):
    """a tree clump: a soft dome of the game's foliage, its rim 1.5 m under the ground (follows the slope)"""
    n, rings = 8, 3
    base = [(x + rad * math.cos(2 * math.pi * k / n), y + rad * math.sin(2 * math.pi * k / n)) for k in range(n)]
    pts = [Vector((bx, by, zf(bx, by) - 1.5)) for bx, by in base]
    P_ = list(pts)
    for rr in range(1, rings + 1):
        a = rr / (rings + 1)
        sc = math.cos(a * math.pi / 2)
        zc = zf(x, y) + hgt * math.sin(a * math.pi / 2)
        P_ += [Vector((x + rad * sc * 1.05 * math.cos(2 * math.pi * k / n), y + rad * sc * 1.05 * math.sin(2 * math.pi * k / n), zc)) for k in range(n)]
    P_.append(Vector((x, y, zf(x, y) + hgt)))
    faces = []
    for rr in range(rings):
        for k in range(n):
            a_, b_ = rr * n + k, rr * n + (k + 1) % n
            c_, d_ = (rr + 1) * n + (k + 1) % n, (rr + 1) * n + k
            faces.append(((a_, b_, c_, d_), [(k * 3.0, rr * 4.0), (k * 3.0 + 3, rr * 4.0), (k * 3.0 + 3, rr * 4.0 + 4), (k * 3.0, rr * 4.0 + 4)]))
    top = len(P_) - 1
    for k in range(n):
        a_, b_ = rings * n + k, rings * n + (k + 1) % n
        faces.append(((a_, b_, top), [(k * 3.0, 12.0), (k * 3.0 + 3, 12.0), (k * 3.0 + 1.5, 15.0)]))
    f0 = len(mesh.f)
    mesh._grid(P_, m, faces)
    mesh.orient(f0, (x, y, zf(x, y) + hgt * 0.3))


def hedge(mesh, x, ya, yb, zf, h=2.6, w=2.4):
    """a hedgerow along y at x: a soft prism of foliage following the ground, its feet under it"""
    n = max(2, int((yb - ya) / 18.0) + 1)
    ys_ = [ya + (yb - ya) * k / (n - 1) for k in range(n)]
    P_ = []
    for y_ in ys_:
        g = zf(x, y_)
        P_ += [Vector((x - w / 2, y_, g - 1.2)), Vector((x - w * 0.15, y_, g + h)), Vector((x + w * 0.15, y_, g + h)), Vector((x + w / 2, y_, g - 1.2))]
    faces = []
    for k in range(n - 1):
        for s in range(3):
            a_, b_ = k * 4 + s, k * 4 + s + 1
            faces.append(((a_, b_, b_ + 4, a_ + 4), [(ys_[k], s * 1.5), (ys_[k], s * 1.5 + 1.5), (ys_[k + 1], s * 1.5 + 1.5), (ys_[k + 1], s * 1.5)]))
    f0 = len(mesh.f)
    mesh._grid(P_, "wood", faces)
    mesh.orient(f0, (x, (ya + yb) / 2, zf(x, (ya + yb) / 2) - 30.0))


trng2 = random.Random(68)
x0, x1, zf, pmat, patch = RIDGES[0]
yv0, yv1 = EYE.y - 120.0, EYE.y + 2050.0          # what the cameras see of the near ridge
# hedgerows along the patch edges that run across the view (constant x), broken where a wood patch meets
for (pi, pj), m in pmat.items():
    xe = x0 + (pi + 1) * patch[0]
    ya, yb = EYE.y - 5000 + pj * patch[1], EYE.y - 5000 + (pj + 1) * patch[1]
    if xe >= x1 - 60 or yb < yv0 or ya > yv1 or m == "wood" or pmat.get((pi + 1, pj)) == "wood":
        continue
    hedge(trees, xe, ya + 6.0, yb - 6.0, zf)
# woods: clumps over every wood patch's edge facing the attic + a scatter inside; the crest lined with trees, gaps between
for (pi, pj), m in pmat.items():
    if m != "wood":
        continue
    xa, ya = x0 + pi * patch[0], EYE.y - 5000 + pj * patch[1]
    if ya + patch[1] < yv0 or ya > yv1:
        continue
    for k in range(int(patch[1] / 13.0)):
        clump(trees, xa + trng2.uniform(2, 9), ya + 6.5 + k * 13.0 + trng2.uniform(-2, 2), zf, trng2.uniform(5.5, 8.0), trng2.uniform(11, 17))
    for k in range(int(patch[0] * patch[1] / 2600.0)):
        clump(trees, xa + trng2.uniform(15, patch[0] - 8), ya + trng2.uniform(8, patch[1] - 8), zf, trng2.uniform(6, 9), trng2.uniform(12, 18))
xc = x0 + (x1 - x0) * 0.5
y_ = yv0
while y_ < yv1:
    run = trng2.uniform(60, 220)
    for k in range(int(run / 12.0)):
        clump(trees, xc + trng2.uniform(-25, 25), y_ + k * 12.0, zf, trng2.uniform(5.5, 8.5), trng2.uniform(12, 18))
    y_ += run + trng2.uniform(40, 160)
# the far ridges: woods as soft bands along their crests (no detail reads at 2-3 km, the silhouette does)
for (xr0, xr1, zfr, _, _), stepy in ((RIDGES[1], 26.0), (RIDGES[2], 40.0)):
    xc_ = xr0 + (xr1 - xr0) * 0.5
    y_ = yv0
    while y_ < EYE.y + 3000:
        run = trng2.uniform(150, 500)
        for k in range(int(run / stepy)):
            clump(trees, xc_ + trng2.uniform(-40, 40), y_ + k * stepy, zfr, trng2.uniform(9, 14), trng2.uniform(14, 20))
        y_ += run + trng2.uniform(80, 300)
print("DISTANCE hills tris", sum(len(f) - 2 for f in hills.f), "trees tris", sum(len(f) - 2 for f in trees.f), flush=True)


def _sq(p):
    v = Vector(p)
    dd = (v - EYE).length
    f = squash(dd) / dd if dd > 1e-6 else 1.0
    return EYE + (v - EYE) * f, f


# every vertex by its own distance (shared walls stay shared), and every light and mark the same way; a banner's wall normal is the
# SQUASHED wall's (the squash compresses along the sight line, so the wall turns: a banner on the real normal stood off one edge)
for _m in (near, town, far, gnd, gnd_near, hills, trees):
    _m.squash_each(0)
LIGHTS[:] = [[tuple(_sq(p)[0]) for p in q] for q in LIGHTS]
for _mk in MARKS:
    p0 = Vector(_mk[1])
    sp, f = _sq(p0)
    nr = _mk[3]
    if nr is not None:
        n = Vector(nr)
        t = n.cross(Vector((0, 0, 1))).normalized()
        a, _ = _sq(p0 + t * 0.5)
        b, _ = _sq(p0 - t * 0.5)
        up, _ = _sq(p0 + Vector((0, 0, 0.5)))
        dn, _ = _sq(p0 - Vector((0, 0, 0.5)))
        ns = (a - b).cross(up - dn).normalized()
        if ns.dot(n) < 0:
            ns = -ns
        _mk[3] = tuple(ns)
    _mk[1], _mk[2] = tuple(sp), _mk[2] * f
    _mk += [tuple(p0), tuple(nr) if nr is not None else None]          # [4] the real point, [5] the real wall normal
_ov = []
_FPs = sorted(FP)
for _i, a_ in enumerate(_FPs):
    for b_ in _FPs[_i + 1:]:
        if b_[0] >= a_[1] - 0.05:
            break
        ox = min(a_[1], b_[1]) - max(a_[0], b_[0])
        oy_ = min(a_[3], b_[3]) - max(a_[2], b_[2])
        if ox > 0.05 and oy_ > 0.05:
            _ov.append((a_[4], b_[4], round(ox, 2), round(oy_, 2)))
print("OVERLAPS", len(_ov), _ov[:10], flush=True)
print("TRIS", {k: sum(len(fc) - 2 for fc in m_.f) for k, m_ in (("near", near), ("town", town), ("far", far), ("ground", gnd),
                                                             ("ground_near", gnd_near), ("hills", hills), ("trees", trees))}, "LIGHTS", len(LIGHTS), flush=True)
near.build("near", "near")
town.build("town", "town")
far.build("far", "far")
gnd.build("ground", "ground")
gnd_near.build("ground_near", "ground")
hills.smooth = trees.smooth = True
hills.build("hills", "hills")
trees.build("trees", "trees")



def dump_marks():
    json.dump([dict({"kind": k, "p": list(p), "size": sz, "preal": list(pr)},
                    **({"face": list(fc), "facereal": list(fr)} if fc is not None else {})) for k, p, sz, fc, pr, fr in MARKS],
              open(os.path.join(OUT, "marks.json"), "w"), indent=1)
    print("MARKS", len(MARKS))


# ---------------------------------------------------------------- light: bright overcast sky + a low warm sun from the left
SC.render.engine = 'CYCLES'
cy = SC.cycles
prefs = bpy.context.preferences.addons["cycles"].preferences
cy.device = 'CPU'
for dev in (() if arg("--device", "gpu") == "cpu" else ("OPTIX", "CUDA")):      # --device cpu: leave the GPU to the user's game
    try:
        prefs.compute_device_type = dev
        prefs.get_devices()
        if [d for d in prefs.devices if d.type == dev]:
            for d in prefs.devices:
                d.use = d.type == dev
            cy.device = 'GPU'
            break
    except Exception as e:
        print("device", dev, e)
cy.samples = SPP
cy.use_denoising = True
cy.max_bounces = 4
world = bpy.data.worlds.new("w")
SC.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.62, 0.68, 0.80, 1)
bg.inputs["Strength"].default_value = 0.9
sd = bpy.data.lights.new("sun", 'SUN')
sd.energy = 2.6
sd.angle = math.radians(6)
sd.color = (1.0, 0.95, 0.86)
so = bpy.data.objects.new("sun", sd)
SC.collection.objects.link(so)
so.rotation_euler = (math.radians(52), 0, math.radians(-25))       # from the upper left and in front: facades towards the attic half-lit
SC.view_settings.view_transform = 'Standard'

if MODE == "marks":
    dump_marks()

if MODE == "preview":
    sky = arg("--sky", "")
    # stand-in wall with the window hole, black inside
    wm = bpy.data.materials.new("wallin"); wm.use_nodes = True
    wm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.05, 0.05, 1)
    wall = Mesh()
    y0, y1, z0, z1 = WIN["y0"], WIN["y1"], WIN["z0"], WIN["z1"]
    M["wallin"] = wm
    REP["wallin"] = 1.0
    for (ya, yb, za, zb) in ((-20, y0, -6, 12), (y1, 30, -6, 12), (y0, y1, -6, z0), (y0, y1, z1, 12)):
        wall.quad([(WALL_X, ya, za), (WALL_X, yb, za), (WALL_X, yb, zb), (WALL_X, ya, zb)], "wallin", [(0, 0), (1, 0), (1, 1), (0, 1)])
    wall.build("wall", "_wall")
    if sky:
        sm = bpy.data.materials.new("sky"); sm.use_nodes = True
        nt = sm.node_tree
        for n in list(nt.nodes):
            if n.type == 'BSDF_PRINCIPLED':
                nt.nodes.remove(n)
        em = nt.nodes.new("ShaderNodeEmission")
        ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(sky)
        uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = "tex"
        nt.links.new(uv.outputs["UV"], ti.inputs["Vector"]); nt.links.new(ti.outputs["Color"], em.inputs["Color"])
        nt.links.new(em.outputs["Emission"], nt.nodes["Material Output"].inputs["Surface"])
        M["sky"] = sm
        REP["sky"] = 1.0
        # the sky plane: 90 deg face, horizon row at v=SKY_HV, at x = 300 m
        info = json.load(open(arg("--skyjson", "H:/hzm_work/wx/sky/wx_sky.json")))
        D = info["D"]; X = WALL_X + D
        hz = horizon_z(X)
        sk = Mesh()
        sk.quad([(X, info["yL"], hz + info["zB"]), (X, info["yR"], hz + info["zB"]),
                 (X, info["yR"], hz + info["zT"]), (X, info["yL"], hz + info["zT"])], "sky",
                [(0, 0), (1, 0), (1, 1), (0, 1)])
        o = sk.build("sky", "_sky")
        o.visible_diffuse = o.visible_shadow = o.visible_glossy = False
    cams = arg("--cams", "home,close,ng").split(",")
    for cn in cams:
        (ox, oy, oz), pitch, yaw, vfov = CAMS[cn]
        cd = bpy.data.cameras.new(cn)
        cd.sensor_fit = 'VERTICAL'
        cd.angle_y = math.radians(vfov)
        cd.clip_start = 0.05
        cd.clip_end = 2048 / 52.5 if cn != "homezoom" else 60.0          # the engine's UI scene far plane (along x for yaw 0)
        co = bpy.data.objects.new(cn, cd)
        SC.collection.objects.link(co)
        co.location = (ox / 52.5, oy / 52.5, oz / 52.5)
        # game: x forward, yaw about z, pitch positive = down. Blender camera looks down -Z local.
        co.rotation_euler = (math.radians(90 - pitch), 0, math.radians(yaw - 90))
        SC.camera = co
        SC.render.resolution_x = int(RES * 2.39)
        SC.render.resolution_y = RES
        SC.render.filepath = os.path.join(OUT, "prev_%s.png" % cn)
        bpy.ops.render.render(write_still=True)
        print("PREVIEW", cn, SC.render.filepath, flush=True)

if MODE == "bake":
    TEXG = ("near", "town", "far", "ground", "hills", "trees")                 # drawn with the game's textures x LIGHT + HAZE atlases
    SIZES = {"near": int(arg("--near", "1024")), "town": int(arg("--town", "4096")), "far": int(arg("--far", "2048")),
             "ground": int(arg("--ground", "2048")), "hills": int(arg("--hills", "2048")), "trees": 2048}
    for k_, m_ in M.items():
        m_["key"] = k_
    bk = SC.render.bake
    bk.margin = 8
    for g, objs in GROUPS.items():
        if g.startswith("_"):
            continue
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.duplicate()
        dup = list(bpy.context.selected_objects)
        bpy.context.view_layer.objects.active = dup[0]
        if len(dup) > 1:
            bpy.ops.object.join()
        t = bpy.context.view_layer.objects.active
        t.name = "B_" + g
        for o in objs:
            o.hide_render = True
        me = t.data
        at = me.uv_layers.new(name="atlas")
        me.uv_layers.active = at
        # unwrap on the SQUASHED shape (texels where the screen has pixels), bake on the real one
        real = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", real)
        sqv = np.empty(len(me.vertices) * 3, np.float32)
        me.attributes["sq"].data.foreach_get("vector", sqv)
        me.vertices.foreach_set("co", sqv)
        me.update()
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(40), island_margin=0.0003, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
        bpy.ops.uv.pack_islands(margin=0.002, rotate=True)
        bpy.ops.object.mode_set(mode='OBJECT')
        me.vertices.foreach_set("co", real)
        me.update()
        me.uv_layers["tex"].active_render = True
        R_ = SIZES[g]
        im = bpy.data.images.new("bake_" + g, R_, R_, float_buffer=True)
        mats_here = [m for m in me.materials]
        for m in mats_here:
            nt = m.node_tree
            for n in list(nt.nodes):
                if n.name.startswith("BAKE"):
                    nt.nodes.remove(n)
            uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = "atlas"; uvn.name = "BAKEUV"
            n = nt.nodes.new("ShaderNodeTexImage"); n.image = im; n.name = "BAKE"
            nt.links.new(uvn.outputs["UV"], n.inputs["Vector"])
            nt.nodes.active = n
        bpy.ops.object.select_all(action='DESELECT')
        t.select_set(True)
        bpy.context.view_layer.objects.active = t
        bk.use_selected_to_active = False

        def grab():
            a = np.empty(R_ * R_ * 4, np.float32)
            im.pixels.foreach_get(a)
            return a.reshape(R_, R_, 4)[::-1, :, :3]            # row 0 = the top (v = 1), like an image file

        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT', 'COLOR'}, margin=8, use_clear=True)
        if g in TEXG:
            Lt = grab()
            np.savez_compressed(os.path.join(OUT, g + "_L.npz"), img=Lt.astype(np.float16))
            for m in mats_here:
                m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 1.0
            bpy.ops.object.bake(type='EMIT', margin=8, use_clear=True)
            Ht = grab()
            np.savez_compressed(os.path.join(OUT, g + "_H.npz"), img=Ht.astype(np.float16))
            for m in mats_here:
                m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 0.0
            print("BAKED-L", g, "L p50/p99 %.3f %.3f" % (float(np.percentile(Lt, 50)), float(np.percentile(Lt, 99))), flush=True)
        else:
            im.filepath_raw = os.path.join(OUT, g + ".png")
            im.file_format = 'PNG'
            im.save_render(os.path.join(OUT, g + ".png"), scene=SC)
        # triangles: squashed positions (metres, game axes), atlas uv, the texture's uv, material
        me.calc_loop_triangles()
        uvd = me.uv_layers["atlas"].data
        tvd = me.uv_layers["tex"].data
        sqd = me.attributes["sq"].data
        Pp, U_, T_, MI = [], [], [], []
        for tr in me.loop_triangles:
            Pp.append([tuple(sqd[i].vector) for i in tr.vertices])
            U_.append([tuple(uvd[l].uv) for l in tr.loops])
            T_.append([tuple(tvd[l].uv) for l in tr.loops])
            MI.append(tr.material_index)
        names = [m.get("key", m.name) for m in me.materials]
        np.savez_compressed(os.path.join(OUT, g + ".npz"), pos=np.array(Pp, np.float32), uv=np.array(U_, np.float32),
                            tuv=np.array(T_, np.float32), mi=np.array(MI, np.int16), mats=np.array(names))
        print("BAKED", g, len(Pp), flush=True)
        for m in mats_here:
            for n in list(m.node_tree.nodes):
                if n.name.startswith("BAKE"):
                    m.node_tree.nodes.remove(n)
        bpy.data.objects.remove(t, do_unlink=True)
        for o in objs:
            o.hide_render = False
    np.savez_compressed(os.path.join(OUT, "lights.npz"), quads=np.array(LIGHTS, np.float32))
    dump_marks()
    json.dump({"WC": list(WC), "wall_x": WALL_X, "win": WIN, "lights": len(LIGHTS),
               "townmats": {k: [v[0], v[1]] for k, v in TOWNTEX.items()}}, open(os.path.join(OUT, "town.json"), "w"), indent=1)
    print("LIGHTS", len(LIGHTS))
