#!/usr/bin/env python3
"""test_armory_sim.py - offline proof of the Armory cfg chains (sorting, equipped/selected marks, compare join, progress join).

Builds the generated cfgs in memory, writes them (plus the real mod tree) to a scratch overlay, and runs them through cfgsim.Sim.
    python docs/tools/test_armory_sim.py            # exit 1 on the first failed expectation
"""
import io
import os
import random
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfgsim
import gen_armory as ga
import gen_loadout as gl
import gen_weapon_stats as gws

FAILS = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("  " + str(detail) if (detail and not ok) else ""))
    if not ok:
        FAILS.append(name)


def main():
    rows = gl.load()
    files, _clipped = gl.render_all(rows)
    out = ga.build(rows, files, gl.MOD)
    tmp = tempfile.mkdtemp(prefix="armsim_")
    try:
        for rel, text in out.items():
            p = os.path.join(tmp, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            io.open(p, "w", encoding="latin-1", newline="").write(text)
        for name, text in files.items():           # the generated gun pages too (t<id>, p<id>, eq/lkw ...)
            p = os.path.join(tmp, "ui", "loadout", name)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            io.open(p, "w", encoding="latin-1", newline="").write(text)
        tabs = ga.tabs_of(rows)
        stats = gws.load()
        rnd = random.Random(7)
        for trial in range(6):
            unl = set(w["id"] for t in tabs.values() for w in t if rnd.random() < (0.15 + 0.15 * trial))
            if trial == 0:
                unl = {"01", "24", "48", "64"}
            sim = cfgsim.Sim(tmp)
            sim.exec("ui/loadout/armory_defaults.cfg")
            for t in tabs.values():
                for w in t:
                    sim.run('set coop_loSrt%s "exec ui/loadout/%s%s.cfg"' % (w["id"], "sru" if w["id"] in unl else "srl", w["id"]))
            for t in range(6):
                ids = [w["id"] for w in tabs[t]]
                sim.exec("ui/loadout/fill%d.cfg" % t)
                want = [i for i in ids if i in unl] + [i for i in ids if i not in unl]
                got = []
                for c in range(len(ids)):
                    go = sim.get("coop_loK%dGo" % c, "")
                    got.append(go.replace("exec ui/loadout/t", "").replace(".cfg", ""))
                check("trial %d tab %d order (unlocked first, authoring order)" % (trial, t), got == want, (got, want))
                nu = len([i for i in ids if i in unl])
                locks = [sim.get("coop_loK%dL" % c) for c in range(len(ids))]
                check("trial %d tab %d lock flags" % (trial, t), locks == ["0"] * nu + ["1"] * (len(ids) - nu), locks)
                check("trial %d tab %d counts" % (trial, t),
                      sim.get("coop_loUnTxt") == "UNLOCKED %d" % nu and sim.get("coop_loLkTxt") == "LOCKED %d" % (len(ids) - nu),
                      (sim.get("coop_loUnTxt"), sim.get("coop_loLkTxt")))
                tail = [sim.get("coop_loK%dV" % c) for c in range(len(ids), ga.NC)]
                check("trial %d tab %d unused cards hidden" % (trial, t), all(v == "0" for v in tail), tail)
        # equipped / selected marks follow the card position
        sim = cfgsim.Sim(tmp)
        sim.exec("ui/loadout/armory_defaults.cfg")
        for t in tabs.values():
            for w in t:
                sim.run('set coop_loSrt%s "exec ui/loadout/%s%s.cfg"' % (w["id"], "sru" if w["id"] in {"01", "02", "24"} else "srl", w["id"]))
        sim.exec("ui/loadout/fill0.cfg")
        pos = [sim.get("coop_loK%dGo" % c).replace("exec ui/loadout/t", "").replace(".cfg", "") for c in range(13)].index("02")
        sim.run("vstr coop_loEqOn02")
        check("equipped mark lands on the card of gun 02 (pos %d)" % pos, sim.get("coop_loEqP%d" % pos) == "1")
        sim.run("vstr coop_loSlOn02")
        check("selected mark lands on the card of gun 02", sim.get("coop_loKs%d" % pos) == "1")
        # compare join: equipped 01 (garand) vs candidate 03 (kar98k)
        sim.exec("ui/loadout/pubgun01.cfg")
        sim.exec("ui/loadout/cand03.cfg")
        s1, s3 = stats["01"], stats["03"]
        check("raw texts", sim.get("coop_loCv0") == "110" and sim.get("coop_loEv0") == "50", (sim.get("coop_loCv0"), sim.get("coop_loEv0")))
        check("damage: candidate level %s vs equipped %s -> green + mark" % (s3["dmgL"], s1["dmgL"]),
              sim.get("coop_loCpl0") == "1" and sim.get("coop_loCmi0") == "0" and sim.get("coop_loCbg0_%s" % s3["dmgL"]) == "1")
        check("rate: candidate below equipped -> red -", sim.get("coop_loCmi1") == "1" and sim.get("coop_loCpl1") == "0")
        check("equipped bar level", sim.get("coop_loEb0_%s" % s1["dmgL"]) == "1" and sim.get("coop_loEb0_%d" % (int(s1["dmgL"]) + 1)) == "0")
        # n/a: gun 04 has no reload time
        sim.exec("ui/loadout/cand04.cfg")
        check("n/a reload shows n/a, no bar, no mark", sim.get("coop_loCv4") == "n/a" and sim.get("coop_loCpl4") == "0"
              and sim.get("coop_loCmi4") == "0" and sim.get("coop_loCeq4") == "0"
              and all(sim.get("coop_loCb%s4_%d" % (c, i)) == "0" for c in "ngr" for i in range(1, 11)))
        # progress join on a locked card
        sim.exec("ui/loadout/fill0.cfg")
        lpos = [sim.get("coop_loK%dGo" % c).replace("exec ui/loadout/t", "").replace(".cfg", "") for c in range(13)].index("05")
        sim.run('set coop_loPgA05 "vstr coop_loPgX7"')
        sim.exec("ui/loadout/pll_05_%d.cfg" % lpos)
        check("locked card progress level 7 lights step 7 only", sim.get("coop_loKb%d_7" % lpos) == "1" and sim.get("coop_loKb%d_6" % lpos) == "0")
        bad = [l for l in sim.log if l.startswith("exec: missing")]
        check("no missing cfg files", not bad, bad[:5])
        print("generated files:", len(out))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("FAILED %d" % len(FAILS) if FAILS else "ALL PASS")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
