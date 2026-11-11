#!/usr/bin/env python3
"""flfidelity - the ORIGINAL level's event list, read from the player's own disc, as a LOCAL fidelity reference
(our code). It writes a JSON + a Markdown table to a local folder (never to git: it lists Frontline's own class names
and positions per record). docs/proposals/flpolish_2026-11-10/FIDELITY.md is the committed checklist, written in our
own words from this reference.

  python flfidelity.py <image> <level> <outdir>

Per trigger (in route order, x+y falling from the drop to the docks): position, radius, action code, and every group
it sends with its members (class, team, initial state, weapon hash) and set-piece objects. Plus: pickups by kind and
position, actors that need no trigger, motion files, dialogue cue streams (fl_levels.json), music segments.
"""
import collections
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flcore  # noqa: E402
import flconvert  # noqa: E402
import flpack  # noqa: E402
import flscene  # noqa: E402


def main(image, level, outdir):
    os.makedirs(outdir, exist_ok=True)
    L = flcore.Level(flcore.Disc(image), level)
    coll = list(L.collision())
    allc = [v for _, vs, _ in coll for v in vs]
    lo = [min(v[k] for v in allc) for k in range(3)]
    hi = [max(v[k] for v in allc) for k in range(3)]
    X = flconvert.Xform(48.0, True, ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, 0.0))
    E = L.entities()
    groups = collections.defaultdict(list)
    loose = []
    pickups = collections.defaultdict(list)
    for e in E:
        names = [s for s in e["strs"] if not s.lower().startswith("start")]
        cls = names[0] if names else ""
        p = [round(v) for v in X(e["pos"])]
        k = flscene.kind(e)
        w = flscene.words(e)
        rec = {"i": e["i"], "cls": cls, "pos": p, "kind": k, "start": [s for s in e["strs"] if s.startswith(("Start", "start"))]}
        if k == 3:
            rec["team"] = {1: "allied", 2: "axis"}.get(flscene.team(e), "neutral")
            rec["state"] = flscene.state(e)
            rec["weapon_hash"] = "%08x" % w[38] if len(w) > 38 else ""
        if "StartPowerup" in e["strs"] or cls.startswith(("Health", "GrenadeAmmo", "Colt45", "M1Garand")):
            pickups[cls].append(p)
            continue
        ids = flscene.ids(e)
        if k == 1:
            continue
        if ids:
            for g in ids[:1]:
                groups[g].append(rec)
        elif k in (2, 3) and cls:
            loose.append(rec)
    trig = []
    for e in E:
        t = flscene.trigger(e)
        if not t:
            continue
        r_m, sends, code = t
        p = [round(v) for v in X(e["pos"])]
        trig.append({"i": e["i"], "pos": p, "radius": round(r_m * 48), "code": code,
                     "sends": [{"group": g, "members": groups.get(g, [])} for g in sends]})
    trig.sort(key=lambda t: -(t["pos"][0] + t["pos"][1]))
    sp = flpack.spec(level)
    ref = {"level": level, "triggers": trig, "untriggered": loose,
           "pickups": {k: v for k, v in sorted(pickups.items())},
           "motions": sorted(k for k in L.files if k.lower().endswith(".mvd")),
           "dialogue_streams": sp.get("cues", {}), "music_segments": sp.get("music", {}).get("segments", {}),
           "objective_ordinals": sp.get("chars_bum", {})}
    json.dump(ref, open(os.path.join(outdir, "fidelity_%s.json" % level), "w"), indent=1)
    lines = ["# %s - original event list (LOCAL ONLY: disc class names and positions)" % level, "",
             "| # | trigger | pos | r | code | sends -> members |", "|---|---|---|---|---|---|"]
    for n, t in enumerate(trig, 1):
        s = []
        for g in t["sends"]:
            c = collections.Counter("%s/%s" % (m["cls"], m.get("team", "")) for m in g["members"])
            s.append("%d: %s" % (g["group"], ", ".join("%dx %s" % (v, k) for k, v in c.items()) or "-"))
        lines.append("| %d | %d | %s | %d | %d | %s |" % (n, t["i"], t["pos"], t["radius"], t["code"], "; ".join(s)))
    lines += ["", "## Untriggered (present from the start)", ""]
    for m in loose:
        lines.append("- %s %s %s %s" % (m["cls"], m.get("team", ""), m["pos"], " ".join(m["start"])))
    lines += ["", "## Pickups", ""]
    for k, v in sorted(pickups.items()):
        lines.append("- %s: %d" % (k, len(v)))
    open(os.path.join(outdir, "fidelity_%s.md" % level), "w").write("\n".join(lines) + "\n")
    print("triggers", len(trig), "groups", len(groups), "untriggered", len(loose),
          "pickups", {k: len(v) for k, v in pickups.items()})


if __name__ == "__main__":
    main(*sys.argv[1:4])
