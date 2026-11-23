#!/usr/bin/env python3
"""Frontline clips (flanim) -> MOHAA .skc for the converted disc characters (flchar). Our own code, stdlib only; runs
on the PLAYER's PC inside the converter, output only into the player's own converted pak.

Retargeting (2026-11-15, the European Assault route: docs/tools/ea/eaanimconv.py): flchar.repose() carries each
Frontline bone group from the disc bind pose onto the stock standing pose P by a rotation R (MOHAA axes). A disc clip
turns a disc joint by D(t) = G(t) G(bind)^-1 (G = the joint's model-space rotation; disc model axes: faces +y, left -x).
The stock bone that carries that joint's vertices turns by D'(t) R^-1 from its P frame (D' = D in MOHAA's axes):
its rows at t are that rotation applied to its P rows. Channels are written the way the engine reads them (mohskel:
row-vector, local = global * parent^-1; the legs as their foot IK target in model space). Bone lengths are the stock
skeleton's own; only the pelvis moves, by the disc pelvis' own translation scaled to the skin (flchar's girth scale s).

Poses are written 1:1 at the clip's own rate (4 ticks of 60 Hz = 15 per second); the engine interpolates between them
as the original did.

The scripted scenes are written under their own aliases fl_a<id> (fl_a<id>_<n> for the alternatives of one id), in
the disc character's tik (flchar.build), so the mission script plays them by name. A scene clip keeps its root
travel and turn in the pose (the thrown riders fly off the jeep; the actor's origin stays where the script put it).
Gate: a definition gets the block only when it is listed in OWN_ANIM (empty = converter output byte-identical).
"""
import math
import struct

import flanim
import flchar
import mohskel

# definitions (flchar hashes) whose tik carries the disc's own clips; "*" = every placed definition (the
# decodeaudit 2026-11-22 "Everything" pass: the scene clips go in; the mission script plays them by name, a
# coop_flOwnAnim 0 server keeps the stock poses). Empty = converter output byte-identical to the old one.
OWN_ANIM = {"*"}


def own(h):
    return "*" in OWN_ANIM or h in OWN_ANIM


# [decodeaudit 2026-11-22, gap 17] a clip's movement-sound opcodes (flanim OPS: action = opcode - 0xca01, the ground
# decides the sample) -> the stock cgame commands that pick the sound by the surface under the man (cg_commands.cpp
# footstep / landing / bodyfall). 0xca00 is one of the two special ids (23 / 27 in 0x80226): read as a shuffle step.
# The argument word (9 / 10 / 1 / 2 in the scene clips) is not decoded; ASSUMPTION: 10 = the right foot.
def step_cmd(op, arg):
    a = op - 0xca01
    if op == 0xca00 or 4 <= a <= 8:
        foot = "Bip01 R Foot" if arg == 10 else "Bip01 L Foot"
        return 'footstep "%s" %s' % (foot, "run" if a >= 6 else "walk")
    if a == 9:
        return "landing 0.6"
    if a == 0x12:
        return "bodyfall 1.0"
    return None

# [decodeaudit r100, senders 2] a clip's sound opcodes: c80f n = row n of <l>animSnd.som (the PLAYSOUND player; flpack
# _anim_sounds writes the alias fl<l>_anim<n>); c806 n = AEMS module 6 of GunBnk (event n + 0x65 -> BNK slot 66 + n, the
# soldiers' weapon-handling foley) - written only for the n in foley (the caller's live slots), since an empty slot
# plays nothing on the disc. On 1_1 the converted clips carry one: 6507 frame 0 c80f 2 (the gunner's line)
def snd_cmd(level, op, n, foley=()):
    pre = "fl%s" % level.replace("_", "")
    if op == 0xc80f:
        return "sound %s_anim%d" % (pre, n)
    if op == 0xc806 and n in foley:
        return "sound %s_foley%d" % (pre, n)
    return None


def anim_sound_ops(emt_bytes, level):
    """{(op, n)} of the c806 / c80f opcodes in the clips build() converts for this level"""
    emt = flanim.Emt(emt_bytes)
    out = set()
    for aid in list(SCENES) + list(globals().get("SCENES_LEVEL", {}).get(level, {})):    # SCENES_LEVEL: per-level additions
        a = emt.anims.get(aid)
        if not a:
            continue
        for ci, _w, _p in a["variants"]:
            for kind_, v_, _t in emt.events(ci):
                if kind_ == "op" and v_[0] in (0xc806, 0xc80f) and not isinstance(v_[1], tuple):
                    out.add((v_[0], v_[1]))
    return out


# stock bone <- the disc joint whose motion it carries (flchar.FL_TO_BIP's primary joint per stock bone)
PRIMARY = {"Bip01 Pelvis": "Hip", "Bip01 Spine": "spine1", "Bip01 Spine1": "spine2", "Bip01 Spine2": "chest",
           "Bip01 Neck": "neck1", "Bip01 Head": "head"}
for _s in "LR":
    PRIMARY.update({"Bip01 %s Clavicle" % _s: "scapula_" + _s, "Bip01 %s UpperArm" % _s: "uparm_" + _s,
                    "Bip01 %s Forearm" % _s: "loarm_" + _s, "Bip01 %s Hand" % _s: "hand" + _s,
                    "Bip01 %s Thigh" % _s: "thigh_" + _s, "Bip01 %s Calf" % _s: "calf_" + _s,
                    "Bip01 %s Foot" % _s: "ankle_" + _s, "Bip01 %s Toe0" % _s: "toe_" + _s})

C3 = [[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]      # disc model axes -> MOHAA's ((x, y, z) -> (y, -x, z))
I3 = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]

# the scripted scenes of 1_1 (ids from the emulator traces, H:/hzm_work/ref_xemu/TRACE_*.md): id -> loops
SCENES = {
    # jeep crew (TRACE_jeep / _wreck): ride loops driver 6500, passenger 6502, gunner 6504; thrown 6501 / 6503 /
    # 6505; the gunner's wounded loop 6506 and his push-up / rise 6507; 6508; bumps 6509-6511
    6500: True, 6501: False, 6502: True, 6503: False, 6504: True, 6505: False, 6506: True, 6507: False,
    6508: False, 6509: False, 6510: False, 6511: False,
    # interrogation (TRACE_interrogation): officer 903 / 900 idle, 2201 / 2209 idles, 2221 hit, 8301 death; victim 901
    900: True, 901: True, 903: False, 2201: True, 2209: True, 2221: False, 8301: False,
    # talkers (TRACE_germans): talker 14397, listener 14419 / 14423, notice 14140, combat 14051
    14397: True, 14419: True, 14423: True, 14140: False, 14051: False,
    # the Soldier_Say* shout (state 79 PLAYANIMATION 14228, with the line)
    14228: False,
    # MG nest crew (TRACE_mg_ambush_end): gunner 784 / 826 loops, 776 / 777 / 769 transitions; feeder 770 / 771 /
    # 778 / 779; lead 775 / 774 / 767 / 764 / 765 / 773
    784: True, 826: True, 776: False, 777: False, 769: False, 770: True, 771: False, 778: False, 779: False,
    775: True, 774: False, 767: True, 764: False, 765: False, 773: False,
}


def _mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _tr(a):
    return [[a[j][i] for j in range(3)] for i in range(3)]


def _mv(a, v):
    return [sum(a[i][k] * v[k] for k in range(3)) for i in range(3)]


def fl_globals(skl, angles, root, keep_root=True):
    """[(R column-vector 3x3, t (m))] per disc bone, disc model space, for one decoded pose"""
    n = len(skl["names"])
    G = [None] * n
    for i in range(n):
        p = skl["par"][i]
        R = flchar._euler(angles[i] if i < len(angles) else (0, 0, 0))
        if p < 0:
            yaw = math.radians(root["yaw"]) if (keep_root or not root["yaw_motion"]) else 0.0
            c, s = math.cos(yaw), math.sin(yaw)
            on = keep_root or not root["xy_motion"]
            G[i] = (_mm([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]], R),
                    [root["x"] if on else 0.0, root["y"] if on else 0.0, root["z"]])
        else:
            Rp, tp = G[p]
            G[i] = (_mm(Rp, R), [tp[k] + _mv(Rp, skl["loc"][i])[k] for k in range(3)])
    return G


def stock_pose():
    return {nm: (p, flchar._axes(*a)) for nm, (p, a) in flchar.POSE.items()}


def convert_clip(emt, ci, skl, B, bones, keep_root=True, yaw=0.0):
    """(.skc bytes, frames) of one disc clip for the stock human skeleton. B = flchar.bind(skl, body dmf) of the
    character the skin was built from; bones = mohskel.read_skd_bones of the stock skd"""
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    Rz = [[cy, -sy, 0.0], [sy, cy, 0.0], [0.0, 0.0, 1.0]]
    J = stock_pose()
    T, s = flchar.repose(B, J)
    names = skl["names"]
    idx = {nm: i for i, nm in enumerate(names)}
    bind = {nm: (B[nm][1], list(B[nm][0])) for nm in names if nm in B}
    bmap = {b[0]: b for b in bones}
    order = [b[0] for b in bones]
    info = emt.clip_info(ci)
    poses = emt.frames(ci)
    hip0 = bind["Hip"][1]
    frames = []
    for _tick, root, ang in poses:
        G = fl_globals(skl, ang, root, keep_root)
        rows = {}
        for m, e in PRIMARY.items():
            if e not in idx or m not in J or e not in bind:
                continue
            i = idx[e]
            D = _mm(G[i][0], _tr(bind[e][0]))                 # disc delta from bind (column-vector)
            Dm = _mm(_mm(C3, D), _tr(C3))
            R = T[e][2] if e in T else I3
            Q = _mm(Dm, _tr(R))                               # undo the re-pose, then the clip's own turn
            rows[m] = [_mv(Rz, _mv(Q, ax)) for ax in J[m][1]]
        ch = {}
        dp = [G[idx["Hip"]][1][k] - hip0[k] for k in range(3)]
        dpm = [dp[1] * 100.0 * s, -dp[0] * 100.0 * s, dp[2] * 100.0 * s]
        porg = _mv(Rz, [J["Bip01 Pelvis"][0][k] + dpm[k] for k in range(3)])
        ch["Bip01 pos"] = (porg[0], porg[1], porg[2], 0.0)
        ch["Bip01 rot"] = (0.0, 0.0, 0.0, 1.0)
        ch["Bip01 Pelvis pos"] = (0.0, 0.0, 0.0, 0.0)
        ch["Bip01 Pelvis rot"] = mohskel.rows_to_quat(rows["Bip01 Pelvis"])
        glob = {"Bip01": [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0], porg],
                "Bip01 Pelvis": rows["Bip01 Pelvis"] + [porg]}
        for nm, par, jt, v in bones:
            if nm in glob or par not in glob:
                continue
            P = glob[par]
            if jt == 0 and nm in rows:
                loc = _mm(rows[nm], _tr(P[:3]))                # local = global * parent^-1 (rows)
                ch[nm + " rot"] = mohskel.rows_to_quat(loc)
                glob[nm] = mohskel.mul(mohskel.quat_to_rows(ch[nm + " rot"]) + [list(v[0:3])], P)
            elif jt == 1 and nm in J and par in J:
                Jl = mohskel.mul([list(r) for r in J[nm][1]] + [list(J[nm][0])],
                                 mohskel.inv([list(r) for r in J[par][1]] + [list(J[par][0])]))
                ch[nm + " rot"] = mohskel.rows_to_quat(Jl[:3])
                ch[nm + " pos"] = tuple(Jl[3]) + (0.0,)
                glob[nm] = mohskel.mul(Jl, P)
            elif jt == 2 and nm in rows:     # thigh (IK shoulder): solve the leg forward, the foot target is its result
                side = nm.split(" ")[1]
                th, ca, fo = nm, "Bip01 %s Calf" % side, "Bip01 %s Foot" % side
                off = v[4:7]
                o = [P[3][j] + off[0] * P[0][j] + off[1] * P[1][j] + off[2] * P[2][j] for j in range(3)]
                up, lo = bmap[ca][3][0], bmap[fo][3][0]
                knee = [o[j] + rows[th][0][j] * up for j in range(3)]
                ank = [knee[j] + rows[ca][0][j] * lo for j in range(3)]
                ch[fo + " pos"] = (ank[0], ank[1], ank[2], 0.0)
                ch[fo + " rot"] = mohskel.rows_to_quat(rows[fo])
                glob[th] = rows[th] + [o]
                glob[ca] = rows[ca] + [knee]
                glob[fo] = rows[fo] + [ank]
        for side in "LR":
            fo, toe = "Bip01 %s Foot" % side, "Bip01 %s Toe0" % side
            if fo in glob and toe in rows:
                ch[toe + " rot"] = mohskel.rows_to_quat(_mm(rows[toe], _tr(glob[fo][:3])))
        ch["ORIGIN pos"], ch["ORIGIN rot"] = (0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.7071068, 0.7071068)
        frames.append(ch)
    chans = sorted(frames[0], key=lambda c: order.index(c.rsplit(" ", 1)[0]) if c.rsplit(" ", 1)[0] in order else 999)
    ft = info["frame_time"] / flanim.TICKS_PER_SECOND
    return mohskel.write_skc(ft, chans, frames), frames


def build(emt_bytes, level, skl, B, skd_bytes, files, label, log=print, foley=()):
    """write the scene clips for one disc BODY (label = its .dmf name, lower case, e.g. bm22: the retarget depends
    only on the body's bind pose, so the men who share a body share the files) as models/human/fl_<level>/anim/
    <label>/fl_a<id>[_<n>].skc; returns the tik 'animations' block text ("" when nothing was written)"""
    emt = flanim.Emt(emt_bytes)
    bones = mohskel.read_skd_bones(skd_bytes)
    rows = []
    for aid, loop in SCENES.items():
        a = emt.anims.get(aid)
        if not a:
            continue
        seen = []
        for ci, _w, _p in a["variants"]:
            if ci in seen:
                continue
            seen.append(ci)
            alias = "fl_a%d" % aid if len(seen) == 1 else "fl_a%d_%d" % (aid, len(seen))
            path = "models/human/fl_%s/anim/%s/%s.skc" % (level, label, alias)
            if path in files:
                rows.append("%s		anim/%s/%s.skc" % (alias, label, alias))
                continue
            try:
                skc, _ = convert_clip(emt, ci, skl, B, bones)       # _ = the frames
            except Exception as e:      # never fail the conversion: this alias is left out
                log("flanimconv: %s clip %d skipped (%s)" % (alias, ci, e))
                continue
            if loop:
                skc = skc[:8] + struct.pack("<i", struct.unpack_from("<i", skc, 8)[0] | 0x20) + skc[12:]
            files[path] = skc
            cmds = []
            nframes = max(1, len(_))
            for kind_, v_, t_ in emt.events(ci):
                if kind_ == "op":
                    c_ = step_cmd(v_[0], v_[1] if not isinstance(v_[1], tuple) else None)
                    if not c_ and v_[0] in (0xc806, 0xc80f) and not isinstance(v_[1], tuple):
                        c_ = snd_cmd(level, v_[0], v_[1], foley)
                    if c_:
                        fr = min(nframes - 1, int(round(t_ / emt.clip_info(ci)["frame_time"])))
                        cmds.append("\t\t\t%d %s" % (fr, c_))
            if cmds:
                rows.append("%s\t\tanim/%s/%s.skc\n\t{\n\t\tclient\n\t\t{\n%s\n\t\t}\n\t}" % (
                    alias, label, alias, "\n".join(cmds)))
            else:
                rows.append("%s\t\tanim/%s/%s.skc" % (alias, label, alias))
    if not rows:
        return ""
    log("flanimconv: %s: %d clips -> models/human/fl_%s/anim/%s" % (label, len(rows), level, label))
    return "animations\n{\n\t$path models/human/fl_%s\n%s\n}\n\n" % (level, "\n".join("\t" + r for r in rows))
