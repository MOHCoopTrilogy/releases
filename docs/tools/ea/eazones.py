#!/usr/bin/env python3
"""European Assault area zones: the original's bloom door strips, irradiance volumes and mixer-snapshot boxes.
Our own code, stdlib only. Run on the player's own disc only; the output stays in the player's own pak.

Decoded 2026-11-15 on the user's disc (1_11, "Their Dying Breath"; AUDIT F4 / F5 / F9):

BloomTrigger (37 on 1_11): box (w15 = 2; w19..21 = FULL extents in metres along the record's local x / y / z; the
  local x axis is rot row 0 = r.yaw), w22 = 1 on the level's global record, w23 = bloom level 0..255, w24 = 1..3
  (the number of blur downsample passes, clamped 0-3: code decode, bug-11258), w25..28 = RGBA 255, w29 = 60 (fade in frames: 1 s), w30 = the
  debug string '@BloomTrigger Fired'. On 1_11 they are DOOR STRIPS: each doorway has an ENT strip on its inside
  (level 230) and an EXT strip on its outside (135, as the global record): the one a player crossed last decides,
  so the original blooms its interiors 230 / 135 = 1.70x harder than outdoors. Checked across the other levels on
  the disc: w23 runs 25..255, w24 1..3.
IrradianceVolumeTrigger (17): box + w22 = volume index (0..16), w23 = 0..3, w24 = 1.0. No colour is in the record
  and no decoded chunk holds one; the interior ambient light of a dynamic model therefore comes from the level's own
  baked vertex light inside the volume (light_volumes() -> flbsp's entity light grid).
SoundBusTrigger (12): box, w24 = the snapshot entered, w25 = the snapshot on leaving (Default_Mix on all eleven
  interior boxes); record 1 (off-map sphere) names Default_Mix alone.
SOUND/AUDIO.BUS: 'UBUS' header, 8 (crc, n, index) triplets at 0x2c, then 28-byte records from 0x8c:
  {u32 0, u16 Volume Ramp (1/60 s), u16 PITCH Ramp, u32 FX Ramp, s16 Volume Target, s16 Pitch Target,
  u32 FX Target, u32 bus crc, u32 snapshot crc} (field names: the code decode, CODE_FINDINGS_ea_1_11 F9; bug-11258).
  Only the Volume Ramp and Volume Target are used, entering and leaving a box alike (+6 is NOT a fade-out).
  Names by CRC32 of the string: buses Music, Speech, Vehicle, Explosions, BulletImpacts, Death, Debris, RailGun,
  Weapon_Mech, Weapon_Fire_Loop; snapshots Default_Mix, Rail_Gun, DialogDuck, Radio_Mix, Revive. SOUND/AUDIO.UBR
  routes each sound event to a bus (the word after the event's flags): the ambience streams and the fire loops
  (AmbienceTrigger, SoundDefTrigger) are on bus f645799c, the PA speech streams on fd0fb324.
  The Volume Target is a PERCENT: the original applies gain = 1 + target / 100 (code decode), not dB.

Our runtime (coop_mod/zonefx.scr) applies a snapshot RELATIVE to Default_Mix, so outdoors is identity:
  coop_zoneMix "<snapshot> <fadeMs> <music> <speech> <vehicle> <weapons> <ambience> <effects>" (dB, engine
  snd_openal_new.cpp S_HZM_ZoneMixUpdate), coop_zoneFx "<tag> <fadeMs> <bloomMul>" (cgame CG_CoopZoneFxThink).
"""
import math
import struct
import zlib

BUS_NAMES = ("Music", "Speech", "Vehicle", "Explosions", "BulletImpacts", "Death", "Debris", "RailGun",
             "Weapon_Mech", "Weapon_Fire_Loop")
SNAP_NAMES = ("Default_Mix", "Rail_Gun", "DialogDuck", "Radio_Mix", "Revive")
AMBIENT_BUS = 0xF645799C          # the bus the ambience streams and fire loops route to (AUDIO.UBR)


def _crc(s):
    return zlib.crc32(s.encode()) & 0xffffffff


BUS = {_crc(n): n for n in BUS_NAMES}
SNAP = {_crc(n): n for n in SNAP_NAMES}
DEFAULT_MIX = _crc("Default_Mix")
# our six engine categories <- the original's buses (one representative bus each; see the module doc)
CATEGORY_BUS = (("music", _crc("Music")), ("speech", _crc("Speech")), ("vehicle", _crc("Vehicle")),
                ("weapons", _crc("Weapon_Fire_Loop")), ("ambience", AMBIENT_BUS), ("effects", _crc("Explosions")))


def read_bus(data):
    """AUDIO.BUS -> {snapshot crc: {bus crc: (level, fade_in, fade_out)}}"""
    if data[:4] != b"UBUS":
        raise ValueError("not a UBUS file")
    n, size = struct.unpack_from("<2I", data, 0x14)
    o = 0x8c
    out = {}
    for _i in range(n):
        if o + size > len(data):
            break
        _z, fa, fb, _c, lvl, _hi, _d, bus, snap = struct.unpack_from("<IHHIhhIII", data, o)
        out.setdefault(snap, {})[bus] = (lvl, fa, fb)
        o += size
    return out


def _snap_name(c):
    return SNAP.get(c, "%08x" % c)


def mix_value(snaps, snap):
    """coop_zoneMix value of `snap` relative to Default_Mix (dB per category) and its fade (ms)"""
    base, s = snaps.get(DEFAULT_MIX, {}), snaps.get(snap, {})
    db, fade = [], 0
    for _cat, bus in CATEGORY_BUS:
        b = base.get(bus, (0, 0, 0))[0]
        v = s.get(bus, (b, 0, 0))
        g0, g1 = max(0.0, 100.0 + b) / 100.0, max(0.0, 100.0 + v[0]) / 100.0
        db.append(0.0 if g0 <= 0 else (-60.0 if g1 <= 0 else 20.0 * math.log10(g1 / g0)))
        if bus in s:
            fade = max(fade, v[1])
    ms = int(round(fade * 1000.0 / 60.0))
    return "%s %d %s" % (_snap_name(snap), ms, " ".join("%.1f" % d for d in db))


def _box(r, X):
    """map-frame box in the convention of eavm.shape / the map script's ea_am_in: centre, the record's yaw (rot row
    0) and half extents along the yaw's own x / y / z (flconvert's Xform keeps the disc axes, no mirror on 1_11)"""
    q = X(r.pos)
    return q, r.yaw, abs(r.f(19) or 0) * 24.0, abs(r.f(20) or 0) * 24.0, abs(r.f(21) or 0) * 24.0


def _bloom_level(r):
    return r.u(23)


def bloom_mix(level, passes_level):
    """the original's bloom add k = (247/255)^(2n) x Bloom/255 (n = Level + 1 blur passes, Level clamped 0..3; the tent
    weights sum to 247/255 by truncation - code decode F4) as the renormalised mix weight k / (1 + k)"""
    n = max(0, min(3, int(passes_level or 0))) + 1
    k = (247.0 / 255.0) ** (2 * n) * max(0, min(255, level)) / 255.0
    return k / (1.0 + k)


def zones(db, snaps):
    """[(name, kind, record, enter value, exit value)] - kind 'bloom' (latched door strip) or 'mix' (box)"""
    out = []
    bl = db.of("BloomTrigger")
    glb = [r for r in bl if r.u(22) == 1]
    base = _bloom_level(glb[0]) if glb else 135
    for r in bl:
        if r.u(22) == 1 or not base:
            continue
        lv = _bloom_level(r)
        tag = "bloom_in" if lv > base else ("bloom_out" if lv == base else "bloom_%d" % lv)
        fade = int(round((r.u(29) or 60) * 1000.0 / 60.0))
        # 4th field (0.7.48): the original's bloom as cgame's r_ppZoneMix (code decode F4 exact, 2026-11-22: ADDITIVE,
        # out = S + k blur(S), k = (247/255)^(2n) x Bloom/255, n = Level + 1 tent passes). Our world light is matched
        # to the original's FINAL frames, which already carry that add, so ours takes it renormalised: out =
        # (S + k blur) / (1 + k) = mix(S, blur, k / (1 + k)) - flat areas keep their level, the dark ones gain the
        # share of light the original spreads into them. Engines without the mix read the first three fields only
        out.append((r.name, "bloom", r, "%s %d %.3f %.3f" % (tag, fade, lv / float(base), bloom_mix(lv, r.u(24))), ""))
    for r in db.of("SoundBusTrigger"):
        if r.u(15) != 2:
            continue                             # the off-map global record (Default_Mix alone)
        enter, leave = r.u(24), r.u(25)
        if enter not in snaps:
            continue
        out.append((r.name, "mix", r, mix_value(snaps, enter), mix_value(snaps, leave if leave in snaps else DEFAULT_MIX)))
    for r in db.of("IrradianceVolumeTrigger"):
        if "_INT_" in r.name:                    # interiors: a respawn inside one starts on the indoor bloom
            out.append((r.name, "interior", r, "", ""))
    return out


def emit(L, level, db, X, lines, log=print):
    """append level.coop_zn_* to the data script body; returns the zone count"""
    d = f"DATA/{level.split('_')[0]}/{level}/SOUND/"
    try:
        snaps = read_bus(L.disc.read(d + "AUDIO.BUS"))
    except Exception as e:
        log("eazones: no AUDIO.BUS", e)
        snaps = {}
    zs = zones(db, snaps)
    k = 0
    for name, kind, r, val, out in zs:
        q, yaw, hx, hy, hz = irrad_box(r, X) if kind == "interior" else _box(r, X)
        if kind == "bloom":
            hx, hy = max(hx, 40.0), max(hy, 40.0)    # a 0.66 m strip is 16u: at a 0.1 s poll a runner steps over it
        k += 1
        lines.append(f'\tlevel.coop_zn_name[{k}] = "{name}"')
        lines.append(f'\tlevel.coop_zn_kind[{k}] = "{kind}"')
        lines.append(f"\tlevel.coop_zn_pos[{k}] = ( {q[0]:.0f} {q[1]:.0f} {q[2]:.0f} )")
        lines.append(f"\tlevel.coop_zn_yaw[{k}] = {yaw:.1f}")
        lines.append(f"\tlevel.coop_zn_hx[{k}] = {max(hx, 8.0):.0f}")
        lines.append(f"\tlevel.coop_zn_hy[{k}] = {max(hy, 8.0):.0f}")
        lines.append(f"\tlevel.coop_zn_hz[{k}] = {max(hz, 48.0):.0f}")
        lines.append(f'\tlevel.coop_zn_val[{k}] = "{val}"')
        lines.append(f'\tlevel.coop_zn_out[{k}] = "{out}"')
    lines.append(f"\tlevel.coop_zn_n = {k}")
    if snaps:
        lines.append(f'\tlevel.coop_zn_mixDefault = "{mix_value(snaps, DEFAULT_MIX)}"')
    _glb = [r for r in db.of("BloomTrigger") if r.u(22) == 1]
    lines.append('\tlevel.coop_zn_fxDefault = "bloom_out 1000 1.000 %.3f"' % (
        bloom_mix(_bloom_level(_glb[0]) if _glb else 135, _glb[0].u(24) if _glb else 1)))
    ins = [z[3] for z in zs if z[1] == "bloom" and z[3].startswith("bloom_in")]
    if ins:
        lines.append(f'\tlevel.coop_zn_fxIndoor = "{ins[0]}"')
    log("eazones: %d zones (%d bloom strips, %d mix boxes, %d interiors), %d snapshots" % (
        k, sum(1 for z in zs if z[1] == "bloom"), sum(1 for z in zs if z[1] == "mix"),
        sum(1 for z in zs if z[1] == "interior"), len(snaps)))
    return k


def irrad_box(r, X):
    """an IrradianceVolumeTrigger's map-frame box: its w19..21 are HALF extents (code decode 2026-11-17: the cellar's
    INT_01 holds its own probe nodes and the leader's ICS point only at 3.35 / 4.61 m each way; read as full extents
    (_box) it held neither), so x48, not x24"""
    q = X(r.pos)
    return q, r.yaw, abs(r.f(19) or 0) * 48.0, abs(r.f(20) or 0) * 48.0, abs(r.f(21) or 0) * 48.0


def light_volumes(db, X):
    """the interior irradiance volumes as oriented map-frame boxes for flbsp's entity light grid:
    [(centre, yaw_degrees, half_x, half_y, half_z)] in ea_am_in's convention (see irrad_box)"""
    return [irrad_box(r, X) for r in db.of("IrradianceVolumeTrigger") if "_INT_" in r.name]


def inside(box, p):
    """point p (map frame) in a light_volumes() / _box() box"""
    (c, yaw, hx, hy, hz) = box
    dx, dy, dz = p[0] - c[0], p[1] - c[1], p[2] - c[2]
    a = math.radians(yaw)
    lx = dx * math.cos(a) + dy * math.sin(a)
    ly = dy * math.cos(a) - dx * math.sin(a)
    return abs(lx) <= hx and abs(ly) <= hy and abs(dz) <= hz


if __name__ == "__main__":
    import sys
    import eadb
    import eacore
    from flcore import Disc
    from flconvert import Xform
    if len(sys.argv) < 3:
        print("usage: eazones.py <disc image> <level e.g. 1_11>")
        sys.exit(2)
    disc, lv = Disc(sys.argv[1]), sys.argv[2]
    Lx = eacore.Level(disc, lv)
    allc = [v for _, vs, _ in Lx.collision() for v in vs]
    lo = [min(v[k] for v in allc) for k in range(3)]
    hi = [max(v[k] for v in allc) for k in range(3)]
    X = Xform(48.0, False, ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, 0.0))     # flconvert.convert's own X
    sn = read_bus(disc.read(f"DATA/{lv.split('_')[0]}/{lv}/SOUND/AUDIO.BUS"))
    for s in sn:
        print("snapshot", mix_value(sn, s))
    body = []
    emit(Lx, lv, eadb.DB(Lx.stream), X, body)
    print("\n".join(body))
