"""gen_weapon_rof.py - real rates of fire for every automatic, as a GENERATED table (coop_mod/weapon_rof.txt), plus the
per-shot damage retune that keeps time-to-kill in line, and the AI burst length.

WHY. User 2026-11-10: "set every gun's rate of fire to its real-world value, and do the same for enemy and friendly AI
using those guns." The tik fire delays were tuned for feel (MP40 0.08 s = 750 rpm against a real 500, PPSh 0.09 s = 667
against a measured 1050). Nothing is hand-edited into the ~1,000 weapon tiks: the engine (fgame Weapon::FireDelay,
coop_realRof 1) reads this table, finish variants follow their base by suffix stripping, exactly like the recoil
patterns, and AI fire is driven at the same rate (Sentient::CoopAiRofFire).

INPUTS
  recoil_research.tsv / recoil_measured.tsv  the rate (measured beats spec), through recoil_shape.tsv's stem -> physics map
  weapon_rof_tune.tsv                        authored: rate overrides with the reason, AI burst length, bullets per shot
  the weapon tiks (weapon_tik_values.py)     today's delay / damage / pellets, from the copy the engine loads

DAMAGE. Time to kill 100 HP (AI, MP) = (ceil(100 / (dmg x pellets)) - 1) x delay. A gun whose TTK moves more than
+-TTK_BAND keeps its role by an integer per-shot damage change (the smallest one that brings TTK back inside the band);
otherwise damage is untouched. The table carries the SCALE (new / tik damage), applied at the shot, so every variant tik
keeps its own base number.

    python docs/tools/gen_weapon_rof.py build  [--mod DIR]   write <mod>/coop_mod/weapon_rof.txt + the report
    python docs/tools/gen_weapon_rof.py check  [--mod DIR]   exit 1 when the table is stale
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_recoil_pattern as G  # noqa: E402
import weapon_tik_values as V  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
MOD = G.MOD
V.MOD = MOD          # the tiks of the same mod tree the table is written to
OUT = os.path.join(MOD, "coop_mod", "weapon_rof.txt")
REPORT = os.path.join(ROOT, "docs", "proposals", "recoil_2026-11-10", "ROF.md")
TTK_BAND = 0.20
HP = 100.0
DEFAULT_BURST = {"smg": 6, "lmg": 5, "mg": 6}


def ttk(dmg, count, delay, hp=HP):
    """discrete: every round hits the torso"""
    per = dmg * count
    if per <= 0:
        return None
    return (math.ceil(hp / per) - 1) * delay


def ttk_c(dmg, count, delay, hp=HP):
    """continuous: the same with the round count un-rounded - what TTK averages to across hit locations (head x4,
    limbs less) and partial hits. The retune holds THIS inside the band; the discrete one jumps a whole round at a time
    and would demand absurd damage changes to stay put."""
    per = dmg * count
    if per <= 0:
        return None
    return max(0.0, hp / per - 1.0) * delay


def derive():
    phys = G.physics()
    tune = {r["stem"]: r for r in G.read_tsv(os.path.join(HERE, "weapon_rof_tune.tsv"))}
    rows = []
    for s in G.read_tsv(os.path.join(HERE, "recoil_shape.tsv")):
        if s["cls"] != "A":
            continue
        stem = s["stem"]
        p = phys[s["phys"]]
        t, k = {}, stem
        while True:                       # a variant takes its base's tuning, the recoil-pattern way
            if k in tune:
                t = tune[k]
                break
            if "_" not in k:
                break
            k = k.rsplit("_", 1)[0]
        rpm, src = p["rof_rpm"], p["rof_rpm_src"]
        if t.get("rpm", "-") not in ("-", ""):
            rpm, src = float(t["rpm"]), "tune: " + t.get("note", "")
        v = V.values(stem)
        if not v or not v.get("firedelay") or not v.get("bulletdamage"):
            print("skip %s: no tik values" % stem)
            continue
        d0, c0, t0 = v["bulletdamage"], (v["bulletcount"] or 1.0), v["firedelay"]
        count = float(t["count"]) if t.get("count", "-") not in ("-", "") else c0
        delay = round(60.0 / rpm, 4)
        k0 = ttk_c(d0, c0, t0)
        dmg = d0
        k1 = ttk_c(dmg, count, delay)
        free = t.get("ttk", "-") == "free"
        if not free and k0 and k1 is not None and abs(k1 - k0) / k0 > TTK_BAND:
            # the smallest integer damage change that brings TTK back inside the band (search outward from today's)
            best = None
            for step in range(1, int(d0)):
                for cand in (d0 + step, d0 - step):
                    if cand <= 0:
                        continue
                    kk = ttk_c(cand, count, delay)
                    if kk is not None and abs(kk - k0) / k0 <= TTK_BAND:
                        best = cand
                        break
                if best:
                    break
            if best:
                dmg = best
                k1 = ttk_c(dmg, count, delay)
        heavy = "mg" if s["layout"] == "inline" and "mg42" in stem or "30cal" in stem else ("lmg" if float(s["hip"]) >= 1.4 else "smg")
        burst = int(t["aiburst"]) if t.get("aiburst", "-") not in ("-", "") else DEFAULT_BURST[heavy]
        rows.append(dict(stem=stem, name=v["name"], rpm=rpm, src=src, delay=delay, t0=t0, rpm0=60.0 / t0, d0=d0, c0=c0,
                         dmg=dmg, count=count, scale=round(dmg / d0, 4), burst=burst, ttkc0=k0, ttkc1=k1, free=free,
                         ttk0=ttk(d0, c0, t0), ttk1=ttk(dmg, count, delay),
                         ttk0_50=ttk(d0, c0, t0, 50), ttk1_50=ttk(dmg, count, delay, 50), tik=v["tik"]))
    return rows


def turret_rows():
    out = []
    for r in G.read_tsv(os.path.join(HERE, "weapon_rof_turrets.tsv")):
        rpm = float(r["rpm"])
        out.append(dict(stem=r["stem"], rpm=rpm, delay=round(60.0 / rpm, 4), note=r["note"]))
    return out


def render(rows):
    out = ["// GENERATED by docs/tools/gen_weapon_rof.py (rates: recoil_research/recoil_measured.tsv, tune: weapon_rof_tune.tsv)",
           "// - do not edit. Read by fgame Weapon::FireDelay / the shot damage / Sentient::CoopAiRofFire (coop_realRof 1).",
           "// Finish variants share their base row (trailing _segments dropped). count 0 = the tik's own bullets per shot.",
           "// name rpm delay dmgscale count aiburst"]
    for r in rows:
        cnt = int(r["count"]) if r["count"] != r["c0"] else 0
        out.append("%s %g %.4f %.4f %d %d" % (r["stem"], r["rpm"], r["delay"], r["scale"], cnt, r["burst"]))
    out.append("// turret MGs (weapon_rof_turrets.tsv): only an AI gunner's fire reads these; aiburst 0 = the turret's own burst rhythm")
    for t in turret_rows():
        out.append("%s %g %.4f 1.0000 0 0" % (t["stem"], t["rpm"], t["delay"]))
    return "\n".join(out) + "\n"


def fmt(x):
    return "-" if x is None else "%.2f" % x


def report(rows):
    out = ["# Real rates of fire - before / after (GENERATED by docs/tools/gen_weapon_rof.py)", "",
           "TTK = time to kill from the first round, every round hitting, no armour/location multiplier: (rounds - 1) x delay. "
           "100 HP = AI and MP; 50 HP = Hardcore. Damage changes only where TTK moved more than %d%%." % int(TTK_BAND * 100), "",
           "Avg TTK = the continuous form (round count un-rounded: the average across hit locations); the retune holds it "
           "inside the band. 'free' = exempt by weapon_rof_tune.tsv (the before value was an artifact).", "",
           "| gun | stem | rpm before | rpm after | rate source | dmg before | dmg after | bullets before/after | avg TTK100 before | avg TTK100 after "
           "| TTK100 before | TTK100 after | TTK50 before | TTK50 after | AI burst |", "|" + "---|" * 15]
    for r in rows:
        out.append("| %s | %s | %d | %d | %s | %g | %g | %g/%g | %s | %s%s | %s | %s | %s | %s | %d |" % (
            r["name"], r["stem"], round(r["rpm0"]), round(r["rpm"]), r["src"].replace("|", "/")[:90], r["d0"], r["dmg"],
            r["c0"], r["count"], fmt(r["ttkc0"]), fmt(r["ttkc1"]), " (free)" if r["free"] else "", fmt(r["ttk0"]),
            fmt(r["ttk1"]), fmt(r["ttk0_50"]), fmt(r["ttk1_50"]), r["burst"]))
    out += ["", "## Turret machine guns (AI gunners)", "",
            "An AI on a turret fired every server frame (40 a second = 2,400 rpm). Now each round leaves at the gun's real rate and "
            "carries the rounds it replaces (frame rate / real rate, capped x2.5), so an MG 42 nest keeps its lethality in half the "
            "rounds and a .30 cal - slower for real - is about half as dangerous as before.", "",
            "| turret | rpm before (AI) | rpm after | per-round damage x | source |", "|---|---|---|---|---|"]
    for t in turret_rows():
        rps = t["rpm"] / 60.0
        out.append("| %s | 2400 | %d | %.2f | %s |" % (t["stem"], t["rpm"], min(2.5, 40.0 / rps), t["note"]))
    return "\n".join(out) + "\n"


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    rows = derive()
    text = render(rows)
    if mode == "build":
        with open(OUT, "w", newline="\n") as f:
            f.write(text)
        os.makedirs(os.path.dirname(REPORT), exist_ok=True)
        with open(REPORT, "w", newline="\n", encoding="utf-8") as f:
            f.write(report(rows))
        print("wrote %s (%d rows) and %s" % (OUT, len(rows), REPORT))
    else:
        cur = open(OUT).read() if os.path.exists(OUT) else ""
        if cur != text:
            print("STALE: %s - run build" % OUT)
            return 1
        print("ok: %d rows" % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
