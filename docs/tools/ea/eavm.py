#!/usr/bin/env python3
"""eavm - European Assault mission logic -> the tables our mission script runs (maps/coop_ea_<l>_data.scr).
Our own code. Runs on the PLAYER's PC inside the converter; reads their own disc through eadb.py; the data script
it writes is local, never shipped.

The original level is a message graph (eadb.py): triggers, timers, counters and dispatchers send Activate /
Deactivate / ObjectiveSucceeded / Play to activation GROUPS, and squads, spawn points, pickups, props, tanks,
objectives and other logic objects that belong to a group react. Scripted "gags" are ordered Action_* lists.
maps/coop_ea_<l>.scr (our script) interprets the same graph: nothing here is hand-placed.

level vars (single frame, no waits; groups are strings "g<hex>"):
  ea_sp_*   spawn points        pos yaw team wpn grp cnt alive death name
  ea_lo_*   logic objects       cls name pos yaw shape r hx hy hz fire(enter|activate|use) gag
                                ln/l[i_k] listen groups, tn/t[i_k] targets, send, cnt, dur, say
  ea_ga_*   gag actions         n[gag], k/act/time/tn/t/msg/say/to [gag_k]
  ea_pu_*   pickups             pos item grp       ea_pr_*  props  pos yaw sob grp name
  ea_tk_*   tanks               pos yaw grp tn/t   ea_mg_*  MG points pos yaw tower
  ea_ob_*   objectives          grp key_add key_done key_pause text_add text_done
  ea_say[cue] subtitle text (the disc's own subtitles for a scripted line)
"""
import math
import re
import zlib

import eadb

TRIGGERS = ("BasicTrigger", "SoundDialogueTrigger", "GagDialogueTrigger", "GagTrigger", "CSATrigger",
            "DirectDamageTrigger")
# AI weapon names global/weapon.scr knows ('ppsh smg' fell to "setting to none": the partisans fought unarmed,
# bug-eap-aikills); the AI rifle is the Kar98k: anim/reload.scr has no AI G43 reload
GUNS = {"npcwpn_mp40": "mp40", "npcwpn_nem_mp40": "mp40", "npcwpn_gewehr": "mauser kar 98k",
        "npcwpn_ps_gewehr": "mauser kar 98k",
        "npcwpn_ppsh": "ppsh", "npcwpn_ps_ppsh": "ppsh", "npcwpn_kar98": "mauser kar 98k",
        "npcwpn_mg42": "mg42", "npcwpn_stg44": "stg44", "npcwpn_panzerschreck": "panzerschrek"}
ITEMS = {"medkit": "health", "revive": "health", "rus1_playerstick": "grenade", "playerm1bazooka": "bazooka",
         "playerppsh": "ppsh", "playergewehr": "g43", "document": "document"}


def base(s):
    return (s or "").replace("\\", "/").split("/")[-1].rsplit(".", 1)[0]


def gid(g):
    return '"g%x"' % g


def glists(r, start):
    """[(index, [groups])]: runs of `n, g1..gn` from field `start`"""
    out, i, w = [], start, r.w
    while i < len(w):
        n = w[i]
        if 1 <= n <= 16 and i + n < len(w) and all(eadb.is_group(w[i + k]) for k in range(1, n + 1)):
            out.append((i, [w[i + k] for k in range(1, n + 1)]))
            i += n + 1
            continue
        i += 1
    return out


def is_msg(r, x):
    if x in eadb.MSG or x in eadb.NAMES:
        return True
    if x < 0x01000000 or eadb.is_group(x):
        return False
    import struct as _s
    f = abs(_s.unpack("<f", _s.pack("<I", x))[0])
    return not (1e-3 < f < 1e4)


def mname(x):
    return eadb.MSG.get(x) or eadb.NAMES.get(x) or "h%08x" % x


def lists(r, start):
    """the record's ordered runs `n, item1..itemn` from field `start`: ('g', [groups]) or ('m', [message names])"""
    out, i, w = [], start, r.w
    while i < len(w):
        n = w[i]
        if 1 <= n <= 8 and i + n < len(w):
            items = [w[i + k] for k in range(1, n + 1)]
            if all(eadb.is_group(x) for x in items):
                out.append(("g", items))
                i += n + 1
                continue
            # 0.7.22: a run holding a named message is a message run even when an unnamed id in it reads as a float
            # (the railgun destroy's hbd5a5da6 beside Disable and Vanish)
            named = any(x in eadb.MSG or x in eadb.NAMES for x in items)
            if all(is_msg(r, x) for x in items) or (named and all(x >= 0x01000000 and not eadb.is_group(x) for x in items)):
                out.append(("m", [mname(x) for x in items if mname(x) not in ("CSA_DemoCharge", "Charge_Set")]))
                i += n + 1
                continue
        i += 1
    return out


def msgs_after(r, i):
    return [eadb.MSG[x] for x in r.w[i:] if x in eadb.MSG and eadb.MSG[x] not in ("CSA_DemoCharge", "Charge_Set")]


def marker(r):
    """index of the '@Trigger Fired' string field (the output event), or None"""
    for k, x in enumerate(r.w[15:], 15):
        if r.db.s(x) in ("@Trigger Fired", "Trigger Fired", "@Camera Activate"):
            return k
    return None


def shape(r, X):
    kind = r.u(15)
    c = X(r.pos)
    if kind == 1:
        return 1, max(64.0, abs(r.f(16)) * 48), 0, 0, 0
    hx, hy, hz = (abs(r.f(19) or 0) * 24, abs(r.f(20) or 0) * 24, abs(r.f(21) or 0) * 24)
    return 2, 0, max(48.0, hx), max(48.0, hy), max(64.0, hz)


def build(db, X, spot, ground, text, lines, log=print):
    """append the VM tables to `lines` (data script body). spot(q) -> engine-accepted standing spot or None,
    ground(q) -> grounded point or None, text = {key: english} from strings.viv"""
    cue = {}
    for k in text:
        cue[zlib.crc32(k.encode()) & 0xffffffff] = k
    said = set()

    def P(q):
        return "( %.0f %.0f %.0f )" % (q[0], q[1], q[2])

    def S(s):
        s = (s or "").replace("\\", "/").replace('"', "'")
        return '"' + "".join(c if 32 <= ord(c) < 127 else " " for c in s) + '"'

    def say_of(r):
        for x in r.w[15:]:
            if x in cue:
                said.add(cue[x])
                return cue[x]
        return None

    L = lines.append
    import re as _re2
    # ---- spawn points ----
    n = 0
    sp_ix = {}
    # 0.7.22: the dead-body prefabs. Their squad is the actor group of an ICS point whose rig is a dead pose
    # (amb_ics_gl_rap_DeadPoseFlatOnGround01): on the disc a posed corpse, in the build they spawned as live, armed
    # Germans (one shot the partisan woman before her scene). Marked ea_sp_dead with the pose point.
    dead_pts = []
    for ic in db.of("ICSPoint"):
        rg = "".join(sv for _k, sv in ic.strings() if sv.endswith(".xdd"))
        if "DeadPose" not in rg:
            continue
        w, i2, lsts = ic.w, 47, []
        while i2 < len(w) and len(lsts) < 3:
            c = w[i2]
            if c > 16:
                break
            lsts.append(list(w[i2 + 1:i2 + 1 + c]))
            i2 += c + 1
        for lst in lsts:
            for x in lst:
                if eadb.is_group(x):
                    dead_pts.append((x, ic.pos, ic.name))
    for r in db.of("NPCSpawnPoint"):
        npc = r.npc()
        team = eadb.team_of(npc["character"])
        if team is None:
            continue
        q = spot(X(r.pos))
        if q is None:
            log("eavm: spawn point dropped (no free spot)", r.name)
            continue
        n += 1
        g = r.group()
        L(f"\tlevel.ea_sp_pos[{n}] = ( {q[0]:.0f} {q[1]:.0f} {q[2] + 24:.0f} )")
        L(f"\tlevel.ea_sp_yaw[{n}] = {(r.yaw + 90) % 360:.0f}")      # facing = row 1
        L(f'\tlevel.ea_sp_team[{n}] = "{team}"')
        L(f'\tlevel.ea_sp_wpn[{n}] = "{GUNS.get(base(npc["weapon"]).lower(), "mp40" if team == "axis" else "ppsh")}"')
        L(f'\tlevel.ea_sp_chr[{n}] = {S(base(npc["character"]))}')
        # [dbfix] a named squadmate: the archetype's own name string (PartisanVasileva -> "Vasileva"), for the
        # original's "<name> has died!" (PlayerSquadNPCDeath)
        _an = base(npc["archetype"] or "")
        if _an and text.get(_an):
            L(f'\tlevel.ea_sp_shown[{n}] = {S(text[_an])}')
        L(f"\tlevel.ea_sp_grp[{n}] = {gid(g) if g else chr(34) * 2}")
        L(f"\tlevel.ea_sp_cnt[{n}] = {max(1, min(12, r.u(48) or 1))}")
        L(f"\tlevel.ea_sp_alive[{n}] = {max(1, min(12, r.u(50) or 1))}")      # 0.7.15: word 50 (min, max, alive-at-once sit at 48-50); word 55 was misread as it
        dl = lists(r, 73)
        dg = [x for k, v in dl if k == "g" for x in v]
        dm = next((v for k, v in dl if k == "m"), ["Activate"])
        L(f"\tlevel.ea_sp_dn[{n}] = {len(dg)}")
        for k, g in enumerate(dg, 1):
            L(f'\tlevel.ea_sp_d["{n}_{k}"] = {gid(g)}')
        L(f"\tlevel.ea_sp_dmn[{n}] = {len(dm)}")
        for k, mm in enumerate(dm, 1):
            L(f'\tlevel.ea_sp_dm["{n}_{k}"] = "{mm}"')
        # [0.7.35] when the death channel sends (code-decode agent, NPCSpawnPoint actor-gone handler 0xa1204): only if
        # "send on death" (word 45, b3a7d3aa) is set, on every Nth death of the point's men (N: word 55, 718aa23a),
        # once (deaths <= N) unless "repeat" (word 46, 98ac4b15). The counter-attack points send once, on their 4th death
        L(f"\tlevel.ea_sp_dsend[{n}] = {1 if (len(r.w) > 45 and r.u(45)) else 0}")
        L(f"\tlevel.ea_sp_drep[{n}] = {1 if (len(r.w) > 46 and r.u(46)) else 0}")
        L(f"\tlevel.ea_sp_dN[{n}] = {max(1, r.u(55) or 1) if len(r.w) > 55 else 1}")
        L(f"\tlevel.ea_sp_name[{n}] = {S(r.name)}")
        sp_ix[r.name] = n
        dp = sorted((((pp[0] - r.pos[0]) ** 2 + (pp[1] - r.pos[1]) ** 2) ** 0.5, pp, nm2) for gg, pp, nm2 in dead_pts if r.group() and gg == r.group())
        if dp:
            dq = spot(X(dp[0][1])) or X(dp[0][1])
            L(f"\tlevel.ea_sp_dead[{n}] = 1")
            L(f"\tlevel.ea_sp_deadAt[{n}] = ( {dq[0]:.0f} {dq[1]:.0f} {dq[2] + 24:.0f} )")
            log("  dead body %s at its pose point %s (%.1f m)" % (r.name, dp[0][2], dp[0][0]))
        ms = _re2.match(r"^(?:JA|BR|JP|AG|END|DR)_NPCSpawnPoint_(.+?)_(\d+)$", r.name)
        L(f"\tlevel.ea_sp_sq[{n}] = {S(ms.group(1) if ms else '')}")
    L(f"\tlevel.ea_sp_n = {n}")
    # ---- squad objectives: the positions a squad moves to (its _01 at once, later ones when their group fires) ----
    import re as _re
    n = 0
    for r in db.of("SquadObjective_New"):
        m = _re.match(r"^(?:JA|BR|JP|AG|END|DR)_SquadObjective_(.+?)_(\d+)$", r.name)
        if not m:
            continue
        q = spot(X(r.pos))
        if q is None:
            continue
        n += 1
        g = r.u(49) if len(r.w) > 49 and eadb.is_group(r.u(49)) else None
        L(f'\tlevel.ea_so_sq[{n}] = {S(m.group(1))}')
        L(f"\tlevel.ea_so_num[{n}] = {int(m.group(2))}")
        L(f"\tlevel.ea_so_pos[{n}] = ( {q[0]:.0f} {q[1]:.0f} {q[2] + 24:.0f} )")
        L(f"\tlevel.ea_so_grp[{n}] = {gid(g) if g else chr(34) * 2}")
    L(f"\tlevel.ea_so_n = {n}")
    # ---- ICS points (0.7.16): flag word 15 set, an actor group in list B and a slot-1 send list. Words from 47:
    # three head lists (A listen, B actors, C), seven target lists, seven message lists; an empty list is one 0.
    # Only slot 1 is relayed (the one the original-game trace shows firing); the other slots' events are not decoded.
    n = 0
    for r in db.of("ICSPoint"):
        w = r.w
        if len(w) < 60 or w[15] != 1:
            continue
        i, icl = 47, []
        while i < len(w) and len(icl) < 17:
            c = w[i]
            if c > 16 or i + c >= len(w) + 0 and c:
                break
            icl.append(list(w[i + 1:i + 1 + c]))
            i += c + 1
        if len(icl) < 11:
            continue
        b_, t_, m_ = icl[1], icl[3], icl[10]
        act = [x for x in m_ if eadb.MSG.get(x) == "Activate"]
        if not b_ or not t_ or not act or not all(eadb.is_group(x) for x in b_ + t_):
            continue
        n += 1
        q = X(r.pos)
        L(f"\tlevel.ea_ic_name[{n}] = {S(r.name)}")
        L(f"\tlevel.ea_ic_pos[{n}] = ( {q[0]:.0f} {q[1]:.0f} {q[2]:.0f} )")
        L(f"\tlevel.ea_ic_b[{n}] = {gid(b_[0])}")
        L(f"\tlevel.ea_ic_tn[{n}] = {len(t_)}")
        for k, g in enumerate(t_, 1):
            L(f'\tlevel.ea_ic_t["{n}_{k}"] = {gid(g)}')
    L(f"\tlevel.ea_ic_n = {n}")
    # ---- 0.7.32 (EA) ICS send slots 2-7 (sweep 2026-11-15: only slot 1 was relayed). Every ICS point, any flag:
    # slot k's targets (list 3+k-1) and its Activate / Deactivate messages (list 10+k-1); other message ids are not
    # decoded and are left out. Which rig event fires slot 2 and later is not decoded either: the script relays them
    # once the point's scene or pose has finished (an inference; slot 1 keeps its own timing, ea_ic above).
    n = 0
    for r in db.of("ICSPoint"):
        w = r.w
        if len(w) < 60:
            continue
        i, icl = 47, []
        while i < len(w) and len(icl) < 17:
            c = w[i]
            if c > 16 or i + c >= len(w) + 0 and c:
                break
            icl.append(list(w[i + 1:i + 1 + c]))
            i += c + 1
        if len(icl) < 17:
            continue
        sl = []
        for k in range(1, 7):
            tg = [x for x in icl[3 + k] if eadb.is_group(x)]
            ms = [eadb.MSG.get(x) for x in icl[10 + k] if eadb.MSG.get(x) in ("Activate", "Deactivate")]
            if tg and ms:
                sl.append((k + 1, tg, ms))
        if not sl:
            continue
        n += 1
        L(f"\tlevel.ea_isl_name[{n}] = {S(r.name)}")
        L(f"\tlevel.ea_isl_c[{n}] = {len(sl)}")
        for j, (k, tg, ms) in enumerate(sl, 1):
            L(f'\tlevel.ea_isl_k["{n}_{j}"] = {k}')
            L(f'\tlevel.ea_isl_tn["{n}_{j}"] = {len(tg)}')
            for x, g in enumerate(tg, 1):
                L(f'\tlevel.ea_isl_t["{n}_{j}_{x}"] = {gid(g)}')
            L(f'\tlevel.ea_isl_mn["{n}_{j}"] = {len(ms)}')
            for x, m in enumerate(ms, 1):
                L(f'\tlevel.ea_isl_m["{n}_{j}_{x}"] = {S(m)}')
    L(f"\tlevel.ea_isl_n = {n}")
    # ---- 0.7.20 loudspeaker points: the level's SoundDefTriggers named GERMANPA (their own sound defs are not
    # decoded). A PA announcement plays from these, not on every player. Word 23 = 1 reads as starts-on.
    n = 0
    pa_events = []
    for r in db.of("SoundDefTrigger"):
        if "GERMANPA" not in r.name.upper():
            continue
        n += 1
        q = X(r.pos)
        gr = [x for x in r.w[30:] if eadb.is_group(x)]      # word 32 (word 22 is an offset that can look like one)
        L(f"\tlevel.ea_pa_name[{n}] = {S(r.name)}")
        L(f"\tlevel.ea_pa_pos[{n}] = ( {q[0]:.0f} {q[1]:.0f} {q[2]:.0f} )")
        L(f"\tlevel.ea_pa_grp[{n}] = {gid(gr[0]) if gr else chr(34) * 2}")
        L(f"\tlevel.ea_pa_on[{n}] = {1 if len(r.w) > 23 and r.w[23] == 1 else 0}")
        pa_ev = "#%08x" % r.w[30] if len(r.w) > 30 else ""
        L(f"\tlevel.ea_pa_ev[{n}] = {S(pa_ev)}")
        if pa_ev:
            pa_events.append(pa_ev)
    L(f"\tlevel.ea_pa_n = {n}")
    # ---- 0.7.20 scripted character scenes (ICS): the rig's cue events. Each ICS point names its rig (string 16);
    # the rig's animation (<rig>.aso) is preceded in the level file by 12-byte events: u16 frame, u16 0xcaf0,
    # u32 CRC32 of the cue name, u32 0. Frames are at 30 a second (cue spacing equals the voice lengths).
    # Emitted for every ICS point with a listen group (list A) and an actor group (list B) whose rig has voice
    # cues; the skeleton animation itself is not decoded (the script plays the lines from the actor, stock pose).
    import struct as _st
    raw = getattr(db, "raw", None) or b""
    n = 0
    for r in db.of("ICSPoint"):
        w = r.w
        rig = ""
        for _i, sv in r.strings():
            if sv.endswith(".xdd"):
                rig = sv.split("/")[-1][:-4]
        if not rig or len(w) < 60:
            continue
        i, icl = 47, []
        while i < len(w) and len(icl) < 3:
            c = w[i]
            if c > 16:
                break
            icl.append(list(w[i + 1:i + 1 + c]))
            i += c + 1
        # 0.7.22: a point with a listen group but an empty actor list (Checkpoint_02 GuardStopsPlayer, "Halt") takes
        # the group of the NPC spawn point standing on it (within 4 m): inferred, the record names no actor
        sc_how = "actor list"
        sc_sp = 0
        if len(icl) >= 2 and icl[0] and not icl[1] and all(eadb.is_group(x) for x in icl[0]):
            near = []
            for sp in db.of("NPCSpawnPoint"):
                d = ((sp.pos[0] - r.pos[0]) ** 2 + (sp.pos[1] - r.pos[1]) ** 2) ** 0.5
                if d <= 4.0 and sp.name in sp_ix:
                    near.append((d, sp.name))
            if near:
                near.sort()
                sc_sp = sp_ix[near[0][1]]
                icl[1] = [0x7fffffff]
                sc_how = "spawn point %s %.1f m from the point (inferred)" % (near[0][1], near[0][0])
        if len(icl) < 2 or not icl[0] or not icl[1] or not all(eadb.is_group(x) for x in icl[0] + (icl[1] if not sc_sp else [])):
            continue
        at = raw.find((rig + ".aso").encode())
        evs = []
        if at > 0:
            o = at - 12
            lo = max(0, at - 1200)
            while o >= lo:
                fr, tag, crc, z = _st.unpack_from("<HHII", raw, o)
                if tag == 0xcaf0 and z == 0 and crc in cue and cue[crc] in text:
                    evs.append((fr, cue[crc]))
                o -= 2
        evs = sorted(set(evs))
        if not evs:
            continue
        n += 1
        q = X(r.pos)
        L(f"\tlevel.ea_sc_name[{n}] = {S(r.name)}")
        L(f"\tlevel.ea_sc_rig[{n}] = {S(rig)}")
        L(f"\tlevel.ea_sc_pos[{n}] = ( {q[0]:.0f} {q[1]:.0f} {q[2]:.0f} )")
        L(f"\tlevel.ea_sc_yaw[{n}] = {(r.yaw + 90) % 360:.0f}")
        L(f"\tlevel.ea_sc_a[{n}] = {gid(icl[0][0])}")
        if sc_sp:
            # the actor by his spawn point (a point with no group of its own): the script matches ea_sc_sp
            L(f'\tlevel.ea_sc_b[{n}] = "sp{sc_sp}"')
            L(f"\tlevel.ea_sc_sp[{n}] = {sc_sp}")
        else:
            L(f"\tlevel.ea_sc_b[{n}] = {gid(icl[1][0])}")
        L(f"\tlevel.ea_sc_cn[{n}] = {len(evs)}")
        for k, (fr, c) in enumerate(evs, 1):
            said.add(c)
            L(f'\tlevel.ea_sc_cue["{n}_{k}"] = {S(c)}')
            L(f'\tlevel.ea_sc_t["{n}_{k}"] = {fr / 30.0:.2f}')
        log("  ICS scene %s (%s, actor: %s): %s" % (r.name, rig, sc_how, ", ".join("%s@%.2f" % (c, fr / 30.0) for fr, c in evs)))
    L(f"\tlevel.ea_sc_n = {n}")
    # ---- 0.7.22 pose-only ICS points (no voice cue in the rig): the scene's actor stands on the point facing the
    # record's way and holds there until his squad is given its next order (the rig animation is not decoded: stock
    # pose). Actor = the point's actor group (list B), or the spawn point standing on it when the list is empty.
    # Dead poses are the corpses above; scenes with voice cues are emitted as scenes.
    sc_names = set()
    for ln in lines:
        mm = _re.match(r'\tlevel\.ea_sc_name\[\d+\] = "(.*)"', ln)
        if mm:
            sc_names.add(mm.group(1))
    n = 0
    # a point whose record names no actor takes the squad whose first objective stands on it (within 1 m): the
    # level binds the graveyard wall vaults, the church window jumps and the tower rig point that way
    first_at = []
    for o in db.of("SquadObjective_New"):
        mo = _re.match(r"^(?:JA|BR|JP|AG|END|DR)_SquadObjective_(.+?)_01$", o.name)
        if mo:
            first_at.append((o.pos, mo.group(1)))
    for r in list(db.of("ICSPoint")) + [x for x in db.recs if x.cls == "CreativeRigPoint"]:
        rig = ""
        for _i, sv in r.strings():
            if sv.endswith(".xdd"):
                rig = sv.replace(chr(92), "/").split("/")[-1][:-4]
        if not rig or "DeadPose" in rig or r.name in sc_names:
            continue
        if r.cls == "CreativeRigPoint":
            icl = [[], []]
        elif len(r.w) < 60:
            continue
        if r.cls == "ICSPoint":
            w, i, icl = r.w, 47, []
            while i < len(w) and len(icl) < 3:
                c = w[i]
                if c > 16:
                    break
                icl.append(list(w[i + 1:i + 1 + c]))
                i += c + 1
        if len(icl) < 2:
            continue
        b_groups = [x for x in icl[1] if eadb.is_group(x)]
        ps_sp = 0
        ps_sq = ""
        if not b_groups and not [x for x in icl[0] if eadb.is_group(x)]:
            fa = sorted((((op[0] - r.pos[0]) ** 2 + (op[1] - r.pos[1]) ** 2) ** 0.5, sq) for op, sq in first_at)
            if not fa or fa[0][0] > 1.0:
                continue
            ps_sq = fa[0][1]
        elif not b_groups:
            near = sorted((((sp.pos[0] - r.pos[0]) ** 2 + (sp.pos[1] - r.pos[1]) ** 2) ** 0.5, sp.name)
                          for sp in db.of("NPCSpawnPoint") if sp.name in sp_ix)
            near = [x for x in near if x[0] <= 4.0]
            if not near:
                continue
            ps_sp = sp_ix[near[0][1]]
        n += 1
        q = spot(X(r.pos)) or X(r.pos)
        L(f"\tlevel.ea_ps_name[{n}] = {S(r.name)}")
        L(f"\tlevel.ea_ps_rig[{n}] = {S(rig)}")
        L(f"\tlevel.ea_ps_pos[{n}] = ( {q[0]:.0f} {q[1]:.0f} {q[2] + 24:.0f} )")
        L(f"\tlevel.ea_ps_yaw[{n}] = {(r.yaw + 90) % 360:.0f}")
        L(f"\tlevel.ea_ps_b[{n}] = {gid(b_groups[0]) if b_groups else chr(34) * 2}")
        a_groups = [x for x in icl[0] if eadb.is_group(x)]
        L(f"\tlevel.ea_ps_a[{n}] = {gid(a_groups[0]) if a_groups else chr(34) * 2}")
        L(f"\tlevel.ea_ps_sp[{n}] = {ps_sp}")
        L(f"\tlevel.ea_ps_sq[{n}] = {S(ps_sq)}")
        L(f"\tlevel.ea_ps_fall[{n}] = {1 if 'DeathFromAbove' in rig else 0}")
        log("  ICS pose %s (%s): actor %s" % (r.name, rig, ("group %x" % b_groups[0]) if b_groups else
            ("squad %s (its first objective on the point)" % ps_sq) if ps_sq else ("spawn point %d (inferred)" % ps_sp)))
    L(f"\tlevel.ea_ps_n = {n}")
    # ---- logic objects ----
    music_events = set()
    n = 0
    for r in db.recs:
        if r.cls not in TRIGGERS + ("Dispatcher", "Counter", "BasicTimer", "DemoCharge", "SoundMusicTrigger"):
            continue
        listen, targets, send, fire, gag, cnt, dur, lmsg = [], [], [], "enter", "", 0, 0, ""
        mus = None

        def G(ls):
            return [x for k, v in ls if k == "g" for x in v]

        def Ms(ls):
            return [v for k, v in ls if k == "m"]
        if r.cls == "SoundMusicTrigger":
            # field 32 = the music event, 30 = its volume, 35 = 1: started by its group (36) instead of a volume
            mus = r.u(32)
            if r.u(35) == 1 and eadb.is_group(r.u(36) or 0):
                listen, fire = [r.u(36)], "activate"
            music_events.add(mus)
        elif r.cls in TRIGGERS:
            m = marker(r)
            ls = lists(r, (m or 26) + 1)
            gl = [v for k, v in ls if k == "g"]
            ml = Ms(ls)
            if r.cls == "GagTrigger":
                gag = r.s(26) or ""
                listen = G(ls)
                fire = "activate" if listen else "enter"
            elif r.cls == "GagDialogueTrigger":
                gag = next((t for _k, t in r.strings()
                            if t in {a.s(16) for a in db.recs if a.cls.startswith("Action_")}), "")
                listen = G(ls)
                fire = "activate" if listen else "enter"
            elif r.cls == "SoundDialogueTrigger" and len(gl) >= 2:
                listen, targets = gl[0], [x for v in gl[1:] for x in v]
            elif r.cls in ("CSATrigger", "DirectDamageTrigger"):
                ls = lists(r, 22)
                targets, ml = G(ls), Ms(ls)
                fire = "use" if r.cls == "CSATrigger" else "damage"
            else:
                targets = gl[0] if gl else []
            send = ml[0] if ml else []
        elif r.cls == "Dispatcher":
            # listen groups, targets, the message it listens for, the messages it sends
            ls = lists(r, 21)
            gl, ml = [v for k, v in ls if k == "g"], Ms(ls)
            listen = gl[0] if gl else []
            targets = [x for v in gl[1:] for x in v]
            if len(ml) >= 2:
                lmsg, send = ml[0][0] if ml[0] else "", ml[1]
            elif ml:
                send = ml[0]
            fire = "activate"
        elif r.cls == "Counter":
            # counts the increments on its first listen group; at the count it sends to its targets
            cnt = r.u(19) or 1
            ls = lists(r, 22)
            gl = [v for k, v in ls if k == "g"]
            listen = gl[0][:1] if gl else []
            targets = [x for v in gl[1:] for x in v]
            ml = Ms(ls)
            send = ml[0] if ml else ["Activate"]
            fire = "count"
        elif r.cls == "BasicTimer":
            dur = r.u(20) or 1
            ls = lists(r, 23)
            gl = [v for k, v in ls if k == "g"]
            listen = gl[0] if gl else []
            targets = [x for v in gl[1:] for x in v]
            ml = Ms(ls)
            send = ml[0] if ml else ["Activate"]
            fire = "activate"
        elif r.cls == "DemoCharge":
            ls = lists(r, 43)
            targets = G(ls)
            ml = Ms(ls)
            send = ml[0] if ml else ["Activate"]
            fire = "use"
            # [0.7.34] StartActive (word 34 = the class schema's +0x4c, the code-decode agent's property names): a charge
            # the original starts inactive listens on its first group list and is set only once that group is activated
            # (1_11: the comm tower's two, by the graveyard spawn trigger / the leader's ammo-dump line)
            gl_ = [v for k, v in ls if k == "g"]
            if len(r.w) > 34 and r.u(34) == 0 and len(gl_) >= 2:
                listen = gl_[0]
                targets = [x for v in gl_[1:] for x in v]
        if not (targets or listen or gag or mus is not None):
            continue
        n += 1
        q = X(r.pos)
        if r.cls in TRIGGERS + ("DemoCharge", "SoundMusicTrigger") and r.pos != (0.0, 0.0, 0.0):
            gq = ground(q)
            # records at z 0 (several music and gag triggers) sit far above the floor: look further down
            for dz in range(150, 1500, 150):
                if gq:
                    break
                gq = ground((q[0], q[1], q[2] - dz))
            if gq:
                q = gq
        L(f'\tlevel.ea_lo_cls[{n}] = "{r.cls}"')
        L(f"\tlevel.ea_lo_name[{n}] = {S(r.name)}")
        L(f"\tlevel.ea_trig_pos[{n}] = {P(q)}")
        if r.cls in ("DemoCharge", "CSATrigger"):
            # 0.7.6: where the original holds the charge / plunger (the record's own height, not the floor under
            # it): the marker the player looks for goes here
            L(f"\tlevel.ea_lo_opos[{n}] = {P(X(r.pos))}")
        L(f"\tlevel.ea_lo_yaw[{n}] = {r.yaw:.0f}")
        if r.cls in TRIGGERS + ("DemoCharge", "SoundMusicTrigger"):
            k, rad, hx, hy, hz = shape(r, X)
            if r.cls == "DemoCharge":
                k, rad = 1, 96.0
            L(f"\tlevel.ea_lo_shape[{n}] = {k}")
            L(f"\tlevel.ea_lo_r[{n}] = {rad:.0f}")
            L(f"\tlevel.ea_lo_hx[{n}] = {hx:.0f}")
            L(f"\tlevel.ea_lo_hy[{n}] = {hy:.0f}")
            L(f"\tlevel.ea_lo_hz[{n}] = {hz:.0f}")
        L(f'\tlevel.ea_lo_fire[{n}] = "{fire}"')
        L(f"\tlevel.ea_lo_gag[{n}] = {S(gag)}")
        if r.cls == "GagTrigger" and r.u(24) == 1:     # once flag (0 only on the leader's go-back gag)
            L(f"\tlevel.ea_lo_once[{n}] = 1")
        # 0.7.24: a BasicTrigger with word 25 = 0 starts switched off (5 on 1_11, none of them in any group, so
        # nothing switches them on): the cellar trigger BR_BasicTrigger_22 fired the leader's go-back line before his
        # plan speech; the original plays it only from the speech's own timer
        if r.cls == "BasicTrigger" and len(r.w) > 25 and r.u(25) == 0:
            L(f"\tlevel.ea_lo_dis[{n}] = 1")
        if r.cls == "DemoCharge" and len(r.w) > 34 and r.u(34) == 0:
            L(f"\tlevel.ea_lo_dis[{n}] = 1")
        send = send or ["Activate"]
        L(f"\tlevel.ea_lo_sn[{n}] = {len(send)}")
        for k, mm in enumerate(send, 1):
            L(f'\tlevel.ea_lo_s["{n}_{k}"] = "{mm}"')
        L(f'\tlevel.ea_lo_send[{n}] = "{send[0]}"')
        L(f'\tlevel.ea_lo_lmsg[{n}] = "{lmsg}"')
        L(f"\tlevel.ea_lo_cnt[{n}] = {cnt}")
        L(f"\tlevel.ea_lo_dur[{n}] = {dur}")
        if mus is not None:
            L(f"\tlevel.ea_lo_mus[{n}] = {mus}")
        L(f"\tlevel.ea_lo_ln[{n}] = {len(listen)}")
        for k, g in enumerate(listen, 1):
            L(f'\tlevel.ea_lo_l["{n}_{k}"] = {gid(g)}')
        L(f"\tlevel.ea_lo_tn[{n}] = {len(targets)}")
        for k, g in enumerate(targets, 1):
            L(f'\tlevel.ea_lo_t["{n}_{k}"] = {gid(g)}')
        s = say_of(r)
        if s:
            L(f"\tlevel.ea_lo_say[{n}] = {S(s)}")
    L(f"\tlevel.ea_lo_n = {n}")
    # ---- gags (every Action_* list a trigger or another gag names) ----
    want = set()
    for r in db.recs:
        if r.cls in ("GagTrigger", "GagDialogueTrigger"):
            for _k, t in r.strings():
                want.add(t)
    acts = {}
    for r in db.recs:
        if r.cls.startswith("Action_") and r.s(16):
            acts.setdefault(r.s(16), []).append(r)
    for g in list(acts):
        for a in acts[g]:
            if a.cls == "Action_GoToScriptedGag" and a.s(17):
                want.add(a.s(17))
    # a gag no trigger names (run by a scripted-animation point we do not port) chains after the gag that
    # ACTIVATES the group its first message DEACTIVATES (the partisan leader's speech -> his go-back timer)
    def first_msg(seq):
        for a in seq:
            if a.cls == "Action_Message":
                gl = lists(a, 17)
                return [x for k, v in gl if k == "g" for x in v], (a.messages() or ["Activate"])[0]
        return [], None
    after = {}
    for g in sorted(acts):
        if g in want:
            continue
        seq = sorted(acts[g], key=lambda a: a.u(15) or 0)
        gs, m = first_msg(seq)
        if m != "Deactivate" or not gs:
            continue
        for h in sorted(want):
            if h not in acts or h in after:
                continue
            for a in acts[h]:
                if a.cls == "Action_Message" and (a.messages() or ["Activate"])[0] == "Activate":
                    hg = [x for k, v in lists(a, 17) if k == "g" for x in v]
                    if set(gs) & set(hg):
                        after[h] = g
                        break
    want |= set(after.values())
    for h, g in sorted(after.items()):
        L(f"\tlevel.ea_ga_after[{S(h)}] = {S(g)}")
    ng = 0
    for g in sorted(acts):
        if g not in want:
            continue
        ng += 1
        seq = sorted(acts[g], key=lambda a: a.u(15) or 0)
        L(f'\tlevel.ea_ga_n[{S(g)}] = {len(seq)}')
        for k, a in enumerate(seq, 1):
            key = '"%s_%d"' % (S(g)[1:-1], k)
            act = a.cls[7:]
            L(f'\tlevel.ea_ga_act[{key}] = "{act}"')
            if act == "Wait":
                L(f"\tlevel.ea_ga_time[{key}] = {a.u(17) if (a.u(17) or 0) < 600 else round(a.f(17), 2)}")
            elif act in ("Message", "WaitForMessage"):
                gl = lists(a, 17)
                ts = [x for k, v in gl if k == "g" for x in v] or [x for x in a.w[17:] if eadb.is_group(x)]
                gm = next((v for k, v in gl if k == "m"), None)
                if gm:
                    L(f'\tlevel.ea_ga_msg2[{key}] = "{gm[-1]}"')
                    L(f"\tlevel.ea_ga_mn[{key}] = {len(gm)}")
                    for j, x in enumerate(gm, 1):
                        L(f'\tlevel.ea_ga_m["{S(g)[1:-1]}_{k}_{j}"] = "{x}"')
                L(f"\tlevel.ea_ga_tn[{key}] = {len(ts)}")
                for j, x in enumerate(ts, 1):
                    L(f'\tlevel.ea_ga_t["{S(g)[1:-1]}_{k}_{j}"] = {gid(x)}')
                L(f'\tlevel.ea_ga_msg[{key}] = "{(a.messages() or ["Activate"])[0]}"')
            elif act == "PlaySound":
                s = say_of(a)
                if s:
                    L(f"\tlevel.ea_ga_say[{key}] = {S(s)}")
                    if g.endswith("_PA") and "_GENPC" in s:
                        L(f"\tlevel.ea_pa_cue[{S(s)}] = 1")
            elif act == "Fade":
                L(f"\tlevel.ea_ga_time[{key}] = {a.u(17) or 0}")
            elif act == "GoToScriptedGag":
                L(f"\tlevel.ea_ga_to[{key}] = {S(a.s(17))}")
            elif act == "CameraShake":
                L(f"\tlevel.ea_ga_time[{key}] = {round(a.f(18) or 0.5, 2)}")
            elif act == "ChangeGPSBehavior":
                # [0.7.32] the squad it hands from its scripted objectives to squad AI (word 18: the squad name; the
                # record has no other parameter - a 3x4 identity transform and the action order)
                sq = a.s(18) or ([t for _k, t in a.strings()][-1:] or [""])[0]
                L(f"\tlevel.ea_ga_sq[{key}] = {S(sq)}")
    L(f"\tlevel.ea_ga_count = {ng}")
    # ---- pickups, props, tanks, MG points, objectives ----
    n = 0
    for r in db.of("WeaponPowerup"):
        it = ITEMS.get(base(r.s(15)).lower())
        if not it:
            continue
        q = ground(X(r.pos))
        if q is None:
            continue
        n += 1
        g = r.group()
        L(f"\tlevel.ea_pu_pos[{n}] = {P(q)}")
        L(f'\tlevel.ea_pu_item[{n}] = "{it}"')
        L(f"\tlevel.ea_pu_grp[{n}] = {gid(g) if g else chr(34) * 2}")
    L(f"\tlevel.ea_pu_n = {n}")
    n = 0
    for r in db.recs:
        if not (r.cls in ("SmartObject", "SMA_RailGun6") or r.cls.startswith(("SX_", "S_X", "SP_"))):
            continue
        q = ground(X(r.pos)) or X(r.pos)
        n += 1
        g = r.group()
        L(f"\tlevel.ea_pr_pos[{n}] = {P(q)}")
        L(f"\tlevel.ea_pr_yaw[{n}] = {r.yaw:.0f}")
        L(f'\tlevel.ea_pr_sob[{n}] = {S(base(r.s(15)))}')
        L(f"\tlevel.ea_pr_name[{n}] = {S(r.name)}")
        L(f"\tlevel.ea_pr_grp[{n}] = {gid(g) if g else chr(34) * 2}")
        # [dbfix] a breakable smart object names its break package at word 18 (the tombstones' dust and debris)
        bx = r.s(18) if r.cls.startswith(("SX_", "S_X")) else None
        if bx and bx.lower().endswith(".xpd"):
            L(f"\tlevel.ea_pr_bfx[{n}] = {S(base(bx))}")
    L(f"\tlevel.ea_pr_n = {n}")
    # ---- [dbfix 0.7.27] damage detection volumes: a shot into the box sends its messages (the checkpoint volume
    # Deactivates the checkpoint scene's group: the guards stop playing it and fight). Size from the .sob name
    # (S_FX_<x>x<y>x<z>_DamageDetectionVolume, metres, the object's own axes), turned by the record's yaw ----
    n = 0
    for r in db.recs:
        m = re.search(r"S_FX_(\d+)x(\d+)x(\d+)_DamageDetectionVolume", r.cls)
        if not m or r.pos == (0.0, 0.0, 0.0) or not r.targets():
            continue
        n += 1
        sx, sy, sz = (float(v) for v in m.groups())
        q0, q1 = X((0.0, 0.0, 0.0)), X((1.0, 0.0, 0.0))
        u = abs(q1[0] - q0[0]) or 48.0          # map units per metre
        L(f"\tlevel.ea_dv_pos[{n}] = {P(X(r.pos))}")
        L(f"\tlevel.ea_dv_yaw[{n}] = {r.yaw:.0f}")
        L(f"\tlevel.ea_dv_half[{n}] = ( {sx * u / 2:.0f} {sy * u / 2:.0f} {sz * u / 2:.0f} )")
        L(f"\tlevel.ea_dv_name[{n}] = {S(r.name)}")
        msgs = r.messages() or ["Activate"]
        tg = r.targets()
        L(f"\tlevel.ea_dv_tn[{n}] = {len(tg)}")
        for k, t in enumerate(tg, 1):
            L(f'\tlevel.ea_dv_t["{n}_{k}"] = {gid(t)}')
            L(f'\tlevel.ea_dv_m["{n}_{k}"] = "{msgs[min(k, len(msgs)) - 1]}"')
    L(f"\tlevel.ea_dv_n = {n}")
    # ---- [dbfix 0.7.27] dynamic lights with an animated light (DynamicLight_Generic + AnimLightFlicker: the
    # flickering light in the village). Colour, radius and the flicker's timing are not decoded: the script uses a
    # stock firelight (a listed deviation) ----
    n = 0
    for r in db.recs:
        if not r.cls.startswith("DynamicLight_Generic") or r.pos == (0.0, 0.0, 0.0):
            continue
        anim = [t for _k, t in r.strings() if t.startswith("AnimLight")]
        n += 1
        L(f"\tlevel.ea_dl_pos[{n}] = {P(X(r.pos))}")
        L(f"\tlevel.ea_dl_anim[{n}] = {S(anim[0] if anim else '')}")
        L(f"\tlevel.ea_dl_name[{n}] = {S(r.name)}")
    L(f"\tlevel.ea_dl_n = {n}")
    # ---- [dbfix 0.7.27] the other SoundDefTriggers (fire loops, barbed wire, the plunger; the PA points are above):
    # sphere radius (word 16, m), the sound definition's hash (word 30: 6 distinct sounds on 1_11, ref_xemu
    # TRACE_ea_sounds.md), looping flag (word 23), one-shot by message (words 25-26), group list (31: count, 32..) ----
    n = 0
    for r in db.of("SoundDefTrigger"):
        if "GERMANPA" in r.name.upper() or r.pos == (0.0, 0.0, 0.0) or len(r.w) < 31:
            continue
        n += 1
        q0, q1 = X((0.0, 0.0, 0.0)), X((1.0, 0.0, 0.0))
        u = abs(q1[0] - q0[0]) or 48.0
        cnt = (r.u(31) or 0) if len(r.w) > 31 else 0
        grs = [r.u(32 + k) for k in range(min(cnt, 4)) if len(r.w) > 32 + k]
        L(f"\tlevel.ea_sd_pos[{n}] = {P(X(r.pos))}")
        L(f"\tlevel.ea_sd_r[{n}] = {max(32.0, r.f(16) * u):.0f}")
        L(f'\tlevel.ea_sd_hash[{n}] = "{r.u(30):08x}"')
        L(f"\tlevel.ea_sd_loop[{n}] = {1 if r.u(23) == 1 else 0}")
        L(f"\tlevel.ea_sd_once[{n}] = {1 if (r.u(25) == 1 or r.u(26) == 1) else 0}")
        L(f"\tlevel.ea_sd_grp[{n}] = {gid(grs[0]) if grs else chr(34) * 2}")
        L(f"\tlevel.ea_sd_name[{n}] = {S(r.name)}")
    L(f"\tlevel.ea_sd_n = {n}")
    # ---- effects packages (fires, smoke, fog, explosions): the .xpd name, its place, the group that plays it ----
    n = 0
    for r in db.of("EffectsPackage"):
        xp = [t for _k, t in r.strings() if t.lower().endswith(".xpd")]
        if not xp or r.pos == (0.0, 0.0, 0.0):
            continue
        n += 1
        gl = [x for k, v in lists(r, 15) if k == "g" for x in v]
        L(f"\tlevel.ea_fx_pos[{n}] = {P(X(r.pos))}")
        L(f"\tlevel.ea_fx_name[{n}] = {S(base(xp[0]))}")
        # the placement's own turn (its systems lie along a roof slope): forward = row 0, up = row 2 of the record
        f0, l0, u0 = r.rot[0:3], r.rot[3:6], r.rot[6:9]
        pit = -math.degrees(math.asin(max(-1.0, min(1.0, f0[2]))))
        yw = math.degrees(math.atan2(f0[1] * X.m, f0[0])) % 360
        rl = math.degrees(math.atan2(l0[2] * X.m, u0[2]))
        L(f"\tlevel.ea_fx_ang[{n}] = ( {pit:.1f} {yw:.1f} {rl:.1f} )")
        L(f"\tlevel.ea_fx_grp[{n}] = {gid(gl[0]) if gl else chr(34) * 2}")
    L(f"\tlevel.ea_fx_n = {n}")
    n = 0
    for r in db.of("TreadedVehicle"):
        q = ground(X(r.pos)) or X(r.pos)
        n += 1
        L(f"\tlevel.ea_tk_pos[{n}] = {P(q)}")
        L(f"\tlevel.ea_tk_yaw[{n}] = {(r.yaw + 90) % 360:.0f}")      # facing = row 1
        L(f"\tlevel.ea_tk_sq[{n}] = {S(r.s(29) or '')}")
        L(f"\tlevel.ea_tk_grp[{n}] = {gid(r.group()) if r.group() else chr(34) * 2}")
        tl = lists(r, 30)
        ts = [x for k, v in tl if k == "g" for x in v if x != r.group()]
        tm = next((v for k, v in tl if k == "m"), ["Activate"])
        L(f'\tlevel.ea_tk_msg[{n}] = "{tm[0]}"')
        L(f"\tlevel.ea_tk_tn[{n}] = {len(ts)}")
        for k, g in enumerate(ts, 1):
            L(f'\tlevel.ea_tk_t["{n}_{k}"] = {gid(g)}')
    L(f"\tlevel.ea_tk_n = {n}")
    n = 0
    for r in db.of("MMGPoint"):
        q = ground(X(r.pos)) or X(r.pos)
        n += 1
        L(f"\tlevel.ea_mg_pos[{n}] = {P(q)}")
        # [0.7.36] the MMG point's own height: ea_mg_pos is grounded, and on the railgun deck and the wall nests the ground
        # under the point lies 30-40u lower; the disc's pole mount stands level.ea_poleH over THIS point. And the crew's
        # own floor: the nearest SquadObjective (within 160u; 13-65u under the point on 1_11), where the original's crew
        # stands behind the gun
        _mp = X(r.pos)
        L(f"\tlevel.ea_mg_pz[{n}] = {_mp[2]:.1f}")
        _co = sorted(((((X(o.pos)[0] - _mp[0]) ** 2 + (X(o.pos)[1] - _mp[1]) ** 2) ** 0.5, X(o.pos))
                      for o in db.of("SquadObjective_New")), key=lambda t: t[0])
        if _co and _co[0][0] <= 160:
            L(f"\tlevel.ea_mg_cz[{n}] = {_co[0][1][2]:.1f}")
        # the gun's squad: the one whose first SquadObjective the level places at this MMG point (within 120u);
        # MMG points carry no link of their own
        first = {}
        for o in db.of("SquadObjective_New"):
            mo = _re.match(r"^(?:JA|BR|JP|AG|END|DR)_SquadObjective_(.+?)_(\d+)$", o.name)
            if mo and (mo.group(1) not in first or int(mo.group(2)) < first[mo.group(1)][0]):
                first[mo.group(1)] = (int(mo.group(2)), X(o.pos))
        mp = X(r.pos)
        cand = sorted((((p[0] - mp[0]) ** 2 + (p[1] - mp[1]) ** 2) ** 0.5, sq) for sq, (_k, p) in first.items())
        # 0.7.20: the record's own order first. A SquadObjective whose tactic (string 23) is a StayOnMMG one and that
        # sits at this MMG point (within 120u) names the squad the level orders onto the gun, and from which
        # objective number. Only a gun with no such objective falls back to the nearest first objective (192u).
        stay = []
        for o in db.of("SquadObjective_New"):
            mo = _re.match(r"^(?:JA|BR|JP|AG|END|DR)_SquadObjective_(.+?)_(\d+)$", o.name)
            if not mo or "StayOnMMG" not in (o.s(23) or ""):
                continue
            op = X(o.pos)
            if ((op[0] - mp[0]) ** 2 + (op[1] - mp[1]) ** 2) ** 0.5 <= 120:
                stay.append((int(mo.group(2)), mo.group(1)))
        stay.sort()
        if stay:
            mg_sq, mg_obj, mg_how = stay[0][1], stay[0][0], "StayOnMMG objective"
        elif cand and cand[0][0] <= 192:
            mg_sq, mg_obj, mg_how = cand[0][1], 1, "nearest first objective %.0fu" % cand[0][0]
        else:
            mg_sq, mg_obj, mg_how = "", 1, "no squad"
        log("  MMG %d %s: squad %s from objective %d (%s)" % (n, r.name, mg_sq or "-", mg_obj, mg_how))
        L(f"\tlevel.ea_mg_sq[{n}] = {S(mg_sq)}")
        L(f"\tlevel.ea_mg_obj[{n}] = {mg_obj}")
        L(f"\tlevel.ea_mg_yaw[{n}] = {(r.yaw + 90) % 360:.0f}")      # facing = row 1
        L(f"\tlevel.ea_mg_tower[{n}] = {1 if 'Tower' in (r.s(22) or '') else 0}")
        if len(r.w) > 43 and eadb.is_group(r.w[43]):
            L(f"\tlevel.ea_mg_grp[{n}] = {gid(r.w[43])}")
    L(f"\tlevel.ea_mg_n = {n}")
    n = 0
    for r in db.of("MissionObjective"):
        keys = [r.s(24), r.s(25), r.s(26)]
        n += 1
        L(f"\tlevel.ea_ob_grp[{n}] = {gid(r.u(38)) if eadb.is_group(r.u(38) or 0) else chr(34) * 2}")
        L(f"\tlevel.ea_ob_name[{n}] = {S(r.name)}")
        L(f"\tlevel.ea_ob_pos[{n}] = {P(X(r.pos))}")
        L(f"\tlevel.ea_ob_add[{n}] = {S(text.get(keys[1], keys[1]))}")
        L(f"\tlevel.ea_ob_done[{n}] = {S(text.get(keys[2], keys[2]))}")
    L(f"\tlevel.ea_ob_n = {n}")
    for k in sorted(said):
        if k in text:
            L(f"\tlevel.ea_say[{S(k)}] = {S(text[k])}")
    for r in db.of("Player"):
        q = spot(X(r.pos))
        if q:
            L(f"\tlevel.ea_player = ( {q[0]:.0f} {q[1]:.0f} {q[2] + 24:.0f} )")
            L(f"\tlevel.ea_player_yaw = {(r.yaw + 90) % 360:.0f}")
        kit = [ITEMS.get(base(t).lower()) for _k, t in r.strings() if "Powerups" in t]
        L(f'\tlevel.ea_kit = "{" ".join(k for k in kit if k)}"')
    return {"pa_events": pa_events, "music_events": sorted(music_events), "spawn_points": sum(1 for x in lines if "ea_sp_team" in x), "logic": sum(1 for x in lines if "ea_lo_cls" in x),
            "gags": ng, "said": len(said)}
