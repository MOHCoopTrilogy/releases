#!/usr/bin/env python3
"""patch_armory_c.py - the HAND-maintained files the second Showroom pass (tab counts, slot names, finish name) needs a line in. Idempotent applier + check.

    HZM_MOD=<mod dir> python docs/tools/patch_armory_c.py check|apply

  coop_mod/loadoutpick.scr   loadout_ui_exportUnlocks: per-tab "unlocked / total" counts pushed as seta coop_loTc<t> (tab strip), and the slot tile NAME
                             command coop_loNsA<slot> pushed next to coop_loPubS<slot>
  ui/loadout/init.cfg        replays coop_loNsA1..4 (the four slot tiles show their gun's name from the first frame)
  ui/loadout/fin<f>_s<n>.cfg remembers the applied finish NAME of the slot (coop_loFNmS<n>) and shows it (coop_loFinNm, under the swatches)
  ui/loadout/s<N>sel.cfg     replays coop_loFNmS<N> when the slot is activated
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_armory_b as pb

MOD = pb.MOD
FIN = ["STD", "GOLD", "CHROME", "BLUED", "BLOODY", "WOOD", "SNOW", "SAND"]


def server_edits(p):
    ch = pb.edit_once(
        p,
        "\tlocal.chg = 0\t//[armory B] anything pushed -> ask the client to refill its card grid at the end\n",
        "\tlocal.chg = 0\t//[armory B] anything pushed -> ask the client to refill its card grid at the end\n"
        "\twaitthread coop_mod/unlockprog_gen.scr::main\t//[armory B] also holds the gun -> category table (coop_loTabOf)\n"
        "\tlocal.t = 0\n"
        "\twhile(local.t < 6){\n"
        "\t\tlocal.player.flags[\"coop_loTcU\" + local.t] = 0\n"
        "\t\tlocal.t++\n"
        "\t}\n",
        "coop_loTcU\" + local.t] = 0")
    ch |= pb.edit_once(
        p,
        "\t\tlocal.id = level.coop_loRosterId[local.i]\n\t\tif(local.player.flags[\"coop_loLkALast\" + local.id] != local.lk){\n",
        "\t\tlocal.id = level.coop_loRosterId[local.i]\n"
        "\t\tif(local.lk == 0){\t//[armory B] the tab strip's \"unlocked / total\"\n"
        "\t\t\tlocal.tb = level.coop_loTabOf[local.id]\n"
        "\t\t\tif(local.tb != NIL){ local.player.flags[\"coop_loTcU\" + local.tb] = local.player.flags[\"coop_loTcU\" + local.tb] + 1 }\n"
        "\t\t}\n"
        "\t\tif(local.player.flags[\"coop_loLkALast\" + local.id] != local.lk){\n",
        "the tab strip's \"unlocked / total\"")
    ch |= pb.edit_once(
        p,
        "\t//[user 2026-08-18] FINISH STRIP locks - same archived-seta + diff-guard pattern as the gun\n",
        "\t//[armory B] per-tab counts for the tab strip (coop_loTc<t> = \"5 / 13\"), pushed only when they change\n"
        "\tlocal.t = 0\n"
        "\twhile(local.t < 6){\n"
        "\t\tlocal.ctx = \"\" + local.player.flags[\"coop_loTcU\" + local.t] + \" / \" + level.coop_loTabN[local.t]\n"
        "\t\tif(local.player.flags[\"coop_loTcLast\" + local.t] != local.ctx){\n"
        "\t\t\tlocal.player.flags[\"coop_loTcLast\" + local.t] = local.ctx\n"
        "\t\t\tlocal.player stufftext ( \"seta coop_loTc\" + local.t + \" \" + local.ctx )\n"
        "\t\t}\n"
        "\t\tlocal.t++\n"
        "\t}\n"
        "\t//[user 2026-08-18] FINISH STRIP locks - same archived-seta + diff-guard pattern as the gun\n",
        "coop_loTcLast")
    ch |= pb.edit_once(
        p,
        "\t\t\tlocal.player stufftext ( \"seta coop_loPubS\" + local.sl + \" exec ui/loadout/pubgun\" + local.sid + \".cfg\" )",
        "\t\t\tlocal.player stufftext ( \"seta coop_loNsA\" + local.sl + \" exec ui/loadout/nsn\" + local.sl + \"_\" + local.sid + \".cfg\" )\t//[armory B] the slot tile's name\n"
        "\t\t\tlocal.player stufftext ( \"seta coop_loPubS\" + local.sl + \" exec ui/loadout/pubgun\" + local.sid + \".cfg\" )",
        "seta coop_loNsA\" + local.sl")
    return ch


def init_edits(p):
    t = pb.rd(p)
    e = pb.eol(t)
    if "vstr coop_loNsA1" in t:
        return False
    if not t.endswith(e):
        t += e
    pb.wr(p, t + e.join(["// [armory B 2026-10-18] the four slot tiles show their gun's name", "vstr coop_loNsA1", "vstr coop_loNsA2", "vstr coop_loNsA3", "vstr coop_loNsA4"]) + e)
    return True


def fin_edits(p, f, n):
    t = pb.rd(p)
    e = pb.eol(t)
    if "coop_loFNmS%d" % n in t:
        return False
    if not t.endswith(e):
        t += e
    pb.wr(p, t + ('seta coop_loFNmS%d "set coop_loFinNm %s"' % (n, FIN[f])) + e + ("set coop_loFinNm %s" % FIN[f]) + e)
    return True


def sel_edits(p, n):
    return pb.insert_before(p, "exec ui/loadout/ffill%d.cfg" % n, "vstr coop_loFNmS%d" % n)


def targets():
    U = os.path.join(MOD, "ui", "loadout")
    yield ("loadoutpick.scr", os.path.join(MOD, pb.SCR), server_edits, lambda t: "coop_loTcLast" in t and "seta coop_loNsA\" + local.sl" in t)
    yield ("init.cfg", os.path.join(U, "init.cfg"), init_edits, lambda t: "vstr coop_loNsA1" in t)
    for n in range(1, 5):
        yield ("s%dsel.cfg" % n, os.path.join(U, "s%dsel.cfg" % n), lambda p, n=n: sel_edits(p, n), lambda t, n=n: "vstr coop_loFNmS%d" % n in t)
        for f in range(8):
            yield ("fin%d_s%d.cfg" % (f, n), os.path.join(U, "fin%d_s%d.cfg" % (f, n)), lambda p, f=f, n=n: fin_edits(p, f, n),
                   lambda t, n=n: "coop_loFNmS%d" % n in t)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    todo = []
    for name, p, fn, ok in targets():
        if mode == "apply":
            if fn(p):
                print("patched", name)
        elif not ok(pb.rd(p)):
            todo.append(name)
    if mode != "apply":
        print("patch_armory_c: %s" % ("applied" if not todo else "MISSING in %s" % todo))
        return 1 if todo else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
