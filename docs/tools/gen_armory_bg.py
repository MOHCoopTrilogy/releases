"""Bake the Field Requisition armory background (overhaul concept 01, user-approved 2026-08-18).

Replaces textures/mohmenu/coop_lo_bg2.tga (2048x2048 on the 640x480 virtual grid, SCALE = 3.2)
with the riveted olive-steel material world: header band + wordmark, four plated panels with
brass section headers, viewport wells with corner brackets, a blueprint-grid inspection bay,
baked stat/section labels, the finish tray with material swatches, and the instruction caption.

Every functional widget rect stays exactly where it is - this is art underneath the existing
interaction layer. THE CLEANLINESS RULE IS LAW ("I'd like to make sure it's clean... no text
overlaps"): every baked-text box is collision-checked against every text-bearing widget rect
parsed live from ui/coop_loadout.urc, and any intersection FAILS THE BAKE. The layout cannot
drift into overlap without this generator refusing to build.
"""
import io
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
OUT = os.path.join(MOD, "textures", "mohmenu", "coop_lo_bg2.tga")
URC = os.path.join(MOD, "ui", "coop_loadout.urc")

TW = 2048
S = TW / 640.0

# palette (concept 01)
STEEL = (58, 62, 46)
STEEL_D = (47, 51, 39)
STEEL_XD = (35, 38, 29)
PLATE_HI = (255, 255, 255, 12)
BRASS = (179, 144, 63)
BRASS_D = (138, 108, 44)
KHAKI = (205, 191, 142)
CREAM = (230, 220, 186)
DIM = (149, 141, 107)
WELL = (27, 29, 22)
INK_SHADOW = (0, 0, 0, 110)


def px(v):
    return int(round(v * S))


def font(size, bold=True):
    for name in ("HATTEN.TTF", "impact.ttf", "ariblk.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype("C:/Windows/Fonts/" + name, px(size))
        except OSError:
            continue
    return ImageFont.load_default()


img = Image.new("RGB", (TW, TW), STEEL)
dr = ImageDraw.Draw(img, "RGBA")

baked_text_boxes = []   # (x, y, w, h, label) in 640-space - fed to the overlap check


def text(x, y, s, size, fill, tracking=0.0, box_label=None):
    """Baked type at 640-space coords; records its box for the collision check."""
    f = font(size)
    tx = px(x)
    ty = px(y)
    if tracking <= 0:
        dr.text((tx + 2, ty + 2), s, font=f, fill=INK_SHADOW)
        dr.text((tx, ty), s, font=f, fill=fill)
        w = dr.textlength(s, font=f)
    else:
        cx = tx
        step = px(tracking)
        for ch in s:
            dr.text((cx + 2, ty + 2), ch, font=f, fill=INK_SHADOW)
            dr.text((cx, ty), ch, font=f, fill=fill)
            cx += int(dr.textlength(ch, font=f)) + step
        w = cx - tx
    h = px(size * 1.25)
    baked_text_boxes.append((x, y, w / S, h / S, box_label or s[:18]))


def rect(x, y, w, h, fill, outline=None, ow=1):
    dr.rectangle([px(x), px(y), px(x + w), px(y + h)], fill=fill,
                 outline=outline, width=max(1, int(ow * S / 2)))


def vgrad(x, y, w, h, top, bot):
    x0, y0, x1, y1 = px(x), px(y), px(x + w), px(y + h)
    for i in range(y0, y1):
        t = (i - y0) / max(1, (y1 - y0))
        c = tuple(int(top[k] + (bot[k] - top[k]) * t) for k in range(3))
        dr.line([(x0, i), (x1, i)], fill=c)


def rivet(x, y):
    r = px(1.6)
    cx, cy = px(x), px(y)
    dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(78, 79, 60))
    dr.ellipse([cx - r, cy - r, cx + int(r * 0.2), cy + int(r * 0.2)], fill=(155, 152, 120))


def plate(x, y, w, h, header):
    vgrad(x, y, w, h, (71, 75, 56), (51, 55, 42))
    rect(x, y, w, h, None, outline=(31, 34, 25), ow=1.2)
    dr.rectangle([px(x) + 2, px(y) + 2, px(x + w) - 2, px(y) + 5], fill=PLATE_HI)
    for rx, ry in [(x + 3, y + 3), (x + w - 3, y + 3), (x + 3, y + h - 3), (x + w - 3, y + h - 3)]:
        rivet(rx, ry)
    # section header lives in the HEADER BAND's free bottom row, above the panel - the panel
    # tops themselves are wall-to-wall widgets (cosReq1, card1, tabs, the 3D preview), which the
    # first bake's 26 collisions proved. The band row y25.5-33 is genuinely empty.
    dr.rectangle([px(x + 1), px(26.6), px(x + 4.4), px(30.0)], fill=BRASS_D)
    text(x + 7, y - 13.2, header, 6.6, KHAKI, tracking=1.5, box_label="hdr:" + header)


def well(x, y, w, h, brackets=True, grid=False):
    x0, y0, x1, y1 = px(x), px(y), px(x + w), px(y + h)
    cxp, cyp = (x0 + x1) / 2, (y0 + y1) / 2
    maxd = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 / 2
    for i in range(y0, y1):
        for seg in range(1):
            pass
    # radial-ish fill by rows (cheap)
    for i in range(y0, y1):
        t = abs(i - cyp) / max(1, (y1 - y0) / 2)
        c = tuple(int(WELL[k] + (12 - 12 * t)) for k in range(3))
        dr.line([(x0, i), (x1, i)], fill=c)
    rect(x, y, w, h, None, outline=(30, 33, 24), ow=1)
    if grid:
        step = px(12)
        for gx in range(x0 + step, x1, step):
            dr.line([(gx, y0), (gx, y1)], fill=(140, 160, 150, 14))
        for gy in range(y0 + step, y1, step):
            dr.line([(x0, gy), (x1, gy)], fill=(140, 160, 150, 14))
    if brackets:
        L = px(7)
        for (bx, by, dx, dy) in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]:
            dr.line([(bx, by), (bx + dx * L, by)], fill=BRASS_D, width=px(0.5))
            dr.line([(bx, by), (bx, by + dy * L)], fill=BRASS_D, width=px(0.5))


# ---------------- the world ---------------------------------------------------------------------
# base brushed steel: vertical micro-striation
for gx in range(0, TW, 4):
    if (gx // 4) % 3 == 0:
        dr.line([(gx, 0), (gx, TW)], fill=(255, 255, 255, 5))

# header band
vgrad(0, 0, 640, 34, (44, 47, 36), (35, 38, 28))
dr.rectangle([0, px(33), TW, px(34.6)], fill=BRASS_D + (140,))
text(12, 3, "ARMORY", 21, (226, 213, 163), tracking=3.4, box_label="wordmark")
text(100, 14.5, "// REQUISITION OF ORDNANCE - FORM 40-1863", 7, DIM, tracking=1.1)

# panels
plate(6, 38, 142, 438, "OPERATOR")
plate(151, 38, 152, 350, "LOADOUT")
plate(305, 38, 167, 380, "WEAPON RACK")
plate(474, 38, 160, 380, "INSPECTION")

# operator viewport + pager labels
well(12, 82, 134, 312)
text(78, 413.2, "SKIN", 5.6, DIM, tracking=1.6)
text(78, 443.2, "HELMET", 5.6, DIM, tracking=1.6)

# loadout card recesses (cards themselves are widgets; these are the seats they sit in)
for cy in (55, 133, 211, 289):
    rect(152, cy - 1, 150, 76, (0, 0, 0, 45))

# inspect: 3D bay with blueprint grid, stat labels, ammo/recoil wells
well(478, 44, 152, 100, grid=True)
for label, y in (("DMG", 218), ("RPM", 234), ("ACC", 250), ("MOB", 266)):
    text(478, y, label, 7.6, (191, 178, 135), tracking=1.9, box_label="stat:" + label)
# RDS is an ENGINE label (magRds widget) - baking one would double it
text(481, 306, "RECOIL PATTERN", 6.2, DIM, tracking=1.6)
well(481, 317, 70, 58)
well(559, 317, 68, 58)

# finish tray
vgrad(146, 420, 488, 22, (38, 41, 31), (31, 34, 25))
dr.rectangle([px(146), px(420), px(149), px(442)], fill=BRASS_D)
# FINISH is an ENGINE label (finstrip_lbl widget) - the tray + brass tab are ours, the word is its
# swatch underlines beneath each chip rect (chips are engine buttons at y423 h15)
SW = [(228, ((163, 120, 42), (230, 196, 106))), (273, ((143, 151, 155), (223, 230, 234))),
      (318, ((60, 74, 99),) * 2), (363, ((126, 34, 19),) * 2),
      (408, ((78, 90, 51), (55, 65, 31))), (453, ((207, 212, 214), (154, 165, 168))),
      (498, ((194, 168, 120), (160, 135, 87)))]
for sx, cols in SW:
    x0, x1 = px(sx), px(sx + 43)
    y0 = px(439.4)
    half = (x1 - x0) // 2
    dr.rectangle([x0, y0, x0 + half, y0 + px(1.6)], fill=cols[0])
    dr.rectangle([x0 + half, y0, x1, y0 + px(1.6)], fill=cols[1])

# caption (re-baked in the new voice, same place)
text(150, 461.5, "CLICK A SLOT, THEN CLICK A WEAPON TO EQUIP IT.  SAVED INSTANTLY.  MISSION-CRITICAL WEAPONS ARE STILL ISSUED AUTOMATICALLY.",
     6.2, (127, 121, 94), tracking=0.8, box_label="caption")

# gentle vignette
vig = Image.new("L", (TW, TW), 0)
vd = ImageDraw.Draw(vig)
vd.rectangle([0, 0, TW, TW], fill=40)
vd.rectangle([px(30), px(30), TW - px(30), TW - px(30)], fill=0)
vig = vig.filter(ImageFilter.GaussianBlur(px(18)))
img = Image.composite(Image.new("RGB", (TW, TW), (10, 11, 8)), img, vig)
dr = ImageDraw.Draw(img, "RGBA")

# ---------------- THE CLEANLINESS RULE: no baked text under any widget text --------------------
u = io.open(URC, encoding="latin-1").read()
widget_boxes = []
for m in re.finditer(r"resource\s*\r?\n(\w+)\s*\r?\n\{(.*?)\}", u, re.S):
    body = m.group(2)
    rm = re.search(r"rect (\d+) (\d+) (\d+) (\d+)", body)
    nm = re.search(r'name "([^"]+)"', body)
    if not rm:
        continue
    has_text = ('title "' in body and re.search(r'title "[^"]+"', body)) or "linkcvar" in body
    # the fit-tuner overlay (name fit*) is a DEV mode that deliberately draws over the whole
    # lower page behind enabledcvar coop_loFitUI - it is not part of the player-visible layout
    if nm and nm.group(1).startswith("fit"):
        has_text = False
    if has_text:
        x, y, w, h = map(int, rm.groups())
        widget_boxes.append((x, y, w, h, nm.group(1) if nm else "?"))

overlaps = []
for bx, by, bw, bh, bl in baked_text_boxes:
    for wx, wy, ww, wh, wl in widget_boxes:
        if bx < wx + ww and bx + bw > wx and by < wy + wh and by + bh > wy:
            overlaps.append("baked '%s' (%.0f,%.0f %.0fx%.0f) intersects widget '%s' (%d,%d %dx%d)"
                            % (bl, bx, by, bw, bh, wl, wx, wy, ww, wh))
for o in overlaps:
    print("OVERLAP:", o)
if overlaps:
    raise SystemExit("gen_armory_bg: %d text overlap(s) - BAKE REFUSED (the cleanliness rule)" % len(overlaps))

img.save(OUT)
img.resize((1024, 1024)).save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           "..", "..", "_armory_bake_preview.png"))
print("baked %s (%d baked texts, %d widget text rects checked, 0 overlaps)"
      % (os.path.relpath(OUT, ROOT), len(baked_text_boxes), len(widget_boxes)))
