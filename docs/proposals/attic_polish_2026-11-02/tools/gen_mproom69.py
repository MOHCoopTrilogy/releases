"""gen_mproom69.py <base pak> <pkadd dir> <out json> - v1.10.69: the MP (join-game) room lived in.

User (2026-11-09): the multiplayer room "feels barren". Four WWII posters went up in v1.10.68; this adds, in the handoff's order:
  1. a NOTICE BOARD on the right-hand wall (front half, x 15-75: the only free wall left - the back wall and the visible parts of
     the side walls are taken). It is a twin of the room's own SERVICE RECORD board: the same frame (its triangles copied from the
     hub bake and turned onto the right wall, so its light and wood are the room's own), an olive-drab face and a plaque. Three
     typed notices pinned to it - ORDERS OF THE DAY, SERVICE RECORD, PROMOTIONS - each its own model with a lit copy, so the
     scenehotfx lit-copy recipe (the attic projector) lights the hovered one. Off the home view: a right-edge cue turns the
     camera to it (a scripted peek, see patch_mproom69.py).
  2. a FIELD RADIO on an ammunition crate in front of the card table (the game's static_radio2 receiver on a .45 crate - the
     one floor spot whose hit box clears the six hotspots' boxes). Its lit copy (the dial window glowing) shows while it is
     hovered; a click tunes to the next menu record (vstr ui_mmSelNext, the gramophone's shuffle) with a short crackle cut from
     the game's own sound/mechanics/mec_radionoise_11.wav.
  3. a SOLDIER at a card table (a staged actor: the game's 29th-infantry private, the m1l1 card-game animations; MOHAA has no
     rifle-cleaning animation, so he plays patience with his Garand on the table). The game's square wooden table and the m1l1
     card chair, seated the way global/cardgame.scr seats its card players (15.4 u off a table side), two mugs, a saucer with
     a cigarette (the game has no ashtray), a hurricane lantern glowing softly.
  4. READY-ROOM CLUTTER: the bunker stove in the back-left corner with its flue to the ceiling and a soft flickering glow, a
     footlocker (the game's trunk) under the SERVICE RECORD board, and by the notice board a bench and a peg rail with two
     helmets and a pack. Soft contact shadows under the floor props. (No duffel bag: the game has no duffel model.)

Every prop is the game's own mesh with the game's own texture (main/mainta/maintt pak*.pk3 only - never an HD pack's, whose
paths a player without it would not have), baked into a menu model here so it can sit at any angle. Their shaders are mod-owned
copies (hzm_h69_*) with rgbGen lightingSpherical: the scene's lights (scenelight) light them like the attic's actors; the
room itself is baked and ignores those lights. Walls and floor are RAYCAST against the hub's own bake (the plaster is not where
the dado is: left 178.5 / 176.9 below the dado rail, right -136.5 / -134.9, back 283.5 / 281.9).
"""
import io, json, math, os, re, struct, sys, wave, zipfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools\engrave")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools\weapon_hd")
import skd_read as R  # noqa: E402
import skx as X  # noqa: E402
import vfs  # noqa: E402
import gunmesh as G  # noqa: E402

# the game's own assets only: the stock paks (Pak0..Pak6 / pak1..pak7), never an HD / mod pak that shadows a stock path
_paks0 = vfs.paks
vfs.paks = lambda: [p for p in _paks0() if re.match(r"(?i)^pak\d", os.path.basename(p))]
vfs._idx = None

base_pak, pkadd, out_json = sys.argv[1:4]
mdir, tdir, sdir, sndd = (os.path.join(pkadd, d) for d in ("models/menu", "textures/menu", "scripts", "sound/menu"))
adir = os.path.join(pkadd, "models", "human", "hzm_menu")
for d_ in (mdir, tdir, sdir, sndd, adir):
    os.makedirs(d_, exist_ok=True)
U = 52.5
LIGHT = 0.70                      # the hub's plaster level (gen_posters68): painted light for the baked (rgbGen identity) parts
rng = np.random.default_rng(1945)
SH = {}                           # shader name -> text
INFO = {"models": [], "lines": [], "lights": [], "hots": {}}

# ------------------------------------------------------------------ the room, for raycasts
zb = zipfile.ZipFile(base_pak)
TR = []
for n in ("hub_bg1", "hub_bg2", "hub_chrome1", "hub_floor1"):
    k = R.read_skd(zb.read("models/menu/%s.skd" % n))
    for s in k["surfaces"]:
        P = np.array([v[3] for v in s["verts"]])
        if len(s["tris"]):
            TR.append(P[s["tris"]])
TR = np.concatenate(TR)
_V0, _E1, _E2 = TR[:, 0], TR[:, 1] - TR[:, 0], TR[:, 2] - TR[:, 0]


def ray(o, d):
    o = np.asarray(o, float)
    d = np.asarray(d, float) / np.linalg.norm(d)
    p = np.cross(d, _E2)
    det = (_E1 * p).sum(1)
    ok = np.abs(det) > 1e-9
    inv = np.where(ok, 1.0 / np.where(ok, det, 1), 0)
    s = o - _V0
    u = (s * p).sum(1) * inv
    q = np.cross(s, _E1)
    v = (q * d).sum(1) * inv
    t = (q * _E2).sum(1) * inv
    hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-4)
    return float(np.min(np.where(hit, t, 1e18)))


def floor_z(x, y):
    return 100.0 - ray((x, y, 100.0), (0, 0, -1))


def wall(x, y, z, d):
    """the first surface from (x, y, z) along d: the hit point"""
    d = np.asarray(d, float)
    return np.asarray((x, y, z), float) + d * ray((x, y, z), d)


WL = wall(150, 0, 100, (0, 1, 0))[1]            # left plaster (y)
WLlo = wall(150, 0, 30, (0, 1, 0))[1]           # left wainscot
WR = wall(40, 0, 100, (0, -1, 0))[1]            # right plaster
WRlo = wall(40, 0, 30, (0, -1, 0))[1]
WB = wall(150, 160, 100, (1, 0, 0))[0]          # back plaster
WBlo = wall(150, 160, 30, (1, 0, 0))[0]
print("walls: left %.1f/%.1f right %.1f/%.1f back %.1f/%.1f" % (WL, WLlo, WR, WRlo, WB, WBlo))


# ------------------------------------------------------------------ helpers
def rot(yaw=0.0, pitch=0.0, roll=0.0):
    """column-vector rotation: roll about x, then pitch about y (positive = nose down, the engine's sense), then yaw about z"""
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    return Rz @ Ry @ Rx


def tri(p, uv, flip_v=True):
    p = [np.asarray(q, float) for q in p]
    nn = np.cross(p[1] - p[0], p[2] - p[0])
    ln = np.linalg.norm(nn)
    if ln < 1e-9:
        return None
    nn /= ln
    return [(0, tuple(p[k]), tuple(-nn), (float(uv[k][0]), float(1 - uv[k][1]) if flip_v else float(uv[k][1]))) for k in range(3)]


def quad(c, right, up, w, h, uv=(0, 0, 1, 1)):
    """a rectangle centred c spanning right * w, up * h; uv (u0, v0, u1, v1) v up; faces right x up"""
    c, right, up = (np.asarray(a, float) for a in (c, right, up))
    P = [c - right * w / 2 - up * h / 2, c + right * w / 2 - up * h / 2, c + right * w / 2 + up * h / 2, c - right * w / 2 + up * h / 2]
    u0, v0, u1, v1 = uv
    UV = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    return [t for t in (tri([P[0], P[1], P[2]], [UV[0], UV[1], UV[2]]), tri([P[0], P[2], P[3]], [UV[0], UV[2], UV[3]])) if t]


def write_model(nm, parts, anim=True):
    """parts = [(shader, corners)] -> models/menu/<nm>.tik/.skd/.skc (one bone); <= 30 surfaces (TRAPS: 32 drawn, chunk at 30)"""
    surfs, sl = [], []
    by = {}
    for sh_, crs in parts:
        by.setdefault(sh_, []).extend(c for c in crs if c)
    for k, (sh_, crs) in enumerate(by.items()):
        if not crs:
            continue
        ss = X.split_surfaces("s%d_" % k, crs)
        surfs += ss
        sl += ["\tsurface %s shader %s" % (q[0], sh_) for q in ss]
    assert 0 < len(surfs) <= 30, (nm, len(surfs))
    Pv = np.array([v[3] for s_ in surfs for v in s_[2]])
    open(os.path.join(mdir, nm + ".skd"), "wb").write(X.build_skd(nm, [("root", "worldbone")], surfs))
    open(os.path.join(mdir, nm + ".skc"), "wb").write(X.build_skc(["root pos", "root rot"], [[(0, 0, 0, 0), (0, 0, 0, 1)]], 0.1,
                                                                   (Pv.min(0) - 1).tolist(), (Pv.max(0) + 1).tolist(),
                                                                   float(np.linalg.norm(Pv, axis=1).max()) + 1))
    open(os.path.join(mdir, nm + ".tik"), "w", newline="\n").write(
        "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel %s.skd\n%s\n}\n\ninit\n{\n\tserver\n\t{\n\t\tclassname effectentity\n"
        "\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle %s.skc\n}\n" % (nm, "\n".join(sl), nm))
    INFO["models"].append(nm)
    return len(surfs), Pv.min(0), Pv.max(0)


# ------------------------------------------------------------------ the game's meshes, re-homed (mod-owned lightingSpherical shaders)
_shtext = None


def stock_shader(name):
    global _shtext
    if _shtext is None:
        _shtext = []
        for vp in sorted(vfs.index()):
            if vp.startswith("scripts/") and vp.endswith(".shader"):
                for k in range(len(vfs.index()[vp])):
                    _shtext.append(vfs.read(vp, k).decode("latin-1", "ignore"))
    for t in reversed(_shtext):                      # the last stock definition wins, as in the engine's load order
        m = re.search(r"(?im)^[ \t]*%s[ \t\r]*(?://[^\n]*)?\n\s*\{" % re.escape(name), t)
        if not m:
            continue
        i, depth, j = m.end() - 1, 0, m.end() - 1
        while j < len(t):
            depth += {"{": 1, "}": -1}.get(t[j], 0)
            if depth == 0:
                break
            j += 1
        return t[i:j + 1]
    return None


def lit_shader(orig):
    """hzm_h69_<orig>: the stock shader's first stage (map, blend / alpha, depthwrite, cull) lit by the scene's lights"""
    nm = "hzm_h69_" + re.sub(r"[^A-Za-z0-9_]", "_", orig).lower()
    if nm in SH:
        return nm
    body = stock_shader(orig)
    if body is None:
        raise SystemExit("no stock shader %s" % orig)
    head = [l.strip() for l in body.split("\n") if re.match(r"(?i)\s*(cull|surfaceparm\s+trans|nopicmip|nomipmaps)", l.split("{")[0])
            and not l.strip().startswith("//")]
    # the first stage that maps a real texture ($lightmap / $whiteimage stages are the map's lighting, absent here). A multiply
    # stage (GL_DST_COLOR GL_ZERO) is passed over: that blend draws nothing in the menu scene (in-game test, the poster shadows).
    # An additive stage (a lantern's glass) is emissive: rgbGen identity, not lit.
    stages = re.findall(r"\{([^{}]*)\}", body[body.index("{") + 1:])
    st, emissive = None, False
    for cand in stages:
        mm = re.search(r"(?im)^\s*(?:map|clampmap|animmap)\s+(\S+)", cand)
        bf = re.search(r"(?im)^\s*blendfunc\s+(.*)$", cand)
        bfs = bf.group(1).lower().split("//")[0].split() if bf else []
        if not mm or mm.group(1).startswith("$"):
            continue
        if bfs[:2] == ["gl_dst_color", "gl_zero"] or bfs[:1] == ["filter"]:
            continue
        st, emissive = cand, bfs[:2] in (["gl_one", "gl_one"], ["add"])
        break
    assert st is not None, (orig, body)
    keep = []
    for l in st.split("\n"):
        l = l.split("//")[0].strip()
        if re.match(r"(?i)(map|clampmap|animmap|blendfunc|alphafunc|depthwrite|tcmod)\b", l):
            keep.append(l)
    SH[nm] = "%s\n{\n%s\t{\n%s\n\t\trgbGen %s\n\t}\n}" % (nm, "".join("\t%s\n" % h for h in head), "\n".join("\t\t" + l for l in keep),
                                                         "identity" if emissive else "lightingSpherical")
    return nm


def game_mesh(tik, pos=(0, 0, 0), yaw=0.0, pitch=0.0, roll=0.0, scale=1.0, ground=None, anim="idle", skip=(), top=None):
    """the tik's mesh (posed by its idle frame, scaled by the tik) turned / moved into the room -> [(shader, corners)], lo, hi.
    ground: put the lowest point at this z (the floor, a table top)"""
    m = G.load(tik, anim)
    Rm = rot(yaw, pitch, roll)
    out, allp = [], []
    for s in m["surfaces"]:
        if not s["shader"] or s["name"].lower() in skip:
            continue
        P = (s["pos"] * scale) @ Rm.T
        N = s["nrm"] @ Rm.T
        out.append((lit_shader(s["shader"]), s["tris"], P, N, s["uv"]))
        allp.append(P)
    A = np.vstack(allp)
    off = np.asarray(pos, float).copy()
    if ground is not None:
        off[2] = ground - A[:, 2].min()
    if top is not None:                              # hung: its highest point at this z (a helmet's crown over its peg)
        off[2] = top - A[:, 2].max()
    if pos is not None and (ground is not None or top is not None):
        c_ = (A.min(0) + A.max(0)) / 2                # ...and its footprint centred on pos (x, y), not its origin
        off[0], off[1] = pos[0] - c_[0], pos[1] - c_[1]
    parts = []
    for sh_, T, P, N, UV in out:
        P = P + off
        parts.append((sh_, [[(0, tuple(P[k]), tuple(N[k]), tuple(UV[k])) for k in t] for t in T]))
    return parts, A.min(0) + off, A.max(0) + off


def tag(tik, name, anim="idle"):
    """a bone of a tik in its idle frame, entity space (scaled): (origin, R)"""
    tk = G.read_tik(tik)
    bones, _ = G.read_skd(vfs.read(G._join(tk["path"], tk["skelmodel"])))
    a = tk["anims"].get(anim) or next(iter(tk["anims"].values()))
    BW = G.bone_world(bones, G.read_skc_frame0(vfs.read(G._join(tk["path"], a))))
    for (n, _p), (Rb, t) in zip(bones, BW):
        if n.lower() == name.lower():
            return t * tk["scale"], Rb
    raise KeyError(name)


def yawv(yaw, v):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1]])


SETS = {"home": [], "corner": []}            # the props models: the home-view vignette / the notice-board corner
REPORT = {}


def shift(parts, d):
    d = np.asarray(d, float)
    return [(sh_, [[(c[0], tuple(np.asarray(c[1]) + d), c[2], c[3]) for c in tr] for tr in crs]) for sh_, crs in parts]


def put(group, label, *a, wall_y=None, **k):
    """wall_y: hung on the right-hand wall - pushed out until its back just clears the plaster"""
    parts, lo, hi = game_mesh(*a, **k)
    if wall_y is not None:
        d = np.array([0.0, wall_y + 0.25 - lo[1], 0.0])
        parts, lo, hi = shift(parts, d), lo + d, hi + d
    d = np.array([min(0.0, WBlo - 2.0 - hi[0]), min(0.0, WLlo - 2.0 - hi[1]) + (max(0.0, WRlo + 0.25 - lo[1]) if wall_y is None else 0.0), 0.0])
    if np.abs(d).max() > 0:                          # 2 u clear of the back / left wainscot, never through the right one
        print("  %s: moved %s off the wall" % (label, d.round(2).tolist()))
        parts, lo, hi = shift(parts, d), lo + d, hi + d
    SETS[group] += parts
    REPORT[label] = (lo.round(1).tolist(), hi.round(1).tolist())
    return lo, hi


# ================================================================== 3. THE CARD TABLE (home view, left of the lockers)
# global/cardgame.scr seats an actor 15.4 u off the middle of a table side (the m1l1 card table's tag_actor01), the chair at the
# same spot and angle. Here: the game's plain square wooden table (static square_table, legs at its corners - the m1l1 trestle
# table's X-legs stand at its ends and went through his shins when he sat at an end), the soldier at S facing YAW, three-quarters
# to the camera, the table in front of him.
# (coordinator QA 2026-11-09: facing the home camera, his raised cards hid his face, and the stove behind him read as standing on
# the table. Now he sits 20 deg off the camera's line (his face shows past the cards) at the table scaled to a 0.70 m card table,
# moved forward and left so the stove stands clear to his right on screen, its feet on the floor.)
S = np.array([float(os.environ.get("MP69_SX", "148")), float(os.environ.get("MP69_SY", "118"))])
YAW = float(os.environ.get("MP69_YAW", "165"))
TSC = float(os.environ.get("MP69_TABLESCALE", "0.76"))
t1, _ = tag("models/furniture/cardtable.tik", "tag_actor01")
_ct = game_mesh("models/furniture/cardtable.tik")
GAP = _ct[1][0] - t1[0]                                          # the stock seat-to-edge distance (15.4 u)
TABLE = "models/static/square_table.tik"
_tb = game_mesh(TABLE, scale=TSC)
HALF = (_tb[2][0] - _tb[1][0]) / 2
fwd, left = yawv(YAW, (1, 0)), yawv(YAW, (0, 1))                 # the soldier's forward (to the table) / left
TC = S + fwd * (HALF + GAP)                                      # the table's centre
fz = floor_z(*S)
lo_, hi_ = put("home", "table", TABLE, (TC[0], TC[1], fz), YAW, scale=TSC, ground=fz)
put("home", "chair", "models/furniture/cardchair.tik", (S[0], S[1], fz), YAW)
TOP = float(hi_[2])                                              # (its top is flat at its highest point)
print("table top %.2f centre %s half %.1f" % (TOP, TC.round(1), HALF))


def on_table(dx, dy):
    """a point on the table top: dx along the soldier's forward from the table centre, dy to his left"""
    p = TC + fwd * dx + left * dy
    return (p[0], p[1], TOP)


# his patience spread just in front of him, across the table; the rest round it, clear of one another
put("home", "cards", "models/miscobj/cardpile.tik", on_table(-10, 0), YAW + 90, ground=TOP + 0.05)
put("home", "mug1", "models/static/metal_mug.tik", on_table(-15, -16), YAW + 40, ground=TOP)
put("home", "mug2", "models/static/metal_mug.tik", on_table(6, 15), YAW + 160, ground=TOP)
put("home", "saucer", "models/static/whiteplate.tik", on_table(-15, 15), 0, scale=0.42, ground=TOP)
sc = on_table(-15, 15)
put("home", "cigarette", "models/items/cigarette.tik", (sc[0], sc[1], 0), YAW + 70, ground=TOP + 0.65)
put("home", "lantern", "models/items/af_p_lantern.tik", on_table(4, -14), YAW, roll=90, ground=TOP)      # (its mesh lies along y: stood up)
LANTERN = np.array(on_table(4, -14)) + np.array([0, 0, 11.0])
# the Garand along the far edge, lying on its side (rolled 90 deg), butt and muzzle a hand's width over the ends as a rifle on a
# small table does (corner to corner it pointed at the home camera and read as a stub)
put("home", "garand", "models/weapons/m1_garand.tik", on_table(17, 0), YAW + 90, roll=90, ground=TOP)

# ================================================================== 4a. THE STOVE in the back-left corner, its flue to the ceiling
STV = np.array([float(os.environ.get("MP69_STX", "266")), float(os.environ.get("MP69_STY", "130"))])
SYAW = float(os.environ.get("MP69_STYAW", "-135"))
slo, shi = put("home", "stove", "models/static/bunkerstove.tik", (STV[0], STV[1], 0), SYAW, ground=floor_z(*STV))
# the flue: a 6-inch pipe from the stove's top-centre straight up into the ceiling, a collar at the top
STOVE_C = (slo + shi) / 2
CEIL = 100.0 + ray((STOVE_C[0], STOVE_C[1], 100.0), (0, 0, 1))
pipe_c = np.array([STOVE_C[0], STOVE_C[1]]) + yawv(SYAW, (-float(os.environ.get("MP69_FLUE", "-8")), 0))
st_img = Image.open(io.BytesIO(vfs.read("textures/models/items/bunkerstove.tga"))).convert("RGB")
# the pipe's metal: the stove texture's plainest dark patch (the lowest local variance) - the game's own iron
sa = np.asarray(st_img, np.float32)
best = None
for yy in range(0, 240, 8):
    for xx in range(0, 240, 8):
        blk = sa[yy:yy + 16, xx:xx + 16]
        sc_ = blk.std() + abs(blk.mean() - 70) * 0.3
        if best is None or sc_ < best[0]:
            best = (sc_, xx, yy)
_, bx, by_ = best
PIPE_UV = (bx / 256, 1 - (by_ + 16) / 256, (bx + 16) / 256, 1 - by_ / 256)


def cylinder(c, r, z0, z1, n=14, uv=PIPE_UV):
    out = []
    u0, v0, u1, v1 = uv
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        p = [np.array([c[0] + r * math.cos(a), c[1] + r * math.sin(a), z]) for a, z in ((a0, z0), (a1, z0), (a1, z1), (a0, z1))]
        uu = [(u0 + (u1 - u0) * k / n, v0), (u0 + (u1 - u0) * (k + 1) / n, v0), (u0 + (u1 - u0) * (k + 1) / n, v1), (u0 + (u1 - u0) * k / n, v1)]
        # outward faces: winding as quad() (right x up = outward)
        for a, b, d in ((0, 1, 2), (0, 2, 3)):
            t = tri([p[a], p[b], p[d]], [uu[a], uu[b], uu[d]])
            if t:
                out.append(t)
    return out


pipe_sh = lit_shader("bunkerstove")
# (coordinator QA 2026-11-09 round 2: a flue to the ceiling crossed the UNITED poster from the home camera wherever the stove stood
# clear of the soldier.) The pipe rises a hand's width off the stove top and turns into the back wainscot - a chimney thimble -
# below the poster and the dado rail.
ELBOW_Z = shi[2] + 3.0


def cyl_x(cy, cz, r, x0, x1, n=14):
    """a pipe along +x from x0 to x1 at (cy, cz): cylinder() about z, turned by the rotation (x, y, z) -> (z, y, -x)"""
    out = []
    for tr in cylinder((0.0, 0.0), r, 0.0, x1 - x0, n):
        out.append([(c[0], (x0 + c[1][2], cy + c[1][1], cz - c[1][0]), (c[2][2], c[2][1], -c[2][0]), c[3]) for c in tr])
    return out


SETS["home"].append((pipe_sh, cylinder(pipe_c, 3.9, shi[2] - 1.5, ELBOW_Z + 3.9)))
SETS["home"].append((pipe_sh, cylinder(pipe_c, 4.6, shi[2] - 1.5, shi[2] + 2.5)))      # the collar on the stove
SETS["home"].append((pipe_sh, cyl_x(pipe_c[1], ELBOW_Z, 3.9, pipe_c[0] - 3.9, WBlo + 0.5)))
SETS["home"].append((pipe_sh, cyl_x(pipe_c[1], ELBOW_Z, 5.0, WBlo - 1.2, WBlo + 0.5)))   # the thimble collar at the wall
assert ELBOW_Z + 5.0 < 62.0, ELBOW_Z      # under the poster (its foot at z 62.7) and at the dado rail
STOVE_C = (slo + shi) / 2
_sm = game_mesh("models/static/bunkerstove.tik")
_half = (_sm[2][0] - _sm[1][0]) / 2                  # its local x half-depth: the door face is at +x
STOVE_FIRE = np.array([STOVE_C[0], STOVE_C[1], slo[2] + float(os.environ.get("MP69_FIREZ", "12.0"))]) + np.append(yawv(SYAW, (_half, 0)), 0)

# ================================================================== 4b. THE FOOTLOCKER under the AMERICANS poster (left wall)
# on the back wall under the SERVICE RECORD board, its back to the wainscot: in the home view, below the board's hit box and clear
# of the door's and the game-type board's. (Under the notice board's peg rail it was never seen: the board view does not reach the
# floor there, and that front corner opens on the void - the room has no front wall behind the home camera.)
FLY = float(os.environ.get("MP69_FLY", "-88"))
flo, fhi = put("home", "footlocker", "models/static/trunk.tik", (WBlo - 16.0, FLY, 0), float(os.environ.get("MP69_FLYAW", "180")),
               ground=0.0)
_d = (WBlo - 1.0) - fhi[0]          # its back to the wainscot, clear of the baseboard (0.5 u proud of it below z 8)
SETS["home"][-1] = (SETS["home"][-1][0], [[(c[0], (c[1][0] + _d, c[1][1], c[1][2]), c[2], c[3]) for c in tr] for tr in SETS["home"][-1][1]])
REPORT["footlocker"] = ((flo + [_d, 0, 0]).round(1).tolist(), (fhi + [_d, 0, 0]).round(1).tolist())

# ================================================================== 2. THE RADIO on the footlocker (coordinator QA: on its crate in the
# middle of the floor it read as dropped there and blocked the room; on the cabinet it would sit inside the game-type board's hit
# box). The footlocker's top, under the SERVICE RECORD board: its hit box clears the board's, the door's and the game board's.
FL_TOP = float(fhi[2])
RC = np.array([(flo[0] + fhi[0]) / 2 + _d, (flo[1] + fhi[1]) / 2 + float(os.environ.get("MP69_RDY", "4"))])
RY = float(os.environ.get("MP69_RYAW", "172"))
rparts, rlo, rhi = game_mesh("models/static/static_radio2.tik", (RC[0], RC[1], 0), RY, ground=FL_TOP)
RADIO_C = ((rlo + rhi) / 2).round(1)
REPORT["radio"] = (rlo.round(1).tolist(), rhi.round(1).tolist())

# ================================================================== 1. THE NOTICE BOARD (right wall, front half) + its corner
BX = float(os.environ.get("MP69_BX", "45"))
# the SERVICE RECORD board's frame in the hub bake: back wall, face at x 282, y -114.2..-59.1, z 63..102.4, plaque above
FR = []
bgtik = zb.read("models/menu/hub_bg1.tik").decode("latin-1") + zb.read("models/menu/hub_bg2.tik").decode("latin-1")
for n in ("hub_bg1", "hub_bg2"):
    k = R.read_skd(zb.read("models/menu/%s.skd" % n))
    for s in k["surfaces"]:
        V, T = s["verts"], s["tris"]
        if not len(T):
            continue
        P = np.array([v[3] for v in V])
        c = P[T].mean(1)
        inb = (c[:, 0] > 279.5) & (c[:, 1] > -118.5) & (c[:, 1] < -54.5) & (c[:, 2] > 59.5) & (c[:, 2] < 113.5)
        for t_ in T[inb]:
            FR.append([(0, tuple(V[q][3]), tuple(V[q][0]), tuple(V[q][1])) for q in t_])
assert 300 < len(FR) < 2000, len(FR)
# (coordinator QA: the copied frame's top and bottom rails were half dark, half light with a hard split at the middle - the back
# wall's bake lit the two halves differently. Keep the brighter half, mirror it across the board's centre line y -86.6.)
_bg = np.asarray(Image.open(io.BytesIO(zb.read("textures/menu/hzm_hub_bg.jpg"))).convert("L"), np.float32)
YC_SR = -86.6


def _lum(tr):
    u = np.mean([c[3][0] for c in tr]) % 1.0
    v = np.mean([c[3][1] for c in tr]) % 1.0
    return _bg[int(v * (_bg.shape[0] - 1)), int(u * (_bg.shape[1] - 1))]


_rail = [tr for tr in FR if min(c[1][2] for c in tr) > 104.0 or max(c[1][2] for c in tr) < 65.0]
_side = lambda tr: np.mean([c[1][1] for c in tr]) > YC_SR  # noqa: E731
_lp = np.mean([_lum(t) for t in _rail if _side(t)])
_lm = np.mean([_lum(t) for t in _rail if not _side(t)])
_keep_plus = _lp >= _lm
_half = [tr for tr in FR if _side(tr) == _keep_plus]
FR = _half + [[(c[0], (c[1][0], 2 * YC_SR - c[1][1], c[1][2]), (c[2][0], -c[2][1], c[2][2]), c[3]) for c in reversed(tr)] for tr in _half]
print("board frame: rail halves lit %.0f / %.0f - kept the %s half, mirrored" % (_lp, _lm, "+y" if _keep_plus else "-y"))
C_SR = np.array([WB, -86.6, 0.0])
C_NB = np.array([BX, WR, 0.0])


def to_right(p):
    d = np.asarray(p, float) - C_SR
    return C_NB + np.array([d[1], -d[0], d[2]])          # yaw -90: back wall (normal -x) -> right wall (normal +y)


def to_right_n(n):
    return (n[1], -n[0], n[2])


board = [("hzm_hub_bg", [[(c[0], tuple(to_right(c[1])), to_right_n(c[2]), c[3]) for c in tr] for tr in FR])]
FACE = dict(c=to_right((282.0, -86.65, 82.7)), w=55.1, h=39.4)
PLQ = dict(c=to_right((282.5, -86.6, 108.55)), w=44.6, h=6.5)
RIGHT = np.array([1.0, 0, 0])      # along the right wall, to a viewer facing it: +x is to the LEFT; the face's u runs -x
UP = np.array([0, 0, 1.0])
INW = np.array([0, 1.0, 0])

F = r"C:\Windows\Fonts"


def font(name, size):
    return ImageFont.truetype(os.path.join(F, name), size)


OD = (84, 88, 58)
INK = (40, 34, 28)


def noise_rgb(w, h, base, amp, blur, seed=3):
    a = np.random.default_rng(seed).normal(0, 1, (h // 4 + 1, w // 4 + 1)).astype(np.float32)
    im = Image.fromarray(np.uint8(np.clip(128 + a * 40, 0, 255))).resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(blur))
    n = (np.asarray(im, np.float32) - 128) / 40.0
    g = np.random.default_rng(seed + 2).normal(0, 1, (h, w)).astype(np.float32) * 0.35
    return np.clip(np.array(base, np.float32)[None, None, :] + (n + g)[..., None] * amp, 0, 255)


def lit(a, k=LIGHT):
    """painted room light: the plaster level, a gentle top-down falloff"""
    h = a.shape[0]
    f = k * (1.06 - 0.14 * (np.arange(h) / h))[:, None, None]
    return Image.fromarray(np.uint8(np.clip(a * f, 0, 255)))


# the face: olive-drab painted board (gen_srboard.py's paint), the pin holes of older notices
fw, fh = 1024, 732
face = noise_rgb(fw, fh, OD, 7, 2.2)
holes = Image.fromarray(np.uint8(face))
dh = ImageDraw.Draw(holes)
for _ in range(26):
    x, y = rng.integers(30, fw - 30), rng.integers(30, fh - 30)
    dh.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(52, 54, 36))
lit(np.asarray(holes, np.float32)).save(os.path.join(tdir, "hzm_hub69_face.jpg"), quality=92)
# the plaque: the hub's own plaque style (stencil, cream on dark wood) - the SR board's plaque texture, re-lettered
plq = Image.open(io.BytesIO(zb.read("textures/menu/hzm_hub_q_nb_plaque_face.jpg"))).convert("RGB")
pa = np.asarray(plq, np.float32)
wood = pa[22:138, 12:60].mean((0, 1))
inner = noise_rgb(1024 - 60, 160 - 44, wood, 6, 1.5, seed=9)
pa2 = pa.copy()
pa2[22:138, 30:994] = inner[:, :964]
plq2 = Image.fromarray(np.uint8(np.clip(pa2, 0, 255)))
d = ImageDraw.Draw(plq2)
f_ = font("STENCIL.TTF", 96)
txt = "NOTICES"
tw = d.textlength(txt, font=f_)
d.text(((1024 - tw) / 2, 22), txt, font=f_, fill=(236, 226, 190))
plq2.save(os.path.join(tdir, "hzm_hub69_plaque.jpg"), quality=92)

SH["hzm_hub69_face"] = "hzm_hub69_face\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tclampmap textures/menu/hzm_hub69_face.jpg\n\t\trgbGen identity\n\t}\n}"
SH["hzm_hub69_plaque"] = ("hzm_hub69_plaque\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tclampmap textures/menu/hzm_hub69_plaque.jpg\n\t\trgbGen identity\n\t}\n"
                          "\t{\n\t\tclampmap textures/menu/hzm_hub_q_nb_plaque_face_lm.jpg\n\t\tblendFunc filter\n\t\trgbGen identity\n\t}\n}")
# the face's u runs along -x on this wall (a viewer facing -y has +x on the left): right vector = -x
board.append(("hzm_hub69_face", quad(FACE["c"] + INW * 0.0, -RIGHT, UP, FACE["w"], FACE["h"])))
board.append(("hzm_hub69_plaque", quad(PLQ["c"], -RIGHT, UP, PLQ["w"], PLQ["h"])))

# ---- the three notices: typed sheets in the SR board's style (cream paper, Stencil / Georgia heads, Courier body), pinned
NOTES = [
    ("daily", "ORDERS OF THE DAY", "HEADQUARTERS",
     ["Five orders, the same", "for every man:", "two easy, two medium,", "one hard.", "",
      "Easy      400 XP", "Medium    750 XP", "Hard     1250 XP", "",
      "All five: Mentioned in", "Dispatches, +1500 XP.", "", "New orders 1000 Zulu."]),
    ("record", "SERVICE RECORD", "CHALLENGES AND MEDALS",
     ["[ ] Rifles", "[ ] Snipers", "[ ] Submachine guns", "[ ] Pistols", "[ ] Support weapons", "[ ] Combat",
      "[ ] Fireteam", "[ ] Vehicles", "[ ] Campaign", "[ ] Discovery"]),
    ("ranks", "PROMOTIONS", "MULTIPLAYER",
     ["Rank is shared", "with Co-op.", "", "Rank", "Prestige", "Total XP", "XP to next rank", "",
      "Your rank and your", "challenges both", "unlock weapons."]),
]
NW, NH = 16.6, 21.6                        # the sheet (units): 32 x 41 cm
PW, PH = 512, 666
centres = [(-18.2, 0.8, -1.4), (0.0, -0.4, 0.9), (18.2, 0.5, -0.7)]     # along the face (to the viewer's right), up, tilt deg
NOTE_INFO = []


def paper(title, sub, lines, seed):
    a = noise_rgb(PW, PH, (232, 223, 196), 4, 1.2, seed=seed)
    im = Image.fromarray(np.uint8(a))
    d = ImageDraw.Draw(im)
    d.rectangle((3, 3, PW - 4, PH - 4), outline=(198, 186, 156), width=2)
    fs = font("georgiab.ttf", 22)
    tw = d.textlength(sub, font=fs)
    d.text(((PW - tw) / 2, 34), sub, font=fs, fill=INK)
    size = 52
    while True:
        ft = font("STENCIL.TTF", size)
        tw = d.textlength(title, font=ft)
        if tw < PW - 70:
            break
        size -= 2
    d.text(((PW - tw) / 2, 66), title, font=ft, fill=INK)
    d.line((40, 76 + size + 8, PW - 40, 76 + size + 8), fill=INK, width=3)
    fb = font("courbd.ttf", 27)
    y = 76 + size + 30
    for l in lines:
        if l.startswith("[ ] "):
            d.rectangle((46, y + 5, 66, y + 25), outline=INK, width=3)
            d.text((82, y), l[4:], font=fb, fill=INK)
        else:
            d.text((44, y), l, font=fb, fill=INK)
        y += 36
    return np.asarray(im, np.float32)


def aged(a, seed):
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    e = np.minimum.reduce([xx, yy, w - 1 - xx, h - 1 - yy]).astype(np.float32)
    wear = np.clip(e / (0.03 * w), 0, 1) ** 0.6
    a = a * (0.86 + 0.14 * wear[..., None]) + (1 - wear[..., None]) * np.array([10, 8, 4])
    dust = np.asarray(Image.fromarray((np.random.default_rng(seed).random((h // 8, w // 8)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255
    return a * (0.97 + 0.04 * dust[..., None])


NOTE_PARTS = {}
for i, (key, title, sub, lines) in enumerate(NOTES):
    a = aged(paper(title, sub, lines, 20 + i), 30 + i)
    lit(a).save(os.path.join(tdir, "hzm_hub69_n_%s.jpg" % key), quality=93)
    # the lit copy: the lamp turned up on it - brighter and warmer (the attic projector's lit copy: atlas x1.9 + warm lift)
    lit(a * np.array([1.0, 0.97, 0.88]), LIGHT * 1.45).save(os.path.join(tdir, "hzm_hub69_n_%s_lit.jpg" % key), quality=93)
    for sfx in ("", "_lit"):
        SH["hzm_hub69_n_%s%s" % (key, sfx)] = ("hzm_hub69_n_%s%s\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tclampmap textures/menu/hzm_hub69_n_%s%s.jpg\n"
                                             "\t\trgbGen identity\n\t}\n}" % (key, sfx, key, sfx))
    along, upo, tilt = centres[i]
    c = FACE["c"] + (-RIGHT) * along + UP * upo + INW * 0.18
    ca, sa_ = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    r2, u2 = (-RIGHT) * ca + UP * sa_, UP * ca - (-RIGHT) * sa_
    # a slightly curled sheet: 0.18 u off the board, the lower corners lifting
    nu, nv = 6, 8
    Pg, UVg = [], []
    for a_ in range(nu + 1):
        for b_ in range(nv + 1):
            x, y = a_ / nu - 0.5, b_ / nv - 0.5
            cw = (abs(2 * x) ** 4) * (abs(2 * y) ** 4) * (1.0 if y < 0 else 0.3)
            Pg.append(c + INW * (0.6 * cw) + r2 * x * NW + u2 * y * NH)
            UVg.append((a_ / nu, b_ / nv))
    crs = []
    K = lambda a_, b_: a_ * (nv + 1) + b_  # noqa: E731
    for a_ in range(nu):
        for b_ in range(nv):
            q4 = (K(a_, b_), K(a_ + 1, b_), K(a_ + 1, b_ + 1), K(a_, b_ + 1))
            for t3 in ((q4[0], q4[1], q4[2]), (q4[0], q4[2], q4[3])):
                t = tri([Pg[k] for k in t3], [UVg[k] for k in t3])
                if t:
                    crs.append(t)
    # the two pins (red heads, the SR board's): small domes at the top corners
    pins = []
    for sx in (-1, 1):
        q = c + r2 * sx * (NW / 2 - 1.4) + u2 * (NH / 2 - 1.4) + INW * 0.25
        ring = [q + (r2 * math.cos(t_) + u2 * math.sin(t_)) * 0.42 for t_ in np.linspace(0, 2 * math.pi, 10)]
        top = q + INW * 0.45
        for k in range(9):
            t = tri([ring[k], ring[k + 1], top], [(0.2, 0.2), (0.8, 0.2), (0.5, 0.8)])
            if t:
                pins.append(t)
    NOTE_PARTS[key] = (crs, pins)
    NOTE_INFO.append(dict(key=key, title=title, centre=c.round(2).tolist(), w=NW, h=NH))
Image.new("RGB", (16, 16), (176, 40, 34)).save(os.path.join(tdir, "hzm_hub69_pin.jpg"), quality=95)
Image.new("RGB", (16, 16), (236, 74, 60)).save(os.path.join(tdir, "hzm_hub69_pin_lit.jpg"), quality=95)
for sfx in ("", "_lit"):
    SH["hzm_hub69_pin%s" % sfx] = "hzm_hub69_pin%s\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_hub69_pin%s.jpg\n\t\trgbGen identity\n\t}\n}" % (sfx, sfx)
for key, (crs, pins) in NOTE_PARTS.items():
    write_model("hzm_hub69_n_%s" % key, [("hzm_hub69_n_%s" % key, crs), ("hzm_hub69_pin", pins)])
    write_model("hzm_hub69_n_%s_lit" % key, [("hzm_hub69_n_%s_lit" % key, crs), ("hzm_hub69_pin_lit", pins)])
# a soft shadow behind the frame on the wall (the hub's bake never saw a board here). NOT the posters' multiply (GL_DST_COLOR
# GL_ZERO): an in-game test quad showed that blend draws nothing in the menu scene, while a plain alpha blend (no sort keyword)
# does - so a black sheet whose alpha is the shadow
def shadow_tga(name, inner, blur, strength):
    a = Image.new("L", (128, 128), 0)
    ImageDraw.Draw(a).rounded_rectangle(inner, 10, fill=int(255 * strength))
    a = a.filter(ImageFilter.GaussianBlur(blur))
    Image.merge("RGBA", (Image.new("L", (128, 128), 0),) * 3 + (a,)).save(os.path.join(tdir, name + ".tga"))
    SH[name] = ("%s\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tmap textures/menu/%s.tga\n\t\tblendFunc blend\n\t\trgbGen identity\n\t}\n}"
                % (name, name))


shadow_tga("hzm_hub69_shadow", (16, 16, 112, 112), 6, 0.30)
FPTS = np.array([c[1] for tr in board[0][1] for c in tr])
flo_, fhi_ = FPTS.min(0), FPTS.max(0)
sc_c = np.array([(flo_[0] + fhi_[0]) / 2 + 0.4, WR + 0.15, (flo_[2] + fhi_[2]) / 2 - 0.9])
board.append(("hzm_hub69_shadow", quad(sc_c, -RIGHT, UP, (fhi_[0] - flo_[0]) + 6.5, (fhi_[2] - flo_[2]) + 6.5)))
write_model("hzm_hub69_board", board)
REPORT["board"] = (flo_.round(1).tolist(), fhi_.round(1).tolist())

# ---- the corner under / beside it: a bench along the wall, a peg rail with two helmets, a pack and a canteen
BENCH_X = float(os.environ.get("MP69_BENCHX", "-43"))
blo, bhi = put("corner", "bench", "models/static/bunkerbench.tik", (BENCH_X, WRlo + 14.0, 0), 90.0, ground=0.0)
_d = (WRlo + 1.0) - blo[1]            # against the wainscot
SETS["corner"][-1] = (SETS["corner"][-1][0], [[(c[0], (c[1][0], c[1][1] + _d, c[1][2]), c[2], c[3]) for c in tr] for tr in SETS["corner"][-1][1]])
REPORT["bench"] = ((blo + [0, _d, 0]).round(1).tolist(), (bhi + [0, _d, 0]).round(1).tolist())
BENCH_TOP = bhi[2]
# the peg rail: a plank of the game's work-table wood on the plaster above the dado, three turned pegs
RAIL_X0, RAIL_X1, RAIL_Z = float(os.environ.get("MP69_RAILX0", "-62")), float(os.environ.get("MP69_RAILX1", "6")), 96.0
wt_sh = lit_shader("static_bunkerbench")
# (a generated quad's winding is the posters' - drawn with cull none; the stock bench shader culls, which hid the plank's face)
SH["hzm_h69_rail"] = SH[wt_sh].replace(wt_sh, "hzm_h69_rail", 1).replace("{\n\t{", "{\n\tcull none\n\t{", 1)
wt_sh = "hzm_h69_rail"
rail = []
rc_ = np.array([(RAIL_X0 + RAIL_X1) / 2, WR + 0.9, RAIL_Z])
rail += quad(rc_ + INW * 0.9, -RIGHT, UP, RAIL_X1 - RAIL_X0, 7.0, (0.05, 0.40, 0.95, 0.50))
rail += quad(rc_ + UP * 3.5, -RIGHT, -INW, RAIL_X1 - RAIL_X0, 1.8, (0.05, 0.40, 0.95, 0.42))
rail += quad(rc_ - UP * 3.5, -RIGHT, INW, RAIL_X1 - RAIL_X0, 1.8, (0.05, 0.40, 0.95, 0.42))
for xe, sgn in ((RAIL_X0, 1), (RAIL_X1, -1)):
    rail += quad(np.array([xe, WR + 0.9, RAIL_Z]), INW * sgn, UP, 1.8, 7.0, (0.1, 0.4, 0.15, 0.45))
PEGS = []
for k in range(3):
    px = RAIL_X0 + (RAIL_X1 - RAIL_X0) * (k + 0.5) / 3
    PEGS.append(np.array([px, WR + 1.8, RAIL_Z]))
    for a0 in range(8):
        aa, ab = 2 * math.pi * a0 / 8, 2 * math.pi * (a0 + 1) / 8
        ring = lambda a, y: np.array([px + 0.75 * math.cos(a), y, RAIL_Z + 0.75 * math.sin(a)])  # noqa: E731
        p = [ring(aa, WR + 1.8), ring(ab, WR + 1.8), ring(ab, WR + 7.0), ring(aa, WR + 7.0)]
        for t3 in ((0, 2, 1), (0, 3, 2)):
            t = tri([p[q] for q in t3], [(0.3, 0.4), (0.35, 0.45), (0.3, 0.45)])
            if t:
                rail.append(t)
SETS["corner"].append((wt_sh, rail))
# the plaster never saw the rail: a soft shadow (shadow_tga), offset down, behind the rail and its load
RAIL_SH = ("hzm_hub69_shadow", quad(np.array([(RAIL_X0 + RAIL_X1) / 2 + 0.6, WR + 0.15, RAIL_Z - 5.0]), -RIGHT, UP, RAIL_X1 - RAIL_X0 + 6.0, 21.0))
# peg 1: a helmet hung by its chinstrap - crown out, tipped forward off the peg; peg 2: the pack; peg 3: a helmet and the canteen
# a helmet hangs on its peg crown up, the peg inside it under the crown, tipped a little; the pack and the canteen flat to the wall
put("corner", "helmet1", "models/static/static_ushelmet_private.tik", (PEGS[0][0], PEGS[0][1] + 4.0, 0), float(os.environ.get("MP69_HYAW", "0")),
    roll=float(os.environ.get("MP69_HROLL", "-14")), top=PEGS[0][2] + 1.6, wall_y=WR)
put("corner", "pack", "models/equipment/usbackpack.tik", (PEGS[1][0], PEGS[1][1], 0), float(os.environ.get("MP69_PYAW", "0")), top=PEGS[1][2] + 2.0, wall_y=WR)
put("corner", "helmet2", "models/static/static_us-helmet_29th.tik", (PEGS[2][0], PEGS[2][1] + 4.0, 0), float(os.environ.get("MP69_HYAW", "0")) + 8,
    roll=float(os.environ.get("MP69_HROLL", "-14")), top=PEGS[2][2] + 1.6, wall_y=WR)

# ================================================================== the models
write_model("hzm_hub69_radio", rparts)
# the radio's lit copy: its own texture with the dial window glowing (the game's radio2.tga, the window region warmed and lit)
r2 = Image.open(io.BytesIO(vfs.read("textures/models/submodels/radio2.tga"))).convert("RGBA")
ra = np.asarray(r2, np.float32)
win = np.zeros(ra.shape[:2], np.float32)
H2, W2 = ra.shape[:2]
y0, y1, x0, x1 = int(0.045 * H2), int(0.155 * H2), int(0.24 * W2), int(0.80 * W2)        # the dial window (radio2.tga, top panel)
win[y0:y1, x0:x1] = 1.0
win = np.asarray(Image.fromarray(np.uint8(win * 255)).filter(ImageFilter.GaussianBlur(6)), np.float32) / 255
rl = ra.copy()
rl[..., :3] = np.clip(ra[..., :3] * (1 + win[..., None] * np.array([0.85, 0.62, 0.20])) + win[..., None] * np.array([46, 30, 4]), 0, 255)
Image.fromarray(np.uint8(rl)).save(os.path.join(tdir, "hzm_hub69_radio_lit.tga"))
rsh = rparts[0][0]
SH["hzm_hub69_radio_lit"] = SH[rsh].replace(rsh, "hzm_hub69_radio_lit", 1).replace("textures/models/submodels/radio2.tga", "textures/menu/hzm_hub69_radio_lit.tga")
write_model("hzm_hub69_radio_lit", [("hzm_hub69_radio_lit", crs) for _sh, crs in rparts])

# ---- glows: the stove's fire door and the lantern - additive soft sprites, the stove's flickering (shader noise), never lit by
# anything (no depth write); a warm spill on the floor in front of the stove
g = np.zeros((128, 128), np.float32)
yy, xx = np.mgrid[0:128, 0:128]
rr = np.hypot(xx - 63.5, yy - 63.5) / 63.5
g = np.clip(1 - rr, 0, 1) ** 2.2
Image.fromarray(np.uint8(np.stack([g * 255, g * 190, g * 110], -1))).save(os.path.join(tdir, "hzm_hub69_glow.jpg"), quality=95)
SH["hzm_hub69_stoveglow"] = ("hzm_hub69_stoveglow\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_hub69_glow.jpg\n"
                             "\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave noise 0.55 0.18 0 2.2\n\t}\n}")
SH["hzm_hub69_lampglow"] = ("hzm_hub69_lampglow\n{\n\tnopicmip\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_hub69_glow.jpg\n"
                            "\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave noise 0.30 0.04 0 1.3\n\t}\n}")
fwd_s = np.append(yawv(SYAW, (1, 0)), 0)           # the stove's front (its +x: the door)
side_s = np.append(yawv(SYAW, (0, 1)), 0)
glows = [("hzm_hub69_stoveglow", quad(STOVE_FIRE + fwd_s * 0.8, side_s, UP, 13, 10)),
         ("hzm_hub69_stoveglow", quad(np.array([STOVE_FIRE[0], STOVE_FIRE[1], 0.25]) + fwd_s * 12, side_s, fwd_s, 30, 22))]
cam_home = np.array([-70.9, 15.8, 86.6])
to_cam = cam_home - LANTERN
to_cam[2] = 0
to_cam /= np.linalg.norm(to_cam)
lr = np.cross(UP, to_cam)
glows.append(("hzm_hub69_lampglow", quad(LANTERN + to_cam * 6.5, -lr, UP, 11, 11)))
corner_fx = [RAIL_SH]
# contact shadows on the floor (the bake never saw these props): a soft dark patch under each floor prop, darker in the middle,
# never past a wall (the alpha-blended black of shadow_tga)
# (its dark core is the middle 60 % of the patch: a patch must be ~1.9 x the footprint for the core to show past the prop - the
# first sizes, 1.25-1.35 x, hid the whole core under the props and read as no shadow at all)
shadow_tga("hzm_hub69_fshadow", (26, 26, 102, 102), 9, 0.50)


def fshadow(c, ax, w, d):
    ax = np.append(np.asarray(ax, float) / np.linalg.norm(ax), 0)
    side = np.cross(UP, ax)
    return ("hzm_hub69_fshadow", quad(np.array([c[0], c[1], floor_z(c[0], c[1]) + 0.25]), ax, side, w, d))


def box_shadow(lo, hi, pad=1.9):
    c = (np.asarray(lo) + np.asarray(hi)) / 2
    return fshadow(c, (1, 0), (hi[0] - lo[0]) * pad, (hi[1] - lo[1]) * pad)


glows.append(box_shadow(slo, shi, 1.8))
glows.append(fshadow(TC, fwd, 2 * HALF * 1.9, 2 * HALF * 1.9))               # the table
glows.append(fshadow(S - fwd * 3.0, fwd, 52.0, 52.0))                        # the chair and his feet
_bl, _bh = np.array(REPORT["bench"][0]), np.array(REPORT["bench"][1])
corner_fx.append(box_shadow(_bl, _bh, 1.5))
_fl, _fh = np.array(REPORT["footlocker"][0]), np.array(REPORT["footlocker"][1])
glows.append(box_shadow(_fl, _fh, 1.8))
# the glows and the shadows: a model of their own, placed without an anim (no actor exposure pull-down on them). In-game test quads
# (2026-11-09) settled one thing: a multiply (GL_DST_COLOR GL_ZERO) draws nothing in the menu scene, a plain alpha blend does. Several
# "the shadows do not draw" reads before that were the patches' dark cores hidden under the props - judge such changes from a
# DIFF of two stills, not by eye.
n1 = write_model("hzm_hub69_props", SETS["home"])
n2 = write_model("hzm_hub69_corner", SETS["corner"])
write_model("hzm_hub69_fx", glows + corner_fx)

# ------------------------------------------------------------------ the soldier (a staged actor) - models/human/hzm_menu/hub_gi_menu.tik
# (coordinator QA 2026-11-10: the m1l1 card idles - cardidle01 / 02 and the pickup - hold the hand up at the face, so from the home
# view he read as drinking or using binoculars. Ten table / card clips rendered side by side, three time samples each: the m1l1
# "give me your king" clip (actor_m1l1_11) keeps the cards at chest height, the face clear throughout. It loops alone and silent -
# its line is a client sound in the stock table.tik, not in this one.)
open(os.path.join(adir, "hub_gi_menu.tik"), "w", newline="\n").write("""TIKI
setup
{
	scale 0.52
	path models/human/allied_army_soldier
	skelmodel usarmy.skd
	surface ranger_pants shader hbtpants
	surface us_top shader hbt_jacket
	surface armband shader hbt_29th_pfc
	surface us_top_c shader hbt_jacket_c
	path models/human/heads
	skelmodel head2.skd
	surface head shader us_thomas
	path models/human/hands
	skelmodel hand.skd
	surface hand shader handsnew
	scale 0.52
	path models/human/protoanimations
	radius 20
}

init
{
	server
	{
		classname Actor
	}
}

animations
{
	$path models/human/animation
	idle scripted/table/actor_m1l1_11.skc
	cardA scripted/table/actor_m1l1_11.skc
}
""")

# ------------------------------------------------------------------ the crackle: 0.39 s of the game's radio noise, softened
wv = wave.open(io.BytesIO(vfs.read("sound/mechanics/mec_radionoise_11.wav")))
sr_, nch, sw = wv.getframerate(), wv.getnchannels(), wv.getsampwidth()
a = np.frombuffer(wv.readframes(wv.getnframes()), "<i2").astype(np.float32).reshape(-1, nch).mean(1)
a *= 10 ** (-9 / 20)
fl = int(0.015 * sr_)
a[:fl] *= np.linspace(0, 1, fl)
a[-fl * 3:] *= np.linspace(1, 0, fl * 3)
with wave.open(os.path.join(sndd, "hzm_radio_tune.wav"), "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(sr_)
    w.writeframes(np.clip(a, -32768, 32767).astype("<i2").tobytes())

open(os.path.join(sdir, "hzm_hub69.shader"), "w", newline="\n").write(
    "// generated by gen_mproom69.py (v1.10.69 MP room props): the game's props lit by the scene's lights, the notice board, glows\n\n"
    + "\n\n".join(SH.values()) + "\n")

# ------------------------------------------------------------------ urc data for patch_mproom69.py
AL = "models/human/hzm_menu/hub_gi_menu.tik"
INFO.update(
    soldier=dict(tik=AL, pos=S.round(1).tolist(), yaw=YAW, z=fz),
    radio=dict(centre=RADIO_C.tolist(), lo=rlo.round(1).tolist(), hi=rhi.round(1).tolist()),
    notices=NOTE_INFO, board=dict(face=FACE["c"].round(2).tolist(), lo=flo_.round(1).tolist(), hi=fhi_.round(1).tolist()),
    stove=dict(fire=STOVE_FIRE.round(1).tolist(), lo=slo.round(1).tolist(), hi=shi.round(1).tolist(), pipe=pipe_c.round(1).tolist(), ceil=CEIL),
    lantern=LANTERN.round(1).tolist(), table=dict(top=TOP, centre=TC.round(1).tolist()), walls=dict(left=WL, right=WR, back=WB),
    report=REPORT)
INFO["lines"] = [
    'scenemodel "models/menu/hzm_hub69_board.tik" 0 0 0 0',
    'scenemodel "models/menu/hzm_hub69_n_daily.tik" 0 0 0 0', 'scenemodel "models/menu/hzm_hub69_n_daily_lit.tik" 0 0 0 0',
    'scenemodel "models/menu/hzm_hub69_n_record.tik" 0 0 0 0', 'scenemodel "models/menu/hzm_hub69_n_record_lit.tik" 0 0 0 0',
    'scenemodel "models/menu/hzm_hub69_n_ranks.tik" 0 0 0 0', 'scenemodel "models/menu/hzm_hub69_n_ranks_lit.tik" 0 0 0 0',
    'scenemodel "models/menu/hzm_hub69_props.tik" 0 0 0 0 "idle"',
    'scenemodel "models/menu/hzm_hub69_corner.tik" 0 0 0 0 "idle"',
    'scenemodel "models/menu/hzm_hub69_radio.tik" 0 0 0 0 "idle"', 'scenemodel "models/menu/hzm_hub69_radio_lit.tik" 0 0 0 0 "idle"',
    'scenemodel "models/menu/hzm_hub69_fx.tik" 0 0 0 0',
    'scenemodel "%s" %.1f %.1f %.1f %.1f "idle" ""' % (AL, S[0], S[1], fz, YAW),
]
json.dump(INFO, open(out_json, "w"), indent=1)
print("props %s, corner %s surfaces; radio at %s; notices %s" % (n1[0], n2[0], RADIO_C.tolist(), [n["centre"] for n in NOTE_INFO]))
for k, v in REPORT.items():
    print("  %-11s %s .. %s" % (k, v[0], v[1]))
