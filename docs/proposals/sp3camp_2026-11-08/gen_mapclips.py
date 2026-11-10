"""gen_mapclips.py - loading-screen clips from THE shared war map (user 2026-11-08: "Yes option 1 for map loads too").

    python -P -E gen_mapclips.py frames <ne_dir> <work_dir> [only1 only2 ...]   render the zoom of every location (or the named ones)
    python -P -E gen_mapclips.py titles <mod_dir> <work_dir>                     overlay the join-card lines per map, write <work>/clips/<map>/
    python -P -E gen_mapclips.py pack <mod_dir> <work_dir>                      gen_loadclip.py each clip (+ the pak) and write ui/loadclips.txt

Per map: a slow push-in on the parchment war map (warmap.py: same data, projection, palette and type) from the whole theatre to the
level's real place (missions.json pins, level_pins for levels elsewhere), a red ink ring drawn round the pin, then the join card's own
lines typed in one at a time - title, unit, place, date and time - read from coop_mod/joincard_table.scr, the join card's source, so
the two always match.  Maps with no known place (lobbies, MP maps) get the theatre view without a pin (clip 'nm_theatre').
Every frame is drawn from the vectors at frame scale (no scaled bitmap: nothing shimmers during the zoom), supersampled 2x and
Lanczos-downsampled; the clip plays once and holds its last frame (gen_loadclip.py --once)."""
import json, math, os, re, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import warmap  # noqa: E402

FD = r"C:\Windows\Fonts"
OW, OH = 1024, 576            # frame size (16:9), packed 1024x512 by gen_loadclip.py (the engine stretches it back)
SS = 2
FPS = 30
TOP = int(576 * 0.78) - 162    # the title block's top: its last line ends at 78% of the frame height
ZOOM_S, TOTAL_S = 3.4, 4.6    # the push-in, then the ring and the last lines; the engine holds the last frame after that
MJ = json.load(open(os.path.join(HERE, "missions.json")))
THEATRE = dict(lat=(33.0, 65.0), lon_c=12.0)
K = math.cos(math.radians(49.0))      # the wall view's projection constant (warmap: lon span = lat span x aspect / cos(mid lat))
INK = (58, 44, 30)


def font(n, px):
    return ImageFont.truetype(os.path.join(FD, n), max(8, int(px)))


def map_mission(m):
    """the mission key of a map name (levels + their briefings), None for anything else"""
    for pat, camp in ((r"^m(\d)l", "aa"), (r"^t(\d)l", "sh"), (r"^e(\d)l", "bt"), (r"^briefing(\d)$", "aa"), (r"^briefingt(\d)$", "sh"), (r"^briefinge(\d)$", "bt")):
        mm = re.match(pat, m.split("/")[-1].lower())
        if mm:
            return "%s%s" % (camp, mm.group(1))
    return None


def place_of(m):
    lp = MJ.get("level_pins", {})
    if m in lp:
        return tuple(lp[m])
    k = map_mission(m)
    if k:
        return tuple([x for x in MJ["missions"] if x["key"] == k][0]["pin"])
    return None


class Cam:
    """an equirectangular view centred (lat, lon) showing `span` degrees of latitude over the frame height"""

    def __init__(self, lat, lon, span, W, H):
        self.lat, self.lon, self.span, self.W, self.H = lat, lon, span, W, H
        self.s = H / span

    def P(self, lat, lon):
        return (self.W / 2 + (lon - self.lon) * K * self.s, self.H / 2 - (lat - self.lat) * self.s)

    def box(self):
        hw = self.W / 2 / (K * self.s)
        hh = self.H / 2 / self.s
        return (self.lon - hw, self.lat - hh, self.lon + hw, self.lat + hh)


_PAPER = {}


def paper_frame(W, H):
    if (W, H) not in _PAPER:
        _PAPER[(W, H)] = warmap.paper(W, H, seed=5)
    return _PAPER[(W, H)].copy()


def draw_frame(D, cam, target, ring_t, pins_all=False, label=None):   # a clip shows only its own pin
    W, H = cam.W, cam.H
    s = H / 1152.0                                   # sizes are set for a 2048x1152 render
    im = paper_frame(W, H)
    bx = cam.box()
    landm = Image.new("L", (W, H), 0)
    ld = ImageDraw.Draw(landm)

    def vis(part):
        a = np.asarray(part)
        return a[:, 0].max() >= bx[0] - 1 and a[:, 0].min() <= bx[2] + 1 and a[:, 1].max() >= bx[1] - 1 and a[:, 1].min() <= bx[3] + 1

    for shape in D["land"]:
        for part in shape:
            if len(part) > 2 and vis(part):
                ld.polygon([cam.P(la, lo) for lo, la in part], fill=255)
    im.alpha_composite(Image.composite(Image.new("RGBA", (W, H), (210, 192, 140, 255)), Image.new("RGBA", (W, H), (150, 166, 160, 125)), landm))
    d = ImageDraw.Draw(im, "RGBA")
    rank_max = 4 if cam.span > 16 else (6 if cam.span > 6 else 8)        # more rivers as the view closes in
    for sh, row in D["rivers"]:
        try:
            rk = int(row.get("scalerank", "9") or 9)
        except ValueError:
            rk = 9
        if rk > rank_max:
            continue
        for part in sh:
            if len(part) > 1 and vis(part):
                d.line([cam.P(la, lo) for lo, la in part], fill=(70, 92, 104, 170), width=max(1, int(round((4.5 - 0.35 * rk) * s))), joint="curve")
    for shape in D["coast"]:
        for part in shape:
            if len(part) > 1 and vis(part):
                d.line([cam.P(la, lo) for lo, la in part], fill=INK + (235,), width=max(2, int(round(4 * s))), joint="curve")
    # graticule: 5 degrees wide out, 1 degree close in (the projection's own lines)
    step = 5 if cam.span > 12 else (2 if cam.span > 5 else 1)
    for lo in range(int(math.floor(bx[0] / step)) * step, int(bx[2]) + step, step):
        x, _ = cam.P(cam.lat, lo)
        d.line([(x, 0), (x, H)], fill=(150, 70, 50, 100), width=max(1, int(2 * s)))
    for la in range(int(math.floor(bx[1] / step)) * step, int(bx[3]) + step, step):
        _, y = cam.P(la, cam.lon)
        d.line([(0, y), (W, y)], fill=(150, 70, 50, 100), width=max(1, int(2 * s)))
    # names at a fixed screen size (the field-map look), drawn with the paper halo
    ft = font("courbd.ttf", 30 * s)
    for n, la, lo, side in warmap.TOWNS:
        x, y = cam.P(la, lo)
        if -50 < x < W + 50 and -50 < y < H + 50:
            d.ellipse([x - 4 * s, y - 4 * s, x + 4 * s, y + 4 * s], fill=INK + (150,))   # faint city dots: never read as a pin
            tw = d.textlength(n, font=ft)
            tx = x + 12 * s if side != "l" else x - 12 * s - tw
            d.text((tx, y - 16 * s), n, font=ft, fill=INK + (235,), stroke_width=max(1, int(4 * s)), stroke_fill=(220, 204, 160, 230))
    for n, la, lo, px_ in warmap.REGIONS:
        x, y = cam.P(la, lo)
        if not (-200 < x < W + 200 and -100 < y < H + 100):
            continue
        sea = "SEA" in n or "OCEAN" in n
        f = font("timesi.ttf" if sea else "timesbd.ttf", abs(px_) * 0.62 * s)
        for li, ln_ in enumerate(n.split("|")):
            sp = " ".join(ln_) if px_ > 0 else ln_
            tw = d.textlength(sp, font=f)
            d.text((x - tw / 2, y - abs(px_) * 0.35 * s + li * abs(px_) * 0.7 * s), sp, font=f, fill=(60, 78, 84, 220) if sea else (70, 50, 36, 210),
                   stroke_width=max(1, int(3 * s)), stroke_fill=(174, 186, 176, 200) if sea else (214, 196, 148, 210))
    if pins_all:
        for m in MJ["missions"]:
            x, y = cam.P(*m["pin"])
            r = 8 * s
            d.ellipse([x - r, y - r, x + r, y + r], fill=(176, 28, 24, 200), outline=(70, 14, 10, 220), width=max(1, int(2 * s)))
    if target:
        x, y = cam.P(*target)
        r = 13 * s
        d.ellipse([x - r, y - r, x + r, y + r], fill=(196, 30, 24, 255), outline=(70, 14, 10, 255), width=max(1, int(3 * s)))
        if ring_t > 0:                              # the red ink ring, drawn round the place like a grease pencil
            R = 70 * s
            n_ = max(2, int(80 * min(1.0, ring_t)))
            pts = []
            for i in range(n_ + 1):
                a = -math.pi / 2 + 2.15 * math.pi * i / 80.0
                rr = R * (1 + 0.06 * math.sin(3 * a + 0.4))
                pts.append((x + rr * math.cos(a), y + rr * 0.92 * math.sin(a)))
            d.line(pts, fill=(160, 26, 20, 225), width=max(2, int(7 * s)), joint="curve")
        if label and ring_t > 0.6:                  # the place's name in red grease pencil beside the ring, fading in
            a_ = int(255 * min(1.0, (ring_t - 0.6) / 0.4))
            fl = font("courbd.ttf", 44 * s)
            d.text((x + 86 * s, y - 64 * s), label, font=fl, fill=(150, 24, 18, a_), stroke_width=max(1, int(5 * s)), stroke_fill=(222, 206, 162, int(a_ * 0.9)))
    return im


def ease(t):
    return t * t * (3 - 2 * t)


def frames(ne, work, only):
    D = warmap.load(ne)
    W, H = OW * SS, OH * SS
    jobs = {}
    for k in sorted(set(parse_joincard(None).keys()) | {"theatre"}):
        if only and k not in only:
            continue
        jobs[k] = None if k == "theatre" else place_of(k)
    jc = parse_joincard(None)
    names = {}
    for k, pl in jobs.items():
        if pl is None:
            continue
        lp = MJ.get("level_pins", {})
        if k in lp:
            names[pl] = jc.get(k, {}).get("Place", "").split(",")[0].upper()
        else:
            names.setdefault(pl, [x for x in MJ["missions"] if tuple(x["pin"]) == pl][0]["name"] if any(tuple(x["pin"]) == pl for x in MJ["missions"]) else "")
    # one zoom per distinct place (levels sharing a place share the frames)
    places = {}
    for k, pl in jobs.items():
        places.setdefault(pl, []).append(k)
    n_fr = int(TOTAL_S * FPS)
    for pl, keys in places.items():
        tag = "theatre" if pl is None else "p_%.3f_%.3f" % pl
        out = os.path.join(work, "zoom", tag)
        if os.path.exists(os.path.join(out, "f%04d.png" % (n_fr - 1))):
            continue
        os.makedirs(out, exist_ok=True)
        lat0, lon0, span0 = (THEATRE["lat"][0] + THEATRE["lat"][1]) / 2, THEATRE["lon_c"], THEATRE["lat"][1] - THEATRE["lat"][0]
        if pl is None:
            lat1, lon1, span1 = lat0, lon0, span0 * 0.78
        else:
            lat1, lon1, span1 = pl[0], pl[1], 3.2
            lon1 -= 0.13 * W * span1 / (K * H)        # the place ends right of centre (x 0.63): the card block owns the left
        for i in range(n_fr):
            t = min(1.0, i / (ZOOM_S * FPS))
            e = ease(t)
            span = math.exp(math.log(span0) + (math.log(span1) - math.log(span0)) * e)        # log zoom: even feel
            # the centre moves with the zoom so the place stays on its straight line to the middle (no swing)
            w = (span0 - span) / (span0 - span1) if span0 != span1 else e
            lat, lon = lat0 + (lat1 - lat0) * w, lon0 + (lon1 - lon0) * w
            ring = (i - ZOOM_S * FPS) / (0.8 * FPS) if pl is not None else 0
            im = draw_frame(D, Cam(lat, lon, span, W, H), pl, ring, label=names.get(pl))
            im.convert("RGB").resize((OW, OH), Image.LANCZOS).save(os.path.join(out, "f%04d.png" % i))
        print("zoom", tag, keys, flush=True)
    ix = os.path.join(work, "zoom_index.json")
    old = json.load(open(ix)) if os.path.exists(ix) else {}          # a partial run (samples) keeps the other maps' entries
    old.update({k: ("theatre" if pl is None else "p_%.3f_%.3f" % pl) for k, pl in jobs.items()})
    json.dump(old, open(ix, "w"), indent=1)


def parse_joincard(mod):
    mod = mod or r"C:\mohaa-coop-dev\hzm-mod-spfix2"
    t = open(os.path.join(mod, "coop_mod", "joincard_table.scr"), encoding="latin-1").read()
    out = {}
    for f, m, v in re.findall(r'level\.coop_jc(\w+)\["([^"]+)"\]\s*=\s*"((?:[^"\\]|\\.)*)"', t):
        out.setdefault(m, {})[f] = v
    return out


BLOCK = 1.7      # the text block's scale over the card's u (sizes and gaps together, so the card's ratios hold)


def titles(mod, work, only=None):
    """the join card's lines over the zoom, typed in one at a time: TITLE, unit, place, date - time (joincard_table.scr).
    Same fonts, colours and size ratio as cg_coopjoincard.c: facfont-20 title at 86 u, courier-20 unit 16 u (grey),
    place 19 u (cream), date 19 u (brass), courier scaled x1.55 like JC_Scale, 2 u drop shadow at 0.8, a brass rule
    under the title (u = frame height / 1080). The 'who' line is the joining player's name, so a loading clip has none."""
    from ritualfont import RitualFont
    fdir = r"H:/hzm_work/mapclips/fonts"
    fh = RitualFont(os.path.join(fdir, "facfont-20@3x.RitualFont"), os.path.join(fdir, "facfont-20@3x.tga"))
    fc = RitualFont(os.path.join(fdir, "courier-20@3x.RitualFont"), os.path.join(fdir, "courier-20@3x.tga"))
    jc = parse_joincard(mod)
    idx = json.load(open(os.path.join(work, "zoom_index.json")))
    CREAM, BRASS = (242, 235, 212), (219, 181, 102)
    GREY = tuple(int(c * 0.8) for c in CREAM)      # the card's grey vanishes over paper: the clips use cream at 80%
    # the whole block at BLOCK x the card's u (every size and gap together, so the ratios stay the card's): the clip is 1024 wide
    # and the engine stretches it to the screen, and courier at the card's 1x is one texel thick here over a busy map
    u = OH / 1080.0 * BLOCK
    X0 = int(round(40 * OH / 1080.0 * 1.4))
    def band(solid):
        # a straight, full-height dark band from the left edge: 75% until past the longest line, then a linear fade over 15%
        x = np.arange(OW, dtype=np.float32)
        gx = np.clip(1.0 - (x - solid) / (0.15 * OW), 0, 1) * 0.75
        g = np.zeros((OH, OW, 4), np.uint8)
        g[..., 0], g[..., 1], g[..., 2] = 4, 4, 3
        g[..., 3] = (np.tile(gx, (OH, 1)) * 255).astype(np.uint8)
        return Image.fromarray(g, "RGBA")
    n_fr = int(TOTAL_S * FPS)
    for m in sorted(set(list(jc.keys()) + ["theatre"])):
        if only and m not in only:
            continue
        z = idx.get(m) or idx.get(map_mission(m) or "", None) or "theatre"
        zdir = os.path.join(work, "zoom", z)
        if not os.path.isdir(zdir):
            continue
        rec = jc.get(m, {})
        title = rec.get("Title", "")
        maxw = 0.40 * OW            # long titles shrink to fit (the card's JC_Fit), so the band never reaches the pin at x 0.63
        def fit(f, s_, px, k=1.0):
            w = f.width(s_, px * k)
            return px * (maxw / w) if w > maxw else px
        hp = fit(fh, title, 86 * u) if title else 0
        # (text, font, px as drawn, colour, y offset from the block top) - the card's own spacings
        rows, y = [], 0.0
        if title:
            rows.append((title, fh, hp, CREAM, y))
            y += hp + 44 * u
        rule_y = y
        y += 30 * u
        for key, sz, col, step in (("Unit", 16, GREY, 46), ("Place", 19, CREAM, 40), ("Date", 19, BRASS, 40)):
            txt = rec.get(key, "")
            if txt:
                px = fit(fc, txt, sz * u * 1.55, 1.0)
                rows.append((txt, fc, px, col, y))
                y += step * u
        ext = max([X0 + f.width(r0, px) for r0, f, px, _c, _y in rows] + [X0 + 360 * u])
        grad = band(min(0.47 * OW, max(0.40 * OW, ext + 24 * u)))
        top = int(OH * 0.78 - y)            # the block ends at 78% of the height: inside the 21:9 'cover' and above the tip strip
        out = os.path.join(work, "clips", m)
        os.makedirs(out, exist_ok=True)
        t0, cps = 0.5, 40.0                 # the title first, then each line in turn, ~40 characters a second
        starts, t = [], t0
        for r in rows:
            starts.append(t)
            t += len(r[0]) / cps + 0.25
        for i in range(n_fr):
            im = Image.open(os.path.join(zdir, "f%04d.png" % i)).convert("RGBA")
            if rows:
                im.alpha_composite(grad)
                tsec = i / FPS
                if tsec >= t0 + 0.3:            # the brass rule draws out under the title, like the card's
                    rw = 360 * u * min(1.0, (tsec - t0 - 0.3) / 0.5)
                    ImageDraw.Draw(im).rectangle((X0, top + rule_y, X0 + rw, top + rule_y + max(1, round(1 * u))), fill=BRASS + (128,))
                for (txt, f, px, col, oy), st in zip(rows, starts):
                    nch = int(max(0, (tsec - st) * cps)) + 1 if tsec >= st else 0
                    if nch <= 0:
                        break
                    shown = txt[:nch]
                    f.draw(im, X0 + 2 * u, top + oy + 2 * u, shown, px, (0, 0, 0), 0.8)
                    f.draw(im, X0, top + oy, shown, px, col, 1.0)
            im.convert("RGB").save(os.path.join(out, "f%04d.jpg" % i), quality=95, subsampling=0)
        print("titles", m, len(rows), flush=True)


def pack(mod, work):
    tool = r"C:\mohaa-coop-dev\docs\tools\gen_loadclip.py"
    cdir = os.path.join(work, "hzlc")
    os.makedirs(cdir, exist_ok=True)
    clips = []
    for m in sorted(os.listdir(os.path.join(work, "clips"))):
        name = "nm_%s" % m
        subprocess.check_call([sys.executable, "-P", "-E", tool, "clip", os.path.join(work, "clips", m), name, "--out", cdir, "--fps", "24",
                               "--src-fps", str(FPS), "--size", "1024x512", "--quality", "80", "--once"])   # 24 fps q80: ~6.5 MB a clip, text stays crisp
        clips.append(os.path.join(cdir, name + ".hzlc"))
    # the rules: every join-card map its own clip, any other level of a mission that mission's zoom, everything else the theatre
    R = ["// GENERATED by docs/proposals/sp3camp_2026-11-08/gen_mapclips.py - do not hand-edit.  The loading screens are the shared war map",
         "// (warmap.py) zooming in on the level's real place with the join card's lines (coop_mod/joincard_table.scr).",
         "//   map <mapname>[*] <clip> [clip ...]   first matching rule wins (cl_loadcine.cpp); 'map *' is the fallback",
         "// Lobby / briefing loads play the UPCOMING mission's clip (coop_campaignNext), as before.",
         "transit nm_theatre"]
    for c in clips:
        m = os.path.basename(c)[3:-5]
        if m != "theatre":
            R.append("map %s nm_%s" % (m, m))
    R.append("map * nm_theatre")
    open(os.path.join(mod, "ui", "loadclips.txt"), "w", newline="\r\n").write("\n".join(R) + "\n")
    subprocess.check_call([sys.executable, "-P", "-E", tool, "pak", os.path.join(work, "zzzzzzzzzz_coop_mapclips.pk3")] + clips
                          + ["--rules", os.path.join(mod, "ui", "loadclips.txt")])
    # the rules ride in the pak too: it sorts after the old zzzzzzzzzz_coop_loadclips*.pk3 (dev installs, 1.10.34-36 players), whose
    # own ui/loadclips.txt would otherwise beat the code pak's (fewer z's) and point every load at the old 2048 clips
    print("packed", len(clips), "clips")


if __name__ == "__main__":
    a = sys.argv
    if a[1] == "frames":
        frames(a[2], a[3], set(a[4:]))
    elif a[1] == "titles":
        titles(a[2], a[3], set(a[4:]))
    elif a[1] == "pack":
        pack(a[2], a[3])
