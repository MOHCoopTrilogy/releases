"""patch_wx73.py <mod ui dir> - v1.10.73 urc side of gen_rain73.py (idempotent).

* every scene carrying the skylight's cloud deck (hzm_wx_top_cloud: main.urc, the New Game wall-map copies) gets the scud layer
  right after it (scenemodel + scenewx role 'cloud').
* LOOK UP (ui_atcStop 4): the camera stands on the skylight's normal and looks straight up it, close enough that the pane fills
  most of the view (user: "the skylight pane is small in frame, sitting in a big expanse of plain ceiling, with a lamp cord crossing
  the view"). Skylight centre (202.65, 152.25, 157.2), normal (0, 0.4205, 0.9073) (gen_window_view SKY_CORNERS); 52 u up the
  slope x 59 u across. At 56 u out with a 50 deg vertical fov the pane is ~0.95 of the frame height (a strip of its reveal and
  frame round it); yaw 90 / pitch -65.1 = along the normal.
"""
import math, os, re, sys

ui = sys.argv[1]
C = (202.65, 152.25, 157.2)
N = (0.0, 0.4205, 0.9073)
D, FOV = 56.0, 50.0
cam = tuple(C[i] - N[i] * D for i in range(3))
pitch = -math.degrees(math.asin(N[2]))
POSE = "%.1f %.1f %.1f %.2f 90.00 0.00 %.2f" % (cam[0], cam[1], cam[2], pitch, FOV)
OLD = "202.7 112.4 70.5 -65.50 90.00 0.00 70.00"
n_files = 0
for f in sorted(os.listdir(ui)):
    if not f.lower().endswith((".urc", ".inc")):
        continue
    p = os.path.join(ui, f)
    t = open(p, encoding="latin-1", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    t0 = t
    t = t.replace(OLD, POSE)
    if 'scenemodel "models/menu/hzm_wx_top_cloud.tik"' in t and "hzm_wx_top_scud" not in t:
        t = re.sub(r'(scenemodel "models/menu/hzm_wx_top_cloud\.tik" 0 0 0 0\r?\n)',
                   lambda m: m.group(1) + 'scenemodel "models/menu/hzm_wx_top_scud.tik" 0 0 0 0' + nl, t, count=1)
        t = re.sub(r'(scenewx "hzm_wx_top_cloud" cloud\r?\n)', lambda m: m.group(1) + 'scenewx "hzm_wx_top_scud" cloud' + nl, t, count=1)
        assert t.count("hzm_wx_top_scud") == 2, f
    if t != t0:
        open(p, "w", encoding="latin-1", newline="").write(t)
        n_files += 1
print("patch_wx73: %d files; LOOK UP pose %s" % (n_files, POSE))
