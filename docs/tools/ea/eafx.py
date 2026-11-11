"""European Assault particle systems -> MOHAA emitters, built on the player's PC from their own disc.

The level stream carries one property bag per particle system (class ProcParticleType) and one sprite sheet
per texture; the object DB says which systems make up each effects package (Action_CreateParticle) and where
the packages stand (EffectsPackage, placed by eavm). This module turns every package the level uses into
emitter .tik files, a sprite shader file and the sprite images, all written into the converted pak.

What the stock emitter can say is said with stock commands (emit box, velocity ranges, acceleration, life,
rate, size range and end scale, roll and spin, additive or blended sprites, sheet animation). What it cannot
(start and end colour ranges, the alpha curve, velocity and acceleration end ratios, distance and height
fades, preroll, bursts) rides on the engine's "convfx" emitter command, which only acts on converted maps;
an engine without it ignores the command and still shows the stock part.

Our reading of the numbers (not documented anywhere; from the values themselves):
  metres, Z up; EmitRate particles every EmitDelay ticks of 1/30 s; lifetimes in seconds; colours and
  alpha 0..255 with 128 = 1.0; angles in radians, spin in radians per second; sizes are full width/height.
Not carried over: a different end scale for width and height (their mean is used), DepthBias, noise
diffusion, trails, FogMultiplier.

Nothing here is stored in the repository except this code: every output is derived at convert time.
"""
import math
import re
import struct
import zlib

import shpx

T_PARTICLE = 0x472c4c34
T_TEXTURE = 0x1c1d93ac
TICK = 30.0
BURST_ON = 0.25          # seconds the script keeps a one-burst part switched on
BURST_MAX = 128


def _k(name):
    return zlib.crc32(name.encode()) & 0xffffffff


K_FILE = 0x654f240d
K_TEX = 0x81728b86
K_ACC = (0x36356113, 0x41325185, 0xd83b003f)
K_SPIN = (0x8edb31ba, 0xcbd97238)


def _chunks(d):
    n = struct.unpack_from("<I", d, 0x14)[0]
    p = 0x18 + 8 * n
    while p + 16 <= len(d):
        cid, typ, sz, _x = struct.unpack_from("<4I", d, p)
        if sz < 16:
            break
        yield p, cid, typ, sz
        p += sz


def _bag(b):
    cnt = struct.unpack_from("<I", b, 0x10)[0]
    o, out = 0x14, {}
    for _ in range(cnt):
        if o + 12 > len(b):
            break
        k, t, n = struct.unpack_from("<3I", b, o)
        v = b[o + 12:o + 12 + n]
        if t == 1 and n == 4:
            out[k] = struct.unpack("<f", v)[0]
        elif t == 0 and n == 4:
            out[k] = struct.unpack("<i", v)[0]
        elif t == 2:
            out[k] = v.split(b"\0")[0].decode("latin-1")
        else:
            out[k] = tuple(struct.unpack("<%dI" % (n // 4), v[:n & ~3]))
        o += 12 + ((n + 3) & ~3)
    return out


def _base(path):
    return re.split(r"[\\/]", path)[-1].rsplit(".", 1)[0].lower()


class Def:
    def __init__(self, bag):
        self.b = bag
        self.name = _base(bag.get(K_FILE, "") or "")

    def g(self, name, dflt=0.0):
        v = self.b.get(name if isinstance(name, int) else _k(name), dflt)
        return dflt if isinstance(v, (tuple, str)) else v

    def tex(self):
        v = self.b.get(K_TEX)
        return v[0] if isinstance(v, tuple) and v else None


def parse(stream):
    """-> ({def name: Def}, {texture chunk id: (offset, size)})"""
    defs, tex = {}, {}
    for p, cid, typ, sz in _chunks(stream):
        if typ == T_PARTICLE:
            try:
                d = Def(_bag(stream[p:p + sz]))
            except struct.error:
                continue
            if d.name:
                defs.setdefault(d.name, d)
        elif typ == T_TEXTURE:
            tex[cid] = (p, sz)
    return defs, tex


def packages(db):
    """{package (lower-case .xpd base name): [def name, ...] in package order}"""
    out = {}
    for r in db.of("Action_CreateParticle"):
        pkg, xdd = r.s(16), r.s(17)
        if not pkg or not xdd:
            continue
        pkg = _base(pkg).replace("ru1s_", "rus1_")       # two records of one package carry a transposed name
        out.setdefault(pkg, []).append((r.u(15) or 0, _base(xdd)))
    return {k: [n for _i, n in sorted(v)] for k, v in out.items()}


# ------------------------------------------------------------------ sprites
def _resample(rgba, w, h, tw, th):
    if (tw, th) == (w, h):
        return rgba
    out = bytearray(tw * th * 4)
    for y in range(th):
        fy = (y + 0.5) * h / th - 0.5
        y0 = min(h - 1, max(0, int(math.floor(fy))))
        y1 = min(h - 1, y0 + 1)
        wy = min(1.0, max(0.0, fy - y0))
        for x in range(tw):
            fx = (x + 0.5) * w / tw - 0.5
            x0 = min(w - 1, max(0, int(math.floor(fx))))
            x1 = min(w - 1, x0 + 1)
            wx = min(1.0, max(0.0, fx - x0))
            a, b, c, d = (y0 * w + x0) * 4, (y0 * w + x1) * 4, (y1 * w + x0) * 4, (y1 * w + x1) * 4
            o = (y * tw + x) * 4
            for k in range(4):
                top = rgba[a + k] + (rgba[b + k] - rgba[a + k]) * wx
                bot = rgba[c + k] + (rgba[d + k] - rgba[c + k]) * wx
                out[o + k] = int(top + (bot - top) * wy + 0.5)
    return bytes(out)


def tga_bytes(w, h, rgba):
    """uncompressed 32-bit TGA, bottom-up rows"""
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 8)
    rows = []
    for y in range(h - 1, -1, -1):
        b = bytearray(rgba[y * w * 4:(y + 1) * w * 4])
        b[0::4], b[2::4] = b[2::4], b[0::4]
        rows.append(bytes(b))
    return hdr + b"".join(rows)


def _crop(rgba, w, x0, y0, cw, ch):
    return b"".join(rgba[((y0 + y) * w + x0) * 4:((y0 + y) * w + x0 + cw) * 4] for y in range(ch))


def _pow2(v):
    return max(4, 1 << int(round(math.log(max(1.0, v), 2))))


class Sprites:
    def __init__(self, stream, tex, level, files):
        self.stream, self.tex, self.level, self.files, self.tga = stream, tex, level, files, tga_bytes
        self.img, self.shaders, self.order = {}, {}, []

    def image(self, cid):
        if cid not in self.img:
            im = None
            if cid in self.tex:
                p, sz = self.tex[cid]
                o = self.stream.find(b"SHPX", p, p + sz)
                if o >= 0:
                    try:
                        for x in shpx.decode(self.stream, o):
                            if x["rgba"] is not None:
                                im = x
                                break
                    except (struct.error, IndexError, ValueError, AssertionError):
                        im = None
            self.img[cid] = im
        return self.img[cid]

    def shader(self, cid, cols, rows, fps, aspect, additive):
        """shader name of a sprite whose image is `aspect` (width / height) wide, and its image width in pixels"""
        im = self.image(cid)
        if im is None:
            return None, 0
        cols, rows = max(1, cols), max(1, rows)
        fw, fh = im["w"] // cols, im["h"] // rows
        if fw < 1 or fh < 1:
            return None, 0
        # keep the longer side, squeeze the other to the particle's own width : height
        if aspect >= 1.0:
            tw, th = _pow2(max(fw, fh)), _pow2(max(fw, fh) / aspect)
        else:
            tw, th = _pow2(max(fw, fh) * aspect), _pow2(max(fw, fh))
        key = (cid, cols, rows, round(fps, 1) if cols * rows > 1 else 0, tw, th, bool(additive))
        if key not in self.shaders:
            name = "ea_%s_fx_%08x_%dx%d_%s%d" % (self.level, cid, tw, th, "a" if additive else "b", len(self.shaders))
            paths = []
            for fr in range(cols * rows):
                rel = "textures/ea/%s/fx/%08x_%dx%d_%02d.tga" % (self.level, cid, tw, th, fr)
                if rel not in self.files:
                    cell = _crop(im["rgba"], im["w"], (fr % cols) * fw, (fr // cols) * fh, fw, fh)
                    self.files[rel] = self.tga(tw, th, _resample(cell, fw, fh, tw, th))
                paths.append(rel)
            stage = ("animMap %.2f %s" % (max(0.5, fps), " ".join(paths))) if len(paths) > 1 else ("clampmap " + paths[0])
            blend = "blendFunc GL_SRC_ALPHA GL_ONE" if additive else "blendFunc blend"
            self.shaders[key] = name
            self.order.append("%s\n{\n\tcull none\n\tnomipmaps\n\tspriteGen parallel_oriented\n\t{\n\t\t%s\n\t\t%s\n"
                              "\t\trgbGen vertex\n\t\talphaGen vertex\n\t}\n}\n\n" % (name, stage, blend))
        return self.shaders[key], tw


# ------------------------------------------------------------------ one system -> one emitter block
def _f(v):
    s = "%.4f" % v
    s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _rng(lo, hi):
    lo, hi = min(lo, hi), max(lo, hi)
    return ("range %s %s" % (_f(lo), _f(hi - lo))) if hi - lo > 1e-6 else _f(lo)


def _c(v):
    return min(1.0, max(0.0, v / 128.0))


def _lim(v):
    return max(-1.0e6, min(1.0e6, v))


def emitter(d, idx, X, sprites, rate_scale=1.0):
    """-> (text of the originemitter block, on-time class, particle life, live particles)"""
    u, m = X.s, X.m
    g = d.g
    life = max(0.02, g("PartLifetime", 1.0))
    n = max(1, int(g("EmitRate", 1)))
    delay = max(1, int(g("EmitDelay", 1)))
    sys = max(0.0, g("SysLifetime", 0.0))
    eps = TICK / delay
    if sys > 0 and sys <= 0.5:                      # one burst
        burst = min(BURST_MAX, max(1, int(round(sys * TICK / delay))) * n)
        stock_rate, emit, on, live = burst / BURST_ON, (0.001, burst), BURST_ON, burst
    else:
        eps *= rate_scale
        stock_rate, emit, on = eps * n, ((eps, n) if n > 1 else None), (round(sys, 2) if sys > 0 else 0.0)
        live = eps * n * (min(life, sys + 0.1) if sys > 0 else life)
    w0, w1 = abs(g("SizeMinWidth", 1.0)), abs(g("SizeMaxWidth", 1.0))
    h0, h1 = abs(g("SizeMinHeight", 1.0)), abs(g("SizeMaxHeight", 1.0))
    w0, w1 = min(w0, w1), max(w0, w1)
    wm, hm = max(1e-3, (w0 + w1) / 2), max(1e-3, (h0 + h1) / 2)
    additive = int(g("RenderType", 0)) == 0
    shader, tw = sprites.shader(d.tex(), int(g("HorizCount", 1)), int(g("VertCount", 1)), g("UVAnimRate", 0.0),
                                min(16.0, max(1 / 16.0, wm / hm)), additive)
    if shader is None:
        return None, on, life, 0
    es = (g("SizeEndScale", 1.0) + g("SizeEndScaleY", 1.0)) / 2
    L = ["originemitter e%d" % idx, "\t\t("]
    A = L.append
    A("\t\t\tspawnrate %s" % _f(max(0.001, stock_rate)))
    A("\t\t\tmodel %s.spr" % shader)
    c0 = [_c(g("ColorStart" + x, 128)) for x in "RGB"] + [_c(g("ColorStartMax" + x, 128)) for x in "RGB"]
    c1 = [_c(g("ColorEnd" + x, 128)) for x in "RGB"] + [_c(g("ColorEndMax" + x, 128)) for x in "RGB"]
    a0, a1, ae = _c(g("AlphaStart", 128)), _c(g("AlphaStartMax", 128)), _c(g("AlphaEnd", 128))
    fin, fout = min(1.0, max(0.0, g("FadeInStop", 0.0))), min(1.0, max(0.0, g("FadeOutStart", 1.0)))
    A("\t\t\tcolor %s %s %s" % tuple(_f((c0[i] + c0[i + 3] + c1[i] + c1[i + 3]) / 4) for i in range(3)))
    A("\t\t\talpha %s" % _f(max(0.02, (a0 + a1 + ae) / 3)))
    A("\t\t\tlife %s" % _f(life))
    A("\t\t\tscalemin %s" % _f(w0 * u / tw))
    A("\t\t\tscalemax %s" % _f(max(w1, w0 + 1e-4) * u / tw))
    if abs(es - 1.0) > 1e-3:
        A("\t\t\tscalerate %s" % _f((es - 1.0) / life))
    ylo, yhi = sorted((g("LocMinY") * m, g("LocMaxY") * m))
    A("\t\t\toffsetalongaxis %s %s %s" % (_rng(g("LocMinX") * u, g("LocMaxX") * u), _rng(ylo * u, yhi * u),
                                 _rng(g("LocMinZ") * u, g("LocMaxZ") * u)))
    vlo, vhi = sorted((g("VelMinY") * m, g("VelMaxY") * m))
    vel = (g("VelMinX"), g("VelMaxX"), vlo, vhi, g("VelMinZ"), g("VelMaxZ"))
    if any(abs(v) > 1e-6 for v in vel):
        A("\t\t\trandvelaxis %s %s %s" % (_rng(vel[0] * u, vel[1] * u), _rng(vel[2] * u, vel[3] * u), _rng(vel[4] * u, vel[5] * u)))
    acc = (g(K_ACC[0]) * u, g(K_ACC[1]) * u * m, g(K_ACC[2]) * u)
    if any(abs(v) > 1e-6 for v in acc):
        A("\t\t\taccel %s %s %s" % tuple(_f(v) for v in acc))
    r0, r1 = math.degrees(g("RotOffsetMin")), math.degrees(g("RotOffsetMax"))
    if abs(r0) > 1e-3 or abs(r1) > 1e-3:
        A("\t\t\tangles 0 0 %s" % _rng(r0, r1))
    s0, s1 = math.degrees(g(K_SPIN[0])), math.degrees(g(K_SPIN[1]))
    if abs(s0) > 0.5 or abs(s1) > 0.5:
        A("\t\t\tavelocity 0 0 %s" % _rng(s0, s1))
    if fin > 0.01:
        A("\t\t\tfadein %s" % _f(fin * life))
    if fout < 0.99:
        A("\t\t\tfadedelay %s" % _f(fout * life))
    A("\t\t\tfade")
    # ---- the converted-map life curves (engine "convfx"; an engine without it skips these lines) ----
    A("\t\t\tconvfx color " + " ".join(_f(v) for v in c0))
    A("\t\t\tconvfx colorend " + " ".join(_f(v) for v in c1))
    A("\t\t\tconvfx alpha %s %s %s %s %s" % (_f(a0), _f(a1), _f(ae), _f(fin), _f(fout)))
    ve = [g("VelEndRatio" + x, 1.0) for x in "XYZ"]
    ac = [g("AccelEndRatio" + x, 1.0) for x in "XYZ"]
    if any(abs(v - 1.0) > 1e-3 for v in ve):
        A("\t\t\tconvfx velend %s %s %s" % tuple(_f(v) for v in ve))
    if any(abs(v - 1.0) > 1e-3 for v in ac) and any(abs(v) > 1e-6 for v in acc):
        A("\t\t\tconvfx accelend %s %s %s" % tuple(_f(v) for v in ac))
    dist = [_lim(g(x, dv) * u) for x, dv in (("NearClip", 0.0), ("NearFade", 0.0), ("FarFade", 1e9), ("FarClip", 1e9))]
    if dist[1] > 1.0 or 0.0 < dist[3] < 9.0e5:
        A("\t\t\tconvfx dist %s %s %s %s" % tuple(_f(max(0.0, v)) for v in dist))
    hgt = [_lim(g(x, dv) * u) for x, dv in (("HeightMinClip", -1e30), ("HeightMinFade", -1e30),
                                             ("HeightMaxFade", 1e30), ("HeightMaxClip", 1e30))]
    if hgt[1] > -9.0e5 or hgt[2] < 9.0e5:
        A("\t\t\tconvfx height %s %s %s %s" % tuple(_f(v) for v in hgt))
    if emit:
        A("\t\t\tconvfx emit %s %d" % (_f(emit[0]), emit[1]))
    if int(g("PreRoll", 0)) and not sys:
        A("\t\t\tconvfx preroll")
    A("\t\t)")
    return "\n".join(L) + "\n", on, life, live


TIK = """TIKI
// GENERATED on this PC by the European Assault converter from the player's own disc
setup
{
	scale 1.0
	path models/fx/dummy
	skelmodel dummy3.skd
}

init
{
	server
	{
		classname effectentity
		notsolid
		rendereffects +dontdraw
	}
	client
	{
%s	}
}

animations
{
	idle dummy3.skc
	start dummy3.skc
	{
		client
		{
%s		}
	}
	stop dummy3.skc
	{
		client
		{
%s		}
	}
}
"""


def build(stream, db, X, level, files, lines, used=None, log=print, budget=2600):
    """Write the emitters of every effects package into `files`; append the script table to `lines`.
    used: {package name as the script knows it: number of always-on placements} (None = every package once)"""
    defs, tex = parse(stream)
    pk = packages(db)
    sprites = Sprites(stream, tex, level, files)
    want = {n.lower(): (n, c) for n, c in (used or {k: 1 for k in pk}).items()}
    # live particles of everything that burns all the time, to hold the client's particle budget
    total = 0.0
    for low, (_n, cnt) in want.items():
        for dn in pk.get(low, ()):
            d = defs.get(dn)
            if d is not None and not d.g("SysLifetime", 0.0):
                # a system with a far clip stops emitting past it (engine), so it rarely counts in full
                far = d.g("FarClip", 0.0)
                total += ((0.5 if 0.0 < far < 1.0e4 else 1.0) * cnt * max(1, int(d.g("EmitRate", 1))) * TICK
                          / max(1, int(d.g("EmitDelay", 1))) * d.g("PartLifetime", 1.0))
    rate_scale = min(1.0, budget / total) if total > 0 else 1.0
    made, missing = 0, []
    lines.append("\t// ---- particle systems converted from the disc (eafx): parts of each package, on-time, tail ----")
    for low in sorted(want):
        name = want[low][0]
        parts = {}
        for i, dn in enumerate(pk.get(low, ())):
            d = defs.get(dn)
            if d is None:
                continue
            txt, on, life, _live = emitter(d, i, X, sprites, rate_scale)
            if txt is None:
                continue
            p = parts.setdefault(on, {"txt": [], "names": [], "tail": 0.0})
            p["txt"].append(txt)
            p["names"].append("e%d" % i)
            p["tail"] = max(p["tail"], life)
        if not parts:
            missing.append(name)
            continue
        safe = re.sub(r"[^a-z0-9_]", "_", low)
        for k, on in enumerate(sorted(parts), 1):
            p = parts[on]
            rel = "models/emitters/ea_%s_%s_%d.tik" % (level, safe, k)
            files[rel] = (TIK % ("".join(p["txt"]),
                                 "".join("\t\t\tenter emitteron %s\n" % e for e in p["names"]),
                                 "".join("\t\t\tenter emitteroff %s\n" % e for e in p["names"]))).encode("latin-1")
            lines.append('\tlevel.ea_fxg_mdl["%s_%d"] = "emitters/ea_%s_%s_%d.tik"' % (name, k, level, safe, k))
            lines.append('\tlevel.ea_fxg_on["%s_%d"] = %s' % (name, k, _f(on)))
            lines.append('\tlevel.ea_fxg_tail["%s_%d"] = %s' % (name, k, _f(p["tail"])))
            made += 1
        lines.append('\tlevel.ea_fxg["%s"] = %d' % (name, len(parts)))
    files["scripts/ea_%s_fx.shader" % level] = ("// GENERATED on this PC by the European Assault converter\n\n"
                                                + "".join(sprites.order)).encode("latin-1")
    log("eafx: %d packages -> %d emitter files, %d sprite shaders, always-on load %.0f particles (rate x%.2f)%s"
        % (len(want) - len(missing), made, len(sprites.order), total, rate_scale,
           ("; no systems for " + ", ".join(missing)) if missing else ""))
    return {"packages": len(want) - len(missing), "tiks": made, "shaders": len(sprites.order),
            "load": round(total), "rate_scale": round(rate_scale, 3), "missing": missing}
