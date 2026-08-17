"""Aggregate a dynamic-AI A/B captured by ai_ab_test.ps1 and report it honestly.

Reads arm_OFF.log / arm_ON.log (full per-arm snapshots - qconsole.log truncates on every
server start, so offset slicing across runs reads the wrong arm).

The exposure guard is the point. Three earlier comparisons were invalidated because the two
arms saw different amounts of contact, not different AI, and nothing in the output said so.
So this prints contact FIRST and refuses to draw a conclusion when the arms are not comparable.
"""
import os
import re
import sys

B1 = re.compile(r'AIBEHAV alive=(\d+) engaging=(\d+) moving=(\d+) staticCombat=(\d+) '
                r'flanked=(\d+) \| aggr=(\d+) cover=(\d+) flank=(\d+) prone=(\d+) none=(\d+)')
B2 = re.compile(r'AIBEHAV2 window=8s engagedMoved=(\d+) repositioned=(\d+) '
                r'totalDist=(\d+) avgDist=(\d+)')
SQ = re.compile(r'SQUAD clusters=(\d+) engaged=(\d+) alerts=(\d+) search=(\d+)')
MN = re.compile(r'MANEUVER attackState=(\d+) candidates=(\d+) runtoIssued=(\d+)')


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def parse(path):
    with open(path, errors="ignore") as f:
        txt = f.read()
    b1 = [[int(v) for v in m] for m in B1.findall(txt)]
    b2 = [[int(v) for v in m] for m in B2.findall(txt)]
    sq = [[int(v) for v in m] for m in SQ.findall(txt)]
    mn = [[int(v) for v in m] for m in MN.findall(txt)]
    eng = [r[1] for r in b1]
    per = [r[2] / r[1] for r in b1 if r[1] > 0]
    em_tot = sum(r[0] for r in b2)
    dist_tot = sum(r[2] for r in b2)
    return {
        "moving_per_engaged": mean(per),
        "dist_per_mover": dist_tot / em_tot if em_tot else 0.0,
        "samples": len(b1),
        "engaging_mean": mean(eng),
        "contact_windows": sum(1 for e in eng if e > 0),
        "moving_mean": mean([r[2] for r in b1]),
        "static_mean": mean([r[3] for r in b1]),
        "roles": (mean([r[5] for r in b1]), mean([r[6] for r in b1]),
                  mean([r[7] for r in b1]), mean([r[9] for r in b1])),
        "repositioned": sum(r[1] for r in b2),
        "engagedMoved": sum(r[0] for r in b2),
        "totalDist": sum(r[2] for r in b2),
        "windows": len(b2),
        "sq_engaged_mean": mean([r[1] for r in sq]),
        "sq_alerts": sum(r[2] for r in sq),
        "mn_candidates_max": max([r[1] for r in mn], default=0),
        "mn_runto": sum(r[2] for r in mn),
    }


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "C:/mohaa-coop-dev/ai_ab_out"
    arms = {}
    for name in ("OFF", "ON"):
        p = os.path.join(d, "arm_%s.log" % name)
        if not os.path.exists(p):
            print("missing %s" % p)
            return 1
        arms[name] = parse(p)

    a, b = arms["OFF"], arms["ON"]
    print("=" * 62)
    print("EXPOSURE  (must be comparable or nothing below means anything)")
    print("  %-22s OFF=%-8.1f ON=%-8.1f" % ("engaging mean", a["engaging_mean"], b["engaging_mean"]))
    print("  %-22s OFF=%-8d ON=%-8d" % ("contact windows", a["contact_windows"], b["contact_windows"]))
    print("  %-22s OFF=%-8d ON=%-8d" % ("AIBEHAV samples", a["samples"], b["samples"]))

    lo, hi = sorted([a["engaging_mean"], b["engaging_mean"]])
    if hi <= 0:
        print("\nVERDICT: NO CONTACT IN EITHER ARM - the AI never engaged. Nothing to compare.")
        return 2
    if lo <= 0 or hi / max(lo, 1e-9) > 1.5:
        print("\nVERDICT: EXPOSURE MISMATCH (>1.5x) - do not read the RAW movement totals below.")
        print("         BUT NOTE: with coop_aiSquad on, engagement count is an OUTCOME, not a")
        print("         confound - SB2 alert propagation is SUPPOSED to wake more enemies. A")
        print("         mismatch in that direction is the squad brain working. Judge the layer")
        print("         on the NORMALISED block instead, which divides by engaged count.")
        verdict_ok = False
    else:
        verdict_ok = True

    print("-" * 62)
    print("MOVEMENT")
    for k, lbl in (("repositioned", "repositioned"), ("engagedMoved", "engagedMoved"),
                   ("totalDist", "totalDist"), ("moving_mean", "moving mean"),
                   ("static_mean", "staticCombat mean")):
        print("  %-22s OFF=%-8s ON=%-8s" % (lbl, round(a[k], 2), round(b[k], 2)))
    print("-" * 62)
    print("NORMALISED  (fair when the treatment changes how many enemies engage)")
    for k, lbl in (("moving_per_engaged", "moving / engaged"),
                   ("dist_per_mover", "dist / engagedMoved")):
        print("  %-22s OFF=%-8s ON=%-8s" % (lbl, round(a[k], 3), round(b[k], 3)))
    print("-" * 62)
    print("ROLES (aggr/cover/flank/none)")
    print("  OFF= %.0f/%.0f/%.0f/%.0f     ON= %.0f/%.0f/%.0f/%.0f" % (a["roles"] + b["roles"]))
    print("SQUAD   OFF engaged=%.2f alerts=%d | ON engaged=%.2f alerts=%d"
          % (a["sq_engaged_mean"], a["sq_alerts"], b["sq_engaged_mean"], b["sq_alerts"]))
    print("MANEUVER ON: candidates max=%d  runtoIssued=%d" % (b["mn_candidates_max"], b["mn_runto"]))
    print("=" * 62)

    if verdict_ok:
        if a["repositioned"] == 0 and b["repositioned"] == 0:
            print("VERDICT: comparable exposure, NEITHER arm repositioned. The layer is not firing.")
        elif b["repositioned"] > a["repositioned"]:
            print("VERDICT: comparable exposure; ON repositions more (%d vs %d)."
                  % (b["repositioned"], a["repositioned"]))
        else:
            print("VERDICT: comparable exposure; ON is NOT better (%d vs %d)."
                  % (b["repositioned"], a["repositioned"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
