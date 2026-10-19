"""Loading-screen layout preview: PIL renders a loading menu + ui/loadingbar.txt with the ENGINE's scale
math, so placement and aspect mistakes show up before any game launch (research.md section 5, P0.2).

It PARSES the real files - the menu's .urc and ui/loadingbar.txt - rather than restating their rects:
  * stock stretch (ui_menuCenter 0): x * vidWidth/640, y * vidHeight/480     (uilib/uiwidget.cpp SetVirtualScale)
  * scalecvar <cvar>: vidHeight/480 * cvar on BOTH axes, position included  (same function, m_scaleCvar branch)
  * align centerx: x = vidWidth/2 - width/2                                   (Realign)
  * bgcolor fill, shader stretched over the rect, enabledcvar (multi-condition AND, uiwidget.cpp isEnabled)
  * Label text: linkcvar value, centred both ways (the Label default), glyphs from the real RitualFont atlas
    at a UNIFORM vidHeight/480 scale (ui_textUniform 1, uilib/uifont.cpp UI_UniformTextScale)
  * hzmLoadMedal is composited from medal_ring.tga + medal_star_NN.tga
Images are approximations of the renderer (no gamma, no mip filtering), not game screenshots.

usage: python docs/tools/loadscreen_preview.py --out DIR [--overlay DIR] [--menu m1l1|loading_default|m2l1]
          [--res 1024x768 ...] [--hint "text"] [--frame N] [--set cvar=value ...]
--overlay: a staging tree searched BEFORE the mod tree (to preview files not yet copied in).
"""
import argparse
import glob
import io
import os
import re
import zipfile

from PIL import Image, ImageDraw

MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
GAME = r"G:\GOG\Medal of Honor - Allied Assault War Chest"


class VFS:
    """Engine-order lookup: retail paks (main < mainta < maintt, alphabetical inside each), then the mod tree,
    then the overlay. LAST match wins, like the engine (TRAPS T6)."""

    def __init__(self, overlay=None):
        self.layers = []
        for d in ("main", "mainta", "maintt"):
            for p in sorted(glob.glob(os.path.join(GAME, d, "*.pk3")), key=lambda s: os.path.basename(s).lower()):
                if "co-op_hzm_mod" in os.path.basename(p).lower():
                    continue  # the mod tree stands in for the (possibly stale) deployed coop paks
                try:
                    z = zipfile.ZipFile(p)
                except Exception:
                    continue
                self.layers.append(("zip", z, {n.lower(): n for n in z.namelist()}))
        self.layers.append(("dir", MOD, None))
        if overlay:
            self.layers.append(("dir", overlay, None))

    def read(self, path):
        pl = path.replace("\\", "/").lower()
        for kind, src, idx in reversed(self.layers):
            if kind == "zip":
                if pl in idx:
                    return src.read(idx[pl])
            else:
                f = os.path.join(src, pl.replace("/", os.sep))
                if os.path.exists(f):
                    return open(f, "rb").read()
                # case-insensitive fallback
                d, b = os.path.split(f)
                if os.path.isdir(d):
                    for n in os.listdir(d):
                        if n.lower() == b.lower():
                            return open(os.path.join(d, n), "rb").read()
        return None

    def names(self, prefix, ext):
        out = set()
        for kind, src, idx in self.layers:
            if kind == "zip":
                out.update(k for k in idx if k.startswith(prefix) and k.endswith(ext))
            else:
                base = os.path.join(src, prefix.replace("/", os.sep))
                if os.path.isdir(base):
                    for n in os.listdir(base):
                        if n.lower().endswith(ext):
                            out.add((prefix + n).lower())
        return sorted(out)

    def image(self, path):
        stem = re.sub(r"\.(tga|jpg|png|dds)$", "", path, flags=re.I)
        for ext in (".tga", ".jpg", ".png"):  # the engine tries .dds first; previews skip DXT
            b = self.read(stem + ext)
            if b:
                return Image.open(io.BytesIO(b)).convert("RGBA")
        return None


def parse_shaders(vfs):
    """name -> first map/clampMap/animMap image path of each stage list (enough for 2D menu art)."""
    table = {}
    for sp in vfs.names("scripts/", ".shader"):
        txt = vfs.read(sp).decode("latin1")
        txt = re.sub(r"//[^\n]*", "", txt)
        toks = re.findall(r'"[^"]*"|[{}]|[^\s{}]+', txt)
        i, depth, name, maps = 0, 0, None, []
        while i < len(toks):
            t = toks[i]
            if t == "{":
                depth += 1
            elif t == "}":
                depth -= 1
                if depth == 0 and name:
                    table[name.lower()] = maps
                    name, maps = None, []
            elif depth == 0:
                name = t.strip('"')
            elif depth == 2 and t.lower() in ("map", "clampmap") and i + 1 < len(toks):
                maps.append(toks[i + 1])
            elif depth == 2 and t.lower() == "animmap" and i + 2 < len(toks):
                maps.append(toks[i + 2])
            i += 1
    return table


def parse_urc(text):
    """-> (menu_header_tokens, [widget dicts]) in file order."""
    text = re.sub(r"//[^\n]*", "", text)
    lines = [l.strip() for l in text.splitlines()]
    header, widgets, cur, depth, cls, pending = {}, [], None, 0, None, False
    for l in lines:
        if not l:
            continue
        toks = re.findall(r'"[^"]*"|\S+', l)
        head = toks[0]
        if head == "resource":
            pending = True
            continue
        if pending and depth == 0 and head not in ("{", "}"):
            cls = head
            continue
        if head == "{":
            depth += 1
            cur = {"class": cls, "enabledcvar": "", "align": []}
            pending = False
            continue
        if head == "}":
            depth -= 1
            widgets.append(cur)
            cur = None
            continue
        args = [t.strip('"') for t in toks[1:]]
        if cur is not None:
            k = head.lower()
            if k == "align":
                cur["align"] += [a.lower() for a in args]
            else:
                cur[k] = args
        else:
            header[head.lower()] = args
    return header, widgets


def enabled(expr, cvars):
    for tok in expr.split():
        m = re.match(r"^(!?)([A-Za-z_0-9]+)(<=|>=|==|!=|<|>)?(-?\d+)?$", tok)
        if not m:
            continue
        neg, name, op, rhs = m.groups()
        v = int(float(cvars.get(name, "0") or 0))
        if op:
            r = int(rhs)
            ok = {"<": v < r, ">": v > r, "<=": v <= r, ">=": v >= r, "==": v == r, "!=": v != r}[op]
        elif neg:
            ok = v == 0
        else:
            ok = v != 0
        if not ok:
            return False
    return True


class RitualFont:
    def __init__(self, vfs, name):
        for cand in (name + "@3x", name):
            b = vfs.read("fonts/%s.ritualfont" % cand)
            if b:
                break
        t = b.decode("latin1")
        self.height = float(re.search(r"height\s+([\d.]+)", t).group(1))
        self.aspect = float(re.search(r"aspect\s+([\d.]+)", t).group(1))
        ind = re.search(r"indirections\s*{([^}]*)}", t).group(1).split()
        self.ind = [int(x) for x in ind]
        locs = re.findall(r"{\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*}", t[t.find("locations"):])
        self.loc = [tuple(float(v) for v in q) for q in locs]
        self.atlas = vfs.image("gfx/fonts/%s" % cand)

    def glyph(self, ch):
        i = self.ind[ord(ch)] if ord(ch) < len(self.ind) else -1
        if i < 0:
            i = self.ind[ord("?")]
        return self.loc[i]

    def width(self, text):
        return sum(self.glyph(c)[2] for c in text)

    def draw(self, img, x, y, text, scale, color):
        W, H = self.atlas.size
        for c in text:
            px, py, pw, ph = self.glyph(c)
            if pw > 0 and ph > 0 and c != " ":
                s0, t0 = px / 256.0, py * self.aspect / 256.0
                s1, t1 = s0 + pw / 256.0, t0 + ph * self.aspect / 256.0
                g = self.atlas.crop((int(round(s0 * W)), int(round(t0 * H)), int(round(s1 * W)), int(round(t1 * H))))
                gw, gh = max(1, int(round(pw * scale))), max(1, int(round(self.height * scale)))
                g = g.resize((gw, gh), Image.LANCZOS)
                a = g.split()[3]
                tint = Image.new("RGBA", g.size, color)
                tint.putalpha(Image.eval(a, lambda v: v * color[3] // 255))
                img.alpha_composite(tint, (int(round(x)), int(round(y))))
            x += pw * scale


def render(vfs, shaders, menu_text, bar_text, W, H, cvars, frame, overlay_dir):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    header, own = parse_urc(menu_text)
    _, inc = parse_urc(bar_text)
    sx, sy = W / 640.0, H / 480.0
    fonts = {}
    nav_geom = None  # (centre x, centre y, text width) of the hint, for the arrow widgets that follow it
    for w in own + inc:
        name = (w.get("name") or [""])[0]
        if name in ("continuebutton",):
            continue  # disabled for the whole load (cl_ui.cpp UI_BeginLoad)
        if name in ("loadingbar", "loadingbar_border"):
            continue  # SS_LOADING2 only; these previews show a map without a .min (flasher mode)
        if w["enabledcvar"] and not enabled(w["enabledcvar"][0], cvars):
            continue
        if "rect" not in w:
            continue
        x, y, rw, rh = (float(v) for v in w["rect"])
        if "scalecvar" in w:
            s = sy * float(cvars.get(w["scalecvar"][0], "1"))
            X, Y, RW, RH = x * s, y * s, rw * s, rh * s
        else:
            X, Y, RW, RH = x * sx, y * sy, rw * sx, rh * sy
        if "centerx" in w["align"]:
            X = W / 2.0 - RW / 2.0
        if name in ("hzm_loadhint_prev", "hzm_loadhint_next") and nav_geom:
            # an exe that can page parks these beside the hint text every frame (client/cl_ui.cpp
            # UI_LoadHints_PlaceNav: LOADNAV_GAP 8, box 7 x 14 virtual px, at the text's own vertical scale)
            cx, cy, tw = nav_geom
            RW, RH = 7.0 * sy, 14.0 * sy
            X = cx - tw / 2.0 - 8.0 * sy - RW if name.endswith("prev") else cx + tw / 2.0 + 8.0 * sy
            Y = cy - RH / 2.0
        box = (int(round(X)), int(round(Y)), int(round(X + RW)), int(round(Y + RH)))
        bw, bh = max(1, box[2] - box[0]), max(1, box[3] - box[1])
        bg = [float(v) for v in w.get("bgcolor", ["0", "0", "0", "0"])]
        if bg[3] > 0:
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(layer).rectangle(box, fill=tuple(int(round(c * 255)) for c in bg))
            img.alpha_composite(layer)
        # linkcvartoshader (uilib/uilabel.cpp Draw): the shader NAME is the linkcvar value, and no text is drawn
        cvshader = "linkcvartoshader" in w and "linkcvar" in w
        if "shader" in w or (cvshader and cvars.get(w["linkcvar"][0], "")):
            sh = cvars.get(w["linkcvar"][0], "") if cvshader else w["shader"][0]
            if sh.lower() == "hzmloadmedal":
                base = os.path.join(overlay_dir or MOD, "ui", "hzm_loadscreen")
                ring = vfs.image("ui/hzm_loadscreen/medal_ring.tga")
                star = vfs.image("ui/hzm_loadscreen/medal_star_%02d.tga" % frame)
                pic = Image.alpha_composite(ring, star)
            else:
                maps = shaders.get(sh.lower(), [sh])
                pic = vfs.image(maps[0]) if maps else None
            if pic is not None:
                pic = pic.convert("RGBa").resize((bw, bh), Image.LANCZOS).convert("RGBA")
                img.alpha_composite(pic, (box[0], box[1]))
        if w["class"] == "Label" and ("linkcvar" in w or "title" in w) and not cvshader:
            text = cvars.get(w["linkcvar"][0], "") if "linkcvar" in w else w["title"][0]
            if text:
                fname = (w.get("font") or ["verdana-12"])[0]
                if fname not in fonts:
                    fonts[fname] = RitualFont(vfs, fname)
                f = fonts[fname]
                fg = tuple(int(round(float(c) * 255)) for c in w.get("fgcolor", ["1", "1", "1", "1"]))
                scale = sy  # ui_textUniform 1: glyphs at vidHeight/480 on both axes
                tw, th = f.width(text) * scale, f.height * scale
                tx = X + (RW - tw) / 2.0
                ty = Y + (RH - th) / 2.0
                f.draw(img, tx, ty, text, scale, fg)
                if name == "hzm_loadhint":
                    nav_geom = (X + RW / 2.0, Y + RH / 2.0, tw)
    return img.convert("RGB")


MENUS = {
    "m1l1": "ui/loading_m1l1.urc",
    "loading_default": "ui/loading_default.urc",
    "m2l1": "ui/loading_m2l1.urc",
    "mohdm1": "ui/loading_mohdm1.urc",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--overlay")
    ap.add_argument("--menu", nargs="+", default=["m1l1"])
    ap.add_argument("--res", nargs="+", default=["1024x768", "1920x1080", "3440x1440"])
    ap.add_argument("--hint", default="Downed? Tap F to call a medic, or hold F with a medkit to revive yourself in 5 seconds.")
    ap.add_argument("--frame", type=int, default=0)
    ap.add_argument("--set", nargs="*", default=[])
    a = ap.parse_args()
    vfs = VFS(a.overlay)
    shaders = parse_shaders(vfs)
    cvars = {"ui_loadClassic": "0", "ui_loadHintsOn": "1", "ui_loadIconScale": "1", "ui_voodoo": "0",
             "ui_loadhint": a.hint}
    for kv in a.set:
        k, v = kv.split("=", 1)
        cvars[k] = v
    bar = vfs.read("ui/loadingbar.txt").decode("latin1")
    os.makedirs(a.out, exist_ok=True)
    for m in a.menu:
        menu = vfs.read(MENUS.get(m, m)).decode("latin1")
        for r in a.res:
            W, H = (int(v) for v in r.split("x"))
            im = render(vfs, shaders, menu, bar, W, H, cvars, a.frame, a.overlay)
            p = os.path.join(a.out, "loadscreen_%s_%s.png" % (m, r))
            im.save(p)
            print(p)


if __name__ == "__main__":
    main()
