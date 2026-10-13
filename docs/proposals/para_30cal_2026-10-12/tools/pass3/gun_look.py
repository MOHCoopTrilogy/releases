"""gun_look.py - the surfaces of models/statweapons/30cal/30cal.skd (Breakthrough pak1): name, vertex count, extent in
world units (tik scale 0.52), through each vertex's first bone at frame 0 of 30cal.skc (bones are treated as roots:
enough to see what stands where)."""
import sys, zipfile
sys.path.insert(0, "C:/mohaa-coop-dev/docs/proposals/ironsights_2026-09-28/batches/heavy/tools")
import skdlib as K
z = zipfile.ZipFile(r"G:\GOG\Medal of Honor - Allied Assault War Chest\maintt\pak1.pk3")
skd = K.read_skd(z.read("models/statweapons/30cal/30cal.skd"))
skc = K.read_skc(z.read("models/statweapons/30cal/30cal.skc"))
print("bones:", [(b.name, b.parent, K.JT_NAMES.get(b.jointType)) for b in skd.bones])
print("channels:", skc.channels)
S = 0.52
mats = {}
for i, b in enumerate(skd.bones):
    try:
        pos = K.skc_channel(skc, 0, skc.channels.index(b.name + " pos"))[:3]
    except ValueError:
        pos = (0, 0, 0)
    try:
        rot = K.skc_channel(skc, 0, skc.channels.index(b.name + " rot"))
    except ValueError:
        rot = (0, 0, 0, 1)
    m = K.mat4(K.quat_to_mat3(rot), pos)
    par = b.parent
    pi = next((j for j, bb in enumerate(skd.bones) if bb.name == par), None)
    if pi is not None and pi in mats:
        m = K.mat4_mul(m, mats[pi])
    mats[i] = m
for s in skd.surfaces:
    pts = []
    for (normal, texc, wl, ml) in s.verts:
        bi, bw, off = wl[0]
        p = K.xform_point(off, mats[bi])
        pts.append((p[0] * S, p[1] * S, p[2] * S))
    xs, ys, zs = zip(*pts)
    print("surface %-12s verts %4d  x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f" % (s.name, len(pts), min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
