#!/usr/bin/env python3
"""gen_east_lift.py - exposure lift for East's WW1 weapon imports (v1.10.64, wpnfix).

    python docs/tools/gen_east_lift.py stats     # luminance p50 / p90 of every East sheet against the stock guns
    python docs/tools/gen_east_lift.py build     # write the lifted sheets into the fixes pak sources + pin their bases
    python docs/tools/gen_east_lift.py check     # exit 1 when a lifted sheet no longer matches what build would write

WHY. The WW1 imports (G98, SMLE, MP18, Webley Mk VI, C96 trench, M1903, G98 scoped, P14, Lewis) ship their pack's own
sheets, authored for a brighter engine: flat, low-key art (the G98 stock sheet's median is 37/255, the stock Kar98's
HRRTM sheet carries grain and highlights up to 200+). In a map the light grid's overbright still lifts them a little;
in a menu preview (the Armory hero, the attic weapon viewer) the model is lit fullbright = the texture as authored,
so they sat flat against the dark backdrop and read as see-through (measured 2026-11-04: r_fastentlight, r_light_nolight
and a HUD ambient cvar all changed NOTHING - the lighting is already 1:1; it is the art).

WHAT. Per sheet, a luminance-only lift (hue and saturation kept): a gain so the sheet's 90th percentile reaches the stock
guns' typical 90th percentile, capped at x1.8, then a mild gamma for the shadows. Pure function of the base sheet, so
`check` can re-derive every output. Sheets ship in zzzzzzzzzzzzzzzz_coop_wpnfix.pk3 (docs/tools/gen_wpnfix_pak.py), which
out-sorts every coop pak (some of these sheets already ship in fixes / fixes2, where an override would be shadowed);
each base - the copy the game loads today - is pinned by md5 in wpnfix_manifest.json. The mod tree keeps its copy.
"""
import hashlib
import io
import json
import os
import re
import shutil
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.environ.get("HZM_MOD") or os.path.join(ROOT, "hzm-mohaa-coop-mod")
FIX = os.path.join(ROOT, "docs", "tools", "assets", "fixes")
FIXBASE = os.path.join(ROOT, "docs", "tools", "assets", "fixes_base")
MANIFEST = os.path.join(FIX, "fixes_manifest.json")
EPOCH_TICKS = 621355968000000000

# the East WW1 imports: tik -> their private texture dirs are read from the tik's shaders (scripts/coop_<x>.shader)
EAST_TIKS = ["kar98_g98", "springfield_smlescope", "mp40_mp18", "colt45_colt1911w", "mauser_c96_c96trench",
             "springfield_m1903", "KAR98sniper_g98scope", "enfield_p14", "bar_bar1918", "coop_lewis"]
# stock reference sheets (mod tree / HRRTM art the stock rifles show): their p90 is the target exposure
STOCK_P90 = 70           # measured 2026-11-08: stock kar98 57, m1 garand 85, colt45 67, mp40 70, springfield 58 (sheet p90)
GAIN_MAX = 1.8
GAMMA = 0.92


def lum_hist(im):
    g = im.convert("L")
    g.thumbnail((512, 512))
    return g.histogram()


def pct(h, q):
    n, c = sum(h), 0
    for i, v in enumerate(h):
        c += v
        if c >= n * q:
            return i
    return 255


def shader_textures():
    """every texture the East tiks' surfaces map, as mod-tree relpaths (case as on disk)"""
    shaders = {}
    for p in os.listdir(os.path.join(MOD, "scripts")):
        if p.lower().startswith("coop_") and p.endswith(".shader"):
            t = io.open(os.path.join(MOD, "scripts", p), encoding="latin-1").read()
            for m in re.finditer(r"(?ms)^(\w+)\s*\{(.*?)^\}", t):
                shaders[m.group(1).lower()] = re.findall(r"(?mi)^\s*map\s+(\S+)", m.group(2))
    out = set()
    for tk in EAST_TIKS:
        p = os.path.join(MOD, "models", "weapons", tk + ".tik")
        if not os.path.exists(p):
            p = os.path.join(FIX, "models", "weapons", tk + ".tik")
        if not os.path.exists(p):
            continue
        t = io.open(p, encoding="latin-1").read()
        for sh in re.findall(r"(?mi)^\s*surface\s+\S+\s+shader\s+(\S+)", t):
            for m in shaders.get(sh.lower(), []):
                if not m.lower().startswith("textures/coop_"):
                    continue                       # shared stock art (m1clip, static_mg42 ...) is not East's
                base = os.path.join(MOD, *m.split("/"))
                d, f = os.path.split(base)
                if os.path.isdir(d):
                    for g in os.listdir(d):
                        if g.lower() == f.lower():
                            out.add(os.path.relpath(os.path.join(d, g), MOD).replace(os.sep, "/"))
    return sorted(out)


def lift(data, ext):
    im = Image.open(io.BytesIO(data))
    mode = im.mode
    rgb = im.convert("RGB")
    h = lum_hist(rgb)
    p90 = max(pct(h, 0.90), 1)
    gain = min(GAIN_MAX, max(1.0, STOCK_P90 / float(p90)))
    lut = [min(255, int(round(255.0 * ((i / 255.0) ** GAMMA) * gain))) for i in range(256)]
    # luminance lift with hue kept: scale each pixel's RGB by lut(L)/L
    px = rgb.load()
    out = Image.new("RGB", rgb.size)
    po = out.load()
    w, hh = rgb.size
    for y in range(hh):
        for x in range(w):
            r, g, b = px[x, y]
            L = (r * 299 + g * 587 + b * 114) // 1000
            k = lut[L] / float(L) if L else 1.0
            po[x, y] = (min(255, int(r * k + 0.5)), min(255, int(g * k + 0.5)), min(255, int(b * k + 0.5)))
    if mode == "RGBA":
        out.putalpha(im.getchannel("A"))
    buf = io.BytesIO()
    if ext in (".jpg", ".jpeg"):
        out.save(buf, "JPEG", quality=92, subsampling=0)
    else:
        out.save(buf, "TGA")
    return buf.getvalue(), gain, p90


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gen_wpnfix_pak as wp
    rels = shader_textures()
    man = wp.load_manifest()
    fails = []
    for rel in rels:
        pin = man.get(rel)
        dst = os.path.join(wp.SRC, *rel.split("/"))
        c = wp.carriers(rel)
        if not c:
            fails.append(rel + ": no base copy ships")
            continue
        base = c[-1][1]                       # the copy the game loads today (mod tree, fixes, fixes2 ...)
        out, gain, p90 = lift(base, os.path.splitext(rel)[1].lower())
        if mode == "stats":
            print("%-52s p90 %3d gain x%.2f  (base %s)" % (rel, p90, gain, c[-1][0]))
            continue
        if mode == "build":
            man[rel] = {"base": c[-1][0], "base_md5": hashlib.md5(base).hexdigest(), "by": "gen_east_lift.py"}
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "wb").write(out)
        elif not os.path.exists(dst) or open(dst, "rb").read() != out:
            fails.append(rel)
    if mode == "build":
        open(wp.MANIFEST, "w", encoding="utf-8", newline="\n").write(json.dumps(man, indent=2, sort_keys=True) + "\n")
        print("east lift: %d sheets written to the wpnfix pak sources (run gen_wpnfix_pak.py build)" % len(rels))
    elif mode == "check":
        for f in fails:
            print("STALE", f)
        print("east lift: %d sheets, %d stale" % (len(rels), len(fails)))
        return 1 if fails else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
