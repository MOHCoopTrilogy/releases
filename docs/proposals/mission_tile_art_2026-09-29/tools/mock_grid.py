"""mock_grid.py - before/after mocks of the coop mission select, plus the war-room board, from the sample tiles.

    python tools/mock_grid.py

Uses the menu remaster's offline .urc renderer (docs/proposals/menu_system_remaster_2026-09-29/theme/urcdraw.py) READ-ONLY:
it is imported, never edited, and nothing is written into that proposal. It draws the SHIPPED ui/coop_start.urc with the
engine's rules (virtual 640x480, stretch, bgfill colour swap, fonts from the real RitualFont tables).

Writes ../samples/mock/:
  grid_<s|c>_before_after_<W>x<H>.png  today vs the new cards, per menu layout (s = default stretch, c = centred)
  tiles_<s|c>_1to1_<W>x<H>.png         the tile rows cropped at real screen pixels (what a player sees)
  warroom_sicily_<mode>.png       the remaster's own Sicily board, only its blank briefing card replaced (brief_e2)
  warroom_mixed_<mode>.png        the same board with four sample prints, captions re-typed from titles.json
Tile slots hold the 8 samples, which come from different missions: the mission header reads 'SAMPLES'.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)
OUT = os.path.join(PROP, "samples", "mock")
REM = r"C:\mohaa-coop-dev\docs\proposals\menu_system_remaster_2026-09-29"
sys.path.insert(0, os.path.join(REM, "theme"))
import urcdraw as U  # noqa: E402

sys.path.insert(0, HERE)
import fontfit  # noqa: E402

import samples as SMP  # noqa: E402

ORDER = SMP.live()          # the samples that exist now (pending re-stages join after the staging run)
CV = {"ui_voodoo": "0", "ui_menuCenter": "0", "ui_dedicated": "0", "ui_dmmap": "m1l2a", "developer": "0"}


def today_state():
    """per sample: today's shader + today's engine label for that bsp, swept from the inventory."""
    inv = json.load(open(os.path.join(PROP, "inventory.json"), encoding="utf-8"))["tiles"]
    src = json.load(open(os.path.join(PROP, "sources", "SOURCES.json")))
    by = {}
    for r in inv:
        by.setdefault(r["bsp"], r)          # first board that shows it
    return {i: by[src[i]["bsp"]] for i in ORDER}


def render(W, H, after, mode="s"):
    """mode s = the DEFAULT stretched menu (ui_menuCenter 0), c = centred (ui_menuCenter 1). The new art uses the
    matching per-layout texture; today's art is one texture for both."""
    st = today_state()
    cv = U.Canvas(W, H, mode == "c")
    tiles = {"coop_startMap%d" % (k + 1): i for k, i in enumerate(ORDER)}

    def tile(c, r, w):
        n = w["name"][0]
        if n not in tiles:
            return
        i = tiles[n]
        if after:
            c.image(r, Image.open(os.path.join(PROP, "samples", "game", "%s_%s.jpg" % (i, mode))).convert("RGBA"))
        else:
            c.image(r, U.resolve(st[i]["shader"]))
            lab = st[i]["label_today"]
            if lab:                             # Button title: facfont-20, centred in the rect (coop_maps.inc)
                c.text(r, lab, "facfont-20", (1, 1, 1, 1), "center")

    sp = {k: tile for k in tiles}
    for k in range(len(ORDER) + 1, 12):
        sp["coop_startMap%d" % k] = lambda c, r, w: None
    sp["coop_startServerLogo"] = lambda c, r, w: None
    sp["coop_startMapSelect"] = lambda c, r, w: None

    def mname(c, r, w):
        c.fill(r, U.f4(w, "bgcolor", (0, 0, 0, 0)))
        c.engine_bevel(r, U.f4(w, "bgcolor", (0, 0, 0, 0)), inset=True)
        c.image(r, U.resolve("textures/mohmenu/weapon_sign"))
        c.text(r, "SAMPLES (mixed missions)", "facfont-20", (1, 1, 1, 1), "center")
    sp["coop_missionName"] = mname
    U.render(cv, "ui/coop_start.urc", CV, special=sp,
             fields={"sv_hostname": "HZM Coop", "password": "", "sv_maxclients": "8", "ui_dmmap": "m1l2a",
                     "coop_lmsLives": "0", "coop_health": "750"})
    return cv.img.convert("RGB")


def label(im, text, h=44):
    out = Image.new("RGB", (im.width, im.height + h), (12, 12, 12))
    out.paste(im, (0, h))
    ImageDraw.Draw(out).text((12, 8), text, font=fontfit.caption_font(28, 600, 100), fill=(250, 199, 71))
    return out


def grids():
    os.makedirs(OUT, exist_ok=True)
    for mode, mname in (("s", "stretched (default, ui_menuCenter 0)"), ("c", "centred (ui_menuCenter 1)")):
        for W, H in ((1920, 1080), (1280, 720)):
            b, a = render(W, H, False, mode), render(W, H, True, mode)
            gap = 16
            S = Image.new("RGB", (2 * W + gap, H + 44), (12, 12, 12))
            S.paste(label(b, "TODAY  %dx%d %s" % (W, H, mname)), (0, 0))
            S.paste(label(a, "NEW  %dx%d %s - card_%s textures" % (W, H, mname, mode)), (W + gap, 0))
            S.save(os.path.join(OUT, "grid_%s_before_after_%dx%d.png" % (mode, W, H)), optimize=True)
            # 1:1 crop of the tile rows (virtual y 130..366), in the layout's own coordinate frame
            sx, sy = W / 640.0, H / 480.0
            ox = 0
            if mode == "c":
                sx = sy = min(sx, sy)
                ox = (W - 640 * sx) / 2
            box = (int(ox), int(130 * sy), int(ox + 640 * sx), int(366 * sy))
            cb, ca = b.crop(box), a.crop(box)
            T = Image.new("RGB", (cb.width, 2 * cb.height + 88), (12, 12, 12))
            T.paste(label(cb, "TODAY - tile rows at real screen pixels, %dx%d %s" % (W, H, mode)), (0, 0))
            T.paste(label(ca, "NEW - tile rows at real screen pixels, %dx%d %s" % (W, H, mode)), (0, cb.height + 44))
            T.save(os.path.join(OUT, "tiles_%s_1to1_%dx%d.png" % (mode, W, H)), optimize=True)
            print("grid", mode, W, H)


# remaster station 04 (station_layouts.py COOPOPS, read here, never edited): 2x2 large prints, 4:3 in menu units, the
# typed caption drawn BELOW each rect (caption_h). Rendered by the room agent at 1920x1080 in both menu layouts.
STATIONS = os.path.join(REM, "mockups", "stations")


def layout():
    sys.path.insert(0, os.path.join(REM, "theme"))
    import station_layouts as SL
    return SL.COOPOPS


def to_px(r, mode, W=1920, H=1080):
    if mode == "stretched":
        sx, sy, ox = W / 640.0, H / 480.0, 0
    else:
        sx = sy = min(W / 640.0, H / 480.0)
        ox = (W - 640 * sx) / 2
    return (int(round(ox + r[0] * sx)), int(round(r[1] * sy)), int(round(ox + (r[0] + r[2]) * sx)), int(round((r[1] + r[3]) * sy)))


def warroom_one(mode, picks, redraw_captions, tag):
    C = layout()
    im = Image.open(os.path.join(STATIONS, "04_coop_operations_%s_1920x1080.png" % mode)).convert("RGB")
    d = ImageDraw.Draw(im)
    titles = json.load(open(os.path.join(HERE, "titles.json"), encoding="utf-8"))["tiles"]
    src = json.load(open(os.path.join(PROP, "sources", "SOURCES.json")))
    f = ImageFont.truetype(r"C:\Windows\Fonts\verdana.ttf", 22)      # the remaster's captions are verdana-12
    for r, i in zip(C["tiles_large"], picks):
        if i is None:
            continue
        box = to_px(r, mode)
        lay = "s" if mode == "stretched" else "c"
        p = Image.open(os.path.join(PROP, "samples", "full", "%s_print_%s_1024x768.jpg" % (i, lay))).convert("RGB")
        im.paste(p.resize((box[2] - box[0], box[3] - box[1]), Image.LANCZOS), box[:2])
        if redraw_captions:
            cap = to_px((r[0], r[1] + r[3] + 2, r[2], C["caption_h"]), mode)
            strip = im.crop(cap)
            mount = tuple(int(v) for v in np.median(np.asarray(strip).reshape(-1, 3), axis=0))
            d.rectangle(cap, fill=mount)
            t = titles[src[i]["bsp"]]["title"]
            tw = d.textlength(t, font=f)
            d.text(((cap[0] + cap[2] - tw) / 2, cap[1] + (cap[3] - cap[1] - 24) / 2), t, font=f, fill=(41, 23, 8))
    b = to_px(C["board"], mode)
    # start below the mission-name slate: mixed-mission prints must never sit under one mission's name
    nm = to_px(C["name"], mode)
    board = im.crop((max(0, b[0] - 10), nm[3] + 6, min(1920, b[2] + 10), min(1080, b[3] + 10)))
    return board


def warroom():
    have = set(ORDER)
    for mode in ("stretched", "centred"):
        if "brief_e2" in have:
            a = warroom_one(mode, ["brief_e2", None, None, None], False, "sicily")
            label(a, "WAR ROOM %s - the room agent's Sicily board; only its blank SICILY card replaced" % mode.upper()
                  ).save(os.path.join(OUT, "warroom_sicily_%s.png" % mode), optimize=True)
        picks = [i for i in ("brief_t2", "sh1_t2l1", "bt2_e1l3", "aa1_m1l2a", "aa2_m5l2a", "bt1_e1l1") if i in have][:4]
        picks += [None] * (4 - len(picks))
        b = warroom_one(mode, picks, True, "mixed")
        label(b, "WAR ROOM %s - sample prints (mixed missions), captions from titles.json" % mode.upper()
              ).save(os.path.join(OUT, "warroom_mixed_%s.png" % mode), optimize=True)
        print("warroom", mode)


if __name__ == "__main__":
    grids()
    warroom()
