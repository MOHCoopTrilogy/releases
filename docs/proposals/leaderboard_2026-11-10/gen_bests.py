"""gen_bests.py --mod <mod dir> --add <menus-pak add dir> [--check]  -  v1.10.73 PERSONAL BESTS (PLAN.md, option C).

Writes, from ONE mission list (docs/proposals/mission_tile_art_2026-09-29/tools/titles.json, the chalk names the menus use):
  <mod>/coop_mod/bests_table.scr   level.coop_pbMap[i] / coop_pbIdx[map] / coop_pbCount  (i = the row index everywhere)
  <mod>/ui/coop_pb.urc             the PERSONAL BESTS screen: three campaign pages (coop_pbPg 0/1/2), baked paper backgrounds,
                                   value Labels (linkcvar coop_pb*) placed on the baked rows
  <add>/textures/mohmenu/hzm_pb_pg<k>.jpg + <add>/scripts/hzm_pb.shader   the three page backgrounds (menus pak: the tex pak
                                   baseline gate keeps new textures out of the mod tree)
--check prints the layout and writes nothing. The value cvars are pushed by coop_mod/bests.scr::bests_export.
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
TITLES = os.path.join(HERE, "..", "mission_tile_art_2026-09-29", "tools", "titles.json")
AA = ["m1l1", "m1l2a", "m1l2b", "m1l3a", "m1l3b", "m1l3c", "m2l1", "m2l2a", "m2l2b", "m2l2c", "m2l3", "m3l1a", "m3l1b", "m3l2",
      "m3l3", "m4l1", "m4l2", "m4l3", "m5l1a", "m5l1b", "m5l2a", "m5l2b", "m5l3", "m6l1a", "m6l1b", "m6l1c", "m6l2a", "m6l2b",
      "m6l3a", "m6l3b", "m6l3d", "m6l3c", "m6l3e"]
SH = ["t1l1", "t1l2", "t1l3", "t2l1", "t2l2", "t2l3", "t2l4", "t3l1", "t3l2"]
BT = ["e1l1", "e1l2", "e1l3", "e1l4", "e2l1", "e2l2", "e2l3", "e3l1", "e3l2", "e3l3", "e3l4"]
PAGES = [("ALLIED ASSAULT", AA), ("SPEARHEAD", SH), ("BREAKTHROUGH", BT)]
MAPS = AA + SH + BT

# ---- layout, virtual 640 x 480 (the urc and the bake share these numbers)
PX, PY, PW, PH = 64, 10, 512, 460          # the paper
TEX_W, TEX_H = 1024, 1024                  # the texture (stretched onto the paper rect)
SX, SY = TEX_W / PW, TEX_H / PH
REC_ROWS = ["Missions cleared", "Flawless clears (never went down)", "Longest flawless run", "Missions with a best time",
            "Most kills in one mission"]
REC_CV = ["coop_pbC", "coop_pbF", "coop_pbSB", "coop_pbN", "coop_pbKm"]
CAR_ROWS = ["Rank", "Prestige", "Total XP", "XP to next rank", "Orders of the Day done"]
CAR_CV = ["coop_xp_rankName", "coop_xp_prestige", "coop_xp_totalOwn", "coop_xp_next", "coop_dlyC"]
BLK_Y, BLK_DY = 96, 13                     # first block row, row step
LX0, LX1 = 82, 306                         # RECORDS block: text x, value right edge
RX0, RX1 = 336, 558                        # CAREER block
KM_Y = BLK_Y + 5 * BLK_DY                  # the most-kills mission's name, under the records
TAB_Y, TAB_H = 186, 16
TABS = [(82, 226), (248, 392), (414, 558)]
HDR_Y = 210                                # table header
ROW_Y, ROW_DY, ROWS = 224, 13.5, 17
COLS = [(82, 272, 306), (336, 524, 558)]   # (name x, time right edge, kills right edge)
FOOT_Y = 455
INK = (40, 34, 28)
FONTS = r"C:\Windows\Fonts"


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def names():
    t = json.load(open(TITLES, encoding="utf-8"))["tiles"]
    out = {}
    for m in MAPS:
        title = t[m]["title"]
        out[m] = "%s  %s" % (m[1], title)             # the campaign's mission number, then the chalk name
    return out


def paper_bg(seed):
    rng = np.random.default_rng(seed)
    a = rng.normal(0, 1, (TEX_H // 8 + 1, TEX_W // 8 + 1)).astype(np.float32)
    im = Image.fromarray(np.uint8(np.clip(128 + a * 40, 0, 255))).resize((TEX_W, TEX_H), Image.BICUBIC)
    n = (np.asarray(im, np.float32) - 128) / 40.0
    g = rng.normal(0, 1, (TEX_H, TEX_W)).astype(np.float32) * 0.3
    base = np.array((232, 223, 196), np.float32)
    px = np.clip(base[None, None, :] + (n + g)[..., None] * 4, 0, 255)
    yy, xx = np.mgrid[0:TEX_H, 0:TEX_W]
    e = np.minimum.reduce([xx, yy, TEX_W - 1 - xx, TEX_H - 1 - yy]).astype(np.float32)
    wear = np.clip(e / 28.0, 0, 1) ** 0.6
    px = px * (0.86 + 0.14 * wear[..., None]) + (1 - wear[..., None]) * np.array([10, 8, 4])
    return Image.fromarray(np.uint8(np.clip(px, 0, 255)))


def T(x, y):
    """virtual (screen) -> texture pixels"""
    return (x - PX) * SX, (y - PY) * SY


def text(d, x, y, s, f, anchor="la"):
    d.text(T(x, y), s, font=f, fill=INK, anchor=anchor)


def leader(d, x0, x1, y, f):
    """dotted leader from x0 to x1 (virtual), on the text baseline"""
    a, b = T(x0, y)[0], T(x1, y)[0]
    yy = T(0, y)[1]
    w = d.textlength(". ", font=f)
    k = a
    while k + w < b:
        d.text((k, yy), ".", font=f, fill=(150, 138, 116), anchor="ls")
        k += w


def page(k, NM):
    title, maps = PAGES[k]
    im = paper_bg(40 + k)
    d = ImageDraw.Draw(im)
    fh, fs, fb, fr, fsm = font("STENCIL.TTF", 60), font("georgiab.ttf", 22), font("georgiab.ttf", 21), font("georgia.ttf", 20), font("georgiai.ttf", 18)
    frow = font("georgia.ttf", 18)
    text(d, 320, 18, "PERSONAL BESTS", fh, "ma")
    text(d, 320, 58, "YOUR OWN RECORDS", fs, "ma")
    d.line((*T(82, 76), *T(558, 76)), fill=INK, width=3)
    text(d, LX0, 81, "RECORDS", fb)
    text(d, RX0, 81, "CAREER", fb)
    for i, r in enumerate(REC_ROWS):
        y = BLK_Y + i * BLK_DY
        text(d, LX0, y, r, fr)
        leader(d, LX0 + d.textlength(r, font=fr) / SX + 3, LX1 - 40, y + 10, fr)
    for i, r in enumerate(CAR_ROWS):
        y = BLK_Y + i * BLK_DY
        text(d, RX0, y, r, fr)
        leader(d, RX0 + d.textlength(r, font=fr) / SX + 3, RX1 - 62, y + 10, fr)
    d.line((*T(82, 180), *T(558, 180)), fill=INK, width=2)
    for j, (x0, x1) in enumerate(TABS):
        cx = (x0 + x1) / 2
        if j == k:
            d.rectangle((*T(x0, TAB_Y - 1), *T(x1, TAB_Y + TAB_H)), outline=INK, width=3)
            text(d, cx, TAB_Y + 1, PAGES[j][0], fb, "ma")
        else:
            text(d, cx, TAB_Y + 1, PAGES[j][0], fr, "ma")
    cols = [maps[:ROWS], maps[ROWS:]]
    for c, (nx, tx, kx) in enumerate(COLS):
        if not cols[c]:
            continue
        text(d, nx, HDR_Y, "MISSION", fb)
        fhd = font("georgiab.ttf", 17)
        text(d, tx, HDR_Y + 1, "TIME", fhd, "ra")
        text(d, kx, HDR_Y + 1, "KILLS", fhd, "ra")
        for r, m in enumerate(cols[c]):
            y = ROW_Y + r * ROW_DY
            s, fz = NM[m], 18
            fn = frow
            while d.textlength(s, font=fn) / SX > tx - nx - 36:       # a long chalk name: a smaller face, never cut
                fz -= 1
                fn = font("georgia.ttf", fz)
            assert fz >= 14, s
            text(d, nx, y + (18 - fz) * 0.4 / SY * 2, s, fn)
            leader(d, nx + d.textlength(s, font=fn) / SX + 3, tx - 32, y + 10, frow)
    text(d, LX0, FOOT_Y, "Kept on this PC.  A best time needs you there from the start of the mission.", fsm)
    return im


def label(name, rect, cv, align="right", en=None, title=None, color="0.16 0.13 0.10 1.00"):
    L = ["resource", "Label", "{", 'name "%s"' % name, "rect %d %d %d %d" % rect, "fgcolor %s" % color,
         "bgcolor 0.00 0.00 0.00 0.00", 'borderstyle "NONE"', 'font "verdana-12"', "textalign %s" % align, "dontlocalize"]
    if en:
        L.append('enabledcvar "%s"' % en)
    if title is not None:
        L.append('title "%s"' % title)
    if cv:
        L.append('linkcvar "%s"' % cv)
    return "\n".join(L + ["}", ""])


def urc(NM):
    o = ["// HZM coop - PERSONAL BESTS (the MP room's NOTICES board, 4th notice). GENERATED by",
         "// docs/proposals/leaderboard_2026-11-10/gen_bests.py - DO NOT HAND-EDIT. Values are ARCHIVED client cvars pushed by",
         "// coop_mod/bests.scr::bests_export (coop_pbT<i> / coop_pbK<i>: row i of coop_mod/bests_table.scr); the career rows",
         "// read xp.scr's / daily.scr's own pushed cvars. Pages: coop_pbPg 0 / 1 / 2 (no pushmenu on a tab switch, bug-461).",
         'menu "coop_pb" 640 480 NONE 1', "borderstyle NONE", "bgcolor 0 0 0 0", "align centerx centery", "virtualres 1",
         "fullscreen 0", "", "direction from_top 0", 'include "ui/hzm_mpui_scene_record.inc"', ""]
    for k in range(3):
        o.append("\n".join(["resource", "Label", "{", "ordernumber 50", 'name "pbbg%d"' % k, "rect %d %d %d %d" % (PX, PY, PW, PH),
                            "fgcolor 1.00 1.00 1.00 1.00", "bgcolor 0.00 0.00 0.00 0.00", 'borderstyle "NONE"',
                            'enabledcvar "coop_pbPg==%d"' % k, 'shader "hzm_pb_pg%d"' % k, "}", ""]))
    for i, cv in enumerate(REC_CV):
        o.append(label("pbr%d" % i, (LX1 - 60, BLK_Y + i * BLK_DY - 1, 60, 13), cv))
    for i, m in enumerate(MAPS):        # the most-kills mission: one label per mission, shown by index
        o.append(label("pbkm%d" % i, (LX0 + 12, KM_Y - 1, LX1 - LX0 - 12, 13), None, "left", "coop_pbKmI==%d" % i, NM[m],
                       "0.30 0.22 0.12 1.00"))
    for i, cv in enumerate(CAR_CV):
        o.append(label("pbc%d" % i, (RX1 - 90, BLK_Y + i * BLK_DY - 1, 90, 13), cv))
    for k, (_t, maps) in enumerate(PAGES):
        cols = [maps[:ROWS], maps[ROWS:]]
        for c, (nx, tx, kx) in enumerate(COLS):
            for r, m in enumerate(cols[c]):
                i = MAPS.index(m)
                y = int(round(ROW_Y + r * ROW_DY)) - 1
                o.append(label("pbt%d" % i, (tx - 34, y, 34, 13), "coop_pbT%d" % i, en="coop_pbPg==%d" % k))
                o.append(label("pbk%d" % i, (kx - 24, y, 24, 13), "coop_pbK%d" % i, en="coop_pbPg==%d" % k))
    for j, (x0, x1) in enumerate(TABS):
        o.append("\n".join(["resource", "Button", "{", 'name "pbtab%d"' % j, "rect %d %d %d %d" % (x0, TAB_Y - 2, x1 - x0, TAB_H + 4),
                            "fgcolor 0 0 0 0", "bgcolor 0 0 0 0", 'borderstyle "NONE"', 'clicksound "sound/menu/apply.wav"',
                            'stuffcommand "set coop_pbPg %d"' % j, "}", ""]))
    o.append("\n".join(["resource", "Button", "{", 'name "pbback"', "rect 506 452 52 14", 'title "BACK"',
                        "fgcolor 0.93 0.89 0.78 1.00", "bgcolor 0.18 0.15 0.11 0.95", 'borderstyle "NONE"', 'font "verdana-12"',
                        "textalign center", 'clicksound "sound/menu/apply.wav"', 'stuffcommand "popmenu 0"', "}", ""]))
    o.append("end.")
    return "\n".join(o) + "\n"


def table():
    o = ["//=========================================================================",
         "// bests_table.scr - GENERATED by docs/proposals/leaderboard_2026-11-10/gen_bests.py. DO NOT EDIT.",
         "// The PERSONAL BESTS missions in screen order (ui/coop_pb.urc rows). coop_mod/bests.scr reads it.",
         "//=========================================================================", "", "pb_table:{"]
    for i, m in enumerate(MAPS):
        o.append('\tlevel.coop_pbMap[%d] = "%s"' % (i, m))
        o.append('\tlevel.coop_pbIdx["%s"] = %d' % (m, i))
    o += ["\tlevel.coop_pbCount = %d" % len(MAPS), "}end", ""]
    return "\r\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod")
    ap.add_argument("--add")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    NM = names()
    assert len(set(MAPS)) == len(MAPS) == 53
    assert max(len(p[1]) for p in PAGES) <= 2 * ROWS
    if a.check:
        for m in MAPS:
            print(m, NM[m])
        return
    if a.mod:
        open(os.path.join(a.mod, "coop_mod", "bests_table.scr"), "w", newline="").write(table())
        open(os.path.join(a.mod, "ui", "coop_pb.urc"), "w", newline="\r\n").write(urc(NM))
    if a.add:
        td = os.path.join(a.add, "textures", "mohmenu")
        os.makedirs(td, exist_ok=True)
        os.makedirs(os.path.join(a.add, "scripts"), exist_ok=True)
        sh = []
        for k in range(3):
            page(k, NM).save(os.path.join(td, "hzm_pb_pg%d.jpg" % k), quality=92)
            sh.append("hzm_pb_pg%d\n{\n\tnopicmip\n\tnomipmaps\n\t{\n\t\tclampmap textures/mohmenu/hzm_pb_pg%d.jpg\n"
                      "\t\trgbGen identity\n\t}\n}" % (k, k))
        open(os.path.join(a.add, "scripts", "hzm_pb.shader"), "w", newline="\n").write(
            "// generated by docs/proposals/leaderboard_2026-11-10/gen_bests.py: the PERSONAL BESTS pages\n\n" + "\n\n".join(sh) + "\n")
    print("gen_bests: %d missions, pages %s" % (len(MAPS), [len(p[1]) for p in PAGES]))


if __name__ == "__main__":
    sys.exit(main())
