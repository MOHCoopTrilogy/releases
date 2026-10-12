#!/usr/bin/env python
"""gen_scope_reticles.py - every shipped asset of the modern scope view (bug-3462).

WHAT IT WRITES (TRAPS T2: every shipped byte is derived here, never hand-painted) - ONE out-of-band pak,
hzm-mohaa-coop-mod/zzzzzzzzzz_coop_scopes.pk3 (~1.2 MB, stored, fixed mtimes - deterministic), holding
  textures/hud/coop_scope/ret_<optic>.tga   1024x1024 reticle, black, anti-aliased alpha (RLE TGA)
  textures/hud/coop_scope/aperture.tga      512x512 lens aperture mask (gl1 / no-post fallback)
  textures/hud/coop_scope/eyebox.tga        512x512 exit-pupil (scope shadow) mask (same fallback)
  scripts/coop_scope.shader                 one 2D shader per texture
NOT in the mod tree: under textures/ they would land in zzzzzz_co-op_hzm_mod_assets_tex.pk3 and make every player
re-download ~1.3 GB (same reason as gen_loadart_pak.py, bug-3251). Every name is NEW, so pak order cannot hide them.

    python docs/tools/gen_scope_reticles.py build            write the pak
    python docs/tools/gen_scope_reticles.py check            exit 1 if the pak on disk differs from a fresh build
    python docs/tools/gen_scope_reticles.py sheet OUT.png    a preview contact sheet (QA only)

WHO DRAWS THEM. cgame's cg_hzmscope.c (CG_HzmScopeDraw2D): the reticle is a 2D quad centred on the screen and
sized to the lens (texture radius 1.0 == lens radius), drawn on both renderers. aperture/eyebox are only drawn when
the gl2 scope pass (renderergl2 RB_HZMScope, glsl/hzmscope_fp.glsl) did not run, i.e. on gl1 or with post off.

THE RETICLES are drawn as geometry in lens units (radius 1), rasterised at 4x and box-filtered, so there is no
text, no numbers and nothing painted. One per optic family, period-correct:
  zf39    German Absehen 1 (Zeiss/Hensoldt ZF39 on the Kar98k): pointed post + two heavy side posts, open centre
  zf4     ZF4 (G43 / FG42 / StG 44 scoped): pointed spike from below + a fine horizontal line
  m73b1   Weaver 330 / M73B1 (Springfield '03): fine crosshair
  m84     M84 (M1 Garand sniper): fine crosshair + a fine tapered post from below
  pu      Soviet PU (Mosin, SVT-40): pointed post + side lines that stop short of the centre
  no32    British No.32 (Lee-Enfield No.4(T), L42A1): flat-topped post + full fine horizontal
  type97  Japanese Type 97 (Arisaka): fine crosshair with plain range ticks (no figures)
  carcano Italian scope (Carcano sniper): fine crosshair + a short heavy post that stops below the centre
"""
import io
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
PAK = os.path.join(MOD, "zzzzzzzzzz_coop_scopes.pk3")
STAMP = (2026, 10, 6, 0, 0, 0)

RET_PX = 1024          # shipped reticle size (lens diameter on a 1080p screen is ~990 px)
SS = 4                 # supersampling factor
INK = 6                # reticle colour (near black, never pure 0 so it reads as ink on glass)
FADE_R0, FADE_R1 = 0.93, 0.995   # every reticle fades out at the lens rim (the rim itself is the aperture's job)

OPTICS = ["zf39", "zf4", "m73b1", "m84", "pu", "no32", "type97", "carcano"]


# ---------------------------------------------------------------- geometry helpers (lens units, +y = up)
class Canvas:
    def __init__(self, px):
        self.n = px * SS
        self.img = Image.new("L", (self.n, self.n), 0)
        self.d = ImageDraw.Draw(self.img)

    def p(self, x, y):
        h = self.n / 2.0
        return (h + x * h, h - y * h)

    def poly(self, pts):
        self.d.polygon([self.p(x, y) for x, y in pts], fill=255)

    def rect(self, x0, y0, x1, y1):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])

    def hline(self, x0, x1, y, w):
        self.rect(min(x0, x1), y - w / 2, max(x0, x1), y + w / 2)

    def vline(self, x, y0, y1, w):
        self.rect(x - w / 2, min(y0, y1), x + w / 2, max(y0, y1))

    def alpha(self, px):
        a = np.asarray(self.img, dtype=np.float64) / 255.0
        a = a.reshape(px, SS, px, SS).mean(axis=(1, 3))
        return a


def rim_fade(px):
    c = (np.arange(px) + 0.5) / px * 2.0 - 1.0
    x, y = np.meshgrid(c, -c)
    r = np.sqrt(x * x + y * y)
    t = np.clip((r - FADE_R0) / (FADE_R1 - FADE_R0), 0.0, 1.0)
    return 1.0 - t * t * (3.0 - 2.0 * t)


HAIR = 0.0080          # fine wire: ~4 px at 1080p (0.0042 and 0.0055 vanished against foliage at 720p, s1c/s2)
POST = 0.075           # heavy post width


def post_up(cv, w, tip_y, taper, bottom=-1.2, point=True):
    """a vertical post rising from below to tip_y; the last `taper` units narrow to a point (or a flat top)"""
    top_w = 0.0 if point else w
    cv.poly([(-w / 2, bottom), (w / 2, bottom), (w / 2, tip_y - taper), (top_w / 2, tip_y),
             (-top_w / 2, tip_y), (-w / 2, tip_y - taper)])


def side_posts(cv, w, inner, taper):
    for s in (-1, 1):
        x0 = s * 1.2
        x1 = s * inner
        cv.poly([(x0, -w / 2), (x0, w / 2), (x1 + s * taper, w / 2), (x1, w * 0.30), (x1, -w * 0.30),
                 (x1 + s * taper, -w / 2)])


def draw(optic):
    cv = Canvas(RET_PX)
    if optic == "zf39":
        post_up(cv, POST, 0.0, 0.16)
        side_posts(cv, POST * 0.85, 0.20, 0.05)
    elif optic == "zf4":
        post_up(cv, POST * 0.8, 0.0, 0.30)
        cv.hline(-1.2, -0.035, 0.0, HAIR * 1.3)
        cv.hline(0.035, 1.2, 0.0, HAIR * 1.3)
    elif optic == "m73b1":
        cv.hline(-1.2, 1.2, 0.0, HAIR)
        cv.vline(0.0, -1.2, 1.2, HAIR)
    elif optic == "m84":
        cv.hline(-1.2, 1.2, 0.0, HAIR)
        cv.vline(0.0, 0.0, 1.2, HAIR)
        post_up(cv, 0.034, 0.0, 0.22)
    elif optic == "pu":
        post_up(cv, POST * 0.72, 0.0, 0.20)
        cv.hline(-1.2, -0.14, 0.0, HAIR * 1.6)
        cv.hline(0.14, 1.2, 0.0, HAIR * 1.6)
    elif optic == "no32":
        post_up(cv, 0.070, 0.0, 0.0, point=False)     # heavy, flat-topped (review 1: 0.040 read as a line)
        cv.hline(-1.2, 1.2, 0.0, HAIR)
    elif optic == "type97":
        cv.hline(-1.2, 1.2, 0.0, HAIR)
        cv.vline(0.0, -1.2, 1.2, HAIR)
        for k in range(1, 6):            # plain stadia ticks, no figures
            t = 0.13 * k
            L = 0.045 if k % 2 == 0 else 0.028
            cv.vline(t, -L, L, HAIR)
            cv.vline(-t, -L, L, HAIR)
            cv.hline(-L, L, -t, HAIR)
    elif optic == "carcano":
        cv.hline(-1.2, 1.2, 0.0, HAIR)
        cv.vline(0.0, -1.2, 1.2, HAIR)
        post_up(cv, POST * 0.9, -0.20, 0.08, point=False)  # heavy (review 1: 0.041 read as a crosshair)
    else:
        raise SystemExit("unknown optic " + optic)
    a = cv.alpha(RET_PX) * rim_fade(RET_PX)
    return a


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def radial(px):
    c = (np.arange(px) + 0.5) / px * 2.0 - 1.0
    x, y = np.meshgrid(c, c)
    return np.sqrt(x * x + y * y)


def aperture():
    """lens aperture for the 2D fallback: clear centre, a gentle inner vignette, a SOFT rim (no hard frame)"""
    r = radial(512)
    vig = 0.30 * smooth(0.55, 0.97, r) ** 1.6
    rim = smooth(0.90, 1.0, r)
    return np.maximum(vig, rim)


def eyebox():
    """exit pupil: fully clear inside 0.86, then a soft fall-off - the crescent of the scope shadow (matches
    glsl/hzmscope_fp.glsl: a centred eye casts no shadow, an off-axis one a crescent that deepens quickly)"""
    return smooth(0.86, 1.0, radial(512))


def to_rgba(alpha):
    a = np.clip(np.rint(alpha * 255.0), 0, 255).astype(np.uint8)
    rgb = np.full(a.shape + (3,), INK, dtype=np.uint8)
    return Image.fromarray(np.dstack([rgb, a]), "RGBA")


def tga_bytes(img):
    b = io.BytesIO()
    img.save(b, format="TGA", compression="tga_rle")
    return b.getvalue()


def shader_text(names):
    out = ["// GENERATED by docs/tools/gen_scope_reticles.py - do not edit (bug-3462).",
           "// 2D-only shaders for the modern scope view, drawn by cgame cg_hzmscope.c. New names only (TRAPS T6):",
           "// the retail textures/hud/zoomoverlay, kartop and karbottom shaders are left untouched.",
           "// rgbGen/alphaGen GLOBAL = the R_SetColor colour (what implicit 2D shaders use). NOT vertex: a 2D quad's",
           "// vertex alpha is not the R_SetColor alpha here - alphaGen vertex drew the reticle at (1 - fade) (bug-3462).", ""]
    for n in names:
        mip = "" if n.startswith("ret_") else "\tnomipmaps\n"
        out.append("textures/hud/coop_scope/%s\n{\n\tnopicmip\n%s\t{\n\t\tclampmap textures/hud/coop_scope/%s.tga\n"
                   "\t\tblendFunc blend\n\t\trgbGen global\n\t\talphaGen global\n\t}\n}\n" % (n, mip, n))
    return "\n".join(out).replace("\n", "\r\n").encode("ascii")


def build_all():
    files = {}
    for o in OPTICS:
        a = draw(o)
        # assertion gates (DECISIONS: generators fail loudly)
        assert a.shape == (RET_PX, RET_PX)
        cov = float(a.mean())
        assert 0.0015 < cov < 0.12, (o, cov)                      # something drawn, never a filled disc
        h = RET_PX // 2
        assert a[h - 3:h + 3, h - 3:h + 3].max() > 0.0 or o in ("zf39", "pu", "carcano", "zf4"), o
        assert a[0, 0] == 0.0 and a[-1, -1] == 0.0, o                # nothing outside the lens
        files["ret_%s.tga" % o] = tga_bytes(to_rgba(a))
    ap = aperture()
    assert ap[256, 256] == 0.0 and ap[0, 256] > 0.99, "aperture centre/rim"
    files["aperture.tga"] = tga_bytes(to_rgba(ap))
    ey = eyebox()
    assert ey[256, 256] == 0.0 and ey[0, 256] > 0.99, "eyebox centre/rim"
    files["eyebox.tga"] = tga_bytes(to_rgba(ey))
    names = ["ret_%s" % o for o in OPTICS] + ["aperture", "eyebox"]
    return files, shader_text(names)


def render_pak(files, sh):
    import zipfile
    members = [("textures/hud/coop_scope/" + n, b) for n, b in sorted(files.items())] + [("scripts/coop_scope.shader", sh)]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for name, data in members:
            zi = zipfile.ZipInfo(name, STAMP)
            zi.compress_type = zipfile.ZIP_STORED
            zi.external_attr = 0o644 << 16
            zi.create_system = 0
            z.writestr(zi, data)
    return buf.getvalue(), len(members)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    files, sh = build_all()
    if cmd == "build":
        data, n = render_pak(files, sh)
        open(PAK, "wb").write(data)
        print("wrote %s: %d members, %d bytes" % (os.path.relpath(PAK, ROOT), n, len(data)))
    elif cmd == "check":
        data, n = render_pak(files, sh)
        if not os.path.exists(PAK) or open(PAK, "rb").read() != data:
            print("stale or missing: %s - run: python docs/tools/gen_scope_reticles.py build" % PAK)
            sys.exit(1)
        print("OK %s: %d members, byte-identical to a rebuild" % (os.path.basename(PAK), n))
    elif cmd == "sheet":
        out = sys.argv[2]
        tiles = []
        for o in OPTICS:
            im = Image.open(io.BytesIO(files["ret_%s.tga" % o])).convert("RGBA").resize((384, 384), Image.LANCZOS)
            bg = Image.new("RGBA", im.size, (196, 206, 214, 255))
            d = ImageDraw.Draw(bg)
            d.ellipse((0, 0, 383, 383), outline=(120, 40, 40, 255))
            bg.alpha_composite(im)
            d = ImageDraw.Draw(bg)
            d.text((8, 8), o, fill=(160, 0, 0, 255))
            tiles.append(bg)
        sheet = Image.new("RGB", (384 * 4, 384 * 2), (0, 0, 0))
        for i, t in enumerate(tiles):
            sheet.paste(t.convert("RGB"), ((i % 4) * 384, (i // 4) * 384))
        sheet.save(out)
        print("sheet", out)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
