"""gen_records3d.py <bake dir> <art dir> <medalbox.json> <out pak dir> <mod ui dir> - v1.10.63: RECORDS in the 3D room.

User: "the 'records' area for personal records needs modernized to 3d as well" + "needs to have continuity there... the box with
medals should be on that table just as it is when you go to it in vanilla".
Vanilla (maintt pak1 ui/war_records.urc): a desk with the closed medal box and two LOAD / SAVE trays; PERSONAL RECORDS (the box)
-> ui/medals.urc: the box open, six medals (g_medalbt0..5, each shown only when earned) with a name plate and a description card
on hover; LOAD / SAVE (the trays) -> `pushmenu_sp loadsave; pushmenu_dm loadsave_mp`; BACK pops.
Here the same desk kit stands on the attic's long desk (attic62_edit section 8: box body + trays baked into the room, the lid its
own baked group) and:
  * hzm_medal_lid: the box's lid on its hinge - outer from the medallid bake, inside = the vanilla case art (gen_records_art.py);
    anims closed / open (0.6 s to upright) / opened / close;
  * menu hzm_records3d: the attic seen from the desk (the camera the attic's RECORDS hotspot flies to): hotspots on the box
    (PERSONAL RECORDS) and the trays (LOAD / SAVE), the vanilla desk sign top right, the vanilla BACK button;
  * menu hzm_medals3d: the camera square on the opened lid; the six medals sit in the case's own recesses (vanilla rects), the
    name plate and description card are the vanilla sign / desc art framed onto the case's brass plate and white card.
BACK / ESC: medals -> the lid closes and the desk view returns; desk -> popmenu, the attic flies home (sceneleave)."""
import json, math, os, re, sys
import numpy as np
from PIL import Image

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\c96_model_2026-10-18\tools")
import skx as X  # noqa: E402

bake, art, mbj, out, ui = sys.argv[1:6]
S = 52.5
MB = json.load(open(mbj))
LAY = json.load(open(os.path.join(art, "medalbox_layout.json")))
mdir, tdir, sdir = (os.path.join(out, d) for d in ("models/menu", "textures/menu", "scripts"))
for d in (mdir, tdir, sdir):
    os.makedirs(d, exist_ok=True)


def conv(a, k=S):
    a = np.asarray(a, np.float64)
    return np.stack([a[..., 1], -a[..., 0], a[..., 2]], -1) * k


X0, X1 = MB["x"]
Y0, Y1 = MB["y"]
ZL, Z1 = MB["zl"], MB["z1"]
HINGE_BU = np.array([(X0 + X1) / 2, Y1, ZL])
HINGE = conv(HINGE_BU)
DEPTH = Y1 - Y0                                     # the lid's depth = its height when upright

# ---- the lid model (origin on the hinge)
d = np.load(os.path.join(bake, "medallid.npz"))
P, N, UV = conv(d["pos"]) - HINGE, conv(d["nrm"], 1.0), d["uv"].astype(np.float64).copy()
UV[..., 1] = 1.0 - UV[..., 1]
corners = []
for t in range(len(P)):
    p, n, u = P[t], N[t], UV[t]
    cc = [(0, p[k], n[k], u[k]) for k in range(3)]
    if np.dot(np.cross(p[1] - p[0], p[2] - p[0]), n.sum(0)) > 0:
        cc = [cc[0], cc[2], cc[1]]
    corners.append(cc)
outer = X.split_surfaces("o", corners)
Image.open(os.path.join(bake, "medallid.png")).convert("RGB").save(os.path.join(tdir, "hzm_medal_lid.jpg"), quality=95)
# the inside: the vanilla case art on the lid's underside, its top (the description card) at the lid's free (front) edge, which
# rises when the lid opens; the viewer then looks +Y (BU) and his right is +X
zi = ZL - 0.0015
quad_bu = [(X0, Y0, zi), (X1, Y0, zi), (X1, Y1, zi), (X0, Y1, zi)]          # front-left, front-right, back-right, back-left
quv = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]                      # skd v down: the art's top row at the front edge
qp = conv(np.array(quad_bu)) - HINGE
nrm = tuple(conv(np.array([0, 0, -1.0]), 1.0))
verts = [(nrm, quv[i], 0, tuple(qp[i])) for i in range(4)]
tris = np.array([[0, 1, 2], [0, 2, 3]])
if np.dot(np.cross(qp[1] - qp[0], qp[2] - qp[0]), nrm) > 0:
    tris = tris[:, ::-1].copy()
surfs = outer + [("inside", tris, verts)]
Image.open(os.path.join(art, "medalbox_inside.png")).convert("RGB").save(os.path.join(tdir, "hzm_medal_inside.jpg"), quality=95)
allv = np.vstack([np.array([v[3] for v in s[2]]) for s in surfs])
rad = float(np.linalg.norm(allv, axis=1).max()) + 2
lo, hi = (-np.ones(3) * rad).tolist(), (np.ones(3) * rad).tolist()
open(os.path.join(mdir, "hzm_medal_lid.skd"), "wb").write(X.build_skd("hzm_medal_lid", [("root", "worldbone")], surfs))
# the hinge runs along BU +X = game -Y; opening lifts the front edge: -90 deg about BU +X.  The skc quaternion is applied the
# way the clock hands showed (gen_clock.py: +angle/2 gave the intended turn), so the sign is set from that.
AX = conv(np.array([1.0, 0, 0]), 1.0)


def q(deg):
    t = math.radians(deg) / 2
    return (AX[0] * math.sin(t), AX[1] * math.sin(t), AX[2] * math.sin(t), math.cos(t))


OPEN_SIGN = float(os.environ.get("LID_SIGN", "1"))
ANIMS = {"closed": [0.0], "opened": [90.0], "open": [90.0 * (0.5 - 0.5 * math.cos(math.pi * k / 12)) for k in range(13)],
         "close": [90.0 * (0.5 + 0.5 * math.cos(math.pi * k / 12)) for k in range(13)]}
for an, degs in ANIMS.items():
    fr = [[(0, 0, 0, 0), q(OPEN_SIGN * dg)] for dg in degs]
    open(os.path.join(mdir, "hzm_medal_lid_%s.skc" % an), "wb").write(X.build_skc(["root pos", "root rot"], fr, 0.05, lo, hi, rad))
open(os.path.join(mdir, "hzm_medal_lid.tik"), "w", newline="\n").write(
    "TIKI\nsetup\n{\n\tscale 1.0\n\tpath models/menu\n\tskelmodel hzm_medal_lid.skd\n" +
    "".join("\tsurface %s shader hzm_medal_lid\n" % s[0] for s in outer) + "\tsurface inside shader hzm_medal_inside\n}\n\n"
    "init\n{\n\tserver\n\t{\n\t\tclassname effectentity\n\t\tnotsolid\n\t}\n}\n\nanimations\n{\n" +
    "".join("\t%s hzm_medal_lid_%s.skc\n" % (a, a) for a in ("closed", "open", "opened", "close")) + "\tidle hzm_medal_lid_closed.skc\n}\n")
open(os.path.join(sdir, "hzm_records3d.shader"), "w", newline="\n").write(
    "// v1.10.63 the RECORDS medal box (gen_records3d.py)\n"
    "hzm_medal_lid\n{\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_medal_lid.jpg\n\t\trgbGen identity\n\t}\n}\n\n"
    "hzm_medal_inside\n{\n\tcull none\n\t{\n\t\tmap textures/menu/hzm_medal_inside.jpg\n\t\trgbGen identity\n\t}\n}\n")
LID_LINE = 'scenemodel "models/menu/hzm_medal_lid.tik" %.2f %.2f %.2f 0.0 "%s"'


def pose(org_bu, pitch, fov):
    o = conv(np.array(org_bu))
    return "%.1f %.1f %.1f %.2f 0.00 0.00 %.2f" % (o[0], o[1], o[2], pitch, fov)       # yaw 0 = looking +Y (BU): square on to the box


# the desk view: from the front of the long desk, a little above, the box and both trays in frame (vanilla's war_records framing)
DESK_POSE = pose((0.06, 2.08, 1.33), 24.0, 50.0)   # between the box (x -0.13) and the trays (0.26): both in a 4:3 frame
# the medals: square on to the upright lid, the case filling ~80 % of the height
LID_C = np.array([(X0 + X1) / 2, Y1, ZL + DEPTH / 2])
DIST = DEPTH / 0.80 / 2 / math.tan(math.radians(20.0))
MEDAL_POSE = pose((LID_C[0], Y1 - DIST, LID_C[2]), 0.0, 40.0)

# ---- the attic's own model list (no actors), shared by both menus
main = open(os.path.join(ui, "main.urc"), encoding="latin-1").read().replace("\r\n", "\n")
blk = main[main.index('name "atticscene"'):]
blk = blk[:blk.index("\n}\n")]
models = [l for l in blk.split("\n") if l.startswith("scenemodel ") and "models/human" not in l and "hzm_medal_lid" not in l]
models += [l for l in blk.split("\n") if l.startswith("scenemodelcvar ")]     # v1.10.66: the gramophone's per-record 3D pieces stay gated


def board(rect):
    """vanilla case rect (0..1 of the art: x, y-from-top, w, h) -> a scenelabel board on the upright lid's inside face"""
    u, v, w, h = rect
    xb = X0 + (u + w / 2) * (X1 - X0)
    zb = ZL + DEPTH - (v + h / 2) * DEPTH
    c = conv(np.array([xb, Y1 - 0.004, zb]))
    return "%.2f %.2f %.2f %.2f %.2f" % (c[0], c[1], c[2], w * (X1 - X0) / 2 * S, h * DEPTH / 2 * S)


NL = "\r\n"


def menu_head(name, esc, comment):
    return ["// generated by docs/proposals/attic_polish_2026-11-02/tools/gen_records3d.py - do not hand-edit.  " + comment,
            'menu "%s" 640 480 NONE 0' % name, "bgcolor 0 0 0 1", "borderstyle NONE", "bgfill 0 0 0 1", "fullscreen 1", "virtualres 1",
            'escapecommand "%s"' % esc, ""]


def back_button(cmd):
    return ["resource", "Button", "{", 'name "back"', "rect 8 448 96 24", "fgcolor 1.00 1.00 1.00 1.00", "bgcolor 0.00 0.00 0.00 0.00",
            'borderstyle "NONE"', 'shader "textures/mohmenu/back"', 'hovershader "textures/mohmenu/back_h"', 'clicksound "sound/menu/back.wav"',
            'stuffcommand "%s"' % cmd, "}", ""]


# ---- hzm_records3d: the desk
BOX_C = conv(np.array([(X0 + X1) / 2, (Y0 + Y1) / 2, (MB["z0"] + Z1) / 2]))
TRAY_C = conv(np.array([0.26, 3.32, 0.86]))
OPEN_CMD = ("set ui_scene_hot 0; set ui_recordsign 0; globalwidgetcommand records3dscene scenemodelanim hzm_medal_lid open,opened; "
            "globalwidgetcommand records3dscene sceneleave; globalwidgetcommand records3dscene scenefly 0.8 %s; "
            "uiafter 0.65 uiveil 1 0.15; uiafter 0.8 pushmenu hzm_medals3d; uiafter 0.82 uiveil 0 0.2" % MEDAL_POSE)
LS_CMD = "set ui_scene_hot 0; set ui_recordsign 0; pushmenu_sp loadsave; pushmenu_dm loadsave_mp"
R = menu_head("hzm_records3d", "set ui_scene_hot 0; set ui_recordsign 0; popmenu 1",
              "The attic's RECORDS desk (ui_atticMain 1): the medal box -> hzm_medals3d, the LOAD / SAVE trays -> loadsave.")
R += ["resource", "Scene3D", "{", 'name "records3dscene"', "rect 0 0 640 480"] + models + [LID_LINE % (tuple(HINGE) + ("closed",)),
      "scenecam " + DESK_POSE,
      'scenehot "medals" %.1f %.1f %.1f %.1f "%s" "PERSONAL RECORDS" "rec_h1"' % (tuple(BOX_C) + (13.0, OPEN_CMD)),
      'scenehot "loadsave" %.1f %.1f %.1f %.1f "%s" "LOAD / SAVE" "rec_h2"' % (tuple(TRAY_C) + (11.0, LS_CMD)), "}", ""]
# the vanilla desk sign (war_records.urc: rect 394 55 157 41, linkcvar ui_recordsign)
R += ["resource", "Label", "{", 'name "recsign"', "rect 394 55 157 41", "fgcolor 1.00 1.00 1.00 1.00", "bgcolor 0.50 0.50 0.50 0.00",
      'borderstyle "NONE"', "tileshader 0", 'linkcvar "ui_recordsign"', "linkcvartoshader", "}", ""]
for nm, idx, cmd, sign in (("rec_h1", 1, OPEN_CMD, "textures/mohmenu/desk_personalrecords"), ("rec_h2", 2, LS_CMD, "textures/mohmenu/desk_loadsave")):
    R += ["resource", "Button", "{", 'name "%s"' % nm, "rect 0 0 8 8", "fgcolor 0 0 0 0", "bgcolor 0 0 0 0", 'borderstyle "NONE"',
          'clicksound "sound/menu/apply.wav"', 'stuffcommand "%s"' % cmd, 'hovercommand "set ui_scene_hot %d; set ui_recordsign %s"' % (idx, sign),
          'mouseawaycommand "set ui_scene_hot 0; set ui_recordsign 0"', "}", ""]
R += back_button("set ui_scene_hot 0; set ui_recordsign 0; popmenu 1") + ["end."]
open(os.path.join(ui, "hzm_records3d.urc"), "wb").write((NL.join(R) + NL).encode("latin-1"))

# ---- hzm_medals3d: the open case
CLOSE = "set ui_medalsign 0; set ui_medaldesc 0; popmenu 1; globalwidgetcommand records3dscene scenemodelanim hzm_medal_lid close,closed"
M = menu_head("hzm_medals3d", CLOSE, "PERSONAL RECORDS: the open medal box on the attic desk - vanilla ui/medals.urc in the scene.")
M += ["resource", "Scene3D", "{", 'name "medals3dscene"', "rect 0 0 640 480"] + models + [LID_LINE % (tuple(HINGE) + ("opened",)),
      "scenecam " + MEDAL_POSE]
for k, m in enumerate(LAY["medals"]):
    M.append('scenelabel "medal%d" %s' % (k, board(m["rect"])))
M += ['scenelabel "medaldesc" %s' % board(LAY["desc"]), 'scenelabel "medalsign" %s' % board(LAY["sign"]), "}", ""]
for k, m in enumerate(LAY["medals"]):
    n = m["name"]
    M += ["resource", "Button", "{", 'name "medal%d"' % k, "rect 0 0 8 8", "fgcolor 1.00 1.00 1.00 1.00", "bgcolor 0.50 0.50 0.50 0.00",
          'borderstyle "NONE"', 'shader "%s_med"' % n, 'enabledcvar "%s"' % m["cvar"],
          'hovercommand "set ui_medalsign %s_sign; set ui_medaldesc %s_desc"' % (n, n), 'mouseawaycommand "set ui_medalsign 0; set ui_medaldesc 0"', "}", ""]
for nm, cv in (("medaldesc", "ui_medaldesc"), ("medalsign", "ui_medalsign")):
    M += ["resource", "Label", "{", 'name "%s"' % nm, "rect 0 0 8 8", "fgcolor 1.00 1.00 1.00 1.00", "bgcolor 0.50 0.50 0.50 0.00",
          'borderstyle "NONE"', 'linkcvar "%s"' % cv, "linkcvartoshader", "}", ""]
M += back_button(CLOSE) + ["end."]
open(os.path.join(ui, "hzm_medals3d.urc"), "wb").write((NL.join(M) + NL).encode("latin-1"))
json.dump({"desk_pose": DESK_POSE, "medal_pose": MEDAL_POSE, "hinge": HINGE.tolist(), "box_hot": BOX_C.tolist(), "tray_hot": TRAY_C.tolist()},
          open(os.path.join(out, "records3d.json"), "w"), indent=1)
print("records3d: desk pose", DESK_POSE, "| medal pose", MEDAL_POSE, "| lid hinge", np.round(HINGE, 2))
