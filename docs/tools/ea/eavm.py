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
    if x in eadb.MSG:
        return True
    if x < 0x01000000 or eadb.is_group(x):
        return False
    import struct as _s
    f = abs(_s.unpack("<f", _s.pack("<I", x))[0])
    return not (1e-3 < f < 1e4)


def mname(x):
    return eadb.MSG.get(x) or "h%08x" % x


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
            if all(is_msg(r, x) for x in items):
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
        L(f"\tlevel.ea_sp_yaw[{n}] = {r.yaw:.0f}")
        L(f'\tlevel.ea_sp_team[{n}] = "{team}"')
        L(f'\tlevel.ea_sp_wpn[{n}] = "{GUNS.get(base(npc["weapon"]).lower(), "mp40" if team == "axis" else "ppsh")}"')
        L(f'\tlevel.ea_sp_chr[{n}] = {S(base(npc["character"]))}')
        L(f"\tlevel.ea_sp_grp[{n}] = {gid(g) if g else chr(34) * 2}")
        L(f"\tlevel.ea_sp_cnt[{n}] = {max(1, min(12, r.u(48) or 1))}")
        L(f"\tlevel.ea_sp_alive[{n}] = {max(1, min(4, r.u(55) or 1))}")
        dl = lists(r, 73)
        dg = [x for k, v in dl if k == "g" for x in v]
        dm = next((v for k, v in dl if k == "m"), ["Activate"])
        L(f"\tlevel.ea_sp_dn[{n}] = {len(dg)}")
        for k, g in enumerate(dg, 1):
            L(f'\tlevel.ea_sp_d["{n}_{k}"] = {gid(g)}')
        L(f"\tlevel.ea_sp_dmn[{n}] = {len(dm)}")
        for k, mm in enumerate(dm, 1):
            L(f'\tlevel.ea_sp_dm["{n}_{k}"] = "{mm}"')
        L(f"\tlevel.ea_sp_name[{n}] = {S(r.name)}")
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
                L(f"\tlevel.ea_ga_tn[{key}] = {len(ts)}")
                for j, x in enumerate(ts, 1):
                    L(f'\tlevel.ea_ga_t["{S(g)[1:-1]}_{k}_{j}"] = {gid(x)}')
                L(f'\tlevel.ea_ga_msg[{key}] = "{(a.messages() or ["Activate"])[0]}"')
            elif act == "PlaySound":
                s = say_of(a)
                if s:
                    L(f"\tlevel.ea_ga_say[{key}] = {S(s)}")
            elif act == "Fade":
                L(f"\tlevel.ea_ga_time[{key}] = {a.u(17) or 0}")
            elif act == "GoToScriptedGag":
                L(f"\tlevel.ea_ga_to[{key}] = {S(a.s(17))}")
            elif act == "CameraShake":
                L(f"\tlevel.ea_ga_time[{key}] = {round(a.f(18) or 0.5, 2)}")
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
    L(f"\tlevel.ea_pr_n = {n}")
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
        L(f"\tlevel.ea_tk_yaw[{n}] = {r.yaw:.0f}")
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
        L(f"\tlevel.ea_mg_yaw[{n}] = {r.yaw:.0f}")
        L(f"\tlevel.ea_mg_tower[{n}] = {1 if 'Tower' in (r.s(22) or '') else 0}")
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
            L(f"\tlevel.ea_player_yaw = {r.yaw:.0f}")
        kit = [ITEMS.get(base(t).lower()) for _k, t in r.strings() if "Powerups" in t]
        L(f'\tlevel.ea_kit = "{" ".join(k for k in kit if k)}"')
    return {"music_events": sorted(music_events), "spawn_points": sum(1 for x in lines if "ea_sp_team" in x), "logic": sum(1 for x in lines if "ea_lo_cls" in x),
            "gags": ng, "said": len(said)}
