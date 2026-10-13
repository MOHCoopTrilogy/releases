"""gun_profile.py - the side profile of models/statweapons/30cal/30cal.skd (surface material1 = what is drawn), in world
units (tik scale 0.52), gun frame (x forward from the pivot, z up): per 4u slice of x the lowest and highest vertex.
Then, for a gun h over the ground behind it and a support edge (bx back, bz under the pivot), the pitch at which the
underside first touches the ground or that edge."""
import math, sys, zipfile
sys.path.insert(0, "C:/mohaa-coop-dev/docs/proposals/ironsights_2026-09-28/batches/heavy/tools")
import skdlib as K
z = zipfile.ZipFile(r"G:\GOG\Medal of Honor - Allied Assault War Chest\maintt\pak1.pk3")
skd = K.read_skd(z.read("models/statweapons/30cal/30cal.skd"))
skc = K.read_skc(z.read("models/statweapons/30cal/30cal.skc"))
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
    pi = next((j for j, bb in enumerate(skd.bones) if bb.name == b.parent), None)
    if pi is not None and pi in mats:
        m = K.mat4_mul(m, mats[pi])
    mats[i] = m
pts = []
for s in skd.surfaces:
    if s.name != "material1":
        continue
    for (normal, texc, wl, ml) in s.verts:
        bi, bw, off = wl[0]
        p = K.xform_point(off, mats[bi])
        pts.append((p[0] * S, p[1] * S, p[2] * S))
xs = [p[0] for p in pts]
print("x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f" % (min(xs), max(xs), min(p[1] for p in pts), max(p[1] for p in pts),
                                                 min(p[2] for p in pts), max(p[2] for p in pts)))
x = math.floor(min(xs) / 4) * 4
while x < max(xs):
    sl = [p for p in pts if x <= p[0] < x + 4]
    if sl:
        print("  x %6.1f..%6.1f n=%4d  z %6.1f..%6.1f  y %6.1f..%6.1f" % (x, x + 4, len(sl), min(p[2] for p in sl), max(p[2] for p in sl),
                                                                    min(p[1] for p in sl), max(p[1] for p in sl)))
    x += 4


def rest(h, edge=None):
    """smallest pitch-up (deg) at which a vertex behind the pivot is on the ground h under it, or under the edge point"""
    best = None
    for t10 in range(0, 801):
        t = math.radians(t10 / 10.0)
        c, s_ = math.cos(t), math.sin(t)
        hit = False
        for (px, py, pz) in pts:
            if px >= 0:
                continue
            wx = px * c - pz * s_          # pitch up: the rear goes down
            wz = px * s_ + pz * c
            if wz <= -h:
                hit = True
                break
            if edge and -edge[0] - 1.5 <= wx <= -edge[0] + 1.5 and wz <= -edge[1]:
                hit = True
                break
        if hit:
            best = t10 / 10.0
            break
    return best


for h in (38.2, 39.3, 44, 48.5, 55, 61.5, 66.5):
    print("h=%5.1f  ground only: %s   bags (rear edge 19.8 back, 13.5 under): %s" % (h, rest(h), rest(h, (19.8, 13.5))))
