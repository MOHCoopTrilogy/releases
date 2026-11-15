#!/usr/bin/env python3
"""Frontline level SCENE data for the mission script (our code; decoded 2026-11-10 from the .bpd/.mvd layouts, see
docs/proposals/flpolish_2026-11-10/README.md). Runs on the player's PC inside the converter and writes only level
variables into the generated data script - who is on which side, which placement group a trigger wakes, and the
motion paths of set pieces - never Frontline text or art.

.bpd section-3 record words (u32): [3] kind (1 trigger volume, 2 object, 3 actor, 10 projectile generator),
[4..6] position, [7..10] quaternion (w, x, y, z). Actor word [13] byte 1 = team (1 Allied, 2 Axis, 0 neutral).
Message ids are words in 65536..69999 past word 12: an object/actor ANSWERS to them; a trigger holds at [28] the count N,
then the N ids it SENDS, then a 2-word action (1, code) (4 = player enters, 51/52 = proximity/sight, 42 = clean-up). The trigger's
size is the high half of word [11] in decimetres.
.mvd v2: header u32 [1] version, [2] frame count, [3] flags; frames from byte 16, 32 bytes {f32 x,y,z; u32 tag;
f32 quaternion w,x,y,z}, 30 per second. Model forward = local -y (heading = quaternion yaw - 90).
"""
import math
import re
import struct

ID_LO, ID_HI = 65536, 70000
FPS = 30.0


def words(e):
    r = e["raw"]
    return struct.unpack_from("<%dI" % (len(r) // 4), r)


def kind(e):
    w = words(e)
    return w[3] if len(w) > 3 else None


def team(e):
    w = words(e)
    return (w[13] >> 8) & 255 if len(w) > 13 else 0


def ids(e):
    w = words(e)
    return [x for k, x in enumerate(w) if k > 12 and ID_LO <= x < ID_HI]


def trigger(e):
    """(radius_m, sends[ids], code) of a kind-1 record, or None"""
    w = words(e)
    if len(w) < 30 or w[3] != 1:
        return None
    n = w[28]
    if not (0 < n < 32) or 29 + n >= len(w):
        return None
    sends = [x for x in w[29:29 + n] if ID_LO <= x < ID_HI]
    # after the ids: a 2-word action, (1, code): 4 = start on player enter, 51 = proximity, 42/73/103 seen on
    # later triggers (follow-up messages to groups already started)
    code = w[30 + n] if 30 + n < len(w) else 0
    return (w[11] >> 16) / 10.0, sends, code


def state(e):
    for s in e["strs"]:
        if s in ("StartAlert", "StartIdle", "StartCurious"):
            return s[5:].lower()
    return ""


class _Frames(list):
    ticks = 2


def mvd_frames(data):
    v, n, fl = struct.unpack_from("<3I", data, 4)
    fr = _Frames(struct.unpack_from("<3fI4f", data, 16 + 32 * i) for i in range(n))
    # [flfix2 bug-11080] the header's first word is how many 60 Hz game ticks one key lasts (measured against the
    # emulator's position tracks: 1 = the P-47s, the bombs, the rockets - one key per tick; 2 = the jeep, its wheels,
    # the Stuka, the house parts, the U-boat - one key per two ticks). Everything was played at 30 keys a second, so
    # the bomber and its bombs ran at half speed (12.0 s instead of the original's 6.1 s).
    fr.ticks = v if v in (1, 2) else 2
    return fr


def _qmat(w, x, y, z):
    return ((1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
            (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
            (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)))


def mohaa_angles(q, mirror):
    """Frontline frame quaternion -> MOHAA (pitch, yaw, roll) of a model whose forward is +x (our MOHAA vehicles)"""
    m = _qmat(*q)
    # Frontline model forward = local -y (measured: the jeep's keys head 90 deg clockwise of the quaternion yaw),
    # left = local +x, up = +z
    fwd = (-m[0][1], -m[1][1], -m[2][1])
    lft = (m[0][0], m[1][0], m[2][0])
    up = (m[0][2], m[1][2], m[2][2])
    # The quaternions are stored in the MIRRORED handedness of the positions (measured on the jeep's own keys: the
    # model heading equals the path tangent of the y-mirrored path, 4 of 4 keys within 8 degrees) - so they need the
    # mirror exactly when the positions do NOT get it.
    if not mirror:
        # mirror y; the frame is re-made right-handed (left = up x forward) so it is a proper MOHAA rotation
        fwd = (fwd[0], -fwd[1], fwd[2])
        up = (up[0], -up[1], up[2])
        lft = (up[1] * fwd[2] - up[2] * fwd[1], up[2] * fwd[0] - up[0] * fwd[2], up[0] * fwd[1] - up[1] * fwd[0])
    yaw = math.degrees(math.atan2(fwd[1], fwd[0]))
    pitch = -math.degrees(math.asin(max(-1.0, min(1.0, fwd[2]))))
    # [flfix2 round 19, bug-11165] the engine's AngleVectors gives left.z = +sin(roll) (up.y = -sin(roll) at yaw 0):
    # atan2(-left.z, up.z) rolled every object the wrong way (the canal-bridge crates leaned against the deck's
    # arch instead of with it). Checked: AngleVectors(pitch, yaw, roll) now rebuilds this frame (200 random
    # rotations, axis error < 1e-6; it was up to 2.0)
    roll = math.degrees(math.atan2(lft[2], up[2]))
    return pitch, yaw, roll


def raw_angles(q, mirror=True):
    """[flpolish] MOHAA (pitch, yaw, roll) of the stored rotation itself, for Frontline's OWN meshes kept in their own
    local frame (flconvert inline models, mirrored in y like the world). Checked on the door (record 401): its 180-degree
    turn hangs the 2.6 m panel from its record point 2.5 m above the street, swinging edge in the drawn doorway."""
    # [flfix2 bug-11035] the stored quaternion is the INVERSE of the object's rotation (measured on the disc keys: with
    # the transpose the jeep body's +y is its direction of travel on every key, dot 0.99-1.00, and each wheel's axle
    # (its mesh x) stays level and across the path while it spins and ends upright = the wheel lying flat; with the
    # matrix as stored the body headed up to 180 degrees off and the wheels came to rest leaning). A yaw-only turn of
    # 180 degrees (the door, the only earlier check) is its own inverse, which is how this passed.
    m = [list(r) for r in zip(*_qmat(*q))]
    # the mesh is mirrored in y like the world (flconvert), so the rotation is conjugated by the mirror: M R M
    # [flfix2] only when the world IS mirrored; the un-mirrored world (bug-10965) takes the stored rotation as it is
    for i, j in (((0, 1), (1, 0), (1, 2), (2, 1)) if mirror else ()):
        m[i][j] = -m[i][j]
    fwd = (m[0][0], m[1][0], m[2][0])
    lft = (m[0][1], m[1][1], m[2][1])
    up = (m[0][2], m[1][2], m[2][2])
    yaw = math.degrees(math.atan2(fwd[1], fwd[0]))
    pitch = -math.degrees(math.asin(max(-1.0, min(1.0, fwd[2]))))
    # [flfix2 round 19, bug-11165] the engine's AngleVectors gives left.z = +sin(roll) (up.y = -sin(roll) at yaw 0):
    # atan2(-left.z, up.z) rolled every object the wrong way (the canal-bridge crates leaned against the deck's
    # arch instead of with it). Checked: AngleVectors(pitch, yaw, roll) now rebuilds this frame (200 random
    # rotations, axis error < 1e-6; it was up to 2.0)
    roll = math.degrees(math.atan2(lft[2], up[2]))
    return pitch, yaw, roll


def path_lines(name, frames, X, mirror, step=3, zoff=0.0, ground=None, raw=False):
    """level.fl_path_<name>_* : sampled positions / angles / times (every `step` frames + the last)"""
    idx = list(range(0, len(frames), step))
    if idx[-1] != len(frames) - 1:
        idx.append(len(frames) - 1)
    out = []
    FPS = 60.0 / getattr(frames, "ticks", 2)        # shadows the module default (30): the motion's own rate
    for k, i in enumerate(idx, 1):
        f = frames[i]
        p = X(f[:3])
        a = raw_angles(f[4:8], mirror) if raw else mohaa_angles(f[4:8], mirror)
        z = p[2] + zoff
        if ground is not None:
            g = ground(p, f)
            if g is not None:
                z = g
        out.append(f"\tlevel.fl_path_{name}[{k}] = ( {p[0]:.0f} {p[1]:.0f} {z:.0f} )")
        out.append(f"\tlevel.fl_path_{name}_ang[{k}] = ( {a[0]:.1f} {a[1]:.1f} {a[2]:.1f} )")
        out.append(f"\tlevel.fl_path_{name}_t[{k}] = {i / FPS:.2f}")
        # [flpolish] the same keys under the motion's NAME, for the generic player (coop_fl_*.scr fl_motion)
        out.append(f'\tlevel.fl_mot["{name}"][{k}] = ( {p[0]:.0f} {p[1]:.0f} {z:.0f} )')
        out.append(f'\tlevel.fl_mot_ang["{name}"][{k}] = ( {a[0]:.1f} {a[1]:.1f} {a[2]:.1f} )')
        out.append(f'\tlevel.fl_mot_t["{name}"][{k}] = {i / FPS:.2f}')
    out.append(f"\tlevel.fl_path_{name}_n = {len(idx)}")
    out.append(f'\tlevel.fl_mot_n["{name}"] = {len(idx)}')
    return out


def yaw(e, mirror):
    """MOHAA yaw of a placed record (quaternion words [7..10] = w, x, y, z; model forward = local -y)"""
    w = words(e)
    if len(w) < 11:
        return 0.0
    q = struct.unpack("<4f", struct.pack("<4I", *w[7:11]))
    return mohaa_angles(q, mirror)[1] % 360


def particle(e):
    """[flfix2 round 20] a kind-9 record's particle-system parameters, or None. Decoded 2026-11-13 from the 15 kind-9
    records of 1_1 and the by-type templates in the same .bpd (CREATEPARTICLESYSTEMBYTYPE hashes; a template is the
    same 168-byte block with its type hash in the first word, so record word k = template word k - 18). Our reading:
      [28] start colour (bytes 1..3 = R, G, B), [29] second colour (bytes 1..3) - the start colour range
      [30], [31] end colour bytes (read, not used)
      [32] high half: 1 = runs from load, 2 = waits for an event (record 8: the house smoke, which the original's
           frames show only after the house blast); low half not decoded (0, 50, 51; 255 on the beach blast)
      [33] not decoded (1, 2, 3)
      [34] emit duration in seconds, 0 = continuous (the one-shot templates: 0.1 to 1.0)
      [36..41] spawn box, [42..47] velocity range, [48..50] acceleration, all metres (per second), each axis given
           as two ends in either order
      [51..54] size, metres: [51, 52] start range, [53, 54] end range (round 22 reading: 13 shrinks 0.9-1.0 -> 0.5,
           11 / 209 / 421 differ between the pairs, the smokes repeat one pair)
      [55] particles per second (continuous systems), [56] particle life, seconds
      [57], [58] spin range; [59] the sprite (an offset into data not on this level: same value = same sprite)
    Fields marked 'read as' in FIDELITY round 20 are readings, not documentation."""
    w = words(e)
    if len(w) < 60 or w[3] != 9:
        return None
    f = lambda k: struct.unpack("<f", struct.pack("<I", w[k]))[0]          # noqa: E731
    rgb = lambda x: ((x >> 8) & 255, (x >> 16) & 255, (x >> 24) & 255)      # noqa: E731
    ax = lambda a, b: [tuple(sorted((f(a + i), f(b + i)))) for i in range(3)]   # noqa: E731
    c0, c1 = rgb(w[28]), rgb(w[29])
    return {"rgb": tuple((a + b) / 510.0 for a, b in zip(c0, c1)), "rgb0": c0, "rgb1": c1,
            "start": w[32] >> 16, "w32lo": w[32] & 0xFFFF, "w33": w[33], "dur": f(34),
            "box": ax(36, 39), "vel": ax(42, 45), "acc": (f(48), f(49), f(50)),
            "size": (min(f(51), f(52), f(53), f(54)), max(f(51), f(52), f(53), f(54))),
            "size_raw": (min(f(51), f(52)), max(f(51), f(52)), min(f(53), f(54)), max(f(53), f(54))),
            "rate": f(55), "life": f(56), "spin": (f(57), f(58)), "sprite": w[59],
            "cls": next((s for s in e["strs"] if s.startswith("Start")), "")}


def links(e):
    """[flfix2 round 22] a record's link list (word 17 = byte offset of {u32 count, u32 (category << 16 | id) ...}) as
    [(category, id)]: 1 message group, 6 trigger <-> partner, 10 AI area, 11 / 12 sound set (cbs_decode FORMAT.md 6)"""
    w = words(e)
    if len(w) < 18 or not w[17] or w[17] % 4:
        return []
    o = w[17] // 4
    if o >= len(w) or not (0 < w[o] < 64) or o + 1 + w[o] > len(w):
        return []
    return [(x >> 16, x & 0xFFFF) for x in w[o + 1:o + 1 + w[o]]]


def slots(e, k):
    """[flfix2 round 22] the messages a record's slot k sends (0 player enters, 1 player leaves, 2 object enters,
    3 object leaves, 4 used); word 22+k = byte offset of {u32 count, u32 msg ...}, 0 = empty"""
    w = words(e)
    if 22 + k >= len(w) or not w[22 + k] or w[22 + k] % 4:
        return []
    o = w[22 + k] // 4
    if o >= len(w) or not (0 < w[o] < 16) or o + 1 + w[o] > len(w):
        return []
    return list(w[o + 1:o + 1 + w[o]])


def projgen(e):
    """[flfix2 round 22] a kind-10 ProjectileGenerator record's settings, or None. Decoded 2026-11-15 from the four 1_1
    records, ProjectileGenerator.lst (state 0 init reads attr(0,25..33)) and the VM traces (TRACE_jeep: builtin 0x1c
    arguments 0x2b / 0x2c; trace/trig256: (1, 0x4f79c15b, 0.5, self, 0x11, 0.5, 0) at the trigger's tick):
      [28] high half = attr 25: the NAMED PATH the shots are spread along (.bpd section 0; 0 = fire at the target
           object instead, FIREPROJECTILE); shot s of a burst of N aims at fraction (s + 0.5) / N along it
      [29] attr 26: shots per second (timer 60 / rate ticks)   [30] attr 27: the second fire argument (0.85 default)
      [31] / [32] attr 28 / 29: shots per burst, min / max     [33] attr 31: bursts per switch-on (0 = unlimited)
      [34] / [35] attr 32 / 33: pause between bursts, min / max seconds   [37] attr 30: the projectile definition
           (a weapbul_*.dat entry hash)
    The class name (word 16) is the behaviour; a record with none is never created (1_1 rec 212)."""
    w = words(e)
    if len(w) < 36 or w[3] != 10:
        return None
    f = lambda k: struct.unpack("<f", struct.pack("<I", w[k]))[0]          # noqa: E731
    # the string scan can pick up a byte or two before the name (1_1 rec 473: 'yOProjectileGenerator')
    cls = next((s[s.find("ProjectileGenerator"):] for s in e["strs"] if "ProjectileGenerator" in s), "")
    return {"cls": cls, "path": w[28] >> 16, "rate": f(29), "arg": f(30), "burst": (w[31], w[32]), "cycles": w[33],
            "pause": (f(34), f(35)), "proj": w[37] if len(w) > 37 and cls else 0, "sound": "MG42Sound" in cls}


def weapbul(data):
    """[flfix2 round 22] weapbul_<skill>.dat -> {definition hash: entry name}: each entry ends with its mesh name, and
    the definition hash sits 5 words before it (cross-checked: 0xb975b217 = the enemy MP40 the jeep generators and
    the SoldierA_Roamer class fire). Read only to label a generator's round as bullet or rocket - no name is stored"""
    out = {}
    for m in re.finditer(rb"([A-Z0-9_]{3,})\.MSH\0", data):
        o = m.start() - 20
        if o >= 0:
            out[struct.unpack_from("<I", data, o)[0]] = m.group(1).decode()
    return out
