#!/usr/bin/env python3
"""eafidelity - the LOCAL fidelity reference for a European Assault level, read from the player's own disc
(level_a.str object DB via eadb.py). Frontline's flfidelity.py recipe. Our code; the output holds EA names and
positions, so it stays under H:\\hzm_work (never committed, never shipped).

usage: eafidelity.py <level_a.str> <outdir> [--offset ox oy] [--scale 48]
writes <outdir>/fidelity_<level>.json and .md: player start + kit, every trigger (volume, target groups, message),
every activation group (members: squads, spawn points with team/weapon, pickups, props, tanks), counters, timers,
dispatchers, the scripted gag sequences (Action_* in order), objectives, demo charges, MG points, music triggers,
dialogue triggers. Positions in metres and in BSP units (the converter's transform).
"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eadb  # noqa: E402

LOGIC = ("BasicTrigger", "GagTrigger", "SoundDialogueTrigger", "GagDialogueTrigger", "Counter", "BasicTimer",
         "Dispatcher", "DemoCharge", "MissionObjective", "SoundMusicTrigger", "DirectDamageTrigger", "CSATrigger")


def build(db, X):
    def P(r):
        q = X(r.pos)
        return [round(q[0]), round(q[1]), round(q[2])]
    gn = {}
    for g in sorted(db.groups):
        gn[g] = "G%x" % g
    out = {"player": None, "groups": {}, "logic": [], "gags": {}, "squads": [], "pickups": [], "props": [],
           "mmg": [], "tanks": [], "objectives": [], "charges": []}
    for r in db.of("Player"):
        out["player"] = {"name": r.name, "m": list(r.pos), "bsp": P(r), "yaw": round(r.yaw),
                         "kit": [t for _k, t in r.strings() if "Powerups" in t]}
    for g in sorted(db.groups):
        mem = db.members(g)
        snd = db.senders(g)
        out["groups"][gn[g]] = {"members": [(m.cls, m.name) for m in mem], "refs": [(s.cls, s.name) for s in snd]}
    for r in db.recs:
        if r.cls in LOGIC:
            out["logic"].append({"cls": r.cls, "name": r.name, "m": [round(v, 2) for v in r.pos], "bsp": P(r),
                                 "vol": [round(v, 3) if isinstance(v, float) else v for v in r.volume()],
                                 "to": [gn.get(x, hex(x)) for x in r.targets()], "msg": r.messages(),
                                 "str": [t for _k, t in r.strings() if not t.startswith("Z:")][:6]})
        if r.cls.startswith("Action_"):
            gag = r.s(16) or "?"
            out["gags"].setdefault(gag, []).append({"n": r.u(15), "act": r.cls[7:], "name": r.name,
                                                    "to": [gn.get(x, hex(x)) for x in r.targets()],
                                                    "msg": r.messages(), "f17": r.f(17), "u17": r.u(17)})
        if r.cls == "NPCSpawnPoint":
            n = r.npc()
            out["squads"].append({"name": r.name, "team": eadb.team_of(n["character"]), "bsp": P(r),
                                  "yaw": round(r.yaw), "group": gn.get(r.group()),
                                  "character": (n["character"] or "").split("\\")[-1],
                                  "weapon": (n["weapon"] or "").split("\\")[-1],
                                  "archetype": (n["archetype"] or "").split("\\")[-1],
                                  "death": [gn.get(x) for x in r.death_channels()]})
        if r.cls == "WeaponPowerup":
            out["pickups"].append({"name": r.name, "item": (r.s(15) or "").split("\\")[-1], "bsp": P(r),
                                   "group": gn.get(r.group())})
        if r.cls in ("SmartObject", "SMA_RailGun6") or r.cls.startswith(("SX_", "S_X", "SP_")):
            out["props"].append({"name": r.name, "cls": r.cls, "sob": (r.s(15) or "").split("\\")[-1],
                                 "bsp": P(r), "yaw": round(r.yaw), "group": gn.get(r.group())})
        if r.cls == "MMGPoint":
            out["mmg"].append({"name": r.name, "gun": (r.s(22) or "").split("\\")[-1], "bsp": P(r), "yaw": round(r.yaw)})
        if r.cls == "TreadedVehicle":
            out["tanks"].append({"name": r.name, "def": (r.s(16) or "").split("\\")[-1], "bsp": P(r),
                                 "yaw": round(r.yaw), "group": gn.get(r.group()), "squad": r.s(29),
                                 "to": [gn.get(x, hex(x)) for x in r.targets()]})
        if r.cls == "MissionObjective":
            out["objectives"].append({"name": r.name, "keys": [r.s(24), r.s(25), r.s(26)], "bsp": P(r),
                                      "to": [gn.get(x, hex(x)) for x in r.targets()]})
        if r.cls == "DemoCharge":
            out["charges"].append({"name": r.name, "bsp": P(r), "yaw": round(r.yaw),
                                   "to": [gn.get(x, hex(x)) for x in r.targets()], "msg": r.messages()})
    for k in out["gags"]:
        out["gags"][k].sort(key=lambda a: a["n"] or 0)
    return out


def md(ref, level):
    L = [f"# EA {level} fidelity reference (LOCAL ONLY - disc names and positions)", ""]
    p = ref["player"]
    if p:
        L += [f"player start {p['bsp']} yaw {p['yaw']} kit {p['kit']}", ""]
    for sec in ("objectives", "charges", "tanks", "props", "mmg"):
        L.append(f"## {sec} ({len(ref[sec])})")
        for o in ref[sec]:
            L.append("- " + json.dumps(o))
        L.append("")
    L.append(f"## logic ({len(ref['logic'])})")
    for o in ref["logic"]:
        L.append(f"- {o['cls']} {o['name']} {o['bsp']} vol={o['vol']} -> {o['to']} {o['msg']} {o['str']}")
    L.append("")
    L.append(f"## squads ({len(ref['squads'])} spawn points)")
    by = collections.defaultdict(list)
    for s in ref["squads"]:
        by[s["group"]].append(s)
    for g, ss in sorted(by.items(), key=lambda kv: str(kv[0])):
        L.append(f"- {g}: " + "; ".join(f"{s['name']} {s['team']} {s['weapon']} {s['bsp']}" for s in ss))
    L.append("")
    L.append(f"## gags ({len(ref['gags'])})")
    for g, acts in sorted(ref["gags"].items()):
        L.append(f"- {g}: " + " | ".join(f"{a['n']}:{a['act']}{a['to'] or ''}{a['msg'] or ''}" for a in acts))
    L.append("")
    L.append(f"## pickups ({len(ref['pickups'])})")
    for o in ref["pickups"]:
        L.append(f"- {o['item']} {o['bsp']} {o['group']}")
    L.append("")
    L.append("## groups")
    for g, v in ref["groups"].items():
        L.append(f"- {g}: members {v['members'][:12]} refs {v['refs'][:12]}")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("level_a")
    ap.add_argument("outdir")
    ap.add_argument("--level", default="1_11")
    ap.add_argument("--offset", nargs=2, type=float, default=(-18.212406158447266, 90.88671237230301))
    ap.add_argument("--scale", type=float, default=48.0)
    a = ap.parse_args()
    db = eadb.DB(open(a.level_a, "rb").read())

    def X(p):
        return ((p[0] - a.offset[0]) * a.scale, (p[1] - a.offset[1]) * a.scale, p[2] * a.scale)
    ref = build(db, X)
    os.makedirs(a.outdir, exist_ok=True)
    json.dump(ref, open(os.path.join(a.outdir, f"fidelity_{a.level}.json"), "w"), indent=1)
    open(os.path.join(a.outdir, f"fidelity_{a.level}.md"), "w").write(md(ref, a.level))
    print({k: len(v) if hasattr(v, "__len__") else v for k, v in ref.items()})
