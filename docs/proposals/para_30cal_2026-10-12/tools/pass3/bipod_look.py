"""bipod_look.py - what is in models/statweapons/mg42/MG42_02.skd (the 'MG42 bipod' the .30 cal stands on): surfaces,
and where the vertices are (bone-local offsets through the one bone's frame-0 pos/rot, * 0.52 = the tik's scale).
Prints a side histogram: for slices of height, the x / y extent."""
import sys, zipfile
sys.path.insert(0, "C:/mohaa-coop-dev/docs/proposals/ironsights_2026-09-28/batches/heavy/tools")
import skdlib as K
z = zipfile.ZipFile(r"G:\GOG\Medal of Honor - Allied Assault War Chest\maintt\zzzzzz-HRRTM_Pak4_Weapons.pk3")
skd = K.read_skd(z.read("models/statweapons/mg42/MG42_02.skd"))
skc = K.read_skc(z.read("models/statweapons/mg42/MG42_02.skc"))
pos = K.skc_channel(skc, 0, skc.channels.index("Object01 pos"))
rot = K.skc_channel(skc, 0, skc.channels.index("Object01 rot"))
print("bone pos", pos, "rot", rot)
M = K.mat4(K.quat_to_mat3(rot), pos[:3])
S = 0.52
for s in skd.surfaces:
    pts = []
    for (normal, texc, wl, ml) in s.verts:
        bi, bw, off = wl[0]
        p = K.xform_point(off, M)
        pts.append((p[0] * S, p[1] * S, p[2] * S))
    xs, ys, zs = zip(*pts)
    print("surface %-10s verts %4d  x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f" % (s.name, len(pts), min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
    lo, hi = min(zs), max(zs)
    n = 12
    for i in range(n):
        a, b = lo + (hi - lo) * i / n, lo + (hi - lo) * (i + 1) / n
        sl = [p for p in pts if a <= p[2] <= b]
        if sl:
            print("   z %6.1f..%6.1f  n=%3d  x %6.1f..%6.1f  y %6.1f..%6.1f" % (a, b, len(sl), min(p[0] for p in sl), max(p[0] for p in sl), min(p[1] for p in sl), max(p[1] for p in sl)))
