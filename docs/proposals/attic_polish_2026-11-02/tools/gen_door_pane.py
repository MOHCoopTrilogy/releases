"""gen_door_pane.py <out dir> [attic bake dir] [hub bake dir] - v1.10.62: the MULTIPLAYER door's glass, the same on both sides.

User: "if the door looks one way inside the main menu, it should look exactly the same from the other side (like the join game
room)".  Both sides bake the door's pane (attic: attic62_edit.py section 7; MP room: mphub3d hub_prep.py), each scaled 1.10 x 1.22
over the archive glass "to fill the light" - so it ran down over the knob height, and the two bakes disagreed (the MP room's came
out as jagged diagonal wedges with dark gaps, the attic's as flat light-grey blocks).  Now the pane is not a bake on either side:

  * a FRAME: the strip between the oversized baked pane and the real glass is covered with the door leaf's own face - the leaf's
    baked triangles' texels on that side (an affine fit of the leaf face's (y, z) -> atlas uv from that side's bake npz), on that
    side's bg shader, 1.5 mm in front of the baked pane - so on each side it is that side's lit wood, seamless with the leaf;
  * the GLASS: the archive door_mp_glass rectangle (0.66 x 0.95 m, z 1.075 .. 2.025: the knob stays below it, on the wood) with
    one frosted-glass texture (fullbright, identical on both sides): soft light from beyond, cool grey, faint mottle and grain,
    a darker line where the glass meets the stop;
  * the glazing bars stay baked on both sides (hub_prep copies the attic door with the same transform) and sit in front.

  attic  : leaf face BU x 3.000 (room side -X), baked pane front x 2.992, glass y 6.07 .. 6.73
  MP room: leaf face BU x -3.330 (room side +X), baked pane front x -3.322, glass y 3.72 .. 4.38  (mpui hub bake)
Writes models/menu/hzm_door_pane_{attic,hub}.*, textures/menu/hzm_door_pane.jpg, scripts/hzm_door_pane.shader; make_attic_polish
puts the attic one into main.urc's atticscene and the hub one into multiplayer.urc's hubscene."""
import os, sys
import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
import skx as X  # noqa: E402

out = sys.argv[1]
ABAKE = sys.argv[2] if len(sys.argv) > 2 else r"H:\hzm_work\attic62\bake"
HBAKE = sys.argv[3] if len(sys.argv) > 3 else r"H:\hzm_work\mpui\hub\bake"
S = 52.5
GZ = (1.075, 2.025)                   # the archive glass, z
PZ = (0.9705, 2.1295)                 # the baked (scaled) pane, z
SIDES = {  # leaf face x, overlay x, room-side normal x, glass y range, baked pane y range, bake dir, bg shader
    "attic": (3.000, 2.9905, -1.0, (6.07, 6.73), (6.037, 6.763), ABAKE, "hzm_atc_bg"),
    "hub": (-3.330, -3.3205, 1.0, (3.72, 4.38), (3.687, 4.413), HBAKE, "hzm_hub_bg"),
}


def game(x, y, z):
    return (y * S, -x * S, z * S)


mdir, tdir, sdir = (os.path.join(out, d) for d in ("models/menu", "textures/menu", "scripts"))
for d in (mdir, tdir, sdir):
    os.makedirs(d, exist_ok=True)

# ---- the frosted glass: 128 x 192 (0.66 x 0.95 m)
W, H = 128, 192
rng = np.random.default_rng(1943)
yy = np.linspace(0, 1, H)[:, None] * np.ones((1, W))        # 0 = top
xx = np.ones((H, 1)) * np.linspace(0, 1, W)[None, :]
top, bot = np.array([96, 98, 98], float), np.array([70, 71, 70], float)     # QA: at 112 / 90 it read as a blank light panel
fall = 0.5 - 0.5 * np.cos(np.pi * yy)
img = top * (1 - fall[..., None]) + bot * fall[..., None]
glow = np.exp(-(((xx - 0.5) / 0.42) ** 2 + ((yy - 0.38) / 0.55) ** 2))       # light from the room beyond, diffused by the frosting
img *= (0.86 + 0.30 * glow)[..., None]
mott = Image.fromarray((rng.random((H // 8, W // 8)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(5))
img *= (1 + (np.asarray(mott, float) / 255 - 0.5) * 0.12)[..., None]           # +-4 % cloud of the acid-etched surface
img *= (1 + (rng.random((H, W)) - 0.5) * 0.04)[..., None]                        # grain
sheen = np.exp(-(((xx * 0.8 + yy * 0.6) - 0.55) / 0.06) ** 2)                    # one faint diagonal reflection
img += (14.0 * sheen)[..., None]
edge = np.minimum(np.minimum(xx, 1 - xx) * W, np.minimum(yy, 1 - yy) * H)
img *= (1 - 0.18 * np.exp(-edge / 2.0) - 0.05 * np.exp(-edge / 10.0))[..., None]   # the stop's shadow line
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(os.path.join(tdir, "hzm_door_pane.jpg"), quality=95)
open(os.path.join(sdir, "hzm_door_pane.shader"), "w", newline="\n").write(
    "// v1.10.62 the MULTIPLAYER door's frosted glass, identical on both sides of the door (gen_door_pane.py)\n"
    "hzm_door_pane\n{\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_door_pane.jpg\n\t\trgbGen identity\n\t}\n}\n")


def leaf_affine(bake, lx, y_range):
    """(y, z) -> atlas (u, v) of the leaf's big room-side face in that bake (its two largest triangles on the plane)"""
    d = np.load(os.path.join(bake, "bg.npz"))
    P, U = d["pos"].astype(float), d["uv"].astype(float)
    A = np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1) / 2
    m = (np.abs(P[:, :, 0] - lx) < 0.004).all(1) & (P[:, :, 1] > y_range[0] - 0.3).all(1) & (P[:, :, 1] < y_range[1] + 0.3).all(1)
    sel = np.where(m)[0]
    sel = sel[np.argsort(-A[sel])][:2]
    assert len(sel) == 2 and A[sel].min() > 0.8, ("leaf face not found", bake, A[sel])
    M = np.c_[P[sel].reshape(-1, 3)[:, 1:], np.ones(6)]
    F = np.linalg.lstsq(M, U[sel].reshape(-1, 2), rcond=None)[0]
    err = np.abs(M @ F - U[sel].reshape(-1, 2)).max()
    assert err < 1e-3, err
    Ys = P[sel].reshape(-1, 3)[:, 1]
    return (lambda y, z: tuple(np.array([y, z, 1.0]) @ F)), (float(Ys.min()), float(Ys.max()))


def remap(uvf, dst, src):
    """uv for a frame strip: its (y, z) mapped linearly from the strip `dst` onto a leaf area `src` that the baked pane does
    not cover (the leaf face UNDER the pane baked in the pane's shadow - grey / dark - so it is never sampled)"""
    (dy0, dy1, dz0, dz1), (sy0, sy1, sz0, sz1) = dst, src
    return lambda y, z: uvf(sy0 + (y - dy0) / (dy1 - dy0) * (sy1 - sy0), sz0 + (z - dz0) / (dz1 - dz0) * (sz1 - sz0))


def quad(x, ya, yb, za, zb, uvf, nx):
    """a rectangle in the plane x, corners (ya..yb, za..zb), facing nx; uvf(y, z) -> (u, v) in the bake's convention"""
    cs = [(ya, zb), (yb, zb), (yb, za), (ya, za)]
    P = [game(x, y, z) for y, z in cs]
    UV = [uvf(y, z) for y, z in cs]
    return P, UV


def surface(name, quads, nx):
    verts, tris = [], []
    n = np.array(game(nx, 0, 0))
    n = tuple(n / np.linalg.norm(n))
    for P, UV in quads:
        b = len(verts)
        for i in range(4):
            u, v = UV[i]
            verts.append((n, (u, 1.0 - v), 0, P[i]))           # skd v runs down (build_models2 flips the bake's v the same way)
        p = np.array(P)
        t = [[b, b + 1, b + 2], [b, b + 2, b + 3]]
        if np.dot(np.cross(p[1] - p[0], p[2] - p[0]), n) > 0:
            t = [r[::-1] for r in t]
        tris += t
    return (name, np.array(tris), verts)


for side, (lx, ox, nx, gy, py, bake, bgsh) in SIDES.items():
    uvf, (ly0, ly1) = leaf_affine(bake, lx, gy)
    g0, g1 = gy
    p0, p1 = py
    # sources: the leaf beside the pane (its stiles, same heights) and above it (the top rail) - lit wood on this side
    top = (PZ[1] + 0.006, PZ[1] + 0.006 + (PZ[1] - GZ[1]))
    frame = [quad(ox, p0, g0, PZ[0], PZ[1], remap(uvf, (p0, g0, PZ[0], PZ[1]), (ly0 + 0.006, p0 - 0.003, PZ[0], PZ[1])), nx),
             quad(ox, g1, p1, PZ[0], PZ[1], remap(uvf, (g1, p1, PZ[0], PZ[1]), (p1 + 0.003, ly1 - 0.006, PZ[0], PZ[1])), nx),
             quad(ox, g0, g1, PZ[0], GZ[0], remap(uvf, (g0, g1, PZ[0], GZ[0]), (g0, g1) + top), nx),
             quad(ox, g0, g1, GZ[1], PZ[1], remap(uvf, (g0, g1, GZ[1], PZ[1]), (g0, g1) + top), nx)]
    # glass: u to the viewer's right (attic viewer faces +X: right is -Y; MP room viewer faces -X: right is +Y); v up here, the
    # skd flip in surface() puts the texture's top row at the glass top
    ya, yb = (g1, g0) if nx < 0 else (g0, g1)
    gl = quad(ox, ya, yb, GZ[0], GZ[1], lambda y, z: ((y - ya) / (yb - ya), (z - GZ[0]) / (GZ[1] - GZ[0])), nx)
    surfs = [surface("frame", frame, nx), surface("glass", [gl], nx)]
    name = "hzm_door_pane_%s" % side
    open(os.path.join(mdir, name + ".skd"), "wb").write(X.build_skd(name, [("root", "worldbone")], surfs))
    allp = np.array([v[3] for s in surfs for v in s[2]])
    lo, hi = allp.min(0) - 1, allp.max(0) + 1
    open(os.path.join(mdir, name + ".skc"), "wb").write(X.build_skc(["root pos", "root rot"], [[(0, 0, 0, 0), (0, 0, 0, 1)]], 0.1,
                                                                     lo.tolist(), hi.tolist(), float(np.linalg.norm(allp, axis=1).max()) + 1))
    open(os.path.join(mdir, name + ".tik"), "w", newline="\n").write(
        "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel %s.skd\n\tsurface frame shader %s\n\tsurface glass shader hzm_door_pane\n}\n\n"
        "init\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle %s.skc\n}\n" % (name, bgsh, name))
    print(side, "frame on", bgsh, "glass", np.round(allp.min(0), 1), np.round(allp.max(0), 1))
