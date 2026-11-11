"""plot_patterns.py - offline plots of every recoil pattern row, with the SAME maths as fgame Weapon::CoopApplyPatternKick
and Player::TickCoopRecoil (no player pull-down: the raw pattern a burst draws if you do not fight it).

    python plot_patterns.py [--mod DIR] [--out DIR]

Writes <out>/pattern_<stem>.png for the main guns and <out>/pattern_sheet.png (all main guns, aimed, standing), plus
<out>/pattern_stance.png (hip / aimed / crouched / prone for four guns) and <out>/pattern_numbers.tsv. Fire intervals are
the GAME's (the tik dm firedelay, which is what a player actually gets), not the real rate.
"""
import math
import os
import random
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


MOD = arg("--mod", os.path.join(ROOT, "hzm-mohaa-coop-mod"))
OUT = arg("--out", os.path.join(HERE, "..", "plots"))
COLS = ["kick1", "kick", "grow", "growN", "plateau", "platMul", "drift", "sway", "period", "phase", "jitP", "jitY",
        "cap", "yawCap", "hip", "ret", "recenter", "minDecay", "maxDecay", "settle"]
# game fire interval (s), from the shipped tiks (dm firedelay); burst length
GAME = {"thompsonsmg": (0.09, 30), "thompsonsmg_tommy28": (0.09, 30), "mp40": (0.08, 32), "ppsh_smg": (0.09, 35),
        "sten": (0.07, 32), "bar": (0.115, 20), "fg42": (0.09, 20), "mp44": (0.11, 30), "coop_bren": (0.115, 30),
        "mg42portable": (0.06, 50), "greasegun": (0.1, 30), "m1_garand": (0.18, 8), "carbine": (0.15, 15),
        "kar98": (1.1, 5), "colt45": (0.14, 7), "shotgun": (0.75, 5), "g43": (0.18, 10), "p38": (0.15, 8),
        "dp28": (0.115, 30), "30calportable": (0.09, 50), "enfield": (1.1, 5), "svt_rifle": (0.65, 10),
        "lugerp08": (0.15, 8), "webley_revolver": (0.12, 6)}
MAIN = ["thompsonsmg", "thompsonsmg_tommy28", "mp40", "ppsh_smg", "sten", "greasegun", "bar", "fg42", "mp44",
        "coop_bren", "mg42portable", "dp28", "m1_garand", "carbine", "kar98", "colt45", "shotgun", "p38"]
NAMES = {"thompsonsmg": "Thompson M1A1", "thompsonsmg_tommy28": "Thompson M1928 (Cutts)", "mp40": "MP40",
         "ppsh_smg": "PPSh-41", "sten": "Sten Mk II", "greasegun": "M3 Grease Gun", "bar": "BAR M1918A2",
         "fg42": "FG 42", "mp44": "StG 44", "coop_bren": "Bren Mk I", "mg42portable": "MG 42 (unmounted)",
         "dp28": "DP-28", "m1_garand": "M1 Garand", "carbine": "M1 Carbine", "kar98": "Kar98k", "colt45": "Colt M1911",
         "shotgun": "M1897 Trench Gun", "p38": "Walther P38"}


def load():
    rows = {}
    for l in open(os.path.join(MOD, "coop_mod", "recoil_pattern.txt")):
        if l.startswith("//") or not l.strip():
            continue
        c = l.split()
        rows[c[0]] = dict(zip(COLS, map(float, c[1:])))
    return rows


# [real rof 2026-11-10] the automatics now fire at the rate of coop_mod/weapon_rof.txt (the engine's FireDelay override)
ROF = {}
try:
    for _l in open(os.path.join(MOD, "coop_mod", "weapon_rof.txt")):
        _c = _l.split()
        if len(_c) == 6 and not _l.startswith("/"):
            ROF[_c[0]] = float(_c[2])
except OSError:
    pass
for _k in list(GAME):
    if _k in ROF:
        GAME[_k] = (ROF[_k], GAME[_k][1])


def burst(r, interval, shots, mult=1.0, seed=None, aimed=True, auto=False):
    """aim offsets (yaw_right_deg, climb_deg) at the moment each round leaves - the engine's maths, step 1/120 s"""
    rnd = random.Random(seed)
    cr = (lambda: 2.0 * (rnd.random() - 0.5)) if seed is not None else (lambda: 0.0)
    owed = [0.0, 0.0]   # climb +, right +
    view = [0.0, 0.0]
    heat, shot_t, hold, t = 0.0, -10.0, -1.0, 0.0
    pts = []
    m = mult * (1.0 if aimed else r["hip"])
    dtf = 1.0 / 120.0
    for k in range(shots):
        tfire = k * interval
        while t + 1e-9 < tfire:     # recovery ticks between rounds
            t += dtf
            if t >= hold:
                for ax in (0, 1):
                    o = owed[ax]
                    if o == 0.0:
                        continue
                    rate = min(max(abs(o) * r["recenter"], r["minDecay"]), r["maxDecay"])
                    back = min(rate * dtf, abs(o)) * (1 if o > 0 else -1)
                    view[ax] -= back * r["ret"]
                    owed[ax] -= back
        pts.append((view[1], view[0]))
        dt = tfire - shot_t
        excess = dt - (interval * 1.5 + 0.05)
        if excess > 0:
            heat *= max(0.0, 1.0 - excess / r["settle"])
        n = int(heat)
        if n <= 0:
            v = r["kick1"]
        else:
            g = min(1.0, (n - 1) / r["growN"])
            v = r["kick"] * (1 + r["grow"] * g)
            if r["plateau"] > 0 and n >= int(r["plateau"]):
                v *= r["platMul"]
        h = v * (r["drift"] + r["sway"] * math.sin(2 * math.pi * (n / r["period"] + r["phase"])))
        v *= 1 + r["jitP"] * cr()
        h += v * r["jitY"] * cr()
        v *= m
        h *= m
        cap = min(r["cap"], 12.0)
        nxt = owed[0] + v
        if nxt > cap:
            v = cap - owed[0]
        owed[0] += v
        nxt = owed[1] + h
        if nxt > r["yawCap"]:
            h = r["yawCap"] - owed[1]
        elif nxt < -r["yawCap"]:
            h = -r["yawCap"] - owed[1]
        owed[1] += h
        view[0] += v
        view[1] += h
        heat += 1
        shot_t = tfire
        hold = tfire + ((min(interval * 1.5, 0.2) + 0.05) if (interval < 0.125 or auto) else 0.06)
    return pts


def draw(ax, r, stem, interval, shots, mult=1.0, aimed=True, title=None):
    auto = stem in ROF
    for s in range(6):
        p = burst(r, interval, shots, mult, seed=s, aimed=aimed, auto=auto)
        ax.plot([x for x, _ in p], [y for _, y in p], "o", ms=2.5, alpha=0.35, color="#c0392b")
    p = burst(r, interval, shots, mult, aimed=aimed, auto=auto)
    ax.plot([x for x, _ in p], [y for _, y in p], "-o", ms=3, lw=1, color="#1f3a5f")
    for i in (0, 4, 9, 19, 29):
        if i < len(p):
            ax.annotate(str(i + 1), p[i], fontsize=6, xytext=(3, 0), textcoords="offset points")
    ax.set_title(title or NAMES.get(stem, stem), fontsize=8)
    ax.set_aspect("equal")
    ax.set_xlim(-6, 6)
    ax.set_ylim(-0.5, 12.5)
    ax.axhline(0, color="#888", lw=0.5)
    ax.axvline(0, color="#888", lw=0.5)
    ax.tick_params(labelsize=6)
    ax.grid(True, lw=0.3, alpha=0.5)
    return p


def single_trace(r, interval, shots, total=1.6):
    """view climb against time for a short string (the kick and its recovery), engine maths, 1/120 s"""
    owed, view, heat, shot_t, hold = 0.0, 0.0, 0.0, -10.0, -1.0
    ts, vs = [], []
    k, t, dtf = 0, 0.0, 1.0 / 120.0
    while t < total:
        if k < shots and t + 1e-9 >= k * interval:
            n = int(heat)
            v = r["kick1"] if n <= 0 else r["kick"] * (1 + r["grow"] * min(1.0, (n - 1) / r["growN"]))
            v = min(v, r["cap"] - owed)
            owed += v
            view += v
            heat += 1
            hold = t + ((min(interval * 1.5, 0.2) + 0.05) if interval < 0.125 else 0.06)
            k += 1
        elif t >= hold and owed > 0:
            rate = min(max(owed * r["recenter"], r["minDecay"]), r["maxDecay"])
            back = min(rate * dtf, owed)
            view -= back * r["ret"]
            owed -= back
        ts.append(t)
        vs.append(view)
        t += dtf
    return ts, vs


def main():
    rows = load()
    os.makedirs(OUT, exist_ok=True)
    nums = ["stem\tinterval\tshots\tclimb_last\tyaw_last\tclimb_after_10\tmax_climb"]
    cols = 6
    rws = math.ceil(len(MAIN) / cols)
    fig, axes = plt.subplots(rws, cols, figsize=(cols * 2.4, rws * 3.6))
    for i, stem in enumerate(MAIN):
        interval, shots = GAME[stem]
        ax = axes.flat[i]
        p = draw(ax, rows[stem], stem, interval, shots)
        ax.set_xlabel("deg right", fontsize=6)
        if i % cols == 0:
            ax.set_ylabel("deg climb (aim offset when each round leaves)", fontsize=6)
        nums.append("%s\t%.3f\t%d\t%.2f\t%.2f\t%.2f\t%.2f" % (stem, interval, shots, p[-1][1], p[-1][0],
                                                             p[min(9, len(p) - 1)][1], max(y for _, y in p)))
    for j in range(len(MAIN), len(axes.flat)):
        axes.flat[j].axis("off")
    fig.suptitle("HZM recoil patterns - aimed, standing, no pull-down; blue = the pattern, red = 6 bursts with jitter "
                 "(real fire rates)", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(os.path.join(OUT, "pattern_sheet.png"), dpi=130)
    plt.close(fig)

    # stance / hip comparison
    four = ["thompsonsmg", "mp40", "mg42portable", "m1_garand"]
    modes = [("hip", 1.0, False), ("aimed", 1.0, True), ("crouched", 0.80, True), ("prone", 0.55, True)]
    fig, axes = plt.subplots(len(four), len(modes), figsize=(len(modes) * 2.4, len(four) * 3.4))
    for a, stem in enumerate(four):
        interval, shots = GAME[stem]
        for b, (nm, mult, aimed) in enumerate(modes):
            draw(axes[a][b], rows[stem], stem, interval, shots, mult, aimed, NAMES[stem] + " - " + nm)
    fig.suptitle("Stance and sights (coop_recoilCrouch 0.80, coop_recoilProne 0.55, per-gun hip multiplier)", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(os.path.join(OUT, "pattern_stance.png"), dpi=120)
    plt.close(fig)
    # single rounds: the big kick and how fast it settles (bolt / semi / pistol / shotgun)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for stem, shots, ivl in (("kar98", 1, 1.1), ("m1_garand", 3, 0.5), ("carbine", 3, 0.5), ("colt45", 3, 0.4),
                             ("shotgun", 1, 0.75), ("p38", 3, 0.4)):
        t, v = single_trace(rows[stem], ivl, shots)
        ax.plot(t, v, label="%s (%d at %.2f s)" % (NAMES[stem], shots, ivl))
    ax.set_xlabel("seconds", fontsize=8)
    ax.set_ylabel("view climb, deg", fontsize=8)
    ax.set_title("Single rounds: the kick, then the recovery (aimed, standing, no pull-down)", fontsize=9)
    ax.legend(fontsize=7)
    ax.grid(True, lw=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "pattern_single.png"), dpi=120)
    plt.close(fig)
    with open(os.path.join(OUT, "pattern_numbers.tsv"), "w", newline="\n") as f:
        f.write("\n".join(nums) + "\n")
    print("\n".join(nums))


if __name__ == "__main__":
    main()
