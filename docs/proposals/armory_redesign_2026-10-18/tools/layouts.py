"""layouts.py - the two Armory directions (A "Quartermaster", B "Showroom"), 640x480 virtual grid -> any output size."""
import os
from bm_core import *   # noqa: F401,F403
from bm_core import Cv, background, header, footer, STATS, MOCK, RN, RXP, RIDX, req_state, counts_by_tab, sorted_tab, \
    STAT_ROWS, raw_str, unit_str, delta, ASSETS, \
    TRACK, PANEL, PANEL2, LINE, CREAM, DIM, FAINT, GREEN, RED, ORANGE, BLUE

FINISH_SW = [("STD", (0x8a, 0x73, 0x55)), ("GOLD", (0xd8, 0xa8, 0x3a)), ("CHROME", (0xc9, 0xcd, 0xd1)), ("BLUED", (0x3a, 0x4a, 0x66)),
             ("BLOODY", (0x8b, 0x2a, 0x22)), ("WOODLAND", (0x55, 0x66, 0x3a)), ("WINTER", (0xdd, 0xe4, 0xea)), ("DESERT", (0xc4, 0xa4, 0x6c))]
LOCKED_FIN = (3, 4, 7)      # sample: finishes that need a challenge on this gun


def has(tag):
    return os.path.isfile(os.path.join(ASSETS, tag + ".png"))


def gun(c, wid, x, y, w, h, dim=1.0, fin=None):
    tag = "g%s_f%d" % (wid, fin) if fin else "g" + wid
    if not has(tag):
        tag = "g" + wid
    return c.paste_fit(tag, x, y, w, h, dim=dim)


def operator(c, x, y, w, h, assets, steppers_y):
    c.rect(x, y, w, h, fill=PANEL, line=LINE)
    c.text(x + 6, y + 3, "OPERATOR", 7.5, DIM)
    tag = next((a for a in assets if has(a)), assets[-1])
    c.paste_fit(tag, x + 2, y + 14, w - 4, steppers_y - y - 18)
    for i, (lab, val) in enumerate((("SKIN", "29th Infantry"), ("HELMET", "Wool Cap"), ("GLOVES", "Bare Hands"))):
        yy = steppers_y + i * 29
        c.rect(x + 4, yy, w - 8, 26, fill=PANEL2)
        c.text(x + 8, yy + 2, lab, 7.5, FAINT)
        c.text(x + 8, yy + 11.5, val, 9.5, CREAM)
        c.text(x + w - 24, yy + 8, "<", 10, DIM)
        c.text(x + w - 13, yy + 8, ">", 10, DIM)


def tabs(c, x, y, w, h, active, cnt, gap=2):
    names = ["RIFLE", "SNIPER", "SMG", "HEAVY", "PISTOL", "NADES"]
    tw = (w - gap * 5) / 6
    for i, nm in enumerate(names):
        tx = x + i * (tw + gap)
        on = i == active
        u, t = cnt[i]
        c.rect(tx, y, tw, h, fill=PANEL2 if on else PANEL, line=LINE)
        if on:
            c.rect(tx, y + h - 3, tw, 3, fill=ORANGE)
        c.text(tx + tw / 2, y + 2, nm, 9.5, CREAM if on else DIM, anchor="m")
        c.text(tx + tw / 2, y + h - 11, "%d / %d" % (u, t), 7.5, ORANGE if on else FAINT, anchor="m")


def stat_summary(w):
    bits = []
    if "dmg" in w:
        bits.append("%g DMG" % w["dmg"])
    if "rpm" in w:
        bits.append("%d RPM" % w["rpm"])
    if "clip" in w:
        bits.append("%d RD" % w["clip"])
    return "  ".join(bits)


def swatches(c, x, y, sw, gap, sel, size_h=12):
    for i, (nm, col) in enumerate(FINISH_SW):
        xx = x + i * gap
        on = i == sel
        c.rect(xx, y, sw, size_h, fill=col, line=ORANGE if on else LINE, lw=2 if on else 1)
        if i in LOCKED_FIN:
            c.lock(xx + (sw - 8) / 2, y + (size_h - 8) / 2, 8, TRACK, 0.9)


def progress_color(rs):
    return ORANGE if rs["kind"] == "rank" else BLUE


def pct(rs):
    return "%d%%" % round(rs["frac"] * 100)


# ======================================================================================================================
def build_A(W, H):
    c = Cv(W, H)
    background(c)
    header(c)
    cnt = counts_by_tab()
    operator(c, 10, 36, 136, 420, ["char_rifle_y120", "char_rifle"], 356)

    # ---- loadout slots
    c.text(154, 37, "LOADOUT", 7.5, DIM)
    slots = [("PRIMARY 1", "P1", True), ("PRIMARY 2", "P2", False), ("SIDEARM", "SIDE", False), ("GRENADE", "NADE", False)]
    for i, (lab, key, act) in enumerate(slots):
        y = 47 + i * 82
        wid = MOCK["eq"][key]
        w = STATS[wid]
        c.rect(154, y, 134, 78, fill=PANEL2 if act else PANEL, line=ORANGE if act else LINE, lw=2 if act else 1)
        c.rect(154, y, 3, 78, fill=GREEN)
        c.text(162, y + 3, lab, 7.5, ORANGE if act else DIM)
        gun(c, wid, 162, y + 12, 122, 30)
        c.text(162, y + 46, w["name"], 10.5, CREAM)
        c.text(162, y + 62, stat_summary(w) if key != "NADE" else "FRAGMENTATION", 7.5, DIM)
    c.rect(154, 378, 134, 16, fill=PANEL, line=LINE)
    c.text(221, 382, "USE MAP DEFAULT", 7.5, DIM, anchor="m")
    # legend
    c.text(154, 404, "KEY", 7, FAINT)
    c.rect(154, 414, 3, 9, fill=GREEN)
    c.text(162, 414, "EQUIPPED", 7.5, DIM)
    c.rect(154, 427, 9, 9, line=ORANGE, lw=2)
    c.text(168, 427, "SELECTED", 7.5, DIM)
    c.lock(154, 440, 9, CREAM, 0.8)
    c.text(168, 440, "LOCKED  (SHOWS WHAT UNLOCKS IT)", 7.5, DIM)

    # ---- picker
    c.text(296, 37, "WEAPONS", 7.5, DIM)
    tabs(c, 296, 45, 182, 25, 0, cnt)
    un, lk = sorted_tab(0)
    cur = "03"
    y = 76
    c.text(296, y, "UNLOCKED  %d" % len(un), 7.5, GREEN)
    c.rect(296 + 52, y + 4, 130, 1, fill=LINE)
    y += 11
    cw, ch = 89.5, 44
    for n, wid in enumerate(un):
        x = 296 + (n % 2) * (cw + 3)
        yy = y + (n // 2) * (ch + 3)
        sel = wid == cur
        c.rect(x, yy, cw, ch, fill=PANEL2 if sel else PANEL, line=ORANGE if sel else LINE, lw=2 if sel else 1)
        gun(c, wid, x + 3, yy + 3, cw - 6, 19)
        c.wrap(x + 5, yy + 25, STATS[wid]["name"], cw - 10, 10.5, CREAM)
        if MOCK["eq"]["P1"] == wid:
            c.rect(x + cw - 21, yy + 2, 19, 8, fill=GREEN)
            c.text(x + cw - 11.5, yy + 2.3, "EQ", 6.5, TRACK, anchor="m")
    y += ((len(un) + 1) // 2) * (ch + 3) + 3
    c.text(296, y, "LOCKED  %d" % len(lk), 7.5, DIM)
    c.rect(296 + 44, y + 4, 138, 1, fill=LINE)
    y += 11
    for n, wid in enumerate(lk[:8]):
        x = 296 + (n % 2) * (cw + 3)
        yy = y + (n // 2) * (ch + 3)
        rs = req_state(wid)
        c.rect(x, yy, cw, ch, fill=PANEL, line=LINE)
        gun(c, wid, x + 3, yy + 3, cw - 20, 14, dim=0.3)
        c.lock(x + cw - 12, yy + 3, 9, CREAM, 0.85)
        c.fit(x + 5, yy + 19, STATS[wid]["name"], cw - 10, 7.5, DIM)
        c.fit(x + 5, yy + 28, rs["text"].replace("Rank: ", ""), cw - 10, 7.5, FAINT)
        c.bar(x + 5, yy + ch - 5, cw - 10, 2, rs["frac"], progress_color(rs))

    # ---- inspector
    c.rect(482, 36, 148, 420, fill=PANEL, line=LINE)
    c.rect(486, 40, 140, 84, fill=PANEL2)
    c.alpha_rect(486, 40, 140, 84, ORANGE, 0.06)
    gun(c, cur, 489, 48, 134, 66, fin=1)
    c.text(490, 42, "INSPECT", 7, FAINT)
    c.text(622, 42, "GOLD", 7.5, ORANGE, anchor="r")
    w = STATS[cur]
    c.text(488, 127, w["name"], 15, CREAM)
    c.text(488, 149, "%s  -  %d RD" % (w["cd"], w["clip"]), 7.5, DIM)
    swatches(c, 488, 162, 14, 17.4, 1)
    c.text(488, 177, "FINISH  GOLD", 7, FAINT)
    c.rect(486, 189, 140, 1, fill=LINE)
    eq = STATS[MOCK["eq"]["P1"]]
    c.text(488, 193, "VS EQUIPPED", 7, FAINT)
    c.text(624, 193, eq["name"], 7.5, DIM, anchor="r")
    for i, (lab, key) in enumerate(STAT_ROWS):
        y = 205 + i * 25
        c.text(488, y, lab, 7.5, DIM)
        c.text(590, y - 2, raw_str(w, key), 10.5, CREAM, anchor="r")
        dt, dc = delta(w, eq, key)
        c.text(624, y - 2, dt, 10.5, dc, anchor="r")
        sc = w.get(key)
        if sc is not None:
            c.bar(488, y + 11, 136, 5, sc / 100.0, dc if dc != FAINT else DIM, ghost=(eq.get(key) or 0) / 100.0)
    c.rect(486, 336, 140, 20, fill=ORANGE)
    c.text(556, 340, "EQUIP TO PRIMARY 1", 10.5, TRACK, anchor="m")
    c.rect(486, 366, 140, 1, fill=LINE)
    c.text(488, 370, "NEXT UNLOCK", 7, FAINT)
    nxt = min(lk, key=lambda i: (RXP[RIDX[req_state(i)["text"][6:]]] if req_state(i)["kind"] == "rank" else 1e9))
    rs = req_state(nxt)
    gun(c, nxt, 488, 378, 56, 18)
    c.fit(548, 378, STATS[nxt]["name"], 76, 10.5, CREAM)
    c.text(548, 391, rs["text"], 7.5, DIM)
    c.bar(488, 403, 136, 5, rs["frac"], ORANGE)
    c.text(488, 411, "{:,} / {:,} XP".format(rs["cur"], rs["need"]), 7.5, DIM)
    c.text(624, 411, pct(rs), 7.5, ORANGE, anchor="r")
    c.text(488, 440, "Sample player: Sergeant.", 6.5, FAINT)
    footer(c, "CLICK A SLOT, THEN A WEAPON.  HOVER A GUN TO COMPARE.  LOCKED GUNS SHOW HOW TO EARN THEM.")
    return c.done()


# ======================================================================================================================
def build_B(W, H):
    c = Cv(W, H)
    background(c)
    header(c)
    cnt = counts_by_tab()
    tabs(c, 140, 36, 340, 24, 2, cnt)
    operator(c, 10, 36, 124, 420, ["char_smg_y160", "char_smg"], 356)

    # ---- hero
    cur = "24"
    w = STATS[cur]
    c.rect(140, 64, 340, 152, fill=PANEL, line=LINE)
    c.alpha_rect(140, 64, 340, 152, ORANGE, 0.05)
    c.rect(140, 64, 340, 2, fill=ORANGE)
    gun(c, cur, 150, 70, 320, 96, fin=1)
    c.text(150, 168, w["name"], 15, CREAM)
    c.text(150, 190, "%s   -   %d RD" % (w["cd"], w["clip"]), 7.5, DIM)
    c.text(472, 69, "INSPECT  -  GOLD", 7, FAINT, anchor="r")
    c.rect(412, 192, 60, 14, fill=PANEL2, line=GREEN)
    c.text(442, 195, "UNLOCKED", 7.5, GREEN, anchor="m")

    # ---- slot selector
    c.text(140, 221, "EQUIP INTO", 7, FAINT)
    sl = [("PRIMARY 1", "P1", True), ("PRIMARY 2", "P2", False), ("SIDEARM", "SIDE", False), ("GRENADE", "NADE", False)]
    for i, (lab, key, act) in enumerate(sl):
        x = 140 + i * 86
        wid = MOCK["eq"][key]
        c.rect(x, 229, 82, 41, fill=PANEL2 if act else PANEL, line=ORANGE if act else LINE, lw=2 if act else 1)
        c.text(x + 4, 231, lab, 7, ORANGE if act else FAINT)
        gun(c, wid, x + 4, 240, 74, 15)
        c.fit(x + 4, 257, STATS[wid]["name"], 74, 7.5, CREAM)

    # ---- filmstrip
    un, lk = sorted_tab(2)
    c.text(140, 276, "SMG", 7.5, DIM)
    c.text(162, 276, "UNLOCKED  %d" % len(un), 7.5, GREEN)
    c.text(478, 276, "<   1 / 3   >", 7.5, DIM, anchor="r")
    y = 286
    cw, ch = 62, 68
    x = 140
    for wid in un[:4]:
        sel = wid == cur
        c.rect(x, y, cw, ch, fill=PANEL2 if sel else PANEL, line=ORANGE if sel else LINE, lw=2 if sel else 1)
        gun(c, wid, x + 3, y + 5, cw - 6, 28)
        c.wrap(x + 4, y + 38, STATS[wid]["name"], cw - 8, 10.5, CREAM)
        c.text(x + 4, y + ch - 10, "%d RD" % STATS[wid]["clip"], 7, DIM)
        x += cw + 3
    xl = x + 1
    c.rect(xl, y, 1, ch, fill=LINE)
    c.text(xl + 5, y, "LOCKED  %d" % len(lk), 7, DIM)
    x = xl + 5
    shown = 0
    for wid in lk:
        if x + 50 > 450:
            break
        rs = req_state(wid)
        c.rect(x, y + 10, 50, ch - 10, fill=PANEL, line=LINE)
        gun(c, wid, x + 2, y + 14, 46, 16, dim=0.3)
        c.lock(x + 39, y + 12, 8, CREAM, 0.85)
        c.text(x + 3, y + 12.5, pct(rs), 7, progress_color(rs))
        c.wrap(x + 3, y + 36, STATS[wid]["name"], 45, 7.5, DIM)
        c.bar(x + 4, y + ch - 6, 42, 2, rs["frac"], progress_color(rs))
        x += 53
        shown += 1
    if shown < len(lk):
        c.text(x + 2, y + 30, "+%d" % (len(lk) - shown), 10.5, DIM)
        c.text(x + 2, y + 42, "MORE", 7, FAINT)

    # ---- what unlocks next
    c.rect(140, 359, 340, 1, fill=LINE)
    c.text(140, 363, "WHAT UNLOCKS NEXT", 7, FAINT)
    for i, wid in enumerate(lk[:4]):
        rs = req_state(wid)
        yy = 374 + i * 19
        c.lock(140, yy + 1, 9, CREAM, 0.7)
        c.text(153, yy, STATS[wid]["name"], 9.5, CREAM)
        c.text(153, yy + 12, rs["text"] + (("  " + rs["sub"]) if rs.get("sub") else ""), 7, DIM)
        c.bar(390, yy + 5, 62, 4, rs["frac"], progress_color(rs))
        c.text(478, yy + 1, pct(rs), 7.5, progress_color(rs), anchor="r")

    # ---- comparison ledger
    c.rect(486, 36, 144, 420, fill=PANEL, line=LINE)
    eq = STATS[MOCK["eq"]["P1"]]
    c.text(492, 40, "COMPARE", 7.5, DIM)
    c.rect(492, 53, 6, 6, fill=ORANGE)
    c.text(502, 51, w["name"], 9.5, CREAM)
    c.rect(492, 65, 6, 6, fill=FAINT)
    c.text(502, 63, "NOW:  " + eq["name"], 9.5, DIM)
    for i, (lab, key) in enumerate(STAT_ROWS):
        y = 82 + i * 45
        dt, dc = delta(w, eq, key)
        c.text(492, y, lab, 7.5, DIM)
        c.text(624, y - 3, dt, 12, dc, anchor="r")
        v = raw_str(w, key)
        c.text(492, y + 9, v, 12, CREAM)
        c.text(492 + c.twidth(v, 12) + 4, y + 12, unit_str(key), 7, FAINT)
        sc, se = w.get(key), eq.get(key)
        if sc is not None:
            c.bar(492, y + 26, 132, 4, sc / 100.0, dc if dc != FAINT else CREAM)
        if se is not None:
            c.bar(492, y + 32, 132, 3, se / 100.0, FAINT)
    c.rect(492, 310, 132, 1, fill=LINE)
    c.text(492, 314, "FINISH", 7, FAINT)
    swatches(c, 492, 324, 13, 16.6, 1, 13)
    c.text(492, 342, "GOLD", 7.5, ORANGE)
    c.text(492, 351, "Blued, Bloody, Desert: challenge", 7, FAINT)
    c.rect(492, 368, 132, 24, fill=ORANGE)
    c.text(558, 374, "EQUIP TO PRIMARY 1", 10.5, TRACK, anchor="m")
    c.text(492, 400, "Compared with what that slot", 7, FAINT)
    c.text(492, 409, "holds right now. Bars: top new,", 7, FAINT)
    c.text(492, 418, "bottom equipped.", 7, FAINT)
    c.text(492, 440, "Sample player: Sergeant.", 6.5, FAINT)
    footer(c, "PICK A SLOT, THEN A GUN.  THE COMPARISON ALWAYS READS AGAINST WHAT THAT SLOT HOLDS NOW.")
    return c.done()
