# -*- coding: utf-8 -*-
"""Team-select faction emblems for ui/SelectTeam.urc + ui/ObjSelectTeam.urc.

[user 2026-09-20] "I like it but can you make icons too?" - the modern team-select panels (ALLIES / AXIS +
SPECTATE) were text-only. These are the three emblems that sit above/beside the labels:

  coop_ts_allies.tga  - a five-point Allied star in a thin ring (US/Allied insignia), cool white-blue to
                        match the blue ALLIES panel text (0.86 0.90 0.98).
  coop_ts_axis.tga    - a cross patteE (the Wehrmacht Balkenkreuz / Iron-Cross military marking the game
                        itself uses on German materiel - a standard armed-forces insignia, NOT a party
                        symbol), warm off-white to match the red AXIS panel text (0.98 0.88 0.84).
  coop_ts_spec.tga    - a simple eye glyph for the SPECTATE button.

Drawn, not upscaled: UI materials load with RegisterShaderNoMip (no mipmaps, cl_ui.cpp), so each texture is
drawn at 8x and Lanczos-downsampled to 128 for clean edges near its largest on-screen size (same recipe as
gen_menu_arrows.py). Textures are gitignored in the mod repo, so THIS SCRIPT is the source; build.ps1 packs
whatever sits in textures/mohmenu/. Referenced from the .urc by raw path "textures/mohmenu/coop_ts_*.tga",
exactly like the coop_mp_lock padlock.

    python docs/tools/gen_teamselect_icons.py            # write the three TGAs
    python docs/tools/gen_teamselect_icons.py --preview <png>
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter


def _dither(img, amp=2.2):
    """[user 2026-09-21] Kill 8-bit gradient BANDING (the visible horizontal steps / blocky look the user
    reported on the team-select backdrop). force32bit only sets the GPU texture format - an 8-bit-per-channel
    source gradient still quantises into bands, which read hard on a 2048px image stretched to 3440. Add a
    small amount of signed per-pixel noise to the RGB channels so each band edge is broken up into a smooth
    ramp (standard ordered-dither substitute). Alpha is left untouched. Requires numpy."""
    import numpy as np
    a = np.asarray(img.convert("RGBA")).astype(np.int16)
    noise = np.random.default_rng(12345).integers(-int(amp), int(amp) + 1, size=a[:, :, :3].shape, dtype=np.int16)
    a[:, :, :3] = np.clip(a[:, :, :3] + noise, 0, 255)
    return Image.fromarray(a.astype("uint8"), "RGBA")


OUT_DIR = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\textures\mohmenu"
SIZE = 256          # [user 2026-09-21] emblems bumped 128 -> 256 for the redesigned, larger team panels
SS = 8
BIG = SIZE * SS

ALLIES = (222, 233, 252, 255)      # ~0.86 0.90 0.98, lifted
ALLIES_RING = (150, 178, 224, 255)
AXIS = (246, 236, 226, 255)        # ~0.98 0.88 0.84, lifted to off-white
AXIS_TRIM = (58, 40, 36, 255)
SPEC = (216, 211, 197, 255)        # ~0.84 0.82 0.76
TRIM = (14, 16, 22, 235)


def _canvas():
    return Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))


def _shadow(shape_layer, blur, alpha, off):
    """A soft drop shadow of any opaque layer, for depth on the panel."""
    a = shape_layer.split()[3].point(lambda v: min(alpha, v))
    sh = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
    sh.putalpha(a)
    sh = Image.composite(Image.new("RGBA", (BIG, BIG), (0, 0, 0, 255)), sh, a)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out = _canvas()
    out.alpha_composite(sh, (off, off))
    return out


def _star_points(cx, cy, r_out, r_in, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(2 * n):
        r = r_out if i % 2 == 0 else r_in
        a = rot + i * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def allies():
    img = _canvas()
    cx = cy = BIG / 2.0
    R = BIG * 0.40
    # thin outer ring
    ring = _canvas()
    dr = ImageDraw.Draw(ring)
    dr.ellipse([cx - R * 1.14, cy - R * 1.14, cx + R * 1.14, cy + R * 1.14],
               outline=ALLIES_RING, width=int(BIG * 0.020))
    # star
    star = _canvas()
    pts = _star_points(cx, cy, R, R * 0.40)
    ds = ImageDraw.Draw(star)
    ds.polygon(pts, fill=ALLIES)
    ds.polygon(pts, outline=TRIM, width=int(BIG * 0.010))
    img.alpha_composite(_shadow(star, BIG * 0.020, 150, int(BIG * 0.014)))
    img.alpha_composite(ring)
    img.alpha_composite(star)
    return img.resize((SIZE, SIZE), Image.LANCZOS)


def _cross_pattee(cx, cy, R):
    A = R * 0.98      # arm reach
    t = R * 0.66      # tip half-width
    n = R * 0.20      # neck half-width
    c = R * 0.20      # neck distance from centre
    return [
        (-n, -c), (-t, -A), (t, -A), (n, -c),   # top arm
        (c, -n), (A, -t), (A, t), (c, n),       # right arm
        (n, c), (t, A), (-t, A), (-n, c),       # bottom arm
        (-c, n), (-A, t), (-A, -t), (-c, -n),   # left arm
    ]


def axis():
    img = _canvas()
    cx = cy = BIG / 2.0
    R = BIG * 0.42
    pts = [(cx + x, cy + y) for x, y in _cross_pattee(0, 0, R)]
    cross = _canvas()
    dc = ImageDraw.Draw(cross)
    # dark trim underneath (Balkenkreuz reads as a white cross with a dark edge)
    dc.polygon(pts, fill=AXIS)
    dc.polygon(pts, outline=AXIS_TRIM, width=int(BIG * 0.028))
    img.alpha_composite(_shadow(cross, BIG * 0.020, 150, int(BIG * 0.014)))
    img.alpha_composite(cross)
    return img.resize((SIZE, SIZE), Image.LANCZOS)


def spec():
    img = _canvas()
    cx = cy = BIG / 2.0
    w = BIG * 0.42      # eye half-width
    h = BIG * 0.26      # eye half-height
    lw = int(BIG * 0.030)
    eye = _canvas()
    de = ImageDraw.Draw(eye)
    # almond outline (two arcs approximated by a stretched ellipse outline + lids)
    de.ellipse([cx - w, cy - h, cx + w, cy + h], outline=SPEC, width=lw)
    # iris + pupil
    ir = BIG * 0.15
    de.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill=SPEC)
    de.ellipse([cx - ir * 0.45, cy - ir * 0.45, cx + ir * 0.45, cy + ir * 0.45], fill=(14, 16, 22, 255))
    img.alpha_composite(_shadow(eye, BIG * 0.016, 140, int(BIG * 0.012)))
    img.alpha_composite(eye)
    return img.resize((SIZE, SIZE), Image.LANCZOS)


NAMES = {"coop_ts_allies.tga": allies, "coop_ts_axis.tga": axis, "coop_ts_spec.tga": spec}


# [user 2026-09-21] WHOLE-LAYOUT REDESIGN of the team-select screen: a full-screen backdrop + two faction
# panels, so the .urc can render a designed page instead of flat-colour boxes. All procedural (crisp at any
# scale, no source art needed), matching the emblem style above.
def _fractal(W, H, octaves, seed, aspect=1.0):
    """Smooth multi-octave value noise in [0,1] - cheap 'atmospheric' cloud/haze field. Low-res random per
    octave, bicubic-upsampled and summed with halving amplitude, so it has large soft forms plus fine detail."""
    import numpy as np
    rng = np.random.default_rng(seed)
    acc = np.zeros((H, W), np.float32)
    amp = 1.0
    tot = 0.0
    for o in range(octaves):
        nh = max(2, int(H / (2 ** (octaves - o))))
        nw = max(2, int(W / (2 ** (octaves - o)) * aspect))
        low = (rng.random((nh, nw), np.float32) * 255).astype("uint8")
        up = np.asarray(Image.fromarray(low).resize((W, H), Image.BICUBIC), np.float32) / 255.0
        acc += amp * up
        tot += amp
        amp *= 0.5
    return acc / tot


def background():
    """[user 2026-09-21] HD atmospheric backdrop pass. The flat dithered gradient read 'clean but simple';
    this builds real depth in numpy - a cinematic vertical gradient, a soft faction colour wash (allied blue
    L / axis red R), a drifting haze layer (fractal noise) that reads like distant smoke, a top light bloom,
    and a wide vignette - then dithers so nothing bands. Still fully procedural (no external art)."""
    import numpy as np
    W, H = 2048, 1536
    yy = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None]
    xx = np.linspace(0.0, 1.0, W, dtype=np.float32)[None, :]

    # cinematic vertical luminance: darkest at top & bottom, lifted a touch above centre where the panels sit
    vg = np.clip(1.0 - np.abs(yy - 0.44) * 1.35, 0.0, 1.0) ** 1.2
    r = 9.0 + 15.0 * vg
    g = 11.0 + 17.0 * vg
    b = 15.0 + 25.0 * vg

    # faction wash - blue bleeding from the left edge, warm red from the right, fading to a neutral seam
    left = np.clip((0.5 - xx) * 2.0, 0.0, 1.0) ** 1.3
    right = np.clip((xx - 0.5) * 2.0, 0.0, 1.0) ** 1.3
    r += right * 66.0 * vg + left * 6.0 * vg
    g += left * 26.0 * vg + right * 20.0 * vg
    b += left * 74.0 * vg + right * 16.0 * vg

    # atmospheric haze - two fractal layers, one broad + one finer, modulated by the vertical gradient so it
    # pools in the mid-band and fades into the dark edges (like backlit smoke over a battlefield)
    haze = 0.65 * _fractal(W, H, 5, 7, aspect=1.4) + 0.35 * _fractal(W, H, 6, 23, aspect=1.4)
    haze = (haze - haze.mean())
    hz = (22.0 * vg) * (0.6 + 0.4 * right + 0.4 * left)  # a bit stronger under the coloured sides
    r += haze * hz
    g += haze * hz
    b += haze * hz

    # top light bloom - a soft cool glow from above-centre, so the eye is drawn up to the title
    bloom = np.clip(1.0 - (((xx - 0.5) * 2.2) ** 2 + ((yy - 0.06) * 2.6) ** 2), 0.0, 1.0) ** 1.5
    r += bloom * 26.0
    g += bloom * 30.0
    b += bloom * 40.0

    # wide radial vignette
    cxn = (xx - 0.5) * 2.0
    cyn = (yy - 0.5) * 2.0
    rad = np.sqrt(cxn * cxn * 0.85 + cyn * cyn)
    vigmul = np.clip(1.15 - rad * 0.55, 0.35, 1.0)
    r *= vigmul
    g *= vigmul
    b *= vigmul

    arr = np.stack([np.clip(r, 0, 255), np.clip(g, 0, 255), np.clip(b, 0, 255),
                    np.full((H, W), 255.0, np.float32)], axis=-1).astype("uint8")
    img = Image.fromarray(arr, "RGBA")

    # centre divider glow (PIL, for the soft blur) - the seam between the two factions
    cx = W // 2
    dv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(dv).rectangle([cx - 3, 40, cx + 3, H - 40], fill=(205, 212, 224, 40))
    dv = dv.filter(ImageFilter.GaussianBlur(9))
    ImageDraw.Draw(dv).rectangle([cx - 1, 64, cx + 1, H - 64], fill=(226, 231, 240, 70))
    img.alpha_composite(dv)

    return _dither(img, 2.6)


def _panel(base, edge):
    W, H = 720, 960
    r = 26
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dg = ImageDraw.Draw(grad)
    for y in range(H):
        f = 1.0 - (y / float(H)) * 0.55
        dg.line([(0, y), (W, y)], fill=(int(base[0] * f), int(base[1] * f), int(base[2] * f), 236))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1], radius=r, fill=255)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)
    # top edge highlight
    hl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(hl).line([(24, 9), (W - 24, 9)], fill=(255, 255, 255, 80), width=5)
    hl = hl.filter(ImageFilter.GaussianBlur(3))
    img.alpha_composite(Image.composite(hl, Image.new("RGBA", (W, H), (0, 0, 0, 0)), mask))
    # border
    bd = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(bd).rounded_rectangle([1, 1, W - 2, H - 2], radius=r, outline=edge, width=3)
    img.alpha_composite(bd)
    return _dither(img, 2.2)


def panel_allies():
    return _panel((26, 42, 66), (120, 160, 210, 255))


def panel_axis():
    return _panel((62, 30, 28), (200, 120, 110, 255))


SPECIALS = {
    "coop_ts_bg.tga": background,
    "coop_ts_panel_allies.tga": panel_allies,
    "coop_ts_panel_axis.tga": panel_axis,
}


def build():
    out = {}
    for name, fn in NAMES.items():
        img = fn()
        path = os.path.join(OUT_DIR, name)
        img.save(path, format="TGA")
        out[name] = img
        print("wrote %s %dx%d" % (path, img.size[0], img.size[1]))
    for name, fn in SPECIALS.items():
        img = fn()
        path = os.path.join(OUT_DIR, name)
        img.save(path, format="TGA")
        out[name] = img
        print("wrote %s %dx%d" % (path, img.size[0], img.size[1]))
    return out


def preview(imgs, png):
    scale = 2
    W, H = 640 * scale, 480 * scale
    im = Image.new("RGBA", (W, H), (10, 13, 18, 255))

    def U(v):
        return int(round(v * scale))

    def panel(box, c0, c1, border):
        x0, y0, x1, y1 = [U(v) for v in box]
        for i in range(y1 - y0):
            t = i / max(1, (y1 - y0) - 1)
            c = tuple(int(c0[k] + (c1[k] - c0[k]) * t) for k in range(3))
            ImageDraw.Draw(im).line([(x0, y0 + i), (x1, y0 + i)], fill=c)
        ImageDraw.Draw(im).rectangle([x0, y0, x1, y1], outline=border, width=3)

    panel((66, 104, 296, 354), (34, 50, 78), (20, 30, 49), (120, 150, 200))
    panel((344, 104, 574, 354), (72, 36, 33), (45, 22, 20), (190, 120, 110))
    ImageDraw.Draw(im).rectangle([U(220), U(388), U(420), U(418)], fill=(23, 26, 33), outline=(90, 95, 105), width=2)

    def place(name, cx, cy, sz):
        ic = imgs[name].resize((U(sz), U(sz)), Image.LANCZOS)
        im.alpha_composite(ic, (U(cx) - ic.size[0] // 2, U(cy) - ic.size[1] // 2))

    place("coop_ts_allies.tga", 181, 175, 66)
    place("coop_ts_axis.tga", 459, 175, 66)
    place("coop_ts_spec.tga", 250, 403, 22)
    im.save(png)
    print("preview", png)


if __name__ == "__main__":
    imgs = build()
    if "--preview" in sys.argv:
        preview(imgs, sys.argv[sys.argv.index("--preview") + 1])
