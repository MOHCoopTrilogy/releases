#!/usr/bin/env python3
"""patch_armory_b.py - the few HAND-maintained cfg files the Showroom Armory needs a line in (the record + an idempotent applier).

Everything else is generated (gen_loadout.py -> gen_armory.py). These files have no generator, so, like patch_armory_gating.py, the edit is a
script: it is idempotent, preserves each file's line endings, and `check` says whether the tree already has it.

    HZM_MOD=<mod dir> python docs/tools/patch_armory_b.py check|apply

  coop_defaults.cfg          + `exec ui/loadout/armory_defaults.cfg` (fail-locked sort commands, execs BEFORE the saved config)
  ui/loadout/init.cfg        + `vstr coop_loPubS1` before the p01 inspect (publish the slot-1 gun as the EQUIPPED side of the compare)
  ui/loadout/s<N>sel.cfg     + `vstr coop_loPubS<N>` before the slot's inspect replay (same, for the slot being activated)
  coop_mod/loadoutpick.scr   + the sort command push (coop_loSrt<id>), the PubS self-heal, loadout_ui_exportProgress (assets/armory_prog.scr.txt)
                             and the refill ping at the end of loadout_ui_exportUnlocks
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.environ.get("HZM_MOD") or os.path.join(ROOT, "hzm-mohaa-coop-mod")


def rd(p):
    return io.open(p, "r", encoding="latin-1", newline="").read()


def wr(p, t):
    io.open(p, "w", encoding="latin-1", newline="").write(t)


def eol(t):
    return "\r\n" if "\r\n" in t else "\n"


def insert_before(p, anchor, line):
    """insert `line` before the first line starting with `anchor` unless it is already in the file; returns True when changed"""
    t = rd(p)
    e = eol(t)
    if (line + e) in t or t.rstrip().endswith(line):
        return False
    i = t.find(anchor)
    assert i >= 0, "%s: anchor not found: %s" % (p, anchor)
    assert i == 0 or t[i - 1] == "\n", "%s: anchor is not at a line start: %s" % (p, anchor)
    wr(p, t[:i] + line + e + t[i:])
    return True


def append_line(p, line, marker):
    t = rd(p)
    e = eol(t)
    if line in t:
        return False
    if not t.endswith(e):
        t += e
    wr(p, t + e + marker + e + line + e)
    return True


def edit_once(p, old, new, marker):
    """replace `old` by `new` (both written with \\n; converted to the file's line endings) unless `marker` is already in the file"""
    t = rd(p)
    e = eol(t)
    if marker in t:
        return False
    o, n = old.replace("\n", e), new.replace("\n", e)
    assert t.count(o) == 1, "%s: anchor not unique/found (%d): %s" % (p, t.count(o), old[:60])
    wr(p, t.replace(o, n))
    return True


SCR = os.path.join("coop_mod", "loadoutpick.scr")
PROG_FN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "armory_prog.scr.txt")


def server_edits(p):
    """loadoutpick.scr: the sort command + progress pushes + the refill ping (see assets/armory_prog.scr.txt)"""
    ch = False
    ch |= edit_once(
        p,
        "\tlocal.i = 0\n\tlocal.w = 0\n\twhile(local.i < local.n){\n\t\t//raw locked-ness only",
        "\tlocal.i = 0\n\tlocal.w = 0\n\tlocal.chg = 0\t//[armory B] anything pushed -> ask the client to refill its card grid at the end\n\twhile(local.i < local.n){\n\t\t//raw locked-ness only",
        "local.chg = 0\t//[armory B]")
    ch |= edit_once(
        p,
        "\t\t\tlocal.w++\t//count the 2nd stufftext so the reliable-command flush (below) stays under the ring\n",
        "\t\t\t//[armory B 2026-10-18] the SORT command the client's card chain walks: ui/loadout/sru<id>.cfg places the gun among the unlocked\n"
        "\t\t\t//ones, srl<id>.cfg among the locked ones (gen_armory.py). Archived like the commands above; the fail-locked default is\n"
        "\t\t\t//ui/loadout/armory_defaults.cfg.\n"
        "\t\t\tif(local.lk == 0){\n"
        "\t\t\t\tlocal.player stufftext ( \"seta coop_loSrt\" + local.id + \" exec ui/loadout/sru\" + local.id + \".cfg\" )\n"
        "\t\t\t} else {\n"
        "\t\t\t\tlocal.player stufftext ( \"seta coop_loSrt\" + local.id + \" exec ui/loadout/srl\" + local.id + \".cfg\" )\n"
        "\t\t\t}\n"
        "\t\t\tlocal.chg = 1\n"
        "\t\t\tlocal.w++\n"
        "\t\t\tlocal.w++\t//count the 2nd and 3rd stufftext so the reliable-command flush (below) stays under the ring\n",
        "seta coop_loSrt\" + local.id")
    ch |= edit_once(
        p,
        "\t\t\tlocal.player stufftext ( \"seta coop_loInspectS\" + local.sl + \" exec ui/loadout/p\" + local.sid + \".cfg\" )\n",
        "\t\t\tlocal.player stufftext ( \"seta coop_loInspectS\" + local.sl + \" exec ui/loadout/p\" + local.sid + \".cfg\" )\n"
        "\t\t\tlocal.player stufftext ( \"seta coop_loPubS\" + local.sl + \" exec ui/loadout/pubgun\" + local.sid + \".cfg\" )\t//[armory B] the slot's gun = the EQUIPPED side of the compare\n",
        "seta coop_loPubS\" + local.sl")
    ch |= edit_once(
        p,
        "\twaitthread loadout_slotLocksExport local.player\n\n}end\n",
        "\twaitthread loadout_slotLocksExport local.player\n"
        "\t//[armory B 2026-10-18] unlock progress for the locked cards, then one refill ping when anything changed (sort order or progress)\n"
        "\tlocal.pc = ( waitthread loadout_ui_exportProgress local.player )\n"
        "\tif(local.player == NULL){ end }\n"
        "\tif(local.pc == 1){ local.chg = 1 }\n"
        "\tif(local.chg){ local.player stufftext ( \"vstr coop_loRefill\" ) }\n"
        "\n}end\n",
        "loadout_ui_exportProgress local.player )")
    # finish chips: per slot, which of the 7 finishes are open for the slot's gun (global unlock AND the gun mastered), as sort commands
    ch |= edit_once(
        p,
        "\t\tlocal.key = local.sid + \"|\" + local.mast + \"|\" + local.mvlk + \"|\" + local.txt\n",
        "\t\t//[armory B 2026-10-18] which finishes are open for this slot's gun (finish unlocked AND the gun mastered): the client sorts its chips\n"
        "\t\t//unlocked first from coop_loFsrt<slot>_<fid> (ui/loadout/fsu<fid>.cfg | fsl<fid>.cfg, gen_armory.py)\n"
        "\t\tlocal.fk = \"\"\n"
        "\t\tlocal.f = 1\n"
        "\t\twhile(local.f <= 7){\n"
        "\t\t\tlocal.flk = 0\n"
        "\t\t\tif(getcvar(\"coop_lockLoadout\") != \"0\"){\n"
        "\t\t\t\tif(local.mast == 0){ local.flk = 1 }\n"
        "\t\t\t\telse if(!(waitthread loadout_finUnlocked local.player local.f)){ local.flk = 1 }\n"
        "\t\t\t}\n"
        "\t\t\tlocal.fk = local.fk + local.flk\n"
        "\t\t\tlocal.f++\n"
        "\t\t}\n"
        "\t\tif(local.player == NULL){ end }\n"
        "\t\tlocal.key = local.sid + \"|\" + local.mast + \"|\" + local.mvlk + \"|\" + local.txt + \"|\" + local.fk\n",
        "local.key = local.sid + \"|\" + local.mast + \"|\" + local.mvlk + \"|\" + local.txt + \"|\" + local.fk")
    ch |= edit_once(
        p,
        "\t\t\tif(local.sid != \"\" && local.tab != \"\"){\n"
        "\t\t\t\tlocal.player stufftext ( \"seta coop_loEqR\" + local.tab + \"_\" + local.sl + \" set coop_loEqV\" + local.sid + \" 1\" )\n"
        "\t\t\t}\n",
        "\t\t\tif(local.sid != \"\" && local.tab != \"\"){\n"
        "\t\t\t\tlocal.player stufftext ( \"seta coop_loEqR\" + local.tab + \"_\" + local.sl + \" vstr coop_loEqOn\" + local.sid )\t//[armory B] the marker is a card flag now\n"
        "\t\t\t}\n"
        "\t\t\tlocal.f = 1\n"
        "\t\t\twhile(local.f <= 7){\n"
        "\t\t\t\tlocal.fi = local.f - 1\n"
        "\t\t\t\tif(local.fk[local.fi] == \"1\"){\n"
        "\t\t\t\t\tlocal.player stufftext ( \"seta coop_loFsrt\" + local.sl + \"_\" + local.f + \" exec ui/loadout/fsl\" + local.f + \".cfg\" )\n"
        "\t\t\t\t} else {\n"
        "\t\t\t\t\tlocal.player stufftext ( \"seta coop_loFsrt\" + local.sl + \"_\" + local.f + \" exec ui/loadout/fsu\" + local.f + \".cfg\" )\n"
        "\t\t\t\t}\n"
        "\t\t\t\tlocal.f++\n"
        "\t\t\t}\n",
        "\" vstr coop_loEqOn\" + local.sid )")
    ch |= edit_once(      # pace the finish pushes: 7 per changed slot, so one frame break in the middle
        p,
        "\t\t\t\tlocal.f++\n\t\t\t}\n\t\t\twaitframe\n",
        "\t\t\t\tlocal.f++\n\t\t\t\tif(local.f == 5){\n\t\t\t\t\twaitframe\n\t\t\t\t\tif(local.player == NULL){ end }\n\t\t\t\t}\n\t\t\t}\n\t\t\twaitframe\n",
        "if(local.f == 5){")
    # the function itself, before loadout_isUnlocked
    ch |= edit_once(
        p,
        "loadout_isUnlocked local.player local.tik:{\n",
        io.open(PROG_FN, encoding="utf-8").read() + "loadout_isUnlocked local.player local.tik:{\n",
        "loadout_ui_exportProgress local.player:{")
    return ch


def init_edits(p):
    ch = insert_before(p, "exec ui/loadout/p01.cfg", "vstr coop_loPubS1")
    # open = slot 1 active: the finish chips and the slot-1 compare are live from the first frame (the strip used to wait for a slot click)
    ch |= append_line(p, "exec ui/loadout/s1sel.cfg", "// [armory B 2026-10-18] the armory opens with slot 1 active")
    return ch


def sel_edits(p, n):
    """s<N>sel.cfg: publish the slot's gun as the compare's equipped side; fill the finish chips (and refill them when the server's
    mastery push replays coop_loMastApply)"""
    ch = insert_before(p, 'set coop_loOpenInspect "vstr coop_loInspectS%s"' % n, "vstr coop_loPubS%s" % n)
    ch |= edit_once(
        p,
        'set coop_loMastApply "exec ui/loadout/lkfin.cfg ; vstr coop_loMast%s ; vstr coop_loMvLk%s"' % (n, n),
        'set coop_loMastApply "exec ui/loadout/lkfin.cfg ; vstr coop_loMast%s ; vstr coop_loMvLk%s ; exec ui/loadout/ffill%s.cfg"' % (n, n, n),
        "vstr coop_loMvLk%s ; exec ui/loadout/ffill%s.cfg" % (n, n))
    ch |= insert_before(p, 'set coop_loMastTCur "vstr coop_loMastT%s"' % n, "exec ui/loadout/ffill%s.cfg" % n)
    return ch


def helm_edits(p):
    """helmet.scr: after the skin / helmet lock exports, push the unlocked-first page order (coop_mod/cosorder.scr, generated)"""
    ch = edit_once(
        p,
        "\t//something changed: re-exec the s-page the armory is currently showing (archived open-replay)\n",
        "\t//[armory B 2026-10-18] unlocked-first page order for the uniform stepper (cosorder.scr; pointer cvars the pages step through)\n"
        "\twaitthread coop_mod/cosorder.scr::cos_exportOrder local.player \"skin\"\n"
        "\tif( local.player == NULL ){ end }\n"
        "\t//something changed: re-exec the s-page the armory is currently showing (archived open-replay)\n",
        "cos_exportOrder local.player \"skin\"")
    ch |= edit_once(
        p,
        "\t//refresh the currently shown h-page's lock icon (see armory_skin_exportLocks tail)\n",
        "\twaitthread coop_mod/cosorder.scr::cos_exportOrder local.player \"helm\"\t//[armory B] unlocked-first order for the helmet stepper\n"
        "\tif( local.player == NULL ){ end }\n"
        "\t//refresh the currently shown h-page's lock icon (see armory_skin_exportLocks tail)\n",
        "cos_exportOrder local.player \"helm\"")
    return ch


def glove_edits(p):
    """gloves.scr: keep a lock FLAG per glove page (the other two exports already do), then push the page order"""
    ch = edit_once(
        p,
        "\t\tlocal.pg = local.i\n\t\tif( local.i < 10 ){ local.pg = \"0\" + local.i }\n",
        "\t\tlocal.player.flags[\"coop_loGlLkL\" + local.i] = local.lk\t//[armory B] read by cosorder.scr (unlocked-first glove order)\n"
        "\t\tlocal.pg = local.i\n\t\tif( local.i < 10 ){ local.pg = \"0\" + local.i }\n",
        "coop_loGlLkL\" + local.i")
    ch |= edit_once(
        p,
        "\t\t\tlocal.player stufftext ( \"seta coop_loGlLkA\" + local.pg + \" set coop_loCosLk 1\" )\n\t\t}\n\t}\n}end\n",
        "\t\t\tlocal.player stufftext ( \"seta coop_loGlLkA\" + local.pg + \" set coop_loCosLk 1\" )\n\t\t}\n\t}\n"
        "\twaitthread coop_mod/cosorder.scr::cos_exportOrder local.player \"glove\"\t//[armory B] unlocked-first order for the glove stepper\n"
        "}end\n",
        "cos_exportOrder local.player \"glove\"")
    return ch


def targets():
    U = os.path.join(MOD, "ui", "loadout")
    yield ("coop_defaults.cfg", os.path.join(MOD, "coop_defaults.cfg"),
           lambda p: append_line(p, "exec ui/loadout/armory_defaults.cfg", "// [armory B 2026-10-18] fail-locked sort commands + compare defaults (generated by gen_armory.py)"))
    yield ("init.cfg", os.path.join(U, "init.cfg"), init_edits)
    yield ("loadoutpick.scr", os.path.join(MOD, SCR), server_edits)
    yield ("helmet.scr", os.path.join(MOD, "coop_mod", "helmet.scr"), helm_edits)
    yield ("gloves.scr", os.path.join(MOD, "coop_mod", "gloves.scr"), glove_edits)
    for n in "1234":
        yield ("s%ssel.cfg" % n, os.path.join(U, "s%ssel.cfg" % n), lambda p, n=n: sel_edits(p, n))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    todo = []
    for name, p, fn in targets():
        t = rd(p)
        if mode == "apply":
            if fn(p):
                print("patched", name)
        else:
            tmp_done = {"coop_defaults.cfg": "exec ui/loadout/armory_defaults.cfg" in t,
                        "init.cfg": "vstr coop_loPubS1" in t and "exec ui/loadout/s1sel.cfg" in t,
                        "loadoutpick.scr": "loadout_ui_exportProgress local.player:{" in t and "seta coop_loSrt" in t,
                        "helmet.scr": "cos_exportOrder local.player \"helm\"" in t and "cos_exportOrder local.player \"skin\"" in t,
                        "gloves.scr": "cos_exportOrder local.player \"glove\"" in t}.get(
                name, ("vstr coop_loPubS%s" % name[1]) in t if name.startswith("s") else False)
            if name.startswith("s") and name.endswith("sel.cfg"):
                tmp_done = tmp_done and ("exec ui/loadout/ffill%s.cfg" % name[1]) in t
            if not tmp_done:
                todo.append(name)
    if mode != "apply":
        print("patch_armory_b: %s" % ("applied" if not todo else "MISSING in %s" % todo))
        return 1 if todo else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
