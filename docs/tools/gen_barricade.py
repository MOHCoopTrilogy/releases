#!/usr/bin/env python3
"""gen_barricade.py - HZM coop BOARD-UP-THE-WINDOWS data, meshes and icons (coop_mod/barricade.scr).

    python docs/tools/gen_barricade.py build <bsp-or-pk3> [--out ROOT]   # write everything
    python docs/tools/gen_barricade.py check <bsp-or-pk3>                # re-measure, exit 1 on any QA failure

[user 2026-11-16, Their Dying Breath] "find planks lying around downstairs in the church cellar and other places ...
place perfectly over some windows to create cover ... not be able to see through the windows the boards cover".

WHAT IS DERIVED, NOT TYPED. Every window slot is MEASURED from the converted level's own collision (the player's pak,
read only): a seed point inside each opening is flood-filled on a 1 u grid with horizontal rays through the wall, which
gives the opening's exact rectangle; the boards are then laid over that rectangle on the wall's INSIDE face (user: "placed
inside the church"), with a margin that is cut back wherever the wall plane is blocked (a pilaster, the side gallery's
underside). QA run on every build:
  * coverage - every point of the opening on a 1 u grid lies behind at least one board (no see-through gap),
  * clearance - no board volume is inside the world's collision (no board through a pilaster or gallery),
  * contact - every board's back face is within 0.5 u of the wall face behind it (no floating board).
Plank stacks are placed on the floor found by a down-trace.

Outputs (relative to the repo root):
  hzm-mohaa-coop-mod/coop_mod/barricade_data.scr                    level.bar_* tables, one label per map
  docs/tools/assets/fixes/models/coop_barricade/board<L><v>.{tik,skd,skc}   box boards, plank texture, 3 UV variants
  docs/tools/assets/fixes/textures/hud/coop_plank_icon.tga          item-row icon (cgame CG_DrawCoopItems)
  docs/tools/assets/fixes/textures/hud/loot/coop_act_plank.tga      crosshair action prompt (actprompt.scr)
The board mesh is shape_beam.skd (the build-mode box) re-dimensioned and re-UV'd; nothing is copied from the disc.
"""
import io, json, math, os, random, struct, sys, zipfile

ROOT = os.environ.get("HZM_ROOT") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "docs", "tools"))
from bsptrace import BSP  # noqa: E402

MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
FIX = os.path.join(ROOT, "docs", "tools", "assets", "fixes")
SHAPE = os.path.join(MOD, "models", "coop_build", "shapes")

BOARD_H = 14.0          # board width (its height on the wall), inches
BOARD_T = 1.25          # board thickness
LENGTHS = (64, 70, 76, 82, 116, 120, 186, 190, 194)
VARIANTS = "ab"
UOFF = {"a": 0.0, "b": 0.43}
MARGIN_SIDE = 10.0
MARGIN_TB = 8.0

# ------------------------------------------------------------------------------------------------ per-map data
# A slot = a seed inside the opening (wall side, y, z) and how many planks board it fully. A stack = a floor point,
# a yaw for the planks and how many lie there. Everything else is measured.
MAPS = {
    "coop_ea_1_11": {
        "bsp": "maps/coop_ea_1_11.bsp",
        "pak": r"G:\mohaa-gl2\home\maintt\zzzz_coop_ea_1_11.pk3",
        # inside face of each wall (measured: rays from the nave hit the inner skin here)
        "walls": {"E": (5493.78, -1.0), "W": (4778.58, 1.0)},
        "slots": [
            # side, seed y, seed z, planks, name
            ("E", -1708, -440, 1, "east window 1"),
            ("E", -1885, -440, 1, "east window 2"),
            ("E", -2063, -440, 1, "east window 3"),
            ("E", -2240, -440, 1, "east window 4"),
            # the breach minus its north window: that window is the church's MG42 port (the original's mg nest 1, gun at
            # 4773 -1710) and stays open, so the boards stop 3u short of it (clip y <= -1744)
            ("W", -1850, -440, 2, "west breach", (-1e9, -1744.0)),
            ("W", -2063, -440, 1, "west window"),
            ("W", -2240, -440, 1, "west broken window"),
        ],
        # x, y, yaw, count, where (floor z is traced)
        "stacks": [
            (4672, -2490, 3, 6, "cellar"),
            (5442, -1975, 90, 2, "east aisle"),
            (4830, -1975, 90, 2, "west aisle"),
        ],
        # the objective appears when a player first stands inside this box (the nave, cellar excluded)
        "zone": ((4778, -2516, -560), (5494, -1460, -330)),
        "objtext": "Board up the Church",
    },
}


def load_bsp(src, m):
    if src.lower().endswith(".pk3"):
        with zipfile.ZipFile(src) as z:
            return BSP(z.read(m["bsp"]))
    return BSP(open(src, "rb").read())


# ------------------------------------------------------------------------------------------------ measurement
def through(B, face, n, y, z):
    a = (face + n * 20.0, y, z)
    b = (face - n * 120.0, y, z)
    r = B.trace(a, b)
    return r is None or r[0] > 0.9


def opening(B, face, n, y, z, yclip=(-1e9, 1e9)):
    seen, st, cells = set(), [(int(y), int(z))], []
    while st:
        c = st.pop()
        if c in seen:
            continue
        seen.add(c)
        if not (yclip[0] <= c[0] <= yclip[1]) or not through(B, face, n, c[0], c[1]):
            continue
        cells.append(c)
        if len(cells) > 60000:
            raise RuntimeError("opening flood ran away at %r" % ((y, z),))
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            st.append((c[0] + d[0], c[1] + d[1]))
    ys = [c[0] for c in cells]
    zs = [c[1] for c in cells]
    return [min(ys) - 0.5, max(ys) + 0.5, min(zs) - 0.5, max(zs) + 0.5], set(cells)


def free_along(B, x, y, z, dy, dz, reach):
    """free distance from (x,y,z) along (0,dy,dz) in the board plane, up to reach"""
    if B.point_solid((x, y, z)):
        return 0.0                  # a trace that starts in solid reports no hit
    r = B.trace((x, y, z), (x, y + dy * reach, z + dz * reach))
    return reach if r is None else r[0] * reach


def plan_slot(B, wall, seed):
    """[user 2026-11-16] "make sure the boards effectively cover each window and they shouldn't be perfect".
    Two layers with two jobs:
      BLOCKER - one invisible solid box per plank step, the opening's exact rectangle (+0.5 u), set in the wall plane.
                It is what stops sight, shots and movement; it never has a gap.
      BOARDS  - the look only (notsolid): crooked, different lengths, small overlaps and small visual gaps, nail heads,
                laid out by a per-slot seeded random so every window looks hand-done and every build looks the same."""
    side, sy, sz, need, name = seed[:5]
    yclip = seed[5] if len(seed) > 5 else (-1e9, 1e9)
    face, n = wall[side]
    (y0, y1, z0, z1), cells = opening(B, face, n, sy, sz, yclip)
    xp = face + n * 2.0                          # the board plane
    zc = (z0 + z1) / 2.0
    yc0 = (y0 + y1) / 2.0
    ysamp = [y0 + 3, yc0, y1 - 3]
    # the clear wall plane above and below, traced from the opening's middle: the side gallery's underside can sit BELOW
    # the opening's top (the west breach runs on up inside the gallery's hollow floor), and then it closes the wall plane
    zroof = min(zc + free_along(B, xp, y, zc, 0, 1, 200) for y in ysamp) - 0.25
    zfloor = max(zc - free_along(B, xp, y, zc, 0, -1, 200) for y in ysamp) + 0.25
    ztop = min(z1, zroof)
    zroof = min(zroof, z1 + 12.0)
    zfloor = max(zfloor, z0 - 12.0)
    # room along the wall plane on each side, over every height a board can occupy
    zs = [zfloor + 0.5 + (zroof - zfloor - 1.0) * i / 8.0 for i in range(9)]
    xs = [face + n * d for d in (0.1, 0.8, 1.6, 2.4, 3.2)]      # every depth the two board layers occupy
    # traced from the opening's middle outwards, so a pilaster that hides part of the hole is found too
    ylim_lo = yc0 - min(free_along(B, x, yc0, z, -1, 0, 200) for z in zs for x in xs) + 0.5
    ylim_hi = yc0 + min(free_along(B, x, yc0, z, 1, 0, 200) for z in zs for x in xs) - 0.5
    ra, rb = max(ylim_lo, y0 - 14.0, yclip[0]), min(ylim_hi, y1 + 14.0, yclip[1] + 0.5)
    up = zroof - z1
    rng = random.Random("bar:" + name)
    # ---- boards, bottom up
    boards = []
    width = y1 - y0
    zcur = z0 - rng.uniform(3.0, 6.0)            # the bottom board starts a little under the sill
    zcur = max(zcur, zfloor + 0.5)
    k = 0
    while True:
        h = BOARD_H
        # length: 4-14 u over the edge on each side, within the room the wall plane has
        room = rb - ra
        cands = [L for L in LENGTHS if min(width + 8, room) <= L <= room]
        if not cands:
            raise RuntimeError("%s: no board fits %.1f u of wall" % (name, room))
        L = rng.choice(cands)
        yc = rng.uniform(ra + L / 2.0, rb - L / 2.0)
        maxtilt = math.degrees(math.asin(min(1.0, 4.5 / (L / 2.0))))
        pitch = rng.uniform(0.35, 1.0) * maxtilt * rng.choice((-1, 1))
        zc_b = zcur + h / 2.0
        # keep the tilted board inside the clear wall plane (sill / floor below, gallery slab above)
        def ext(p):
            r = math.radians(abs(p))
            return L / 2.0 * math.sin(r) + h / 2.0 * math.cos(r)
        while zc_b + ext(pitch) > zroof - 0.25 or zc_b - ext(pitch) < zfloor + 0.25:
            pitch *= 0.5
            if abs(pitch) < 0.05:
                pitch = 0.0
                break
        if zc_b + ext(pitch) > zroof - 0.25:
            zc_b = zroof - 0.25 - ext(pitch)
        # and inside the room along the wall (a pilaster beside the west broken window): slide, then straighten
        while True:
            r = math.radians(abs(pitch))
            ey = L / 2.0 * math.cos(r) + h / 2.0 * math.sin(r)
            if ey * 2.0 <= (rb - ra) - 0.5 or pitch == 0.0:
                break
            pitch *= 0.5
            if abs(pitch) < 0.05:
                pitch = 0.0
        yc = min(max(yc, ra + ey + 0.25), rb - ey - 0.25)
        boards.append(dict(y=yc, z=zc_b, pitch=pitch, L=L, var=VARIANTS[k % 2], k=k))
        k += 1
        top = zc_b + h / 2.0
        if top >= ztop - 2.0:
            break
        # next: a small visual gap or a small overlap
        zcur = top + rng.choice((rng.uniform(-3.0, -1.0), rng.uniform(0.5, 2.5), rng.uniform(-1.5, 1.5)))
        if k > 40:
            raise RuntimeError("%s: board layout ran away" % name)
    nb = len(boards)
    yaw = 90.0 if n < 0 else 270.0
    for b in boards:
        layer = b["k"] % 2
        b["depth"] = BOARD_T / 2.0 + 0.2 + layer * (BOARD_T + 0.15)
        b["x"] = face + n * b["depth"]
        b["yaw"] = yaw
        b["plank"] = int(b["k"] * need / nb) + 1
    # ---- blockers, one per plank step: horizontal bands of the opening (bottom first)
    blockers = []
    zt = min(z1, ztop)
    for p in range(1, need + 1):
        za = z0 + (zt - z0) * (p - 1) / need - (0.5 if p == 1 else 0.0)
        zb = z0 + (zt - z0) * p / need + (0.5 if p == need else 0.0)
        if p == need:
            zb = min(zb, ztop)      # flush under a slab, never into it
        # x: from 1 u proud of the face into the wall skin, symmetric about its own origin (TRAPS T9)
        bx0, bx1 = face + n * 1.0, face - n * 3.0
        blockers.append(dict(org=((bx0 + bx1) / 2.0, (y0 + y1) / 2.0, (za + zb) / 2.0),
                             half=(abs(bx1 - bx0) / 2.0, (y1 - y0) / 2.0 + 0.5, (zb - za) / 2.0)))
    # where a player stands to board it: 34 u in front of the opening, on the floor
    ux, uy = face + n * 34.0, (y0 + y1) / 2.0
    r = B.trace((ux, uy, z0), (ux, uy, z0 - 200))
    uz = z0 - 200 * r[0] if r else z0 - 48
    return dict(name=name, side=side, need=need, open=(y0, y1, z0, z1), cells=cells, face=face, n=n, boards=boards,
                blockers=blockers, ztop=ztop, zbot=zfloor, ya=min(b["y"] - b["L"] / 2 for b in boards),
                yb=max(b["y"] + b["L"] / 2 for b in boards), use=(ux, uy, uz))


def board_rect(b):
    """the board's 4 corners in the wall plane (y, z), with its in-plane tilt"""
    c, s = math.cos(math.radians(b["pitch"])), math.sin(math.radians(b["pitch"]))
    pts = []
    for (u, v) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        du, dv = u * b["L"] / 2.0, v * BOARD_H / 2.0
        pts.append((b["y"] + du * c - dv * s, b["z"] + du * s + dv * c))
    return pts


def inside(pt, poly):
    x, y = pt
    ins = False
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            ins = not ins
    return ins


def qa_slot(B, s):
    fails = []
    # BLOCKER coverage: every through-cell of the opening (below the slab) inside some blocker band - exact, no gaps
    miss = 0
    for (y, z) in s["cells"]:
        for qy in (y - 0.5, y + 0.5):
            for qz in (z - 0.5, z + 0.5):
                if qz > s["ztop"]:
                    continue
                ok = False
                for bl in s["blockers"]:
                    (ox, oy, oz), (hx, hy, hz) = bl["org"], bl["half"]
                    if abs(qy - oy) <= hy and abs(qz - oz) <= hz:
                        ok = True
                        break
                if not ok:
                    miss += 1
    if miss:
        fails.append("%s: blocker leaves %d opening points open" % (s["name"], miss))
    # neighbouring blocker bands must touch
    for a, b in zip(s["blockers"], s["blockers"][1:]):
        if (a["org"][2] + a["half"][2]) < (b["org"][2] - b["half"][2]) - 0.01:
            fails.append("%s: blocker bands do not meet" % s["name"])
    # visual coverage (report only: the user wants it imperfect, but it should read as boarded)
    rects = [board_rect(b) for b in s["boards"]]
    tot = cov = 0
    for (y, z) in s["cells"]:
        if z > s["ztop"]:
            continue
        tot += 1
        if any(inside((y, z), r) for r in rects):
            cov += 1
    s["vis_cov"] = cov / max(1, tot)
    if s["vis_cov"] < 0.80:
        fails.append("%s: boards cover only %.0f%% of the opening" % (s["name"], 100 * s["vis_cov"]))
    # clearance: no board inside the world's collision
    for b in s["boards"]:
        poly = board_rect(b)
        for t in range(0, 25):
            for u in range(0, 5):
                # walk the rotated rectangle in its own frame
                du = (t / 24.0 - 0.5) * (b["L"] - 0.2)
                dv = (u / 4.0 - 0.5) * (BOARD_H - 0.2)
                c, sn = math.cos(math.radians(b["pitch"])), math.sin(math.radians(b["pitch"]))
                y = b["y"] + du * c - dv * sn
                z = b["z"] + du * sn + dv * c
                for dd in (-BOARD_T / 2 + 0.05, BOARD_T / 2 - 0.05):
                    x = b["x"] + s["n"] * dd
                    if B.point_solid((x, y, z)):
                        fails.append("%s board %d: in collision at (%.1f %.1f %.1f)" % (s["name"], b["k"], x, y, z))
                        break
                else:
                    continue
                break
            else:
                continue
            break
        # contact: a back-layer board's back face sits on the wall (<= 0.5 u) wherever it is not over the hole
        if b["k"] % 2 == 0:
            back = b["x"] + s["n"] * (BOARD_T / 2.0)
            gaps = []
            for t in range(1, 20):
                y = b["y"] - b["L"] / 2.0 + b["L"] * t / 20.0
                if s["open"][0] - 1 <= y <= s["open"][1] + 1 and s["open"][2] - 1 <= b["z"] <= s["open"][3] + 1:
                    continue
                r = B.trace((back - s["n"] * 0.01, y, b["z"]), (back + s["n"] * 6.0, y, b["z"]))
                if r is not None:
                    gaps.append(r[0] * 6.0)
            if gaps and max(gaps) > 0.5:
                fails.append("%s board %d: back face %.2f u off the wall" % (s["name"], b["k"], max(gaps)))
    return fails


def plan_stack(B, st):
    x, y, yaw, cnt, where = st
    r = B.trace((x, y, -380), (x, y, -900))
    if r is None:
        raise RuntimeError("stack %s: no floor" % where)
    # under the side gallery (its floor is at -344): start below it; the cellar starts below the nave floor
    z = -380 - 520 * r[0]
    if where == "cellar":
        r = B.trace((x, y, -620), (x, y, -900))
        z = -620 - 280 * r[0]
    # clearance: the pile's footprint (72 x 14, up to cnt planks) must be free
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    for t in (-36, 0, 36):
        for w in (-7, 7):
            px = x + t * c - w * s
            py = y + t * s + w * c
            for h in (1, cnt * 1.4 + 2):
                if B.point_solid((px, py, z + h)):
                    raise RuntimeError("stack %s: pile in collision at %.0f %.0f %.0f" % (where, px, py, z + h))
    return dict(x=x, y=y, z=z, yaw=yaw, cnt=cnt, where=where)


# ------------------------------------------------------------------------------------------------ meshes
def _surface(name, verts, tris):
    """one SKSF surface in shape_beam.skd's own layout: 100-byte header | tris | 48-byte verts | identity collapse |
    zero collapse index (the engine reads both unconditionally, bug-1002)"""
    nT, nV = len(tris), len(verts)
    vb = bytearray()
    for (nrm, uv, off) in verts:
        vb += struct.pack("<3f2f2i", nrm[0], nrm[1], nrm[2], uv[0], uv[1], 1, 0)
        vb += struct.pack("<if3f", 0, 1.0, off[0], off[1], off[2])
    tb = b"".join(struct.pack("<3i", *t) for t in tris)
    ofsTri = 100
    ofsVerts = ofsTri + len(tb)
    ofsColl = ofsVerts + len(vb)
    ofsCollIdx = ofsColl + nV * 4
    ofsEnd = ofsCollIdx + nV * 4
    nm = name.encode("ascii")
    hdr = struct.pack("<4s64s8i", b"SKSF", nm + b"\0" * (64 - len(nm)), nT, nV, 0, ofsTri, ofsVerts, ofsColl, ofsEnd,
                      ofsCollIdx)
    return hdr + tb + bytes(vb) + struct.pack("<%di" % nV, *range(nV)) + struct.pack("<%di" % nV, *([0] * nV))


def _box(hx, hy, hz, uvf):
    """24 verts / 12 tris, outward faces, winding as shape_beam.skd (tri (a, c, b) per quad)"""
    V, T = [], []
    faces = [((1, 0, 0), [(hx, -hy, hz), (hx, -hy, -hz), (hx, hy, -hz), (hx, hy, hz)]),
             ((-1, 0, 0), [(-hx, hy, hz), (-hx, hy, -hz), (-hx, -hy, -hz), (-hx, -hy, hz)]),
             ((0, 0, 1), [(hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz), (-hx, -hy, hz)]),
             ((0, 0, -1), [(-hx, -hy, -hz), (-hx, hy, -hz), (hx, hy, -hz), (hx, -hy, -hz)]),
             ((0, -1, 0), [(hx, -hy, hz), (-hx, -hy, hz), (-hx, -hy, -hz), (hx, -hy, -hz)]),
             ((0, 1, 0), [(hx, hy, -hz), (-hx, hy, -hz), (-hx, hy, hz), (hx, hy, hz)])]
    for nrm, q in faces:
        b = len(V)
        for p in q:
            V.append((nrm, uvf(nrm, p), p))
        T += [(b, b + 2, b + 1), (b, b + 3, b + 2)]
    return V, T


def _check_winding(V, T):
    """every triangle's geometric normal must agree with its vertex normal (shape_beam's convention)"""
    for (a, b, c) in T:
        pa, pb, pc = V[a][2], V[b][2], V[c][2]
        u = [pb[i] - pa[i] for i in range(3)]
        w = [pc[i] - pa[i] for i in range(3)]
        cr = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
        dot = sum(cr[i] * V[a][0][i] for i in range(3))
        assert dot != 0
        yield dot


def _orient(V, T, sign):
    """flip any triangle whose winding disagrees with the reference mesh's convention"""
    out = []
    for t, d in zip(T, _check_winding(V, T)):
        out.append(t if (d > 0) == (sign > 0) else (t[0], t[2], t[1]))
    return out


def board_mesh(L, var):
    """a plank: box L x T x H (length on x, thickness on y, the church side is +y) with the stock plank texture, and
    four nail heads on the church side, two at each end"""
    ref = open(os.path.join(SHAPE, "shape_beam.skd"), "rb").read()
    # the reference's own winding sign, so ours matches whatever convention the engine culls with
    o = 266
    nT, nV, _, oT, oV, oC, oE, oCI = struct.unpack_from("<8i", ref, o + 68)
    RV = []
    for i in range(nV):
        p = o + oV + 48 * i
        nrm = struct.unpack_from("<3f", ref, p)
        off = struct.unpack_from("<3f", ref, p + 36)
        RV.append((nrm, (0, 0), off))
    RT = [struct.unpack_from("<3i", ref, o + oT + 12 * i) for i in range(nT)]
    ref_sign = 1 if all(d > 0 for d in _check_winding(RV, RT)) else -1
    uL = (L / BOARD_H) / 4.0            # plank_flat is 256 x 64: square texels
    uo = UOFF[var]
    hx, hy, hz = L / 2.0, BOARD_T / 2.0, BOARD_H / 2.0

    def uv(nrm, p):
        if abs(nrm[1]) > 0.5:
            return ((p[0] / L + 0.5) * uL + uo, 0.5 - p[2] / BOARD_H)
        if abs(nrm[2]) > 0.5:
            return ((p[0] / L + 0.5) * uL + uo, 0.5 + p[1] / BOARD_T * 0.08)
        return (0.02 + (p[1] / BOARD_T + 0.5) * 0.03 + uo, 0.5 - p[2] / BOARD_H)
    V, T = _box(hx, hy, hz, uv)
    # [in-game still, run 1] a skd vertex offset is in the BONE's frame, which is the model frame turned about x: offset y
    # draws as model UP and offset z as model -y (the first build stood every board on its 1.25u edge). The board is
    # built in model axes (x length, y thickness with the church on +y, z height) and turned into the bone frame here.
    def to_bone(v):
        return (v[0], v[2], -v[1])
    V = [(to_bone(n), uvv, to_bone(o)) for (n, uvv, o) in V]
    T = _orient(V, T, ref_sign)
    assert all((d > 0) == (ref_sign > 0) for d in _check_winding(V, T))
    # nails: small square heads just proud of the church face, 4-7 u in from each end, 3.5 u above / below centre
    NV, NT = [], []
    rng = random.Random("nails%d%s" % (L, var))
    # [in-game still, run 2: no nail showed from the nave] heads on BOTH faces (a nail driven through shows its head on
    # the church side and, bent over, on the street side too), 1.1u square so they read at room distance
    for ex in (-1, 1):
        for ez in (-1, 1):
            cx = ex * (hx - rng.uniform(3.5, 6.5))
            cz = ez * rng.uniform(2.6, 4.0)
            r = 0.55
            for side in (1, -1):
                y = side * (hy + 0.06)
                b = len(NV)
                quad = [(cx + r, y, cz - r), (cx - r, y, cz - r), (cx - r, y, cz + r), (cx + r, y, cz + r)]
                for p in quad:
                    NV.append(((0, side, 0), ((p[0] - cx) / (2 * r) + 0.5, (p[2] - cz) / (2 * r) + 0.5), p))
                NT += [(b, b + 2, b + 1), (b, b + 3, b + 2)]
    NV = [(to_bone(n), uvv, to_bone(o)) for (n, uvv, o) in NV]
    NT = _orient(NV, NT, ref_sign)
    assert all((d > 0) == (ref_sign > 0) for d in _check_winding(NV, NT))
    surfs = [_surface("board", V, T), _surface("nails", NV, NT)]
    body = b"".join(surfs)
    head = bytearray(ref[:266])          # SKMD v5 header + the one-bone block ("origin" / worldbone)
    total = 266 + len(body)
    struct.pack_into("<5i", head, 72, 2, 1, 148, 266, total)
    struct.pack_into("<4i", head, 72 + 20 + 40, 0, total, 0, total)
    skd = bytes(head) + body
    skc = bytearray(open(os.path.join(SHAPE, "shape_beam.skc"), "rb").read())
    hyn = hy + 0.1
    struct.pack_into("<7f", skc, 48, -hx, -hz, -hz, hx, hz, hz, math.sqrt(hx * hx + 2 * hz * hz))
    stem = "board%d%s" % (L, var)
    tik = ("TIKI\n"
           "// HZM coop barricade plank, %d x %d x %.2f u, UV variant %s, nail heads at both ends, both faces.\n"
           "// GENERATED by docs/tools/gen_barricade.py - do not hand-edit. The build-mode box layout (shape_beam.skd),\n"
           "// the stock plank texture and the stock iron-bar texture for the nails.\n"
           "setup\n{\n\tscale 1.00\n\tpath models/coop_barricade\n\tskelmodel %s.skd\n"
           "\tsurface board shader textures/general_structure/plank_flat\n"
           "\tsurface nails shader textures/general_industrial/ironbar\n}\n\n"
           "init\n{\n\tserver\n\t{\n\t\tclassname animate\n\t}\n}\n\n"
           "animations\n{\n\tidle %s.skc\n\t{\n\t}\n}\n") % (L, BOARD_H, BOARD_T, var, stem, stem)
    return stem, tik.encode("ascii"), skd, bytes(skc)


# ------------------------------------------------------------------------------------------------ icons
def write_tga(img, path):
    img = img.convert("RGBA")
    w, h = img.size
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 8)
    px = img.transpose(1).tobytes("raw", "BGRA")          # bottom-up
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(hdr + px)


def hud_icon():
    """128x128, the item row's look (coop_cover_icon: warm fills, dark keyline, soft shade): three planks across a
    dark window opening, nail heads at the ends."""
    from PIL import Image, ImageDraw, ImageFilter
    S = 4
    W = 128 * S
    base = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    # window opening behind the planks (pointed arch), dark
    arch = [(30, 120), (30, 46), (64, 14), (98, 46), (98, 120)]
    d.polygon([(x * S, y * S) for x, y in arch], fill=(26, 24, 22, 255), outline=(10, 9, 8, 255))
    planks = [((14, 40), (114, 30)), ((14, 70), (114, 76)), ((14, 104), (114, 96))]
    for (a, b) in planks:
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        nx, ny = -math.sin(ang), math.cos(ang)
        hw = 11
        poly = [(a[0] + nx * hw, a[1] + ny * hw), (b[0] + nx * hw, b[1] + ny * hw),
                (b[0] - nx * hw, b[1] - ny * hw), (a[0] - nx * hw, a[1] - ny * hw)]
        d.polygon([(x * S, y * S) for x, y in poly], fill=(10, 8, 6, 255))
        hw2 = 8.2
        poly2 = [(a[0] + 3 * math.cos(ang) + nx * hw2, a[1] + 3 * math.sin(ang) + ny * hw2),
                 (b[0] - 3 * math.cos(ang) + nx * hw2, b[1] - 3 * math.sin(ang) + ny * hw2),
                 (b[0] - 3 * math.cos(ang) - nx * hw2, b[1] - 3 * math.sin(ang) - ny * hw2),
                 (a[0] + 3 * math.cos(ang) - nx * hw2, a[1] + 3 * math.sin(ang) - ny * hw2)]
        d.polygon([(x * S, y * S) for x, y in poly2], fill=(196, 146, 92, 255))
        # lighter top edge, grain lines
        d.line([(poly2[0][0] * S, poly2[0][1] * S), (poly2[1][0] * S, poly2[1][1] * S)], fill=(228, 184, 128, 255), width=2 * S)
        for g in (-3.0, 2.5):
            d.line([((a[0] + 10 * math.cos(ang) + nx * g) * S, (a[1] + 10 * math.sin(ang) + ny * g) * S),
                    ((b[0] - 22 * math.cos(ang) + nx * g) * S, (b[1] - 22 * math.sin(ang) + ny * g) * S)],
                   fill=(150, 104, 60, 255), width=S)
        for e in (a, b):
            cx = e[0] + (9 if e is a else -9) * math.cos(ang)
            cy = e[1] + (9 if e is a else -9) * math.sin(ang)
            d.ellipse([(cx - 2.6) * S, (cy - 2.6) * S, (cx + 2.6) * S, (cy + 2.6) * S], fill=(60, 60, 64, 255))
    img = base.resize((128, 128), Image.LANCZOS)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    a = img.split()[3].filter(ImageFilter.GaussianBlur(2.2))
    shadow.putalpha(a.point(lambda v: int(v * 0.55)))
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.alpha_composite(shadow, (1, 2))
    out.alpha_composite(img)
    return out


def act_icon():
    """512x512 action prompt in the icon-prompts finish (cream fill, dark keyline, soft halo): a window with two
    crossed planks."""
    sys.path.insert(0, os.path.join(ROOT, "docs", "proposals", "icon_prompts_2026-10-18", "tools"))
    import build_action_icons as bai
    p = bai.Pen()
    # window frame: an arch outline
    p.poly([(116, 470), (116, 200), (256, 60), (396, 200), (396, 470)])
    p.poly([(156, 440), (156, 214), (256, 114), (356, 214), (356, 440)], v=0)
    # two crossed planks over it, with a gap ring cut round each so they read as separate pieces
    for (a, b) in (((60, 210), (452, 330)), ((60, 380), (452, 270))):
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        nx, ny = -math.sin(ang), math.cos(ang)
        for hw, v in ((52, 0), (36, 255)):
            p.poly([(a[0] + nx * hw, a[1] + ny * hw), (b[0] + nx * hw, b[1] + ny * hw),
                    (b[0] - nx * hw, b[1] - ny * hw), (a[0] - nx * hw, a[1] - ny * hw)], v=v)
        for e, sgn in ((a, 1), (b, -1)):
            p.ell(e[0] + sgn * 30 * math.cos(ang), e[1] + sgn * 30 * math.sin(ang), 9, v=0)
    return bai.finish(p.mask(), seed=11)


# ------------------------------------------------------------------------------------------------ data script
def fmt(v):
    s = ("%.2f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def vec(*a):
    return "( " + " ".join(fmt(x) for x in a) + " )"


def data_label(mapname, m, slots, stacks):
    L = []
    L.append("bar_data_%s:{" % mapname)
    L.append("\tlevel.bar_objText = \"%s\"" % m["objtext"])
    (a, b) = m["zone"]
    L.append("\tlevel.bar_zoneMin = %s" % vec(*a))
    L.append("\tlevel.bar_zoneMax = %s" % vec(*b))
    L.append("\tlevel.bar_nSlots = %d" % len(slots))
    for i, s in enumerate(slots, 1):
        L.append("\t// %s: opening y %s..%s z %s..%s, %d boards, %d plank(s)" % (
            s["name"], fmt(s["open"][0]), fmt(s["open"][1]), fmt(s["open"][2]), fmt(s["open"][3]), len(s["boards"]), s["need"]))
        L.append("\tlevel.bar_sName[%d] = \"%s\"" % (i, s["name"]))
        L.append("\tlevel.bar_sNeed[%d] = %d" % (i, s["need"]))
        L.append("\tlevel.bar_sUse[%d] = %s" % (i, vec(*s["use"])))
        L.append("\tlevel.bar_sMid[%d] = %s" % (i, vec(s["face"], (s["open"][0] + s["open"][1]) / 2.0, (s["open"][2] + s["open"][3]) / 2.0)))
        L.append("\tlevel.bar_sNb[%d] = %d" % (i, len(s["boards"])))
        for p, bl in enumerate(s["blockers"], 1):
            L.append("\tlevel.bar_xOrg[%d][%d] = %s" % (i, p, vec(*bl["org"])))
            L.append("\tlevel.bar_xHalf[%d][%d] = %s" % (i, p, vec(*bl["half"])))
        for k, bd in enumerate(s["boards"], 1):
            L.append("\tlevel.bar_bOrg[%d][%d] = %s" % (i, k, vec(bd["x"], bd["y"], bd["z"])))
            # engine angles: a positive pitch LOWERS the model's +x end (AngleVectors: forward z = -sin pitch). With yaw 90
            # the board's +x runs along world +y, with yaw 270 along world -y; board_rect() tilts the +y end up by "pitch"
            qp = -bd["pitch"] if bd["yaw"] == 90.0 else bd["pitch"]
            L.append("\tlevel.bar_bAng[%d][%d] = %s" % (i, k, vec(qp, bd["yaw"], 0)))
            L.append("\tlevel.bar_bMdl[%d][%d] = \"models/coop_barricade/board%d%s.tik\"" % (i, k, bd["L"], bd["var"]))
            L.append("\tlevel.bar_bLen[%d][%d] = %d" % (i, k, bd["L"]))
            L.append("\tlevel.bar_bPlank[%d][%d] = %d" % (i, k, bd["plank"]))
    L.append("\tlevel.bar_nStacks = %d" % len(stacks))
    for i, st in enumerate(stacks, 1):
        L.append("\tlevel.bar_kOrg[%d] = %s\t// %s" % (i, vec(st["x"], st["y"], st["z"]), st["where"]))
        L.append("\tlevel.bar_kYaw[%d] = %s" % (i, fmt(st["yaw"])))
        L.append("\tlevel.bar_kCount[%d] = %d" % (i, st["cnt"]))
    L.append("}end")
    return "\n".join(L)


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("build", "check"):
        print(__doc__)
        sys.exit(2)
    mode, src = sys.argv[1], sys.argv[2]
    out = ROOT
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    fails = []
    labels = []
    report = []
    for mapname, m in MAPS.items():
        B = load_bsp(src, m)
        slots = [plan_slot(B, m["walls"], sd) for sd in m["slots"]]
        for s in slots:
            f = qa_slot(B, s)
            fails += f
            o = s["open"]
            report.append("%-20s opening %5.1f x %5.1f  %2d boards (%s)  boards y %.1f..%.1f  look %3.0f%%  blockers %d  %s" % (
                s["name"], o[1] - o[0], o[3] - o[2], len(s["boards"]), ",".join(str(b["L"]) for b in s["boards"]),
                s["ya"], s["yb"], 100 * s.get("vis_cov", 0), len(s["blockers"]), "OK" if not f else "FAIL"))
        stacks = [plan_stack(B, st) for st in m["stacks"]]
        for st in stacks:
            report.append("stack %-14s %s x%d" % (st["where"], vec(st["x"], st["y"], st["z"]), st["cnt"]))
        labels.append(data_label(mapname, m, slots, stacks))
    print("\n".join(report))
    for f in fails:
        print("QA FAIL:", f)
    if mode == "check":
        sys.exit(1 if fails else 0)
    if fails:
        sys.exit(1)
    hdr = ("// barricade_data.scr - GENERATED by docs/tools/gen_barricade.py from each map's own collision. Do not hand-edit:\n"
           "// edit the seeds in the generator and re-run. One label per map, read by coop_mod/barricade.scr::bar_init.\n"
           "// Slot boards lie on the INSIDE face of the wall; every slot passed coverage / clearance / contact QA.\n\n")
    scr = hdr + "\n\n".join(labels) + "\n"
    scr.encode("ascii")
    # [bug-11325] every table barricade.scr reads must be in the data (the blocker rows once went missing: no box, AI saw
    # straight through every boarded window, and the only symptom was "Cannot cast 'none' to vector")
    for field in ("objText", "zoneMin", "zoneMax", "nSlots", "sName", "sNeed", "sUse", "sMid", "sNb", "xOrg", "xHalf",
                  "bOrg", "bAng", "bMdl", "bPlank", "nStacks", "kOrg", "kYaw", "kCount"):
        if ("level.bar_%s" % field) not in scr:
            print("DATA FAIL: level.bar_%s is never written" % field)
            sys.exit(1)
    p = os.path.join(out, "hzm-mohaa-coop-mod", "coop_mod", "barricade_data.scr")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(scr.encode("ascii"))
    fx = os.path.join(out, "docs", "tools", "assets", "fixes")
    for L in LENGTHS:
        for v in VARIANTS:
            stem, tik, skd, skc = board_mesh(L, v)
            d = os.path.join(fx, "models", "coop_barricade")
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, stem + ".tik"), "wb").write(tik)
            open(os.path.join(d, stem + ".skd"), "wb").write(skd)
            open(os.path.join(d, stem + ".skc"), "wb").write(skc)
    write_tga(hud_icon(), os.path.join(fx, "textures", "hud", "coop_plank_icon.tga"))
    write_tga(act_icon(), os.path.join(fx, "textures", "hud", "loot", "coop_act_plank.tga"))
    print("wrote", p)


if __name__ == "__main__":
    main()
