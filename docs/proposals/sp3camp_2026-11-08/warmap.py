"""warmap.py - THE shared war map (user 2026-11-08: "We will need the maps to match across the main menu and all other menus where it
appears").  One projection, palette, typography and paper; every view is a render of the same lat/long data.

    python -P -E warmap.py all <ne_dir> <outdir>          every menu view (below) + the marker json
    python -P -E warmap.py box <ne_dir> <out.png> LAT0 LAT1 LON_CENTRE PHYS_ASPECT OUT_W OUT_H [--pins] [--frame]
                                                          any lat/long box at any size (e.g. a loading screen pushing in)

Data: Natural Earth 1:10m coastline + admin_0_countries (public domain), the copy the loading-screen maps use
(docs/proposals/loadscreens_2026-10-18/data/ne, git-ignored).  Look: those field maps (loadscreens_2026-10-18/tools/mapintro.py).
No modern borders are drawn.  Run with -P -E (the data folder is untrusted input; no code is ever loaded from it).

Projection: equirectangular scaled for TRUE proportions on the physical surface (lon span = lat span x surface aspect / cos(mid lat)),
so meridians and parallels are straight, evenly spaced lines and the graticule IS the projection's grid (towns, pins and the coast are
projected by the same function P).  Every view is rendered at square pixels for its physical size, then resized to its texture size,
so a texture stretched onto a non-square surface (the attic wall map: 4096x3072 on 3.149 x 2.705 m) shows undistorted land and type.

Views written by `all` (outdir):
  wallmap_ne.png        4096x3072  the attic wall map (atc_wallmap1, UV 0..1 = 3.149 x 2.705 m) - for newgame/ng_bake.py.  Base map +
                                   the twelve mission pins.  Shared by the attic home view, NEW GAME, the difficulty screens, Records,
                                   Medals and the Armory view (they all show atc_wallmap1).
  ng_overlay.png        2048x1536  RGBA, NEW GAME only: the dashed leaders pin -> tag and the campaign legend (tags are scene labels)
  flat_main.png /       1024x832   the flat main menu's map (main.urc map_bg rect, 305x248): the same map framed as a board, and the lit
  flat_main_h.png                  hover variant
  flat_room.png         1024x672   the map on the stock briefing room's board (hzm_ngroom.inc), lit by the room's lamp
  allmap_markers.json              wall uv of every pin and tag, the toggle box, the printed-name boxes (make_ng3campaigns.py)
  wallmap_ne_markers.json          the same in make_newgame3d.py's schema (tunisia/sicily/italy + all twelve) for its BT tag pass
QA (wall view, asserted): pins on the sheet; no tag over a pin, a tag, a printed name, the toggle or the legend; no printed name over a
pin; no two names overlapping; every name at least 100 px inside the sheet."""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ne_shp  # noqa: E402

FD = r"C:\Windows\Fonts"
WALL_M = (3.149, 2.705)                 # the attic wallmap quad, metres
TAG_M = (0.38, 0.13)                    # a NEW GAME tag on the wall (make_ng3campaigns.py reads it from the json)
# [attic70] widened east to take in Stalingrad (EA's THEIR DYING BREATH, Gorodishche 48.8N 44.5E - its pin sat clamped on the
# right edge of the old 33..65N / lon_c 12 window, which ended at 40.4E). The sheet's aspect is the wall's, so the extra width comes
# from a taller latitude span: 31.5..67.5N, centred 15.9E -> about 16.4W..48.1E (the west edge where it was).
WALL_WIN = dict(lat=(31.5, 67.5), lon_c=15.85)

# the missions, their campaigns and colours: missions.json (THE table; one row adds a mission everywhere)
_MJ = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "missions.json")))
MISSIONS = [(m["key"], m["camp"], m["n"], m["name"], tuple(m["pin"]), tuple(m["tag"])) for m in _MJ["missions"]]
OPTIONAL = {m["key"]: m.get("optional_cvar") for m in _MJ["missions"]}
TOGGLE = dict(c=(63.35, -9.8), w=0.56, h=0.085)          # NEW GAME's VANILLA | CHRONOLOGICAL tabs (scene labels) - kept clear
TOWNS = [("LONDON", 51.507, -0.128, "r"), ("PARIS", 48.857, 2.352, "r"), ("ROME", 41.903, 12.496, "l"), ("MADRID", 40.417, -3.704, "r"),
         ("ALGIERS", 36.754, 3.059, "b"), ("OSLO", 59.914, 10.752, "l"), ("STOCKHOLM", 59.329, 18.069, "r"), ("WARSAW", 52.230, 21.012, "r"),
         ("VIENNA", 48.208, 16.373, "r"), ("TUNIS", 36.806, 10.181, "r"), ("NAPLES", 40.852, 14.268, "r"), ("AMSTERDAM", 52.370, 4.895, "r"),
         ("HAMBURG", 53.551, 9.993, "r"), ("MUNICH", 48.137, 11.576, "r"),
         ("MOSCOW", 55.756, 37.617, "r"), ("KIEV", 50.450, 30.523, "r")]          # [attic70] the widened east
REGIONS = [("ATLANTIC|OCEAN", 38.2, -12.6, -46), ("NORTH  SEA", 56.6, 3.4, 64), ("MEDITERRANEAN SEA", 33.6, 20.6, -64),
           ("BALTIC SEA", 55.4, 17.8, -50), ("FRANCE", 45.4, 1.8, 76), ("SPAIN", 39.0, -4.2, 76), ("GERMANY", 50.9, 10.6, -76),
           ("NORWAY", 61.2, 8.6, 64), ("SWEDEN", 63.3, 16.3, 64), ("ITALY", 40.0, 16.4, 56), ("ENGLAND", 52.6, -1.6, 52),
           ("U. S. S. R.", 54.2, 31.0, -76), ("BLACK SEA", 43.3, 34.4, 56)]
COL = {c["key"]: tuple(c["colour"]) for c in _MJ["campaigns"]}
# [byo69] an OPTIONAL mission (optional_cvar: converted on the player's PC from their own disc) is never baked into the shared
# images - no pin, no leader, no legend row - because a baked pin cannot be hidden when the pak is absent. make_ng3campaigns.py
# draws its pin and tag as scene labels gated on the cvar instead. Its pin may lie east of the sheet (Stalingrad): the markers
# json then carries it clamped to the sheet edge ("pin_offsheet": true).
LEGEND = [(c["key"], c["name"]) for c in _MJ["campaigns"]
          if any(m["camp"] == c["key"] and not m.get("optional_cvar") for m in _MJ["missions"])]
INK = (58, 44, 30)


def font(name, px):
    return ImageFont.truetype(os.path.join(FD, name), max(8, int(px)))


_DATA = {}


def load(ne):
    if not _DATA:
        def shp(layer):
            for root, _d, fs in os.walk(ne):
                for f in fs:
                    if f.lower() == layer + ".shp":
                        return ne_shp.read(os.path.join(root, f), bbox=(-40, 20, 70, 75))
            raise SystemExit("missing " + layer)
        _DATA["land"] = shp("ne_10m_admin_0_countries")
        _DATA["coast"] = shp("ne_10m_coastline")
        for root, _d, fs in os.walk(ne):
            for f in fs:
                if f.lower() == "ne_10m_rivers_lake_centerlines.shp":
                    _DATA["rivers"] = ne_shp.read_with_attrs(os.path.join(root, f), bbox=(-40, 20, 70, 75))
        _DATA.setdefault("rivers", [])
    return _DATA


class View:
    """lat0..lat1, centred on lon_c, for a physical surface of aspect `aspect` (w/h), rendered at square pixels W x Hs."""

    def __init__(self, lat0, lat1, lon_c, aspect, W):
        self.lat0, self.lat1 = lat0, lat1
        span = (lat1 - lat0) * aspect / math.cos(math.radians((lat0 + lat1) / 2))
        self.lon0, self.lon1 = lon_c - span / 2, lon_c + span / 2
        self.W, self.H = int(W), int(round(W / aspect))
        self.s = W / 4096.0                       # type and line sizes are set for the 4096-wide wall view

    def P(self, lat, lon):
        return ((lon - self.lon0) / (self.lon1 - self.lon0) * self.W, (self.lat1 - lat) / (self.lat1 - self.lat0) * self.H)

    def uv(self, x, y):
        return [x / self.W, 1 - y / self.H]


def paper(W, H, seed=3):
    from scipy.ndimage import gaussian_filter
    rng = np.random.default_rng(seed)
    k = W / 4096.0
    pap = np.zeros((H, W, 3), np.float32)
    pap[:] = (222, 205, 166)
    n1 = gaussian_filter(rng.normal(0, 1, (H, W)).astype(np.float32), 50 * k) * 70
    n2 = gaussian_filter(rng.normal(0, 1, (H, W)).astype(np.float32), max(1, 4 * k)) * 7
    fib = gaussian_filter(rng.normal(0, 1, (H, W)).astype(np.float32), (max(0.6, 1.2 * k), 10 * k)) * 22
    pap += (n1 + n2 + fib)[..., None] * np.array([1.0, 0.95, 0.8], np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rr = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    pap *= (1 - 0.32 * np.clip(rr - 0.55, 0, 1) ** 1.4)[..., None]
    return Image.fromarray(np.clip(pap, 0, 255).astype(np.uint8)).convert("RGBA")


def hit(a, b, m=0):
    return a[0] - m < b[2] and a[2] + m > b[0] and a[1] - m < b[3] and a[3] + m > b[1]


def render(ne, v, names=True, pins=True, grid=True, ss=3):
    """the base map for view v, vector-drawn at ss x supersampling and Lanczos-downsampled (no jaggies, line weights hold at every
    mip); returns (RGBA image at v.W x v.H, info: label boxes and pins in v's pixels)."""
    vv = v
    v = View(vv.lat0, vv.lat1, (vv.lon0 + vv.lon1) / 2, vv.W / vv.H, vv.W * ss)
    v.H = vv.H * ss
    im, info = _render(ne, v, paper(vv.W, vv.H).resize((v.W, v.H), Image.BICUBIC), names, pins, grid)
    im = im.resize((vv.W, vv.H), Image.LANCZOS)
    k = 1.0 / ss
    info["labels"] = [(n, tuple(c * k for c in r)) for n, r in info["labels"]]
    info["pins"] = {kk: (x * k, y * k) for kk, (x, y) in info["pins"].items()}
    return im, info


def _render(ne, v, im, names, pins, grid):
    D = load(ne)
    s = v.s
    landm = Image.new("L", (v.W, v.H), 0)
    ld = ImageDraw.Draw(landm)
    for shape in D["land"]:                      # land = the union of the country polygons; no borders drawn
        for part in shape:
            if len(part) > 2:
                ld.polygon([v.P(la, lo) for lo, la in part], fill=255)
    im.alpha_composite(Image.composite(Image.new("RGBA", (v.W, v.H), (210, 192, 140, 255)), Image.new("RGBA", (v.W, v.H), (150, 166, 160, 125)), landm))
    d = ImageDraw.Draw(im, "RGBA")
    for shape in D["coast"]:
        for part in shape:
            if len(part) > 1:
                d.line([v.P(la, lo) for lo, la in part], fill=INK + (235,), width=max(2, int(round(6 * s))), joint="curve")
    for sh, row in D["rivers"]:                  # the major rivers (Natural Earth scalerank <= 6), thin blue-grey ink
        try:
            rk = int(row.get("scalerank", "9") or 9)
        except ValueError:
            rk = 9
        if rk > 6:
            continue
        for part in sh:
            if len(part) > 1:
                d.line([v.P(la, lo) for lo, la in part], fill=(70, 92, 104, 175), width=max(1, int(round((5.0 - 0.45 * rk) * s))), joint="curve")
    info = {"labels": [], "pins": {}}
    # the graticule and the lettering go on their own layers: every name's box (plus its halo) is cut out of the grid layer, so no
    # meridian or parallel ever crosses lettering (a masked map name, as on the printed field maps)
    gl = Image.new("RGBA", (v.W, v.H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gl)
    tl = Image.new("RGBA", (v.W, v.H), (0, 0, 0, 0))
    td = ImageDraw.Draw(tl)
    if grid:                                     # the projection's own meridians / parallels, labelled ON their line at each edge
        fg = font("cour.ttf", 46 * s)
        for lo in range(-40, 75, 5):
            x, _ = v.P(v.lat0, lo)
            if 30 * s < x < v.W - 30 * s:
                gd.line([(x, 0), (x, v.H)], fill=(150, 70, 50, 110), width=max(1, int(3 * s)))
        for la in range(20, 75, 5):
            _, y = v.P(la, v.lon0)
            if 30 * s < y < v.H - 30 * s:
                gd.line([(0, y), (v.W, y)], fill=(150, 70, 50, 110), width=max(1, int(3 * s)))
    knock = []
    if names:
        er = np.asarray(landm.filter(ImageFilter.MinFilter(max(3, int(9 * s) | 1)))) > 0
        ft = font("courbd.ttf", 64 * s)
        for n, la, lo, side in TOWNS:
            x, y = v.P(la, lo)
            if not (0 < x < v.W and 0 < y < v.H):
                continue
            if not er[int(y), int(x)]:            # a coastal town's dot onto the land
                rr_ = int(120 * s)
                x0, y0 = max(0, int(x) - rr_), max(0, int(y) - rr_)
                ys, xs = np.nonzero(er[y0:int(y) + rr_, x0:int(x) + rr_])
                if len(xs):
                    k_ = np.argmin((xs + x0 - x) ** 2 + (ys + y0 - y) ** 2)
                    x, y = float(x0 + xs[k_]), float(y0 + ys[k_])
            tw = td.textlength(n, font=ft)
            tx, ty = {"l": (x - 20 * s - tw, y - 26 * s), "b": (x - tw / 2, y + 14 * s), "r": (x + 20 * s, y - 26 * s)}[side]
            td.ellipse([x - 12 * s, y - 12 * s, x + 12 * s, y + 12 * s], fill=INK + (255,))
            td.text((tx, ty), n, font=ft, fill=INK + (235,), stroke_width=max(1, int(7 * s)), stroke_fill=(220, 204, 160, 235))    # paper halo
            box = (min(tx, x - 12 * s), ty, max(tx + tw, x + 12 * s), ty + 56 * s)
            info["labels"].append((n, box))
            knock.append(td.textbbox((tx, ty), n, font=ft, stroke_width=max(1, int(7 * s))))
            knock.append((x - 16 * s, y - 16 * s, x + 16 * s, y + 16 * s))
        for n, la, lo, px_ in REGIONS:
            x, y = v.P(la, lo)
            sea = "SEA" in n or "OCEAN" in n
            f = font("timesi.ttf" if sea else "timesbd.ttf", abs(px_) * 1.25 * s)
            hpx = abs(px_) * 1.25 * s
            halo = (174, 186, 176, 200) if sea else (214, 196, 148, 215)
            lines_ = n.split("|")                     # "|" stacks a name on lines (ATLANTIC / OCEAN fits the open sea west of Iberia)
            y0 = y - hpx / 2 - (len(lines_) - 1) * hpx * 0.55
            box = None
            for li, ln_ in enumerate(lines_):
                sp = " ".join(ln_) if px_ > 0 else ln_
                tw = td.textlength(sp, font=f)
                ly = y0 + li * hpx * 1.1
                td.text((x - tw / 2, ly), sp, font=f, fill=(60, 78, 84, 225) if sea else (70, 50, 36, 215), stroke_width=max(1, int(6 * s)), stroke_fill=halo)
                b_ = (x - tw / 2, ly, x + tw / 2, ly + hpx * 1.2)
                box = b_ if box is None else (min(box[0], b_[0]), box[1], max(box[2], b_[2]), b_[3])
                knock.append(td.textbbox((x - tw / 2, ly), sp, font=f, stroke_width=max(1, int(6 * s))))
            info["labels"].append((n.replace("|", " "), box))
    pad = 10 * s
    for kb in knock:
        gd.rectangle((kb[0] - pad, kb[1] - pad, kb[2] + pad, kb[3] + pad), fill=(0, 0, 0, 0))
    if grid:                                     # the edge degree labels sit ON their line, over a paper patch (after the knock-out)
        for lo in range(-40, 75, 5):
            x, _ = v.P(v.lat0, lo)
            if 30 * s < x < v.W - 30 * s:
                t = "%d\u00b0%s" % (abs(lo), "W" if lo < 0 else ("E" if lo else ""))
                tw = gd.textlength(t, font=fg)
                for ty in (8 * s, v.H - 56 * s):
                    gd.rectangle((x - tw / 2 - 6 * s, ty - 2 * s, x + tw / 2 + 6 * s, ty + 48 * s), fill=(222, 205, 166, 220))
                    gd.text((x - tw / 2, ty), t, font=fg, fill=(120, 60, 44, 230))
        for la in range(20, 75, 5):
            _, y = v.P(la, v.lon0)
            if 30 * s < y < v.H - 30 * s:
                t = "%d\u00b0N" % la
                tw = gd.textlength(t, font=fg)
                for tx in (8 * s, v.W - tw - 8 * s):
                    gd.rectangle((tx - 6 * s, y - 26 * s, tx + tw + 6 * s, y + 24 * s), fill=(222, 205, 166, 220))
                    gd.text((tx, y - 24 * s), t, font=fg, fill=(120, 60, 44, 230))
    im.alpha_composite(gl)
    im.alpha_composite(tl)
    d = ImageDraw.Draw(im, "RGBA")
    if pins:
        for k, _c, _n, _t, pin, _tc in MISSIONS:
            if OPTIONAL[k]:
                continue
            px, py = v.P(*pin)
            r = 17 * s
            d.ellipse([px - r, py - r, px + r, py + r], fill=(176, 28, 24, 250), outline=(70, 14, 10, 255), width=max(1, int(5 * s)))
            info["pins"][k] = (px, py)
    return im, info


def tag_rect(v, lat, lon, wm, hm):
    x, y = v.P(lat, lon)
    hw, hh = wm / WALL_M[0] * v.W / 2, hm / WALL_M[1] * v.H / 2
    return (x - hw, y - hh, x + hw, y + hh)


def legend_box(v):
    s = v.s
    return (v.W - 980 * s, v.H - 400 * s, v.W - 120 * s, v.H - 130 * s)


def overlay(v, out_size):
    """NEW GAME only: dashed leaders pin -> the nearest point of its tag, and the campaign legend (transparent elsewhere)."""
    s = v.s
    im = Image.new("RGBA", (v.W, v.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k, _c, _n, _t, pin, tc in MISSIONS:
        if OPTIONAL[k]:
            continue
        px, py = v.P(*pin)
        r = tag_rect(v, *tc, *TAG_M)
        qx, qy = min(max(px, r[0]), r[2]), min(max(py, r[1]), r[3])
        L = math.hypot(qx - px, qy - py)
        if L > 30 * s:
            steps = int(L / (30 * s))
            for i in range(0, steps, 2):
                a, b = i / steps, min(1, (i + 1) / steps)
                d.line([(px + (qx - px) * a, py + (qy - py) * a), (px + (qx - px) * b, py + (qy - py) * b)], fill=(120, 24, 20, 225), width=max(2, int(8 * s)))
    lb = legend_box(v)
    d.rectangle(lb, fill=(226, 208, 152, 240), outline=(90, 70, 44, 255), width=max(2, int(6 * s)))
    fl = font("timesbd.ttf", 56 * s)
    for i, (c, nm) in enumerate(LEGEND):
        y0 = lb[1] + 30 * s + i * 80 * s
        d.rectangle((lb[0] + 36 * s, y0, lb[0] + 136 * s, y0 + 52 * s), fill=COL[c] + (255,), outline=(90, 74, 50, 255), width=max(1, int(4 * s)))
        d.text((lb[0] + 168 * s, y0 - 2 * s), nm, font=fl, fill=INK + (240,))
    return im.resize(out_size, Image.LANCZOS)


def board(img, out_size, lit=False):
    """the map framed as a board (dark wood frame, a little shadow) - the flat menus keep reading as a room."""
    W, H = out_size
    fr = int(min(W, H) * 0.045)
    bd = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(bd)
    d.rectangle((0, 0, W - 1, H - 1), fill=(74, 46, 26, 255))
    for i in range(fr):
        c = int(74 + 40 * (1 - i / fr) * (1 if i < fr / 2 else 0.4))
        d.rectangle((i, i, W - 1 - i, H - 1 - i), outline=(c, int(c * 0.62), int(c * 0.35), 255))
    m = img.convert("RGB").resize((W - 2 * fr, H - 2 * fr), Image.LANCZOS)
    if lit:
        m = Image.fromarray(np.clip(np.asarray(m, np.float32) * 1.12 + 10, 0, 255).astype(np.uint8))
    bd.paste(m, (fr, fr))
    d.rectangle((fr - 1, fr - 1, W - fr, H - fr), outline=(30, 18, 10, 255), width=max(2, fr // 6))
    return bd


def qa(v, info):
    s = v.s
    bad = []
    tags = {k: tag_rect(v, *tc, *TAG_M) for k, _c, _n, _t, _p, tc in MISSIONS}
    tg = tag_rect(v, *TOGGLE["c"], TOGGLE["w"], TOGGLE["h"] * 1.6)
    lb = legend_box(v)
    sheet = (100 * s, 100 * s, v.W - 100 * s, v.H - 100 * s)
    for k, (px, py) in info["pins"].items():
        pr = (px - 20 * s, py - 20 * s, px + 20 * s, py + 20 * s)
        if not hit(pr, sheet):
            bad.append(("pin off the sheet", k))
        bad += [("name over a pin", n, k) for n, r in info["labels"] if hit(pr, r)]
        bad += [("tag over a pin", k2, k) for k2, r in tags.items() if hit(pr, r)]
        if hit(pr, tg) or hit(pr, lb):
            bad.append(("toggle/legend over a pin", k))
    ks = list(tags)
    for i, k in enumerate(ks):
        r = tags[k]
        if not (40 * s <= r[0] and r[2] <= v.W - 40 * s and 40 * s <= r[1] and r[3] <= v.H - 40 * s):
            bad.append(("tag off the sheet", k))
        bad += [("tags overlap", k, k2) for k2 in ks[i + 1:] if hit(r, tags[k2], 12 * s)]
        bad += [("tag over a name", k, n) for n, lr in info["labels"] if hit(r, lr)]
        if hit(r, tg, 12 * s) or hit(r, lb, 12 * s):
            bad.append(("tag over toggle/legend", k))
    for i, (n, r) in enumerate(info["labels"]):
        bad += [("names overlap", n, n2) for n2, r2 in info["labels"][i + 1:] if hit(r, r2, 4 * s)]
        if not (sheet[0] <= r[0] and r[2] <= sheet[2] and sheet[1] <= r[1] and r[3] <= sheet[3]):
            bad.append(("name not fully inside the sheet", n))
        if hit(r, tg, 40 * s) or hit(r, lb, 40 * s):
            bad.append(("name under toggle/legend", n))
    return bad


def pin_uv(v, info, k, pin):
    """a baked pin's own uv; an optional (scene-label) pin's uv, clamped onto the sheet when the place lies beyond it"""
    if k in info["pins"]:
        return v.uv(*info["pins"][k])
    u, w = v.uv(*v.P(*pin))
    return [min(max(u, 0.03), 0.97), min(max(w, 0.03), 0.97)]


def wall_view(W=4096):
    return View(WALL_WIN["lat"][0], WALL_WIN["lat"][1], WALL_WIN["lon_c"], WALL_M[0] / WALL_M[1], W)


def all_views(ne, out):
    os.makedirs(out, exist_ok=True)
    v = wall_view()
    im, info = render(ne, v)
    bad = qa(v, info)
    for b in bad:
        print("QA FAIL", b)
    assert not bad or os.environ.get("WARMAP_DRAFT"), bad
    im.convert("RGB").resize((4096, 3072), Image.LANCZOS).save(os.path.join(out, "wallmap_ne.png"))
    overlay(v, (2048, 1536)).save(os.path.join(out, "ng_overlay.png"))
    # the flat menus: the same map (same window, same data), framed as boards at their widget aspect
    vm = View(WALL_WIN["lat"][0], WALL_WIN["lat"][1], WALL_WIN["lon_c"], 305 / 248.0, 2048)
    fm, _ = render(ne, vm)
    board(fm, (1024, 832)).save(os.path.join(out, "flat_main.png"))
    board(fm, (1024, 832), lit=True).save(os.path.join(out, "flat_main_h.png"))
    # the stock briefing room's own board (its frame stays): the map under the room's hanging lamp - a warm pool from the top centre
    vr = View(WALL_WIN["lat"][0], WALL_WIN["lat"][1], WALL_WIN["lon_c"], 464 / 304.0, 2048)
    fr, _ = render(ne, vr)
    fr = np.asarray(fr.convert("RGB").resize((1024, 672), Image.LANCZOS), np.float32)
    yy, xx = np.mgrid[0:672, 0:1024].astype(np.float32)
    pool = np.exp(-(((xx - 512) / 620.0) ** 2 + ((yy - 40) / 520.0) ** 2))
    fr *= (0.62 + 0.48 * pool)[..., None] * np.array([1.0, 0.97, 0.88], np.float32)
    fr = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8))
    ImageDraw.Draw(fr).rectangle((0, 0, 1023, 671), outline=(40, 26, 14), width=4)
    fr.save(os.path.join(out, "flat_room.png"))
    mk = {"lon": [v.lon0, v.lon1], "lat": [v.lat0, v.lat1], "tag_m": list(TAG_M), "wall_m": list(WALL_M),
          "toggle": {"uv": v.uv(*v.P(*TOGGLE["c"])), "w": TOGGLE["w"], "h": TOGGLE["h"]},
          "missions": [{"key": k, "camp": c, "n": n, "name": nm, "pin_latlon": list(pin), "pin_uv": pin_uv(v, info, k, pin),
                        "pin_offsheet": not (0.03 <= v.uv(*v.P(*pin))[0] <= 0.97 and 0.03 <= v.uv(*v.P(*pin))[1] <= 0.97),
                        "tag_uv": v.uv(*v.P(*tc)), "colour": COL[c], "optional_cvar": OPTIONAL[k]} for k, c, n, nm, pin, tc in MISSIONS],
          "labels": {n: [r[0] / v.W, 1 - r[3] / v.H, r[2] / v.W, 1 - r[1] / v.H] for n, r in info["labels"]}}
    json.dump(mk, open(os.path.join(out, "allmap_markers.json"), "w"), indent=1)
    # make_newgame3d.py's schema (its BT tag pass reads tunisia / sicily / italy; its label QA reads "labels")
    compat = {"lon": mk["lon"], "lat": mk["lat"], "labels": {},
              "markers": {m["key"]: {"lonlat": [m["pin_latlon"][1], m["pin_latlon"][0]], "uv": m["pin_uv"]} for m in mk["missions"]}}
    for old, k in (("tunisia", "bt1"), ("sicily", "bt2"), ("italy", "bt3")):
        compat["markers"][old] = compat["markers"][k]
    json.dump(compat, open(os.path.join(out, "wallmap_ne_markers.json"), "w"), indent=1)
    print("warmap: lon %.2f..%.2f lat %.1f..%.1f; wall/overlay/flat views written to %s; QA %s" % (v.lon0, v.lon1, v.lat0, v.lat1, out, "FAIL" if bad else "ok"))


if __name__ == "__main__":
    a = sys.argv
    if a[1] == "all":
        all_views(a[2], a[3])
    elif a[1] == "box":
        ne, outp, lat0, lat1, lonc, asp, ow, oh = a[2], a[3], float(a[4]), float(a[5]), float(a[6]), float(a[7]), int(a[8]), int(a[9])
        vb = View(lat0, lat1, lonc, asp, max(ow, 2048))
        img, _ = render(ne, vb, pins="--pins" in a)
        img = board(img, (ow, oh)) if "--frame" in a else img.convert("RGB").resize((ow, oh), Image.LANCZOS)
        img.save(outp)
        print("box", outp, "lon %.2f..%.2f" % (vb.lon0, vb.lon1))
