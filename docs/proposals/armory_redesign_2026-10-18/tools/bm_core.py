"""build_mockups.py - composite the Armory redesign mock-ups (two directions) from REAL assets.

    python build_mockups.py            # writes ../mockup_A.jpg, mockup_B.jpg, *_1024x768.jpg

Everything on screen is one of:
  * a harness render of the real model/operator (assets/*.png, build_cutouts.py: difference-matted, nothing painted)
  * text drawn with the game's own bitmap fonts (gamefont.py: verdana-12 / verdana-14 / facfont-20 @3x sheets)
  * the real padlock texture (textures/mohmenu/coop_lo_lock.tga)
  * flat panels / bars / keylines (what a Label bgcolor or a baked bg texture can draw)
  * numbers from gen_weapon_stats.py (armory_stats.json, derived from the weapon .tik files), unlock text from req<id>.cfg,
    rank names / XP thresholds parsed from coop_mod/xp.scr.
The MOCK player (rank, XP, challenge progress, what is equipped) is the only invented input; see MOCK below.
UI geometry is authored in the menu's 640x480 virtual grid (vx, vy) and scaled to the target size like the engine (virtualres 1).
"""
import hashlib, json, os, re, sys
from PIL import Image, ImageDraw, ImageEnhance
import gamefont as GF

HERE = os.path.dirname(os.path.abspath(__file__))
OUTD = os.path.dirname(HERE)
ASSETS = os.environ.get("ARM_ASSETS") or os.path.join(OUTD, "assets")
MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"

# ---- palette: the hdring HUD set + the cream icon finish -------------------------------------------------------
TRACK = (0x13, 0x12, 0x11)
PANEL = (0x1c, 0x1b, 0x19)
PANEL2 = (0x26, 0x24, 0x21)
LINE = (0x3d, 0x39, 0x34)
CREAM = (0xF0, 0xE8, 0xD6)
DIM = (0x9c, 0x95, 0x86)
FAINT = (0x62, 0x5d, 0x54)
GREEN = (0x8C, 0xC7, 0x73)
RED = (0xEC, 0x5B, 0x43)
ORANGE = (0xFF, 0xA8, 0x33)
BLUE = (0x8C, 0xB8, 0xE6)

STATS = {w["id"]: w for w in json.load(open(os.path.join(HERE, "armory_stats.json")))}

# ---- the MOCK player (the only invented input) ------------------------------------------------------------------
MOCK = {"rank": 5, "xp": 6240, "eq": {"P1": "01", "P2": "24", "SIDE": "48", "NADE": "64"}}


def ranks():
    t = open(os.path.join(MOD, "coop_mod", "xp.scr"), encoding="latin-1").read()
    names = {int(i): n for i, n in re.findall(r'coop_xp_rankName\[(\d+)\]\s*=\s*"([^"]+)"', t)}
    xp = {int(i): int(v) for i, v in re.findall(r"coop_xp_rankXP\[(\d+)\]\s*=\s*(\d+)", t)}
    return names, xp


RN, RXP = ranks()
RIDX = {n: i for i, n in RN.items()}


def req_state(wid):
    """-> dict(unlocked, kind, text, cur, need, frac). Derived from req<id>.cfg (+ xp.scr); challenge progress is sample data."""
    w = STATS[wid]
    r = w.get("req", "")
    if not r:
        return {"unlocked": True}
    m = re.match(r"UNLOCK: Rank: (.+)", r)
    if m:
        i = RIDX[m.group(1)]
        ok = MOCK["rank"] >= i
        return {"unlocked": ok, "kind": "rank", "text": "Rank: " + m.group(1), "cur": MOCK["xp"], "need": RXP[i],
                "frac": min(1.0, MOCK["xp"] / RXP[i])}
    t = r.replace("UNLOCK: ", "")
    n = re.search(r"(\d+)", t)
    need = int(n.group(1)) if n else 1
    frac = 0.12 + (int(hashlib.md5(wid.encode()).hexdigest()[:4], 16) % 70) / 100.0
    return {"unlocked": False, "kind": "chal", "text": t, "sub": w.get("req2", ""), "cur": int(need * frac), "need": need, "frac": frac}


# ---- drawing helpers ----------------------------------------------------------------------------------------------
class Cv:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.sx, self.sy = W / 640.0, H / 480.0
        self.im = Image.new("RGBA", (W, H), TRACK + (255,))
        self.d = ImageDraw.Draw(self.im)

    def X(self, v):
        return int(round(v * self.sx))

    def Y(self, v):
        return int(round(v * self.sy))

    def R(self, x, y, w, h):
        return (self.X(x), self.Y(y), self.X(x + w) - 1, self.Y(y + h) - 1)

    def rect(self, x, y, w, h, fill=None, line=None, lw=1):
        r = self.R(x, y, w, h)
        self.d.rectangle(r, fill=fill, outline=line, width=lw)

    def alpha_rect(self, x, y, w, h, color, a):
        ov = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
        ImageDraw.Draw(ov).rectangle(self.R(x, y, w, h), fill=tuple(color) + (int(255 * a),))
        self.im.alpha_composite(ov)

    @staticmethod
    def quant(vh, baked=False):
        """only the fonts the UI can use, at their REAL size (measured against the live menu: verdana-12 = 7.5 vy, i.e. 0.63 vx per sheet unit):
        verdana-12 7.5 vy | facfont-20 10.7 vy | delima-30 19.5 vy.  baked=True = static chrome painted into the bg texture, any size."""
        if baked:
            return "facfont-20", vh
        if vh <= 8.6:
            return "verdana-12", 7.5
        if vh <= 13:
            return "facfont-20", 10.7
        return "delima-30", 19.5

    def text(self, x, y, s, vh=9.0, color=CREAM, font=None, anchor="l", alpha=1.0, baked=False):
        fam, vv = self.quant(vh, baked)
        px = vv * self.sy
        xs = self.sx / self.sy
        return GF.draw(self.im, (self.X(x), self.Y(y)), s, fam, px, color, anchor, xs=xs)

    def fit(self, x, y, s, maxw, vh=9.0, color=CREAM, anchor="l"):
        """draw s; drop to the small face (verdana-12) when the large one would overflow maxw"""
        if self.twidth(s, vh) > maxw:
            vh = 7.5
        if self.twidth(s, vh) > maxw:
            s = s[:max(3, int(len(s) * maxw / self.twidth(s, vh)) - 1)].rstrip() + "."
        return self.text(x, y, s, vh, color, anchor=anchor)

    def wrap(self, x, y, s, maxw, vh=9.0, color=CREAM, anchor="l", lh=None):
        """one line when it fits, else two (split at the space nearest the middle); returns the number of lines"""
        if self.twidth(s, vh) <= maxw or " " not in s:
            self.fit(x, y, s, maxw, vh, color, anchor)
            return 1
        words = s.split(" ")
        best = min(range(1, len(words)), key=lambda i: abs(self.twidth(" ".join(words[:i]), vh) - self.twidth(" ".join(words[i:]), vh)))
        l1, l2 = " ".join(words[:best]), " ".join(words[best:])
        vh = 7.5
        l1, l2 = " ".join(words[:best]), " ".join(words[best:])
        lh = lh or 8.4
        self.fit(x, y - 1, l1, maxw, vh, color, anchor)
        self.fit(x, y + lh - 1, l2, maxw, vh, color, anchor)
        return 2

    def twidth(self, s, vh=9.0, font=None):
        fam, vv = self.quant(vh)
        return GF.measure(fam, s, vv * self.sy, self.sx / self.sy) / self.sx

    def paste_fit(self, tag, x, y, w, h, dim=1.0, mirror=False, anchor="c"):
        p = os.path.join(ASSETS, tag + ".png")
        if not os.path.isfile(p):
            self.rect(x, y, w, h, fill=None, line=RED)
            self.text(x + 2, y + 2, "MISSING " + tag, 7, RED)
            return None
        g = Image.open(p).convert("RGBA")
        bw, bh = self.X(w), self.Y(h)
        k = min(bw / g.size[0], bh / g.size[1])
        g = g.resize((max(1, int(g.size[0] * k)), max(1, int(g.size[1] * k))), Image.LANCZOS)
        if dim < 1.0:
            a = g.split()[3].point(lambda v: int(v * dim))
            rgb = ImageEnhance.Brightness(g.convert("RGB")).enhance(0.8)
            g = Image.merge("RGBA", (*rgb.split(), a))
        ox = self.X(x) + (bw - g.size[0]) // 2 if anchor == "c" else self.X(x)
        oy = self.Y(y) + (bh - g.size[1]) // 2
        self.im.alpha_composite(g, (ox, oy))
        return g.size

    def lock(self, x, y, vh=9, color=CREAM, alpha=0.85):
        p = os.path.join(MOD, "textures", "mohmenu", "coop_lo_lock.tga")
        g = Image.open(p).convert("RGBA")
        n = self.Y(vh)
        g = g.resize((n, n), Image.LANCZOS)
        a = g.split()[3].point(lambda v: int(v * alpha))
        col = Image.new("RGBA", g.size, tuple(color) + (255,))
        col.putalpha(a)
        self.im.alpha_composite(col, (self.X(x), self.Y(y)))

    def bar(self, x, y, w, h, frac, color, back=PANEL2, ghost=None):
        self.rect(x, y, w, h, fill=back)
        if frac > 0:
            self.rect(x, y, w * min(1.0, frac), h, fill=color)
        if ghost is not None:
            gx = x + w * ghost
            self.d.rectangle((self.X(gx) - 1, self.Y(y) - 2, self.X(gx) + 1, self.Y(y + h) + 1), fill=CREAM)

    def done(self):
        return self.im.convert("RGB")


def background(c):
    """what the baked bg texture would carry: track colour, faint diagonal hairlines, vignette"""
    d = ImageDraw.Draw(c.im)
    for i in range(-c.H, c.W, 46):
        d.line((i, 0, i + c.H // 2, c.H), fill=(0x17, 0x16, 0x14), width=1)
    ov = Image.new("L", (c.W, c.H), 0)
    od = ImageDraw.Draw(ov)
    od.rectangle((0, 0, c.W, c.H), fill=0)
    # soft darkening toward the edges
    for k in range(40):
        od.rectangle((k, k, c.W - k, c.H - k), outline=int(70 * (1 - k / 40) ** 2))
    black = Image.new("RGBA", (c.W, c.H), (0, 0, 0, 255))
    black.putalpha(ov)
    c.im.alpha_composite(black)


def header(c, title_right=""):
    c.text(10, 6, "ARMORY", 19, CREAM, baked=True)
    c.rect(10, 26.5, 52, 2, fill=ORANGE)
    c.text(74, 13, "// SELECT LOADOUT", 7.5, DIM)
    c.rect(10, 30, 620, 1, fill=LINE)
    c.rect(556, 8, 74, 17, fill=PANEL2, line=LINE)
    c.text(593, 11, "DONE", 10, CREAM, anchor="m")


def footer(c, hint):
    c.rect(10, 458, 620, 1, fill=LINE)
    c.text(10, 463, hint, 8.5, DIM)


def tabs_for(c, x, y, w, h, active, names, counts, gap=3):
    n = len(names)
    tw = (w - gap * (n - 1)) / n
    for i, (nm, (u, t)) in enumerate(zip(names, counts)):
        tx = x + i * (tw + gap)
        on = i == active
        c.rect(tx, y, tw, h, fill=PANEL2 if on else PANEL, line=ORANGE if on else LINE)
        c.text(tx + tw / 2, y + 2, nm, 9.5, CREAM if on else DIM, anchor="m")
        c.text(tx + tw / 2, y + h - 9.5, "%d/%d" % (u, t), 7.5, ORANGE if on else FAINT, anchor="m")


def counts_by_tab():
    out = {}
    for wid, w in STATS.items():
        t = int(w["tab"])
        u = 1 if req_state(wid)["unlocked"] else 0
        a, b = out.get(t, (0, 0))
        out[t] = (a + u, b + 1)
    return out


def sorted_tab(tab):
    """unlocked first (authoring order inside the group), then locked ordered by how close they are (progress desc)"""
    ids = [i for i, w in STATS.items() if int(w["tab"]) == tab]
    un = [i for i in ids if req_state(i)["unlocked"]]
    lk = [i for i in ids if not req_state(i)["unlocked"]]
    lk.sort(key=lambda i: -req_state(i)["frac"])
    return un, lk


STAT_ROWS = [("DAMAGE", "dmg_score"), ("RATE OF FIRE", "rate_score"), ("ACCURACY", "acc_score"), ("MOBILITY", "mob_score"), ("RELOAD", "reload_score")]


def raw_str(w, key):
    if key == "dmg_score":
        return "%g" % w["dmg"] if "dmg" in w else "-"
    if key == "rate_score":
        return "%d" % w["rpm"] if "rpm" in w else "-"
    if key == "acc_score":
        return "%d" % w["acc_score"] if "acc_score" in w else "-"
    if key == "mob_score":
        return "%d%%" % round(w["mob"] * 100)
    if key == "reload_score":
        return "%.1fs" % w["reload_s"] if "reload_s" in w else "-"
    return ""


def unit_str(key):
    return {"dmg_score": "per shot", "rate_score": "rpm", "acc_score": "", "mob_score": "speed", "reload_score": "mag swap"}[key]


def delta(cand, eq, key):
    a, b = cand.get(key), eq.get(key)
    if a is None or b is None:
        return "n/a", FAINT
    d = a - b
    if key == "reload_score":
        s = cand["reload_s"] - eq["reload_s"]
        txt = "%+.1fs" % s if abs(s) >= 0.05 else "="
    elif key == "dmg_score":
        s = cand["dmg"] - eq["dmg"]
        txt = "%+g" % s if s else "="
    elif key == "rate_score":
        s = cand["rpm"] - eq["rpm"]
        txt = "%+d" % s if s else "="
    elif key == "mob_score":
        s = round((cand["mob"] - eq["mob"]) * 100)
        txt = "%+d%%" % s if s else "="
    else:
        txt = "%+d" % d if d else "="
    col = GREEN if d > 1 else (RED if d < -1 else FAINT)
    return txt, col


