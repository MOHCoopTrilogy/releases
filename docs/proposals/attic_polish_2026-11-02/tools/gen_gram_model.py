"""gen_gram_model.py <out dir> - stock MOHAA props re-written for the attic's Scene3D, plus the gramophone's spinning record.

Scene3D draws a skeletal model in its BIND space at entity scale 1: a stock static prop then lies on its side (its Max export is
stood upright by the .skc bone pose) and is ~1.9x too big (the .tik's `scale 0.52` is not applied).  So each prop's frame-0 bone
pose (parents composed) and its tik scale are baked into the vertices, with one identity bone; uv, surfaces and the stock shaders
are unchanged.  Writes models/menu/hzm_<name>.{skd,skc,tik}.

The phonograph is split in two: the cabinet / tone arm / crank (hzm_gram) and the record (hzm_gram_disc: the dark top disc tris,
re-centred on the spindle) with an `idle` animation of one turn every 1.8 s (33 1/3 rpm), so the record visibly spins under the arm."""
import math, os, re, struct, sys, zipfile
import numpy as np

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
import skx as X  # noqa: E402

out = sys.argv[1]
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest\main"
ZS = [zipfile.ZipFile(os.path.join(GOG, p)) for p in ("Pak0.pk3", "Pak1.pk3", "Pak2.pk3", "Pak3.pk3")]
mdir = os.path.join(out, "models", "menu")
os.makedirs(mdir, exist_ok=True)


LOWER = {}
for _z in ZS:
    for _n in _z.namelist():
        LOWER.setdefault(_n.lower(), (_z, _n))


def rd(n):          # pk3 paths are case-insensitive to the engine (models/static/METAL_MUG/...)
    if n.lower() in LOWER:
        z, real = LOWER[n.lower()]
        return z.read(real)
    raise KeyError(n)


def qmat(qx, qy, qz, qw):     # row-vector convention: p' = p @ R
    return np.array([[1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
                     [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
                     [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)]])


def _wild(shaders, sname):
    """a tik surface pattern such as `surface gun* shader MP40` (the MP40's surfaces are gun1, gun2 ...): first fnmatch hit, any case; also a case-only mismatch"""
    import fnmatch
    for k, v in shaders.items():
        if fnmatch.fnmatch(sname.lower(), k.lower()):      # also a plain name in another case (`surface Clip` for the surface CLIP)
            return v
    return ""


def load(tikpath):
    t = rd(tikpath).decode("latin-1")
    path = re.search(r"\bpath\s+(\S+)", t).group(1)
    skd = re.search(r"\bskelmodel\s+(\S+)", t).group(1)
    scale = float((re.search(r"\bscale\s+([\d.]+)", t) or [0, "1"])[1])
    shaders = dict(re.findall(r"\bsurface\s+(\S+)\s+shader\s+(\S+)", t))
    anim = re.search(r"\bidle\s+(\S+\.skc)", t).group(1)
    d = rd(path + "/" + skd)
    c = rd(path + "/" + anim)
    # bones (name, parent) from the skd bone blocks
    h = struct.unpack_from("<4si64s5i", d, 0)
    nsurf, nbone, ofsB, ofsS = h[3], h[4], h[5], h[6]
    bones, o = [], ofsB
    for b in range(nbone):
        name = d[o:o + 32].split(b"\0")[0].decode()
        par = d[o + 32:o + 64].split(b"\0")[0].decode()
        end = struct.unpack_from("<5i", d, o + 64)[4]
        bones.append((name, par))
        o += end
    # skc v13 frame 0 channel values
    nc, o_ch, nf = struct.unpack_from("<3i", c, 36)
    ov = struct.unpack_from("<i", c, 48 + 44)[0]
    chans = [c[o_ch + 32 * i:o_ch + 32 * i + 32].split(b"\0")[0].decode() for i in range(nc)]
    vals = {chans[i]: struct.unpack_from("<4f", c, ov + 16 * i) for i in range(nc)}
    world = {}

    def pose(i):
        if i in world:
            return world[i]
        name, par = bones[i]
        p = np.array(vals.get(name + " pos", (0, 0, 0, 0))[:3])
        R = qmat(*vals.get(name + " rot", (0, 0, 0, 1)))          # verified: the phonograph comes out upright, bounds = the skc's own
        pi = next((k for k, b in enumerate(bones) if b[0] == par), None)
        if pi is not None:
            Rp, pp = pose(pi)
            R, p = R @ Rp, p @ Rp + pp
        world[i] = (R, p)
        return world[i]
    surfs = []
    o = ofsS
    for s in range(nsurf):
        sh = struct.unpack_from("<4s64s8i", d, o)
        sname = sh[1].split(b"\0")[0].decode()
        nT, nV, _, oT, oV, oC, oE, oCI = sh[2:]
        tris = np.frombuffer(d, "<i4", nT * 3, o + oT).reshape(nT, 3).copy()
        p = o + oV
        P, N, U = [], [], []
        for v in range(nV):
            n0, n1, n2, u, vv, nw, nm = struct.unpack_from("<3f2f2i", d, p)
            p += 28
            acc, nrm = np.zeros(3), np.zeros(3)
            for w in range(nw):
                bi, wt, x, y, zz = struct.unpack_from("<if3f", d, p)
                p += 20
                R, t0 = pose(bi)
                acc += wt * (np.array([x, y, zz]) @ R + t0)
                nrm += wt * (np.array([n0, n1, n2]) @ R)
            p += nm * 16
            P.append(acc * scale)
            N.append(nrm / (np.linalg.norm(nrm) + 1e-9))
            U.append((u, vv))
        surfs.append(dict(name=sname, tris=tris, P=np.array(P), N=np.array(N), U=np.array(U), shader=shaders.get(sname) or _wild(shaders, sname) or shaders.get("all") or shaders.get("*") or (list(shaders.values())[0] if len(shaders) == 1 else "")))
        o += oE
    return surfs


def write(name, surfs, anim_frames=None, frame_time=0.1):
    """surfs: dicts (name, tris, P, N, U, shader); anim_frames: [(pos, quat)] for the one bone, default the identity"""
    ss = []
    allp = np.vstack([s["P"] for s in surfs])
    for s in surfs:
        verts = [(tuple(s["N"][i]), tuple(s["U"][i]), 0, tuple(s["P"][i])) for i in range(len(s["P"]))]
        ss.append((s["name"], s["tris"], verts))
    open(os.path.join(mdir, name + ".skd"), "wb").write(X.build_skd(name, [("root", "worldbone")], ss))
    lo, hi = allp.min(0), allp.max(0)
    rad = float(np.linalg.norm(allp, axis=1).max())
    frames = [[(0, 0, 0, 0), (0, 0, 0, 1)]] if not anim_frames else [[tuple(p) + (0,), tuple(q)] for p, q in anim_frames]
    open(os.path.join(mdir, name + ".skc"), "wb").write(X.build_skc(["root pos", "root rot"], frames, frame_time, lo.tolist(), hi.tolist(), rad))
    surf_lines = "".join("\tsurface %s shader %s\n" % (s["name"], s["shader"]) for s in surfs)
    open(os.path.join(mdir, name + ".tik"), "w", newline="\n").write(
        "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel %s.skd\n%s}\n\n"
        "init\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle %s.skc\n}\n" % (name, surf_lines, name))
    print("%-22s surfs %d  bounds x %.1f..%.1f y %.1f..%.1f z %.1f..%.1f" % (name, len(surfs), lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    return lo, hi


def sub(s, keep):
    """the triangles `keep` (bool per tri) of a surface, re-indexed"""
    t = s["tris"][keep]
    used = np.unique(t)
    remap = -np.ones(len(s["P"]), int)
    remap[used] = np.arange(len(used))
    return dict(s, tris=remap[t], P=s["P"][used], N=s["N"][used], U=s["U"][used])


# ---- the phonograph: cabinet + arm (static) and the record (spinning)
ph = load("models/static/phonograph.tik")[0]
tex = None
c = ph["P"][ph["tris"]].mean(1)
top = ph["P"][:, 2].max()
# the record: a 16-sided slab (two fans + rim, 40 tris) between z 12.3 and 13.3 (tik scale applied), centred on the spindle;
# every vertex of its triangles lies in that band and inside the rim, so the tone arm / spindle (higher) and the cabinet stay put
T = ph["P"][ph["tris"]]
cxy = np.array([-0.33, 0.42])
inband = ((T[:, :, 2] > 12.3) & (T[:, :, 2] < 13.3)).all(1) & (np.linalg.norm(T[:, :, :2] - cxy, axis=2) < 9.8).all(1)
disc = inband
platter_z = float(T[disc][:, :, 2].max())
dv = ph["P"][np.unique(ph["tris"][disc])]
ctr = (dv.min(0) + dv.max(0)) / 2
rim = np.linalg.norm(dv[:, :2] - ctr[:2], axis=1).max()
print("record: %d tris, centre %s, radius %.2f, platter z %.2f" % (disc.sum(), np.round(ctr, 2), rim, platter_z))
# v1.10.62 the tone arm (hzm_gram_arm): the stock mesh's arm parts above the platter on the -x side (the counterweight knob at
# x -14.3 .. the reproducer and its needle at x -2.5); the low bracket under it (z < 12.9) stays on the cabinet
cxy_all = np.linalg.norm(c[:, :2] - cxy, axis=1)
arm = (~disc) & (T[:, :, 2] >= 12.9).all(1) & (T[:, :, 0] <= -1.0).all(1) & (T[:, :, 1] > -3.2).all(1) & (T[:, :, 1] < 1.5).all(1)
body = sub(ph, ~disc & ~arm)
rec = sub(ph, disc)
rec["P"] = rec["P"] - np.array([ctr[0], ctr[1], 0.0])          # spin about the spindle


def round_record(stock, n=96, R=8.9, bevel=0.22):
    """v1.10.62: the stock record is a 16-sided slab and not even round (half-widths 8.9 x 9.1 about the spindle), so spinning it
    the outline swelled and shrank - it read as a wobble and a faceted edge.  A true disc instead: n segments, flat top at the
    stock top (13.19), a small rounded bevel, a straight side down to the stock bottom; the top keeps the stock record's own
    texture mapping (the groove sheen) by an affine xy -> uv fit to the stock top ring, the edge takes the stock outer ring."""
    P0, U0 = stock["P"], stock["U"]
    ztop, zbot = float(P0[:, 2].max()), float(P0[:, 2].min())
    top = np.abs(P0[:, 2] - ztop) < 1e-3
    bot = ~top

    def fit(sel):
        A = np.c_[P0[sel, :2], np.ones(sel.sum())]
        return np.linalg.lstsq(A, U0[sel], rcond=None)[0]
    Ft, Fb = fit(top), fit(bot)
    uvt = lambda x, y: np.array([x, y, 1.0]) @ Ft          # noqa: E731
    uvb = lambda x, y: np.array([x, y, 1.0]) @ Fb          # noqa: E731
    V, N, UV = [], [], []

    def add(p, nrm, uv):
        V.append(p); N.append(nrm / np.linalg.norm(nrm)); UV.append(uv)
        return len(V) - 1
    c = add((0.0, 0.0, ztop), np.array([0, 0, 1.0]), uvt(0, 0))
    rings = []
    # (radius, z, normal-up weight, uv source): top edge, two bevel steps, side top, side bottom
    for r, z, up, src in ((R - bevel, ztop, 1.0, "t"), (R - bevel * 0.3, ztop - bevel * 0.3, 0.6, "t"), (R, ztop - bevel, 0.0, "b"), (R, zbot, 0.0, "b")):
        ring = []
        for k in range(n):
            a = 2 * math.pi * k / n
            x, y = r * math.cos(a), r * math.sin(a)
            nrm = np.array([math.cos(a) * (1 - up), math.sin(a) * (1 - up), up]) if up < 1 else np.array([0, 0, 1.0])
            ring.append(add((x, y, z), nrm, (uvt if src == "t" else uvb)(x, y)))
        rings.append(ring)
    tris = []
    for k in range(n):
        k2 = (k + 1) % n
        tris.append((c, rings[0][k], rings[0][k2]))
        for a_, b_ in zip(rings[:-1], rings[1:]):
            tris.append((a_[k], b_[k], b_[k2]))
            tris.append((a_[k], b_[k2], a_[k2]))
    t = np.array(tris, int)
    # winding as the stock record's own top triangles (the shader culls: the engine's front face is the stock winding)
    st = stock["tris"][np.all(top[stock["tris"]], 1)][0]
    sgn = np.sign(np.cross(P0[st[1]] - P0[st[0]], P0[st[2]] - P0[st[0]])[2])
    mine = np.sign(np.cross(np.array(V[t[0][1]]) - V[t[0][0]], np.array(V[t[0][2]]) - V[t[0][0]])[2])
    t = t[:, ::-1] if mine != sgn else t
    return dict(stock, tris=t, P=np.array(V, float), N=np.array(N, float), U=np.array(UV, float))


rec = round_record(rec)
GRAM_SPINDLE = (float(ctr[0]), float(ctr[1]), float(platter_z))
write("hzm_gram", [body])
ARM_PIVOT = np.array([-12.9, -0.11, 15.0])                       # the arm's base, in front of the counterweight knob
armS = sub(ph, arm)
tip = armS["P"][np.argmin(armS["P"][:, 2])]                     # the needle point
print("tone arm: %d tris, needle %s" % (arm.sum(), np.round(tip, 2)))
armS["P"] = armS["P"] - ARM_PIVOT                               # the bone sits on the pivot


def qcol(M):
    """a column-vector rotation M -> the skc quaternion (the engine applies p @ qmat(q), the transpose)"""
    w = math.sqrt(max(0.0, 1 + M[0, 0] + M[1, 1] + M[2, 2])) / 2
    x = math.copysign(math.sqrt(max(0.0, 1 + M[0, 0] - M[1, 1] - M[2, 2])) / 2, M[2, 1] - M[1, 2])
    y = math.copysign(math.sqrt(max(0.0, 1 - M[0, 0] + M[1, 1] - M[2, 2])) / 2, M[0, 2] - M[2, 0])
    z = math.copysign(math.sqrt(max(0.0, 1 - M[0, 0] - M[1, 1] + M[2, 2])) / 2, M[1, 0] - M[0, 1])
    q = np.array([x, y, z, w])          # measured in game: Scene3D turns a bone by q itself (the conjugate swung the arm the wrong way)
    return q / np.linalg.norm(q)


def arm_rot(yaw, lift):
    """yaw (deg) about the pivot's vertical axis, then the arm raised by `lift` (deg) about its own horizontal cross axis"""
    a, b = math.radians(yaw), math.radians(lift)
    Rz = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
    Ry = np.array([[math.cos(b), 0, -math.sin(b)], [0, 1, 0], [math.sin(b), 0, math.cos(b)]])  # the arm points +x from the pivot: +b lifts the tip
    return Rz @ Ry


TIP = tip - ARM_PIVOT
SP2 = np.array(GRAM_SPINDLE[:2]) - ARM_PIVOT[:2]


def yaw_for(r):
    """the arm yaw that puts the needle r units from the spindle (the solution nearest the stock pose)"""
    best = None
    for k in range(-1800, 1):          # one side of the platter: the sweep never crosses the closest point (yaw 0, r 2.2)
        y = k / 20.0
        p = (arm_rot(y, 0) @ TIP)[:2]
        e = abs(np.linalg.norm(p - SP2) - r)
        if best is None or e < best[0] - 1e-9 or (abs(e - best[0]) < 1e-9 and abs(y) < abs(best[1])):
            best = (e, y)
    return best[1]


R_OUT, R_IN, R_REST, R_LIFTPT = 8.0, 4.2, 11.2, 6.8           # lead-in groove, run-out, the rest beside the platter, the lift point
Y_OUT, Y_IN, Y_REST, Y_LP = yaw_for(R_OUT), yaw_for(R_IN), yaw_for(R_REST), yaw_for(R_LIFTPT)
FT, PLAY_S = 0.05, int(os.environ.get("GRAM_PLAY_S", "180"))
Y_PLAY_END = yaw_for(5.6)
UP = math.degrees(math.atan2(1.6, np.linalg.norm(TIP[:2])))     # the needle 1.6 u clear of the record


def ease(u):
    return u * u * (3 - 2 * u)


def frames_of(poses):
    """rotation only: the arm model's origin IS the pivot (corner_layout places hzm_gram_arm at the gramophone + the rotated pivot).
    No bone `pos`: in the first in-game test the arm drew offset by -pivot, the pos channel did not apply in Scene3D."""
    return [((0.0, 0.0, 0.0), qcol(arm_rot(y, l))) for y, l in poses]


ARM_ANIMS = {
    # play: three minutes from the lead-in inward (r 8 -> 5.6, about a theme's length), with the small sway of a record's eccentricity
    # once a turn (1.8 s).  Every anim is 20 frames a second: Scene3D played a 15 s-a-frame skc at 0.05 s a frame (measured in game)
    # GRAM_PLAY_S=0: the needle rides the lead-in groove with the sway only (one turn, 37 frames).  The shipped default tracks
    # inward (a frame-sequence clip looked jumpy, but it was the capture: screenshotJPEG frames are ~0.15 s apart, not 0.05)
    "play": (FT, [(Y_OUT + (Y_PLAY_END - Y_OUT) * k / (PLAY_S * 20) + 0.25 * math.sin(2 * math.pi * k / 36), 0.0) for k in range(PLAY_S * 20 + 1)]
             if PLAY_S else [(Y_OUT + 0.25 * math.sin(2 * math.pi * k / 36), 0.0) for k in range(37)]),
    # lift (0.3 s): up off the groove, then out to the rest
    "lift": (0.05, [(Y_LP, UP * ease(min(1, k / 2))) for k in range(3)] + [(Y_LP + (Y_REST - Y_LP) * ease(k / 4), UP) for k in range(1, 5)]),
    # drop (0.4 s): over to the lead-in, then down onto it
    "drop": (0.05, [(Y_REST + (Y_OUT - Y_REST) * ease(k / 5), UP) for k in range(6)] + [(Y_OUT, UP * (1 - ease(k / 3))) for k in range(1, 4)]),
}
print("arm yaw: out %.1f in %.1f rest %.1f lift-point %.1f, lift %.1f deg" % (Y_OUT, Y_IN, Y_REST, Y_LP, UP))
ap = armS["P"]
alo, ahi = ap.min(0) - 3, ap.max(0) + 3
arad = float(np.linalg.norm(ap, axis=1).max()) + 2
X.build_skd  # noqa: B018
verts = [(tuple(armS["N"][i]), tuple(armS["U"][i]), 0, tuple(armS["P"][i])) for i in range(len(ap))]
open(os.path.join(mdir, "hzm_gram_arm.skd"), "wb").write(X.build_skd("hzm_gram_arm", [("root", "worldbone")], [(armS["name"], armS["tris"], verts)]))
for an, (ft, poses) in ARM_ANIMS.items():
    fr = [[tuple(p) + (0,), tuple(q)] for p, q in frames_of(poses)]
    open(os.path.join(mdir, "hzm_gram_arm_%s.skc" % an), "wb").write(
        X.build_skc(["root pos", "root rot"], fr, ft, alo.tolist(), ahi.tolist(), arad))
open(os.path.join(mdir, "hzm_gram_arm.tik"), "w", newline="\n").write(
    "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel hzm_gram_arm.skd\n\tsurface %s shader %s\n}\n\n"
    "init\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n"
    "\tidle hzm_gram_arm_play.skc\n\tplay hzm_gram_arm_play.skc\n\tlift hzm_gram_arm_lift.skc\n\tdrop hzm_gram_arm_drop.skc\n}\n" % (armS["name"], armS["shader"]))
# the needle at the lead-in and mid-record (model space): the needle hotspot sits on the reproducer head
_head = lambda y: ARM_PIVOT + arm_rot(y, 0) @ (TIP + np.array([0, 0, 1.6]))   # noqa: E731
open(os.path.join(out, "gram_arm.txt"), "w").write("%.3f %.3f %.3f\n" % tuple(_head((Y_OUT + Y_IN) / 2)))
TURN, NF = 1.8, 36                                              # 33 1/3 rpm, 20 frames a second (see FT)
frames = [((0, 0, 0), (0, 0, math.sin(-math.pi * k / NF), math.cos(-math.pi * k / NF))) for k in range(NF + 1)]
write("hzm_gram_disc", [rec], frames, TURN / NF)
open(os.path.join(out, "gram_spindle.txt"), "w").write("%.3f %.3f %.3f %.3f\n" % (GRAM_SPINDLE + (rim,)))

# ---- v1.10.66 (user: "the records in the main menu come off as obviously being a 2d image"): the record's paper label, the sleeve and
# the SHUFFLE tag were screen-space Labels framed onto boards (scenelabel) - flat cut-outs that turn with the camera. Now 3D:
#   hzm_gram_disc<n>   the record (the same 96-segment disc) with ITS round paper label as a disc 0.03 u proud of the vinyl, spinning
#                      with it (one model per record; the menu shows the playing one - engine scenemodelcvar on ui_mmLabel)
#   hzm_gram_sleeve3d<n>  a 12-inch sleeve 15.6 x 15.6 x 0.30 u: the sleeve art on the front, kraft back and edges (gen_gram_art.py)
#   hzm_gram_tag3d     the pencilled manila tag, 10.8 x 4.8 x 0.08 u, tucked into the sleeve while the pick is shuffle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_menumusic as _GM  # noqa: E402
_top = float(rec["P"][:, 2].max())


def _fan(name, shader, r, z, n=48, uvr=0.5, up=True):
    """a flat disc of radius r at height z (local), uv mapped onto the unit square's inscribed circle"""
    P, N, U = [(0.0, 0.0, z)], [(0, 0, 1.0 if up else -1.0)], [(0.5, 0.5)]
    for k in range(n):
        t = 2 * math.pi * k / n
        P.append((r * math.cos(t), r * math.sin(t), z))
        N.append((0, 0, 1.0 if up else -1.0))
        U.append((0.5 + uvr * math.cos(t), 0.5 - uvr * math.sin(t)))
    tris = [[0, 1 + k, 1 + (k + 1) % n] if up else [0, 1 + (k + 1) % n, 1 + k] for k in range(n)]
    return dict(name=name, tris=np.array(tris), P=np.array(P), N=np.array(N, float), U=np.array(U), shader=shader)


for _i in range(len(_GM.THEMES)):
    write("hzm_gram_disc%d" % _i, [rec, _fan("label", "hzm_gram_rlabel%d" % _i, 3.0, _top + 0.03)], frames, TURN / NF)


def _box(name, shader, w, h, t, front_uv=True):
    """a thin card standing in its local Y (width) x Z (height) plane, thickness t along -X (the front faces -X, the camera's way);
    the front carries the whole texture, the back / edges a kraft swatch from the art's edge (u 0.01)"""
    P, N, U, tris = [], [], [], []

    def quad(c, nrm, uv):
        b = len(P)
        P.extend(c)
        N.extend([nrm] * 4)
        U.extend(uv)
        tris.extend([[b, b + 1, b + 2], [b, b + 2, b + 3]])
    y0, y1, z0, z1, x0, x1 = -w / 2, w / 2, 0.0, h, -t / 2, t / 2
    E = [(0.01, 0.5)] * 4
    # front (-X): seen from the camera, u to the viewer's right (= +Y here, the camera looks +X with +Y on its left -> u runs -Y)
    quad([(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)], (-1, 0, 0), [(0, 1), (1, 1), (1, 0), (0, 0)] if front_uv else E)
    quad([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (1, 0, 0), E)
    quad([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0), E)
    quad([(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)], (0, 1, 0), E)
    quad([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1), E)
    quad([(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)], (0, 0, -1), E)
    return dict(name="s", tris=np.array(tris), P=np.array(P), N=np.array(N, float), U=np.array(U), shader=shader)


SLV = 13.2                          # the sleeve's side (game units: 0.25 m)
LEAN = math.radians(10.0)           # the sleeve stands on its bottom edge, its top leaning back 10 deg against the gramophone's side


def _lean(sf, off=(0.0, 0.0, 0.0)):
    """offset in the sleeve's own frame, then the lean: x += z tan(LEAN) (a shear about the bottom edge)"""
    P = sf["P"] + np.array(off)
    P[:, 0] += P[:, 2] * math.tan(LEAN)
    return dict(sf, P=P)


for _i in range(len(_GM.THEMES)):
    # a 10-inch sleeve (78 rpm shellac was 10-inch): 13.2 u - the 12-inch one's top corner cut into the gramophone's lid moulding
    write("hzm_gram_sleeve3d%d" % _i, [_lean(_box("s", "hzm_gram_sleeve3d%d" % _i, SLV, SLV, 0.30))])
# the tag: in the sleeve's frame (same origin and yaw in the menu), behind its top-right corner, poking 3 u above it
write("hzm_gram_tag3d", [_lean(_box("s", "hzm_gram_tag3d", 9.2, 4.1, 0.08), (0.30, -SLV * 0.23, SLV - 1.6))])

# ---- the officer's corner: his own tall side table (the stock square table, its top cut to 60 % and 80 % as tall: a lamp-table that fits
# the gap between Weathers' work table and the long desk at the near end)
def scaled(surfs, k):
    return [dict(x, P=x["P"] * np.array(k)) for x in surfs]


write("hzm_corner_table", scaled(load("models/static/square_table.tik"), (0.6, 0.6, 0.8)))
