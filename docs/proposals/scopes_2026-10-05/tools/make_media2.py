"""make_media2.py - media of the 2026-10-12 integrator pass (run_scopes2.py sessions in G:/mohaa-hudfeed/runs).

    python make_media2.py gifs      one GIF per optic from the "ease" session (480x270)
    python make_media2.py sheets    the per-resolution stills, the housing probe, gl1 / no-post / no-pak, MP

GIF timing follows run_scopes2.ease (fixedtime 16): hip 3 + scope in 26 frames and scope out 22 frames are every game
frame (16 ms) and are shown at every 2nd frame, 30 ms each (real time); the shot is 4 frames at 16 ms; the bolt cycle
is 20 frames taken every 3rd game frame (48 ms), shown at 50 ms. A caption names the segment.
"""
import os, sys, glob
from PIL import Image, ImageDraw, ImageFont

RUNS = "G:/mohaa-hudfeed/runs"
HERE = os.path.dirname(os.path.abspath(__file__))
MEDIA = os.path.join(os.path.dirname(HERE), "media")
GUNS = [("kar98s", "zf39_kar98k"), ("g43s", "zf4_g43"), ("springfield", "m73b1_springfield"), ("garands", "m84_garand"),
        ("mosins", "pu_mosin"), ("enfields", "no32_leeenfield"), ("arisakas", "type97_arisaka"),
        ("carcanos", "italian_carcano")]
SEG = [("hip", 3, 16), ("scope in", 26, 16), ("shot", 4, 16), ("bolt", 20, 48), ("scope out", 22, 16)]


def font(sz):
    for f in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, sz)
    return ImageFont.load_default()


def gifs(sess="sc_ease", w=480):
    h = w * 9 // 16
    f = font(15)
    for gun, name in GUNS:
        fs = sorted(glob.glob(os.path.join(RUNS, sess, "e__%s__*.jpg" % gun)))
        if len(fs) != sum(c for _, c, _ in SEG):
            print("skip", gun, len(fs))
            continue
        lay = []
        for nm, c, ms in SEG:
            lay += [(nm, ms)] * c
        out, dur = [], []
        k = 0
        while k < len(fs):
            nm, ms = lay[k]
            step = 2 if (ms == 16 and nm != "shot") else 1
            im = Image.open(fs[k]).convert("RGB").resize((w, h), Image.LANCZOS)
            d = ImageDraw.Draw(im)
            x = w - 10 - d.textlength(nm, font=f)
            d.text((x + 1, h - 29), nm, fill=(0, 0, 0), font=f)
            d.text((x, h - 30), nm, fill=(235, 235, 235), font=f)
            out.append(im.quantize(colors=128, method=Image.MEDIANCUT, dither=Image.NONE))
            dur.append(30 if ms == 16 else 50)
            k += step
        dur[-1] = 900
        dst = os.path.join(MEDIA, "v2_scope_%s.gif" % name)
        out[0].save(dst, save_all=True, append_images=out[1:], duration=dur, loop=0, optimize=True, disposal=1)
        print("gif", dst, len(out), "frames", "%.1f MB" % (os.path.getsize(dst) / 1e6))


def grid(fs, dst, tw, cols, labels=None, crop=None):
    tiles = []
    for k, p in enumerate(fs):
        im = Image.open(p).convert("RGB")
        if crop:
            im = im.crop(crop(im.size))
        th = int(round(tw * im.size[1] / im.size[0]))
        im = im.resize((tw, th), Image.LANCZOS)
        if labels:
            d = ImageDraw.Draw(im)
            f = font(15)
            d.text((7, 5), labels[k], fill=(0, 0, 0), font=f)
            d.text((6, 4), labels[k], fill=(255, 235, 160), font=f)
        tiles.append(im)
    if not tiles:
        print("no files for", dst)
        return
    th = max(t.size[1] for t in tiles)
    rows = (len(tiles) + cols - 1) // cols
    S = Image.new("RGB", (cols * tw + (cols - 1) * 4, rows * th + (rows - 1) * 4), (16, 16, 16))
    for k, t in enumerate(tiles):
        S.paste(t, ((k % cols) * (tw + 4), (k // cols) * (th + 4)))
    S.save(dst, quality=90)
    print("sheet", dst, S.size)


OPT = {"kar98s": "ZF39 4x - Kar98k", "g43s": "ZF4 4x - G43", "springfield": "M73B1 2.5x - Springfield",
       "garands": "M84 2.2x - Garand", "mosins": "PU 3.5x - Mosin", "enfields": "No.32 3x - Lee-Enfield",
       "arisakas": "Type 97 2.5x - Arisaka", "carcanos": "Italian 2.2x - Carcano"}


def sheets():
    order = [g for g, _ in GUNS]
    for sess, pre, nm, tw, cols in (("sc_res_1280x720", "r1280x720", "v2_stills_1280x720.jpg", 640, 4),
                                    ("sc_res_1920x1080", "r1920x1080", "v2_stills_1920x1080.jpg", 640, 4),
                                    ("sc_res_1024x768", "r1024x768", "v2_stills_1024x768_4x3.jpg", 512, 4),
                                    ("sc_res_1920x804", "r1920x804", "v2_stills_1920x804_ultrawide.jpg", 800, 2),
                                    ("sc_gl1_1280x720", "g1280x720", "v2_stills_gl1_1280x720.jpg", 640, 4)):
        fs = [os.path.join(RUNS, sess, "%s__%s__1in.png" % (pre, g)) for g in order]
        fs = [p for p in fs if os.path.exists(p)]
        grid(fs, os.path.join(MEDIA, nm), tw, cols, [OPT[os.path.basename(p).split("__")[1]] for p in fs])
    # one rifle through its stages (Kar98k, 1280x720): hip, scoped, just after the shot, after the bolt, out
    st = ["0hip", "1in", "2fire", "3bolt", "4out"]
    fs = [os.path.join(RUNS, "sc_res_1280x720", "r1280x720__kar98s__%s.png" % s) for s in st]
    grid([p for p in fs if os.path.exists(p)], os.path.join(MEDIA, "v2_stages_kar98k.jpg"), 512, 5,
         ["hip", "scoped", "just after the shot", "bolt cycled", "scoped out"])
    # the housing ("grey smudge") probe
    # same frame, three housing levels; then the view turned, old level, the same lifted x6 so the eye can see it, and all of it
    v = os.path.join(RUNS, "sc_variants")
    tmp = os.path.join(MEDIA, "_boost.png")
    im = Image.open(os.path.join(v, "v__05_pan_outer097.png")).convert("RGB")
    im.point(lambda p: min(255, p * 6)).save(tmp)
    grid([os.path.join(v, "v__04_outer097.png"), os.path.join(v, "v__02_outer100.png"), os.path.join(v, "v__03_outer000.png"),
          os.path.join(v, "v__05_pan_outer097.png"), tmp, os.path.join(v, "v__06_pan_outer000.png")],
         os.path.join(MEDIA, "v2_housing_probe.jpg"), 640, 3,
         ["old default: housing keeps 3% of the blurred frame", "new default: flat black (r_ppScopeOuter 1)",
          "r_ppScopeOuter 0: what was being blurred - this frame", "view turned, old 3% housing",
          "the same still, brightness x6: the smudge", "view turned, r_ppScopeOuter 0: it follows the frame"])
    os.remove(tmp)
    # two clients, gl1, no post chain, no pak
    m = os.path.join(RUNS, "sc_mp")
    grid([os.path.join(m, n) for n in ("mp__h1_host_scoped_at_joiner.png", "mp__j1_sees_host_scoped.png",
                                       "mp__j3_joiner_scoped.png", "mp__h4_host_sees_joiner_scoped.png")],
         os.path.join(MEDIA, "v2_two_clients.jpg"), 640, 2,
         ["host: scoped at the second player", "second player's screen meanwhile", "second player (remote client) scoped",
          "host's screen meanwhile"])
    fs = [os.path.join(RUNS, "sc_gl1_1280x720", "g1280x720__kar98s__1in.png"),
          os.path.join(RUNS, "sc_gl1_1280x720", "g1280x720__retail_in.png"),
          os.path.join(RUNS, "sc_nopost", "np__kar98s__1in.png"),
          os.path.join(RUNS, "sc_nopak_opengl2", "np_opengl2__1in.png"),
          os.path.join(RUNS, "sc_nopak_opengl1", "np_opengl1__1in.png")]
    grid([p for p in fs if os.path.exists(p)], os.path.join(MEDIA, "v2_fallbacks.jpg"), 512, 5,
         ["old renderer (gl1): 2D fallback", "gl1, cg_hzmScope 0: retail", "gl2, post chain off: 2D fallback",
          "gl2, scopes pak missing: retail", "gl1, scopes pak missing: retail"])


if __name__ == "__main__":
    {"gifs": gifs, "sheets": sheets}[sys.argv[1]](*sys.argv[2:])
