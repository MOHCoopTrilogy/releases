"""patch_attic70.py <mod ui dir> <byo70 json> - v1.10.70 urc side of gen_byodisc70.py (the OWN DISCS film cans). Idempotent: every
line it adds is recognisable (hzm_byo70_ models, the "byodisc" hotspot, the scenelight whose radius ends in .70, the two widgets)
and is removed first. Runs after patch_attic68.py / patch_mproom69.py.

main.urc (scene "atticscene")
  * the cans and their lit copy (hidden until hovered: scenemodelhide ... 1; scenehotfx shows the lit copy and hides the plain one
    - the projector's recipe), one warm fill light over the desk for them (they are lightingSpherical; the room is baked).
  * hotspot "byodisc", appended LAST (ui_scene_hot is the list position): caption OWN DISCS on the hanging chalk sign, a proxy Button
    (mouse / keyboard / pad focus like the others). Its hit box is the cans' projected outline at the home view, clipped so it
    clears every other home hotspot (the projector's FILM ROOM box sits just above-left of it).
  * click: the camera flies down to the cans (the REPORT A BUG toolbox's recipe: sceneleave, scenefly, veil), then the OWN DISCS
    sheet opens (pushmenu coop_byodisc - the sheet reads coop_flHave_1_1 / coop_eaHave_1_11 itself; ui_byoLock 0 as the co-op
    map select's own button sets it). Its CLOSE / ESC pops back to the attic, which flies home as after every other prop.
hzm_records3d.urc / hzm_medals3d.urc (the attic seen from the long desk, every attic model copied): the plain cans only.
"""
import json, math, os, re, sys
import numpy as np

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\menus3d")
import scene_params as SP  # noqa: E402

ui, js = sys.argv[1:3]
A = json.load(open(js))
LIGHT = "scenelight 62.0 -38.0 80.0 60.70 0.40 0.35 0.28"
NAME, CAP = "byodisc", "OWN DISCS"


def rd(p):
    t = open(p, encoding="latin-1", newline="").read()
    return t.replace("\r\n", "\n"), ("\r\n" if "\r\n" in t else "\n")


def wr(p, t, nl):
    open(p, "w", encoding="latin-1", newline="").write(t.replace("\n", nl))


def strip70(t):
    t = re.sub(r'(?m)^(?:scenemodel|scenemodelhide) "(?:models/menu/)?hzm_byo70_[^\n]*\n', "", t)
    t = re.sub(r'(?m)^scenelight (?:\S+ ){3}\d+\.70 [^\n]*\n', "", t)
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
m = strip70(m)
s0 = m.index('name "atticscene"')
s1 = m.index("\n}\n", s0)
blk = m[s0:s1]
cam = cam_of(blk)
n0 = len(re.findall(r'(?m)^scenehot "', blk))
idx = n0 + 1
others = hot_rects(blk, cam)

# ---- the hit box: the cans' outline at the home view, then pulled in off every other hotspot (6 px apart)
lo, hi, C = np.array(A["lo"]), np.array(A["hi"]), np.array(A["centre"])
pts = [project((x, y, z), cam) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
r = [min(p[0] for p in pts) - 4, min(p[1] for p in pts) - 4, max(p[0] for p in pts) + 4, max(p[1] for p in pts) + 4]
for n, o in others.items():
    if r[0] < o[2] and r[2] > o[0] and r[1] < o[3] and r[3] > o[1]:
        # clip the side that loses the least area
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
sx, sy, _ = project(C, cam)
box = ((r[0] + r[2]) / 2 - sx, (r[1] + r[3]) / 2 - sy, (r[2] - r[0]) / 2, (r[3] - r[1]) / 2)

# ---- the click: fly down to the cans (from the room side, the home camera's bearing), then the sheet
az = math.radians(A["cam_az"])
fly_cam = (C[0] + 38.0 * math.cos(az), C[1] + 38.0 * math.sin(az), C[2] + 24.0)
FLY = pose_to(fly_cam, C, 42.0)
cmd = ("set ui_scene_hot 0; set ui_byoLock 0; globalwidgetcommand atticscene sceneleave; globalwidgetcommand atticscene scenefly 0.6 %s; "
       "uiafter 0.45 uiveil 1 0.15; uiafter 0.6 pushmenu coop_byodisc; uiafter 0.62 uiveil 0 0.2" % FLY)
sign = re.search(r'(?m)^scenelabel "atticsign_bugbox" (.*)$', blk).group(1)
add = A["lines"] + ['scenemodelhide "hzm_byo70_cans_lit" 1', LIGHT,
                    'scenehot "%s" %.1f %.1f %.1f 10.0 "%s" "%s" "hot_%s" 0' % (NAME, C[0], C[1], C[2], cmd, CAP, NAME),
                    'scenelabel "atticsign_%s" %s' % (NAME, sign),
                    'scenehotbox "%s" %.1f %.1f %.1f %.1f' % ((NAME,) + box),
                    'scenehotfx "%s" "-" 0 "-" "-" "hzm_byo70_cans_lit" "hzm_byo70_cans"' % NAME]
m = m[:s1] + "\n" + "\n".join(add) + m[s1:]
assert len(re.findall(r'(?m)^scenehot "', m[s0:m.index("\n}\n", s0)])) == idx

# ---- widgets: the caption (the bug box's chalk style) and the proxy, after the LOOK UP pair
lab = re.search(r'resource\nLabel\n\{\nname "atticsign_bugbox"\n(.*?)\n\}\n', m, re.S).group(1)
btn = re.search(r'resource\nButton\n\{\nname "hot_bugbox"\n(.*?)\n\}\n', m, re.S).group(1)
lab = re.sub(r'(?m)^title ".*"$', 'title "%s"' % CAP, lab)
lab = re.sub(r'(?m)^enabledcvar ".*"$', 'enabledcvar "ui_atticActive==1 ui_scene_hot==%d"' % idx, lab)
btn = re.sub(r'(?m)^stuffcommand ".*"$', lambda _m: 'stuffcommand "%s"' % cmd, btn)
btn = re.sub(r'(?m)^hovercommand ".*"$', 'hovercommand "set ui_scene_hot %d"' % idx, btn)
blk_w = 'resource\nLabel\n{\nname "atticsign_%s"\n%s\n}\nresource\nButton\n{\nname "hot_%s"\n%s\n}\n' % (NAME, lab, NAME, btn)
mm = re.search(r'resource\nButton\n\{\nname "hot_lookup"\n.*?\n\}\n', m, re.S)
m = m[:mm.end()] + blk_w + m[mm.end():]
wr(mp, m, nl)
print("main.urc: hotspot %d '%s' at %s, box %s (1080p rect %s), fly %s" % (idx, NAME, C.tolist(), [round(v, 1) for v in box],
                                                                          [round(v) for v in r], FLY))

# ---- the other views of the attic: the plain cans
for f in ("hzm_records3d.urc", "hzm_medals3d.urc"):
    p = os.path.join(ui, f)
    t, tnl = rd(p)
    t = strip70(t)
    j = t.index('scenemodel "models/menu/atc_projector1.tik"')
    j = t.index("\n", j) + 1
    t = t[:j] + A["lines"][0] + "\n" + t[j:]
    wr(p, t, tnl)
    print("%s: the cans" % f)
json.dump(dict(idx=idx, box=box, rect=r, fly=FLY), open(os.path.join(os.path.dirname(os.path.abspath(js)), "byo70_urc.json"), "w"), indent=1)
