#!/usr/bin/env python3
"""test_armory_open.py - run the REAL mod tree's open / tab / click flows through cfgsim (offline), the way a fresh client would.

    HZM_MOD=<mod dir> python docs/tools/test_armory_open.py
Seeds exactly what a cold profile has (coop_defaults' armory_defaults.cfg), optionally the server's lock pushes, then:
open.cfg -> tab 2 -> click an earned gun (inspect) -> EQUIP -> click a locked gun -> slot 3. Prints the unknown cvars/files the flows touched.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfgsim
import gen_armory as ga
import gen_loadout as gl

FAILS = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("  " + str(detail) if (detail and not ok) else ""))
    if not ok:
        FAILS.append(name)


def push_locks(sim, rows, unlocked):
    """what loadout_ui_exportUnlocks stufftexts (lock command, commit command, sort command)"""
    for w in rows:
        g = w["id"]
        un = g in unlocked
        sim.run('seta coop_loLkA%s set coop_loLkV%s %d' % (g, g, 0 if un else 1))
        sim.run('seta coop_loCmt%s exec ui/loadout/%s%s.cfg' % (g, "eq" if un else "lkw", g))
        sim.run('seta coop_loSrt%s exec ui/loadout/%s%s.cfg' % (g, "sru" if un else "srl", g))


def main():
    mod = gl.MOD
    rows = gl.load()
    tabs = ga.tabs_of(rows)
    sim = cfgsim.Sim(mod)
    sim.exec("ui/loadout/armory_defaults.cfg")                 # cold profile: coop_defaults.cfg execs this
    unlocked = {"01", "24", "48", "64", "02", "03", "28"}
    push_locks(sim, rows, unlocked)
    sim.run("seta coop_loInspectS1 exec ui/loadout/p01.cfg ; seta coop_loInspectS2 exec ui/loadout/p24.cfg")
    sim.exec("ui/loadout/open.cfg")
    go = [sim.get("coop_loK%dGo" % c, "") for c in range(13)]
    first = [g.replace("exec ui/loadout/t", "").replace(".cfg", "") for g in go[:7]]
    check("open: rifle tab, unlocked first", first[:3] == ["01", "02", "03"], first)
    check("open: slot-1 gun inspected, hero lit", sim.get("coop_loHero") == "1" and sim.get("coop_loPrevId") == "01", (sim.get("coop_loHero"), sim.get("coop_loPrevId")))
    check("open: compare shows equal for the equipped gun", sim.get("coop_loCeq0") == "1", sim.get("coop_loCeq0"))
    check("open: tab 0 flag", sim.get("coop_loTA0") == "1" and sim.get("coop_loTA2") == "0")
    # tab 2 (SMG)
    sim.run("exec ui/loadout/lktab2.cfg")
    ids = [w["id"] for w in tabs[2]]
    want = [i for i in ids if i in unlocked] + [i for i in ids if i not in unlocked]
    got = [sim.get("coop_loK%dGo" % c, "").replace("exec ui/loadout/t", "").replace(".cfg", "") for c in range(len(ids))]
    check("tab 2 sorted", got == want, (got, want))
    check("tab 2 flag", sim.get("coop_loTA2") == "1" and sim.get("coop_loTA0") == "0")
    # click an earned gun (Sten, id 28): inspect, selected mark, can equip
    c28 = got.index("28")
    sim.run(sim.get("coop_loK%dGo" % c28))
    check("click earned: inspect only (hero, CanEq, selected mark)", sim.get("coop_loPrevId") == "28" and sim.get("coop_loCanEq") == "1"
          and sim.get("coop_loKs%d" % c28) == "1" and sim.get("coop_loHeroLk") == "0")
    check("click earned: compare vs slot 1 (garand)", sim.get("coop_loCv0") == "20", sim.get("coop_loCv0"))
    # EQUIP into the active slot (slot 1 = coop_loCcur from init)
    sim.run("vstr coop_loCcur")
    check("equip: slot 1 holds 28", sim.get("coop_lo1") == "28" and sim.get("coop_loN1") == "STEN MK II", (sim.get("coop_lo1"), sim.get("coop_loN1")))
    check("equip: equipped mark on the card", sim.get("coop_loEqP%d" % c28) == "1", sim.get("coop_loEqP%d" % c28))
    check("equip: compare now equal", sim.get("coop_loCeq0") == "1" and sim.get("coop_loCpl0") == "0")
    # click a locked gun (Thompson drum, 25)
    c25 = got.index("25")
    sim.run(sim.get("coop_loK%dGo" % c25))
    check("click locked: hero shows the lock, no equip, selection moved", sim.get("coop_loHero") == "0" and sim.get("coop_loHeroLk") == "1"
          and sim.get("coop_loCanEq") == "0" and sim.get("coop_loKs%d" % c25) == "1" and sim.get("coop_loKs%d" % c28) == "0")
    check("click locked: requirement text", sim.get("coop_loReq", "").startswith("UNLOCK"), sim.get("coop_loReq"))
    # finish chips: the server pushed finishes 1 and 3 as open for slot 1 (and slot 2); STD is fixed first, then unlocked, then locked
    for n in (1, 2):
        for f in range(1, 8):
            sim.run("seta coop_loFsrt%d_%d exec ui/loadout/%s%d.cfg" % (n, f, "fsu" if f in (1, 3) else "fsl", f))
    sim.exec("ui/loadout/s1sel.cfg")
    chips = [sim.get("coop_loFp%dT" % q) for q in range(8)]
    check("finish chips: STD, then unlocked (GOLD BLUED), then locked", chips == ["STD", "GOLD", "BLUED", "CHROM", "BLOOD", "WOOD", "SNOW", "SAND"], chips)
    check("finish chips: lock flags", [sim.get("coop_loFp%dL" % q) for q in range(8)] == ["0", "0", "0", "1", "1", "1", "1", "1"])
    check("finish chip click = the finish gate", sim.get("coop_loFp1Go") == "vstr coop_loFcmt1", sim.get("coop_loFp1Go"))
    # slot 3 (sidearm) -> pistol tab
    sim.exec("ui/loadout/s3sel.cfg")
    check("slot 3: pistol tab", sim.get("coop_loTA4") == "1", sim.get("coop_loTA4"))
    pids = [w["id"] for w in tabs[4]]
    pgot = [sim.get("coop_loK%dGo" % c, "").replace("exec ui/loadout/t", "").replace(".cfg", "") for c in range(len(pids))]
    check("slot 3: pistols sorted, 48 first", pgot[0] == "48", pgot)
    check("slot 3: the colt is the equipped side", sim.get("coop_loEv0") == "37", sim.get("coop_loEv0"))
    # uniform stepper: natural ring by default, then the server's unlocked-first pointers (python mirror of cosorder.scr::cos_exportOrder)
    import json
    import re
    ring = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "armory_cos_ring.json")))
    def pg(n):
        return "%02d" % n if n < 10 else str(n)
    def walk(sim, start, steps, d="skin", var="coop_loCharN", tok=r",sn(\d+)"):
        sim.exec("ui/loadout/%s/%s%s.cfg" % (d, {"skin": "s", "helm": "h", "glove": "g"}[d], pg(start)))
        seq = [start]
        for _ in range(steps):
            sim.run("vstr %s" % var)
            m = re.search(tok, sim.get({"skin": "coop_loSkAcc", "helm": "coop_loHmAcc", "glove": "coop_loGlAcc"}[d], ""))
            seq.append(int(m.group(1)))
        return seq
    sk = ring["skin"]
    check("skin stepper, natural ring (cold defaults)", walk(sim, 1, 4) == sk[:5], walk(sim, 1, 4))
    locked = {2, 3, 7}
    order = [p for p in sk if p not in locked] + [p for p in sk if p in locked]
    n = len(order)
    for j, cur in enumerate(order):
        sim.run("seta coop_loSkNx%s exec ui/loadout/skin/s%s.cfg" % (pg(cur), pg(order[(j + 1) % n])))
        sim.run("seta coop_loSkPv%s exec ui/loadout/skin/s%s.cfg" % (pg(cur), pg(order[(j - 1) % n])))
    seq = walk(sim, 1, 6)
    check("skin stepper, unlocked first (1 -> 4 -> 5 -> 6 -> 8 ...)", seq == [1, 4, 5, 6, 8, 9, 10], seq)
    seq = walk(sim, 135, 4)
    check("skin stepper: last open page wraps into the locked ones (135? -> 2 -> 3 -> 7 -> 1)", order.index(135) + 4 < n or seq[1:4] == [2, 3, 7], seq)
    bad = sorted(set(l for l in sim.log if l.startswith("exec: missing")))
    check("no missing cfg files", not bad, bad[:6])
    novs = sorted(set(l for l in sim.log if l.startswith("vstr: no cvar")))
    print("vstr of unset cvars (a cold profile; harmless if archived-only):", novs[:12])
    print("FAILED %d" % len(FAILS) if FAILS else "ALL PASS")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
