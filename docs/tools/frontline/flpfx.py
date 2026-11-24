#!/usr/bin/env python3
"""Frontline particle systems with the disc's OWN sprites and numbers (decode audit 2026-11-22, gap 3). Our code,
stdlib only; runs on the PLAYER's PC inside the converter, output only into the player's own converted pak.

Decode (H:/hzm_work/codedecode/CODE_FINDINGS_fl_1_1_audit.md part 2, from the emitter's native getters, vtable
0x1302e0): a particle system is a 240-byte kind-9 record - placed ones in .bpd section 3, the by-type templates in
section 4 (type hash = word 18 = CRC32 of the template's name, names in section 8). Byte offsets into the record:
  +0x71 RGB / +0x74 A  start colour A      +0x75 RGB / +0x78 A  start colour B   (a particle starts between A and B)
  +0x79 blend (1 additive, else alpha)     +0x7a / +0x7d RGB    end colours A / B (+0x80 end alpha A)
  +0x82 s16 particles per emission (x0.7 when > 1, x0.4 when > 10)   +0x84 s16 emission period, ticks (60 Hz)
  +0x88 f32 emit duration s (0 = for ever)  +0x8c seed               +0x90..0xa4 spawn box (two corners, m)
  +0xa8..0xbc velocity range (m/s)          +0xc0..0xc8 acceleration (m/s^2, the system's own axes)
  +0xcc / +0xd0 start size range (m)        +0xd4 / +0xd8 end size range (m, x0.7 at init)
  +0xe0 particle life (s)                   +0xe4 / +0xe8 spin range (rad/s)    +0xec sprite = byte offset of an
  SHPX texture in the .bpd itself; section 2 lists the 78 of them (all decode with shpx.decode).
CREATEEXPLOSION spawns no particles and plays no sound: each blast's look is its script's own
CREATEPARTICLESYSTEMBYTYPE calls (fl_levels.json "pfx_bytype": class -> [type hash, dx, dy, dz]).

Readings settled by eye against the emulator frames (READING below): alpha bytes = transparency, colour 0xff = 1.0,
size = radius. MOHAA's emitter holds one colour and fades alpha linearly to 0, so a system's colour is its time mean
and its fade delay gives the same mean opacity as the original's start -> end alpha."""
import math
import struct

import shpx


def _f(r, o):
    return struct.unpack_from("<f", r, o)[0]


def fields(raw):
    """the decoded numbers of one 240-byte particle record (placed kind-9 or section-4 template)"""
    r = raw
    pe = struct.unpack_from("<h", r, 0x82)[0]
    pe_s = pe * (0.4 if pe > 10 else 0.7 if pe > 1 else 1.0)
    per = struct.unpack_from("<h", r, 0x84)[0]
    rng = lambda o: [tuple(sorted((_f(r, o + 4 * i), _f(r, o + 12 + 4 * i)))) for i in range(3)]   # noqa: E731
    c = lambda o: tuple(r[o:o + 3])                                                              # noqa: E731
    return {"hash": struct.unpack_from("<I", r, 0x48)[0], "rgb_a": c(0x71), "a_a": r[0x74], "rgb_b": c(0x75),
            "a_b": r[0x78], "blend": r[0x79], "rgb_end_a": c(0x7a), "rgb_end_b": c(0x7d), "a_end": r[0x80],
            "per_emit": pe, "period": per, "rate": (pe_s * 60.0 / per) if per > 0 else 0.0, "dur": _f(r, 0x88),
            "box": rng(0x90), "vel": rng(0xa8), "acc": (_f(r, 0xc0), _f(r, 0xc4), _f(r, 0xc8)),
            "size0": tuple(sorted((_f(r, 0xcc), _f(r, 0xd0)))),
            "size1": tuple(sorted((_f(r, 0xd4) * 0.7, _f(r, 0xd8) * 0.7))),
            "life": _f(r, 0xe0), "spin": (_f(r, 0xe4), _f(r, 0xe8)),
            "sprite": struct.unpack_from("<I", r, 0xec)[0]}


def templates(L):
    """{type hash: (name, raw 240 bytes)} from .bpd section 4, named through section 8"""
    d = L._bpd()
    sec = L.bpd_sections()
    o4, n4 = sec[4]
    raws = {}
    for k in range(n4):
        raw = d[o4 + 240 * k:o4 + 240 * (k + 1)]
        raws[o4 + 240 * k] = raw
    out = {}
    o8, n8 = sec[8]
    for k in range(n8):
        no, to = struct.unpack_from("<2I", d, o8 + 8 * k)
        raw = raws.get(to)
        if raw is None or no >= len(d):
            continue
        name = d[no:d.index(b"\0", no)].decode("latin-1")
        h = struct.unpack_from("<I", raw, 0x48)[0]
        out[h] = (name, raw)          # h == CRC32(name) on all 244 of 1_1 (codedecode part 2)
    return out


def write_sprites(L, files, level, log=print):
    """the 78 particle sprites of .bpd section 2 -> textures/fl/<level>/pfx/p<offset>.tga + one sprite shader each
    (alpha-blended and additive versions); returns {offset: (shader base name, width)}"""
    d = L._bpd()
    o2, n2 = L.bpd_sections()[2]
    import flchar
    out, sh = {}, []
    for off in struct.unpack_from("<%dI" % n2, d, o2):
        try:
            im = next(shpx.decode(d, off))
        except Exception as e:      # noqa: BLE001 - a sprite that does not decode is left out (its systems keep ours)
            log("flpfx: sprite at %d skipped (%s)" % (off, e))
            continue
        rel = "textures/fl/%s/pfx/p%d.tga" % (level, off)
        files[rel] = flchar.tga(im["w"], im["h"], im["rgba"])
        base = "fl%s_pfx%d" % (level.replace("_", ""), off)
        for suf, bf in (("", "blend"), ("_add", "add")):
            sh.append("%s%s\n{\n\tcull none\n\tspriteGen parallel_oriented\n\t{\n\t\tmap %s\n\t\tblendfunc %s\n"
                      "\t\trgbGen vertex\n\t\talphaGen vertex\n\t}\n}\n\n" % (base, suf, rel, bf))
        out[off] = (base, im["w"])
    if sh:
        files["scripts/fl_%s_pfx.shader" % level] = "".join(sh).encode("latin-1")
    log("flpfx: %d particle sprites" % len(out))
    return out


def _rv(lo, hi, s):
    lo, hi = lo * s, hi * s
    if abs(hi - lo) < 0.05:
        return "%.1f" % ((lo + hi) / 2.0)
    return "range %.1f %.1f" % (lo, hi - lo)


# the readings settled by the camera pass against the emulator frames (2026-11-23, FIDELITY.md "Decode audit gap 3"):
# colour 0xff = 1.0 (0x80 = 1.0 drew white dust and grey columns where the original's are near black), the alpha
# bytes as transparency (as opacity the mine / bomb smoke, alpha 0-1, would not show at all; the original's does), the
# size fields as a radius (x2 = the sprite's full width: the bomb-site and roster columns and the bomb dust match the
# references only so), rate = the code's per emission x0.7 / x0.4 x 60 / period (no frame tells the scaled from the
# raw count; the scaling is read from the native code). The other values exist so a camera pass can compare them
READING = {"col": "avg255", "alp": "trans", "rate": "scaled", "size": 2.0}
# [hotfix 1.10.91, sohotfix] per-template exceptions to READING, each with its evidence. The small-mine set
# (LandMineTriggerParent, also the crate break's smoke): at the emulator's real-speed frames of the jeep ambush
# (ref_xemu clips/jeep e_sheet / w_sheet / k_sheet: the double blast at the wreck seen through the arch +4..+92 ticks
# after it, the bump mine east) the original draws no dirt burst and no smoke wall - the wreck stays clear - while
# the "trans" reading drew both at full opacity (52 sprites of ~2.4 m for 4.9 s: a grey wall over the arch for ~3 s;
# hotfix s_rel/mine_sheet.jpg). Their alpha bytes are 0..8; read as opacity (0x80 = 1.0) they are near invisible,
# which is what the frames show. The shrapnel specks (alpha 107 / 172) keep the default reading.
TEMPLATE_READING = {"ExpSmDirt_Fire1": {"alp": "opac128"}, "ExpSmDirt_Smoke1": {"alp": "opac128"}}
BURST_MAX_S = 0.4      # a system that emits for at most this long is one burst (anim enter originspawn), not an emitter


def look(f, opt=None):
    """(rgb, start opacity, fade delay as a fraction of life, particles per second) under the readings in opt.
    col: avg255 = the mean of the start and end colour ranges (the colour drifts start -> end over the life; MOHAA's
    emitter holds one colour, so the time mean), 0xff = 1.0; avg128 = the same with 0x80 = 1.0; start128 = start only.
    alp: trans = the bytes as transparency (0 = opaque); opac128 = opacity, 0x80 = 1.0.
    rate: scaled = per emission (x0.7 > 1, x0.4 > 10) x 60 / period; raw = without the x0.7 / x0.4."""
    o = dict(READING, **(opt or {}))
    s0 = [(f["rgb_a"][i] + f["rgb_b"][i]) / 2.0 for i in range(3)]
    s1 = [(f["rgb_end_a"][i] + f["rgb_end_b"][i]) / 2.0 for i in range(3)]
    if o["col"] == "start128":
        rgb = [c / 128.0 for c in s0]
    elif o["col"] == "avg255":
        rgb = [(s0[i] + s1[i]) / 2.0 / 255.0 for i in range(3)]
    else:
        rgb = [(s0[i] + s1[i]) / 2.0 / 128.0 for i in range(3)]
    rgb = [min(1.0, c) for c in rgb]
    a0b, a1b = (f["a_a"] + f["a_b"]) / 2.0, (f["a_end"] + f["a_b"]) / 2.0     # end alpha B = start alpha B (decode)
    if o["alp"] == "opac128":
        a0, a1 = min(1.0, a0b / 128.0), min(1.0, a1b / 128.0)
    else:
        a0, a1 = 1.0 - a0b / 255.0, 1.0 - a1b / 255.0
    a0 = max(0.02, a0)
    # MOHAA fades linearly to 0 from fadedelay to the end of the life; a delay of life x a1/a0 gives the same mean
    # opacity as the original's linear a0 -> a1
    fd = min(1.0, max(0.0, a1 / a0))
    pe = f["per_emit"]
    if o["rate"] == "raw":
        rate = pe * 60.0 / f["period"] if f["period"] > 0 else 0.0
    else:
        rate = f["rate"]
    return rgb, min(1.0, a0), fd, rate


def emitter_tik(f, spr, X, note="", opt=None):
    """one system -> a TIKI (stock syntax: models/emitters/tehao_fireSmoke_long.tik). spr = (shader, width): a sprite
    is drawn at its image width x scale units (tr_sprite.c), so scale = size (m) x X.s / width. A system that emits
    for at most BURST_MAX_S is one burst in the "start" animation (count = rate x duration; a script_model carrier
    draws a one-shot only from an animation's enter commands, TRAPS bug-2507); others are an origin emitter that
    "start" turns on and "stop" turns off (the map stops it after the system's emit duration, 0 = never)"""
    s, m = X.s, (-1.0 if X.m < 0 else 1.0)
    shader, px = spr
    if f["blend"] == 1:
        shader += "_add"
    life = f["life"] if f["life"] > 0 else 1.0
    k = dict(READING, **(opt or {}))["size"]
    s0 = [v * k * s / float(px) for v in f["size0"]]
    s1 = [v * k * s / float(px) for v in f["size1"]]
    a0, a1 = sum(s0) / 2.0, sum(s1) / 2.0
    srate = (a1 / a0 - 1.0) / life if a0 > 0 else 0.0
    rgb, alpha, fd, rate = look(f, opt)
    rate = max(0.1, rate)
    burst = 0 < f["dur"] <= BURST_MAX_S

    def ax(rng, k):
        lo, hi = rng[k]
        if k == 1 and m < 0:
            lo, hi = -hi, -lo
        return _rv(lo, hi, s)
    em = ["\t\t\t\tcount %d" % max(1, int(round(rate * f["dur"])))] if burst else ["\t\t\tspawnrate %.2f" % rate]
    em += ["model %s.spr" % shader, "color %.2f %.2f %.2f" % tuple(rgb), "alpha %.2f" % alpha, "life %.2f" % life,
           "scalemin %.3f" % max(0.001, min(s0)), "scalemax %.3f" % max(0.001, max(s0))]
    if abs(srate) > 0.0005:
        em.append("scalerate %.4f" % srate)
    em.append("offset " + " ".join(ax(f["box"], k) for k in range(3)))
    em.append("randvel " + " ".join(ax(f["vel"], k) for k in range(3)))
    acc = (f["acc"][0] * s, f["acc"][1] * s * m, f["acc"][2] * s)
    if any(abs(c) > 0.05 for c in acc):
        em.append("accel %.1f %.1f %.1f" % acc)
    spin = max(abs(f["spin"][0]), abs(f["spin"][1])) * 57.2958
    if spin > 0.5:
        em.append("avelocity 0 0 crandom %.0f" % spin)
    if fd < 0.999:
        em.append("fadedelay %.2f" % (fd * life))
    ind = "\t\t\t\t" if burst else "\t\t\t"
    em = [em[0]] + [ind + x for x in em[1:]]
    head = ["TIKI", "// GENERATED on this PC by docs/tools/frontline/flpfx.py from a particle system on the player's own disc",
            "// (its own sprite and numbers%s). Regenerated by the converter." % (": " + note if note else ""),
            "setup", "{", "\tscale 1.0", "\tpath models/fx/dummy", "\tskelmodel dummy3.skd", "}", ""]
    srv = ["\tserver", "\t{", "\t\tclassname effectentity", "\t\tnotsolid", "\t\trendereffects +dontdraw", "\t}"]
    if burst:
        return "\n".join(head + [
            "init", "{", *srv, "\tclient", "\t{", "\t\tcache %s.spr" % shader, "\t}", "}", "",
            "animations", "{", "\tidle dummy3.skc", "\tstart dummy3.skc", "\t{", "\t\tclient", "\t\t{",
            "\t\t\tenter originspawn", "\t\t\t(", *em, "\t\t\t)", "\t\t}", "\t}", "\tstop dummy3.skc", "}", ""])
    return "\n".join(head + [
        "init", "{", *srv, "\tclient", "\t{", "\t\tcache %s.spr" % shader, "\t\toriginemitter flpfx", "\t\t(", *em,
        "\t\t)", "\t}", "}", "", "animations", "{", "\tidle dummy3.skc", "\tstart dummy3.skc", "\t{", "\t\tclient",
        "\t\t{", "\t\t\tenter emitteron flpfx", "\t\t}", "\t}", "\tstop dummy3.skc", "\t{", "\t\tclient", "\t\t{",
        "\t\t\tenter emitteroff flpfx", "\t\t}", "\t}", "}", ""])


def build(L, X, files, level, spec, lines, log=print):
    """spec = fl_levels.json "pfx_bytype" {class: [[hash hex, dx, dy, dz], ...]}: every template a class's script
    creates -> models/emitters/fl_<level>_pt_<hash>.tik, and per class level.fl_bt_*[class][k] (tik, offset in map
    units along the object's own axes, emit duration, particle life). The placed kind-9 records get a disc-sprite
    twin too: level.fl_pfx_disc[rec] (the mission picks it with coop_flDiscFx 1)."""
    spr = write_sprites(L, files, level, log)
    if not spr:
        return
    tpl = templates(L)
    made = {}

    def tik_for(h):
        if h in made:
            return made[h]
        if h not in tpl:
            made[h] = None
            return None
        name, raw = tpl[h]
        f = fields(raw)
        if f["sprite"] not in spr:
            made[h] = None
            return None
        rel = "models/emitters/fl_%s_pt_%08x.tik" % (level, h)
        files[rel] = emitter_tik(f, spr[f["sprite"]], X, name, TEMPLATE_READING.get(name)).encode("latin-1")
        made[h] = (rel, f)
        return made[h]
    for cls, rows in sorted(spec.items()):
        if cls.startswith("_"):
            continue
        k = 0
        for hh, dx, dy, dz in rows:
            t = tik_for(int(hh, 16))
            if not t:
                continue
            k += 1
            rel, f = t
            lines.append('\tlevel.fl_bt_tik["%s"][%d] = "%s"' % (cls, k, rel))
            lines.append('\tlevel.fl_bt_off["%s"][%d] = ( %.0f %.0f %.0f )' % (cls, k, dx * X.s, dy * X.s * X.m,
                                                                             dz * X.s))
            lines.append('\tlevel.fl_bt_dur["%s"][%d] = %.2f' % (cls, k, f["dur"]))
            lines.append('\tlevel.fl_bt_life["%s"][%d] = %.2f' % (cls, k, f["life"]))
        lines.append('\tlevel.fl_bt_n["%s"] = %d' % (cls, k))
    n = 0
    for e in L.entities():
        if len(e["raw"]) < 240 or struct.unpack_from("<I", e["raw"], 12)[0] != 9:
            continue
        f = fields(e["raw"][:240])
        if f["sprite"] not in spr:
            continue
        rel = "models/emitters/fl_%s_pd%d.tik" % (level, e["i"])
        files[rel] = emitter_tik(f, spr[f["sprite"]], X, "placed record %d" % e["i"]).encode("latin-1")
        lines.append('\tlevel.fl_pfx_disc[%d] = "%s"' % (e["i"], rel))
        n += 1
    log("flpfx: %d by-type templates for %d classes, %d placed systems on their own sprites"
        % (len([v for v in made.values() if v]), len([c for c in spec if not c.startswith("_")]), n))
