"""impact_sheet.py - in-game impact patterns from run_recoil.py logs: every round's REAL direction as the server traced
it (^~^~^ RECOILSHOT, after spread) relative to the burst's fixed start (^~^~^ RCLBURST), drawn on a wall 10 m away.

    python impact_sheet.py <run dir> [<run dir> ...] --out <png> [--title T]
"""
import math
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

KINDS = ["aimed", "hip", "crouch", "prone"]
NAMES = {"thompson": "Thompson M1A1", "mp40": "MP40", "ppsh": "PPSh-41", "sten": "Sten Mk II", "bar": "BAR",
         "fg42": "FG 42", "stg44": "StG 44", "bren": "Bren", "mg42": "MG 42 (unmounted)", "garand": "M1 Garand",
         "kar98": "Kar98k", "carbine": "M1 Carbine", "colt": "Colt M1911"}
WALL = 10.0   # metres


def parse(path):
    groups = {}
    cur = None
    for l in open(path, encoding="latin-1"):
        m = re.search(r"\^~\^~\^ RCLBURST (\S+) (\S+) (-?[\d.]+) (-?[\d.]+)", l)
        if m:
            cur = (m.group(1), m.group(2))
            groups[cur] = {"p0": float(m.group(3)), "y0": float(m.group(4)), "shots": [], "pat": []}
            continue
        if re.search(r"\^~\^~\^ RCLEND", l):
            cur = None
            continue
        if cur is None:
            continue
        m = re.search(r"\^~\^~\^ RCP t=\d+ aim=(-?[\d.]+) (-?[\d.]+)", l)
        if m and not groups[cur]["shots"]:
            # the burst's fixed start = the aim (predicted view) on the last frame before the first round
            groups[cur]["p0"], groups[cur]["y0"] = float(m.group(1)), float(m.group(2))
            continue
        m = re.search(r"RECOILSHOT t=[\d.]+ pitch=(-?[\d.]+) yaw=(-?[\d.]+)", l)
        if m:
            g = groups[cur]
            dp = (float(m.group(1)) - g["p0"] + 180.0) % 360.0 - 180.0
            dy = (float(m.group(2)) - g["y0"] + 180.0) % 360.0 - 180.0
            # pitch: + is DOWN in the engine; yaw: + is LEFT. Wall coords: x right, y up (metres at 10 m)
            g["shots"].append((-math.tan(math.radians(dy)) * WALL, -math.tan(math.radians(dp)) * WALL))
        m = re.search(r"RECOILPAT gun=\S+ n=(\d+) .*prone=(\d) duck=(\d)", l)
        if m:
            groups[cur]["pat"].append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    return groups


def main():
    runs = [a for a in sys.argv[1:] if not a.startswith("--") and os.path.isdir(a)]
    out = sys.argv[sys.argv.index("--out") + 1]
    title = sys.argv[sys.argv.index("--title") + 1] if "--title" in sys.argv else "In-game impact patterns"
    groups = {}
    for r in runs:
        groups.update(parse(os.path.join(r, "qconsole.log")))
    guns = []
    for (g, k) in groups:
        if g not in guns:
            guns.append(g)
    fig, axes = plt.subplots(len(guns), 4, figsize=(4 * 2.3, len(guns) * 2.6), squeeze=False)
    stats = []
    for a, g in enumerate(guns):
        for b, k in enumerate(KINDS):
            ax = axes[a][b]
            gr = groups.get((g, k))
            if gr and gr["shots"]:
                xs = [x for x, _ in gr["shots"]]
                ys = [y for _, y in gr["shots"]]
                ax.scatter(xs, ys, s=7, c=range(len(xs)), cmap="viridis")
                ax.plot(xs[:1], ys[:1], "r+", ms=9)
                stance = ""
                if gr["pat"]:
                    pr = sum(p[1] for p in gr["pat"]) / len(gr["pat"])
                    du = sum(p[2] for p in gr["pat"]) / len(gr["pat"])
                    stance = " pr%.0f du%.0f" % (pr, du)
                ax.set_title("%s - %s (%d)%s" % (NAMES.get(g, g), k, len(xs), stance), fontsize=6.5)
                stats.append("%s\t%s\t%d\t%.2f\t%.2f" % (g, k, len(xs), max(ys), xs[-1]))
            else:
                ax.set_title("%s - %s (none)" % (NAMES.get(g, g), k), fontsize=6.5)
            ax.set_xlim(-1.2, 1.2)
            ax.set_ylim(-0.4, 2.2)
            ax.set_aspect("equal")
            ax.axhline(0, color="#999", lw=0.4)
            ax.axvline(0, color="#999", lw=0.4)
            ax.grid(True, lw=0.25)
            ax.tick_params(labelsize=5)
    fig.suptitle(title + " - metres on a wall at 10 m; + = first round; colour = round order (dark first)", fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(out, dpi=120)
    print("\n".join(stats))


if __name__ == "__main__":
    main()
