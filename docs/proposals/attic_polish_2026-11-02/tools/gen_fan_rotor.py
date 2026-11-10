"""gen_fan_rotor.py <bake dir> <out dir> <rotor_axis.json> - v1.10.62: the attic wall fan's blades spin.

The four blades + the spinner (attic62_edit.py tags them grp "rotor": invisible to every bake ray, so the room, the cage and the
motor bake with no blade shadow) are baked into their own atlas (attic_bake3 group "rotor") and written here as one skeletal
model whose origin is the hub, with an `idle` loop turning about the motor shaft:
  * axis   = the normal of the plane through the blades' tips (SVD of the blade vertices), signed to point out of the guard
             (away from the motor); centre = the spinner's centre (the shaft end), so the blades turn in place inside the cage
  * speed  = 200 rpm (1200 deg/s): at 60 fps that is 20 deg a frame and at 30 fps 40 deg - always under the 45 deg where a
             four-blade rotor starts to read as turning backwards; keyframes every 0.05 s (Scene3D plays skc frames at 20 fps)
             60 deg apart, one revolution = 6 steps
The cage, motor, badge and canopy stay baked in the room (group "fan")."""
import json, math, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\menus3d")
import skx as X  # noqa: E402
import scene_params as SP  # noqa: E402

bake, out = sys.argv[1], sys.argv[2]
SCALE = 52.5
RPM = 200.0
d = np.load(os.path.join(bake, "rotor.npz"))


def conv(a, k):     # BU -> game on the LAST axis (scene_params.conv indexes the first)
    a = np.asarray(a, np.float64)
    return np.stack([a[..., 1], -a[..., 0], a[..., 2]], -1) * k


P = conv(d["pos"], SCALE)            # game units
N = conv(d["nrm"], 1.0)
UV = d["uv"].astype(np.float64).copy()
UV[..., 1] = 1.0 - UV[..., 1]
info = json.load(open(sys.argv[3]))     # written by attic62_edit next to the .blend (spinner centre, motor centre; BU)
hub = conv(info["hub"], SCALE)
motor = conv(info["motor"], SCALE)
V = P.reshape(-1, 3)
c0 = V.mean(0)
bn = np.linalg.svd(V - c0)[2][2]                  # the blades' own plane normal
axis = conv(info["shaft"], 1.0)                   # the motor shaft (the guard rings' axis)
axis /= np.linalg.norm(axis)
if np.dot(bn, axis) < 0:
    bn = -bn
# the stock blades sit off the shaft (17 deg): turn the rotor about the hub so its plane is square to the shaft, then spin it
# about the shaft - a rotor spun about its own tilted normal would wobble against the cage
v = np.cross(bn, axis)
sa, ca = np.linalg.norm(v), float(np.dot(bn, axis))
K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]) / (sa if sa > 1e-9 else 1)
Rfix = np.eye(3) + K * sa + K @ K * (1 - ca) if sa > 1e-9 else np.eye(3)
print("rotor: %d tris, hub %s, shaft %s, blade plane %.1f deg off it (squared)" % (len(P), np.round(hub, 2), np.round(axis, 3), math.degrees(math.atan2(sa, ca))))
P = (P - hub) @ Rfix.T
N = N @ Rfix.T
corners = []
for t in range(len(P)):
    p, n, u = P[t], N[t], UV[t]
    c = [(0, p[k], n[k], u[k]) for k in range(3)]
    if np.dot(np.cross(p[1] - p[0], p[2] - p[0]), n.sum(0)) > 0:
        c = [c[0], c[2], c[1]]
    corners.append(c)
surfs = X.split_surfaces("r", corners)
mdir, tdir, sdir = (os.path.join(out, x) for x in ("models/menu", "textures/menu", "scripts"))
for x in (mdir, tdir, sdir):
    os.makedirs(x, exist_ok=True)
allv = np.vstack([np.array([v[3] for v in s[2]]) for s in surfs])
lo, hi, rad = allv.min(0) - 1, allv.max(0) + 1, float(np.linalg.norm(allv, axis=1).max()) + 1
open(os.path.join(mdir, "hzm_fan_rotor.skd"), "wb").write(X.build_skd("hzm_fan_rotor", [("root", "worldbone")], surfs))
STEP = 60.0                                       # deg per 0.05 s keyframe = 1200 deg/s = 200 rpm
assert abs(STEP / 0.05 / 6.0 - RPM) < 1e-6
frames = []
for k in range(7):                                # 0..360 deg, the last = the first (seamless loop)
    a = math.radians(STEP * k) / 2
    q = (axis[0] * math.sin(a), axis[1] * math.sin(a), axis[2] * math.sin(a), math.cos(a))
    frames.append([(0, 0, 0, 0), q])
open(os.path.join(mdir, "hzm_fan_rotor.skc"), "wb").write(X.build_skc(["root pos", "root rot"], frames, 0.05, lo.tolist(), hi.tolist(), rad))
open(os.path.join(mdir, "hzm_fan_rotor.tik"), "w", newline="\n").write(
    "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel hzm_fan_rotor.skd\n" +
    "".join("\tsurface %s shader hzm_fan_rotor\n" % s[0] for s in surfs) +
    "}\n\ninit\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n\tidle hzm_fan_rotor.skc\n}\n")
# the satin stand-in for the metal bakes too light (the blades read as pale wood in game, QA 2026-11-03): x0.62 on a warm curve,
# so with the env sheen on top they read as aged brass, in the room's own range
_im = np.asarray(Image.open(os.path.join(bake, "rotor.png")).convert("RGB")).astype(np.float32) * np.array([0.66, 0.58, 0.44])
Image.fromarray(np.clip(_im, 0, 255).astype(np.uint8)).save(os.path.join(tdir, "hzm_fan_rotor.jpg"), quality=95)
open(os.path.join(sdir, "hzm_fan_rotor.shader"), "w", newline="\n").write(
    "// v1.10.62 the attic fan's spinning blades (gen_fan_rotor.py): fullbright, the lighting is baked in\n"
    "hzm_fan_rotor\n{\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_fan_rotor.jpg\n\t\trgbGen identity\n\t}\n"
    "\t{\n\t\tmap textures/menu/hzm_atc_env45.jpg\n\t\ttcGen environment\n\t\tblendFunc add\n\t\trgbGen identity\n\t}\n}\n")   # brass sheen (baked satin: rotor_visible.py)
json.dump({"hub_game": hub.tolist(), "axis_game": axis.tolist(), "rpm": RPM}, open(os.path.join(out, "fan_rotor.json"), "w"), indent=1)
print("hzm_fan_rotor: %d surfaces, scenemodel at %.1f %.1f %.1f" % (len(surfs), hub[0], hub[1], hub[2]))
