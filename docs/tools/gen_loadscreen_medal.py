"""Loading-screen medal art (docs/proposals/loading_screen_2026-09-26/research.md, section 3.3).

Renders the chosen design - the reference mockup is https://claude.ai/artifact/XhSWBkXAAqtHgFunCE3cet,
based on the MOHAA.exe desktop icon - as 256x256 RGBA uncompressed TGA:

  medal_ring.tga        the STATIC layer: dark round medallion, gold rim, compass ring with N/E/S/W
                        (N brighter), ticks every 15 deg (the 45-deg ones longer and brighter), the dark
                        inner disk the star turns on
  medal_star_00..23.tga the TURNING layer: the faceted bronze five-point star with its dark centre star,
                        one frame per 3 deg over 72 deg, rendered under a FIXED top-left light, so the
                        facets catch the light as it turns (a tcMod rotate would turn the painted
                        highlights with it). 5-fold symmetry makes frame 24 == frame 0: a seamless loop.

The geometry, colours and lighting formula are the mockup's, verbatim (its 48-unit viewBox, scaled so the
outer rim ends ~2.7 px inside the texture edge). Two deliberate differences from the mockup:
  * the hub dome is shaded by the fixed light and does NOT change per frame (the mockup's hub pulsed with
    the rotation angle on a 360-deg period, which would pop at the 72-deg loop point);
  * transparent texels carry the colour of the nearest opaque texel (edge bleed), so bilinear filtering
    and mip levels do not grow a dark fringe around the rim or the star.

Rendered at 8x and box-filtered down in PREMULTIPLIED space (exact area coverage, no halo). Uncompressed
TGA on purpose: Pillow's DXT encoders skew colour (TRAPS T2). Deterministic: same input -> same bytes.

usage: python docs/tools/gen_loadscreen_medal.py <outdir>      (the mod path is
       hzm-mohaa-coop-mod/ui/hzm_loadscreen - see scripts/coop_loadscreen.shader)
       python docs/tools/gen_loadscreen_medal.py <outdir> --check  (regenerate in memory and compare)

       --morph [--speed DEG_S] [--period S] [--shader PATH] [--check]
         the LOOPING old<->new medal (design v4, 2026-09-27): morph_l0..l4.tga + morph_modern.tga into
         <outdir>, and the 6-stage hzmLoadMedalMorph shader text into PATH. Defaults 30 deg/s, 12 s.
         speed x period must be a whole number of turns (360 deg) or the loop does not repeat exactly.
"""
import math
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

SIZE = int(os.environ.get("HZM_MEDAL_SIZE", "256"))  # 256 = the loading screen; gen_memorial_medal.py asks for 512
SS = 8                      # supersampling factor
BIG = SIZE * SS
UNIT = SIZE / 48.5          # mockup viewBox is 48 units; 48.5 keeps the rim ~2.7 px off the edge
FRAMES = 24
STEP_DEG = 72.0 / FRAMES    # 3 deg per frame

# mockup palette
DARK = (92, 60, 20)
LIGHT = (250, 222, 150)
LIGHT_DIR = -135.0          # SVG angle (y down): up-left. FIXED for every frame.
FONT_PATHS = [r"C:\Windows\Fonts\bahnschrift.ttf", r"C:\Windows\Fonts\arialbd.ttf"]


def hexc(s, a=255):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


def lerp(b):
    b = max(0.0, min(1.0, b))
    return tuple(int(round(d + (l - d) * b)) for d, l in zip(DARK, LIGHT)) + (255,)


def P(u):
    """mockup units -> supersampled pixels"""
    return u * UNIT * SS


def pt(r, deg):
    a = math.radians(deg)
    c = BIG / 2.0
    return (c + P(r) * math.cos(a), c + P(r) * math.sin(a))


def circle(d, r, fill=None, outline=None, width=0.0):
    c = BIG / 2.0
    if fill is not None:
        rr = P(r)
        d.ellipse([c - rr, c - rr, c + rr, c + rr], fill=fill)
    if outline is not None and width > 0:
        # an SVG stroke is centred on the path: draw an annulus r +- w/2
        ro, ri = P(r + width / 2.0), P(r - width / 2.0)
        mask = Image.new("L", (BIG, BIG), 0)
        m = ImageDraw.Draw(mask)
        m.ellipse([c - ro, c - ro, c + ro, c + ro], fill=255)
        m.ellipse([c - ri, c - ri, c + ri, c + ri], fill=0)
        d._image.paste(Image.new("RGBA", (BIG, BIG), outline), (0, 0), mask)


def line_round(d, p1, p2, color, width):
    w = P(width)
    d.line([p1, p2], fill=color, width=max(1, int(round(w))))
    for (x, y) in (p1, p2):
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=color)


def font(size_units):
    px = int(round(P(size_units)))
    for fp in FONT_PATHS:
        if os.path.exists(fp):
            f = ImageFont.truetype(fp, px)
            try:
                f.set_variation_by_name("Bold")
            except Exception:
                pass
            return f
    return ImageFont.load_default()


def downsample(img):
    """8x -> 1x, exact area average in premultiplied space, then bleed colour into clear texels."""
    pm = img.convert("RGBa").resize((SIZE, SIZE), Image.BOX)
    out = pm.convert("RGBA")
    return bleed(out)


def bleed(img, passes=8):
    """Give fully transparent texels the colour of their nearest opaque neighbours (alpha untouched)."""
    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))
    known = a.point(lambda v: 255 if v > 0 else 0)
    for _ in range(passes):
        grown = rgb.filter(ImageFilter.MaxFilter(3))
        # only fill texels not yet known; average-ish via max is fine for a 1-2 px apron
        newknown = known.filter(ImageFilter.MaxFilter(3))
        fill_mask = ImageChops.subtract(newknown, known)
        rgb.paste(grown, (0, 0), fill_mask)
        known = newknown
    rr, gg, bb = rgb.split()
    return Image.merge("RGBA", (rr, gg, bb, a))


def render_ring():
    img = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # dark medallion + gold rim (r 23, stroke 1.3)
    circle(d, 23.0, fill=hexc("#15130e"))
    circle(d, 23.0, outline=hexc("#c9a052"), width=1.3)
    # thin inner ring (r 21.4, stroke .5)
    circle(d, 21.4, outline=hexc("#6b5122"), width=0.5)
    # ticks every 15 deg, skipping the four letter positions
    labels = [("N", 0), ("E", 90), ("S", 180), ("W", 270)]
    taken = [a for _, a in labels]
    for a in range(0, 360, 15):
        if any(abs(x - a) < 1 for x in taken):
            continue
        major = a % 45 == 0
        p1 = pt(17.9 if major else 18.6, a - 90)
        p2 = pt(21.0, a - 90)
        line_round(d, p1, p2, hexc("#c9a052") if major else hexc("#8a6a2c"), 0.9 if major else 0.6)
    # letters (N brighter and larger), centred on r 19.3
    for txt, a in labels:
        size = 5.4 if txt == "N" else 4.6
        col = hexc("#f3d27e") if txt == "N" else hexc("#d7b25e")
        f = font(size)
        x, y = pt(19.3, a - 90)
        d.text((x, y), txt, font=f, fill=col, anchor="mm")
    # the inner disk the star turns on (drawn last, as in the mockup: it trims the letters' inner edge)
    circle(d, 16.9, fill=hexc("#231e15"))
    circle(d, 16.9, outline=hexc("#8a6a2c"), width=0.8)
    return downsample(img)


def render_star(rot):
    img = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    RT, RI = 16.2, 6.9
    c = (BIG / 2.0, BIG / 2.0)
    for i in range(5):
        th = -90 + 72 * i + rot
        T = pt(RT, th)
        A = pt(RI, th - 36)
        B = pt(RI, th + 36)
        for poly, phi in (((c, A, T), th - 60), ((c, T, B), th + 60)):
            b = 0.5 + 0.5 * math.cos(math.radians(phi - LIGHT_DIR))
            d.polygon(poly, fill=lerp(math.pow(b, 1.15)))
    # hub dome, lit from the same fixed light (constant across frames)
    hub = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
    hr = P(3.6)
    lx, ly = math.cos(math.radians(LIGHT_DIR)), math.sin(math.radians(LIGHT_DIR))
    hd = ImageDraw.Draw(hub)
    steps = 48
    for k in range(steps, 0, -1):
        f = k / steps                              # 1 at the rim -> 0 at the highlight
        rr = hr * f
        off = (1 - f) * hr * 0.45                  # highlight centre drifts toward the light
        cx, cy = c[0] + lx * off, c[1] + ly * off
        hd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=lerp(0.52 + 0.36 * (1 - f) ** 1.3))
    mask = Image.new("L", (BIG, BIG), 0)
    ImageDraw.Draw(mask).ellipse([c[0] - hr, c[1] - hr, c[0] + hr, c[1] + hr], fill=255)
    img.paste(hub, (0, 0), mask)
    circle(d, 3.6, outline=hexc("#5a3c12"), width=0.5)
    # the small dark centre star (turns with the big one)
    mini = [pt(1.05 if j % 2 else 2.5, -90 + 36 * j + rot) for j in range(10)]
    d.polygon(mini, fill=hexc("#5a3c12"))
    return downsample(img)


def tga_bytes(img):
    """Uncompressed 32-bit TGA, BOTTOM-UP rows, deterministic (no Pillow metadata variance).

    Bottom-up is not a style choice: this engine IGNORES the TGA top-down bit (0x20) -
    renderercommon/tr_image_tga.c has the flip #if 0'd and only prints a developer-gated warning - so a top-down
    file loads upside down. Pillow honours the bit, so a PIL preview of a top-down file looks right while the game
    shows it flipped (bug-3019: the first medal build had N at the bottom and the light coming from below).
    loadscreen_lint.py fails any medal TGA with the bit set."""
    w, h = img.size
    hdr = bytes([0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, w & 255, w >> 8, h & 255, h >> 8, 32, 8])
    r, g, b, a = img.transpose(Image.FLIP_TOP_BOTTOM).split()
    return hdr + Image.merge("RGBA", (b, g, r, a)).tobytes()


def build():
    out = {"medal_ring.tga": tga_bytes(render_ring())}
    for k in range(FRAMES):
        out["medal_star_%02d.tga" % k] = tga_bytes(render_star(k * STEP_DEG))
    return out


# ------------------------------------------------------------------------------------------------ morph (v4)
# The looping old<->new loading medal (user-approved design v4, 2026-09-27): SHADER-ONLY. One 6-stage shader,
# every stage clampMap + blend + the SAME tcMod rotate (one shared angle - the whole logo turns rigidly), oldest
# layer on top; each upper layer fades out/in once per cycle through one clamped-sine alphaGen wave, so the stack
# is an exact weighted mix of opaque discs at every moment (no dips, no ghosts, no pops at the turnarounds or the
# loop wrap). Levels: the original MOHAA.exe icon (docs/tools/assets/mohaa_exe_32.png, nearest), four de-pixelation
# steps each blended 20% further toward the modern medal, and the modern medal (ring + star pre-composited).
# N lock: at angle 0 the original's top star point, the compass N and the modern star's top point are all at 12.
MORPH_ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "mohaa_exe_32.png")
MORPH_STEPS = ((48, 0.2), (64, 0.4), (96, 0.6), (128, 0.8))
MORPH_CENTRES = (0.13, 0.19, 0.25, 0.31, 0.37)   # cycle fraction where L0..L4 are half faded (forward half)
MORPH_RAMP = 0.075                                # cycle fraction each fade takes; > the 0.06 spacing = overlap
MORPH_TEX = "ui/hzm_loadscreen/morph_%s.tga"
# MIP-SAFE MARGIN (bug-3059). tcMod rotate turns the texture coords about the centre, so the quad's corners sample up to
# 0.707 from it - OUTSIDE [0,1] - and clampMap repeats the EDGE texel there. That texel must be transparent at every mip
# level the widget can use, or the rim smears out to the corners as an X (seen in-game at 720p, mip ~1.8). A 2x2-box
# mip at level L averages the outer 2^L base texels; the smallest draw is 48 px (480p) = LOD 2.4, so levels 0..3 must be
# clear: content (plus a pixelation block's overhang, <= 256/48 = 5.3 px) must end >= 8 px inside the edge. The modern
# medal is drawn at 230/256 (rim ~112.6 px, 15 px margin) and the 32 px original at exactly 7x = 224 px (radius 112).
# loadingbar.txt's hzm_loadmedal rect is enlarged by MORPH_RECT_GROW so the medal's on-screen size is unchanged.
MORPH_MODERN_PX = 230
MORPH_ORIG_PX = 224
MORPH_RECT_GROW = SIZE / float(MORPH_MODERN_PX)
MORPH_CLEAR_LEVELS = 4   # mip levels 0..3 must have fully transparent edge texels (checked by loadscreen_lint.py)


def morph_levels():
    src = Image.open(MORPH_ICON).convert("RGBA")
    orig = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    s = MORPH_ORIG_PX  # even size, so it centres on the same point the rotation turns about
    orig.alpha_composite(src.resize((s, s), Image.NEAREST), ((SIZE - s) // 2, (SIZE - s) // 2))
    full = Image.alpha_composite(render_ring(), render_star(0.0))
    m = MORPH_MODERN_PX
    modern = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    modern.alpha_composite(full.convert("RGBa").resize((m, m), Image.LANCZOS).convert("RGBA"), ((SIZE - m) // 2, (SIZE - m) // 2))

    def pixelate(img, r):
        return img.convert("RGBa").resize((r, r), Image.BOX).convert("RGBA").resize((SIZE, SIZE), Image.NEAREST)

    levels = [("l0", orig)]
    for k, (r, w) in enumerate(MORPH_STEPS, 1):
        levels.append(("l%d" % k, pixelate(Image.blend(orig, modern, w), r)))
    levels.append(("modern", modern))
    return levels


def morph_waves():
    waves = []
    for c in MORPH_CENTRES:
        amp = 1.0 / (MORPH_RAMP * 2 * math.pi * math.sin(2 * math.pi * c))
        waves.append((0.5 - amp * math.cos(2 * math.pi * c), amp))
    return waves


def morph_shader(speed, period):
    waves = morph_waves()
    head = ("// HZM coop [user 2026-09-27] LOOPING LOADING MEDAL (design v4) - GENERATED by docs/tools/gen_loadscreen_medal.py\n"
            "// --morph --speed %g --period %g. Do not hand-edit: regenerate. Old <-> new, forever, the whole logo turning\n"
            "// rigidly at %g deg/s; %g s per full cycle (%g revolution(s)). Every stage shares the tcMod rotate (one angle),\n"
            "// oldest on top, each fading once per cycle (clamped-sine alphaGen wave, phase 0.25 = peak at the old state).\n"
            % (speed, period, speed, period, speed * period / 360.0))
    body = "hzmLoadMedalMorph\n{\n\tnopicmip\n\tcull none\n\tforce32bit\n\tsurfaceparm nolightmap\n"
    stage = "\t{\n\t\tclampMap %s\n\t\tblendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA\n\t\ttcMod rotate %g\n%s\t}\n"
    body += stage % (MORPH_TEX % "modern", speed, "")
    for k in (4, 3, 2, 1, 0):
        b, a = waves[k]
        body += stage % (MORPH_TEX % ("l%d" % k), speed,
                         "\t\talphaGen wave sin %.4f %.4f 0.25 %.8g\n" % (b, a, 1.0 / period))
    return head + body + "}\n"


def build_morph():
    return {os.path.basename(MORPH_TEX % n): tga_bytes(img) for n, img in morph_levels()}


# ------------------------------------------------------------------------------------------------ hint arrows
# [user 2026-09-27] the two chevrons either side of the loading hint (ui/loadingbar.txt hzm_loadhint_prev/next; the
# exe parks them beside the text, client/cl_ui.cpp UI_LoadHints_PlaceNav). 32x64 = the widget box's 1:2 (7 x 14
# virtual px). Hint-text cream (fgcolor 0.93 0.90 0.83) at 0.8 alpha, a round-capped stroke, rendered 8x and
# box-filtered in premultiplied space. Clear margins (5 px each side, 10 top/bottom) keep the edge texels transparent
# at every mip the 7-16 px draw can use (a 2x2-box level L averages the outer 2^L texels - bug-3059's lesson).
ARROW_W, ARROW_H = 32, 64
ARROW_RGBA = (237, 230, 212, 204)
ARROW_BOX = (5.0, 10.0, 27.0, 54.0)   # the chevron's extent inside the 32x64 texture (x0, y0, x1, y1)
ARROW_STROKE = 7.0                    # texture px (~1.5 virtual px at the 7-px-wide box)


def render_arrow(right):
    s = SS
    img = Image.new("RGBA", (ARROW_W * s, ARROW_H * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = (v * s for v in ARROW_BOX)
    half = ARROW_STROKE * s / 2.0
    # keep the round caps inside the box
    x0, x1, y0, y1 = x0 + half, x1 - half, y0 + half, y1 - half
    ym = (y0 + y1) / 2.0
    pts = [(x0, y0), (x1, ym), (x0, y1)] if right else [(x1, y0), (x0, ym), (x1, y1)]
    d.line(pts, fill=ARROW_RGBA, width=int(round(ARROW_STROKE * s)), joint="curve")
    for px, py in pts:
        d.ellipse((px - half, py - half, px + half, py + half), fill=ARROW_RGBA)
    out = img.convert("RGBa").resize((ARROW_W, ARROW_H), Image.BOX).convert("RGBA")
    return bleed(out)


def build_arrows():
    return {"hint_prev.tga": tga_bytes(render_arrow(False)), "hint_next.tga": tga_bytes(render_arrow(True))}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    outdir = sys.argv[1]
    if "--arrows" in sys.argv:
        files = build_arrows()
        if "--check" in sys.argv:
            bad = [n for n, b in files.items()
                   if not os.path.exists(os.path.join(outdir, n)) or open(os.path.join(outdir, n), "rb").read() != b]
            print("check:", "OK" if not bad else "STALE %s" % bad)
            return 1 if bad else 0
        os.makedirs(outdir, exist_ok=True)
        for n, b in files.items():
            open(os.path.join(outdir, n), "wb").write(b)
        print("wrote %d arrow textures to %s" % (len(files), outdir))
        return 0
    if "--morph" in sys.argv:
        speed = float(sys.argv[sys.argv.index("--speed") + 1]) if "--speed" in sys.argv else 30.0
        period = float(sys.argv[sys.argv.index("--period") + 1]) if "--period" in sys.argv else 12.0
        if abs((speed * period / 360.0) - round(speed * period / 360.0)) > 1e-6:
            print("WARNING: speed x period is not a whole number of revolutions - the loop would not repeat exactly")
        files = build_morph()
        shader_path = sys.argv[sys.argv.index("--shader") + 1] if "--shader" in sys.argv else None
        shader_txt = morph_shader(speed, period).encode("ascii")
        if "--check" in sys.argv:
            bad = [n for n, b in files.items()
                   if not os.path.exists(os.path.join(outdir, n)) or open(os.path.join(outdir, n), "rb").read() != b]
            if shader_path and (not os.path.exists(shader_path) or open(shader_path, "rb").read() != shader_txt):
                bad.append(shader_path)
            print("check:", "OK" if not bad else "STALE %s" % bad)
            return 1 if bad else 0
        os.makedirs(outdir, exist_ok=True)
        for n, b in files.items():
            open(os.path.join(outdir, n), "wb").write(b)
        if shader_path:
            os.makedirs(os.path.dirname(os.path.abspath(shader_path)), exist_ok=True)
            open(shader_path, "wb").write(shader_txt)
        print("wrote %d morph textures to %s%s" % (len(files), outdir, (" + " + shader_path) if shader_path else ""))
        return 0
    files = build()
    if "--check" in sys.argv:
        bad = [n for n, b in files.items()
               if not os.path.exists(os.path.join(outdir, n)) or open(os.path.join(outdir, n), "rb").read() != b]
        print("check:", "OK" if not bad else "STALE %s" % bad)
        return 1 if bad else 0
    os.makedirs(outdir, exist_ok=True)
    for n, b in files.items():
        with open(os.path.join(outdir, n), "wb") as fh:
            fh.write(b)
    print("wrote %d files to %s" % (len(files), outdir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
