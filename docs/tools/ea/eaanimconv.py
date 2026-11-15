#!/usr/bin/env python3
"""European Assault clips -> MOHAA .skc for the converted disc characters. Our own code, stdlib only; runs on the
PLAYER's PC inside the converter, output only into the player's own converted pak.

Retargeting (2026-11-15): eachar.repose() carries each EA bone group ('piece') from the EA bind pose onto the stock
standing pose P by a rotation R (and the skin's offsets are expressed in the stock bones' frames in P). An EA clip
moves an EA joint by D(t) = G(t) G(bind)^-1. The stock bone that carries that joint's vertices therefore has to turn
by D'(t) R^-1 (D' = D in MOHAA's axes) from its P frame (undo the re-pose, then the clip's own turn, so a limb points
where the clip points it - R D' R^-1 turned the A-posed arms by the re-pose too): its rows at t are that rotation
applied to its P rows.
From those global frames the channels are written the way the engine reads them (mohskel: row-vector, local =
global * parent^-1; the legs as their foot IK target in model space). Positions come from the stock skeleton's
own lengths; only the pelvis moves by the EA pelvis' own translation (root motion), in the skin's scale.
"""
import math

import eaanim
import eachar
import mohskel

# stock bone <- the EA joint whose motion it carries (the 'primary' joint of eachar's piece)
PRIMARY = {"Bip01 Pelvis": "JO_pelvis", "Bip01 Spine": "JO_lumbar1", "Bip01 Spine1": "JO_lumbar2",
           "Bip01 Spine2": "JO_thoracic", "Bip01 Neck": "JO_neck", "Bip01 Head": "JO_head"}
for _s in "LR":
    PRIMARY.update({"Bip01 %s Clavicle" % _s: "JO_clavicleScapula_" + _s, "Bip01 %s UpperArm" % _s: "JO_shoulder_" + _s,
                    "Bip01 %s Forearm" % _s: "JO_elbow_" + _s, "Bip01 %s Hand" % _s: "JO_wrist_" + _s,
                    "Bip01 %s Thigh" % _s: "JO_hip_" + _s, "Bip01 %s Calf" % _s: "JO_knee_" + _s,
                    "Bip01 %s Foot" % _s: "JO_ankle_" + _s, "Bip01 %s Toe0" % _s: "JO_ball_" + _s})

C3 = [[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]      # EA model axes -> MOHAA's ((x, y, z) -> (y, -x, z))


def _mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _tr(a):
    return [[a[j][i] for j in range(3)] for i in range(3)]


def _mv(a, v):
    return [sum(a[i][k] * v[k] for k in range(3)) for i in range(3)]


def _cols(axes):
    """EA bind axes (3 model-space vectors) as a column-vector rotation matrix"""
    return [[axes[j][i] for j in range(3)] for i in range(3)]


def ea_globals(skel, sample):
    """[(rotation (column-vector 3x3), position)] per EA bone for one sampled frame {joint hash: (q, t)}"""
    G = [None] * len(skel)
    for i, b in enumerate(skel):
        p = b["parent"]
        if b["hash"] in sample:
            q, t = sample[b["hash"]]
            Rl, tl = eaanim.qmat(q), list(t)
        elif p >= 0:
            Rp, Rb = _cols(skel[p]["axes"]), _cols(b["axes"])
            Rl = _mm(_tr(Rp), Rb)
            tl = _mv(_tr(Rp), [b["pos"][k] - skel[p]["pos"][k] for k in range(3)])
        else:
            Rl, tl = [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]], list(b["pos"])
        if p < 0:
            G[i] = (Rl, tl)
        else:
            Rp, tp = G[p]
            G[i] = (_mm(Rp, Rl), [tp[k] + _mv(Rp, tl)[k] for k in range(3)])
    return G


def convert_clip(bank, clip, skel, bones, fps=30.0, root_motion=True, yaw=0.0, fwd=0.0, lat=0.0):
    """MOHAA .skc bytes of one EA clip for the stock human skeleton (bones = mohskel.read_skd_bones of the stock skd);
    yaw (degrees, about the model origin) turns the whole clip - the gunner clips are turned so the gun hands point
    straight ahead, since the engine yaws a gunner with his turret (actor_machinegunner.cpp ThinkHoldGun_TurretGun)"""
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    Rz = [[cy, -sy, 0.0], [sy, cy, 0.0], [0.0, 0.0, 1.0]]
    J = {nm: (p, eachar._axes(*a)) for nm, (p, a) in eachar.POSE.items()}
    T, s = eachar.repose(skel, J)
    byname = {b["name"]: i for i, b in enumerate(skel)}
    bind = [(_cols(b["axes"]), list(b["pos"])) for b in skel]
    bmap = {b[0]: b for b in bones}
    nf = max(1, int(round(clip["duration"] * fps)) + 1)
    pel = byname["JO_pelvis"]
    p0 = bind[pel][1]
    frames = []
    for f in range(nf):
        G = ea_globals(skel, bank.sample(clip, min(clip["duration"], f / fps)))
        rows = {}
        for m, e in PRIMARY.items():
            if e not in byname or m not in J:
                continue
            i = byname[e]
            D = _mm(G[i][0], _tr(bind[i][0]))                 # EA delta from bind (column-vector)
            Dm = _mm(_mm(C3, D), _tr(C3))
            R = T[i][2] if i in T else [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]]
            Q = _mm(Dm, _tr(R))                               # back to the EA bind direction, then the clip's turn
            rows[m] = [_mv(Rz, _mv(Q, ax)) for ax in J[m][1]]   # the P rows turned by Q (and the clip's yaw)
        ch = {}
        # pelvis: Bip01 carries its origin, Pelvis its rows
        dp = [G[pel][1][k] - p0[k] for k in range(3)] if root_motion else [0.0, 0.0, 0.0]
        dpm = [dp[1] * 100.0 * s, -dp[0] * 100.0 * s, dp[2] * 100.0 * s]
        porg = _mv(Rz, [J["Bip01 Pelvis"][0][k] + dpm[k] for k in range(3)])
        porg[0] += fwd                                  # after the turn: along the actor's forward (+X), model units
        porg[1] += lat                                  # and to his left (+Y)
        ch["Bip01 pos"] = (porg[0], porg[1], porg[2], 0.0)
        ch["Bip01 rot"] = (0.0, 0.0, 0.0, 1.0)
        ch["Bip01 Pelvis pos"] = (0.0, 0.0, 0.0, 0.0)
        ch["Bip01 Pelvis rot"] = mohskel.rows_to_quat(rows["Bip01 Pelvis"])
        glob = {"Bip01": [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0], porg],
                "Bip01 Pelvis": rows["Bip01 Pelvis"] + [porg]}
        # rotation bones down the hierarchy (file order: parents first)
        for nm, par, jt, v in bones:
            if nm in glob or par not in glob:
                continue
            P = glob[par]
            if jt == 0 and nm in rows:
                loc = _mm(rows[nm], _tr(P[:3]))                # local = global * parent^-1 (rows)
                ch[nm + " rot"] = mohskel.rows_to_quat(loc)
                glob[nm] = mohskel.mul(mohskel.quat_to_rows(ch[nm + " rot"]) + [list(v[0:3])], P)
            elif jt == 1 and nm in J and par in J:
                # a carried tag (eyes, weapon tags): its P frame relative to its parent, unchanged
                Jl = mohskel.mul([list(r) for r in J[nm][1]] + [list(J[nm][0])],
                                 mohskel.inv([list(r) for r in J[par][1]] + [list(J[par][0])]))
                ch[nm + " rot"] = mohskel.rows_to_quat(Jl[:3])
                ch[nm + " pos"] = tuple(Jl[3]) + (0.0,)
                glob[nm] = mohskel.mul(Jl, P)
            elif jt == 2:      # thigh (IK shoulder): solve the leg forward, the foot target is its result
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
    chans = sorted(frames[0], key=lambda c: [b[0] for b in bones].index(c.rsplit(" ", 1)[0])
                   if c.rsplit(" ", 1)[0] in [b[0] for b in bones] else 999)
    return mohskel.write_skc(1.0 / fps, chans, frames), frames


# ---- the clip sets the converter writes (1_11's own clip names are hashes; these are read from its state graphs) ----
# MG gunner (state graph 'MMG'): an 11-point traverse / elevation grid per state; the grid points are named by the
# clip's own aim (hands' yaw in degrees right / left of the chest's forward, hands' height in cm): r<deg>_z<cm>
MMG_GRID = {
    "idle": ("46d13d0f 67203735 51f46f11 9d382f04 98a35c90 6a189054 9bb576e4 4e953bf4 573c7193 d76d4239 b27037e7", True),
    "aim": ("20eec3c6 85fe72df 11c9ba32 3f1f63a3 4b0d3c70 aca888b7 a270753e ecb27753 1f2c6094 35b307d3 f24de2c4", True),
    "fire": ("74933e1a 07d0c0de 7bd00209 8361c23c acd05c0d 958e4d39 a556acdf b99e9086 4ad27270 e4812e32 86831a5b", True),
    "hit": ("dfe9bcc3 f56b812f ac04dddd 0f17512d b40a4375 d4e07cfa dcba45dd 151cc681 4526f423 4f80852b", False),
}
MMG_CENTRE = "51f46f11"     # l9_z124: the idle point that needs the least turn; the one-shots (enter, exit, deaths) take its yaw
# the engine seats a gunner 62.4u flat behind and 71.8u under the gun pivot (stock seat; dbx test 27 measured 62-64).
# Offsets here are in MODEL units: the character tiks scale 0.52 (eachar), so world / 0.52
MMG_FWD = 0.0
# Where the MG42's grip really is: the stock gunner (MG42_stand_idle_a, FK, x0.52) holds it 22.7u ahead, 8.6u to his
# RIGHT and 68.7u up from his origin at the stock seat 62.4 back / 71.8 down, i.e. 39.7 behind, 8.6 right of and 3.1 below
# the pivot. Our centre cell has its hands 23.0 ahead and 68.9 up on the centreline: on the STOCK seat it only needs the
# 8.6u to the right (an earlier "13u behind the pivot" grip estimate led to the 27u shift and to turretseat 36 74: wrong)
MMG_SIDE = -8.6 / 0.52
MMG_ONE = {"enter": "58f52873", "exit": "647c2159", "death": "7a12045e", "death_explosion": "573a6031"}
# ambient / scripted scenes, by the rig the level's ICS points name (level.ea_ps_rig / ea_sc_rig): the clips of that
# rig's state graph that have length (single-frame state poses left out), longest first. Alias ea_ics_<rig>_<n>.
# Each clip's root is the rig point on the floor, facing the point's yaw: the clip already carries the original's own
# root turn (ExplainsPlan and PolishingWeapon play turned 180, TyingBootLaces 80, GuardIdling 90) and seat heights
# (PolishingWeapon's pelvis 43 cm, TyingBootLaces' 51 cm over the root: the bench must be there).
SCENES = {
    "partisanidling": "d4f7a161 0a84ccf5 982e0d67",
    "crouchedpartisanfemale": "ad30af0a 614ca96c 29619877",
    "explainsplan": "cfebf641 936dea29 db40db32",
    "partisanleadersaysgofight": "e5e54e87 23edf3ec",
    "polishingweapon": "3ae7a727 72ca963c",
    "tyingbootlaces": "fca8bb38 b4858a23",
    "callsplayer": "d933ab7c 22c28d69 428633ce 0aab02d5",
    "guardidling": "8b9bc128 c3b6f033 7a4c26b6",
    "guardatpost": "1926945c 2a1ead82 510ba547",
    "guardstopsplayer": "cfe6595e fdfda7cd 87cb6845",
}


# Ordinary soldier deaths: graph 84033c53 (HitReactions.aso). Its states pick by core pose (ChooseDeathPose), hit
# type and hit location; the named states that follow are DEATH_REACT (low/prone), DEATH_REACT_EXPLOSION (by
# GetHitDirection) and DEATH_REACT_HIT_BY_VEHICLE_BACK / _FRONT. The tree keys (which location takes which clip) are
# not decoded: the clips are named by what they do, measured on the clip (facing +Y: a fall to -Y is a hit from the
# FRONT, a fall to +X - the man's right - a hit from his LEFT). <side> = where the hit came from.
DEATHS = {
    "stand_front": "f70d21c3 8767d54c 10b50cc4 6d90c4aa 7275489a 9648062a 0f415790 17067651 b11393d6",
    "stand_back": "88878a56 e622f2a5 73462e17 600146c7 6ca1f415 36d6a6d8 c83d990b",
    "stand_left": "f060e5da d7d8153b c21f76c8",
    "stand_right": "118edbec",
    "stand_back_flung": "4b8f3976 6838e0ee",
    "crouch_front": "ff247e71 5734ad48 81199f57 138f9b31",
    "crouch_back": "0b05852a",
    "crouch_right": "6140ebd2",
    "prone": "ad7d9333 4fc34180 26e83893",
    "explosion_front": "d5bce6d2",
    "explosion_back": "6ca484ca",
    "explosion_left": "a766919c",
    "explosion_right": "2f5d3268",
    "vehicle_front": "9125c233",
    "vehicle_back": "9a258b22",
}


def aim_label(bank, skel, h):
    """'r<deg>_z<cm>' / 'l<deg>_z<cm>' of a gunner clip's first frame: the hands' yaw about the chest and their height"""
    bn = {b["name"]: i for i, b in enumerate(skel)}
    G = ea_globals(skel, bank.sample(bank.clip(h), 0.0))
    wl, wr, th = G[bn["JO_wrist_L"]][1], G[bn["JO_wrist_R"]][1], G[bn["JO_thoracic"]][1]
    mid = [(wl[k] + wr[k]) / 2 for k in range(3)]
    yaw = math.degrees(math.atan2(mid[0] - th[0], mid[1] - th[1]))
    return "%s%d_z%d" % ("r" if yaw >= 0 else "l", round(abs(yaw)), round(mid[2] * 100))


def hands(bank, skel, bones, h, yaw=0.0, t=0.0):
    """(right hand, left hand) origins of a converted clip at time t, MOHAA model space (x forward, y left, z up)"""
    _, frames = convert_clip(bank, bank.clip(h), skel, bones, yaw=yaw)
    T = mohskel.fk(bones, frames[min(len(frames) - 1, int(round(t * 30)))])
    return T["Bip01 R Hand"][3], T["Bip01 L Hand"][3]


def gun_yaw(bank, skel, bones, h):
    """the yaw that turns a gunner clip so the midpoint of his hands lies straight ahead of the model origin"""
    r, l = hands(bank, skel, bones, h)
    return -math.degrees(math.atan2((r[1] + l[1]) / 2, (r[0] + l[0]) / 2))


def build(stream, level, skd_bytes, files, log=print):
    """write the clip sets as models/human/ea_<level>/anim/*.skc; returns the tik 'animations' block text"""
    import struct
    import easkin
    try:
        bank = eaanim.Bank(stream)
    except ValueError:
        return ""
    skel = easkin.skeleton(stream)
    bones = mohskel.read_skd_bones(skd_bytes)
    rows = []

    def put(alias, h, loop, yaw=0.0):
        if h not in bank.clips:
            return
        mmg = alias.startswith("mmg_")
        skc, _ = convert_clip(bank, bank.clip(h), skel, bones, yaw=yaw, fwd=MMG_FWD if mmg else 0.0,
                              lat=MMG_SIDE if mmg else 0.0)
        if loop:
            skc = skc[:8] + struct.pack("<i", struct.unpack_from("<i", skc, 8)[0] | 0x20) + skc[12:]
        files["models/human/ea_%s/anim/%s.skc" % (level, alias)] = skc
        rows.append("ea_%s\t\tanim/%s.skc" % (alias, alias))
    # the idle, aim and fire grids list their points in the same order: all three take the idle clip's label
    idle = [int(x, 16) for x in MMG_GRID["idle"][0].split()]
    lab = [aim_label(bank, skel, h) if h in bank.clips else None for h in idle]
    for state, (hs, loop) in MMG_GRID.items():
        for i, hx in enumerate(hs.split()):
            h = int(hx, 16)
            if h in bank.clips:
                tag = lab[i] if state != "hit" and i < len(lab) and lab[i] else aim_label(bank, skel, h)
                put("mmg_%s_%s" % (state, tag), h, loop, gun_yaw(bank, skel, bones, h))
    centre = gun_yaw(bank, skel, bones, int(MMG_CENTRE, 16))
    for nm, hx in MMG_ONE.items():
        put("mmg_" + nm, int(hx, 16), False, centre)
    for rig, hs in SCENES.items():
        for n, hx in enumerate(hs.split()):
            put("ics_%s_%d" % (rig, n + 1), int(hx, 16), n == 0 and rig not in ("explainsplan", "partisanleadersaysgofight", "callsplayer", "guardstopsplayer"))
    for kind, hs in DEATHS.items():
        for n, hx in enumerate(hs.split()):
            put("death_%s_%d" % (kind, n + 1), int(hx, 16), False)
    log("eaanimconv: %d clips -> models/human/ea_%s/anim" % (len(rows), level))
    return "animations\n{\n\t$path models/human/ea_%s\n%s\n}\n" % (level, "\n".join("\t" + r for r in rows))
