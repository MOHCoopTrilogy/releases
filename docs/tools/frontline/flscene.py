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


def mvd_frames(data):
    v, n, fl = struct.unpack_from("<3I", data, 4)
    return [struct.unpack_from("<3fI4f", data, 16 + 32 * i) for i in range(n)]


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
    roll = math.degrees(math.atan2(-lft[2], up[2]))
    return pitch, yaw, roll


def raw_angles(q):
    """[flpolish] MOHAA (pitch, yaw, roll) of the stored rotation itself, for Frontline's OWN meshes kept in their own
    local frame (flconvert inline models, mirrored in y like the world). Checked on the door (record 401): its 180-degree
    turn hangs the 2.6 m panel from its record point 2.5 m above the street, swinging edge in the drawn doorway."""
    m = [list(r) for r in _qmat(*q)]
    # the mesh is mirrored in y like the world (flconvert), so the rotation is conjugated by the mirror: M R M
    for i, j in ((0, 1), (1, 0), (1, 2), (2, 1)):
        m[i][j] = -m[i][j]
    fwd = (m[0][0], m[1][0], m[2][0])
    lft = (m[0][1], m[1][1], m[2][1])
    up = (m[0][2], m[1][2], m[2][2])
    yaw = math.degrees(math.atan2(fwd[1], fwd[0]))
    pitch = -math.degrees(math.asin(max(-1.0, min(1.0, fwd[2]))))
    roll = math.degrees(math.atan2(-lft[2], up[2]))
    return pitch, yaw, roll


def path_lines(name, frames, X, mirror, step=3, zoff=0.0, ground=None, raw=False):
    """level.fl_path_<name>_* : sampled positions / angles / times (every `step` frames + the last)"""
    idx = list(range(0, len(frames), step))
    if idx[-1] != len(frames) - 1:
        idx.append(len(frames) - 1)
    out = []
    for k, i in enumerate(idx, 1):
        f = frames[i]
        p = X(f[:3])
        a = raw_angles(f[4:8]) if raw else mohaa_angles(f[4:8], mirror)
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
