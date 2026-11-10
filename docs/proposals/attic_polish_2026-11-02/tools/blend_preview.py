"""blend_preview.py - CPU-only check of an edited attic .blend from the menu's home camera (no Blender render, no GPU).

    blender -b <file.blend> -t 2 --python blend_preview.py -- <out.npz>        dump world triangles + per-object colour key
    python blend_preview.py <out.npz> <out.png> [W H]                          z-buffer them at the menu's home camera

Changed objects (names starting p62_, projector_stock, door_brief_, doorwall0_, rwall_fill, jamb_mp) are drawn in a warm colour,
everything else in flat grey shading, so the edits can be judged in place (overlaps, floating, clipping) before the GPU bake."""
import math, os, sys
import numpy as np

HIGHLIGHT = ("p62_", "p63_", "proj_reels", "projector_stock", "door_brief_", "doorwall0_", "rwall_fill", "jamb_mp")

if "bpy" in sys.modules or os.path.basename(sys.executable).lower().startswith("blender"):
    import bpy
    out = sys.argv[sys.argv.index("--") + 1]
    dg = bpy.context.evaluated_depsgraph_get()
    tris, keys = [], []
    for o in bpy.context.scene.objects:
        if o.type not in ("MESH", "CURVE") or o.hide_render:
            continue
        mats = [s.material.name for s in o.material_slots if s.material]
        if any(m in ("haze", "moon_sky", "moon_sky2", "frosted", "glass") for m in mats):
            continue
        ev = o.evaluated_get(dg)
        try:
            me = ev.to_mesh()
        except Exception:
            continue
        me.calc_loop_triangles()
        M = o.matrix_world
        V = np.array([tuple(M @ v.co) for v in me.vertices], np.float32)
        T = np.array([tuple(t.vertices) for t in me.loop_triangles], np.int32).reshape(-1, 3)
        if len(T):
            tris.append(V[T])
            keys += [1 if o.name.startswith(HIGHLIGHT) else 0] * len(T)
        ev.to_mesh_clear()
    np.savez_compressed(out, tris=np.concatenate(tris), hl=np.array(keys, np.int8))
    print("dumped", sum(len(t) for t in tris))
else:
    sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\menus3d")
    import scene_params as SP
    from PIL import Image
    d = np.load(sys.argv[1])
    out = sys.argv[2]
    W, H = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (1280, 720)
    cam = [-36.7, 21.0, 102.4, 7.01, 0.0, 0.0, 55.11]
    f, l, u = SP.axes_from_angles(*cam[3:6])
    org = np.array(cam[:3])
    F = (H / 2) / math.tan(math.radians(cam[6] / 2))
    P = np.stack([d["tris"][..., 1], -d["tris"][..., 0], d["tris"][..., 2]], -1) * 52.5 - org
    x, y, z = P @ f, P @ l, P @ u
    ok = (x > 1).all(1)
    sx, sy = W / 2 - y / np.maximum(x, 1) * F, H / 2 - z / np.maximum(x, 1) * F
    lo_x, hi_x, lo_y, hi_y = sx.min(1), sx.max(1), sy.min(1), sy.max(1)
    ok &= (hi_x >= 0) & (lo_x < W) & (hi_y >= 0) & (lo_y < H) & ((hi_x - lo_x) < W * 3)
    nrm = np.cross(d["tris"][:, 1] - d["tris"][:, 0], d["tris"][:, 2] - d["tris"][:, 0])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9
    L = np.array([-0.35, -0.55, 0.75]); L /= np.linalg.norm(L)
    shade = 0.25 + 0.75 * np.abs(nrm @ L)
    img = np.full((H, W, 3), 20.0, np.float32)
    zb = np.full((H, W), 1e9, np.float32)
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    for t in np.nonzero(ok)[0]:
        ax, ay, bx, by, cx, cy = sx[t, 0], sy[t, 0], sx[t, 1], sy[t, 1], sx[t, 2], sy[t, 2]
        x0, x1 = int(max(0, lo_x[t])), int(min(W, hi_x[t] + 1))
        y0, y1 = int(max(0, lo_y[t])), int(min(H, hi_y[t] + 1))
        if x0 >= x1 or y0 >= y1:
            continue
        dd = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(dd) < 1e-9:
            continue
        X, Y = xx[y0:y1, x0:x1], yy[y0:y1, x0:x1]
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / dd
        l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / dd
        l3 = 1 - l1 - l2
        ins = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
        zz = l1 * x[t, 0] + l2 * x[t, 1] + l3 * x[t, 2]
        sub = zb[y0:y1, x0:x1]
        m = ins & (zz < sub)
        if m.any():
            sub[m] = zz[m]
            c = np.array([235, 150, 70.0]) if d["hl"][t] else np.array([170, 170, 170.0])
            img[y0:y1, x0:x1][m] = c * shade[t]
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(out)
    print(out)
