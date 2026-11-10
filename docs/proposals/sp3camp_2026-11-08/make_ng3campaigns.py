"""make_ng3campaigns.py - single-player NEW GAME: ONE wall map with all twelve missions of Allied Assault, Spearhead and Breakthrough,
a VANILLA | CHRONOLOGICAL order toggle at the top, and real unlock progress (user 2026-11-08: "a map that just lets you pick all
locations, and at the top an option between chronological or vanilla and respective areas on map unlock accordingly"; "I think it
needs to still have lock progress tho for single player").  Run AFTER newgame/make_newgame3d.py (it rewrites that script's
ui/hzm_newgame3d.urc and replaces its hzm_ng3d_mission<N>difficulty.urc) and after warmap.py:

    python -P -E warmap.py all <Natural Earth 10m folder> H:/hzm_work/warmap
    python make_ng3campaigns.py --mod <mod checkout> [--sheet H:/hzm_work/warmap]

Writes into the mod tree (loose; build.ps1 packs them - the .jpg/.tga are gitignored, so re-run this in the checkout you build from):
  ui/hzm_newgame3d.urc            the attic wall map (the shared war map, baked into atc_wallmap1 from warmap.py wallmap_ne.png), the
                                  leaders + legend overlay, one paper tag per mission (campaign colour), the order toggle
                                  (seta ui_ngMode: unset/1 chronological = the default, 2 vanilla)
  ui/hzm_ng3d_<key>diff.urc       the stock difficulty screen over the same view, per mission (key aa1-aa6, sh1-sh3, bt1-bt3)
  ui/hzm_ngflat.urc + hzm_ngflat_<key>diff.urc   the flat menu (ui_atticMain 0): the vanilla order, same locks
  textures/menu/hzm_ng3c_*  + scripts/hzm_ng3campaigns.shader
  ui/main.urc                     the flat NEW GAME / BRIEFING buttons push hzm_ngflat (idempotent)

Unlocks (bug-10616).  The menu cannot run script, so it reads archived cvars written by coop_mod/spcampaign.scr when a
mission's last level ends in single player: coop_spdoneV_<key> (vanilla) / coop_spdoneC_<key> (chronological) - progress is per mode.
  VANILLA: each game's first mission open; mission N opens when N-1 of the same game is done.
  CHRONOLOGICAL: only the next mission in time (coop_mod/chrono.scr::nextMission, ORDER.md) opens.
  coop_dev 1: everything open (testing).  The stock g_m*/g_t* flags are not used (SH and BT share g_t2l1/g_t3l1; coop uses g_m2l1).
enabledcvar ANDs its terms and has no OR, so an "open" tag is drawn by one widget per reason (its mode's progress, or coop_dev);
when two apply they draw the same texture in the same place.  A tag click seta's coop_spChrono to the mode it was started in."""
import json, math, os, re, sys, zipfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def opt(n, d):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


MOD = opt("--mod", r"C:\mohaa-coop-dev\hzm-mod-spfix2")
SHEETD = opt("--sheet", r"H:\hzm_work\warmap")          # warmap.py all <ne> <dir>
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
FONTS = r"C:\Windows\Fonts"
UI = os.path.join(MOD, "ui")
TEX = os.path.join(MOD, "textures", "menu")
SCR = os.path.join(MOD, "scripts")
NL = "\r\n"
SCALE = 52.5
WM_LO, WM_HI = np.array([-2.8721, 6.745, 0.0707]), np.array([0.2762, 6.745, 2.7760])   # make_newgame3d.py: the attic wallmap plane
DIST = 6.745 - 3.0
FPX = 540.0 / math.tan(math.radians(46.0) / 2)
MJ = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "missions.json")))      # THE mission table
ROW = {m["key"]: m for m in MJ["missions"]}
CAMPS = [c["key"] for c in MJ["campaigns"]]
CAMPNAME = {c["key"]: c["name"] for c in MJ["campaigns"]}
CHRONO = [m["key"] for m in sorted(MJ["missions"], key=lambda m: m["chrono"])]      # = coop_mod/chrono.scr::nextMission
for d in (TEX, SCR):
    os.makedirs(d, exist_ok=True)
JS = json.load(open(os.path.join(SHEETD, "allmap_markers.json")))
TAG_W, TAG_H = JS["tag_m"]
MIS = JS["missions"]
BYKEY = {m["key"]: m for m in MIS}
assert sorted(BYKEY) == sorted(CHRONO)


def conv(p):
    p = np.asarray(p, float)
    return np.array([p[1], -p[0], p[2]]) * SCALE


def map_bu(uv, dy=0.006):
    return np.array([WM_LO[0] + uv[0] * (WM_HI[0] - WM_LO[0]), WM_LO[1] - dy, WM_LO[2] + uv[1] * (WM_HI[2] - WM_LO[2])])


def prev_v(k):
    m = BYKEY[k]
    prev = [x["key"] for x in MJ["missions"] if x["camp"] == m["camp"] and x["n"] == m["n"] - 1]
    return prev[0] if prev else None


def prev_c(k):
    i = CHRONO.index(k)
    return None if i == 0 else CHRONO[i - 1]


def opt_gate(k):
    """' <cvar>==1' when the mission is optional (only when present), '' otherwise"""
    cv = ROW[k].get("optional_cvar")
    return (" %s==1" % cv) if cv else ""


def unlock_gates(k, md, mg):
    """every enabledcvar string that OPENS mission k in mode md (mg = the mode's own gate).  An optional predecessor that is
    absent is skipped: the mission then unlocks from the one before it (one level of skipping per absent mission)."""
    prev = prev_v(k) if md == "V" else prev_c(k)
    base = mg + opt_gate(k)
    if not prev:
        return [base], []
    gates = [base + " coop_spdone%s_%s==1" % (md, prev), base + " coop_dev==1"]
    locks = [base + " coop_spdone%s_%s!=1 coop_dev!=1" % (md, prev)]
    pcv = ROW[prev].get("optional_cvar")
    if pcv:                                       # the predecessor may be absent: then the one before it decides
        locks = [base + " %s==1 coop_spdone%s_%s!=1 coop_dev!=1" % (pcv, md, prev)]
        pp = prev_v(prev) if md == "V" else prev_c(prev)
        if pp:
            gates.append(base + " %s!=1 coop_spdone%s_%s==1" % (pcv, md, pp))
            locks.append(base + " %s!=1 coop_spdone%s_%s!=1 coop_dev!=1" % (pcv, md, pp))
        else:
            gates.append(base + " %s!=1" % pcv)
    return gates, locks


# ---- the scene the menus share: make_newgame3d.py's models and full-map pose, read back from its output
cur = open(os.path.join(UI, "hzm_newgame3d.urc"), encoding="latin-1").read()
blk = cur[cur.index('Scene3D'):]
blk = blk[:blk.index("\n}")]
# [byo69, bug-10711 family] EVERY scenemodel of the source scene, not only the atc_* bakes: the attic window (hzm_wx_*, v1.10.67)
# and any later prop must survive a regeneration (the atc_-only filter dropped 120 lines from each of 13 menus)
MODELS = [l.rstrip("\r") for l in blk.split("\n") if l.split(" ", 1)[0] in ("scenemodel", "scenewx", "scenemodelcvar")]
POSE = re.search(r"(?m)^scenecam ([-\d. ]+)$", blk).group(1).strip()
assert any("atc_wallmap1" in m for m in MODELS) and POSE.startswith("157.5 68.1 74.7"), (MODELS, POSE)

# ---- textures
F_ST = os.path.join(FONTS, "STENCIL.TTF")
F_CB = os.path.join(FONTS, "courbd.ttf")


def fit(d, text, path, px, maxw, minpx=30):
    while px > minpx and d.textlength(text, font=ImageFont.truetype(path, px)) > maxw:
        px -= 2
    return ImageFont.truetype(path, px), px


def padlock(d, x, y, s, col):
    d.rounded_rectangle((x, y + s * 0.42, x + s, y + s), radius=int(s * 0.1), fill=col)
    d.arc((x + s * 0.18, y, x + s * 0.82, y + s * 0.84), 180, 360, fill=col, width=max(4, int(s * 0.13)))
    d.ellipse((x + s * 0.42, y + s * 0.6, x + s * 0.58, y + s * 0.76), fill=(40, 34, 28, 255))


def tag(name, sub, colour, locked):
    # drawn at 4x the 1080p size and mip-mapped; aspect = TAG_W / TAG_H
    h = 300
    w = int(round(h * TAG_W / TAG_H))
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((26, 30, w - 10, h - 6), fill=(0, 0, 0, 110))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(im)
    paper = tuple(int(c * 0.62 + 40) for c in colour) if locked else tuple(colour)
    ink = (84, 80, 74) if locked else (36, 28, 20)
    d.rectangle((12, 12, w - 24, h - 20), fill=paper + (255,), outline=(90, 74, 50, 255), width=6)
    right = w - 24 - (110 if locked else 30)
    f1, px = fit(d, name, F_ST, 120, right - 50)
    tw = d.textlength(name, font=f1)
    d.text((24 + (right - 24 - tw) / 2, 30 + (120 - px) * 0.5), name, font=f1, fill=ink + (255,))
    f2 = ImageFont.truetype(F_CB, 92)          # the mission line must stay readable at 1080p (~11 px)
    tw = d.textlength(sub, font=f2)
    d.text((24 + (right - 24 - tw) / 2, 162), sub, font=f2, fill=ink + (255,))
    if locked:
        padlock(d, w - 124, 70, 86, (70, 62, 52, 255))
    return im


def tick():
    s = 160
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((6, 6, s - 6, s - 6), fill=(176, 28, 24, 235), outline=(90, 14, 10, 255), width=8)
    d.line([(44, 84), (70, 112), (118, 50)], fill=(250, 238, 214, 255), width=18, joint="curve")
    return im


def toggle_tab(text, w_m, on):
    h = 140
    w = int(round(h * w_m / TOG_H))
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    paper = (236, 218, 156) if on else (150, 140, 116)
    ink = (36, 28, 20) if on else (70, 64, 56)
    d.rectangle((6, 6, w - 7, h - 7), fill=paper + (255,), outline=(70, 56, 36, 255), width=6)
    f, px = fit(d, text, F_ST, 84, w - 60)
    tw = d.textlength(text, font=f)
    d.text(((w - tw) / 2, (h - px) / 2 - 10), text, font=f, fill=ink + (255,))
    if on:
        d.rectangle(((w - tw) / 2, h - 30, (w + tw) / 2, h - 20), fill=(170, 30, 24, 255))
    return im


shader = ["// [ng3campaigns] generated by docs/proposals/sp3camp_2026-11-08/make_ng3campaigns.py - do not hand-edit"]


def add_shader(nm, blend, ext, mips=True, pulse=False):
    # pulse [Live Operations]: the grease-pencil contract loops breathe (alphaGen wave)
    shader.append("textures/menu/%s\n{\n\tnopicmip\n%s\tcull none\n\t{\n\t\tclampmap textures/menu/%s.%s\n%s\t\trgbGen identity\n%s\t}\n}"
                  % (nm, "" if mips else "\tnomipmaps\n", nm, ext, "\t\tblendFunc blend\n" if blend else "",
                     "\t\talphaGen wave sin 0.78 0.22 0 0.3\n" if pulse else ""))


def save_jpg(img, path):
    img.convert("RGB").save(path, quality=97, subsampling=0)      # 4:4:4: the red pins and the lettering do not bleed


for fn in os.listdir(TEX):                          # this script's earlier outputs (the three-sheet version included)
    if fn.startswith("hzm_ng3c_"):
        os.remove(os.path.join(TEX, fn))
Image.open(os.path.join(SHEETD, "ng_overlay.png")).save(os.path.join(TEX, "hzm_ng3c_overlay.tga"))     # leaders + legend (RGBA)
add_shader("hzm_ng3c_overlay", True, "tga")
save_jpg(Image.open(os.path.join(SHEETD, "flat_room.png")), os.path.join(TEX, "hzm_ng3c_flatroom.jpg"))   # the flat briefing-room map
add_shader("hzm_ng3c_flatroom", False, "jpg", mips=False)
for m in MIS:
    for lk in (False, True):
        nm = "hzm_ng3c_tag_%s%s" % (m["key"], "_lk" if lk else "")
        tag(m["name"], "MISSION %d" % m["n"], m["colour"], lk).save(os.path.join(TEX, nm + ".tga"))
        add_shader(nm, True, "tga")
tick().save(os.path.join(TEX, "hzm_ng3c_done.tga"))
# [byo69] an optional mission's pin is a scene label (warmap.py never bakes it): the same red pin as the baked ones
_pin = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
ImageDraw.Draw(_pin).ellipse((6, 6, 57, 57), fill=(176, 28, 24, 250), outline=(70, 14, 10, 255), width=5)
_pin.save(os.path.join(TEX, "hzm_ng3c_pin.tga"))
add_shader("hzm_ng3c_pin", True, "tga")
# [attic70] an optional mission's dashed leader pin -> tag (warmap.py lead_<key>.png, its wall uv box in the markers json): a scene
# label gated like its pin, so it is there exactly when the mission is
for m in MIS:
    if m.get("lead_uv"):
        Image.open(os.path.join(SHEETD, "lead_%s.png" % m["key"])).save(os.path.join(TEX, "hzm_ng3c_lead_%s.tga" % m["key"]))
        add_shader("hzm_ng3c_lead_%s" % m["key"], True, "tga")
add_shader("hzm_ng3c_done", True, "tga")
TOG = JS["toggle"]
TOG_H = TOG["h"]
TOG_PARTS = [("van", "VANILLA", 0.22, 2), ("chr", "CHRONOLOGICAL", TOG["w"] - 0.22, 1)]   # the seta ui_ngMode value
for k, text, wm, _v in TOG_PARTS:
    for on in (True, False):
        nm = "hzm_ng3c_tog_%s_%s" % (k, "on" if on else "off")
        toggle_tab(text, wm, on).save(os.path.join(TEX, nm + ".tga"))
        add_shader(nm, True, "tga")
# [Live Operations, v1.10.71] the contract layer's textures (docs/proposals/livemap_2026-11-09/gen_ops.py): grease loops, timer
# rings, TDM / OBJ stamps, the hover slip and the dispatch card. gen_ops also owns the layout pass over the same markers json.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "livemap_2026-11-09"))
import gen_ops  # noqa: E402
gen_ops.build_textures(TEX, add_shader)
# every texture power-of-two: the renderer resamples a non-power-of-two image to the next power of two at load, in temp hunk
# memory (a 4096x3072 test texture made every queued screenshot of the session silently fail).  The labels stretch the picture
# onto their own rect, so the stored aspect does not matter; each side goes UP to the next power of two (no detail is lost).
def _pot(n):
    return 1 << (int(n) - 1).bit_length()


for fn in sorted(os.listdir(TEX)):
    if not fn.startswith("hzm_ng3c_"):
        continue
    fp = os.path.join(TEX, fn)
    im_ = Image.open(fp)
    w_, h_ = im_.size
    if (w_, h_) != (_pot(w_), _pot(h_)):
        im_ = im_.resize((_pot(w_), _pot(h_)), Image.LANCZOS)
        if fn.endswith(".jpg"):
            save_jpg(im_, fp)
        else:
            im_.save(fp)
open(os.path.join(SCR, "hzm_ng3campaigns.shader"), "w", newline="\n").write("\n".join(shader) + "\n")

# ---- the 3D new game menu
MC = (WM_LO + WM_HI) / 2
SHEET_C = conv(np.array([MC[0], WM_LO[1] - 0.003, MC[2]]))
SHEET_HW, SHEET_HH = (WM_HI[0] - WM_LO[0]) / 2 * SCALE, (WM_HI[2] - WM_LO[2]) / 2 * SCALE
HW, HH = TAG_W / 2 / DIST * FPX, TAG_H / 2 / DIST * FPX
MODES = [("V", "ui_ngMode==2", 0), ("C", "ui_ngMode!=2", 1)]      # user 2026-11-08: chronological is the default (unset/0/1)


def label(name, sh, gate):
    return ["resource", "Label", "{", 'name "%s"' % name, "rect 0 0 8 8", "fgcolor 1 1 1 1", "bgcolor 0 0 0 0", 'borderstyle "NONE"',
            'shader "textures/menu/%s"' % sh] + (['enabledcvar "%s"' % gate] if gate else []) + ["}"]


def sheet_scene(name, extra=(), overlay=False):
    b = ["resource", "Scene3D", "{", 'name "%s"' % name, "rect 0 0 640 480"] + MODELS + ["scenecam " + POSE]
    if overlay:      # NEW GAME: the leaders and the legend over the baked wall map (warmap.py ng_overlay.png)
        b.append('scenelabel "%s_overlay" %.1f %.1f %.1f %.2f %.2f' % (name, SHEET_C[0], SHEET_C[1], SHEET_C[2], SHEET_HW, SHEET_HH))
    return b + list(extra)


scn_extra, wid, hots, boxes, caps, btns = [], [], [], [], {}, []
idx = [0]


def hot(hn, ce, half_w, hw, hh, cmd, cap, gate, back=False):
    idx[0] += 1
    i = idx[0]
    hots.append('scenehot "%s" %.1f %.1f %.1f %.1f "%s" "%s" "ng_h%d"' % (hn, ce[0], ce[1], ce[2], half_w, cmd, cap, i))
    boxes.append('scenehotbox "%s" 0.0 0.0 %.1f %.1f' % (hn, hw, hh))
    caps[i] = (cap, ce)
    btns.append((i, cmd, gate, back))
    return i


for m in MIS:
    k = m["key"]
    if ROW[k].get("optional_cvar"):
        if m.get("lead_uv"):
            u0, v0, u1, v1 = m["lead_uv"]
            lc = conv(map_bu(((u0 + u1) / 2, (v0 + v1) / 2), dy=0.0045))
            scn_extra.append('scenelabel "ng3c_lead_%s" %.1f %.1f %.1f %.2f %.2f' % (k, lc[0], lc[1], lc[2], (u1 - u0) * (WM_HI[0] - WM_LO[0]) / 2 * SCALE,
                                                                                  (v1 - v0) * (WM_HI[2] - WM_LO[2]) / 2 * SCALE))
            wid += label("ng3c_lead_%s" % k, "hzm_ng3c_lead_%s" % k, opt_gate(k).strip())
        pc = conv(map_bu(m["pin_uv"], dy=0.004))
        scn_extra.append('scenelabel "ng3c_pin_%s" %.1f %.1f %.1f %.2f %.2f' % (k, pc[0], pc[1], pc[2], 0.018 * SCALE, 0.018 * SCALE))
        wid += label("ng3c_pin_%s" % k, "hzm_ng3c_pin", opt_gate(k).strip())
    c = map_bu(m["tag_uv"])
    ce = conv(c)
    open_gates, lock_gates = [], []
    for md, mg, chrono in MODES:
        gs, ls = unlock_gates(k, md, mg)
        open_gates += [(md, chrono, g) for g in gs]
        prev = prev_v(k) if md == "V" else prev_c(k)
        lock_gates += [(md, g, prev) for g in ls]
    # the tag: one open widget per reason, one locked widget per lock reason, a done tick per mode
    for j, (md, chrono, g) in enumerate(open_gates):
        nm = "ng3c_t_%s_%d" % (k, j)
        scn_extra.append('scenelabel "%s" %.1f %.1f %.1f %.2f %.2f' % (nm, ce[0], ce[1], ce[2], TAG_W / 2 * SCALE, TAG_H / 2 * SCALE))
        wid += label(nm, "hzm_ng3c_tag_%s" % k, g)
        hot("%s_o%d" % (k, j), ce, TAG_W / 2 * SCALE, HW * 1.04, HH * 1.10,
            "set ui_scene_hot 0; seta coop_spChrono %d; pushmenu hzm_ng3d_%sdiff" % (chrono, k), "CHOOSE DIFFICULTY", g)
    for j, (md, g, prev) in enumerate(lock_gates):
        nm = "ng3c_l_%s_%d" % (k, j)
        scn_extra.append('scenelabel "%s" %.1f %.1f %.1f %.2f %.2f' % (nm, ce[0], ce[1], ce[2], TAG_W / 2 * SCALE, TAG_H / 2 * SCALE))
        wid += label(nm, "hzm_ng3c_tag_%s_lk" % k, g)
        pm = BYKEY[prev]
        cap = "LOCKED - FINISH %s %d FIRST" % (CAMPNAME[pm["camp"]], pm["n"])
        hot("%s_l%d" % (k, j), ce, TAG_W / 2 * SCALE, HW * 1.04, HH * 1.10, "set ui_scene_hot 0", cap, g, back=True)
    tk = conv(c + np.array([TAG_W / 2 - 0.012, -0.002, TAG_H / 2 - 0.006]))
    for md, mg, _ch in MODES:
        nm = "ng3c_d_%s_%s" % (k, md)
        scn_extra.append('scenelabel "%s" %.1f %.1f %.1f %.2f %.2f' % (nm, tk[0], tk[1], tk[2], 0.026 * SCALE, 0.026 * SCALE))
        wid += label(nm, "hzm_ng3c_done", "%s coop_spdone%s_%s==1%s" % (mg, md, k, opt_gate(k)))
# the order toggle (top left of the sheet): two tabs, the picked one lit
tc = map_bu(TOG["uv"])
x0 = tc[0] - TOG["w"] / 2
for k, text, wm, v in TOG_PARTS:
    cx = x0 + wm / 2
    x0 += wm
    p = np.array([cx, tc[1], tc[2]])
    ce = conv(p)
    for on in (True, False):
        nm = "ng3c_tog_%s_%s" % (k, "on" if on else "off")
        g = ("ui_ngMode==2" if v == 2 else "ui_ngMode!=2") if on else ("ui_ngMode!=2" if v == 2 else "ui_ngMode==2")
        scn_extra.append('scenelabel "%s" %.1f %.1f %.1f %.2f %.2f' % (nm, ce[0], ce[1], ce[2], wm / 2 * SCALE, TOG_H / 2 * SCALE))
        wid += label(nm, "hzm_ng3c_tog_%s_%s" % (k, "on" if on else "off"), g)
    hot("tog_%s" % k, ce, wm / 2 * SCALE, wm / 2 / DIST * FPX, TOG_H / 2 / DIST * FPX, "set ui_scene_hot 0; seta ui_ngMode %d" % v,
        "VANILLA: EACH GAME IN ITS OWN ORDER" if v == 2 else "CHRONOLOGICAL: ALL THREE GAMES IN THE ORDER OF EVENTS", "")
# [Live Operations] the contract widgets; their hotspots come AFTER every campaign one (ui_scene_hot is the list position) and
# carry no chalk caption (the hover slip is theirs)
_opshots = []


def _ops_hot(*a, **k):
    i = hot(*a, **k)
    _opshots.append(i)
    return i


# [opsfix, v1.10.72] the dispatch card's DEPLOY / FILE AWAY proxy buttons go AFTER the card's labels (see gen_ops: the hit-test
# picks the last widget under the cursor, and a Label counts), so they are kept out of the main button run
_tophots = []


def _ops_hot_top(*a, **k):
    i = _ops_hot(*a, **k)
    _tophots.append(i)
    return i


OPS_SCN, OPS_UNDER, OPS_OVER, OPS_CARD = gen_ops.ng3d({"conv": conv, "map_bu": map_bu, "SCALE": SCALE, "WM": (WM_LO, WM_HI), "hot": _ops_hot,
                                                       "hot_top": _ops_hot_top, "DIST": DIST, "FPX": FPX}, JS)
scn_extra += OPS_SCN
for _i in _opshots:
    del caps[_i]
for i, (cap, ce) in caps.items():
    cc = conv(np.array([0, 0, 0])) if False else None
    p = np.array([-ce[1] / SCALE, ce[0] / SCALE, ce[2] / SCALE])         # back to BU
    p[2] -= TAG_H / 2 + 0.05
    q = conv(p)
    scn_extra.append('scenelabel "ngcap%d" %.1f %.1f %.1f %.2f %.2f' % (i, q[0], q[1], q[2], 0.40 * SCALE, 0.035 * SCALE))

U = ["// generated by docs/proposals/sp3camp_2026-11-08/make_ng3campaigns.py (after make_newgame3d.py) - do not hand-edit.",
     "// Single-player new game: all twelve missions on one wall map, VANILLA | CHRONOLOGICAL (ui_ngMode), unlocks from coop_spdone* (coop_mod/spcampaign.scr).",
     'menu "hzm_newgame3d" 640 480 NONE 0', "bgcolor 0 0 0 1", "borderstyle NONE", "bgfill 0 0 0 1", "fullscreen 1", "virtualres 1",
     'escapecommand "set ui_scene_hot 0; hzm_ops escape"', ""]
U += sheet_scene("ngscene", scn_extra + hots + boxes, overlay=True) + ["}"]
U += label("ngscene_overlay", "hzm_ng3c_overlay", "") + OPS_UNDER + wid
for i, (cap, _ce) in caps.items():
    U += ["resource", "Label", "{", 'name "ngcap%d"' % i, "rect 0 0 8 8", 'title "%s"' % cap, "fgcolor 0.93 0.88 0.72 1.00",
          "bgcolor 0.10 0.08 0.06 0.82", 'borderstyle "NONE"', 'font "facfont-20"', "textalign center", 'enabledcvar "ui_scene_hot==%d"' % i, "}"]
U += OPS_OVER                     # contract stamps and hover slips: over the campaign tags


def _button(i, cmd, gate, back):
    return ["resource", "Button", "{", 'name "ng_h%d"' % i, "rect 0 0 8 8", "fgcolor 0 0 0 0", "bgcolor 0 0 0 0", 'borderstyle "NONE"',
            'clicksound "sound/menu/%s.wav"' % ("back" if back else "apply"), 'stuffcommand "%s"' % cmd, 'hovercommand "set ui_scene_hot %d"' % i,
            'mouseawaycommand "set ui_scene_hot 0"'] + (['enabledcvar "%s"' % gate] if gate else []) + ["}"]


for i, cmd, gate, back in btns:
    if i not in _tophots:
        U += _button(i, cmd, gate, back)
U += OPS_CARD                     # the dispatch card: on top of everything
for i, cmd, gate, back in btns:   # ... and its own buttons on top of the card (the hit-test takes the last widget)
    if i in _tophots:
        U += _button(i, cmd, gate, back)
# the click contract, asserted: every card button comes after every card label (a label after it would eat the click)
_names = [U[k + 3] for k in range(len(U) - 3) if U[k] == "resource" and U[k + 2] == "{"]
_card = {OPS_CARD[k + 3] for k in range(len(OPS_CARD) - 3) if OPS_CARD[k] == "resource"}
_last_card = max(k for k, n in enumerate(_names) if n in _card)
_first_top = min(k for k, n in enumerate(_names) if n in ['name "ng_h%d"' % i for i in _tophots])
assert _tophots and _first_top > _last_card, ("card buttons under the card's labels", _first_top, _last_card)
U += ["resource", "Button", "{", 'name "back"', "rect 8 448 96 24", "fgcolor 1.00 1.00 1.00 1.00", "bgcolor 0.50 0.50 0.50 0.00", 'borderstyle "3D_BORDER"',
      'shader "textures/mohmenu/back"', 'hovershader "textures/mohmenu/back_h"', 'clicksound "sound/menu/back.wav"', 'stuffcommand "set ui_scene_hot 0; hzm_ops close; popmenu 1"', "}", "end."]
open(os.path.join(UI, "hzm_newgame3d.urc"), "wb").write((NL.join(U) + NL).encode("latin-1"))

# ---- the stock difficulty screen, per mission: 3D (over the sheet) and flat (stock backdrop)
TPL = zipfile.ZipFile(os.path.join(GOG, "maintt", "pak1.pk3")).read("ui/mission1difficulty.urc").decode("latin-1").replace("\r\n", "\n")
assert TPL.count("spmap briefing/briefinge1") == 3
for fn in os.listdir(UI):                         # earlier outputs: make_newgame3d.py's BT set and this script's older names
    if re.match(r"hzm_(ng3d_mission\d|ng3d_[a-z]{2}\d|ngflat_[a-z]{2}\d)\w*\.urc$", fn):
        os.remove(os.path.join(UI, fn))
for m in MIS:
    k = m["key"]
    br = ROW[m["key"]]["brief"].split("/", 1)[1]
    s = TPL.replace("spmap briefing/briefinge1", "spmap briefing/" + br)
    s3, k1 = re.subn(r'menu "mission1difficulty" ', 'menu "hzm_ng3d_%sdiff" ' % k, s, count=1)
    s3, k2 = re.subn(r'(?m)^include "ui/briefing_room_nobuttons\.inc"\n', "", s3)
    s3 = re.sub(r'(?m)^//include "ui/common\.inc"\n', "", s3)
    assert k1 == 1 and k2 == 1
    i = s3.index("\nresource\n")
    sb = sheet_scene("ngd_" + k) + ["}"]
    s3 = ("// generated by make_ng3campaigns.py from the stock maintt ui/mission1difficulty.urc: %s mission %d -> spmap briefing/%s"
          " over the 3D wall map\n" % (CAMPNAME[m["camp"]], m["n"], br)) + s3[:i + 1] + "\n".join(sb) + "\n" + s3[i + 1:]
    open(os.path.join(UI, "hzm_ng3d_%sdiff.urc" % k), "wb").write(s3.replace("\n", NL).encode("latin-1"))
    sf, k1 = re.subn(r'menu "mission1difficulty" ', 'menu "hzm_ngflat_%sdiff" ' % k, s, count=1)
    assert k1 == 1
    sf = ("// generated by make_ng3campaigns.py from the stock maintt ui/mission1difficulty.urc: %s mission %d -> spmap briefing/%s"
          " (flat menu)\n" % (CAMPNAME[m["camp"]], m["n"], br)) + sf
    open(os.path.join(UI, "hzm_ngflat_%sdiff.urc" % k), "wb").write(sf.replace("\n", NL).encode("latin-1"))

# ---- the flat briefing room: the stock backdrop with the shared war map on its board (warmap.py flat_room.png)
ROOMRECT = "rect 93 99 464 304"          # the board's inner map area in the stock maintt briefing room (measured at 1280x720)
inc = zipfile.ZipFile(os.path.join(GOG, "maintt", "pak1.pk3")).read("ui/briefing_room_nobuttons.inc").decode("latin-1").replace("\r\n", "\n")
inc = ("// generated by make_ng3campaigns.py - the stock maintt ui/briefing_room_nobuttons.inc, then the shared war map on its board\n" + inc.rstrip()
       + "\n\nresource\nLabel\n{\nname \"ng3c_roommap\"\n" + ROOMRECT + "\nfgcolor 1 1 1 1\nbgcolor 0 0 0 0\nborderstyle \"NONE\"\n"
       "shader \"textures/menu/hzm_ng3c_flatroom\"\n}\n")
open(os.path.join(UI, "hzm_ngroom.inc"), "wb").write(inc.replace("\n", NL).encode("latin-1"))
for m in MIS:
    fp = os.path.join(UI, "hzm_ngflat_%sdiff.urc" % m["key"])
    t = open(fp, "rb").read().decode("latin-1")
    t, k_ = re.subn(r'(?m)^include "ui/briefing_room_nobuttons\.inc"', 'include "ui/hzm_ngroom.inc"', t)
    assert k_ == 1, fp
    open(fp, "wb").write(t.encode("latin-1"))

# ---- the flat chooser: the same order toggle and locks as the 3D map (chronological unless VANILLA was picked)
F = ["// generated by docs/proposals/sp3camp_2026-11-08/make_ng3campaigns.py - do not hand-edit.  Flat (ui_atticMain 0) single-player new game:",
     "// the twelve missions by game; the order (ui_ngMode: unset/1 chronological, 2 vanilla) and the locks are the 3D map's; coop_dev 1 opens all.",
     'menu "hzm_ngflat" 640 480 NONE 0', "bgcolor 1 1 1 1", "borderstyle NONE", "bgfill 0 0 0 1", "fullscreen 1", "virtualres 1",
     'include "ui/hzm_ngroom.inc"', "",
     "resource", "Label", "{", 'name "ngf_panel"', "rect 44 72 552 300", "fgcolor 0 0 0 0", "bgcolor 0.10 0.08 0.06 0.80", 'borderstyle "3D_BORDER"', "}",
     "resource", "Label", "{", 'name "ngf_title"', "rect 44 78 552 24", 'title "NEW GAME - CHOOSE A MISSION"', "fgcolor 0.93 0.88 0.72 1.00",
     "bgcolor 0 0 0 0", 'font "facfont-20"', "textalign center", "}"]
for mode, val, x0 in (("CHRONOLOGICAL", 1, 210), ("VANILLA", 2, 330)):
    on = "ui_ngMode==2" if val == 2 else "ui_ngMode!=2"
    off = "ui_ngMode!=2" if val == 2 else "ui_ngMode==2"
    for st, g in (("on", on), ("off", off)):
        F += ["resource", "Button", "{", 'name "ngf_mode_%s_%s"' % (mode.lower(), st), "rect %d 344 112 20" % x0, 'title "%s"' % mode,
              "fgcolor %s" % ("0.95 0.86 0.55 1.00" if st == "on" else "0.55 0.52 0.46 1.00"),
              "bgcolor %s" % ("0.30 0.10 0.06 0.95" if st == "on" else "0.14 0.11 0.08 0.90"), 'borderstyle "3D_BORDER"', 'font "verdana-12"',
              'clicksound "sound/menu/apply.wav"', 'stuffcommand "seta ui_ngMode %d"' % val, 'enabledcvar "%s"' % g, "}"]
BASECAMPS = [c for c in CAMPS if any(m["camp"] == c and not m.get("optional_cvar") for m in MJ["missions"])]
COLW = int(552 / max(3, len(BASECAMPS)))
for col, c in enumerate(BASECAMPS):
    x = 50 + col * COLW
    F += ["resource", "Label", "{", 'name "ngf_h_%s"' % c, "rect %d 112 %d 22" % (x, COLW - 12), 'title "%s"' % CAMPNAME[c], "fgcolor 0.86 0.74 0.46 1.00",
          "bgcolor 0 0 0 0", 'font "facfont-20"', "textalign center", "}"]
    for m in sorted([m for m in MIS if m["camp"] == c], key=lambda m: m["n"]):
        k, n = m["key"], m["n"]
        rect = "rect %d %d %d 24" % (x, 142 + 34 * (n - 1), COLW - 12)
        for md, mg, chrono in MODES:
            gs, ls = unlock_gates(k, md, mg)
            for j, g in enumerate(gs):
                F += ["resource", "Button", "{", 'name "ngf_%s_%s%d"' % (k, md, j), rect, 'title "%d  %s"' % (n, m["name"]),
                      "fgcolor 0.88 0.83 0.66 1.00", "bgcolor 0.16 0.12 0.08 0.92", 'borderstyle "3D_BORDER"', 'font "facfont-20"',
                      'clicksound "sound/menu/apply.wav"', 'stuffcommand "seta coop_spChrono %d; pushmenu hzm_ngflat_%sdiff"' % (chrono, k),
                      'enabledcvar "%s"' % g, "}"]
            for j, g in enumerate(ls):
                F += ["resource", "Label", "{", 'name "ngf_%s_%slk%d"' % (k, md, j), rect, 'title "%d  %s  (LOCKED)"' % (n, m["name"]),
                      "fgcolor 0.50 0.47 0.42 1.00", "bgcolor 0.12 0.10 0.08 0.80", 'borderstyle "3D_BORDER"', 'font "facfont-20"',
                      'enabledcvar "%s"' % g, "}"]
# [byo69] own-disc missions (optional_cvar): one button each on a strip under the panel, same locks, absent = nothing drawn
OPTM = [m for m in sorted(MIS, key=lambda m: ROW[m["key"]]["chrono"]) if ROW[m["key"]].get("optional_cvar")]
for i, m in enumerate(OPTM):
    k = m["key"]
    rect = "rect %d 378 %d 24" % (50 + i * 276, 264)
    for md, mg, chrono in MODES:
        gs, ls = unlock_gates(k, md, mg)
        for j, g in enumerate(gs):
            F += ["resource", "Button", "{", 'name "ngf_%s_%s%d"' % (k, md, j), rect, 'title "%s  %s"' % (CAMPNAME[m["camp"]], m["name"]),
                  "fgcolor 0.88 0.83 0.66 1.00", "bgcolor 0.16 0.12 0.08 0.92", 'borderstyle "3D_BORDER"', 'font "verdana-12"',
                  'clicksound "sound/menu/apply.wav"', 'stuffcommand "seta coop_spChrono %d; pushmenu hzm_ngflat_%sdiff"' % (chrono, k),
                  'enabledcvar "%s"' % g, "}"]
        for j, g in enumerate(ls):
            F += ["resource", "Label", "{", 'name "ngf_%s_%slk%d"' % (k, md, j), rect, 'title "%s  %s  (LOCKED)"' % (CAMPNAME[m["camp"]], m["name"]),
                  "fgcolor 0.50 0.47 0.42 1.00", "bgcolor 0.12 0.10 0.08 0.80", 'borderstyle "3D_BORDER"', 'font "verdana-12"',
                  'enabledcvar "%s"' % g, "}"]
F += gen_ops.flat(F)              # [Live Operations] the strip of live contracts + the flat dispatch card
F += ["resource", "Button", "{", 'name "back"', "rect 8 448 96 24", "fgcolor 1.00 1.00 1.00 1.00", "bgcolor 0.00 0.00 0.00 0.00", 'borderstyle "3D_BORDER"',
      'shader "textures/mohmenu/back"', 'hovershader "textures/mohmenu/back_h"', 'clicksound "sound/menu/apply.wav"', 'stuffcommand "hzm_ops close; popmenu 1"', "}", "end."]
open(os.path.join(UI, "hzm_ngflat.urc"), "wb").write((NL.join(F) + NL).encode("latin-1"))

# ---- main.urc: the flat NEW GAME and BRIEFING buttons open the chooser; idempotent
mp = os.path.join(UI, "main.urc")
mt = open(mp, "rb").read().decode("latin-1")
nb = 0
for bn in ("new game old", "briefing"):
    pat = re.compile(r'(name "%s"\r\n(?:(?!\r\n\}).)*?stuffcommand ")pushmenu (?:briefingroom|hzm_ngflat)(")' % re.escape(bn), re.S)
    mt, k_ = pat.subn(lambda mm: mm.group(1) + "pushmenu hzm_ngflat" + mm.group(2), mt)
    nb += k_
assert nb == 2, nb
open(mp, "wb").write(mt.encode("latin-1"))
print("ng3campaigns: %d missions, %d hotspots, %d widgets" % (len(MIS), len(hots), sum(1 for x in wid if x == "Label")))

# ---- coop_mod/spcampaign_table.scr: the last level of each mission -> its key (spcampaign.scr::lastKey calls it)
T = ["//==========================================================================================================//",
     "// GENERATED by docs/proposals/sp3camp_2026-11-08/make_ng3campaigns.py from missions.json - do not hand-edit.",
     "// lastKey <map>: the mission key whose LAST level <map> is (finishing it in single player marks the mission done), \"\" otherwise.",
     "//==========================================================================================================//",
     "lastKey local.m:{", "\tlocal.r = \"\""]
first = True
for m in MJ["missions"]:
    cond = " || ".join('local.m == "%s"' % l for l in m["last"])
    T.append("\t%sif( %s ){ local.r = \"%s\" }" % ("" if first else "else ", cond, m["key"]))
    first = False
T.append("}end local.r")
open(os.path.join(MOD, "coop_mod", "spcampaign_table.scr"), "wb").write((NL.join(T) + NL).encode("latin-1"))

# ---- [byo69] coop_mod/byo_campaign.scr: routing into and out of the own-disc (optional) missions, for every campaign
# The order is missions.json "chrono". An optional mission is entered from the LAST level of the mission before it in that
# order, and left to the first mission after it - in the Full Campaign (coop), the Chronological Campaign (coop) and the
# single-player chronological order alike (the two inserted pilots sit between missions whose own vanilla hand-off is the
# same: AA 1 -> AA 2, AA 4 -> AA 5). Only when EVERY player on the server has it (engine coop_byoAll) - otherwise skipped,
# never a dead end. A saved destination that is no longer there resolves to the next mission (resolve).
def _entry(r):
    return r["brief"]


BYOS = [m for m in MJ["missions"] if m.get("optional_cvar")]
ORD = [ROW[k] for k in CHRONO]


def _succ(i):
    """the first mission after position i: [(token, entry)] of the optional ones on the way, then the plain one's entry"""
    chain = []
    for r in ORD[i + 1:]:
        if r.get("optional_cvar"):
            chain.append(r)
            continue
        return chain, _entry(r)
    return chain, "END"


def _route(lines, ind, chain, final):
    """nested ifs: the first present optional mission of the chain, else the plain successor"""
    if not chain:
        lines.append(ind + 'local.r = "%s"' % final)
        return
    r = chain[0]
    lines.append(ind + 'if( waitthread has "%s" ){ local.r = waitthread entry "%s" }' % (r["byo"]["token"], r["key"]))
    lines.append(ind + "else {")
    _route(lines, ind + "\t", chain[1:], final)
    lines.append(ind + "}")


B = ["//==========================================================================================================//",
     "// GENERATED by docs/proposals/sp3camp_2026-11-08/make_ng3campaigns.py from missions.json - do not hand-edit.",
     "// Own-disc missions in the campaigns (Frontline / European Assault, converted on the player's PC; INTEGRATION.md).",
     "// redirect <map>: when <map> is the LAST level of a mission and the next mission in campaign order is an own-disc one that",
     "//   every player here has, that mission's entry; when <map> is an own-disc mission's last level, the next mission after it;",
     "//   \"\" otherwise (the map's own next level stands). Callers: chrono.scr::nextMission (both chronological campaigns) and",
     "//   global/missioncomplete.scr (the coop Full Campaign). exitNext <map>: where an own-disc level hands over at its end.",
     "// has <token>: 1 when this server and every connected player can load it (engine cvar coop_byoAll, \" fl_1_1 ... \").",
     "// resolve <map>: a saved campaign destination that is an own-disc map no longer present -> the next mission's entry.",
     "//==========================================================================================================//",
     "has local.tok:{", '\tlocal.r = 0', '\tlocal.all = getcvar "coop_byoAll"',
     '\tif( local.all != "" && ( waitthread coop_mod/main.scr::containsText local.all ( " " + local.tok + " " ) 0 ) ){ local.r = 1 }',
     "}end local.r", "",
     "// the map a mission starts on: its briefing room when that was converted too (films are optional), else the level",
     "entry local.key:{", '\tlocal.r = ""']
for r in BYOS:
    B += ['\tif( local.key == "%s" ){' % r["key"],
          '\t\tlocal.r = "%s"' % r["byo"]["map"],
          '\t\tif( waitthread has "%s" ){ local.r = "%s" }' % (r["byo"]["brief_token"], r["brief"]), "\t}"]
B += ["}end local.r", "", "redirect local.m:{", '\tlocal.r = ""']
for i, r in enumerate(ORD):
    chain, final = _succ(i)
    if r.get("optional_cvar"):
        conds = r["last"]
    elif chain:
        conds = r["last"]
    else:
        continue
    B.append("\tif( %s ){" % " || ".join('local.m == "%s"' % l for l in conds))
    if r.get("optional_cvar"):
        _route(B, "\t\t", chain, final)
    else:
        # only the optional ones: no present optional mission = "" (the map's own / the table's next mission stands)
        _route(B, "\t\t", chain, "")
    B.append("\t}")
B += ["}end local.r", "",
      "exitNext local.m:{",
      "\tlocal.r = local.m",
      "\tif( level.gametype != 0 && getcvar( \"coop_campaign\" ) == \"1\" ){",
      "\t\tlocal.n = waitthread redirect local.m",
      "\t\tif( local.n != \"\" && local.n != \"END\" ){ local.r = local.n }",
      "\t}",
      "}end local.r", "",
      "resolve local.m:{", "\tlocal.r = local.m"]
for i, r in enumerate(ORD):
    if not r.get("optional_cvar"):
        continue
    chain, final = _succ(i)
    # the level gone: the next mission; only its briefing room gone (films are optional): the level itself
    B.append('\tif( local.m == "%s" && ( waitthread has "%s" ) != 1 ){' % (r["brief"], r["byo"]["brief_token"]))
    B.append('\t\tlocal.m = "%s"' % r["byo"]["map"])
    B.append('\t\tlocal.r = local.m')
    B.append("\t}")
    B.append('\tif( local.m == "%s" && ( waitthread has "%s" ) != 1 ){' % (r["byo"]["map"], r["byo"]["token"]))
    _route(B, "\t\t", chain, final)
    B.append("\t}")
    B.append('\tif( local.r != local.m ){ println ( "^~^~^ BYO_RESOLVE " + local.m + " -> " + local.r ) }')
B += ["}end local.r"]
open(os.path.join(MOD, "coop_mod", "byo_campaign.scr"), "wb").write((NL.join(B) + NL).encode("latin-1"))
print("byo_campaign: %d own-disc missions" % len(BYOS))
