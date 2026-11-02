"""hub_build_models.py <bake dir> <stage dir> [--scale 52.5] - the attic model builder (menus3d/build_models2.py) on the hub bake.

Not a fork: build_models2.py is executed with its names swapped (asserted), so the hub models can never collide with the
attic's in the shared pk3:  models/menu/atc_* -> hub_*,  textures/menu/hzm_atc_* -> hzm_hub_*,  scripts/hzm_atcscene.shader ->
hzm_hubscene.shader, skeleton atticg -> hubg, groups = the hub's (bg, chrome, floor) + the lettered boards as image x lightmap quads (hub_q_*), no attic cut boxes."""
import os, sys

SRC = os.path.join(r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\menus3d", "build_models2.py")
code = open(SRC, encoding="utf-8").read()
SWAP = [
    ('GROUPS = ["bg", "wallmap", "nook", "radio", "chalk", "fan", "chrome", "projector", "floor"]', 'GROUPS = ["bg", "srb", "gtb", "chrome", "floor"]'),
    ('CUT_BOXES = [((-3.90, 3.10, 2.10), (-3.30, 3.65, 2.65))]', 'CUT_BOXES = []'),
    ('name = "atc_%s%d" % (g, m + 1)', 'name = "hub_%s%d" % (g, m + 1)'),
    ('X.build_skd("atticg"', 'X.build_skd("hubg"'),
    ('"hzm_atcscene.shader"', '"hzm_hubscene.shader"'),
    ('"// slice 1 attic: baked groups', '"// 3D multiplayer hub (mphub3d): baked groups'),
]
for a, b in SWAP:
    assert code.count(a) == 1, "build_models2 changed (%s): update hub_build_models.py" % a[:40]
    code = code.replace(a, b)
n = code.count("hzm_atc_")
assert n >= 8, n
code = code.replace("hzm_atc_", "hzm_hub_")
assert "atc_" not in code.replace("hzm_hub_", ""), [l for l in code.splitlines() if "atc_" in l.replace("hzm_hub_", "")]
# the lettered boards (hub_bake.py QUAD_POST): source image (exposure folded in, like the floor tile) x its own lightmap
QUADS = r"""
qj = os.path.join(bake, "quads.json")
QJ = json.load(open(qj)) if os.path.exists(qj) else {}
qsh = []
for qn, q in sorted(QJ.items()):
    d = dict(np.load(os.path.join(bake, "q_%s.npz" % qn)))
    P = conv(d["pos"].astype(np.float64)) * scale
    N = conv(d["nrm"].astype(np.float64))
    UV = d["uv"].astype(np.float64).copy()
    UV[..., 1] = 1.0 - UV[..., 1]
    corners = []
    for t in range(len(P)):
        p, n, u = P[t], N[t], UV[t]
        c = [(0, p[k], n[k], u[k]) for k in range(3)]
        if np.dot(np.cross(p[1] - p[0], p[2] - p[0]), n.sum(0)) > 0:
            c = [c[0], c[2], c[1]]
        corners.append(c)
    surfs = X.split_surfaces("s", corners)
    surfs = [("q%d" % (i + 1), s_[1], s_[2]) for i, s_ in enumerate(surfs)]
    allv = np.array([np.asarray(v[3]) for s_ in surfs for v in s_[2]])
    name = "hub_q_" + qn
    sh = "hzm_hub_q_" + qn
    open(os.path.join(mdir, name + ".skd"), "wb").write(X.build_skd("hubg", [("origin", "worldbone")], surfs))
    open(os.path.join(mdir, name + ".skc"), "wb").write(X.build_skc(["origin pos", "origin rot"], [[(0, 0, 0, 0), (0, 0, 0, 1)]], 0.1, allv.min(0).tolist(), allv.max(0).tolist(), float(np.linalg.norm(allv, axis=1).max())))
    open(os.path.join(mdir, name + ".tik"), "w", newline="\n").write(
        "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel %s.skd\n%s\n}\n\ninit\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle %s.skc\n}\n"
        % (name, "\n".join("\tsurface %s shader %s" % (s_[0], sh) for s_ in surfs), name))
    Emax = 0.92 / q["lm_scale"]
    k = float(os.environ.get("QUAD_EXPOSURE", "1.0"))
    src = np.asarray(Image.open(q["image"]).convert("RGB")).astype(np.float64) / 255.0
    tdisp = np.clip(srgb(np.clip(lin(src) * Emax * k, 0, 1)) / srgb(0.92), 0, 1)
    Image.fromarray((tdisp * 255 + 0.5).astype(np.uint8)).save(os.path.join(tdir, sh + ".jpg"), quality=95)
    Image.open(os.path.join(bake, "q_%s_lm.png" % qn)).convert("RGB").save(os.path.join(tdir, sh + "_lm.jpg"), quality=95)
    qsh.append("%s\n{\n\tcull none\n\t{\n\t\tclampmap textures/menu/%s.jpg\n\t\trgbGen identity\n\t}\n\t{\n\t\tclampmap textures/menu/%s_lm.jpg\n\t\tblendFunc filter\n\t\trgbGen identity\n\t}\n}\n" % (sh, sh, sh))
    info["groups"]["q_" + qn] = {"models": 1, "surfaces": len(surfs), "tris": int(len(P)), "Emax": Emax}
if qsh:
    open(os.path.join(sdir, "hzm_hubscene.shader"), "a", newline="\n").write("\n".join(qsh))
    json.dump(info, open(os.path.join(out, "build.json"), "w"), indent=1)
    print("quads", sorted(QJ))
"""
exec(compile(code + QUADS, SRC + " (hub names)", "exec"))
