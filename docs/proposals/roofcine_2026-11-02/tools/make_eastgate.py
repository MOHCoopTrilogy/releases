"""make_eastgate.py <in.bsp> <out.bsp> - map v10b: the hidden east halftrack start (user 2026-11-02).
* crumble_eastwall_2 (the east wall between y 350 and 530, x 1472..1488, z -512..-296: 216 u high, 180 u wide - the halftrack hull is
  ~260 x 130 x 130) is renamed coop_fin_eastgate2: a script_object that looks and collides exactly like the stock wall. Script slides it out
  of the way (out 24 u east, then 190 u north, behind the wall) to open, and back to close (coop_mod/finale_m2l3_eastgate.scr).
* coop_fin_eastgate2_clip: a permanent brush entity filling the opening (x 1460..1500, y 350..530, z -512..-296) whose brush contents are
  PLAYERCLIP | MONSTERCLIP. Players (MASK_PLAYERSOLID) and AI (MASK_MONSTERSOLID) are stopped by it even while the gate is open;
  vehicles (MASK_VEHICLE has neither bit, fgame/bg_public.h) drive through. Invisible (no surface).
* coop_fin_eastramp: a snow bank outside the gate (the floor drops 64 u at x 1664: too high a step for the halftrack).
A 3rd argument <assets dir> writes scripts/hzm_eastgate.shader (ship it in the map pak)."""
import os, sys, struct, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "v7"))
import bspedit as E

b = E.Bsp(open(sys.argv[1], "rb").read())
names = [x[0] for x in b.shaders()]
shl = b.get("shaders")
nm = "textures/hzm/eastgate_clip"
if nm not in names:
    rec = bytearray(140); rec[:len(nm)] = nm.encode(); struct.pack_into("<3i", rec, 64, 0x80, 0x10000 | 0x20000, 0)
    shl.extend(rec); names.append(nm)
SH = names.index(nm)
plL, bl, sl, mdl = (b.get(n) for n in ("planes", "brushes", "brushsides", "models"))
o = (1480.0, 440.0, -404.0)
mn = (1460.0, 350.0, -512.0); mx = (1500.0, 530.0, -296.0)
s0 = len(sl) // 12
for a in range(3):
    for sg, val in ((-1, mn[a]), (1, mx[a])):
        n = [0.0, 0.0, 0.0]; n[a] = float(sg)
        pi = len(plL) // 16; plL.extend(struct.pack("<4f", n[0], n[1], n[2], sg * val - sg * o[a]))
        sl.extend(struct.pack("<3i", pi, SH, 0))
b0 = len(bl) // 12
bl.extend(struct.pack("<3i", s0, 6, SH))
mi = len(mdl) // 40
lo = [mn[k] - o[k] for k in range(3)]; hi = [mx[k] - o[k] for k in range(3)]
mdl.extend(struct.pack("<6f4i", *lo, *hi, len(b.get("surfaces")) // 108, 0, b0, 1))
# --- the ramp: outside the wall the floor drops 64 u at x 1664 (snowclip floor -512 -> ground -576); a halftrack cannot climb a 64 u
# step, so a snow bank slopes it: x 1664..1920, y 330..550, top from z -512 down to -576 (1:4), solid, its top drawn in vertex-lit snow
import math
nm2 = "textures/hzm/eastramp_snow"
if nm2 not in names:
    rec = bytearray(140); rec[:len(nm2)] = nm2.encode(); struct.pack_into("<3i", rec, 64, 0, 1, 0)
    shl.extend(rec); names.append(nm2)
SR = names.index(nm2)
ro = (1792.0, 440.0, -560.0)
rmn = (1664.0, 330.0, -580.0); rmx = (1920.0, 550.0, -512.0)
sl0 = len(sl) // 12
sides = []
for a_ in range(3):
    for sg, val in ((-1, rmn[a_]), (1, rmx[a_])):
        if a_ == 2 and sg == 1:
            continue                       # no flat top: the slope is the top
        n = [0.0, 0.0, 0.0]; n[a_] = float(sg); sides.append((n, sg * val))
L = math.hypot(256.0, 64.0); nx, nz = 64.0 / L, 256.0 / L      # slope normal (+x down-slope, up)
sides.append(([nx, 0.0, nz], nx * 1664.0 + nz * -512.0))
for n, d in sides:
    pi = len(plL) // 16; plL.extend(struct.pack("<4f", n[0], n[1], n[2], d - (n[0] * ro[0] + n[1] * ro[1] + n[2] * ro[2])))
    sl.extend(struct.pack("<3i", pi, SR, 0))
rb0 = len(bl) // 12
bl.extend(struct.pack("<3i", sl0, len(sides), SR))
sfl, dvl, ixl = b.get("surfaces"), b.get("drawverts"), b.get("drawidx")
P = [(1664.0, 330.0, -512.0), (1664.0, 550.0, -512.0), (1920.0, 550.0, -576.0), (1920.0, 330.0, -576.0)]
fv = len(dvl) // 44
for q in P:
    dvl.extend(struct.pack("<3f2f2f3f4B", q[0] - ro[0], q[1] - ro[1], q[2] - ro[2], q[0] / 256.0, q[1] / 256.0, 0, 0, nx, 0, nz, 214, 216, 222, 255))
fi = len(ixl) // 4
ixl.extend(struct.pack("<6i", 0, 1, 2, 0, 2, 3))   # clockwise seen from above (bug-4430)
rec = bytearray(108)
struct.pack_into("<12i", rec, 0, SR, -1, 1, fv, 4, fi, 6, -1, 0, 0, 0, 0)
struct.pack_into("<9f", rec, 60, 0, 0, 0, 0, 0, 0, nx, 0, nz)
rs0 = len(sfl) // 108
sfl.extend(rec)
mr = len(mdl) // 40
mdl.extend(struct.pack("<6f4i", rmn[0] - ro[0], rmn[1] - ro[1], rmn[2] - ro[2], rmx[0] - ro[0], rmx[1] - ro[1], rmx[2] - ro[2], rs0, 1, rb0, 1))
t = bytes(b.get("ents")).split(b"\0")[0].decode("latin1")
t += '{\n"classname" "script_object"\n"model" "*%d"\n"origin" "%g %g %g"\n"targetname" "coop_fin_eastramp"\n}\n' % (mr, *ro)
n0 = t.count('"targetname" "crumble_eastwall_2"')
assert n0 == 1, n0
t = t.replace('"targetname" "crumble_eastwall_2"', '"targetname" "coop_fin_eastgate2"')
t += '{\n"classname" "script_object"\n"model" "*%d"\n"origin" "%g %g %g"\n"targetname" "coop_fin_eastgate2_clip"\n}\n' % (mi, *o)
b.lumps[E.IX["ents"]] = bytearray(t.encode("latin1") + b"\x00")
open(sys.argv[2], "wb").write(b.tobytes())
print("gate = coop_fin_eastgate2, clip = coop_fin_eastgate2_clip (*%d), ramp = coop_fin_eastramp (*%d)" % (mi, mr))

if len(sys.argv) > 3:
    os.makedirs(os.path.join(sys.argv[3], "scripts"), exist_ok=True)
    open(os.path.join(sys.argv[3], "scripts", "hzm_eastgate.shader"), "w", newline="\n").write(
        "// map v10b (make_eastgate.py)\ntextures/hzm/eastramp_snow\n{\n\tsurfaceparm nolightmap\n\t{\n\t\tmap textures/norway/norsnow_lite256.jpg\n\t\trgbGen vertex\n\t}\n}\n\n"
        "textures/hzm/eastgate_clip\n{\n\tsurfaceparm nodraw\n\tsurfaceparm playerclip\n\tsurfaceparm monsterclip\n\tsurfaceparm nolightmap\n}\n")
