#!/usr/bin/env python3
"""European Assault level data -> maps/coop_ea_<level>_data.scr, generated LOCALLY by the BYO converter from the
player's own disc (Frontline's flpack.py pattern). Our own code. Nothing it writes is shipped.

Reads: the level's strings.viv (objective text, by the keys ea_levels.json lists) and the level_a.str object
database (eadb.DB: placements by NAME, which ea_levels.json references). Positions are converted to BSP
units with the converter's transform X and moved to the nearest free standing spot on the collision (flgeom).

level vars written (single frame, no waits):
  level.ea_text[key]              disc string for a key (MO_PrimaryAdd ...)
  level.ea_pos[key]               named placement (start, railgun, tower, ...)
  level.ea_axis[i] / ea_axis_n    German spawn points      level.ea_ally[i] / ea_ally_n   Russian spawn points
  level.ea_start / ea_start_yaw   player start
"""
import math
import re

import eadb
import eavm
import eastrings

SPAWN_RX = re.compile(r"NPCSpawnPoint_", re.I)
ALLY_RX = re.compile(r"Allie|Ally|Partisan|Russ|Officer_Jumpinto", re.I)   # Russian side (EA names)


def scr_str(s):
    s = s.replace("\\", "/").replace('"', "'")
    s = "".join(c if 32 <= ord(c) < 127 else " " for c in s)
    return '"' + s + '"'


def level_strings(disc, level):
    d = f"DATA/{level.split('_')[0]}/{level}/strings.viv"
    out = {}
    data = disc.read(d)
    import viv
    for name, off, size in viv.parse_toc(data):
        blob = data[off:off + size]
        text = blob.decode("utf-16") if blob[:2] in (b"\xff\xfe", b"\xfe\xff") else blob.decode("latin-1")
        for m in eastrings.STR_RE.finditer(text):
            en = eastrings.EN_RE.search(m.group(2))
            out[m.group(1)] = re.sub(r"\s+", " ", en.group(1)).strip() if en else ""
    return out


def music(L, level, mspec, vgm, files, lines, log=print, events=()):
    """EA interactive music: SOUND/mus_ctrl.mpf (xDFP v5 path map) + mus_str.mus (EALayer3 segments). vgmstream
    (built with mpg123, LGPL) opens the pair when both share a base name; ea_levels.json picks the generic segments.
    [eapolish] events: the level's music-trigger events. Each one plays what the original's own event -> section
    table (eamusic.py, read from the .mpf) says: its intro samples in order (evN), the looping tail if the section
    loops (evN_loop), and whether the score then stops or goes back to the cue before (a stinger)."""
    import os
    import shutil
    import subprocess
    import tempfile
    import wave
    import eamusic
    d = f"DATA/{level.split('_')[0]}/{level}/SOUND/"
    tmp = tempfile.mkdtemp(prefix="eamus_")
    n = 0
    try:
        mpf = L.disc.read(d + mspec.get("mpf", "mus_ctrl.mpf"))
        with open(os.path.join(tmp, "m.mpf"), "wb") as f:
            f.write(mpf)
        with open(os.path.join(tmp, "m.mus"), "wb") as f:
            f.write(L.disc.read(d + mspec.get("mus", "mus_str.mus")))
        cache = {}

        def sample(idx):
            if idx not in cache:
                out = os.path.join(tmp, f"s{idx}.wav")
                r = subprocess.run([vgm, "-s", str(idx), "-o", out, os.path.join(tmp, "m.mpf")],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=(0x08000000 | 0x00000040) if os.name == "nt" else 0)
                cache[idx] = out if r.returncode == 0 and os.path.exists(out) else None
            return cache[idx]

        def write(name, idxs):
            """the samples back to back as one wav (they are cut from one score: same rate and channels)"""
            parts = [sample(i) for i in idxs]
            if not parts or None in parts:
                log("eapack: music segment failed", name, idxs)
                return None
            out = os.path.join(tmp, f"{name}.wav")
            frames, prm = [], None
            for pth in parts:
                with wave.open(pth, "rb") as w:
                    prm = prm or w.getparams()
                    frames.append(w.readframes(w.getnframes()))
            with wave.open(out, "wb") as w:
                w.setparams(prm)
                for fr in frames:
                    w.writeframes(fr)
            rel = f"sound/music/ea_{level}_{name}.wav"
            with open(out, "rb") as f:
                files[rel] = f.read()
            lines.append(f'\tlevel.ea_music["{name}"] = "{rel}"')
            secs = sum(len(fr) for fr in frames) / float(prm.framerate * prm.nchannels * prm.sampwidth)
            lines.append(f'\tlevel.ea_music_len["{name}"] = {secs:.1f}')
            return rel

        for name, idx in sorted(mspec["segments"].items()):
            if write(name, [idx]):
                n += 1
        try:
            tab = eamusic.table(mpf)
        except Exception as e:      # an unknown map layout: the generic segments still play
            log("eapack: music table not read", e)
            tab = {}
        for e in sorted(set(events)):
            t = tab.get(e)
            if not t:
                log("eapack: music event without a section", e)
                continue
            name = "ev%d" % e
            head = t["intro"] or t["loop"]
            if write(name, head):
                n += 1
            if t["intro"] and t["loop"] and write(name + "_loop", t["loop"]):
                n += 1
            lines.append(f'\tlevel.ea_music_cue["{name}"] = 1')
            if t["loop"]:
                lines.append(f'\tlevel.ea_music_loops["{name}"] = 1')
            if t["after"] == "return":
                lines.append(f'\tlevel.ea_music_stinger["{name}"] = 1')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return n


def voices(L, level, text, vgm, files, lines, log=print, extra=()):
    """[eapolish] the original's scripted voice lines (eavoice.py: UBER event -> str.ast stream), decoded on this PC
    to sound/ea/<level>/<n>.wav with a dialog alias each; level.ea_voice[cue] / ea_voice_len[cue]"""
    import os
    import shutil
    import subprocess
    import tempfile
    import wave
    import eavoice
    d = f"DATA/{level.split('_')[0]}/{level}/SOUND/"
    try:
        ubr = L.disc.read(d + "Audio.ubr")
        ast = L.disc.read(d + "str.ast")
    except Exception as e:      # a disc without them: subtitles only
        log("eapack: no voice data", e)
        return 0
    got = eavoice.lines(ubr, ast, [k for k in text if re.match(r"^\d", k)] + list(extra))
    tmp = tempfile.mkdtemp(prefix="eavoice_")
    ali, n = [], 0
    try:
        for i, (key, schl) in enumerate(sorted(got.items()), 1):
            src = os.path.join(tmp, "v.hab")
            dst = os.path.join(tmp, "v.wav")
            with open(src, "wb") as f:
                f.write(schl)
            r = subprocess.run([vgm, "-o", dst, src], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=(0x08000000 | 0x00000040) if os.name == "nt" else 0)
            if r.returncode != 0 or not os.path.exists(dst):
                continue
            rel = f"sound/ea/{level}/v{i:03d}.wav"
            with open(dst, "rb") as f:
                files[rel] = f.read()
            with wave.open(dst) as w:
                secs = w.getnframes() / float(w.getframerate())
            os.remove(dst)
            alias = f"ea{level.replace('_', '')}_v{i:03d}"
            ali.append(f'aliascache {alias} {rel} soundparms 1.0 0.0 1.0 0.0 800 6000 dialog streamed maps "coop_ea"')
            lines.append(f"\tlevel.ea_voice[{scr_str(key)}] = \"{alias}\"")
            lines.append(f"\tlevel.ea_voice_len[{scr_str(key)}] = {secs:.2f}")
            n += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    files[f"ubersound/ea_{level}_voice.scr"] = ("// GENERATED on this PC by the European Assault converter\n" +
                                                 "\n".join(ali) + "\n").encode()
    return n


def ambience(L, level, db, X, vgm, files, lines, log=print):
    """[dbfix 0.7.6] the level's own ambience loops. An AmbienceTrigger record names a sound event (string field 33:
    Amb_Start, Amb_Battle_Village, Amb_Cemetery ...) and carries a trigger volume; SOUND/Audio.ubr maps the event
    (id = CRC32 of its name, record type 0xf645799c - speech is 0xfd0fb324) to its stream in SOUND/str.ast. Each
    distinct stream is decoded once on this PC (mono, half rate: a loaded loop) to sound/ea/<level>/amb<n>.wav;
    level.ea_am_* lists the zones. The map script plays the loop of the zone a player entered last."""
    import array
    import os
    import shutil
    import struct
    import subprocess
    import tempfile
    import wave
    import zlib
    import eavm
    import eavoice
    recs = [r for r in db.of("AmbienceTrigger") if r.pos != (0.0, 0.0, 0.0) and r.s(33)]
    if not recs:
        return 0
    d = f"DATA/{level.split('_')[0]}/{level}/SOUND/"
    try:
        ubr = L.disc.read(d + "Audio.ubr")
        ast = L.disc.read(d + "str.ast")
    except Exception as e:
        log("eapack: no ambience data", e)
        return 0
    idx = {}
    mark = struct.pack("<I", 0xF645799C)
    o = ubr.find(mark)
    while o >= 0:
        if o >= 12:
            i, flag, ev = struct.unpack_from("<III", ubr, o - 12)
            if flag == 0x80000000 and ev == struct.unpack_from("<I", ubr, o + 4)[0] and i < 100000:
                idx[ev] = i
        o = ubr.find(mark, o + 4)
    ents = eavoice.ast_members(ast)
    tmp = tempfile.mkdtemp(prefix="eaamb_")
    alias_of, ali, n = {}, [], 0
    try:
        for ev_name in sorted(set(r.s(33) for r in recs)):
            i = idx.get(zlib.crc32(ev_name.encode()) & 0xffffffff)
            if i is None or i >= len(ents):
                log("eapack: ambience event without a stream", ev_name)
                continue
            off, sz, _nm = ents[i]
            if ast[off:off + 4] != b"SCHl":
                continue
            src, dst = os.path.join(tmp, "a.hab"), os.path.join(tmp, "a.wav")
            with open(src, "wb") as f:
                f.write(ast[off:off + sz])
            r_ = subprocess.run([vgm, "-o", dst, src], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                creationflags=(0x08000000 | 0x00000040) if os.name == "nt" else 0)
            if r_.returncode != 0 or not os.path.exists(dst):
                log("eapack: ambience stream not decoded", ev_name)
                continue
            with wave.open(dst, "rb") as w:
                ch, rate, sw = w.getnchannels(), w.getframerate(), w.getsampwidth()
                pcm = array.array("h", w.readframes(w.getnframes())) if sw == 2 else None
            os.remove(dst)
            if pcm is None:
                continue
            # mono, half rate (mean of the 2 * channels samples of each frame pair): a small loaded loop
            step = 2 * ch
            out = array.array("h", (sum(pcm[k:k + step]) // step for k in range(0, len(pcm) - step + 1, step)))
            n += 1
            rel = f"sound/ea/{level}/amb{n}.wav"
            with wave.open(dst, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(rate // 2)
                w.writeframes(out.tobytes())
            with open(dst, "rb") as f:
                files[rel] = f.read()
            os.remove(dst)
            alias = f"ea{level.replace('_', '')}_amb{n}"
            alias_of[ev_name] = alias
            ali.append(f'aliascache {alias} {rel} soundparms 1.0 0.0 1.0 0.0 160 1600 auto loaded maps "coop_ea"')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    k = 0
    for r in recs:
        a = alias_of.get(r.s(33))
        if not a:
            continue
        k += 1
        q = X(r.pos)
        kind, rad, hx, hy, hz = eavm.shape(r, X)
        lines.append(f'\tlevel.ea_am_name[{k}] = "{r.name}"')
        lines.append(f'\tlevel.ea_am_alias[{k}] = "{a}"')
        lines.append(f"\tlevel.ea_am_pos[{k}] = ( {q[0]:.0f} {q[1]:.0f} {q[2]:.0f} )")
        lines.append(f"\tlevel.ea_am_yaw[{k}] = {r.yaw:.0f}")
        lines.append(f"\tlevel.ea_am_shape[{k}] = {kind}")
        lines.append(f"\tlevel.ea_am_r[{k}] = {rad:.0f}")
        lines.append(f"\tlevel.ea_am_hx[{k}] = {hx:.0f}")
        lines.append(f"\tlevel.ea_am_hy[{k}] = {hy:.0f}")
    lines.append(f"\tlevel.ea_am_n = {k}")
    files[f"ubersound/ea_{level}_amb.scr"] = ("// GENERATED on this PC by the European Assault converter\n" +
                                               "\n".join(ali) + "\n").encode()
    return n


def clear_line(grid, a, b, step=16.0):
    """the player box can stand all along a->b (BSP units): every 16u has ground within a step and free space"""
    import math
    n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
    z = a[2]
    for k in range(n + 1):
        x = a[0] + (b[0] - a[0]) * k / n
        y = a[1] + (b[1] - a[1]) * k / n
        g = grid.ground(x, y, z + 40, z - 64)
        if g is None or not grid.box_free(x, y, g, lift=18.0, margin=2.0):
            return False
        z = g
    return True


def use_points(grid, target, toward, n_ring=16, radii=(0, 96, 160, 220), app_r=(150, 200, 120)):
    """a use point on free ground at/near `target` (biased toward `toward`), plus an approach spot 120-200u out with
    a clear straight walk to it and the yaw that faces it. Deterministic (fixed ring order). BSP units."""
    import math
    tx, ty, tz = target
    base = math.atan2(toward[1] - ty, toward[0] - tx)
    use = None
    for r in radii:
        for k in range(1 if r == 0 else n_ring):
            a = base + (k * 2 * math.pi / n_ring if r else 0)
            x, y = tx + r * math.cos(a), ty + r * math.sin(a)
            g = grid.ground(x, y, tz + 64, tz - 128)
            if g is not None and grid.box_free(x, y, g, lift=2.0, margin=8.0):
                use = (x, y, g)
                break
        if use:
            break
    if not use:
        return None
    for r in app_r:
        for k in range(n_ring):
            a = base + k * 2 * math.pi / n_ring
            x, y = use[0] + r * math.cos(a), use[1] + r * math.sin(a)
            g = grid.ground(x, y, use[2] + 64, use[2] - 128)
            if g is None or not grid.box_free(x, y, g, lift=2.0, margin=8.0):
                continue
            if clear_line(grid, (x, y, g), use):
                yaw = math.degrees(math.atan2(use[1] - y, use[0] - x)) % 360
                return use, (x, y, g), yaw
    return use, None, None


def _places(L, db=None):
    """world-space records of the level's object DB (eadb: names by string-pool index), in file order, as the dicts
    the placement code below expects; spawn points carry their team from the character definition"""
    db = db or eadb.DB(L.stream)
    out = []
    for r in db.recs:
        if r.pos == (0.0, 0.0, 0.0):
            continue
        o = {"name": r.name, "class": r.cls, "pos": r.pos, "yaw": r.yaw, "off": r.off, "size": len(r.w) * 4}
        if r.cls == "NPCSpawnPoint":
            o["team"] = eadb.team_of(r.npc()["character"])
            o["name"] = r.name if "NPCSpawnPoint_" in r.name else "NPCSpawnPoint_" + r.name
        out.append(o)
    return out


def find_object(L, wants, X, grid, zrange):
    """first world-space placement (metres) for a name or a fallback list; same rules as build()"""
    places = _places(L)
    for want in ([wants] if isinstance(wants, str) else wants):
        for o in places:
            if (o["name"] == want or o["name"].endswith(want)) and zrange[0] - 1 <= o["pos"][2] <= zrange[1] + 1:
                q = X(o["pos"])
                if grid.ground(q[0], q[1], q[2] + 48, q[2] - 120) is not None:
                    return o
    return None


def build(L, level, X, files, spec, grid, zrange, log=print, mohaa_base=None, vgm=None):
    text = level_strings(L.disc, level)
    db = eadb.DB(L.stream)
    places = _places(L, db)
    lo_z, hi_z = zrange

    def plausible(o):
        # world-space records only (children carry local z = 0): collision ground within 2.5 m under the point
        if not (lo_z - 1 <= o["pos"][2] <= hi_z + 1):
            return False
        q = X(o["pos"])
        return grid.ground(q[0], q[1], q[2] + 48, q[2] - 120) is not None

    def strict_spot(q0, max_r=192, step=8):
        """nearest standing spot the ENGINE accepts: flgeom's box test with lift 2 / margin 8 (the lenient lift 8 /
        margin 4 passed spots the engine reports stuck - patrol 2026-11-09: 4/28 spawn points). None if nothing."""
        import math
        x0, y0, z0 = q0
        for r in range(0, max_r + 1, step):
            n = 1 if r == 0 else max(8, int(2 * math.pi * r / step))
            for k in range(n):
                a = 2 * math.pi * k / n
                x, y = x0 + r * math.cos(a), y0 + r * math.sin(a)
                g = grid.ground(x, y, z0 + 48, z0 - 96)
                if g is not None and grid.box_free(x, y, g, lift=2.0, margin=8.0):
                    return (round(x), round(y), g)
        # 0.7.10 a point on a hillside: the lift-2 box cuts the slope itself everywhere, and the spawn point was
        # dropped (TAKE_IT_MMG_01). Same search with the feet lifted 14u (the walls' margin unchanged); the actor is
        # dropped to the floor when it spawns.
        for r in range(0, 96 + 1, step):
            n = 1 if r == 0 else max(8, int(2 * math.pi * r / step))
            for k in range(n):
                a = 2 * math.pi * k / n
                x, y = x0 + r * math.cos(a), y0 + r * math.sin(a)
                g = grid.ground(x, y, z0 + 48, z0 - 96)
                if g is not None and grid.box_free(x, y, g, lift=14.0, margin=8.0):
                    return (round(x), round(y), g)
        return None

    def free(p):
        q = strict_spot(X(p))
        if q is not None:
            return q
        q, moved = grid.free_spot(X(p))
        return q

    lines = ["// GENERATED on this PC by docs/tools/ea/eapack.py from the player's own disc.",
             "// Not part of the mod source; regenerated by the converter.", "init:{"]
    for k in sorted(spec.get("text", [])):
        if k in text:
            lines.append(f'\tlevel.ea_text["{k}"] = {scr_str(text[k])}')
    found = {}
    for key, wants in sorted(spec.get("objects", {}).items()):
        cands = []
        for want in ([wants] if isinstance(wants, str) else wants):     # a list = fallbacks in order
            cands = [o for o in places if (o["name"] == want or o["name"].endswith(want)) and plausible(o)]
            if cands:
                break
        if not cands:
            log("eapack: no placement for", key, wants)
            continue
        o = cands[0]
        p = free(o["pos"])
        found[key] = (p, o["yaw"])
        lines.append(f'\tlevel.ea_pos["{key}"] = ( {p[0]:.0f} {p[1]:.0f} {p[2] + 24:.0f} )')
        lines.append(f'\tlevel.ea_yaw["{key}"] = {o["yaw"] % 360:.0f}')
    if "start" in found:
        p, yaw = found["start"]
        lines.append(f'\tlevel.ea_start = ( {p[0]:.0f} {p[1]:.0f} {p[2] + 24:.0f} )')
        lines.append(f'\tlevel.ea_start_yaw = {(yaw + 90) % 360:.0f}')      # facing = row 1
    na = nl = 0
    seen = []
    for o in places:
        if not plausible(o):
            continue
        if not SPAWN_RX.search(o["name"]):
            continue
        is_al = o.get("team") == "allies" if o.get("team") else ALLY_RX.search(o["name"])
        p = strict_spot(X(o["pos"]))
        if p is None:            # no spot the engine accepts near it: drop the spawn point rather than spawn stuck
            log("eapack: spawn point dropped (no free spot)", o["name"])
            continue
        if any((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 < 64 * 64 for q in seen):
            continue
        seen.append(p)
        if is_al:
            nl += 1
            lines.append(f'\tlevel.ea_ally[{nl}] = ( {p[0]:.0f} {p[1]:.0f} {p[2] + 24:.0f} )')
        else:
            na += 1
            lines.append(f'\tlevel.ea_axis[{na}] = ( {p[0]:.0f} {p[1]:.0f} {p[2] + 24:.0f} )')
            lines.append(f'\tlevel.ea_axis_cls[{na}] = {scr_str(o["name"])}')
    # ---- use points: on free ground, clear of the stand-in props (a solid prop on a trigger eats the use-trace),
    # each with an approach spot + yaw for the real-input assist (coop_eatest 3) ----
    import math
    if "start" in found:
        st0 = found["start"][0]
        uses = []
        for key in ("ammo", "tower"):
            if key in found:
                uses.append((key, found[key][0], st0, (0, 96, 160)))
        tanks = []
        if "panzer1" in found:
            tanks.append(found["panzer1"][0])
        if "panzer3" in found:
            p3 = found["panzer3"][0]
            q, _m = grid.free_spot((p3[0], p3[1] + 360, p3[2]))
            tanks.append(q)
        if "panzers_obj" in found:
            tanks.append(found["panzers_obj"][0])
        for i, tp in enumerate(tanks, 1):
            lines.append(f'\tlevel.ea_tankpos[{i}] = ( {tp[0]:.0f} {tp[1]:.0f} {tp[2] + 24:.0f} )')
            uses.append((f"tank{i}", tp, st0, (220, 260, 300)))
        lines.append(f"\tlevel.ea_tank_n = {len(tanks)}")
        if "railgun" in found:
            rg = found["railgun"][0]
            for k in range(3):
                a = math.radians(120 * k)
                uses.append((f"charge{k + 1}", rg, (rg[0] + 1000 * math.cos(a), rg[1] + 1000 * math.sin(a), rg[2]),
                             (240, 280, 320)))
        for key, tgt, toward, radii in uses:
            r = use_points(grid, tgt, toward, radii=radii)
            if not r:
                log("eapack: no use point for", key)
                continue
            use, app, yaw = r
            lines.append(f'\tlevel.ea_use["{key}"] = ( {use[0]:.0f} {use[1]:.0f} {use[2] + 24:.0f} )')
            if app:
                lines.append(f'\tlevel.ea_app["{key}"] = ( {app[0]:.0f} {app[1]:.0f} {app[2] + 24:.0f} )')
                lines.append(f'\tlevel.ea_appyaw["{key}"] = {yaw:.0f}')
                if key in ("ammo", "tower"):
                    dx, dy = use[0] - app[0], use[1] - app[1]
                    l = math.hypot(dx, dy) or 1.0
                    lines.append(f'\tlevel.ea_prop["{key}"] = ( {use[0] + dx / l * 110:.0f} {use[1] + dy / l * 110:.0f} {use[2] + 24:.0f} )')
            else:
                log("eapack: no clear approach for", key)

    def ground_pt(q):
        g = grid.ground(q[0], q[1], q[2] + 48, q[2] - 160)
        return (q[0], q[1], g + 2) if g is not None else None
    vm = eavm.build(db, X, strict_spot, ground_pt, text, lines, log)
    nvoice = 0
    if vgm:
        nvoice = voices(L, level, text, vgm, files, lines, log, vm.get("pa_events", ()))
    vm["voices"] = nvoice
    vm["ambience"] = ambience(L, level, db, X, vgm, files, lines, log) if vgm else 0
    nmus = 0
    if vgm and spec.get("music"):
        # [eapolish] the original's music EVENTS (its music triggers, eavm) play the sections the .mpf's own
        # event table gives them (eamusic.py; converter 0.6.1)
        nmus = music(L, level, spec["music"], vgm, files, lines, log, events=vm.get("music_events", []))
    # [eapolish] the level's own particle systems (fires, smoke, fog, blasts) as emitters (eafx.py; converter 0.7.0)
    import collections
    import eafx
    fxused = collections.Counter(eavm.base(t) for r in db.of("EffectsPackage") for _k, t in r.strings()
                                 if t.lower().endswith(".xpd"))
    vm["fx"] = eafx.build(L.stream, db, X, level, files, lines, used=dict(fxused), log=log,
                          far_gain=float(spec.get("far_fx_gain", 1.0)))
    # [0.7.23] the level's own character models (eachar.py: the partisan woman so far), into this pak only
    import eachar
    eachar.build(L.stream, level, mohaa_base, files, lines, log=log)
    lines += [f"\tlevel.ea_axis_n = {na}", f"\tlevel.ea_ally_n = {nl}", "\tlevel.ea_data_ok = 1", "}end", ""]
    files[f"maps/coop_ea_{level}_data.scr"] = "\n".join(lines).encode("latin-1")
    if mohaa_base:
        import flpack      # stock aliases are map-filtered: re-declare the AA-campaign ones for coop_ea (Frontline recipe)
        _br = flpack.alias_bridge(mohaa_base, "coop_ea_" + level)
        # The allied riflemen use the stock Soviet models, which carry no generic combat head lines, so the AI's
        # sighted / attack / spread shouts fall through to sound aliases no pak defines and the server log fills
        # with missing-alias errors. The install has no Russian generic lines and American ones would be wrong on
        # partisans, so the names are declared silent for coop_ea maps only (the wav is the install's own).
        _sil = []
        for _n in ("sighted", "attack", "spread"):
            for _c in "abcdefghijklmnop":
                _sil.append(f'alias dfr_head_{_n}_{_c} sound/null.wav soundparms 1.0 0 1 0 160 1600 dialog loaded maps "coop_ea"')
        for _c in "abcdefghijklmnop":   # the panic bark has no head animation either
            _sil.append(f'alias dfr_morphonly_panic_{_c} sound/null.wav soundparms 1.0 0 1 0 160 1600 dialog loaded maps "coop_ea"')
        _sil.append('alias pain_generic sound/null.wav soundparms 1.0 0 1 0 160 1600 dialog loaded maps "coop_ea"')
        files["ubersound/ea_aliasbridge.scr"] = (_br + "\n".join(_sil) + "\n").encode("latin-1")
    return {"vm": vm, "objects": sorted(found), "axis": na, "allies": nl, "text": len(spec.get("text", [])), "music": nmus}
