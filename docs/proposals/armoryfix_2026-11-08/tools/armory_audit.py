"""armory_audit.py - contact sheets of the coop Armory (ui/coop_loadout.urc) for every roster gun, on the private client (G:\\mohaa-wpnview,
DISPLAY2, through wpnview_run's launcher).

    python armory_audit.py shoot <tag> [ids...]   main menu -> Armory; per gun: its inspect page (hero) + its slot commit (PRI/SIDE/NADE tile);
                                                  then every tab's card grid. 1920x1080 frames (the hero_fit solver's frame size).
    python armory_audit.py sheet <tag>            hero sheet, slot-tile sheet and card-grid sheet from the frames

Environment: WV_MOD = the mod worktree (ui/loadout pages come from the overlay the caller set up with wpnview_run setup_fix).
"""
import io
import os
import re
import sys

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\wpnviewer_2026-11-04\tools")
import wpnview_run as W  # noqa: E402

W.RES.update({"uw": (3440, 1440, 0), "219s": (1920, 804, 0), "43s": (1440, 1080, 0)})   # the user plays 3440x1440, ui_menuCenter 0
RES = os.environ.get("AA_RES", "1080")
if RES == "uw":
    # the user's real 3440x1440: the background policy clamps a window to the test display (1920x1080); undo the clamp so the
    # framebuffer is 3440x1440 (the window overhangs DISPLAY2; screenshots read the framebuffer, not the desktop)
    _ap = W.hw.apply_policy

    def _uw(args, *a, **k):
        args2, late = _ap(args, *a, **k)
        for i, v in enumerate(args2[:-1]):
            if v == "r_customwidth":
                args2[i + 1] = "3440"
            if v == "r_customheight":
                args2[i + 1] = "1440"
        return args2, late
    W.hw.apply_policy = _uw

TSV = r"C:\mohaa-coop-dev\docs\tools\loadout_weapons.tsv"
RUNS = W.RUNS
HERO = (144, 66, 332, 128)          # gen_armory_urc.py HERO_X/Y/W/H (640x480 virtual)


def roster():
    hdr, out = None, []
    for l in io.open(TSV, encoding="utf-8"):
        if l.startswith("#") or not l.strip():
            continue
        f = l.rstrip("\r\n").split("\t")
        if hdr is None:
            hdr = f
            continue
        d = dict(zip(hdr, f))
        if d["tab"] != "" and d["id"] not in [o["id"] for o in out]:
            out.append(d)
    return out


def slot_rects():
    """the four slot-tile gun widgets (linkcvar coop_loS1..4) from the Armory urc"""
    t = io.open(os.path.join(W.MOD, "ui", "coop_loadout.urc"), encoding="latin-1").read()
    out = {}
    for m in re.finditer(r"(?s)resource\s*\n\s*Label\s*\n\s*\{(.*?)\n\}", t):
        b = m.group(1)
        lk = re.search(r'linkcvar "coop_loS([1-4])"', b)
        rc = re.search(r"(?m)^rect (\d+) (\d+) (\d+) (\d+)", b)
        if lk and rc and "rendermodel 1" in b:
            out[int(lk.group(1))] = tuple(int(v) for v in rc.groups())
    return out


def shoot(tag, ids):
    R = [d for d in roster() if not ids or d["id"] in ids]
    s = W.Script()
    s.cmd("echo ^~^~^ WV boot", 3000)
    s.cmd("pushmenu coop_loadout", 2500)
    s.cmd("screenshot a_000", 400)                  # Armory as it opens
    for d in R:
        g = d["id"]
        sl = d["slots"][0] if d["slots"] else "1"
        s.cmd("exec ui/loadout/w%s_s%s.cfg" % (g, sl), 500)
        s.cmd("exec ui/loadout/eq%s.cfg" % g, 900)
        s.cmd("screenshot a_%s" % g, 350)
    for t in range(6):
        s.cmd("set coop_loP0 %d;set coop_loP1 %d;set coop_loP2 %d" % (t == 0, t == 1, t == 2), 60)
        s.cmd("set coop_loP3 %d;set coop_loP4 %d;set coop_loP5 %d" % (t == 3, t == 4, t == 5), 60)
        s.cmd("exec ui/loadout/lktab%d.cfg" % t, 1500)
        s.cmd("screenshot a_tab%d" % t, 350)
    s.cmd("quit", 0)
    return W.launch("armory_%s" % tag, RES, s, budget=600)


def sheet(tag):
    from PIL import Image, ImageDraw
    d0 = os.path.join(RUNS, "armory_%s" % tag)
    names = {d["id"]: d["name"] for d in roster()}
    tabs = {d["id"]: d["tab"] for d in roster()}
    slots = {d["id"]: (d["slots"][0] if d["slots"] else "1") for d in roster()}
    SR = slot_rects()

    def frame(g):
        for ext in (".tga", ".jpg"):
            p = os.path.join(d0, "a_%s%s" % (g, ext))
            if os.path.isfile(p):
                return Image.open(p).convert("RGB")
        return None

    def crop(im, r, pad=0):
        W_, H_ = im.size
        x, y, w, h = r
        return im.crop((int((x - pad) * W_ / 640.0), int((y - pad) * H_ / 480.0),
                        int((x + w + pad) * W_ / 640.0), int((y + h + pad) * H_ / 480.0)))

    ids = sorted(names, key=lambda i: (tabs[i], i))
    # hero sheet
    cw, ch, cols = 400, 154 + 16, 5
    rows = (len(ids) + cols - 1) // cols
    sh = Image.new("RGB", (cw * cols, ch * rows), "black")
    dr = ImageDraw.Draw(sh)
    for k, g in enumerate(ids):
        im = frame(g)
        x, y = (k % cols) * cw, (k // cols) * ch
        dr.text((x + 3, y + 1), "%s %s" % (g, names[g]), fill="yellow")
        if im:
            sh.paste(crop(im, HERO).resize((cw - 4, ch - 18)), (x, y + 16))
    sh.save(os.path.join(RUNS, "armory_%s_hero.jpg" % tag), quality=85)
    # slot-tile sheet: the tile the gun was committed to
    cw, ch, cols = 260, 150, 8
    rows = (len(ids) + cols - 1) // cols
    sh = Image.new("RGB", (cw * cols, ch * rows), "black")
    dr = ImageDraw.Draw(sh)
    for k, g in enumerate(ids):
        im = frame(g)
        x, y = (k % cols) * cw, (k // cols) * ch
        dr.text((x + 3, y + 1), "%s s%s %s" % (g, slots[g], names[g][:22]), fill="yellow")
        r = SR.get(int(slots[g]))
        if im and r:
            sh.paste(crop(im, r, pad=2).resize((cw - 4, ch - 18)), (x, y + 16))
    sh.save(os.path.join(RUNS, "armory_%s_slots.jpg" % tag), quality=85)
    # card grids: the whole card area of each tab
    tiles = []
    for t in range(6):
        im = frame("tab%d" % t)
        if im:
            tiles.append(crop(im, (138, 270, 340, 160)).resize((850, 400)))
    if tiles:
        sh = Image.new("RGB", (1700, 400 * ((len(tiles) + 1) // 2)), "black")
        for k, im in enumerate(tiles):
            sh.paste(im, ((k % 2) * 850, (k // 2) * 400))
        sh.save(os.path.join(RUNS, "armory_%s_cards.jpg" % tag), quality=85)
    print("sheets: %s" % ", ".join(f for f in os.listdir(RUNS) if f.startswith("armory_%s_" % tag)))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "shoot":
        shoot(a[1], a[2:])
    else:
        sheet(a[1])
