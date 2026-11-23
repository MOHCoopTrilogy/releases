#!/usr/bin/env python3
"""[0.7.57, decode audit gap 11] the original's own footstep, landing, bullet-impact, bullet-whiz and Panzer engine
sounds, from the level's always-loaded bank (SOUND/scr.abk), as MOHAA's stock alias pools on coop_ea maps only.
Our own code; it reads the player's own disc. Nothing it writes is shipped.

How the original names them (DEFAULT.XBE, decode 2026-11-23; CODE_FINDINGS_footsteps.md for the surface table):
  - footsteps / landings: sprintf("%s_%s_%s", "Mvmt" (player) | "NPC", action, surface) (+ "_Zone%d" in an audio
    zone); the action table at .data 0x3770e0 (Step_Walk, Step_Stop, Jump_Land, ...), the surface table at
    0x376f2c (Snow, WoodSolid, Concrete, ...). FALLBACK (code 0x143670-0x143706): when "<pfx>_<action>_<surface>" has
    no Audio.ubr entry the engine plays "<pfx>_<action>" - so on 1_11 every surface without its own event (SnowSlush,
    SandDry, metal, glass) steps on the generic Mvmt_Step_Walk, which is the snow set.
  - bullet impacts: sprintf("%sProjType_%s_%s", "PC_" | "", projectile (0x376f00: Bullet, Grenade ...), surface),
    then "%sProjType_%s"; there is no "ProjType_Bullet" entry on 1_11, so a surface without its own event is silent.
  - vehicles: "Veh_%s" + "_Idle_LP" / "_Move_LP" / "_Turret_Traverse_LP" ... (0x376ff0, 0x307484).
  - "WhizBy" (0x31d858).
  Every name above is checked by its CRC32 against Audio.ubr's Alias field; nothing is guessed by ear.

Audio.ubr (self-describing UBER table, eapack.sounddefs): one record per sample slot; records sharing an Alias form
one event. Read here: field eec5bfe7 = the alternative SET (one set is picked per play [PROV]: NPC_Step_Walk carries
two parallel sets 1 / 2), c016bada = the LAYER inside the set (every layer plays), 32b69800 = the layer's play
chance in %, Volume Min / Max (%), Pitch Min / Max (/4096), Delay Min / Max (read as 1/100 s [PROV]: the code turns
it into a float at +0x38, unit not traced), FalloffStart / End (m).

MOHAA plays one file per alias, so each event is PRE-MIXED into a pool of variants: variant k takes set k mod n,
then every layer of that set that passes its chance (seeded), one random sample of the layer at its mean volume, its
mean pitch (resampled) and its mean delay. The kit-rattle layer of a step (the 33 % layer of Mvmt_Step_Walk*) is NOT
mixed in: MOHAA plays its own snd_step_equipment beside 30 % of steps, so that pool gets the disc's kit samples
instead. Loudness: each pool is peak-normalised and keeps the stock alias's volume (the MOHAA mix level); pitch spread,
distances (falloff x 48) and loops from the disc. EA_DISC_SFX=0 = off (the stock MOHAA sounds)."""
import os
import random
import shutil
import struct
import subprocess
import tempfile
import wave
import zlib

SR = 22050

# (MOHAA alias stem, the original's event names in its own fallback order, kind)
#   kind "mix": pre-mixed variants; "step": the same without the sub-100 % kit layer; "equip": that kit layer's samples;
#   "loop": one looping sample; "pool": one variant per sample record
TARGETS = [
    ("snd_step_snow", ["Mvmt_Step_Walk_Snow", "Mvmt_Step_Walk"], "step"),
    ("snd_step_wood", ["Mvmt_Step_Walk_WoodSolid", "Mvmt_Step_Walk"], "step"),
    ("snd_step_stone", ["Mvmt_Step_Walk_Concrete", "Mvmt_Step_Walk"], "step"),
    ("snd_step_sand", ["Mvmt_Step_Walk_SandDry", "Mvmt_Step_Walk"], "step"),
    ("snd_step_metal", ["Mvmt_Step_Walk_MetalHeavy", "Mvmt_Step_Walk"], "step"),
    ("snd_step_glass", ["Mvmt_Step_Walk_GlassShatter", "Mvmt_Step_Walk"], "step"),
    ("snd_step_equipment", ["Mvmt_Step_Walk"], "equip"),
    ("snd_landing_snow", ["Mvmt_Jump_Land_Snow", "Mvmt_Jump_Land"], "mix"),
    ("snd_landing_stone", ["Mvmt_Jump_Land_Concrete", "Mvmt_Jump_Land"], "mix"),
    ("snd_landing_wood", ["Mvmt_Jump_Land_WoodSolid", "Mvmt_Jump_Land"], "mix"),
    ("snd_landing_sand", ["Mvmt_Jump_Land_SandDry", "Mvmt_Jump_Land"], "mix"),
    ("snd_landing_metal", ["Mvmt_Jump_Land_MetalHeavy", "Mvmt_Jump_Land"], "mix"),
    ("snd_landing_glass", ["Mvmt_Jump_Land_GlassShatter", "Mvmt_Jump_Land"], "mix"),
    # the player's own shots (PC_) first: the impacts a player hears most; the NPC set is the same or near it
    ("snd_bh_snow", ["PC_ProjType_Bullet_Snow", "ProjType_Bullet_Snow"], "mix"),
    ("snd_bh_wood", ["PC_ProjType_Bullet_WoodSolid", "ProjType_Bullet_WoodSolid"], "mix"),
    ("snd_bh_stone", ["PC_ProjType_Bullet_Concrete", "ProjType_Bullet_Concrete"], "mix"),
    ("snd_bh_metal", ["PC_ProjType_Bullet_MetalHeavy", "ProjType_Bullet_MetalHeavy"], "mix"),
    ("snd_bh_glass", ["PC_ProjType_Bullet_GlassShatter", "ProjType_Bullet_GlassShatter"], "mix"),
    ("snd_bh_flesh", ["PC_ProjType_Bullet_Flesh", "ProjType_Bullet_Flesh"], "mix"),
    ("snd_b_zing", ["WhizBy"], "pool"),
    ("tank_snd_idle", ["Veh_Panzer_IV_Idle_LP"], "loop"),
    ("tank_snd_run", ["Veh_Panzer_IV_Move_LP"], "loop"),
    ("tank_snd_move", ["Veh_Panzer_IV_Turret_Traverse_LP"], "loop"),   # the turret's traverse loop (stock veh_tank_turret1)
]
NVAR = {"step": 8, "mix": 6}
FIELDS = {"alias": 0x20ad4490, "bank": 0x7fff5f24, "idx": 0xbc1069ff, "set": 0xeec5bfe7, "layer": 0xc016bada,
          "prob": 0x32b69800, "vmin": "Volume Min", "vmax": "Volume Max", "pmin": "Pitch Min", "pmax": "Pitch Max",
          "dmin": "Delay Min", "dmax": "Delay Max", "fstart": "FalloffStart", "fend": "FalloffEnd", "loop": "Loop"}
BANKS = {0x40000000: "scr.abk", 1: "L1.abk", 2: "L2.abk", 4: "L3.abk", 8: "L4.abk"}


def crc(s):
    return zlib.crc32(s.encode()) & 0xffffffff


def ubr_events(ubr):
    """Audio.ubr -> {alias crc: [record dict]} read by field name / crc through the file's own field table"""
    nf, nr, st = struct.unpack_from("<III", ubr, 16)
    tab = {}
    for i in range(nf):
        c, t, o = struct.unpack_from("<III", ubr, 32 + 12 * i)
        tab[c] = (t, o)
    base = 32 + 12 * nf
    F = {k: tab.get(v if isinstance(v, int) else crc(v)) for k, v in FIELDS.items()}
    if None in F.values():
        return {}
    ev = {}
    for r in range(nr):
        rs = base + r * st
        if rs + st > len(ubr):
            break
        d = {}
        for k, (t, o) in F.items():
            d[k] = ubr[rs + o] if t in (0, 1) else struct.unpack_from("<H" if t == 2 else "<I", ubr, rs + o)[0]
        ev.setdefault(d["alias"], []).append(d)
    return ev


def _layers(recs):
    """{set: {layer: [records]}}"""
    out = {}
    for r in recs:
        out.setdefault(r["set"], {}).setdefault(r["layer"], []).append(r)
    return out


def _read_wav(p):
    import numpy as np
    w = wave.open(p)
    n, ch, sr = w.getnframes(), w.getnchannels(), w.getframerate()
    a = np.frombuffer(w.readframes(n), np.int16).astype(np.float64) / 32768.0
    if ch > 1:
        a = a.reshape(-1, ch).mean(1)
    if sr != SR:
        t = np.arange(int(len(a) * SR / sr)) * (sr / SR)
        a = np.interp(t, np.arange(len(a)), a)
    return a


def _write_wav(a):
    import io
    import numpy as np
    b = io.BytesIO()
    w = wave.open(b, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((np.clip(a, -1, 1) * 32767).astype("<i2").tobytes())
    w.close()
    return b.getvalue()


def _pitch(a, p):
    import numpy as np
    if abs(p - 1.0) < 1e-3:
        return a
    t = np.arange(0, len(a) - 1, p)
    return np.interp(t, np.arange(len(a)), a)


def _stock_parms(bridge, stem):
    """the stock alias's 'volume volrand' and channel token, from the bridge text (the MOHAA mix level)"""
    for ln in bridge.splitlines():
        p = ln.split()
        if len(p) > 10 and p[0] in ("alias", "aliascache") and p[1].lower() in (stem, stem + "1", stem + "#2") \
                and p[3] == "soundparms":
            return float(p[4]), float(p[5]), p[10]
    return 0.8, 0.2, "auto"


def build(L, level, vgm, files, bridge, log=print):
    """write the pools and ubersound/ea_<level>_sfx.scr into files; returns the set of stems overridden (the caller
    drops their stock pool from the alias bridge: MOHAA picks from every alias that STARTS with the stem)"""
    if os.environ.get("EA_DISC_SFX", "1") == "0" or not vgm:
        return set()
    import numpy as np
    d = f"DATA/{level.split('_')[0]}/{level}/SOUND/"
    try:
        ev = ubr_events(L.disc.read(d + "Audio.ubr"))
    except Exception as e:
        log("eadiscsfx: no Audio.ubr", e)
        return set()
    tmp = tempfile.mkdtemp(prefix="easfx_")
    cache, banks = {}, {}

    def sample(bank, idx):
        k = (bank, idx)
        if k not in cache:
            name = BANKS.get(bank)
            cache[k] = None
            if name:
                if name not in banks:
                    banks[name] = os.path.join(tmp, name)
                    with open(banks[name], "wb") as f:
                        f.write(L.disc.read(d + name))
                dst = os.path.join(tmp, "s%d_%d.wav" % (bank, idx))
                r_ = subprocess.run([vgm, "-s", str(idx + 1), "-i", "-o", dst, banks[name]], stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                    creationflags=(0x08000000 | 0x00000040) if os.name == "nt" else 0)
                if r_.returncode == 0 and os.path.exists(dst):
                    cache[k] = _read_wav(dst)
        return cache[k]

    lines, done = [], set()
    try:
        for stem, cands, kind in TARGETS:
            name = next((c for c in cands if crc(c) in ev), None)
            if not name:
                log("eadiscsfx: no disc event for", stem, cands)
                continue
            sets = _layers(ev[crc(name)])
            first = sets[sorted(sets)[0]][sorted(sets[sorted(sets)[0]])[0]][0]
            vol, vrnd, chan = _stock_parms(bridge, stem)
            pm = (first["pmin"] + first["pmax"]) / 2.0 / 4096.0
            spread = (first["pmax"] - first["pmin"]) / 4096.0 / max(pm, 1e-3)
            mind = max(16, int(first["fstart"] * 48))
            maxd = max(mind + 64, int(first["fend"] * 48))
            outs = []        # (wav array, alias pitch, alias pitch rand)
            if kind in ("loop", "pool", "equip"):
                if kind == "equip":
                    recs = [r for s in sets.values() for ly in s.values() for r in ly if r["prob"] < 100]
                else:
                    recs = [r for s in sets.values() for ly in s.values() for r in ly]
                seen = set()
                for r in recs:
                    if (r["bank"], r["idx"]) in seen:
                        continue
                    seen.add((r["bank"], r["idx"]))
                    a = sample(r["bank"], r["idx"])
                    if a is None:
                        continue
                    p = (r["pmin"] + r["pmax"]) / 2.0 / 4096.0
                    s_ = (r["pmax"] - r["pmin"]) / 4096.0
                    if kind == "loop" and r["pmax"] - r["pmin"] > 0.25 * r["pmin"]:
                        p, s_ = 1.0, 0.0      # a wide range is the engine's pitch-by-speed (Move_LP 0.71-1.41): MOHAA does that
                    outs.append((a, p, s_))
                    if kind == "loop":
                        break
            else:
                rng = random.Random(crc(stem))
                sk = sorted(sets)
                for k in range(NVAR[kind] if len(sk) == 1 else max(NVAR[kind], 2 * len(sk))):
                    layers = sets[sk[k % len(sk)]]
                    parts = []
                    for ln_ in sorted(layers):
                        recs = layers[ln_]
                        if kind == "step" and recs[0]["prob"] < 100:
                            continue
                        if rng.random() * 100.0 >= recs[0]["prob"]:
                            continue
                        r = rng.choice(recs)
                        v = (r["vmin"] + r["vmax"]) / 2.0 / 100.0
                        a = sample(r["bank"], r["idx"])
                        if a is None or v <= 0:
                            continue
                        a = _pitch(a, (r["pmin"] + r["pmax"]) / 2.0 / 4096.0 / pm) * v
                        parts.append((int((r["dmin"] + r["dmax"]) / 2.0 * 0.01 * SR), a))
                    if not parts:
                        continue
                    n = max(o + len(a) for o, a in parts)
                    m = np.zeros(n)
                    for o, a in parts:
                        m[o:o + len(a)] += a
                    outs.append((m, pm, spread * pm))
            if not outs:
                log("eadiscsfx: nothing decoded for", stem, name)
                continue
            pk = max(float(np.abs(a).max()) for a, _, _ in outs) or 1.0
            for k, (a, p, s_) in enumerate(outs):
                rel = f"sound/ea/{level}/sfx_{stem}_{k + 1:02d}.wav"
                files[rel] = _write_wav(a * (0.89 / pk))
                an = stem if k == 0 else "%s#%d" % (stem, k + 1)
                lines.append(f'aliascache {an} {rel} soundparms {vol:.2f} {vrnd:.2f} {max(0.3, p - s_ / 2):.3f} {s_:.3f} '
                             f'{mind} {maxd} {chan} loaded maps "coop_ea"')
            done.add(stem)
            log("eadiscsfx:", stem, "<-", name, kind, len(outs), "variants, dist", mind, maxd)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if lines:
        files[f"ubersound/ea_{level}_sfx.scr"] = ("// GENERATED on this PC by the European Assault converter from the "
                                                  "player's own disc (eadiscsfx.py)\n" + "\n".join(lines) + "\n").encode()
    return done


def drop_pools(bridge, stems):
    """the bridge text without any alias in a pool we replaced (a name that starts with the stem and does not go on
    with '_': qcommon/alias.c Alias_ListFindRandomRange)"""
    out = []
    for ln in bridge.splitlines():
        p = ln.split()
        nm = p[1].lower() if len(p) > 1 and p[0].lower() in ("alias", "aliascache") else ""
        if nm and any(nm.startswith(s) and (len(nm) == len(s) or nm[len(s)] != "_") for s in stems):
            continue
        out.append(ln)
    return "\n".join(out) + "\n"
