"""patch_attic_at.py <mod ui dir> <target_at json> - the urc side of gen_target_at.py (the TRAINING practice target).  [advtrain 2026-11-10]
Idempotent: every line it adds is recognisable (hzm_at_target models, the "training" hotspot, the scenelight whose radius ends in
.21, the two widgets) and is removed first. Copy of patch_attic70.py (v1.10.70 OWN DISCS), runs after it.

main.urc (scene "atticscene")
  * the easel and its lit copy (hidden until hovered: scenemodelhide ... 1; scenehotfx shows the lit copy and hides the plain one),
    one warm fill light in front of it (the easel is lightingSpherical; the room is baked).
  * hotspot "training", appended LAST (ui_scene_hot is the 1-based list position - filmroom README): caption TRAINING on the
    hanging chalk sign, a proxy Button (mouse / keyboard / pad focus like the others). Its hit box is the easel's projected
    outline at the home view, clipped so it clears every other home hotspot.
  * click: the camera flies to the target card (sceneleave, scenefly, veil - the OWN DISCS recipe), then the TRAINING sheet
    opens (pushmenu coop_training: Basic Training / Advanced Training). Its BACK / ESC pops back to the attic, which flies home.
hzm_records3d.urc / hzm_medals3d.urc (the attic seen from the long desk, every attic model copied): the plain easel only.
"""
import json, math, os, re, sys
import numpy as np

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\menus3d")
import scene_params as SP  # noqa: E402

ui, js = sys.argv[1:3]
A = json.load(open(js))
NAME, CAP = "training", "TRAINING"
MD = "hzm_at_target"


def rd(p):
    t = open(p, "rb").read().decode("latin-1")
    return t.replace("\r\n", "\n"), ("\r\n" if "\r\n" in t else "\n")


def wr(p, t, nl):
    open(p, "wb").write(t.replace("\n", nl).encode("latin-1"))


def strip_at(t):
    t = re.sub(r'(?m)^(?:scenemodel|scenemodelhide) "(?:models/menu/)?%s[^\n]*\n' % MD, "", t)
    t = re.sub(r'(?m)^scenelight (?:\S+ ){3}\d+\.21 [^\n]*\n', "", t)
    t = re.sub(r'(?m)^(?:scenehot|scenehotbox|scenehotfx) "%s" [^\n]*\n' % NAME, "", t)
    t = re.sub(r'(?m)^scenelabel "atticsign_%s" [^\n]*\n' % NAME, "", t)
    for w in ("atticsign_" + NAME, "hot_" + NAME):
        t = re.sub(r'resource\n\w+\n\{\nname "%s"\n.*?\n\}\n' % re.escape(w), "", t, flags=re.S)
    return t


def cam_of(blk):
    return [float(v) for v in re.search(r"(?m)^scenecam (.*)$", blk).group(1).split()]


def project(p, cam, W=1920.0, H=1080.0):
    org = np.array(cam[:3])
    f, left, up = SP.axes_from_angles(*cam[3:6])
    F = (H / 2) / math.tan(math.radians(cam[6]) / 2)
    c = np.asarray(p, float) - org
    x, y, z = c @ f, c @ left, c @ up
    return W / 2 - y / x * F, H / 2 - z / x * F, x


def pose_to(cam, pt, fov):
    d = [pt[i] - cam[i] for i in range(3)]
    return "%.1f %.1f %.1f %.2f %.2f 0.00 %.2f" % (cam[0], cam[1], cam[2], -math.degrees(math.atan2(d[2], math.hypot(d[0], d[1]))),
                                                   math.degrees(math.atan2(d[1], d[0])), fov)


def hot_rects(blk, cam):
    """every home (stop 0 / none) hotspot's hit rect at 1080p - the engine's rule: the projected radius square, or the scenehotbox"""
    boxes = {m.group(1): [float(v) for v in m.groups()[1:]] for m in re.finditer(r'(?m)^scenehotbox "(\w+)" (\S+) (\S+) (\S+) (\S+)', blk)}
    out = {}
    for m in re.finditer(r'(?m)^scenehot "(\w+)" (\S+) (\S+) (\S+) (\S+) "(?:[^"\\]|\\.)*" "[^"]*" "[^"]*"(?: (-?\d+))?', blk):
        if m.group(6) not in (None, "0", "-1"):
            continue
        sx, sy, dep = project([float(m.group(i)) for i in (2, 3, 4)], cam)
        r = float(m.group(5)) / dep * (540.0 / math.tan(math.radians(cam[6]) / 2))
        cx, cy, hx, hy = sx, sy, r, r
        if m.group(1) in boxes:
            b = boxes[m.group(1)]
            cx, cy, hx, hy = sx + b[0], sy + b[1], b[2], b[3]
        out[m.group(1)] = (cx - hx, cy - hy, cx + hx, cy + hy)
    return out


mp = os.path.join(ui, "main.urc")
m, nl = rd(mp)
m = strip_at(m)
s0 = m.index('name "atticscene"')
s1 = m.index("\n}\n", s0)
blk = m[s0:s1]
cam = cam_of(blk)
n0 = len(re.findall(r'(?m)^scenehot "', blk))
idx = n0 + 1
assert re.search(r'(?m)^scenehot "byodisc" ', blk), "run after patch_attic70.py (v1.10.70 OWN DISCS must already be hotspot 19)"
others = hot_rects(blk, cam)

# ---- the hit box: the easel's outline at the home view (the card and the board up to the cross-piece, the legs to the floor),
#      then pulled in off every other hotspot (6 px apart)
lo, hi, C = np.array(A["lo"]), np.array(A["hi"]), np.array(A["centre"])
pts = [project(q, cam) for q in A["hull"]]          # the easel's own vertices (an AABB of a turned easel is far wider)
r = [min(p[0] for p in pts) - 4, min(p[1] for p in pts) - 4, max(p[0] for p in pts) + 4, max(p[1] for p in pts) + 4]
for n, o in others.items():
    if r[0] < o[2] and r[2] > o[0] and r[1] < o[3] and r[3] > o[1]:
        cuts = {"l": (o[2] + 6 - r[0]) * (r[3] - r[1]), "t": (o[3] + 6 - r[1]) * (r[2] - r[0]),
                "r": (r[2] - (o[0] - 6)) * (r[3] - r[1]), "b": (r[3] - (o[1] - 6)) * (r[2] - r[0])}
        k = min(cuts, key=cuts.get)
        if k == "l":
            r[0] = o[2] + 6
        elif k == "t":
            r[1] = o[3] + 6
        elif k == "r":
            r[2] = o[0] - 6
        else:
            r[3] = o[1] - 6
        print("hit box clipped (%s) off %s" % (k, n))
for n, o in others.items():
    assert not (r[0] < o[2] and r[2] > o[0] and r[1] < o[3] and r[3] > o[1]), ("still overlaps", n, r, o)
assert r[0] >= 0 and r[2] <= 1920 and r[1] >= 0 and r[3] <= 1080, ("hit box off screen", r)
sx, sy, _ = project(C, cam)
box = tuple(float(v) for v in ((r[0] + r[2]) / 2 - sx, (r[1] + r[3]) / 2 - sy, (r[2] - r[0]) / 2, (r[3] - r[1]) / 2))
r = [float(v) for v in r]

# ---- the click: fly to the target card, square on to it (from its front, a little above), then the sheet
CARD = np.array(A["card"])
az = math.radians(A["front_az"])
fly_cam = (CARD[0] + 62.0 * math.cos(az), CARD[1] + 62.0 * math.sin(az), CARD[2] + 10.0)
FLY = pose_to(fly_cam, CARD, 42.0)
cmd = ("set ui_scene_hot 0; globalwidgetcommand atticscene sceneleave; globalwidgetcommand atticscene scenefly 0.6 %s; "
       "uiafter 0.45 uiveil 1 0.15; uiafter 0.6 pushmenu coop_training; uiafter 0.62 uiveil 0 0.2" % FLY)
# the fill light: in front of the easel, above head height, on the camera's side (radius .21 marks it as ours)
lp = (CARD[0] + 40.0 * math.cos(math.radians(A["cam_az"])), CARD[1] + 40.0 * math.sin(math.radians(A["cam_az"])), 96.0)
LIGHT = "scenelight %.1f %.1f %.1f 90.21 0.42 0.37 0.30" % lp
sign = re.search(r'(?m)^scenelabel "atticsign_bugbox" (.*)$', blk).group(1)
add = A["lines"] + ['scenemodelhide "%s_lit" 1' % MD, LIGHT,
                    'scenehot "%s" %.1f %.1f %.1f 12.0 "%s" "%s" "hot_%s" 0' % (NAME, C[0], C[1], C[2], cmd, CAP, NAME),
                    'scenelabel "atticsign_%s" %s' % (NAME, sign),
                    'scenehotbox "%s" %.1f %.1f %.1f %.1f' % ((NAME,) + box),
                    'scenehotfx "%s" "-" 0 "-" "-" "%s_lit" "%s"' % (NAME, MD, MD)]
m = m[:s1] + "\n" + "\n".join(add) + m[s1:]
blk2 = m[s0:m.index("\n}\n", s0)]
hots = re.findall(r'(?m)^scenehot "(\w+)"', blk2)
assert len(hots) == idx and hots[-1] == NAME and hots[18] == "byodisc", hots

# ---- widgets: the caption (the bug box's chalk style) and the proxy, after the OWN DISCS pair
lab = re.search(r'resource\nLabel\n\{\nname "atticsign_bugbox"\n(.*?)\n\}\n', m, re.S).group(1)
btn = re.search(r'resource\nButton\n\{\nname "hot_bugbox"\n(.*?)\n\}\n', m, re.S).group(1)
lab = re.sub(r'(?m)^title ".*"$', 'title "%s"' % CAP, lab)
lab = re.sub(r'(?m)^enabledcvar ".*"$', 'enabledcvar "ui_atticActive==1 ui_scene_hot==%d"' % idx, lab)
btn = re.sub(r'(?m)^stuffcommand ".*"$', lambda _m: 'stuffcommand "%s"' % cmd, btn)
btn = re.sub(r'(?m)^hovercommand ".*"$', 'hovercommand "set ui_scene_hot %d"' % idx, btn)
assert 'title "%s"' % CAP in lab and "ui_scene_hot==%d" % idx in lab and "pushmenu coop_training" in btn and "set ui_scene_hot %d\"" % idx in btn
blk_w = 'resource\nLabel\n{\nname "atticsign_%s"\n%s\n}\nresource\nButton\n{\nname "hot_%s"\n%s\n}\n' % (NAME, lab, NAME, btn)
mm = re.search(r'resource\nButton\n\{\nname "hot_byodisc"\n.*?\n\}\n', m, re.S)
m = m[:mm.end()] + blk_w + m[mm.end():]
wr(mp, m, nl)
print("main.urc: hotspot %d '%s' at %s, box %s (1080p rect %s), fly %s" % (idx, NAME, C.tolist(), [round(v, 1) for v in box],
                                                                          [round(v) for v in r], FLY))

# ---- the other views of the attic: the plain easel
for f in ("hzm_records3d.urc", "hzm_medals3d.urc"):
    p = os.path.join(ui, f)
    t, tnl = rd(p)
    t = strip_at(t)
    j = t.index('scenemodel "models/menu/atc_projector1.tik"')
    j = t.index("\n", j) + 1
    t = t[:j] + A["lines"][0] + "\n" + t[j:]
    wr(p, t, tnl)
    print("%s: the easel" % f)
json.dump(dict(idx=idx, box=box, rect=r, fly=FLY, light=LIGHT), open(os.path.join(os.path.dirname(os.path.abspath(js)), "target_at_urc.json"), "w"), indent=1)
