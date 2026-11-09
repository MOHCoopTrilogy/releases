"""make_mock.py - MOCKUP ONLY for Live Operations on the NEW GAME war map (PLAN.md).  Not shipped, not wired to anything.

    python -P -E make_mock.py <ne_dir> <outdir>
        ne_dir = docs/proposals/loadscreens_2026-10-18/data/ne (Natural Earth, git-ignored; read as data only)

User 2026-11-09: "Instead of it on a board have the locations pop up on the existing map where you pick a mission for single
player."  So this draws the EXISTING NEW GAME wall view (sp3camp_2026-11-08/warmap.py wall_view(): the same window, projection,
twelve campaign pins, dashed leaders, paper tags, legend and the VANILLA | CHRONOLOGICAL toggle) and adds the contract layer:
a red grease-pencil loop + a draining timer ring + a TDM / OBJ rubber stamp at each live contract, a dashed area loop for a
censored ("Somewhere in ...") location, an edge marker for Stalingrad (east of the wall's window), one hover slip and one open
dispatch card with DEPLOY.

Every contract pin comes from ops_locations.json (the evidence table).  The stamp of each contract is placed by a layout pass that
tries 8 directions and refuses any spot over a campaign pin, tag, printed name, the toggle, the legend or another contract - the
same hit-box rules as warmap.qa(); the run prints the verdict for ALL 35 locations, not just the five drawn.

Writes:  mock_newgame.png (2048x1536, the wall view as NEW GAME shows it)
         mock_card.png    (the dispatch card at 2x, for type review)
The campaign tags are drawn here as plain paper slips in campaign colour (the real ones are make_ng3campaigns.py textures); the
contract values are hand-picked examples of a roll, not a real roll.
"""
import json, math, os, random, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "sp3camp_2026-11-08"))
import warmap  # noqa: E402

FD = r"C:\Windows\Fonts"
TYPE = "PrestigeEliteStd-Bd.otf"     # the typed body
HEAD = "courbd.ttf"
GREASE = (168, 24, 20)               # red grease pencil
CARBON = (40, 30, 24)                # typewriter ribbon
LOC = {m["map"]: m for m in json.load(open(os.path.join(HERE, "ops_locations.json"), encoding="utf-8"))["maps"]}

# the example roll drawn in the mock: map, mode, bots, fraction of life left, life in minutes, modifier
LIVE = [("dm/mohdm3", "TDM", 11, 0.62, 4, "STORM"),
        ("obj/mp_bologna_obj", "OBJ", 9, 0.18, 4, ""),
        ("obj/obj_team3", "OBJ", 11, 0.85, 5, ""),
        ("dm/mp_malta_dm", "TDM", 7, 0.45, 4, "HARDCORE"),
        ("dm/mp_verschneit_dm", "TDM", 9, 0.95, 5, ""),
        ("dm/mohdm6", "TDM", 15, 0.30, 3, "LOW AMMO")]
OPEN, HOVER = "dm/mohdm3", "dm/mp_malta_dm"
TAG_NUDGE = {"bt3": (45.9, 12.6), "bt2": (36.0, 18.9), "bt1": (38.7, 8.9)}   # was (43.65,12.6) (36.0,17.9) (34.2,9.4)


def F(name, px):
    return ImageFont.truetype(os.path.join(FD, name), max(8, int(px)))


def grease_circle(d, cx, cy, r, rng, width, col=GREASE, loops=1.15):
    """a hand-drawn grease-pencil loop: slightly elliptical, wobbling radius, overshoots its start, two passes."""
    for p in range(2):
        a0 = rng.uniform(0, 2 * math.pi)
        ex, ey = rng.uniform(0.92, 1.08), rng.uniform(0.88, 1.0)
        tilt = rng.uniform(-0.4, 0.4)
        ph = [rng.uniform(0, 6.28) for _ in range(3)]
        pts = []
        for i in range(91):
            t = a0 + loops * 2 * math.pi * i / 90
            rr = r * (1 + 0.035 * math.sin(3 * t + ph[0]) + 0.02 * math.sin(5 * t + ph[1]) + 0.03 * (i / 90) + p * 0.04)
            x, y = rr * ex * math.cos(t), rr * ey * math.sin(t)
            x, y = x * math.cos(tilt) - y * math.sin(tilt), x * math.sin(tilt) + y * math.cos(tilt)
            pts.append((cx + x, cy + y))
        d.line(pts, fill=col + ((235 if p == 0 else 160),), width=width if p == 0 else max(1, int(width * 0.6)), joint="curve")


def dashed_loop(d, cx, cy, r, w):
    for a in range(0, 360, 16):
        d.arc((cx - r, cy - r, cx + r, cy + r), a, a + 9, fill=GREASE + (215,), width=w)


def timer_ring(d, cx, cy, r, frac, w):
    """time left as an inked arc clockwise from 12 o'clock; the spent part is a faint pencil track; red in the last quarter."""
    box = (cx - r, cy - r, cx + r, cy + r)
    d.arc(box, 0, 360, fill=(90, 70, 50, 80), width=max(1, w // 3))
    if frac > 0:
        d.arc(box, -90, -90 + 360 * frac, fill=(150, 18, 14, 245) if frac < 0.25 else (36, 28, 22, 235), width=w)


def stamp_img(text, s, col=(150, 20, 18), rot=0, seed=7, px=34):
    f = F(HEAD, px * s)
    tw = ImageDraw.Draw(Image.new("RGBA", (4, 4))).textlength(text, font=f)
    W_, H_ = int(tw + 30 * s), int(px * 1.62 * s)
    st = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    sd = ImageDraw.Draw(st)
    sd.rounded_rectangle((3 * s, 3 * s, W_ - 3 * s, H_ - 3 * s), radius=6 * s, outline=col + (235,), width=max(2, int(4 * s)))
    sd.text((15 * s, (H_ - px * s) / 2 - 3 * s), text, font=f, fill=col + (235,))
    rng = random.Random(seed)          # worn rubber: knock specks out of the ink
    a = st.getchannel("A").load()
    for _ in range(int(W_ * H_ * 0.05)):
        x, y = rng.randrange(W_), rng.randrange(H_)
        a[x, y] = int(a[x, y] * 0.3)
    return st.rotate(rot, resample=Image.BICUBIC, expand=True)


def slip(lines, s, rng, rot):
    """a small typed paper slip (the hover caption)."""
    f1, f2 = F(TYPE, 30 * s), F(TYPE, 25 * s)
    dd = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    tw = max(dd.textlength(l, font=f1 if i == 0 else f2) for i, l in enumerate(lines))
    W_, H_ = int(tw + 36 * s), int(22 * s + 36 * s + 31 * s * (len(lines) - 1))
    im = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(0, 0), (W_, 0)] + [(W_ - rng.uniform(0, 5 * s), H_ * t / 6) for t in range(1, 6)] + [(W_, H_), (0, H_)],
              fill=(240, 231, 208, 248), outline=(120, 100, 76, 220))
    y = 11 * s
    for i, l in enumerate(lines):
        red = l.startswith("EXPIRES")
        d.text((18 * s, y), l, font=f1 if i == 0 else f2, fill=((130, 18, 14, 255) if red else CARBON + (255,)))
        y += 36 * s if i == 0 else 31 * s
    return im.rotate(rot, resample=Image.BICUBIC, expand=True)


def shadowed(base, im, x, y, s, blur=4, op=0.35):
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.getchannel("A").point(lambda a: int(a * op)))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur * s)), (int(x + 4 * s), int(y + 5 * s)))
    base.alpha_composite(im, (int(x), int(y)))


def card(s=1.0):
    """the opened dispatch card (typed on a ruled index card), RGBA."""
    W, H = int(470 * s), int(560 * s)
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rectangle((0, 0, W - 1, H - 1), fill=(240, 232, 212, 255), outline=(150, 128, 100, 255), width=max(1, int(2 * s)))
    for yy in range(int(144 * s), H - int(20 * s), int(26 * s)):
        d.line((14 * s, yy, W - 14 * s, yy), fill=(150, 170, 196, 110), width=max(1, int(1 * s)))
    d.line((14 * s, 112 * s, W - 14 * s, 112 * s), fill=(190, 70, 70, 170), width=max(1, int(2 * s)))
    fh, fb, fs = F(HEAD, 20 * s), F(TYPE, 17 * s), F(TYPE, 13 * s)
    d.text((18 * s, 14 * s), "FIELD OPERATIONS  -  DISPATCH", font=fh, fill=CARBON + (255,))
    d.text((18 * s, 40 * s), "No. 0417        PRIORITY: ROUTINE", font=fs, fill=CARBON + (230,))
    d.text((18 * s, 64 * s), "OPERATION IRON KETTLE", font=F(HEAD, 26 * s), fill=CARBON + (255,))
    rows = [("LOCATION", "Remagen, Germany"), ("", "Ludendorff Bridge"), ("MAP", "Remagen (dm/mohdm3)"),
            ("MODE", "TEAM MATCH  (TDM)"), ("FORCES", "You + 5 riflemen"), ("", "vs 6 Axis   (11 bots)"),
            ("BOTS", "VETERAN"), ("MODIFIER", "STORM  (rain, thunder)"), ("LIMIT", "10 min or 40 kills"),
            ("REWARD", "+150 XP, Service Record"), ("EXPIRES", "2 min 28 sec")]
    y = 122 * s
    for k, v in rows:
        if k:
            d.text((20 * s, y), k + ":", font=fs, fill=(90, 70, 54, 255))
        d.text((140 * s, y - 2 * s), v, font=fb, fill=(120, 18, 14, 255) if k == "EXPIRES" else CARBON + (255,))
        y += 26 * s
    d.line((140 * s, 324 * s, 360 * s, 326 * s), fill=GREASE + (200,), width=max(1, int(3 * s)))
    c.alpha_composite(stamp_img("DEPLOY", s, rot=4), (int(30 * s), int(H - 96 * s)))
    c.alpha_composite(stamp_img("FILE AWAY", s * 0.62, col=(60, 60, 70), rot=-3, seed=3), (int(270 * s), int(H - 84 * s)))
    d.rounded_rectangle((W - 64 * s, -14 * s, W - 40 * s, 52 * s), radius=10 * s, outline=(120, 124, 130, 255), width=max(1, int(3 * s)))
    d.rounded_rectangle((W - 58 * s, -6 * s, W - 46 * s, 36 * s), radius=6 * s, outline=(150, 154, 160, 255), width=max(1, int(2 * s)))
    return c


def main(ne, out):
    os.makedirs(out, exist_ok=True)
    rng = random.Random(11)
    # PROPOSED tag nudges (PLAN.md 1): three Breakthrough tags sit on the Italian / Tunisian / Maltese contract locations.
    # Found by a search that keeps warmap.qa() clean and clears every contract loop; pins and leaders follow automatically.
    for i, m in enumerate(warmap.MISSIONS):
        if m[0] in TAG_NUDGE:
            warmap.MISSIONS[i] = m[:5] + (TAG_NUDGE[m[0]],)
    v = warmap.wall_view(W=2400)
    s = v.s
    base, info = warmap.render(ne, v, names=True, pins=True, grid=True, ss=2)
    im = base.convert("RGBA")
    im.alpha_composite(warmap.overlay(v, (v.W, v.H)))              # NEW GAME's dashed leaders + campaign legend
    d = ImageDraw.Draw(im, "RGBA")

    # --- the existing NEW GAME furniture, stand-ins at their real places: campaign tags + the order toggle. On their own layer,
    #     composited ABOVE the contract loops/rings and BELOW the stamps/slips/card (the in-game draw order: map, contract rings,
    #     campaign tags, contract stamps, hover slip, card), so a ring that runs under a tag never hides the tag's lettering ---
    furn = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(furn, "RGBA")
    tags = {}
    ft = F("timesbd.ttf", 54 * s)
    for k, c, n, name, pin, tc in warmap.MISSIONS:
        r = warmap.tag_rect(v, *tc, *warmap.TAG_M)
        tags[k] = r
        d.rectangle(r, fill=warmap.COL[c] + (250,), outline=(90, 70, 44, 255), width=max(2, int(5 * s)))
        lbl = "%d. %s" % (n, name)
        f = ft
        while d.textlength(lbl, font=f) > (r[2] - r[0]) * 0.9:
            f = F("timesbd.ttf", f.size - 2)
        d.text(((r[0] + r[2]) / 2 - d.textlength(lbl, font=f) / 2, (r[1] + r[3]) / 2 - f.size * 0.6), lbl, font=f, fill=warmap.INK + (255,))
    tg = warmap.tag_rect(v, *warmap.TOGGLE["c"], warmap.TOGGLE["w"], warmap.TOGGLE["h"])
    d.rectangle(tg, fill=(226, 208, 152, 245), outline=(90, 70, 44, 255), width=max(2, int(5 * s)))
    tl = "VANILLA  |  CHRONOLOGICAL"
    f = F("timesbd.ttf", 50 * s)
    d.text(((tg[0] + tg[2]) / 2 - d.textlength(tl, font=f) / 2, (tg[1] + tg[3]) / 2 - 30 * s), tl, font=f, fill=warmap.INK + (255,))
    lb = warmap.legend_box(v)
    d = ImageDraw.Draw(im, "RGBA")

    # --- the layout pass: every one of the 35 contract locations gets a stamp spot that collides with nothing ---
    R_LOOP, R_RING = 64 * s, 42 * s
    blockers = [("tag " + k, r) for k, r in tags.items()] + [("name " + n, r) for n, r in info["labels"]]
    blockers += [("pin " + k, (x - 20 * s, y - 20 * s, x + 20 * s, y + 20 * s)) for k, (x, y) in info["pins"].items()]
    blockers += [("toggle", tg), ("legend", lb)]
    sheet = (60 * s, 60 * s, v.W - 60 * s, v.H - 60 * s)
    dirs = [(1, -1), (1, 1), (-1, -1), (-1, 1), (1, 0), (-1, 0), (0, -1), (0, 1)]
    placed, report = {}, []
    for mp, L in LOC.items():
        x, y = v.P(*L["pin"])
        if not (0 < x < v.W and 0 < y < v.H):
            report.append((mp, "off the wall -> edge marker"))
            continue
        rr = 64 * s * (1.55 if L.get("area") else 1)
        under = [k for k, r in tags.items() if warmap.hit((x - rr, y - rr, x + rr, y + rr), r)]
        if under:
            report.append((mp, "LOOP UNDER TAG " + ",".join(under)))
        sw, sh_ = 150 * s, 62 * s                         # the TDM/OBJ stamp's box
        ok = None
        for k_, (dx, dy) in [(k_, dd) for k_ in (1.0, 1.8) for dd in dirs]:     # near ring first, then a wider one
            cx = x + dx * k_ * (R_LOOP + sw / 2 + 6 * s) if dx else x
            cy = y + dy * k_ * (R_LOOP * 0.7 + sh_ / 2) if dy else y
            box = (cx - sw / 2, cy - sh_ / 2, cx + sw / 2, cy + sh_ / 2)
            if not (sheet[0] < box[0] and box[2] < sheet[2] and sheet[1] < box[1] and box[3] < sheet[3]):
                continue
            if any(warmap.hit(box, r, 6 * s) for _, r in blockers):
                continue
            ok = box
            break
        placed[mp] = ok
        report.append((mp, "stamp ok" if ok else "NO CLEAR STAMP SPOT"))
    bad = [r for r in report if r[1].startswith(("NO", "LOOP"))]
    print("layout: %d locations, %d off-wall, %d problems (no stamp spot / loop under a campaign tag)" % (len(LOC), sum(1 for r in report if "edge" in r[1]), len(bad)))
    for r in bad:
        print("   ", r)

    # --- the live contracts: loops + rings first, then the campaign tags over them, then the stamps ---
    stamps = []
    for mp, mode, bots, frac, life, mod in LIVE:
        L = LOC[mp]
        x, y = v.P(*L["pin"])
        if not (0 < x < v.W and 0 < y < v.H):          # Stalingrad: an edge tab at its latitude, arrow pointing east
            ey = v.P(L["pin"][0], v.lon1)[1]
            tab = slip(["STALINGRAD  >>", "TDM   %d BOTS" % bots, "EXPIRES %d:%02d" % divmod(int(frac * life * 60), 60)], s * 1.5, rng, 0)
            tx = v.W - tab.size[0] - 110 * s
            shadowed(im, tab, tx, ey - tab.size[1] / 2, s)
            d = ImageDraw.Draw(im, "RGBA")
            grease_circle(d, tx + tab.size[0] / 2, ey, tab.size[0] * 0.56, rng, max(3, int(7 * s)), loops=1.05)
            continue
        if L.get("area"):
            dashed_loop(d, x, y, R_LOOP * 1.55, max(3, int(7 * s)))
        else:
            grease_circle(d, x, y, R_LOOP, rng, max(3, int(8 * s)))
        timer_ring(d, x, y, R_RING, frac, max(4, int(11 * s)))
        if L.get("area"):                                  # an area has no campaign pin under it: give it its own small tack
            d.ellipse((x - 14 * s, y - 14 * s, x + 14 * s, y + 14 * s), fill=(28, 24, 22, 255))
        stamps.append((mp, mode))
    im.alpha_composite(furn)
    for mp, mode in stamps:
        box = placed[mp]
        st = stamp_img(mode, s * 1.25, rot=rng.uniform(-6, 6), seed=sum(map(ord, mp)) & 255)
        im.alpha_composite(st, (int((box[0] + box[2]) / 2 - st.size[0] / 2), int((box[1] + box[3]) / 2 - st.size[1] / 2)))
    d = ImageDraw.Draw(im, "RGBA")

    # --- hover slip on Malta ---
    L = LOC[HOVER]
    x, y = v.P(*L["pin"])
    hs = slip(["VALLETTA, MALTA", "TEAM MATCH   7 BOTS", "HARDCORE", "EXPIRES 1:48"], s * 1.5, rng, -2)
    shadowed(im, hs, x + 110 * s, y - hs.size[1] - 165 * s, s)

    # --- the open card, pinned over the empty north-east (Russia), leader to its pin ---
    cd = card(s * 2.0).rotate(-1.5, resample=Image.BICUBIC, expand=True)
    cx0, cy0 = v.W - cd.size[0] - 130 * s, 330 * s
    shadowed(im, cd, cx0, cy0, s, blur=12, op=0.5)
    d = ImageDraw.Draw(im, "RGBA")
    rx, ry = v.P(*LOC[OPEN]["pin"])
    sx, sy = cx0 + 8 * s, cy0 + 200 * s
    pts = []
    for i in range(41):
        t = i / 40
        mx, my = (sx + rx) / 2, min(sy, ry) - 160 * s
        pts.append(((1 - t) ** 2 * sx + 2 * (1 - t) * t * mx + t * t * (rx + 70 * s), (1 - t) ** 2 * sy + 2 * (1 - t) * t * my + t * t * (ry - 60 * s)))
    d.line(pts, fill=GREASE + (215,), width=max(3, int(8 * s)), joint="curve")
    ax, ay = pts[-1]
    d.polygon([(ax - 10 * s, ay + 12 * s), (ax + 22 * s, ay - 2 * s), (ax + 4 * s, ay - 22 * s)], fill=GREASE + (225,))

    im.convert("RGB").resize((2048, 1536), Image.LANCZOS).save(os.path.join(out, "mock_newgame.png"))
    c2 = card(2.0)
    big = Image.new("RGBA", (c2.size[0] + 80, c2.size[1] + 80), (58, 40, 24, 255))
    big.alpha_composite(c2, (40, 40))
    big.convert("RGB").save(os.path.join(out, "mock_card.png"))
    json.dump([{"map": m, "verdict": r} for m, r in report], open(os.path.join(out, "layout_report.json"), "w"), indent=1)
    print("ok")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
