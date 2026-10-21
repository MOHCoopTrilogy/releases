"""overview.py <map> <out.png> [x0 x1 y0 y1] - top-down plan of a map from its BSP entity lump: pathnodes coloured by height, named entities labelled,
vehicles, spawns, triggers. Used to choose objective sites by eye before the in-game scouting."""
import sys, math
sys.path.insert(0, "C:/mohaa-coop-dev/docs/tools")
import bsptrace as T
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
mp, out = sys.argv[1], sys.argv[2]
B = T.BSP.load(mp)
ents = B.entities()
def v(e):
    try:
        return [float(x) for x in e["origin"].split()]
    except Exception:
        return None
nodes = [v(e) for e in ents if e["classname"] == "info_pathnode" and v(e)]
fig, ax = plt.subplots(figsize=(14, 14))
ax.set_facecolor("#101216")
sc = ax.scatter([n[0] for n in nodes], [n[1] for n in nodes], c=[n[2] for n in nodes], s=5, cmap="viridis")
plt.colorbar(sc, ax=ax, shrink=0.5, label="node z")
cls = {"info_player_start": ("*", "#22c55e", 140), "trigger_use": ("^", "#a855f7", 30), "trigger_once": ("v", "#f59e0b", 25), "trigger_multiple": (".", "#64748b", 10),
       "script_model": ("s", "#f43f5e", 18), "script_origin": ("D", "#38bdf8", 14)}
for e in ents:
    p = v(e)
    if not p:
        continue
    c = e["classname"]
    if c in cls:
        m, col, s = cls[c]
        ax.scatter([p[0]], [p[1]], marker=m, c=col, s=s, zorder=5)
        tn = e.get("targetname", "")
        if tn and (c in ("script_model", "script_origin", "info_player_start") or c.startswith("trigger_")) and len(tn) > 2:
            ax.text(p[0] + 15, p[1] + 15, tn, fontsize=5.5, color="#e2e8f0")
    elif c.startswith("vehicle_") or c.startswith("ai_actor") or c.startswith("ai_allied"):
        ax.scatter([p[0]], [p[1]], marker="P", c="#fb923c", s=60, zorder=6)
        ax.text(p[0] + 15, p[1] + 15, e.get("targetname", c), fontsize=6, color="#fdba74")
ax.set_aspect("equal")
if len(sys.argv) < 7:
    ax.set_xlim(min(n[0] for n in nodes) - 500, max(n[0] for n in nodes) + 500)
    ax.set_ylim(min(n[1] for n in nodes) - 500, max(n[1] for n in nodes) + 500)
if len(sys.argv) >= 7:
    ax.set_xlim(float(sys.argv[3]), float(sys.argv[4])); ax.set_ylim(float(sys.argv[5]), float(sys.argv[6]))
ax.set_title(mp + " overview", color="white")
fig.patch.set_facecolor("#0b0d10")
ax.tick_params(colors="#9ca3af")
fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
print("wrote", out)
